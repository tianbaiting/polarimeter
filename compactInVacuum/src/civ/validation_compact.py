from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

import FreeCAD as App
import Part

from .chamber import build_chamber, screen_chamber_candidate
from .config import CIVConfig
from .detector import build_active_acceptance_cone, detector_stack_metrics
from .internal import build_internal_assembly
from .layout import (
    DetectorPlacement,
    detector_center,
    norm,
    scaled,
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


def _aggregate_lengths_mm(shapes: list[Part.Shape]) -> tuple[float, float, float]:
    if not shapes:
        return (0.0, 0.0, 0.0)
    xmin = min(float(shape.BoundBox.XMin) for shape in shapes)
    xmax = max(float(shape.BoundBox.XMax) for shape in shapes)
    ymin = min(float(shape.BoundBox.YMin) for shape in shapes)
    ymax = max(float(shape.BoundBox.YMax) for shape in shapes)
    zmin = min(float(shape.BoundBox.ZMin) for shape in shapes)
    zmax = max(float(shape.BoundBox.ZMax) for shape in shapes)
    return (xmax - xmin, ymax - ymin, zmax - zmin)


def _top_projection_diagonal_mm(shapes: list[Part.Shape]) -> float:
    x_length_mm, _, z_length_mm = _aggregate_lengths_mm(shapes)
    return math.hypot(x_length_mm, z_length_mm)


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


def _detector_head_compounds(
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
                ("DetectorNestCradle", "RemovableClampBridge")
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
        raise ValueError("CompactOne validation requires schema version 3")
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

    detector_head_shapes = _detector_head_compounds(internal)
    detector_head_collisions, detector_head_min_clearance = _pair_collisions(
        detector_head_shapes
    )
    checks.append(
        _geometry_check(
            "detector",
            "detector_heads_valid_and_noninterfering",
            not detector_head_collisions
            and len(detector_head_shapes) == 12
            and all(
                shape.isValid() and not shape.isNull()
                for shape in detector_head_shapes.values()
            ),
            (
                f"count={len(detector_head_shapes)}, "
                f"collisions={len(detector_head_collisions)}, "
                f"minimum_clearance_mm={detector_head_min_clearance:.6f}"
            ),
            failures=detector_head_collisions,
            minimum_clearance_mm=detector_head_min_clearance,
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
    required_head_components = (
        "ActivePlastic",
        "ReflectorEnvelope",
        "OpticalCoupling",
        "SiPMPackage",
        "SensorPCBCarrier",
        "LightTightSleeve",
        "RearMountingFace",
    )
    missing_head_components = [
        f"{placement.tag}_{component}"
        for placement in internal.placements
        for component in required_head_components
        if f"{placement.tag}_{component}" not in internal.physical
    ]
    checks.append(
        _geometry_check(
            "detector",
            "detector_head_component_stack_present",
            not missing_head_components,
            f"missing={len(missing_head_components)}",
            failures=missing_head_components,
        )
    )
    sipm_alignment_errors: list[dict[str, object]] = []
    for placement in internal.placements:
        coupling = internal.physical[f"{placement.tag}_OpticalCoupling"]
        sipm = internal.physical[f"{placement.tag}_SiPMPackage"]
        delta = sipm.CenterOfMass - coupling.CenterOfMass
        axial_mm = delta.dot(placement.direction)
        transverse = delta - scaled(placement.direction, axial_mm)
        if axial_mm <= 0.0 or transverse.Length > 1.0e-6:
            sipm_alignment_errors.append(
                {
                    "channel": placement.tag,
                    "axial_separation_mm": axial_mm,
                    "transverse_misalignment_mm": transverse.Length,
                }
            )
    checks.append(
        _geometry_check(
            "detector",
            "sipm_behind_and_aligned_with_optical_coupling",
            not sipm_alignment_errors,
            f"errors={len(sipm_alignment_errors)}",
            failures=sipm_alignment_errors,
        )
    )
    stack = detector_stack_metrics(cfg)
    checks.append(
        _geometry_check(
            "detector",
            "physical_detector_head_depth_gate",
            float(stack["calculated_physical_depth_mm"]) <= 18.0,
            (
                f"calculated_mm={float(stack['calculated_physical_depth_mm']):.3f}, "
                "gate_mm=18.000, cable_and_connector_keepouts_excluded=true"
            ),
            stack=stack,
        )
    )
    removed_monitoring_objects = [
        name
        for name in (
            *internal.physical,
            *internal.keepouts,
            *internal.interfaces,
            *services.physical,
            *services.keepouts,
            *services.centerlines,
        )
        if "temperature" in name.lower() or "housekeeping" in name.lower()
    ]
    checks.append(
        _geometry_check(
            "services",
            "removed_monitoring_subsystem_absent",
            not removed_monitoring_objects,
            f"removed_role_objects={len(removed_monitoring_objects)}",
            failures=removed_monitoring_objects,
        )
    )

    sector_holder_compounds = {
        sector: Part.makeCompound(
            [
                shape
                for name, shape in item.physical.items()
                if name not in item.stationary_physical_names
            ]
        )
        for sector, item in internal.sector_holders.items()
    }
    sector_holder_collisions, sector_holder_min_clearance = _pair_collisions(
        sector_holder_compounds
    )
    coherent_plate_names = [
        name
        for name in internal.physical
        if name.endswith("_SectorCarrierPlate")
    ]
    obsolete_support_names = [
        name
        for name in internal.physical
        if name.endswith(("StructuralRail", "CartridgeMountPad", "ThermalStrap"))
    ]
    checks.append(
        _geometry_check(
            "sector_holder",
            "coherent_three_detector_sector_holders",
            not sector_holder_collisions
            and all(
                len(item.placements) == 3
                for item in internal.sector_holders.values()
            )
            and len(coherent_plate_names) == 4
            and not obsolete_support_names,
            (
                f"holders={len(internal.sector_holders)}, "
                f"carrier_plates={len(coherent_plate_names)}, "
                f"obsolete_supports={len(obsolete_support_names)}, "
                f"collisions={len(sector_holder_collisions)}, "
                f"minimum_clearance_mm={sector_holder_min_clearance:.6f}"
            ),
            failures=[*sector_holder_collisions, *obsolete_support_names],
        )
    )
    removal_collisions: list[dict[str, object]] = []
    for sector, holder_geometry in internal.sector_holders.items():
        for pose_index, removal_pose in enumerate(holder_geometry.removal_poses):
            for other_sector, other_shape in sector_holder_compounds.items():
                if other_sector == sector:
                    continue
                overlap_mm3 = _intersection_volume_mm3(
                    removal_pose,
                    other_shape,
                )
                if overlap_mm3 > 1.0e-6:
                    removal_collisions.append(
                        {
                            "sector": sector,
                            "pose_index": pose_index,
                            "obstacle_sector": other_sector,
                            "intersection_volume_mm3": overlap_mm3,
                        }
                    )
    checks.append(
        _geometry_check(
            "sector_holder",
            "sector_mount_release_envelope_clear",
            not removal_collisions,
            (
                f"initial_inward_release_collisions={len(removal_collisions)}; "
                "complete reorientation/top-lift is a separate evidence gate"
            ),
            failures=removal_collisions,
        )
    )
    detector_removal_collisions: list[dict[str, object]] = []
    for holder_geometry in internal.sector_holders.values():
        holder_obstacles = {
            name: holder_geometry.physical[name]
            for name in holder_geometry.holder_physical_names
        }
        for placement in holder_geometry.placements:
            envelope = holder_geometry.keepouts[
                f"{placement.tag}_DetectorRemovalEnvelope"
            ]
            released_clamp = f"{placement.tag}_RemovableClampBridge"
            for obstacle_name, obstacle in holder_obstacles.items():
                if obstacle_name == released_clamp:
                    continue
                overlap_mm3 = _intersection_volume_mm3(envelope, obstacle)
                if overlap_mm3 > 1.0e-6:
                    detector_removal_collisions.append(
                        {
                            "channel": placement.tag,
                            "obstacle": obstacle_name,
                            "intersection_volume_mm3": overlap_mm3,
                        }
                    )
    checks.append(
        _geometry_check(
            "sector_holder",
            "detector_axial_removal_after_clamp_release_clear",
            not detector_removal_collisions,
            f"collisions={len(detector_removal_collisions)}",
            failures=detector_removal_collisions,
        )
    )
    chamber_access_collisions = []
    for sector, holder_geometry in internal.sector_holders.items():
        for pose_index, removal_pose in enumerate(holder_geometry.removal_poses):
            overlap_mm3 = _intersection_volume_mm3(
                removal_pose,
                chamber.physical["ProjectChamberBody"],
            )
            if overlap_mm3 > 1.0e-6:
                chamber_access_collisions.append(
                    {
                        "sector": sector,
                        "pose_index": pose_index,
                        "intersection_volume_mm3": overlap_mm3,
                    }
                )
    checks.append(
        _geometry_check(
            "mechanical",
            "sector_holder_service_access_contract",
            not chamber_access_collisions
            and (
                cfg.compact_one.deployment.maintenance_access is None
                or cfg.compact_one.deployment.maintenance_access.complete_extraction_status
                == "frozen"
            ),
            (
                f"initial_release_shell_intersections={len(chamber_access_collisions)}; "
                "complete release/reorientation/top-lift evidence status="
                f"{('not_applicable' if cfg.compact_one.deployment.maintenance_access is None else cfg.compact_one.deployment.maintenance_access.complete_extraction_status)}"
            ),
            strict_only=True,
            failures=chamber_access_collisions,
        )
    )

    support_structure_metrics: list[dict[str, object]] = []
    holder_support_failures: list[dict[str, object]] = []
    support_wall_failures: list[dict[str, object]] = []
    ground_bond_failures: list[dict[str, object]] = []
    access_support_failures: list[dict[str, object]] = []
    chamber_body = chamber.physical["ProjectChamberBody"]
    access_lift_corridor = chamber.keepouts.get(
        "MaintenanceAccessInternalLiftCorridor"
    )
    for sector, holder_geometry in internal.sector_holders.items():
        mount = cfg.compact_one.deployment.sector_mount(sector)
        block = holder_geometry.physical[f"{sector}_SectorInterfaceBlock"]
        support = holder_geometry.physical[f"{sector}_PermanentWallSupport"]
        ground = services.physical[f"{sector}_ProtectiveGroundStrap"]
        pins = {
            name: holder_geometry.purchased_interfaces[name]
            for name in holder_geometry.stationary_purchased_interface_names
        }
        block_support_gap_mm = float(block.distToShape(support)[0])
        support_wall_gap_mm = float(support.distToShape(chamber_body)[0])
        pin_support_gaps_mm = {
            name: float(shape.distToShape(support)[0])
            for name, shape in pins.items()
        }
        ground_block_gap_mm = float(ground.distToShape(block)[0])
        ground_support_gap_mm = float(ground.distToShape(support)[0])
        ground_wall_gap_mm = float(ground.distToShape(chamber_body)[0])
        ground_extent_mm = max(
            float(ground.BoundBox.XLength),
            float(ground.BoundBox.YLength),
            float(ground.BoundBox.ZLength),
        )
        other_holder_overlaps: list[dict[str, object]] = []
        for other_sector, other_holder in sector_holder_compounds.items():
            if other_sector == sector:
                continue
            overlap_mm3 = _intersection_volume_mm3(support, other_holder)
            if overlap_mm3 > 1.0e-6:
                other_holder_overlaps.append(
                    {
                        "other_sector": other_sector,
                        "intersection_volume_mm3": overlap_mm3,
                    }
                )
        if (
            block_support_gap_mm > 1.0e-6
            or not support.isValid()
            or support.isNull()
            or other_holder_overlaps
        ):
            holder_support_failures.append(
                {
                    "sector": sector,
                    "block_support_gap_mm": block_support_gap_mm,
                    "support_valid": support.isValid() and not support.isNull(),
                    "other_holder_overlaps": other_holder_overlaps,
                }
            )
        if support_wall_gap_mm > 1.0e-6 or any(
            gap_mm > 1.0e-6 for gap_mm in pin_support_gaps_mm.values()
        ):
            support_wall_failures.append(
                {
                    "sector": sector,
                    "support_wall_gap_mm": support_wall_gap_mm,
                    "pin_support_gaps_mm": pin_support_gaps_mm,
                }
            )
        if (
            ground.Volume <= 100.0
            or ground_extent_mm <= 5.0
            or ground_block_gap_mm > 1.0e-6
            or ground_support_gap_mm > 1.0e-6
            or ground_wall_gap_mm > 1.0e-6
        ):
            ground_bond_failures.append(
                {
                    "sector": sector,
                    "volume_mm3": float(ground.Volume),
                    "maximum_extent_mm": ground_extent_mm,
                    "block_gap_mm": ground_block_gap_mm,
                    "support_gap_mm": ground_support_gap_mm,
                    "wall_gap_mm": ground_wall_gap_mm,
                }
            )
        support_lift_overlap_mm3 = (
            0.0
            if access_lift_corridor is None
            else _intersection_volume_mm3(support, access_lift_corridor)
        )
        pin_lift_overlap_mm3 = sum(
            0.0
            if access_lift_corridor is None
            else _intersection_volume_mm3(shape, access_lift_corridor)
            for shape in pins.values()
        )
        ground_lift_overlap_mm3 = (
            0.0
            if access_lift_corridor is None
            else _intersection_volume_mm3(ground, access_lift_corridor)
        )
        if (
            mount.wall == "positive_y"
            or support_lift_overlap_mm3 > 1.0e-6
            or pin_lift_overlap_mm3 > 1.0e-6
            or ground_lift_overlap_mm3 > 1.0e-6
        ):
            access_support_failures.append(
                {
                    "sector": sector,
                    "mount_wall": mount.wall,
                    "support_lift_overlap_mm3": support_lift_overlap_mm3,
                    "pin_lift_overlap_mm3": pin_lift_overlap_mm3,
                    "ground_lift_overlap_mm3": ground_lift_overlap_mm3,
                }
            )
        support_structure_metrics.append(
            {
                "sector": sector,
                "mount_wall": mount.wall,
                "tangent_coordinate_mm": mount.tangent_coordinate_mm,
                "wall_standoff_mm": mount.wall_standoff_mm,
                "block_support_gap_mm": block_support_gap_mm,
                "support_wall_gap_mm": support_wall_gap_mm,
                "pin_support_gaps_mm": pin_support_gaps_mm,
                "ground_volume_mm3": float(ground.Volume),
                "ground_maximum_extent_mm": ground_extent_mm,
                "ground_wall_gap_mm": ground_wall_gap_mm,
                "support_lift_overlap_mm3": support_lift_overlap_mm3,
                "pin_lift_overlap_mm3": pin_lift_overlap_mm3,
                "ground_lift_overlap_mm3": ground_lift_overlap_mm3,
            }
        )
    checks.append(
        _geometry_check(
            "mechanical",
            "holder_to_stationary_support_load_path",
            not holder_support_failures,
            f"failures={len(holder_support_failures)}",
            failures=holder_support_failures,
        )
    )
    checks.append(
        _geometry_check(
            "mechanical",
            "stationary_support_to_permanent_chamber_contact",
            not support_wall_failures,
            f"failures={len(support_wall_failures)}",
            failures=support_wall_failures,
        )
    )
    checks.append(
        _geometry_check(
            "services",
            "protective_ground_bond_to_permanent_chamber",
            not ground_bond_failures,
            f"failures={len(ground_bond_failures)}",
            failures=ground_bond_failures,
        )
    )
    checks.append(
        _geometry_check(
            "mechanical",
            "maintenance_access_closure_load_free",
            not access_support_failures,
            f"failures={len(access_support_failures)}",
            failures=access_support_failures,
        )
    )

    maintenance_access_metrics: dict[str, object] | None = None
    access = cfg.compact_one.deployment.maintenance_access
    if access is not None and access.enabled:
        access_spec = access.selected
        chamber_candidate = chamber.candidate
        outer_half_x_mm = (
            0.5 * chamber_candidate.inner_size_x_mm
            + chamber_candidate.wall_thickness_mm
        )
        z_min_mm = (
            chamber_candidate.center_z_mm
            - 0.5 * chamber_candidate.length_mm
        )
        z_max_mm = (
            chamber_candidate.center_z_mm
            + 0.5 * chamber_candidate.length_mm
        )
        access_radius_mm = 0.5 * access_spec.flange_outer_diameter_mm
        edge_margins_mm = {
            "negative_x": access_spec.center_x_mm
            - access_radius_mm
            + outer_half_x_mm,
            "positive_x": outer_half_x_mm
            - access_spec.center_x_mm
            - access_radius_mm,
            "front_z": access_spec.center_z_mm - access_radius_mm - z_min_mm,
            "rear_z": z_max_mm - access_spec.center_z_mm - access_radius_mm,
        }
        minimum_edge_margin_mm = min(edge_margins_mm.values())
        checks.append(
            _geometry_check(
                "mechanical",
                "maintenance_access_flange_within_top_face",
                minimum_edge_margin_mm >= access.flange_edge_margin_mm,
                (
                    f"standard={access_spec.standard}, minimum_edge_margin_mm="
                    f"{minimum_edge_margin_mm:.6f}, required_mm="
                    f"{access.flange_edge_margin_mm:.6f}"
                ),
                edge_margins_mm=edge_margins_mm,
            )
        )

        port_clearances: list[dict[str, object]] = []
        minimum_port_clearance_mm = float("inf")
        for port in cfg.compact_one.deployment.service_ports:
            port_outer_diameter_mm = (
                cfg.compact_one.services.signal_interface.module_outer_diameter_mm
                if port.role == "signal"
                else (
                    70.0
                    if cfg.compact_one.deployment.target_feedthrough_standard == "ICF70"
                    else port.collar_outer_diameter_mm
                )
            )
            center_distance_mm = math.hypot(
                access_spec.center_x_mm - port.center_x_mm,
                access_spec.center_z_mm - port.center_z_mm,
            )
            clearance_mm = center_distance_mm - 0.5 * (
                access_spec.flange_outer_diameter_mm
                + port_outer_diameter_mm
            )
            minimum_port_clearance_mm = min(
                minimum_port_clearance_mm,
                clearance_mm,
            )
            port_clearances.append(
                {
                    "port": port.name,
                    "role": port.role,
                    "clearance_mm": clearance_mm,
                }
            )
        checks.append(
            _geometry_check(
                "mechanical",
                "maintenance_access_service_ports_clear",
                minimum_port_clearance_mm >= access.service_port_clearance_mm,
                (
                    f"minimum_clearance_mm={minimum_port_clearance_mm:.6f}, "
                    f"required_mm={access.service_port_clearance_mm:.6f}"
                ),
                port_clearances=port_clearances,
            )
        )

        holder_dimensions_mm: dict[str, tuple[float, float, float]] = {}
        holder_projection_diagonals_mm: dict[str, float] = {}
        holder_edge_on_diagonals_mm: dict[str, float] = {}
        for sector, holder in internal.sector_holders.items():
            xmin, xmax, ymin, ymax, zmin, zmax = (
                holder.loaded_maintenance_bounds_mm
            )
            dimensions = (xmax - xmin, ymax - ymin, zmax - zmin)
            holder_dimensions_mm[sector] = dimensions
            holder_projection_diagonals_mm[sector] = math.hypot(
                dimensions[0],
                dimensions[2],
            )
            two_smallest = sorted(dimensions)[:2]
            holder_edge_on_diagonals_mm[sector] = math.hypot(*two_smallest)
        required_passage_mm = (
            max(holder_projection_diagonals_mm.values())
            + access.passage_diametral_clearance_mm
        )
        passage_margin_mm = (
            access_spec.clear_bore_diameter_mm - required_passage_mm
        )
        checks.append(
            _geometry_check(
                "mechanical",
                "maintenance_access_detached_holder_passage_screen",
                passage_margin_mm >= 0.0,
                (
                    f"standard={access_spec.standard}, clear_bore_mm="
                    f"{access_spec.clear_bore_diameter_mm:.6f}, "
                    f"required_conservative_top_projection_mm={required_passage_mm:.6f}, "
                    f"margin_mm={passage_margin_mm:.6f}"
                ),
                strict_only=True,
                holder_dimensions_mm=holder_dimensions_mm,
                holder_projection_diagonals_mm=holder_projection_diagonals_mm,
                holder_edge_on_diagonals_mm=holder_edge_on_diagonals_mm,
                passage_margin_mm=passage_margin_mm,
            )
        )

        closure_names = {
            "MaintenanceAccessProjectWeldNeck",
            "MaintenanceAccessProjectWeldBead",
            "MaintenanceAccessFixedICFFlange",
            "MaintenanceAccessCopperGasket",
            "MaintenanceAccessBlindFlange",
        }
        generated_access_names = {
            *chamber.physical,
            *chamber.purchased_interfaces,
        }
        fixed_flange = chamber.purchased_interfaces.get(
            "MaintenanceAccessFixedICFFlange"
        )
        gasket = chamber.purchased_interfaces.get("MaintenanceAccessCopperGasket")
        blind = chamber.purchased_interfaces.get("MaintenanceAccessBlindFlange")
        neck = chamber.physical.get("MaintenanceAccessProjectWeldNeck")
        weld_bead = chamber.physical.get("MaintenanceAccessProjectWeldBead")
        contact_gaps_mm = {
            "neck_to_weld_bead": (
                float("inf")
                if neck is None or weld_bead is None
                else float(neck.distToShape(weld_bead)[0])
            ),
            "weld_bead_to_fixed_flange": (
                float("inf")
                if weld_bead is None or fixed_flange is None
                else float(weld_bead.distToShape(fixed_flange)[0])
            ),
            "fixed_flange_to_gasket": (
                float("inf")
                if fixed_flange is None or gasket is None
                else float(fixed_flange.distToShape(gasket)[0])
            ),
            "gasket_to_blind": (
                float("inf")
                if gasket is None or blind is None
                else float(gasket.distToShape(blind)[0])
            ),
        }
        closure_complete = (
            closure_names <= generated_access_names
            and max(contact_gaps_mm.values()) <= 1.0e-6
            and access.seal_type == "conflat_knife_edge_metal_gasket"
            and access.seal_material == "oxygen_free_copper"
            and not access.elastomer_seal_allowed
        )
        checks.append(
            _geometry_check(
                "vacuum",
                "maintenance_access_nominal_metal_seal_topology",
                closure_complete,
                (
                    f"components={len(closure_names & generated_access_names)}/"
                    f"{len(closure_names)}, max_contact_gap_mm="
                    f"{max(contact_gaps_mm.values()):.6g}, "
                    f"seal={access.seal_material}"
                    "; purchased knife-edge detail and leak performance remain evidence gates"
                ),
                contact_gaps_mm=contact_gaps_mm,
            )
        )
        candidate_comparison: list[dict[str, object]] = []
        chamber_by_name = {
            item.name: item
            for item in cfg.compact_one.deployment.chamber_candidates
        }
        flat_required_mm = (
            max(holder_projection_diagonals_mm.values())
            + access.passage_diametral_clearance_mm
        )
        edge_on_required_mm = (
            max(holder_edge_on_diagonals_mm.values())
            + access.passage_diametral_clearance_mm
        )
        for option in access.candidates:
            option_chamber = chamber_by_name[option.chamber_candidate]
            option_half_x_mm = (
                0.5 * option_chamber.inner_size_x_mm
                + option_chamber.wall_thickness_mm
            )
            option_z_min_mm = (
                option_chamber.center_z_mm - 0.5 * option_chamber.length_mm
            )
            option_z_max_mm = (
                option_chamber.center_z_mm + 0.5 * option_chamber.length_mm
            )
            option_radius_mm = 0.5 * option.flange_outer_diameter_mm
            option_edge_margins = (
                option.center_x_mm - option_radius_mm + option_half_x_mm,
                option_half_x_mm - option.center_x_mm - option_radius_mm,
                option.center_z_mm - option_radius_mm - option_z_min_mm,
                option_z_max_mm - option.center_z_mm - option_radius_mm,
            )
            option_port_clearances: list[float] = []
            for port in cfg.compact_one.deployment.service_ports:
                port_outer_diameter_mm = (
                    cfg.compact_one.services.signal_interface.module_outer_diameter_mm
                    if port.role == "signal"
                    else (
                        70.0
                        if cfg.compact_one.deployment.target_feedthrough_standard
                        == "ICF70"
                        else port.collar_outer_diameter_mm
                    )
                )
                option_port_clearances.append(
                    math.hypot(
                        option.center_x_mm - port.center_x_mm,
                        option.center_z_mm - port.center_z_mm,
                    )
                    - 0.5
                    * (
                        option.flange_outer_diameter_mm
                        + port_outer_diameter_mm
                    )
                )
            candidate_comparison.append(
                {
                    "standard": option.standard,
                    "disposition": option.disposition,
                    "chamber_candidate": option.chamber_candidate,
                    "chamber_length_mm": option_chamber.length_mm,
                    "clear_bore_diameter_mm": option.clear_bore_diameter_mm,
                    "minimum_flange_edge_margin_mm": min(option_edge_margins),
                    "minimum_service_port_clearance_mm": min(
                        option_port_clearances
                    ),
                    "flat_lift_passage_margin_mm": (
                        option.clear_bore_diameter_mm - flat_required_mm
                    ),
                    "edge_on_passage_margin_mm": (
                        option.clear_bore_diameter_mm - edge_on_required_mm
                    ),
                    "flat_lift_screen_passed": (
                        option.clear_bore_diameter_mm >= flat_required_mm
                    ),
                    "edge_on_screen_passed": (
                        option.clear_bore_diameter_mm >= edge_on_required_mm
                    ),
                }
            )
        maintenance_access_metrics = {
            "selected_candidate": asdict(access_spec),
            "seal_type": access.seal_type,
            "seal_material": access.seal_material,
            "elastomer_seal_allowed": access.elastomer_seal_allowed,
            "helium_leak_rate_max_pa_m3_s": access.helium_leak_rate_max_pa_m3_s,
            "edge_margins_mm": edge_margins_mm,
            "minimum_service_port_clearance_mm": minimum_port_clearance_mm,
            "port_clearances": port_clearances,
            "holder_projection_diagonals_mm": holder_projection_diagonals_mm,
            "holder_edge_on_diagonals_mm": holder_edge_on_diagonals_mm,
            "required_passage_mm": required_passage_mm,
            "passage_margin_mm": passage_margin_mm,
            "contact_gaps_mm": contact_gaps_mm,
            "complete_extraction_status": access.complete_extraction_status,
            "candidate_comparison": candidate_comparison,
        }

    cable_keepouts = {
        name: shape
        for holder_geometry in internal.sector_holders.values()
        for name, shape in holder_geometry.keepouts.items()
        if name.endswith(("SectorCableRoute", "ConnectorKeepout"))
    }
    service_routes = {
        name: services.keepouts[name]
        for name in services.fast_signal_paths
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
        **internal.purchased_interfaces,
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
            and len(services.fast_signal_paths) == 12,
            (
                f"signal_paths={len(services.fast_signal_paths)}, "
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
    selected_clearance_mm = _candidate_clearance_mm(
        chamber.candidate,
        list(sector_holder_compounds.values()),
    )
    checks.append(
        _geometry_check(
            "mechanical",
            "minimum_internal_assembly_clearance",
            selected_clearance_mm >= 3.0,
            (
                f"minimum_clearance_mm={selected_clearance_mm:.6f}, "
                "prototype_screening_minimum_mm=3.000"
            ),
            minimum_clearance_mm=selected_clearance_mm,
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
        candidate_metrics["sector_holder_clearance_mm"] = (
            _candidate_clearance_mm(
                candidate,
                list(sector_holder_compounds.values()),
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
        "sector_holder",
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
        "schema_version": 3,
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
            "support_structure": support_structure_metrics,
            "maintenance_access": maintenance_access_metrics,
            "chamber_candidates": chamber_candidates,
            "vacuum_control_volume": {
                "solid_count": len(vacuum.Solids),
                "volume_mm3": float(vacuum.Volume),
                "bounding_box": _shape_bounds(vacuum),
            },
            "detector_acceptance": acceptance,
            "detector_head_stack": detector_stack_metrics(cfg),
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
