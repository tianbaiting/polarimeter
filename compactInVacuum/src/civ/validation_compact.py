from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

import FreeCAD as App
import Part

from .cassette import build_detector_cassette
from .chamber import build_chamber, screen_chamber_candidate
from .config import CIVConfig
from .detector import build_active_acceptance_cone
from .internal import build_internal_assembly
from .layout import (
    DetectorPlacement,
    detector_center,
    norm,
    target_facing_active_face_center,
)
from .services import build_services
from .thermal import evaluate_thermal_paths
from .validation_rules import evaluate_config_rules, rule_status


def _bbox_overlap(shape_a: Part.Shape, shape_b: Part.Shape) -> bool:
    a = shape_a.BoundBox
    b = shape_b.BoundBox
    return not (
        a.XMax < b.XMin
        or b.XMax < a.XMin
        or a.YMax < b.YMin
        or b.YMax < a.YMin
        or a.ZMax < b.ZMin
        or b.ZMax < a.ZMin
    )


def _intersection_volume_mm3(shape_a: Part.Shape, shape_b: Part.Shape) -> float:
    if not _bbox_overlap(shape_a, shape_b):
        return 0.0
    common = shape_a.common(shape_b)
    return 0.0 if common.isNull() else float(common.Volume)


def _geometry_check(
    category: str,
    name: str,
    passed: bool,
    detail: str,
    strict_only: bool = False,
    **metrics: object,
) -> dict[str, object]:
    return {
        "category": category,
        "name": name,
        "status": "pass" if passed else ("warning" if strict_only else "fail"),
        "strict_only": strict_only,
        "detail": detail,
        **metrics,
    }


def _config_checks(cfg: CIVConfig, strict: bool) -> list[dict[str, object]]:
    return [
        {
            "category": rule.category,
            "name": rule.name,
            "status": rule_status(rule, strict),
            "strict_only": rule.strict_only,
            "detail": rule.detail,
        }
        for rule in evaluate_config_rules(cfg)
    ]


def _shape_bounds(shape: Part.Shape) -> dict[str, float]:
    box = shape.BoundBox
    return {
        "xmin_mm": float(box.XMin),
        "xmax_mm": float(box.XMax),
        "ymin_mm": float(box.YMin),
        "ymax_mm": float(box.YMax),
        "zmin_mm": float(box.ZMin),
        "zmax_mm": float(box.ZMax),
        "x_length_mm": float(box.XLength),
        "y_length_mm": float(box.YLength),
        "z_length_mm": float(box.ZLength),
    }


def _candidate_clearance_mm(candidate, shapes: list[Part.Shape]) -> float:
    wall_mm = candidate.wall_thickness_mm
    z_min_mm = (
        candidate.center_z_mm
        - 0.5 * candidate.length_mm
        + wall_mm
    )
    z_max_mm = (
        candidate.center_z_mm
        + 0.5 * candidate.length_mm
        - wall_mm
    )
    clearance_mm = float("inf")
    for shape in shapes:
        box = shape.BoundBox
        clearance_mm = min(
            clearance_mm,
            box.ZMin - z_min_mm,
            z_max_mm - box.ZMax,
        )
        if candidate.cross_section == "square":
            clearance_mm = min(
                clearance_mm,
                0.5 * candidate.inner_size_x_mm
                - max(abs(box.XMin), abs(box.XMax)),
                0.5 * candidate.inner_size_y_mm
                - max(abs(box.YMin), abs(box.YMax)),
            )
        else:
            inner_radius_mm = 0.5 * candidate.inner_size_x_mm
            maximum_radius_mm = max(
                math.hypot(vertex.Point.x, vertex.Point.y)
                for vertex in shape.Vertexes
            )
            clearance_mm = min(
                clearance_mm,
                inner_radius_mm - maximum_radius_mm,
            )
    return clearance_mm


def _detector_acceptance_metrics(
    cfg: CIVConfig,
    placements: list[DetectorPlacement],
) -> list[dict[str, object]]:
    active = cfg.compact_one.detector.active
    active_radius_mm = 0.5 * active.diameter_mm
    items: list[dict[str, object]] = []
    for placement in placements:
        center = detector_center(placement)
        face_center = target_facing_active_face_center(
            placement,
            active.thickness_mm,
        )
        face_radius_mm = face_center.Length
        theta_center_deg = math.degrees(
            math.acos(max(-1.0, min(1.0, placement.direction.z)))
        )
        phi_center_deg = math.degrees(
            math.atan2(placement.direction.y, placement.direction.x)
        )
        angular_radius_deg = math.degrees(
            math.atan2(active_radius_mm, face_radius_mm)
        )
        transverse_mm = math.hypot(face_center.x, face_center.y)
        phi_half_width_deg = (
            180.0
            if transverse_mm <= active_radius_mm
            else math.degrees(math.atan2(active_radius_mm, transverse_mm))
        )
        solid_angle_sr = 2.0 * math.pi * (
            1.0
            - face_radius_mm
            / math.sqrt(face_radius_mm * face_radius_mm + active_radius_mm * active_radius_mm)
        )
        items.append(
            {
                "tag": placement.tag,
                "channel": placement.channel_name,
                "sector": placement.sector_name,
                "theta_center_deg": theta_center_deg,
                "phi_center_deg": phi_center_deg,
                "active_diameter_mm": active.diameter_mm,
                "active_thickness_mm": active.thickness_mm,
                "center_radius_mm": center.Length,
                "active_face_radius_mm": face_radius_mm,
                "theta_min_deg": max(0.0, theta_center_deg - angular_radius_deg),
                "theta_max_deg": min(180.0, theta_center_deg + angular_radius_deg),
                "phi_min_deg": phi_center_deg - phi_half_width_deg,
                "phi_max_deg": phi_center_deg + phi_half_width_deg,
                "approximate_solid_angle_sr": solid_angle_sr,
            }
        )
    return items


def _coincidence_metrics(
    cfg: CIVConfig,
    placements: list[DetectorPlacement],
    acceptance: list[dict[str, object]],
) -> list[dict[str, object]]:
    if cfg.physics is None:
        return []
    placement_by_key = {
        (item.channel_name, item.sector_name): item
        for item in placements
    }
    acceptance_by_tag = {item["tag"]: item for item in acceptance}
    opposite = {
        "left": "right",
        "right": "left",
        "up": "down",
        "down": "up",
    }
    pairs: list[dict[str, object]] = []
    for contract in cfg.physics.coincidence_pairs:
        for sector in cfg.sectors:
            deuteron = placement_by_key[(contract.deuteron_channel, sector)]
            proton_sector = opposite[sector]
            proton = placement_by_key[(contract.proton_channel, proton_sector)]
            d_metrics = acceptance_by_tag[deuteron.tag]
            p_metrics = acceptance_by_tag[proton.tag]
            phi_delta_deg = (
                (
                    float(p_metrics["phi_center_deg"])
                    - float(d_metrics["phi_center_deg"])
                    + 180.0
                )
                % 360.0
                - 180.0
            )
            opposite_error_deg = abs(abs(phi_delta_deg) - 180.0)
            d_omega = float(d_metrics["approximate_solid_angle_sr"])
            p_omega = float(p_metrics["approximate_solid_angle_sr"])
            pairs.append(
                {
                    "pair": contract.name,
                    "deuteron_tag": deuteron.tag,
                    "proton_tag": proton.tag,
                    "opposite_azimuth_error_deg": opposite_error_deg,
                    "limiting_solid_angle_sr": min(d_omega, p_omega),
                    "geometric_solid_angle_product_sr2": d_omega * p_omega,
                    "scope": "geometry_only_not_detector_response",
                }
            )
    return pairs


def _cassette_compounds(
    internal,
) -> dict[str, Part.Shape]:
    compounds: dict[str, Part.Shape] = {}
    for placement in internal.placements:
        prefix = f"{placement.tag}_"
        shapes = [
            shape
            for name, shape in internal.physical.items()
            if name.startswith(prefix)
            and not name.endswith(
                ("CartridgeMountPad", "StructuralRail", "ThermalStrap")
            )
        ]
        compounds[placement.tag] = Part.makeCompound(shapes)
    return compounds


def _pair_collisions(
    shapes: dict[str, Part.Shape],
    tolerance_mm3: float = 1.0e-6,
) -> tuple[list[dict[str, object]], float]:
    names = tuple(shapes)
    collisions: list[dict[str, object]] = []
    minimum_clearance_mm = float("inf")
    for index, name_a in enumerate(names):
        for name_b in names[index + 1 :]:
            shape_a = shapes[name_a]
            shape_b = shapes[name_b]
            overlap_mm3 = _intersection_volume_mm3(shape_a, shape_b)
            distance_mm = float(shape_a.distToShape(shape_b)[0])
            minimum_clearance_mm = min(minimum_clearance_mm, distance_mm)
            if overlap_mm3 > tolerance_mm3:
                collisions.append(
                    {
                        "component_a": name_a,
                        "component_b": name_b,
                        "intersection_volume_mm3": overlap_mm3,
                        "distance_mm": distance_mm,
                    }
                )
    return collisions, minimum_clearance_mm


def find_pair_collisions(
    shapes: dict[str, Part.Shape],
) -> list[dict[str, object]]:
    return _pair_collisions(shapes)[0]


def find_target_motion_collisions(
    target,
    obstacles: dict[str, Part.Shape],
) -> list[dict[str, object]]:
    collisions: list[dict[str, object]] = []
    for pose in target.motion_samples:
        for moving_name, moving_shape in pose.physical.items():
            for obstacle_name, obstacle_shape in obstacles.items():
                overlap_mm3 = _intersection_volume_mm3(moving_shape, obstacle_shape)
                if overlap_mm3 > 1.0e-6:
                    collisions.append(
                        {
                            "angle_deg": pose.angle_deg,
                            "moving_component": moving_name,
                            "obstructing_component": obstacle_name,
                            "intersection_volume_mm3": overlap_mm3,
                            "distance_mm": 0.0,
                        }
                    )
    return collisions


def find_acceptance_obstructions(
    cfg: CIVConfig,
    placements: list[DetectorPlacement] | tuple[DetectorPlacement, ...],
    obstacles: dict[str, Part.Shape],
    excluded_components: dict[str, set[str]] | None = None,
) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    exclusions = excluded_components or {}
    for placement in placements:
        cone = build_active_acceptance_cone(cfg, placement)
        for component, shape in obstacles.items():
            if component in exclusions.get(placement.tag, set()):
                continue
            overlap_mm3 = _intersection_volume_mm3(cone, shape)
            if overlap_mm3 > 1.0e-6:
                failures.append(
                    {
                        "channel": placement.channel_name,
                        "sector": placement.sector_name,
                        "obstructing_component": component,
                        "intersection_volume_mm3": overlap_mm3,
                        "distance_mm": 0.0,
                        "margin_mm": 0.0,
                    }
                )
    return failures


def _material_inventory(
    cfg: CIVConfig,
    internal,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    active = cfg.compact_one.detector.active
    target = cfg.compact_one.target.foil
    material_metadata = {
        item.name: {
            "density_g_per_cm3": item.density_g_per_cm3,
            "vacuum_compatibility_status": item.vacuum_compatibility_status,
            "physics_sensitive": item.physics_sensitive,
        }
        for item in cfg.compact_one.materials
    }
    inventories: list[dict[str, object]] = []
    unexpected: list[dict[str, object]] = []
    probe_radius_mm = 0.10
    probe_area_mm2 = math.pi * probe_radius_mm * probe_radius_mm
    for placement in internal.placements:
        start = placement.direction * (-0.5 * target.thickness_mm)
        end = placement.direction * (
            placement.radius_mm + 0.5 * active.thickness_mm
        )
        delta = end - start
        probe = Part.makeCylinder(
            probe_radius_mm,
            delta.Length,
            start,
            delta,
        )
        entries: list[dict[str, object]] = []
        allowed = {
            f"{placement.tag}_ActivePlastic",
            "TargetWork_TargetFoil",
        }
        for component, shape in internal.physical.items():
            if not _bbox_overlap(probe, shape):
                continue
            volume_mm3 = _intersection_volume_mm3(probe, shape)
            if volume_mm3 <= 1.0e-8:
                continue
            material = internal.materials.get(component, "unresolved")
            entry = {
                "component": component,
                "material": material,
                "approximate_path_length_mm": volume_mm3 / probe_area_mm2,
                **material_metadata.get(
                    material,
                    {
                        "density_g_per_cm3": None,
                        "vacuum_compatibility_status": "unresolved",
                        "physics_sensitive": True,
                    },
                ),
            }
            entries.append(entry)
            if component not in allowed:
                unexpected.append(
                    {
                        "channel": placement.tag,
                        **entry,
                    }
                )
        inventories.append(
            {
                "channel": placement.tag,
                "probe_radius_mm": probe_radius_mm,
                "components": entries,
            }
        )
    return inventories, unexpected


def validate_compact_one(
    cfg: CIVConfig,
    placements: list[DetectorPlacement],
    strict: bool,
    output_path: str | Path | None = None,
) -> dict[str, object]:
    if cfg.compact_one is None:
        raise ValueError("CompactOne validation requires schema version 2")
    checks = _config_checks(cfg, strict)
    internal = build_internal_assembly(cfg)
    services = build_services(cfg, internal)
    chamber = build_chamber(cfg)
    thermal = evaluate_thermal_paths(cfg, internal)
    active = cfg.compact_one.detector.active

    acceptance = _detector_acceptance_metrics(cfg, placements)
    coincidence = _coincidence_metrics(cfg, placements, acceptance)
    actual_tags = {item.tag for item in internal.placements}
    expected_tags = {item.tag for item in placements}
    checks.append(
        _geometry_check(
            "physics",
            "detector_center_angles_and_radii",
            actual_tags == expected_tags
            and all(
                abs(norm(detector_center(item)) - item.radius_mm)
                <= cfg.validation.radius_tolerance_mm
                for item in internal.placements
            ),
            f"actual={len(actual_tags)}, expected={len(expected_tags)}",
            detector_count=len(actual_tags),
        )
    )
    channel_groups: dict[str, list[dict[str, object]]] = {}
    for item in acceptance:
        channel_groups.setdefault(str(item["channel"]), []).append(item)
    symmetry_ok = all(
        max(float(item["center_radius_mm"]) for item in group)
        - min(float(item["center_radius_mm"]) for item in group)
        <= cfg.validation.radius_tolerance_mm
        and max(float(item["theta_center_deg"]) for item in group)
        - min(float(item["theta_center_deg"]) for item in group)
        <= cfg.validation.angle_tolerance_deg
        for group in channel_groups.values()
    )
    checks.append(
        _geometry_check(
            "physics",
            "sector_symmetry",
            symmetry_ok,
            f"channel_groups={tuple(channel_groups)}",
        )
    )
    checks.append(
        _geometry_check(
            "physics",
            "coincidence_opposite_azimuth",
            all(
                float(item["opposite_azimuth_error_deg"])
                <= cfg.validation.angle_tolerance_deg
                for item in coincidence
            ),
            f"pair_count={len(coincidence)}",
        )
    )

    cassette_shapes = _cassette_compounds(internal)
    cassette_collisions, cassette_min_clearance = _pair_collisions(cassette_shapes)
    checks.append(
        _geometry_check(
            "detector",
            "cassette_valid_and_noninterfering",
            not cassette_collisions
            and len(cassette_shapes) == 12
            and all(shape.isValid() and not shape.isNull() for shape in cassette_shapes.values()),
            (
                f"count={len(cassette_shapes)}, collisions={len(cassette_collisions)}, "
                f"minimum_clearance_mm={cassette_min_clearance:.6f}"
            ),
            failures=cassette_collisions,
            minimum_clearance_mm=cassette_min_clearance,
        )
    )
    active_face_errors: list[dict[str, object]] = []
    for placement in internal.placements:
        active_shape = internal.physical[f"{placement.tag}_ActivePlastic"]
        expected_center = detector_center(placement)
        center_error_mm = (active_shape.CenterOfMass - expected_center).Length
        expected_volume_mm3 = (
            math.pi
            * (0.5 * active.diameter_mm) ** 2
            * active.thickness_mm
        )
        volume_error_mm3 = abs(active_shape.Volume - expected_volume_mm3)
        if (
            center_error_mm > cfg.validation.radius_tolerance_mm
            or volume_error_mm3 > 1.0e-6
        ):
            active_face_errors.append(
                {
                    "channel": placement.tag,
                    "center_error_mm": center_error_mm,
                    "volume_error_mm3": volume_error_mm3,
                }
            )
    checks.append(
        _geometry_check(
            "detector",
            "active_face_geometry",
            not active_face_errors,
            f"errors={len(active_face_errors)}",
            failures=active_face_errors,
        )
    )

    cartridge_compounds = {
        sector: Part.makeCompound(list(item.physical.values()))
        for sector, item in internal.cartridges.items()
    }
    cartridge_collisions, cartridge_min_clearance = _pair_collisions(
        cartridge_compounds
    )
    checks.append(
        _geometry_check(
            "sector_cartridge",
            "three_detector_mounting_and_cartridge_interference",
            not cartridge_collisions
            and all(len(item.placements) == 3 for item in internal.cartridges.values()),
            (
                f"cartridges={len(internal.cartridges)}, "
                f"collisions={len(cartridge_collisions)}, "
                f"minimum_clearance_mm={cartridge_min_clearance:.6f}"
            ),
            failures=cartridge_collisions,
        )
    )
    removal_collisions: list[dict[str, object]] = []
    for sector, cartridge in internal.cartridges.items():
        removal = cartridge.keepouts[f"{sector}_CartridgeRemovalEnvelope"]
        for other_sector, other_shape in cartridge_compounds.items():
            if other_sector == sector:
                continue
            overlap_mm3 = _intersection_volume_mm3(removal, other_shape)
            if overlap_mm3 > 1.0e-6:
                removal_collisions.append(
                    {
                        "sector": sector,
                        "obstacle_sector": other_sector,
                        "intersection_volume_mm3": overlap_mm3,
                    }
                )
    checks.append(
        _geometry_check(
            "sector_cartridge",
            "internal_removal_envelope_clear",
            not removal_collisions,
            f"collisions={len(removal_collisions)}",
            failures=removal_collisions,
        )
    )
    chamber_access_collisions = []
    for sector, cartridge in internal.cartridges.items():
        removal = cartridge.keepouts[f"{sector}_CartridgeRemovalEnvelope"]
        overlap_mm3 = _intersection_volume_mm3(
            removal,
            chamber.physical["ProjectChamberBody"],
        )
        if overlap_mm3 > 1.0e-6:
            chamber_access_collisions.append(
                {
                    "sector": sector,
                    "intersection_volume_mm3": overlap_mm3,
                }
            )
    checks.append(
        _geometry_check(
            "mechanical",
            "cartridge_service_access_contract",
            not chamber_access_collisions,
            (
                f"shell_intersections={len(chamber_access_collisions)}; "
                "a resolved removable service/access closure is required"
            ),
            strict_only=True,
            failures=chamber_access_collisions,
        )
    )

    cable_keepouts = {
        name: shape
        for cartridge in internal.cartridges.values()
        for name, shape in cartridge.keepouts.items()
        if name.endswith(("SectorCableRoute", "ConnectorKeepout"))
    }
    service_routes = {
        name: services.keepouts[name]
        for name in (
            *services.fast_signal_paths,
            *services.temperature_harnesses,
        )
    }
    target_motion_obstacles = {
        **{
            name: shape
            for name, shape in internal.physical.items()
            if not name.startswith("TargetWork_")
            and name != "TargetRotaryShaft"
        },
        **cable_keepouts,
        **service_routes,
    }
    target_collisions = find_target_motion_collisions(
        internal.target,
        target_motion_obstacles,
    )
    work_center_error_mm = internal.target.work.target_center.Length
    park_center_transverse_mm = math.hypot(
        internal.target.park.target_center.x,
        internal.target.park.target_center.y,
    )
    checks.append(
        _geometry_check(
            "target",
            "work_and_park_states",
            work_center_error_mm <= cfg.validation.radius_tolerance_mm
            and park_center_transverse_mm
            > 0.5
            * (
                cfg.compact_one.deployment.beam_stay_clear_diameter_mm
                + cfg.compact_one.target.foil.diameter_mm
            )
            and all(
                shape.isValid()
                for shape in (
                    *internal.target.work.physical.values(),
                    *internal.target.park.physical.values(),
                )
            ),
            (
                f"work_error_mm={work_center_error_mm:.6f}, "
                f"park_transverse_mm={park_center_transverse_mm:.6f}"
            ),
        )
    )
    checks.append(
        _geometry_check(
            "target",
            "full_motion_sweep_clear",
            not target_collisions,
            (
                f"samples={len(internal.target.motion_samples)}, "
                f"collisions={len(target_collisions)}"
            ),
            failures=target_collisions,
        )
    )

    los_obstacles = {
        **internal.physical,
        **services.physical,
        **chamber.physical,
        **cable_keepouts,
        **service_routes,
    }
    los_failures = find_acceptance_obstructions(
        cfg,
        internal.placements,
        los_obstacles,
        {
            placement.tag: {
                f"{placement.tag}_ActivePlastic",
                "TargetWork_TargetFoil",
            }
            for placement in internal.placements
        },
    )
    for failure in los_failures:
        component = str(failure["obstructing_component"])
        failure["material"] = internal.materials.get(
            component,
            services.materials.get(
                component,
                chamber.materials.get(component, "keepout"),
            ),
        )
    checks.append(
        _geometry_check(
            "LOS",
            "full_active_acceptance_clear",
            not los_failures,
            f"obstructions={len(los_failures)}",
            failures=los_failures,
        )
    )

    route_collisions: list[dict[str, object]] = []
    route_obstacles = {
        **internal.physical,
        **services.physical,
    }
    for route_name, route in service_routes.items():
        for obstacle_name, obstacle in route_obstacles.items():
            overlap_mm3 = _intersection_volume_mm3(route, obstacle)
            if overlap_mm3 > 1.0e-6:
                route_collisions.append(
                    {
                        "route": route_name,
                        "obstacle": obstacle_name,
                        "intersection_volume_mm3": overlap_mm3,
                    }
                )
    checks.append(
        _geometry_check(
            "services",
            "cable_routing_and_connector_keepouts_clear",
            not route_collisions
            and len(services.fast_signal_paths) == 12
            and len(services.temperature_harnesses) == 4,
            (
                f"signal_paths={len(services.fast_signal_paths)}, "
                f"temperature_harnesses={len(services.temperature_harnesses)}, "
                f"collisions={len(route_collisions)}"
            ),
            failures=route_collisions,
        )
    )

    beam = chamber.keepouts["BeamStayClear"]
    beam_collisions: list[dict[str, object]] = []
    beam_obstacles = {
        **{
            name: shape
            for name, shape in internal.physical.items()
            if name != "TargetWork_TargetFoil"
        },
        **service_routes,
    }
    for name, shape in beam_obstacles.items():
        overlap_mm3 = _intersection_volume_mm3(beam, shape)
        if overlap_mm3 > 1.0e-6:
            beam_collisions.append(
                {
                    "component": name,
                    "intersection_volume_mm3": overlap_mm3,
                }
            )
    checks.append(
        _geometry_check(
            "beamline",
            "beam_stay_clear",
            not beam_collisions,
            (
                f"diameter_mm={cfg.compact_one.deployment.beam_stay_clear_diameter_mm}, "
                f"collisions={len(beam_collisions)}"
            ),
            failures=beam_collisions,
        )
    )

    vacuum = chamber.vacuum_control_volume
    closed = all(
        shell.isClosed()
        for solid in vacuum.Solids
        for shell in solid.Shells
    )
    checks.append(
        _geometry_check(
            "vacuum",
            "vacuum_boundary_closed",
            vacuum.isValid()
            and not vacuum.isNull()
            and len(vacuum.Solids) == 1
            and closed,
            (
                f"solids={len(vacuum.Solids)}, closed={closed}, "
                f"volume_mm3={vacuum.Volume:.6f}"
            ),
        )
    )
    outside_components: list[dict[str, object]] = []
    for name, shape in internal.physical.items():
        outside_mm3 = float(shape.cut(vacuum).Volume)
        if outside_mm3 > 1.0e-5:
            outside_components.append(
                {
                    "component": name,
                    "outside_volume_mm3": outside_mm3,
                }
            )
    checks.append(
        _geometry_check(
            "mechanical",
            "internal_assembly_inside_chamber",
            not outside_components,
            f"outside_components={len(outside_components)}",
            failures=outside_components,
        )
    )

    checks.append(
        _geometry_check(
            "thermal",
            "sipm_to_chamber_thermal_paths",
            thermal.status == "pass"
            and all(item.connected for item in thermal.channels),
            (
                f"connected={sum(item.connected for item in thermal.channels)}/"
                f"{len(thermal.channels)}, "
                f"max_gap_mm={max(item.maximum_contact_gap_mm for item in thermal.channels):.6g}"
            ),
            failures=[
                asdict(item)
                for item in thermal.channels
                if not item.connected or item.maximum_contact_gap_mm > 1.0e-6
            ],
        )
    )

    path_inventory, unexpected_material = _material_inventory(cfg, internal)
    checks.append(
        _geometry_check(
            "LOS",
            "nominal_path_material_inventory",
            not unexpected_material,
            f"unexpected_material_entries={len(unexpected_material)}",
            failures=unexpected_material,
        )
    )
    chamber_candidates = []
    for candidate in cfg.compact_one.deployment.chamber_candidates:
        candidate_metrics = asdict(screen_chamber_candidate(candidate))
        candidate_metrics["sector_cartridge_clearance_mm"] = (
            _candidate_clearance_mm(
                candidate,
                list(cartridge_compounds.values()),
            )
        )
        candidate_metrics["target_motion_clearance_mm"] = (
            _candidate_clearance_mm(
                candidate,
                [internal.keepouts["TargetCompleteMotionSweep"]],
            )
        )
        chamber_candidates.append(candidate_metrics)
    if strict:
        for check in checks:
            if check["strict_only"] and check["status"] == "warning":
                check["status"] = "fail"
    category_names = (
        "physics",
        "beamline",
        "detector",
        "sector_cartridge",
        "target",
        "LOS",
        "services",
        "vacuum",
        "mechanical",
        "thermal",
    )
    categories = {
        category: [
            check
            for check in checks
            if check["category"] == category
        ]
        for category in category_names
    }
    failures = [check for check in checks if check["status"] == "fail"]
    warnings = [check for check in checks if check["status"] == "warning"]
    report: dict[str, object] = {
        "status": "fail" if failures else "pass",
        "validation_mode": "strict_engineering" if strict else "prototype_non_strict",
        "strict": strict,
        "summary": {
            "pass_count": sum(check["status"] == "pass" for check in checks),
            "warning_count": len(warnings),
            "fail_count": len(failures),
        },
        "categories": categories,
        "checks": checks,
        "engineering_metrics": {
            "deployment": cfg.compact_one.deployment.name,
            "selected_chamber": asdict(chamber.metrics),
            "chamber_candidates": chamber_candidates,
            "vacuum_control_volume": {
                "solid_count": len(vacuum.Solids),
                "volume_mm3": float(vacuum.Volume),
                "bounding_box": _shape_bounds(vacuum),
            },
            "detector_acceptance": acceptance,
            "coincidence_geometry": coincidence,
            "target": {
                "work_center_mm": list(internal.target.work.target_center),
                "park_center_mm": list(internal.target.park.target_center),
                "motion_sample_count": len(internal.target.motion_samples),
                "hard_stop_interfaces": list(internal.target.interfaces),
            },
            "services": {
                "fast_signal_paths": len(services.fast_signal_paths),
                "fast_signal_capacity": (
                    cfg.compact_one.services.signal_feedthrough_count
                    * cfg.compact_one.services.channels_per_signal_feedthrough
                ),
                "temperature_harnesses": len(services.temperature_harnesses),
                "housekeeping_required_pins": (
                    cfg.compact_one.services.temperature_channels
                    * cfg.compact_one.services.wires_per_temperature_channel
                ),
                "housekeeping_capacity_pins": (
                    cfg.compact_one.services.housekeeping_pin_capacity
                ),
                "grounding_connections": len(services.grounding_connections),
            },
            "material_path_inventory": path_inventory,
        },
        "resolved_configuration": asdict(cfg),
        "software": {
            "freecad_version": ".".join(App.Version()[:3]),
            "freecad_version_tuple": list(App.Version()),
            "python_version": sys.version,
        },
    }
    if output_path is not None:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report
