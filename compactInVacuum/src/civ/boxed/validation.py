from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys

import FreeCAD as App
import Part

from ..config import dump_config_yaml
from ..layout import build_detector_placements, detector_center, scaled
from ..validation_compact import find_acceptance_obstructions
from .geometry import V, moved, fused
from .motion import (
    overlap,
    bbox_distance,
    main_motion_phases,
    preparation_phases,
    parked_environment,
    environment,
)
from .motion import certify_phase
from .motion import study_void_candidates, verify_void_regions
from .motion import plug_parking_delta, ground_parking_delta
import yaml


def contact_area(a, b):
    # [EN] OCC solid common discards zero-volume face contacts; intersect the coincident planar faces to measure real bearing area. / [CN] OCC 实体求交会丢弃零体积面接触，因此对共面平面直接求交来测量真实承压面积。
    if bbox_distance(a.BoundBox, b.BoundBox) > 1e-6:
        return 0.0
    area = 0.0
    for fa in a.Faces:
        if not isinstance(fa.Surface, Part.Plane):
            continue
        for fb in b.Faces:
            if (
                not isinstance(fb.Surface, Part.Plane)
                or bbox_distance(fa.BoundBox, fb.BoundBox) > 1e-6
            ):
                continue
            if abs(fa.normalAt(0, 0).dot(fb.normalAt(0, 0))) < 1 - 1e-7:
                continue
            area += fa.common(fb).Area
    return area


def validate_study(cfg, s, g, strict=False, output_path=None):
    checks = []
    tolerance = s.collision_volume_tolerance_mm3

    def check(name, passed, detail, failures=None, warning=False):
        status = "pass" if passed else ("warning" if warning and not strict else "fail")
        checks.append(
            {
                "name": name,
                "status": status,
                "strict_only": warning,
                "detail": detail,
                "failures": failures or [],
            }
        )
        print(f"{status.upper()} {name}", file=sys.stderr, flush=True)

    invalid = [
        name
        for name, shape in {
            **g.actor,
            **g.fixed,
            **g.tool,
            **g.plugs,
            **g.parked_looms,
        }.items()
        if shape.isNull() or not shape.isValid() or not shape.Solids
    ]
    check(
        "valid_physical_shapes",
        not invalid,
        f"{len(g.actor)} moving module components",
        invalid,
    )
    disconnected = [name for name in g.structural if len(g.actor[name].Solids) != 1]
    check(
        "individual_carrier_parts_connected",
        not disconnected,
        "Every cheek, brace, cradle and grip part is one solid",
        disconnected,
    )
    centers = []
    for p in build_detector_placements(cfg):
        if p.sector_name == s.sector:
            error = (
                g.actor[f"{p.tag}_ActivePlastic"].CenterOfMass - detector_center(p)
            ).Length
            if error > 1e-6:
                centers.append({"channel": p.tag, "center_error_mm": error})
    check(
        "unchanged_active_centers",
        not centers,
        "Three active centers and detector-axis placements inherit the baseline",
        centers,
    )

    collisions = []
    items = list(g.actor.items())
    for i, (name, a) in enumerate(items):
        for other, b in items[:i]:
            if bbox_distance(a.BoundBox, b.BoundBox) > 1e-7:
                continue
            volume = overlap(a, b)
            if volume > tolerance:
                collisions.append({"a": name, "b": other, "volume_mm3": volume})
    check(
        "no_unintended_module_intersections",
        not collisions,
        "Includes pigtails, connector shoulders and all modeled fasteners",
        collisions,
    )

    graph = {name: set() for name in g.structural}
    for i, name in enumerate(g.structural):
        for other in g.structural[:i]:
            a, b = g.actor[name], g.actor[other]
            if bbox_distance(a.BoundBox, b.BoundBox) > 1e-6:
                continue
            if contact_area(a, b) > 1.0:
                graph[name].add(other)
                graph[other].add(name)
    reached = {"CarrierDockFoot"}
    front = ["CarrierDockFoot"]
    while front:
        current = front.pop()
        for neighbor in graph[current] - reached:
            reached.add(neighbor)
            front.append(neighbor)
    missing = sorted(set(graph) - reached)
    check(
        "finite_area_carrier_load_path",
        not missing,
        "Structural parts connect through finite contact faces to the docking foot",
        missing,
    )
    head_contacts = []
    for prefix in g.heads:
        rear = g.actor[f"{prefix}_RearMountingFace"]
        nest = g.actor[f"{prefix}_DetectorNestCradle"]
        area = contact_area(rear, nest)
        if area < 1.0:
            head_contacts.append({"channel": prefix, "contact_area_mm2": area})
    check(
        "detector_rear_face_contacts_nest",
        not head_contacts,
        "Detector loading enters through the rear mounting flange",
        head_contacts,
    )
    wall = g.chamber.physical["ProjectChamberBody"]
    fixed = g.fixed["AnnularSupportWeldment"]
    regions = fused(
        [
            sh
            for n, sh in g.fixed_regions.items()
            if n == "RingWeb" or n.startswith("Socket_")
        ]
    )
    check(
        "collision_regions_match_fixed_weldment",
        regions.cut(fixed).Volume <= tolerance
        and fixed.cut(regions).Volume <= tolerance,
        "Decomposed collision regions represent the complete fixed weldment",
    )
    check(
        "ring_on_permanent_chamber_walls",
        fixed.isValid() and len(fixed.Solids) == 1 and contact_area(fixed, wall) > 1,
        "Ring plus side/bottom feet form one fixed weldment",
    )
    dock = g.actor["CarrierDockFoot"]
    check(
        "docking_face_has_structural_contact",
        contact_area(dock, fixed) > 1 and overlap(dock, fixed) <= tolerance,
        "Plane-pin-slot interface bears on a permanent socket",
    )
    parking_failures = []
    for name in ("ServiceParkingComb", "GroundParkingFixture"):
        fixture = g.fixed[name]
        if (
            not fixture.isValid()
            or len(fixture.Solids) != 1
            or contact_area(fixture, wall) < 1
        ):
            parking_failures.append({"fixture": name, "problem": "wall attachment"})
    for name, shape in g.plugs.items():
        placed = moved(shape, plug_parking_delta(s))
        if (
            contact_area(placed, g.fixed["ServiceParkingComb"]) < 1
            or overlap(placed, g.fixed["ServiceParkingComb"]) > tolerance
        ):
            parking_failures.append({"plug": name, "problem": "collar seating"})
    parked_bond = moved(g.ground["GroundBridge"], ground_parking_delta(s))
    if (
        parked_bond.distToShape(g.fixed["GroundParkingFixture"])[0] > 1e-6
        or overlap(parked_bond, g.fixed["GroundParkingFixture"]) > tolerance
    ):
        parking_failures.append(
            {"fixture": "GroundParkingFixture", "problem": "ground support"}
        )
    check(
        "parked_services_have_physical_support",
        not parking_failures,
        "Plug collars seat on a wall-mounted comb; the ground jumper rests on wall-mounted pegs",
        parking_failures,
    )
    parking_sweep_failures = []
    for name, z in zip(g.plugs, s.connector_z_mm):
        upper = s.half_width + s.connector_withdrawal_mm
        sweeps = [
            Part.makeCylinder(
                s.connector_radius_mm,
                upper - s.connector_parking_y_mm + s.connector_plug_length_mm,
                V(s.connector_parking_x_mm, s.connector_parking_y_mm, z),
                V(0, 1, 0),
            ),
            Part.makeCylinder(
                s.connector_plug_collar_radius_mm,
                upper - s.connector_parking_y_mm + s.connector_plug_collar_depth_mm,
                V(
                    s.connector_parking_x_mm,
                    s.connector_parking_y_mm
                    + s.connector_plug_length_mm
                    - s.connector_plug_collar_depth_mm,
                    z,
                ),
                V(0, 1, 0),
            ),
        ]
        for sweep in sweeps:
            volume = overlap(sweep, g.fixed["ServiceParkingComb"])
            if volume > tolerance:
                parking_sweep_failures.append({"plug": name, "volume_mm3": volume})
    check(
        "parking_plug_exact_seating_sweeps",
        not parking_sweep_failures,
        "Coaxial swept cylinders cover the full downward insertion into the parking seats",
        parking_sweep_failures,
    )

    neighbor_failures = []
    for name, shape in g.other_heads.items():
        sector = name.split("_", 1)[0]
        box = g.neighbors[f"{sector}_ReservedModuleEnvelope"]
        if (
            bbox_distance(shape.BoundBox, box.BoundBox) > 0
            or shape.cut(box).Volume > tolerance
        ):
            neighbor_failures.append(name)
    check(
        "neighbor_reservations_contain_actual_heads",
        not neighbor_failures,
        "Other three sectors remain conservative envelopes; their actual head solids fit inside",
        neighbor_failures,
    )
    envelope = Part.makeBox(
        s.carrier_r_max_mm - s.neighbor_r_min_mm,
        2 * s.half_width,
        s.carrier_z_max_mm - s.carrier_z_min_mm,
        V(s.neighbor_r_min_mm, -s.half_width, s.carrier_z_min_mm),
    )
    outside = [
        {"component": name, "outside_volume_mm3": float(shape.cut(envelope).Volume)}
        for name, shape in g.actor.items()
        if shape.cut(envelope).Volume > tolerance
    ]
    check(
        "complete_module_transport_envelope",
        not outside,
        "The moving envelope includes connectors, cables, grip hardware and fasteners",
        outside,
    )

    installed_obstacles = {**environment(g, s), **g.draw_screw}
    loom_workspaces = {
        n: sh
        for n, sh in parked_environment(g, s).items()
        if n.startswith("FixedLoomWorkspace")
    }
    loom_conflicts = []
    for name, workspace in loom_workspaces.items():
        for obstacle_name, shape in {
            **installed_obstacles,
            **g.actor,
            **g.tool,
        }.items():
            volume = overlap(workspace, shape)
            if volume > tolerance:
                loom_conflicts.append(
                    {"workspace": name, "obstacle": obstacle_name, "volume_mm3": volume}
                )
    check(
        "flexible_loom_workspaces_clear",
        not loom_conflicts,
        "Variable first-leg corridors clear stationary hardware; the downstream bends and tails are modeled separately",
        loom_conflicts,
    )
    initial = []
    for name, shape in g.actor.items():
        for other, obstacle in installed_obstacles.items():
            volume = overlap(shape, obstacle)
            if volume > tolerance:
                initial.append({"actor": name, "obstacle": other, "volume_mm3": volume})
    check(
        "installed_module_clear_of_environment",
        not initial,
        "Checks ring, pins, three neighboring envelopes, chamber and parked target",
        initial,
    )
    los_obstacles = {
        **g.actor,
        **g.fixed,
        **g.other_heads,
        **g.chamber.physical,
        **g.parked_looms,
        **g.target.stationary,
        **{f"TargetWork_{n}": sh for n, sh in g.target.work.physical.items()},
    }
    excludes = {
        p.tag: {f"{p.tag}_ActivePlastic", "TargetWork_TargetFoil"}
        for p in build_detector_placements(cfg)
    }
    los = find_acceptance_obstructions(
        cfg, build_detector_placements(cfg), los_obstacles, excludes
    )
    check(
        "all_twelve_full_disc_acceptances_clear",
        not los,
        "Actual target-to-active-disc ruled volumes; support and all pigtails included",
        los,
    )
    withdrawal = []
    for prefix, sweep in g.removal.items():
        for name, shape in g.actor.items():
            if (
                name in g.head_parts[prefix]
                or name.startswith(prefix + "_M3ClampScrew")
                or name == prefix + "_RemovableClampBridge"
                or name == prefix + "_PassiveCoax"
            ):
                continue
            volume = overlap(sweep, shape)
            if volume > tolerance:
                withdrawal.append(
                    {"channel": prefix, "obstacle": name, "volume_mm3": volume}
                )
    check(
        "individual_head_bench_withdrawal",
        not withdrawal,
        "Selected clamp and pigtail are released before the modeled 12 mm head withdrawal",
        withdrawal,
    )
    bend_radii = [
        edge.Curve.Radius
        for wire in g.cable_paths.values()
        for edge in wire.Edges
        if hasattr(edge.Curve, "Radius")
    ]
    check(
        "pigtail_bend_radius_geometry",
        bool(bend_radii) and min(bend_radii) >= s.cable_bend_radius_mm - 1e-5,
        f"Minimum modeled bend radius {min(bend_radii,default=0):.3f} mm; supplier qualification remains open",
    )

    # [EN] Exact relative sweeps certify the sliding pins before those two mating pairs are omitted from the general positive-clearance interval test. / [CN] 先用精确相对扫掠证明滑动销，再从一般正间隙区间检查中排除这两个接触副。
    pin_failures = []
    for pin, sweep in g.pin_sweeps.items():
        for name, shape in g.actor.items():
            volume = overlap(sweep, shape)
            if volume > tolerance:
                pin_failures.append(
                    {"pin": pin, "obstacle": name, "volume_mm3": volume}
                )
    check(
        "exact_pin_release_sweep",
        not pin_failures,
        "Relative pin cylinders include every point of the inward release",
        pin_failures,
    )
    closed_bearing = fused([g.tool["CaptureUpperJaw"], g.tool["CaptureLowerJaw"]])
    pin = g.actor["GripTrunnion"]
    contact_gap = pin.distToShape(closed_bearing)[0]
    check(
        "capture_joint_geometric_contact",
        overlap(pin, closed_bearing) <= tolerance and contact_gap < 1e-6,
        "Circular pin contacts the lower capture jaw; its geometry is invariant during the controlled turn",
    )
    inner = s.grip_pin_radius_mm + s.grip_bearing_clearance_mm
    center = g.grip + V(0, s.grip_bearing_clearance_mm, 0)
    expected = Part.makeCylinder(
        s.grip_head_radius_mm,
        s.grip_head_depth_mm,
        center - V(0, 0, s.grip_head_depth_mm / 2),
    ).cut(
        Part.makeCylinder(
            inner,
            s.grip_head_depth_mm + 2,
            center - V(0, 0, s.grip_head_depth_mm / 2 + 1),
        )
    )
    upper_box = Part.makeBox(
        2 * s.grip_head_radius_mm + 2,
        s.grip_head_radius_mm + 1,
        s.grip_head_depth_mm + 2,
        center + V(-s.grip_head_radius_mm - 1, 0, -s.grip_head_depth_mm / 2 - 1),
    )
    expected_lower = expected.cut(upper_box)
    expected_pin = Part.makeCylinder(
        s.grip_pin_radius_mm,
        s.grip_pin_length_mm,
        g.grip - V(0, 0, s.grip_pin_length_mm / 2),
    )
    closure_valid = (
        inner > s.grip_pin_radius_mm
        and abs((inner - s.grip_pin_radius_mm) - s.grip_bearing_clearance_mm) < 1e-9
        and expected_lower.cut(g.tool["CaptureLowerJaw"]).Volume <= tolerance
        and g.tool["CaptureLowerJaw"].cut(expected_lower).Volume <= tolerance
        and expected_pin.cut(pin).Volume <= tolerance
        and pin.cut(expected_pin).Volume <= tolerance
    )
    check(
        "capture_jaw_closing_certificate",
        closure_valid,
        "The lower annulus approaches from below; concentric-radius difference equals the upward center offset, so it never penetrates the pin",
    )
    c = s.continuous_clearance_mm
    r = s.grip_rod_radius_mm + c
    rod_space = Part.makeBox(
        s.grip_rod_length_mm + 2 * r,
        s.grip_rod_length_mm + 2 * r,
        2 * r,
        g.grip + V(-r, -r, -r),
    )
    head_space = Part.makeCylinder(
        s.grip_head_radius_mm + s.grip_bearing_clearance_mm + c,
        s.grip_head_depth_mm + 2 * c,
        g.grip - V(0, 0, s.grip_head_depth_mm / 2 + c),
    )
    tool_turn_space = Part.makeCompound([rod_space, head_space])
    tool_conflicts = []
    for name, shape in g.actor.items():
        if name == "GripTrunnion":
            continue
        volume = overlap(tool_turn_space, shape)
        if volume > tolerance:
            tool_conflicts.append({"component": name, "volume_mm3": volume})
    check(
        "capture_tool_full_relative_turn_workspace",
        not tool_conflicts,
        "Conservative full-quadrant rod sweep and bearing envelope in module coordinates",
        tool_conflicts,
    )

    screw_travel = s.draw_screw_withdrawal_mm + 340.0
    screw_sweeps = {
        "shaft": Part.makeCylinder(
            s.draw_screw_shaft_radius_mm,
            s.draw_screw_shaft_length_mm + screw_travel,
            g.screw_point - scaled(g.screw_axis, s.draw_screw_shaft_length_mm),
            g.screw_axis,
        ),
        "head": Part.makeCylinder(
            s.draw_screw_head_radius_mm,
            s.draw_screw_head_depth_mm + screw_travel,
            g.screw_point,
            g.screw_axis,
        ),
        "driver": Part.makeCylinder(
            s.screwdriver_radius_mm,
            s.screwdriver_length_mm + 340 + s.draw_screw_withdrawal_mm,
            g.screw_point + scaled(g.screw_axis, s.draw_screw_head_depth_mm),
            g.screw_axis,
        ),
    }
    screw_failures = []
    screw_obstacles = {**parked_environment(g, s), **g.actor, **g.tool}
    for name, sweep in screw_sweeps.items():
        for other, obstacle in screw_obstacles.items():
            volume = overlap(sweep, obstacle)
            if volume > tolerance:
                screw_failures.append(
                    {"sweep": name, "obstacle": other, "volume_mm3": volume}
                )
    check(
        "draw_screw_and_driver_exact_sweeps",
        not screw_failures,
        "Collinear analytic cylinders cover insertion, screw withdrawal and tool removal",
        screw_failures,
    )

    phases = []
    void_regions, void_records = verify_void_regions(
        study_void_candidates(g, s), environment(g, s), tolerance
    )
    check(
        "analytic_free_regions_are_empty",
        all(item["status"] == "pass" for item in void_records),
        "Exact solid intersections verify the chamber interior, open-port column and annular aperture",
        [r for r in void_records if r["status"] != "pass"],
    )
    certified_mates = (
        {(name, pin) for name in g.actor for pin in g.pin_sweeps}
        if not pin_failures
        else set()
    )
    if closure_valid:
        certified_mates.add(("CaptureLowerJaw", "GripTrunnion"))
    if not parking_sweep_failures:
        certified_mates.update((name, "ServiceParkingComb") for name in g.plugs)
    all_phases = [*preparation_phases(g, s), *main_motion_phases(g, s)]
    if not any(item["status"] == "fail" for item in checks):
        for phase in all_phases:
            print(f"CERTIFY {phase.name}", file=sys.stderr, flush=True)
            result = certify_phase(phase, s, certified_mates, void_regions)
            phases.append(result)
            check(
                phase.name,
                result["status"] == "pass",
                f"{result['certified_intervals']} certified intervals",
                result["failures"],
            )
            if result["status"] != "pass":
                break
    complete = (
        len(phases) == len(all_phases)
        and all(p["status"] == "pass" for p in phases)
        and not screw_failures
        and not pin_failures
        and not tool_conflicts
    )
    check(
        "complete_modeled_right_sector_extraction",
        complete,
        "Includes preparation, capture, release, transfer, controlled turn, centering and lift",
    )
    final = main_motion_phases(g, s)[-1].at(1)
    rim = g.chamber.purchased_interfaces["MaintenanceAccessBlindFlange"].BoundBox.YMax
    final_bounds = {
        name: shape.optimalBoundingBox(False, False) for name, shape in final.items()
    }
    module_bottom = min(final_bounds[n].YMin for n in g.actor)
    headroom = max(box.YMax for box in final_bounds.values()) - rim
    check(
        "module_fully_above_closure_height",
        module_bottom > rim + 5,
        f"Lowest module point clears closure height by {module_bottom-rim:.3f} mm",
    )
    access = cfg.compact_one.deployment.maintenance_access.selected
    projection_radius = max(
        ((x - access.center_x_mm) ** 2 + (z - access.center_z_mm) ** 2) ** 0.5
        for name in g.actor
        for x in (final_bounds[name].XMin, final_bounds[name].XMax)
        for z in (final_bounds[name].ZMin, final_bounds[name].ZMax)
    )
    radial_margin = access.clear_bore_diameter_mm / 2 - projection_radius
    check(
        "full_module_port_passage_allowance",
        radial_margin
        >= cfg.compact_one.deployment.maintenance_access.passage_diametral_clearance_mm
        / 2,
        f"Conservative final projection radial allowance {radial_margin:.3f} mm",
    )
    for name, detail in [
        (
            "supplier_component_evidence",
            "Connector, draw-screw, capture-head and coax envelopes are provisional; capture-head internal guides/latch are not detailed and this is not a supplier-qualified assembly",
        ),
        (
            "structural_preload_and_fabrication_evidence",
            "Carrier/ring stiffness, threads, weld distortion, tolerances and clamp preload require engineering evidence",
        ),
        (
            "vacuum_material_and_optical_evidence",
            "Vacuum cleaning, optical materials and microcoax bend qualification remain unresolved",
        ),
        (
            "human_handling_and_site_envelope_evidence",
            "The modeled tool path does not establish operator reach, handling forces or available overhead space",
        ),
        (
            "flexible_harness_restraint_evidence",
            "Flexible loom motion is bounded by reserved corridors; cable fatigue and the physical parking restraint require prototype verification",
        ),
    ]:
        check(name, False, detail, warning=True)
    summary = {
        f"{status}_count": sum(item["status"] == status for item in checks)
        for status in ("pass", "warning", "fail")
    }
    report = {
        "schema_version": 1,
        "status": "fail" if summary["fail_count"] else "pass",
        "strict": bool(strict),
        "validation_mode": "boxed_sector_study",
        "scope": "one_detailed_RIGHT_sector_with_three_conservative_neighbor_reservations",
        "summary": summary,
        "checks": checks,
        "motion_phases": phases,
        "verified_free_regions": void_records,
        "complete_modeled_extraction_certified": complete,
        "required_tool_headroom_above_closure_mm": headroom,
        "module_port_radial_allowance_mm": radial_margin,
        "prerequisites": [
            "beam off",
            "target parked",
            "blank flange and copper gasket removed",
            "only the specified RIGHT-sector mechanism is evaluated",
        ],
        "study_configuration": asdict(s),
        "resolved_configuration": yaml.safe_load(dump_config_yaml(cfg)),
        "software": {"FreeCAD": ".".join(App.Version()[:3])},
    }
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report
