from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path
import sys

import FreeCAD as App
import Part

from .components import (
    build_cable_route_keepouts,
    build_compact_detector,
    build_end_modules,
    build_housekeeping_harness_keepouts,
    build_inner_frame,
    build_rotary_target_shapes,
    build_strain_relief_envelopes,
    build_top_service_equipment_envelopes,
    build_top_service_mounts,
    build_vessel_body,
    rotary_target_center,
    top_service_port_specs,
    vessel_z_bounds,
)
from .config import CIVConfig, end_module_has_groove
from .layout import DetectorPlacement, detector_center, dot, norm, target_facing_active_face_center
from .manifest import build_channel_manifest


def _scattering_angle_deg(direction) -> float:
    length = norm(direction)
    if length <= 0.0:
        return 0.0
    cos_theta = max(-1.0, min(1.0, direction.z / length))
    return math.degrees(math.acos(cos_theta))


def _result(name: str, passed: bool, **payload: object) -> dict[str, object]:
    result: dict[str, object] = {
        "name": name,
        "status": "pass" if passed else "fail",
    }
    result.update(payload)
    return result


def _end_module_type_semantics_ok(standard: str, groove_depth_mm: float) -> bool:
    if end_module_has_groove(standard):
        return groove_depth_mm > 0.0
    return groove_depth_mm <= 0.0


def _build_vacuum_boundary(cfg: CIVConfig):
    vessel_body = build_vessel_body(cfg)
    front_module, rear_module = build_end_modules(cfg)
    vacuum_boundary = vessel_body.fuse(front_module).fuse(rear_module)
    for mount in build_top_service_mounts(cfg).values():
        vacuum_boundary = vacuum_boundary.fuse(mount)
    return vacuum_boundary


def _vacuum_boundary_check(cfg: CIVConfig) -> dict[str, object]:
    vacuum_boundary = _build_vacuum_boundary(cfg)
    solid_count = len(vacuum_boundary.Solids)
    shell_count = sum(len(solid.Shells) for solid in vacuum_boundary.Solids)
    closed_shells = all(shell.isClosed() for solid in vacuum_boundary.Solids for shell in solid.Shells)
    passed = (
        not vacuum_boundary.isNull()
        and vacuum_boundary.isValid()
        and solid_count == 1
        and closed_shells
        and vacuum_boundary.Volume > 0.0
    )
    return _result(
        "vacuum_boundary_complete",
        passed,
        detail=(
            f"solids={solid_count}, shells={shell_count}, "
            f"closed={closed_shells}, volume={vacuum_boundary.Volume:.3f}"
        ),
    )


def _intersection_volume(shape_a, shape_b) -> float:
    intersection = shape_a.common(shape_b)
    if intersection.isNull():
        return 0.0
    return float(intersection.Volume)


def _bounding_box_payload(shape) -> dict[str, float]:
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


def _engineering_metrics(
    cfg: CIVConfig,
    placements: list[DetectorPlacement],
) -> dict[str, object]:
    vacuum_boundary = _build_vacuum_boundary(cfg)
    detector_metrics: list[dict[str, object]] = []
    for placement in placements:
        detector = build_compact_detector(cfg, placement)
        detector_metrics.append(
            {
                "tag": placement.tag,
                "particle": placement.particle,
                "angle_deg": placement.angle_deg,
                "active_center_radius_mm": placement.radius_mm,
                "active_center_mm": [
                    float(detector_center(placement).x),
                    float(detector_center(placement).y),
                    float(detector_center(placement).z),
                ],
                "volume_mm3": float(detector.Volume),
                "solid_count": len(detector.Solids),
                "bounding_box": _bounding_box_payload(detector),
            }
        )

    metrics: dict[str, object] = {
        "units": {
            "length": "mm",
            "volume": "mm3",
            "angle": "deg",
        },
        "vacuum_boundary": {
            "solid_count": len(vacuum_boundary.Solids),
            "volume_mm3": float(vacuum_boundary.Volume),
            "bounding_box": _bounding_box_payload(vacuum_boundary),
        },
        "detectors": {
            "count": len(detector_metrics),
            "items": detector_metrics,
        },
        "inner_support": {
            "solid_count": len(build_inner_frame(cfg, placements).Solids),
            "bounding_box": _bounding_box_payload(build_inner_frame(cfg, placements)),
        },
    }
    if cfg.top_services is not None:
        services = cfg.top_services
        electrical = services.electrical
        work_center = rotary_target_center(cfg, services.rotary.work_angle_deg)
        park_center = rotary_target_center(cfg, services.rotary.park_angle_deg)
        metrics["top_services"] = {
            "mount_count": len(top_service_port_specs(cfg)),
            "mounts": [
                {
                    "name": spec.name,
                    "role": spec.role,
                    "standard": services.icf70_interface.standard,
                    "center_x_mm": spec.center_x_mm,
                    "center_z_mm": spec.center_z_mm,
                    "bore_diameter_mm": spec.inner_diameter_mm,
                }
                for spec in top_service_port_specs(cfg)
            ],
            "signal_channels_used": electrical.detector_channel_count,
            "signal_channels_capacity": (
                len(electrical.signal_ports) * electrical.channels_per_signal_port
            ),
            "housekeeping_pins_used": (
                electrical.housekeeping.sensor_count
                * electrical.housekeeping.wires_per_sensor
            ),
            "housekeeping_pins_capacity": electrical.housekeeping.feedthrough_pin_count,
            "cable_route_count": len(build_cable_route_keepouts(cfg, placements)),
            "housekeeping_harness_count": len(build_housekeeping_harness_keepouts(cfg)),
            "minimum_static_bend_radius_mm": electrical.routing.minimum_static_bend_radius_mm,
        }
        metrics["rotary_target"] = {
            "mount_standard": services.rotary.mount_standard,
            "supplier_model_status": services.rotary.supplier_model_status,
            "shaft_diameter_mm": services.rotary.shaft_diameter_mm,
            "work_angle_deg": services.rotary.work_angle_deg,
            "park_angle_deg": services.rotary.park_angle_deg,
            "work_center_mm": [float(work_center.x), float(work_center.y), float(work_center.z)],
            "park_center_mm": [float(park_center.x), float(park_center.y), float(park_center.z)],
            "beam_stay_clear_diameter_mm": services.rotary.beam_stay_clear_diameter_mm,
        }
    return metrics


def validate_assembly(
    cfg: CIVConfig,
    placements: list[DetectorPlacement],
    strict: bool,
    output_path: str | Path | None = None,
) -> dict[str, object]:
    if cfg.compact_one is not None:
        from .validation_compact import validate_compact_one

        return validate_compact_one(
            cfg,
            placements,
            strict,
            output_path=output_path,
        )
    channel_by_name = {channel.name: channel for channel in cfg.channels}
    checks: list[dict[str, object]] = []

    for placement in placements:
        channel = channel_by_name[placement.channel_name]
        actual_angle = _scattering_angle_deg(placement.direction)
        actual_radius = norm(detector_center(placement))
        active_face_radius = norm(target_facing_active_face_center(placement, cfg.detector.length_mm))
        expected_active_face_radius = channel.radius_mm - (0.5 * cfg.detector.length_mm)

        angle_delta = abs(actual_angle - channel.angle_deg)
        radius_delta = abs(actual_radius - channel.radius_mm)
        active_face_radius_delta = abs(active_face_radius - expected_active_face_radius)
        detector_shape = build_compact_detector(cfg, placement)
        axial_projections = [
            dot(vertex.Point, placement.direction)
            for vertex in detector_shape.Vertexes
        ]
        actual_axial_center = 0.5 * (min(axial_projections) + max(axial_projections))
        actual_axial_length = max(axial_projections) - min(axial_projections)

        checks.append(
            _result(
                f"{placement.tag}.angle_deg",
                angle_delta <= cfg.validation.angle_tolerance_deg,
                value=actual_angle,
                expected=channel.angle_deg,
                tolerance=cfg.validation.angle_tolerance_deg,
            )
        )
        checks.append(
            _result(
                f"{placement.tag}.radius_mm",
                radius_delta <= cfg.validation.radius_tolerance_mm,
                value=actual_radius,
                expected=channel.radius_mm,
                tolerance=cfg.validation.radius_tolerance_mm,
            )
        )
        checks.append(
            _result(
                f"{placement.tag}.target_facing_active_face_radius_mm",
                expected_active_face_radius > 0.0
                and active_face_radius_delta <= cfg.validation.radius_tolerance_mm,
                value=active_face_radius,
                expected=expected_active_face_radius,
                tolerance=cfg.validation.radius_tolerance_mm,
            )
        )
        checks.append(
            _result(
                f"{placement.tag}.solid_active_center_radius_mm",
                abs(actual_axial_center - channel.radius_mm) <= cfg.validation.radius_tolerance_mm,
                value=actual_axial_center,
                expected=channel.radius_mm,
                tolerance=cfg.validation.radius_tolerance_mm,
            )
        )
        checks.append(
            _result(
                f"{placement.tag}.solid_active_axial_length_mm",
                abs(actual_axial_length - cfg.detector.length_mm) <= cfg.validation.radius_tolerance_mm,
                value=actual_axial_length,
                expected=cfg.detector.length_mm,
                tolerance=cfg.validation.radius_tolerance_mm,
            )
        )

    checks.append(
        _result(
            "detector_placement_count",
            len(placements) == len(cfg.channels) * len(cfg.sectors),
            value=len(placements),
            expected=len(cfg.channels) * len(cfg.sectors),
        )
    )
    checks.append(
        _result(
            "detector_radius_reference",
            cfg.detector.radius_reference == "active_center",
            detail=f"radius_reference={cfg.detector.radius_reference}",
        )
    )

    if cfg.physics is not None:
        manifest = build_channel_manifest(cfg, placements)
        manifest_channels = manifest["channels"]
        manifest_pairs = manifest["coincidence_pairs"]
        observables = manifest["observables"]
        expected_pair_count = len(cfg.physics.coincidence_pairs) * len(cfg.sectors)
        opposite_pairs_ok = all(
            pair["proton_sector"]
            == {
                "left": "right",
                "right": "left",
                "up": "down",
                "down": "up",
            }[pair["deuteron_sector"]]
            for pair in manifest_pairs
        )
        pzz = observables["pzz"]
        pyy = observables["pyy"]
        checks.append(
            _result(
                "physics_manifest_channel_count",
                len(manifest_channels) == 12,
                value=len(manifest_channels),
                expected=12,
            )
        )
        checks.append(
            _result(
                "physics_coincidence_pair_count",
                len(manifest_pairs) == expected_pair_count,
                value=len(manifest_pairs),
                expected=expected_pair_count,
            )
        )
        checks.append(
            _result(
                "physics_opposite_azimuth_pairing",
                opposite_pairs_ok,
                detail=f"pair_count={len(manifest_pairs)}",
            )
        )
        checks.append(
            _result(
                "physics_pzz_pair_partition",
                len(pzz["numerator_pair_ids"]) == 4
                and len(pzz["denominator_pair_ids"]) == 4,
                detail=(
                    f"numerator={len(pzz['numerator_pair_ids'])}, "
                    f"denominator={len(pzz['denominator_pair_ids'])}"
                ),
            )
        )
        checks.append(
            _result(
                "physics_pyy_pair_partition",
                len(pyy["lr_pair_ids"]) == 2 and len(pyy["ud_pair_ids"]) == 2,
                detail=f"lr={len(pyy['lr_pair_ids'])}, ud={len(pyy['ud_pair_ids'])}",
            )
        )
        checks.append(
            _result(
                "detector_technology_selection_state",
                cfg.detector.active_medium_status in {"undecided", "selected"}
                and cfg.detector.photosensor_status in {"undecided", "selected"},
                detail=(
                    f"active_medium={cfg.detector.active_medium_status}, "
                    f"photosensor={cfg.detector.photosensor_status}"
                ),
            )
    )

    if cfg.top_services is not None:
        services = cfg.top_services
        electrical = services.electrical
        rotary = services.rotary
        signal_capacity = len(electrical.signal_ports) * electrical.channels_per_signal_port
        spare_capacity = signal_capacity - electrical.detector_channel_count
        checks.append(
            _result(
                "top_rotary_mount_standard",
                services.icf70_interface.standard.upper() == "ICF70"
                and rotary.mount_standard.upper() == "ICF70",
                detail=(
                    f"interface={services.icf70_interface.standard}, "
                    f"rotary_mount={rotary.mount_standard}, supplier_model={rotary.supplier_model_status}"
                ),
            )
        )
        checks.append(
            _result(
                "signal_bias_service_capacity",
                electrical.detector_channel_count == len(placements)
                and signal_capacity >= len(placements)
                and spare_capacity >= len(cfg.sectors),
                value=signal_capacity,
                expected=len(placements) + len(cfg.sectors),
                detail=(
                    f"used={electrical.detector_channel_count}, spare={spare_capacity}, "
                    f"ports={len(electrical.signal_ports)}x{electrical.channels_per_signal_port}, "
                    f"impedance_ohm={electrical.impedance_ohm:.1f}"
                ),
            )
        )
        housekeeping = electrical.housekeeping
        required_housekeeping_pins = housekeeping.sensor_count * housekeeping.wires_per_sensor
        checks.append(
            _result(
                "housekeeping_pin_capacity",
                housekeeping.sensor_count == len(placements)
                and housekeeping.feedthrough_pin_count >= required_housekeeping_pins,
                value=housekeeping.feedthrough_pin_count,
                expected=required_housekeeping_pins,
                detail=(
                    f"sensors={housekeeping.sensor_count}, "
                    f"wires_per_sensor={housekeeping.wires_per_sensor}"
                ),
            )
        )
        checks.append(
            _result(
                "external_bias_tee_architecture",
                electrical.bias_on_signal_coax and not electrical.active_electronics_in_vacuum,
                detail=(
                    f"bias_on_signal_coax={electrical.bias_on_signal_coax}, "
                    f"active_electronics_in_vacuum={electrical.active_electronics_in_vacuum}"
                ),
            )
        )
        grounding = electrical.grounding
        checks.append(
            _result(
                "protective_grounding_contract",
                grounding.protective_bond_required
                and grounding.coax_shield_bond_at_feedthrough
                and not grounding.signal_shield_is_only_protective_earth,
                detail=(
                    f"protective_bond={grounding.protective_bond_required}, "
                    f"coax_bond={grounding.coax_shield_bond_at_feedthrough}, "
                    f"shield_only_pe={grounding.signal_shield_is_only_protective_earth}"
                ),
            )
        )

        work_center = rotary_target_center(cfg, rotary.work_angle_deg)
        park_center = rotary_target_center(cfg, rotary.park_angle_deg)
        work_center_error_mm = math.sqrt(
            work_center.x * work_center.x
            + work_center.y * work_center.y
            + work_center.z * work_center.z
        )
        park_transverse_mm = math.hypot(park_center.x, park_center.y)
        checks.append(
            _result(
                "rotary_target_work_center",
                work_center_error_mm <= cfg.validation.radius_tolerance_mm,
                value=work_center_error_mm,
                expected=0.0,
                tolerance=cfg.validation.radius_tolerance_mm,
            )
        )
        checks.append(
            _result(
                "rotary_target_park_beam_clearance",
                park_transverse_mm
                > 0.5 * (rotary.beam_stay_clear_diameter_mm + rotary.target_diameter_mm),
                value=park_transverse_mm,
                expected=0.5 * (rotary.beam_stay_clear_diameter_mm + rotary.target_diameter_mm),
                detail=f"park_center=({park_center.x:.3f},{park_center.y:.3f},{park_center.z:.3f})",
            )
        )

        cable_routes = build_cable_route_keepouts(cfg, placements)
        housekeeping_routes = build_housekeeping_harness_keepouts(cfg)
        strain_reliefs = build_strain_relief_envelopes(cfg, placements)
        checks.append(
            _result(
                "signal_cable_route_count",
                len(cable_routes) == len(placements),
                value=len(cable_routes),
                expected=len(placements),
                detail=(
                    f"keepout_diameter_mm={electrical.routing.cable_keepout_diameter_mm:.1f}, "
                    f"minimum_static_bend_radius_mm={electrical.routing.minimum_static_bend_radius_mm:.1f}"
                ),
            )
        )
        checks.append(
            _result(
                "housekeeping_harness_route_count",
                len(housekeeping_routes) == len(cfg.sectors),
                value=len(housekeeping_routes),
                expected=len(cfg.sectors),
            )
        )
        expected_strain_reliefs = len(placements) + len(cfg.sectors)
        checks.append(
            _result(
                "cable_strain_relief_count",
                len(strain_reliefs) == expected_strain_reliefs,
                value=len(strain_reliefs),
                expected=expected_strain_reliefs,
            )
        )

        z_min_mm, z_max_mm = vessel_z_bounds(cfg)
        beam_keepout = Part.makeCylinder(
            0.5 * rotary.beam_stay_clear_diameter_mm,
            z_max_mm - z_min_mm,
            App.Vector(0.0, 0.0, z_min_mm),
            App.Vector(0.0, 0.0, 1.0),
        )
        inner_frame = build_inner_frame(cfg, placements)
        frame_beam_overlap_mm3 = _intersection_volume(inner_frame, beam_keepout)
        cable_beam_overlap_mm3 = sum(
            _intersection_volume(route, beam_keepout)
            for route in (*cable_routes.values(), *housekeeping_routes.values())
        )
        checks.append(
            _result(
                "beam_stay_clear_support_and_services",
                frame_beam_overlap_mm3 <= 1.0e-6 and cable_beam_overlap_mm3 <= 1.0e-6,
                detail=(
                    f"diameter_mm={rotary.beam_stay_clear_diameter_mm:.1f}, "
                    f"support_overlap_mm3={frame_beam_overlap_mm3:.6f}, "
                    f"service_overlap_mm3={cable_beam_overlap_mm3:.6f}"
                ),
            )
        )

        target_work_shapes = build_rotary_target_shapes(cfg, rotary.work_angle_deg)
        target_drive_names = ("RotaryTargetShaft", "RotaryTargetHub", "RotaryTargetArm")
        los_overlap_mm3 = 0.0
        for placement in placements:
            face_center = target_facing_active_face_center(placement, cfg.detector.length_mm)
            los_length_mm = norm(face_center)
            los_keepout = Part.makeCylinder(
                0.5 * cfg.detector.diameter_mm,
                los_length_mm,
                App.Vector(0.0, 0.0, 0.0),
                face_center,
            )
            los_overlap_mm3 += _intersection_volume(inner_frame, los_keepout)
            los_overlap_mm3 += sum(
                _intersection_volume(target_work_shapes[name], los_keepout)
                for name in target_drive_names
            )
        checks.append(
            _result(
                "elastic_particle_los_support_clearance",
                los_overlap_mm3 <= 1.0e-6,
                detail=f"aggregate_overlap_mm3={los_overlap_mm3:.6f}",
            )
        )

        equipment = build_top_service_equipment_envelopes(cfg)
        equipment_items = list(equipment.items())
        equipment_overlap_pairs: list[str] = []
        for idx, (name_a, shape_a) in enumerate(equipment_items):
            for name_b, shape_b in equipment_items[idx + 1 :]:
                if _intersection_volume(shape_a, shape_b) > 1.0e-6:
                    equipment_overlap_pairs.append(f"{name_a}<->{name_b}")
        checks.append(
            _result(
                "external_feedthrough_envelope_clearance",
                not equipment_overlap_pairs,
                detail=(
                    "no overlaps"
                    if not equipment_overlap_pairs
                    else ", ".join(equipment_overlap_pairs)
                ),
            )
        )
        checks.append(
            _result(
                "top_service_port_count",
                len(top_service_port_specs(cfg)) == 2 + len(cfg.sectors),
                value=len(top_service_port_specs(cfg)),
                expected=2 + len(cfg.sectors),
                detail="rotary + four sector signal ports + housekeeping",
            )
        )

    square_contract_ok = (
        cfg.vessel.cross_section == "square"
        and math.isclose(cfg.vessel.inner_size_x_mm, cfg.vessel.inner_size_y_mm, rel_tol=0.0, abs_tol=1e-9)
    )
    checks.append(
        _result(
            "vessel_cross_section_contract",
            square_contract_ok,
            detail=(
                f"cross_section={cfg.vessel.cross_section}, "
                f"inner_size_x_mm={cfg.vessel.inner_size_x_mm:.3f}, "
                f"inner_size_y_mm={cfg.vessel.inner_size_y_mm:.3f}"
            ),
        )
    )

    front_module = cfg.vessel.end_modules.front
    rear_module = cfg.vessel.end_modules.rear
    standards_ok = (
        front_module.standard.upper() == cfg.vessel.contract.front_standard.upper()
        and rear_module.standard.upper() == cfg.vessel.contract.rear_standard.upper()
    )
    checks.append(
        _result(
            "end_module_standard",
            standards_ok,
            detail=f"front={front_module.standard}, rear={rear_module.standard}",
        )
    )

    type_semantics_ok = _end_module_type_semantics_ok(
        front_module.standard,
        front_module.oring_groove_depth_mm,
    ) and _end_module_type_semantics_ok(
        rear_module.standard,
        rear_module.oring_groove_depth_mm,
    )
    checks.append(
        _result(
            "end_module_type_semantics",
            type_semantics_ok,
            detail=(
                f"front={front_module.standard}[groove_depth={front_module.oring_groove_depth_mm:.3f}], "
                f"rear={rear_module.standard}[groove_depth={rear_module.oring_groove_depth_mm:.3f}]"
            ),
        )
    )

    pipe_stub_ok = True
    stub_parts: list[str] = []
    for side_name, module in (("front", front_module), ("rear", rear_module)):
        side_ok = (
            module.pipe_length_mm > 0.0
            and module.pipe_inner_diameter_mm >= cfg.vessel.beam_bore_diameter_mm
            and module.pipe_outer_diameter_mm <= module.module_inner_diameter_mm
        )
        pipe_stub_ok = pipe_stub_ok and side_ok
        stub_parts.append(
            f"{side_name}[std={module.standard},pipe=({module.pipe_outer_diameter_mm:.1f},{module.pipe_inner_diameter_mm:.1f},{module.pipe_length_mm:.1f})]"
        )
    checks.append(
        _result(
            "welded_pipe_stub_to_standard_flange",
            pipe_stub_ok,
            detail="; ".join(stub_parts),
        )
    )

    checks.append(_vacuum_boundary_check(cfg))

    report = {
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "checks": checks,
        "resolved_configuration": asdict(cfg),
        "engineering_metrics": _engineering_metrics(cfg, placements),
        "software": {
            "freecad_version": ".".join(App.Version()[:3]),
            "freecad_version_tuple": list(App.Version()),
            "python_version": sys.version,
        },
    }

    _ = strict

    if output_path is not None:
        path = Path(output_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return report
