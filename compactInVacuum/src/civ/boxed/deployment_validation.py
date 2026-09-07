from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

import FreeCAD as App
import Part
import yaml

from ..config import dump_config_yaml
from ..layout import build_detector_placements, detector_center
from ..validation_compact import (
    find_acceptance_obstructions,
    _detector_acceptance_metrics,
    _coincidence_metrics,
)
from ..detector import detector_stack_metrics
from ..validation_rules import evaluate_config_rules
from .geometry import V, moved, fused
from .deployment import ANGLES, flatten, vector, part_name, chamber_environment
from .motion import (
    Phase,
    overlap,
    certify_phase,
    study_void_candidates,
    verify_void_regions,
)
from .validation import contact_area


def collisions(first, second=None, tolerance=1e-6):
    failures = []
    items = list(first.items())
    for index, (name, a) in enumerate(items):
        others = second.items() if second is not None else items[:index]
        for other, b in others:
            if name == other:
                continue
            volume = overlap(a, b)
            if volume > tolerance:
                failures.append({"a": name, "b": other, "volume_mm3": volume})
    return failures


def validate_deployment(cfg, s, d, f, strict=False, output_path=None, side=None):
    checks, phases, margins, headrooms = [], [], {}, {}
    tolerance = s.collision_volume_tolerance_mm3

    def check(name, passed, detail, failures=None, evidence=False):
        status = (
            "pass" if passed else ("warning" if evidence and not strict else "fail")
        )
        checks.append(
            dict(
                name=name,
                status=status,
                detail=detail,
                failures=failures or [],
                strict_only=evidence,
            )
        )
        print(f"{status.upper()} {name}", file=sys.stderr, flush=True)

    for rule in evaluate_config_rules(cfg):
        if not rule.strict_only:
            check(rule.name, rule.passed, rule.detail)
    if side is not None:
        local = cfg.compact_one.deployment.local_support
        check(
            "registered_local_support_dimensions_match",
            local is not None
            and abs(local.mount_radius_mm - s.dock_plane_r_mm) < 1e-9
            and abs(local.release_clearance_mm - s.radial_release_mm) < 1e-9,
            "Local support and moving module share the configured radial interface",
        )
        ports = cfg.compact_one.deployment.service_ports
        check(
            "top_rotary_left_signals_right_access",
            cfg.compact_one.deployment.maintenance_access.wall == "positive_x_side"
            and all(
                p.wall
                == ("positive_y_top" if p.role == "rotary" else "negative_x_side")
                for p in ports
            ),
            "Physical port normals are top rotary, negative-X signals and positive-X maintenance access",
        )
        check(
            "no_annular_support_present",
            "AnnularSupportWeldment" not in f.fixed and len(f.support_bodies) == 4,
            "Four separately installable local support bodies replace the closed annulus",
        )
    else:
        boxed = cfg.compact_one.deployment.boxed_support
        check(
            "registered_boxed_support_dimensions_match",
            boxed is not None
            and abs(boxed.mount_radius_mm - s.dock_plane_r_mm) < 1e-9
            and abs(boxed.ring_outer_radius_mm - s.ring_outer_radius_mm) < 1e-9
            and abs(boxed.release_clearance_mm - s.radial_release_mm) < 1e-9,
            "Resolved platform metadata and detailed mechanism share one dimensional source",
        )

    actors = flatten(f.sectors)
    services = {
        **flatten(f.plugs),
        **flatten(f.looms),
        **{
            f"{sector}_GroundBond": fused(parts.values())
            for sector, parts in f.grounds.items()
        },
    }
    installed = {**actors, **flatten(f.retainers), **services}
    env = chamber_environment(f, work=True, closed=True)
    invalid = [
        n
        for n, sh in {**installed, **env}.items()
        if sh.isNull() or not sh.isValid() or not sh.Solids
    ]
    check(
        "valid_complete_physical_assembly",
        not invalid,
        f"{len(actors)} carrier components across four physical modules",
        invalid,
    )
    placements = build_detector_placements(cfg)
    active = {n: sh for n, sh in actors.items() if n.endswith("_ActivePlastic")}
    errors = []
    for p in placements:
        key = f"{p.tag}_ActivePlastic"
        if (
            key not in active
            or (active[key].CenterOfMass - detector_center(p)).Length > 1e-6
        ):
            errors.append(p.tag)
    check(
        "twelve_frozen_active_centers",
        len(active) == 12 and not errors,
        "All four azimuths retain the baseline angles, active-center radii and 20 mm discs",
        errors,
    )
    for sector, parts in f.sectors.items():
        bad = collisions(parts, tolerance=tolerance)
        check(
            f"{sector}_component_intersections",
            not bad,
            "Includes all three heads, nests, fasteners, pigtails and the rear journal",
            bad,
        )
    bad = []
    names = list(f.sectors)
    for i, sector in enumerate(names):
        for other in names[:i]:
            bad.extend(collisions(f.sectors[sector], f.sectors[other], tolerance))
    check(
        "four_loaded_modules_do_not_overlap",
        not bad,
        "Actual detailed modules replace neighboring reservation boxes",
        bad,
    )
    bad = collisions(flatten(f.retainers), actors, tolerance) + collisions(
        flatten(f.retainers), tolerance=tolerance
    )
    check(
        "four_retaining_bridges_and_fasteners_clear",
        not bad,
        "Checks the downstream retaining bridges and screw envelopes against every installed carrier and each other",
        bad,
    )
    bad = collisions(services, tolerance=tolerance) + collisions(
        services, {**actors, **flatten(f.retainers)}, tolerance
    )
    check(
        "twelve_installed_looms_and_four_bonds_clear",
        len(flatten(f.looms)) == 12 and len(f.grounds) == 4 and not bad,
        "True curved cable solids connect all twelve plugs to their deployment feedthroughs",
        bad,
    )
    parked_services = {
        **flatten(f.parked_plugs),
        **flatten(f.parked_looms),
        **{
            f"{sector}_ParkedGroundBond": fused(parts.values())
            for sector, parts in f.parked_grounds.items()
        },
    }
    bad = collisions(parked_services, tolerance=tolerance) + collisions(
        parked_services, {**actors, **flatten(f.retainers), **env}, tolerance
    )
    check(
        "all_parked_service_solids_clear",
        not bad,
        "All twelve parked plugs and looms and four parked bonds are checked against each other and the complete installation",
        bad,
    )
    bad = collisions(installed, env, tolerance)
    check(
        "installed_parts_clear_of_closed_chamber",
        not bad,
        "Includes stationary support, pins, working target, all service and vacuum interfaces",
        bad,
    )
    if side is not None:
        wall = f.base.chamber.physical["ProjectChamberBody"]
        weldment = Part.makeCompound(
            [f.fixed[f"LocalWallSupport_{sector}"] for sector in ANGLES]
        )
        bad = collisions(f.fixed, tolerance=tolerance)
        check(
            "local_support_parts_do_not_intersect",
            not bad,
            "Includes wall pads, welds, real bores, locating pins and mounting fasteners",
            bad,
        )
        problems = []
        for sector in ANGLES:
            body, pad = (
                f.fixed[f"LocalWallSupport_{sector}"],
                f.wall_pads[f"FactoryWeldedWallPad_{sector}"],
            )
            if (
                len(body.Solids) != 1
                or len(pad.Solids) != 1
                or contact_area(body, pad) < 1
                or contact_area(pad, wall) < 1
            ):
                problems.append(sector)
            for name, bolt in f.mount_bolts[sector].items():
                if contact_area(bolt, body) < 1:
                    problems.append(name)
        check(
            "four_bolted_supports_bear_on_welded_wall_pads",
            not problems,
            "Finite-area pad/brace/head contacts and modeled weld fillets define the mechanical connections",
            problems,
        )
    else:
        regions = fused(
            [
                sh
                for n, sh in f.fixed_regions.items()
                if n == "RingWeb" or n.startswith("Socket_")
            ]
        )
        weldment = f.fixed["AnnularSupportWeldment"]
        check(
            "fixed_collision_regions_match_weldment",
            regions.cut(weldment).Volume <= tolerance
            and weldment.cut(regions).Volume <= tolerance,
            "Collision decomposition covers the entire fixed annular support",
        )
        wall = f.base.chamber.physical["ProjectChamberBody"]
        check(
            "annular_frame_bears_on_permanent_walls",
            len(weldment.Solids) == 1 and contact_area(weldment, wall) > 1,
            "One connected annular support with permanent side and bottom feet",
        )
    contact_failures = []
    local_structural = (*f.base.structural, "GripRearJournal")
    for sector, parts in f.sectors.items():
        structural = [part_name(sector, n) for n in local_structural]
        graph = {n: set() for n in structural}
        for i, n in enumerate(structural):
            for other in structural[:i]:
                if contact_area(parts[n], parts[other]) > 1:
                    graph[n].add(other)
                    graph[other].add(n)
        reached = {f"{sector}_CarrierDockFoot"}
        frontier = list(reached)
        while frontier:
            for neighbor in graph[frontier.pop()] - reached:
                reached.add(neighbor)
                frontier.append(neighbor)
        contact_failures.extend(sorted(set(graph) - reached))
        dock = parts[f"{sector}_CarrierDockFoot"]
        bridge = f.retainers[sector][f"{sector}_RetainerBridge"]
        if (
            contact_area(dock, weldment) <= 1
            or contact_area(dock, bridge) <= 1
            or contact_area(bridge, weldment) <= 1
        ):
            contact_failures.append(f"{sector}_dock_retaining_contact")
        for prefix in f.base.heads:
            rear = parts[part_name(sector, prefix + "_RearMountingFace")]
            nest = parts[part_name(sector, prefix + "_DetectorNestCradle")]
            if contact_area(rear, nest) <= 1:
                contact_failures.append(part_name(sector, prefix))
    check(
        "all_four_finite_area_structural_paths",
        not contact_failures,
        "Rear head face to nest, cheeks/crossmembers to radial dock and fixed support; retaining bridges bear on both dock and socket",
        contact_failures,
    )
    parking_errors = []
    for sector in ANGLES:
        for suffix in ("ServiceParkingComb", "GroundParkingFixture"):
            name = f"{sector}_{suffix}"
            fixture = f.fixed[name]
            if len(fixture.Solids) != 1 or contact_area(fixture, wall) <= 1:
                parking_errors.append(name)
        for n, sh in f.parked_plugs[sector].items():
            if (
                contact_area(sh, f.fixed[f"{sector}_ServiceParkingComb"]) <= 1
                or overlap(sh, f.fixed[f"{sector}_ServiceParkingComb"]) > tolerance
            ):
                parking_errors.append(n)
        bridge = f.parked_grounds[sector][f"{sector}_GroundBridge"]
        if (
            bridge.distToShape(f.fixed[f"{sector}_GroundParkingFixture"])[0] > 1e-6
            or overlap(bridge, f.fixed[f"{sector}_GroundParkingFixture"]) > tolerance
        ):
            parking_errors.append(f"{sector}_ground_park")
    check(
        "four_permanent_wall_service_parking_stations",
        not parking_errors,
        "Plug collars have physical seats on permanent walls",
        parking_errors,
    )
    los = find_acceptance_obstructions(
        cfg,
        placements,
        {**installed, **env},
        {p.tag: {f"{p.tag}_ActivePlastic", "Target_TargetFoil"} for p in placements},
    )
    check(
        "twelve_complete_active_disc_acceptances",
        not los,
        "All twelve target-to-disc ruled volumes are checked against all four real loaded modules and services",
        los,
    )
    bad = []
    for sector, parts in f.sectors.items():
        for prefix, sweep in f.base.removal.items():
            exclusions = set(f.base.head_parts[prefix]) | {
                n
                for n in f.base.actor
                if n.startswith(prefix + "_M3ClampScrew")
                or n in {prefix + "_RemovableClampBridge", prefix + "_PassiveCoax"}
            }
            obstacles = {
                n: sh
                for n, sh in parts.items()
                if n not in {part_name(sector, x) for x in exclusions}
            }
            bad.extend(
                collisions(
                    {part_name(sector, prefix): moved(sweep, angle=ANGLES[sector])},
                    obstacles,
                    tolerance,
                )
            )
    check(
        "twelve_individual_head_bench_withdrawals",
        not bad,
        "Each detector has its modeled 12 mm rearward withdrawal with its own clamp and pigtail released",
        bad,
    )
    bad = []
    for pose in f.base.target.motion_samples:
        bad.extend(collisions(pose.physical, {**installed, **f.fixed}, tolerance))
    check(
        "target_motion_samples_clear_loaded_supports",
        not bad,
        "Configured target motion samples tested against the full installed detector and service assembly",
        bad,
    )
    closure = f.base.chamber.keepouts["MaintenanceAccessBlindRemovalEnvelope"]
    bad = collisions({"ClosureLift": closure}, {**installed, **f.fixed}, tolerance)
    check(
        "closure_has_no_detector_support_load_or_obstruction",
        not bad,
        "Permanent support and services remain clear of the removed lid lift",
        bad,
    )
    vacuum = f.base.chamber.vacuum_control_volume
    check(
        "closed_valid_vacuum_control_volume",
        vacuum.isValid() and vacuum.isClosed() and len(vacuum.Solids) == 1,
        "Selected chamber and interfaces define one closed control-volume solid; pressure and leak qualification remain separate",
    )
    beam_obstacles = {
        **installed,
        **f.fixed,
        **f.base.target.stationary,
        **{n: sh for n, sh in f.base.target.work.physical.items() if n != "TargetFoil"},
    }
    bad = collisions(
        {"BeamStayClear": f.base.chamber.keepouts["BeamStayClear"]},
        beam_obstacles,
        tolerance,
    )
    check(
        "beam_stay_clear_of_complete_installation",
        not bad,
        "The configured beam cylinder clears all physical components except the intended target foil",
        bad,
    )
    access = cfg.compact_one.deployment.maintenance_access
    port = access.selected
    chamber = f.base.chamber.candidate
    flange_r = port.flange_outer_diameter_mm / 2
    edge_margin = min(
        (chamber.inner_size_y_mm if side is not None else chamber.inner_size_x_mm) / 2
        + chamber.wall_thickness_mm
        - abs(port.center_y_mm if side is not None else port.center_x_mm)
        - flange_r,
        port.center_z_mm - flange_r - (chamber.center_z_mm - chamber.length_mm / 2),
        chamber.center_z_mm + chamber.length_mm / 2 - port.center_z_mm - flange_r,
    )
    check(
        (
            "maintenance_flange_fits_side_face"
            if side is not None
            else "maintenance_flange_fits_top_face"
        ),
        edge_margin >= access.flange_edge_margin_mm,
        f"Minimum flange-to-chamber edge margin {edge_margin:.3f} mm",
    )
    if side is not None:
        flange = f.base.chamber.purchased_interfaces["MaintenanceAccessFixedICFFlange"]
        service_margin = min(
            flange.distToShape(sh)[0]
            for p in f.base.ports.values()
            for sh in p.purchased_interfaces.values()
        )
        check(
            "side_access_clear_of_rotary_and_signal_ports",
            service_margin >= access.service_port_clearance_mm,
            f"Minimum actual 3D clearance to service interfaces {service_margin:.3f} mm",
        )
    else:
        service_margin = min(
            math.hypot(
                p.center_x_mm - port.center_x_mm, p.center_z_mm - port.center_z_mm
            )
            - flange_r
            - (
                cfg.compact_one.services.signal_interface.module_outer_diameter_mm / 2
                if p.role == "signal"
                else (
                    35.0
                    if cfg.compact_one.deployment.target_feedthrough_standard == "ICF70"
                    else p.collar_outer_diameter_mm / 2
                )
            )
            for p in cfg.compact_one.deployment.service_ports
        )
        check(
            "maintenance_flange_clears_service_ports",
            service_margin >= access.service_port_clearance_mm,
            f"Minimum projected clearance to target/signal interfaces {service_margin:.3f} mm",
        )

    basic_ok = not any(c["status"] == "fail" for c in checks)
    motion_env = chamber_environment(f)
    if side is not None:
        from .side_installation import (
            side_void_candidates,
            validate_support_installation,
        )

        candidates = side_void_candidates(f, s)
    else:
        candidates = study_void_candidates(f.base, s)
    voids, void_records = verify_void_regions(candidates, motion_env, tolerance)
    support_installation, support_installed = [], None
    if side is not None:
        if basic_ok:
            support_installation, support_installed = validate_support_installation(
                f, s, side, check, voids
            )
        check(
            "all_four_support_installation_paths_certified",
            bool(support_installed),
            "All local support bodies and locating pins enter through the side opening and seat on permanent wall pads",
        )
        basic_ok = basic_ok and bool(support_installed)
    removed = set()
    all_transport = True
    if basic_ok:
        for sector in d["removal_order"]:
            obstacles = {**motion_env}
            for other in ANGLES:
                if other != sector and other not in removed:
                    obstacles.update(f.sectors[other])
                    obstacles.update(f.retainers[other])
                    obstacles.update(f.plugs[other])
                    obstacles.update(f.grounds[other])
                    obstacles.update(f.looms[other])
                else:
                    obstacles.update(f.parked_plugs[other])
                    obstacles.update(f.parked_grounds[other])
                    obstacles.update(f.parked_looms[other])
            # [EN] Preparation certificates are separate from the loaded-module path, so a transport result cannot silently certify connector handling or retainer-tool internals. / [CN] 准备动作与负载模块路径分开证明，避免把运输结果误称为连接器操作或锁紧工具内部机构的认证。
            pin_failures, mates = [], set()
            for pin, sweep in f.base.pin_sweeps.items():
                global_pin = f"{sector}_{pin}"
                moved_sweep = moved(sweep, angle=ANGLES[sector])
                for name, sh in f.sectors[sector].items():
                    volume = overlap(moved_sweep, sh)
                    if volume > tolerance:
                        pin_failures.append(
                            {"pin": global_pin, "part": name, "volume_mm3": volume}
                        )
                    else:
                        mates.add((name, global_pin))
            check(
                f"{sector}_continuous_pin_disengagement",
                not pin_failures,
                f"Exact relative cylinder sweeps cover the whole {s.radial_release_mm:.1f} mm inward staging travel",
                pin_failures,
            )
            combined = {**f.sectors[sector], **f.tools[sector]}
            journal = f.sectors[sector][f"{sector}_GripRearJournal"]
            tool = fused(f.tools[sector].values())
            check(
                f"{sector}_capture_has_load_contact",
                overlap(journal, tool) <= tolerance
                and journal.distToShape(tool)[0] < 1e-6,
                "Circular rear journal contacts the lower capture jaw",
            )
            tool_clear = collisions(
                {
                    n: sh
                    for n, sh in f.sectors[sector].items()
                    if n != f"{sector}_GripRearJournal"
                },
                f.tools[sector],
                tolerance,
            )
            # [EN] Z separation holds for every rotation about Z; the only overlapping Z range is the invariant circular journal mating surface. / [CN] 绕 Z 转动始终保持 Z 向分离；唯一相同 Z 范围的零件是形状不变的圆柱轴颈接触面。
            z_clear = min(
                sh.optimalBoundingBox(False, False).ZMin
                for sh in f.tools[sector].values()
            ) - max(
                sh.optimalBoundingBox(False, False).ZMax
                for n, sh in f.sectors[sector].items()
                if n != f"{sector}_GripRearJournal"
            )
            check(
                f"{sector}_capture_relative_turn_clear",
                not tool_clear and z_clear > s.continuous_clearance_mm,
                f"Rear tool is separated from the complete module by {z_clear:.3f} mm in Z through the full turn",
                tool_clear,
            )
            capture_obstacles = {
                **obstacles,
                **f.sectors[sector],
                **f.retainers[sector],
            }
            lower_name = f"{sector}_CaptureLowerJaw"
            upper_name = f"{sector}_CaptureUpperJaw"
            jaw_delta = V(*s.grip_jaw_open_offset_mm)
            open_tool = {
                **f.tools[sector],
                lower_name: moved(f.tools[sector][lower_name], jaw_delta),
            }
            if side is not None:
                raise_by = V(0, side["capture_approach_raise_mm"], 0)
                insertion = Phase(
                    f"{sector}_capture_tool_enter_side_window",
                    {
                        n: moved(
                            sh,
                            raise_by + V(side["capture_insertion_offset_x_mm"], 0, 0),
                        )
                        for n, sh in open_tool.items()
                    },
                    capture_obstacles,
                    delta=V(-side["capture_insertion_offset_x_mm"], 0, 0),
                )
                approach = Phase(
                    f"{sector}_capture_tool_lower_onto_journal",
                    insertion.at(1),
                    capture_obstacles,
                    delta=-raise_by,
                )
                capture_phases = [insertion, approach]
            else:
                insertion = Phase(
                    f"{sector}_capture_tool_insertion",
                    {
                        n: moved(sh, V(0, d["handling_rod_length_mm"], 0))
                        for n, sh in open_tool.items()
                    },
                    capture_obstacles,
                    delta=V(0, -d["handling_rod_length_mm"], 0),
                )
                capture_phases = [insertion]
            align = Phase(
                f"{sector}_capture_jaw_alignment",
                {lower_name: open_tool[lower_name]},
                {
                    **capture_obstacles,
                    **{n: sh for n, sh in f.tools[sector].items() if n != lower_name},
                },
                delta=V(-jaw_delta.x, 0, 0),
            )
            journal_name = f"{sector}_GripRearJournal"
            expected_journal = Part.makeCylinder(
                s.grip_pin_radius_mm,
                d["journal_end_z_mm"]
                - (
                    s.grip_center_mm[2]
                    + s.grip_pin_length_mm / 2
                    + s.grip_fork_plate_depth_mm
                ),
                vector(
                    sector,
                    s.grip_center_mm[0],
                    0,
                    s.grip_center_mm[2]
                    + s.grip_pin_length_mm / 2
                    + s.grip_fork_plate_depth_mm,
                ),
            )
            journal_certificate = (
                journal.cut(expected_journal).Volume <= tolerance
                and expected_journal.cut(journal).Volume <= tolerance
                and s.grip_bearing_clearance_mm > 0
            )
            check(
                f"{sector}_capture_jaw_closing_analytic_mate",
                journal_certificate,
                "The lower half-annulus approaches a verified circular journal from below; radial bearing clearance equals its upward center offset",
            )
            jaw_mate = {(lower_name, journal_name)} if journal_certificate else set()
            close = Phase(
                f"{sector}_capture_jaw_closing",
                align.at(1),
                align.obstacles,
                delta=V(0, -jaw_delta.y, 0),
                excluded_pairs=frozenset({(lower_name, journal_name)}),
                contacts=frozenset({(lower_name, upper_name)}),
            )
            prep_pass = True
            for phase in (*capture_phases, align, close):
                print(f"CERTIFY {phase.name}", file=sys.stderr, flush=True)
                result = certify_phase(phase, s, jaw_mate, voids)
                phases.append(result)
                check(
                    phase.name,
                    result["status"] == "pass",
                    f"{result['certified_intervals']} continuous capture-tool intervals",
                    result["failures"],
                )
                if result["status"] != "pass":
                    prep_pass = False
                    break
            retainer_obstacles = {**obstacles, **combined}
            retainer_mates, retainer_errors = set(), []
            for index, tt in enumerate(d["retainer_screw_t_mm"]):
                zz = s.dock_z_max_mm + d["retainer_depth_mm"]
                sweep = Part.makeCylinder(
                    d["retainer_screw_radius_mm"],
                    d["retainer_screw_length_mm"] + d["retainer_release_mm"],
                    vector(
                        sector,
                        d["retainer_screw_r_mm"],
                        tt,
                        zz - d["retainer_screw_length_mm"],
                    ),
                )
                pair = (
                    f"{sector}_RetainerScrew_{index}",
                    (
                        f"LocalWallSupport_{sector}"
                        if side is not None
                        else f"Socket_{sector}"
                    ),
                )
                volume = overlap(sweep, obstacles[pair[1]])
                if volume > tolerance:
                    retainer_errors.append({"pair": pair, "volume_mm3": volume})
                else:
                    retainer_mates.add(pair)
            if side is not None:
                bridge_name = f"{sector}_RetainerBridge"
                support_name = f"LocalWallSupport_{sector}"
                bridge_shape = f.retainers[sector][bridge_name]
                b = bridge_shape.optimalBoundingBox(False, False)
                swept_bridge = Part.makeBox(
                    b.XLength,
                    b.YLength,
                    b.ZLength + d["retainer_release_mm"],
                    V(b.XMin, b.YMin, b.ZMin),
                )
                # [EN] A complete rectangular translation envelope proves separation beyond the finite initial bearing face, even when the remote mounting flange extends behind that face. / [CN] 完整矩形平移包络证明初始有限承压面之后的分离，即使远处安装法兰延伸到该面后方也适用。
                valid_bridge_sweep = (
                    overlap(swept_bridge, obstacles[support_name]) <= tolerance
                    and contact_area(bridge_shape, obstacles[support_name]) > 1
                )
                check(
                    f"{sector}_retainer_initial_bearing_sweep",
                    valid_bridge_sweep,
                    "The complete bridge translation prism clears the local support after separating from its bearing face",
                )
                if valid_bridge_sweep:
                    retainer_mates.add((bridge_name, support_name))
                else:
                    retainer_errors.append(
                        {"kind": "unproved_bridge_bearing_sweep", "sector": sector}
                    )
            retainer = Phase(
                f"{sector}_retaining_bridge_disengagement",
                f.retainers[sector],
                retainer_obstacles,
                delta=V(0, 0, d["retainer_release_mm"]),
                excluded_pairs=frozenset(retainer_mates),
                contacts=frozenset(
                    {
                        (f"{sector}_RetainerBridge", f"{sector}_CarrierDockFoot"),
                        (
                            f"{sector}_RetainerBridge",
                            (
                                f"LocalWallSupport_{sector}"
                                if side is not None
                                else f"Socket_{sector}"
                            ),
                        ),
                    }
                ),
            )
            retainer_out = Phase(
                f"{sector}_retaining_bridge_outward_clearance",
                retainer.at(1),
                retainer_obstacles,
                delta=vector(sector, d["retainer_radial_clearance_mm"], 0),
            )
            retainer_side = Phase(
                f"{sector}_retaining_bridge_rod_clearance",
                retainer_out.at(1),
                retainer_obstacles,
                delta=vector(sector, 0, d["retainer_tangential_clearance_mm"]),
            )
            retainer_back = Phase(
                f"{sector}_retaining_bridge_downstream_transfer",
                retainer_side.at(1),
                retainer_obstacles,
                delta=V(0, 0, d["retainer_downstream_transfer_mm"]),
            )
            retainer_phases = [retainer, retainer_out, retainer_side, retainer_back]
            free_retainer = retainer_back.at(1)
            offset = vector(
                sector,
                sum(d["retainer_r_mm"]) / 2 + d["retainer_radial_clearance_mm"],
                0,
            )
            offset = offset.y if side is not None else offset.x
            if abs(offset) > 1e-6:
                retainer_center = Phase(
                    f"{sector}_retaining_bridge_centering",
                    free_retainer,
                    retainer_obstacles,
                    delta=V(0, -offset, 0) if side is not None else V(-offset, 0, 0),
                )
                retainer_phases.append(retainer_center)
                free_retainer = retainer_center.at(1)
            retainer_phases.append(
                Phase(
                    (
                        f"{sector}_retaining_bridge_side_exit"
                        if side is not None
                        else f"{sector}_retaining_bridge_lift"
                    ),
                    free_retainer,
                    retainer_obstacles,
                    delta=(
                        V(side["retainer_side_extraction_mm"], 0, 0)
                        if side is not None
                        else V(0, d["retainer_lift_mm"], 0)
                    ),
                )
            )
            retainer_pass = not retainer_errors
            for phase in retainer_phases:
                print(f"CERTIFY {phase.name}", file=sys.stderr, flush=True)
                result = certify_phase(phase, s, retainer_mates, voids)
                phases.append(result)
                check(
                    phase.name,
                    result["status"] == "pass" and not retainer_errors,
                    "Continuous retaining-bridge and captive-fastener solid motion; actuating/holding tool qualification is separate",
                    result["failures"] + retainer_errors,
                )
                if result["status"] != "pass":
                    retainer_pass = False
                    break
            release = Phase(
                f"{sector}_radial_release",
                combined,
                obstacles,
                delta=vector(sector, -s.radial_release_mm, 0),
                excluded_pairs=frozenset(mates),
                contacts=frozenset(
                    (
                        n,
                        (
                            f"LocalWallSupport_{sector}"
                            if side is not None
                            else f"Socket_{sector}"
                        ),
                    )
                    for n in f.sectors[sector]
                ),
            )
            transfer = Phase(
                f"{sector}_downstream_transfer",
                release.at(1),
                obstacles,
                delta=V(0, 0, d["downstream_translation_mm"]),
            )
            pivot = f.grips[sector] + vector(
                sector, -s.radial_release_mm, 0, d["downstream_translation_mm"]
            )
            turned = transfer.at(1)
            sector_phases = [release, transfer]
            if d["turn_deg"][sector]:
                turn = Phase(
                    f"{sector}_controlled_turn",
                    {n: sh for n, sh in turned.items() if n in f.sectors[sector]},
                    obstacles,
                    pivot=pivot,
                    angle=d["turn_deg"][sector],
                )
                sector_phases.append(turn)
                turned.update(turn.at(1))
            center_offset = pivot.y if side is not None else pivot.x
            if abs(center_offset) > 1e-6:
                center = Phase(
                    f"{sector}_center_under_port",
                    turned,
                    obstacles,
                    delta=(
                        V(0, -center_offset, 0)
                        if side is not None
                        else V(-center_offset, 0, 0)
                    ),
                )
                sector_phases.append(center)
                turned = center.at(1)
            lift = Phase(
                (
                    f"{sector}_extract_through_side_port"
                    if side is not None
                    else f"{sector}_lift_through_port"
                ),
                turned,
                obstacles,
                delta=(
                    V(side["side_extraction_mm"], 0, 0)
                    if side is not None
                    else V(0, d["lift_mm"], 0)
                ),
            )
            sector_phases.append(lift)
            f.poses[sector] = {phase.name: phase.at(1) for phase in sector_phases}
            passed = (
                prep_pass
                and retainer_pass
                and not pin_failures
                and not tool_clear
                and z_clear > s.continuous_clearance_mm
            )
            for phase in sector_phases:
                print(f"CERTIFY {phase.name}", file=sys.stderr, flush=True)
                result = certify_phase(phase, s, mates, voids)
                phases.append(result)
                check(
                    phase.name,
                    result["status"] == "pass",
                    f"{result['certified_intervals']} certified continuous intervals",
                    result["failures"],
                )
                if result["status"] != "pass":
                    passed = False
                    break
            access = cfg.compact_one.deployment.maintenance_access.selected
            bounds = {
                n: sh.optimalBoundingBox(False, False) for n, sh in lift.at(1).items()
            }
            radius = max(
                math.hypot(
                    x
                    - (access.center_y_mm if side is not None else access.center_x_mm),
                    z - access.center_z_mm,
                )
                for n in f.sectors[sector]
                for x in (
                    (bounds[n].YMin, bounds[n].YMax)
                    if side is not None
                    else (bounds[n].XMin, bounds[n].XMax)
                )
                for z in (bounds[n].ZMin, bounds[n].ZMax)
            )
            margins[sector] = access.clear_bore_diameter_mm / 2 - radius
            rim = f.base.chamber.purchased_interfaces[
                "MaintenanceAccessBlindFlange"
            ].optimalBoundingBox(False, False)
            rim = rim.XMax if side is not None else rim.YMax
            bottom = min(
                bounds[n].XMin if side is not None else bounds[n].YMin
                for n in f.sectors[sector]
            )
            headrooms[sector] = (
                max(b.XMax if side is not None else b.YMax for b in bounds.values())
                - rim
            )
            check(
                f"{sector}_fully_extracted_with_port_allowance",
                margins[sector]
                >= cfg.compact_one.deployment.maintenance_access.passage_diametral_clearance_mm
                / 2
                and bottom > rim + 5,
                f"Module radial allowance {margins[sector]:.3f} mm; lowest normal coordinate clears the closed cover by {bottom-rim:.3f} mm",
            )
            all_transport = all_transport and passed
            if not passed:
                break
            removed.add(sector)
    complete_transport = basic_ok and all_transport and len(removed) == 4
    check(
        "all_four_loaded_modules_transport_certified",
        complete_transport,
        "Configured service sequence with other actual modules present until their removal",
    )
    for name, detail in [
        (
            "purchased_detector_optical_and_connector_evidence",
            "SiPM, reflector, optical stack, PCB, connectors and coax require supplier models and vacuum material qualification",
        ),
        (
            "beam_signal_and_icf305_interface_evidence",
            "Deployment beam mating chains, signal interfaces, fixed/blank ICF305 drawings and metal-seal leak-rate applicability remain unresolved",
        ),
        (
            "chamber_pressure_integrity_evidence",
            "The modeled chamber requires external-pressure/buckling, joint, weld and leak-test evidence before fabrication",
        ),
        (
            "structural_preload_and_tolerance_evidence",
            "Retaining bridges, threads, journals, locating pins and support weldment need strength, stiffness, preload and manufacturing tolerances",
        ),
        (
            "service_preparation_and_capture_mechanism_evidence",
            "Retainer actuation, plug and ground disconnection, captured-part handling, and capture-head guides/latch require a complete tool/service qualification; transport certification assumes these have been released",
        ),
        (
            "flexible_loom_and_parking_retention_evidence",
            "Installed and parked coax solids are modeled; continuous flexible cable deformation, strain relief and retaining clips require prototype qualification",
        ),
        (
            "human_handling_site_and_overhead_evidence",
            (
                "The modeled horizontal rod and driver engagement envelopes do not establish operator reach, holding forces, full mounting-tool insertion or site clearance beside the chamber"
                if side is not None
                else "The modeled vertical rod does not establish operator reach, handling forces or site clearance above the original lid"
            ),
        ),
    ]:
        check(name, False, detail, evidence=True)
    summary = {
        f"{status}_count": sum(c["status"] == status for c in checks)
        for status in ("pass", "warning", "fail")
    }
    acceptance = _detector_acceptance_metrics(cfg, placements)
    report = dict(
        schema_version=1,
        status="fail" if summary["fail_count"] else "pass",
        strict=bool(strict),
        validation_mode=(
            "side_access_local_support_deployment"
            if side is not None
            else "four_boxed_sector_deployment"
        ),
        scope="four_detailed_modules_twelve_detectors_complete_installed_assembly",
        summary=summary,
        checks=checks,
        motion_phases=phases,
        removal_order=d["removal_order"],
        all_four_loaded_module_transport_certified=complete_transport,
        complete_modeled_extraction_certified=False,
        module_port_radial_allowance_mm=margins,
        **(
            {
                "required_tool_reach_beyond_side_closure_mm": headrooms,
                "support_installation_phases": support_installation,
                "all_four_support_installation_certified": bool(support_installed),
                "side_access_configuration": side,
            }
            if side is not None
            else {"required_tool_headroom_above_closure_mm": headrooms}
        ),
        transport_prerequisites=[
            "beam off",
            "target parked",
            "blank flange and copper gasket removed",
            "selected module plugs and ground disconnected and parked",
            "selected downstream retaining bridge and captive fasteners removed",
            "rear journal captured by qualified handling tool",
            "preceding sectors removed in the specified order",
        ],
        verified_free_regions=void_records,
        boxed_configuration=asdict(s),
        deployment_configuration=d,
        resolved_configuration=yaml.safe_load(dump_config_yaml(cfg)),
        engineering_metrics={
            "detector_head_stack": detector_stack_metrics(cfg),
            "detector_acceptance": acceptance,
            "coincidence_geometry": _coincidence_metrics(cfg, placements, acceptance),
            "detailed_sectors": len(f.sectors),
            "physical_signal_looms": len(flatten(f.looms)),
            "maintenance_access": {
                "flange_edge_margin_mm": edge_margin,
                "service_port_clearance_mm": service_margin,
                "module_radial_allowance_mm": margins,
                (
                    "tool_reach_beyond_side_cover_mm"
                    if side is not None
                    else "tool_headroom_above_closed_lid_mm"
                ): headrooms,
            },
        },
        software={"FreeCAD": ".".join(App.Version()[:3])},
    )
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2) + "\n")
    return report
