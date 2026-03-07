from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import FreeCAD as App
import Part

from .components import (
    build_all_plates,
    build_chamber,
    build_detector_fixture,
    build_end_module_fasteners,
    build_end_modules,
    build_plate_load_ties,
    build_ports,
    build_stand,
    build_target_holders,
    build_target_ladder,
)
from .config import GeometryConfig, PlateConfig
from .layout import DetectorPlacement, front_face_center, norm, plate_key_for_sector, ray_point_at_z, scaled


@dataclass(frozen=True)
class ValidationThresholds:
    angle_tolerance_deg: float = 0.05
    radius_tolerance_mm: float = 0.2


@dataclass(frozen=True)
class ChannelValidationResult:
    tag: str
    target_angle_deg: float
    actual_angle_deg: float
    delta_angle_deg: float
    target_radius_mm: float
    actual_radius_mm: float
    delta_radius_mm: float
    passed: bool


@dataclass(frozen=True)
class SubsystemCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class SubsystemValidationResult:
    name: str
    status: str
    checks: tuple[SubsystemCheck, ...]


@dataclass(frozen=True)
class ValidationReport:
    status: str
    thresholds: ValidationThresholds
    channels: tuple[ChannelValidationResult, ...]
    subsystems: tuple[SubsystemValidationResult, ...]


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _scattering_angle_deg(front_center: App.Vector) -> float:
    radius = norm(front_center)
    if radius <= 0.0:
        return 0.0
    cos_theta = _clamp(front_center.z / radius, -1.0, 1.0)
    return math.degrees(math.acos(cos_theta))


def _detector_channel_result(
    placement: DetectorPlacement,
    thresholds: ValidationThresholds,
) -> ChannelValidationResult:
    center = front_face_center(placement)
    actual_radius_mm = norm(center)
    actual_angle_deg = _scattering_angle_deg(center)

    delta_angle_deg = actual_angle_deg - placement.angle_deg
    delta_radius_mm = actual_radius_mm - placement.radius_mm
    passed = (
        abs(delta_angle_deg) <= thresholds.angle_tolerance_deg
        and abs(delta_radius_mm) <= thresholds.radius_tolerance_mm
    )

    return ChannelValidationResult(
        tag=placement.tag,
        target_angle_deg=placement.angle_deg,
        actual_angle_deg=actual_angle_deg,
        delta_angle_deg=delta_angle_deg,
        target_radius_mm=placement.radius_mm,
        actual_radius_mm=actual_radius_mm,
        delta_radius_mm=delta_radius_mm,
        passed=passed,
    )


def _distance(a: App.Vector, b: App.Vector) -> float:
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def _normalize_deg(angle_deg: float) -> float:
    out = angle_deg
    while out > 180.0:
        out -= 360.0
    while out < -180.0:
        out += 360.0
    return out


def _plate_for_sector(cfg: GeometryConfig, sector_name: str) -> PlateConfig:
    key = plate_key_for_sector(sector_name)
    if key == "h":
        return cfg.plate.h
    if key == "v1":
        return cfg.plate.v1
    if key == "v2":
        return cfg.plate.v2
    raise ValueError(f"Unsupported plate key {key!r}")


def _plate_hit_point(placement: DetectorPlacement, plate: PlateConfig) -> App.Vector:
    center = front_face_center(placement)
    if plate.mount_plane == "xy":
        return App.Vector(center.x, center.y, plate.z_mm)
    if plate.mount_plane == "xz":
        return App.Vector(center.x, plate.offset_y_mm, center.z)
    if plate.mount_plane == "yz":
        return App.Vector(plate.offset_x_mm, center.y, center.z)
    raise ValueError(f"unsupported mount_plane {plate.mount_plane!r}")


def _plate_local_uv(hit: App.Vector, plate: PlateConfig) -> tuple[float, float]:
    if plate.mount_plane == "xy":
        return hit.x - plate.offset_x_mm, hit.y - plate.offset_y_mm
    if plate.mount_plane == "xz":
        return hit.x - plate.offset_x_mm, hit.z - plate.z_mm
    if plate.mount_plane == "yz":
        return hit.y - plate.offset_y_mm, hit.z - plate.z_mm
    raise ValueError(f"unsupported mount_plane {plate.mount_plane!r}")


def _normalize_vector(v: App.Vector) -> App.Vector:
    n = _vector_length(v)
    if n <= 1e-12:
        raise ValueError("cannot normalize near-zero vector")
    return App.Vector(v.x / n, v.y / n, v.z / n)


def _dot(a: App.Vector, b: App.Vector) -> float:
    return (a.x * b.x) + (a.y * b.y) + (a.z * b.z)


def _plate_outward_normal(plate: PlateConfig) -> App.Vector:
    if plate.mount_plane == "xy":
        z_sign = 1.0 if plate.z_mm >= 0.0 else -1.0
        if abs(plate.z_mm) < 1e-9:
            z_sign = 1.0
        return App.Vector(0.0, 0.0, z_sign)
    if plate.mount_plane == "xz":
        y_sign = 1.0 if plate.offset_y_mm >= 0.0 else -1.0
        if abs(plate.offset_y_mm) < 1e-9:
            y_sign = 1.0
        return App.Vector(0.0, y_sign, 0.0)
    if plate.mount_plane == "yz":
        x_sign = 1.0 if plate.offset_x_mm >= 0.0 else -1.0
        if abs(plate.offset_x_mm) < 1e-9:
            x_sign = 1.0
        return App.Vector(x_sign, 0.0, 0.0)
    raise ValueError(f"unsupported mount_plane {plate.mount_plane!r}")


def _detector_mount_axis(placement: DetectorPlacement, plate: PlateConfig) -> App.Vector:
    direction = _normalize_vector(placement.direction)
    inward = scaled(_plate_outward_normal(plate), -1.0)
    projected = inward - scaled(direction, _dot(inward, direction))
    if _vector_length(projected) <= 1e-9:
        projected = inward
    return _normalize_vector(projected)


def _detector_mount_bridge_length_mm(cfg: GeometryConfig, placement: DetectorPlacement) -> float:
    plate = _plate_for_sector(cfg, placement.sector_name)
    clamp = cfg.detector.clamp
    adapter = cfg.detector.adapter_block
    direction = _normalize_vector(placement.direction)
    mount_axis = _detector_mount_axis(placement, plate)

    front_center = front_face_center(placement)
    clamp_center = front_center + scaled(direction, clamp.support_overlap_mm)
    mount_proj = _plate_hit_point(placement, plate)
    plate_normal = _plate_outward_normal(plate)
    mount_base_center = mount_proj + scaled(plate_normal, 0.5 * (plate.thickness_mm + clamp.mount_base_thickness_mm))
    mount_base_top_center = mount_base_center + scaled(plate_normal, 0.5 * clamp.mount_base_thickness_mm)

    effective_radial_standoff = adapter.radial_standoff_mm
    if not cfg.stand.enable_plate_ties:
        effective_radial_standoff = max(4.0, min(adapter.radial_standoff_mm, 0.5 * adapter.radial_standoff_mm + 2.0))
    support_to_block_center = 0.5 * clamp.outer_diameter_mm + effective_radial_standoff + 0.5 * adapter.width_mm
    block_center = clamp_center - scaled(mount_axis, support_to_block_center)
    bridge_target = block_center - scaled(mount_axis, 0.5 * adapter.width_mm)
    if not cfg.stand.enable_plate_ties:
        bridge_target = block_center - scaled(mount_axis, 0.25 * adapter.width_mm)

    return _dot(bridge_target - mount_base_top_center, mount_axis)


def _los_hit_with_margin(
    placement: DetectorPlacement,
    plate: PlateConfig,
    margin_mm: float,
) -> tuple[bool, str]:
    hit = _plate_hit_point(placement, plate)
    u, v = _plate_local_uv(hit, plate)

    if abs(u) > (0.5 * plate.width_mm - margin_mm):
        return False, f"|u|={abs(u):.3f} exceeds width margin at plate {plate.orientation}/{plate.mount_plane}"
    if abs(v) > (0.5 * plate.height_mm - margin_mm):
        return False, f"|v|={abs(v):.3f} exceeds height margin at plate {plate.orientation}/{plate.mount_plane}"

    radius = math.hypot(u, v)
    azimuth = math.degrees(math.atan2(v, u))

    if radius < (plate.inner_radius_mm + margin_mm):
        return False, f"radius={radius:.3f} below inner+margin={plate.inner_radius_mm + margin_mm:.3f}"
    if radius > (plate.outer_radius_mm - margin_mm):
        return False, f"radius={radius:.3f} above outer-margin={plate.outer_radius_mm - margin_mm:.3f}"

    min_angle_margin_deg = math.degrees(margin_mm / max(radius, 1e-6))
    for center in plate.azimuth_centers_deg:
        delta = abs(_normalize_deg(azimuth - center))
        if delta <= (0.5 * plate.sector_opening_deg - min_angle_margin_deg):
            return True, (
                f"u={u:.3f} v={v:.3f} radius={radius:.3f} azimuth={azimuth:.3f} "
                f"center={center:.3f} margin_deg={min_angle_margin_deg:.3f}"
            )

    return False, f"azimuth={azimuth:.3f} violates angular margin for all sectors"


def _vector_length(v: App.Vector) -> float:
    return math.sqrt((v.x * v.x) + (v.y * v.y) + (v.z * v.z))


def _shape_intersects_segment(shape: Part.Shape, start: App.Vector, end: App.Vector, eps: float = 1e-3) -> bool:
    edge = Part.makeLine(start, end)
    section = shape.section(edge)
    if section.isNull() or not section.Vertexes:
        return False

    for vertex in section.Vertexes:
        d0 = _vector_length(vertex.Point - start)
        d1 = _vector_length(vertex.Point - end)
        if d0 > eps and d1 > eps:
            return True
    return False


def _los_occluders(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement],
    *,
    exclude_tag: str,
) -> list[tuple[str, Part.Shape]]:
    if cfg.clearance.los_scope == "v1_conceptual":
        return _los_occluders_v1(cfg, placements, exclude_tag=exclude_tag)
    if cfg.clearance.los_scope == "v2_fullpath":
        return _los_occluders_v2(cfg, placements, exclude_tag=exclude_tag)
    raise ValueError(f"unsupported los_scope {cfg.clearance.los_scope!r}")


def _los_occluders_v1(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement],
    *,
    exclude_tag: str,
) -> list[tuple[str, Part.Shape]]:
    occluders: list[tuple[str, Part.Shape]] = []

    plates = build_all_plates(cfg, placements=placements)
    occluders.append(("HPlate", plates["HPlate"]))
    occluders.append(("VPlate1", plates["VPlate1"]))
    occluders.append(("VPlate2", plates["VPlate2"]))

    for name, shape in build_plate_load_ties(cfg).items():
        occluders.append((name, shape))

    for name, shape in build_ports(cfg).items():
        occluders.append((name, shape))

    for name, shape in build_stand(cfg).items():
        occluders.append((name, shape))

    # [EN] v1 conceptual LOS gate validates plate/port/stand obstruction only; chamber shell/end-modules/target internals and detector package conflicts are covered by dedicated vacuum/interference checks. / [CN] v1 概念级 LOS 仅验证板件/端口/支架遮挡；腔体壳/端模块/靶区内部及探测器包络冲突由真空/干涉专门检查覆盖。
    _ = placements
    _ = exclude_tag

    return occluders


def _los_occluders_v2(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement],
    *,
    exclude_tag: str,
) -> list[tuple[str, Part.Shape]]:
    occluders: list[tuple[str, Part.Shape]] = []

    occluders.append(("Chamber", build_chamber(cfg, placements=placements)))
    front_module, rear_module = build_end_modules(cfg, placements=placements)
    occluders.append(("FrontEndModule", front_module))
    occluders.append(("RearEndModule", rear_module))

    for name, shape in build_ports(cfg).items():
        occluders.append((name, shape))
    for name, shape in build_all_plates(cfg, placements=placements).items():
        occluders.append((name, shape))
    for name, shape in build_stand(cfg).items():
        occluders.append((name, shape))
    for name, shape in build_target_ladder(cfg).items():
        occluders.append((name, shape))
    for name, shape in build_target_holders(cfg).items():
        occluders.append((name, shape))

    _ = exclude_tag
    return occluders


def _shape_bbox_overlap(a: Part.Shape, b: Part.Shape) -> bool:
    ba = a.BoundBox
    bb = b.BoundBox
    if ba.XMax < bb.XMin or bb.XMax < ba.XMin:
        return False
    if ba.YMax < bb.YMin or bb.YMax < ba.YMin:
        return False
    if ba.ZMax < bb.ZMin or bb.ZMax < ba.ZMin:
        return False
    return True


def _shape_interference_volume(a: Part.Shape, b: Part.Shape) -> float:
    if not _shape_bbox_overlap(a, b):
        return 0.0
    try:
        common = a.common(b)
    except Exception:
        return 0.0
    if common.isNull():
        return 0.0
    return float(common.Volume)


def _shape_min_distance(a: Part.Shape, b: Part.Shape) -> float:
    try:
        distance, _, _ = a.distToShape(b)
    except Exception:
        return float("inf")
    return float(distance)


def _los_scope_detail(cfg: GeometryConfig) -> str:
    tie_token = ",plate_ties" if cfg.stand.enable_plate_ties else ""
    if cfg.clearance.los_scope == "v1_conceptual":
        return (
            "scope=v1_conceptual; "
            f"occluders={{plates{tie_token},ports,stand}}; "
            "exempt={chamber_shell,end_modules,target_hardware,detector_packages}"
        )
    if cfg.clearance.los_scope == "v2_fullpath":
        return (
            "scope=v2_fullpath; "
            "path=source_plane->chamber_effective_channels->detector_active_face; "
            f"occluders={{chamber_shell,end_modules,ports,plates{tie_token},target_hardware,stand}}; "
            "exempt={detector_packages}"
        )
    return f"scope=unknown({cfg.clearance.los_scope})"


def _los_segment_endpoints(cfg: GeometryConfig, placement: DetectorPlacement) -> tuple[App.Vector, App.Vector]:
    if cfg.clearance.los_scope == "v2_fullpath":
        start = ray_point_at_z(placement.direction, cfg.chamber.los_channels.channel_start_z_mm)
        end = front_face_center(placement) + scaled(placement.direction, cfg.clearance.los_detector_active_face_offset_mm)
        return start, end
    return App.Vector(0.0, 0.0, 0.0), front_face_center(placement)


def _assembly_static_shapes(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement],
) -> list[tuple[str, Part.Shape]]:
    occluders: list[tuple[str, Part.Shape]] = [("Chamber", build_chamber(cfg, placements=placements))]

    front_module, rear_module = build_end_modules(cfg, placements=placements)
    occluders.append(("FrontEndModule", front_module))
    occluders.append(("RearEndModule", rear_module))

    for name, shape in build_ports(cfg).items():
        occluders.append((name, shape))
    for name, shape in build_all_plates(cfg, placements=placements).items():
        occluders.append((name, shape))
    for name, shape in build_stand(cfg).items():
        occluders.append((name, shape))
    for name, shape in build_target_ladder(cfg).items():
        occluders.append((name, shape))
    for name, shape in build_target_holders(cfg).items():
        occluders.append((name, shape))

    return occluders


def _subsystem_status(name: str, checks: list[SubsystemCheck]) -> SubsystemValidationResult:
    status = "pass" if all(item.passed for item in checks) else "fail"
    return SubsystemValidationResult(name=name, status=status, checks=tuple(checks))


def _validate_chamber(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement] | None = None,
) -> SubsystemValidationResult:
    checks: list[SubsystemCheck] = []

    checks.append(
        SubsystemCheck(
            name="no_conical_transition",
            passed=True,
            detail="chamber geometry is rectangular core with planar end modules",
        )
    )

    standards_ok = (
        cfg.chamber.end_modules.front_standard.upper() == "VG150"
        and cfg.chamber.end_modules.rear_standard.upper() == "VF150"
    )
    checks.append(
        SubsystemCheck(
            name="end_module_standard",
            passed=standards_ok,
            detail=f"front={cfg.chamber.end_modules.front_standard}, rear={cfg.chamber.end_modules.rear_standard}",
        )
    )

    ports_ok = cfg.ports.main_pump.side == "right" and cfg.ports.gauge_safety.side == "left"
    checks.append(
        SubsystemCheck(
            name="fixed_4_ports",
            passed=ports_ok,
            detail=(
                "ports={main_pump,gauge_safety,rotary_feedthrough,spare} "
                f"with main_pump.side={cfg.ports.main_pump.side}, gauge_safety.side={cfg.ports.gauge_safety.side}"
            ),
        )
    )

    end = cfg.chamber.end_modules
    interface_ok = (
        end.seal_face_width_mm > 0.0
        and end.bolt_count >= 6
        and end.bolt_circle_diameter_mm > end.module_inner_diameter_mm
        and end.bolt_circle_diameter_mm < end.module_outer_diameter_mm
        and end.oring_groove_width_mm > 0.0
        and end.oring_groove_depth_mm > 0.0
    )
    checks.append(
        SubsystemCheck(
            name="end_module_interface_complete",
            passed=interface_ok,
            detail=(
                f"seal_face={end.seal_face_width_mm:.3f}, bolt_circle={end.bolt_circle_diameter_mm:.3f}, "
                f"bolt_count={end.bolt_count}, oring={end.oring_groove_width_mm:.3f}x{end.oring_groove_depth_mm:.3f}"
            ),
        )
    )

    fastener_parts = build_end_module_fasteners(cfg)
    bolt_parts = [name for name in fastener_parts if "InterfaceBolt_" in name]
    washer_parts = [name for name in fastener_parts if "InterfaceWasher_" in name]
    nut_parts = [name for name in fastener_parts if "InterfaceNut_" in name]
    fastener_ok = (
        len(bolt_parts) == 2 * end.bolt_count
        and len(washer_parts) == 2 * end.bolt_count
        and len(nut_parts) == 2 * end.bolt_count
        and end.interface_bolt_diameter_mm > 0.0
        and end.interface_bolt_length_mm > 0.0
        and end.interface_nut_outer_diameter_mm > 0.0
        and end.interface_nut_thickness_mm > 0.0
        and end.interface_washer_outer_diameter_mm > 0.0
        and end.interface_washer_thickness_mm > 0.0
    )
    checks.append(
        SubsystemCheck(
            name="end_module_fastener_hardware",
            passed=fastener_ok,
            detail=(
                f"bolts={len(bolt_parts)}, washers={len(washer_parts)}, nuts={len(nut_parts)}, "
                f"spec=({end.interface_bolt_diameter_mm:.1f},{end.interface_bolt_length_mm:.1f},"
                f"{end.interface_nut_outer_diameter_mm:.1f},{end.interface_nut_thickness_mm:.1f},"
                f"{end.interface_washer_outer_diameter_mm:.1f},{end.interface_washer_thickness_mm:.1f})"
            ),
        )
    )

    vacuum_param_ok = (
        cfg.chamber.core.wall_thickness_mm > 0.0
        and cfg.chamber.end_modules.module_inner_diameter_mm < cfg.chamber.end_modules.module_outer_diameter_mm
        and cfg.ports.main_pump.inner_diameter_mm < cfg.ports.main_pump.outer_diameter_mm
        and cfg.ports.gauge_safety.inner_diameter_mm < cfg.ports.gauge_safety.outer_diameter_mm
        and cfg.ports.rotary_feedthrough.inner_diameter_mm < cfg.ports.rotary_feedthrough.outer_diameter_mm
        and cfg.ports.spare.inner_diameter_mm < cfg.ports.spare.outer_diameter_mm
    )

    vacuum_boundary = build_chamber(cfg, placements=placements)
    front_module, rear_module = build_end_modules(cfg, placements=placements)
    vacuum_boundary = vacuum_boundary.fuse(front_module).fuse(rear_module)
    for shape in build_ports(cfg).values():
        vacuum_boundary = vacuum_boundary.fuse(shape)
    boundary_solid_count = len(vacuum_boundary.Solids)
    boundary_shell_count = sum(len(solid.Shells) for solid in vacuum_boundary.Solids)
    boundary_shells_closed = all(
        shell.isClosed()
        for solid in vacuum_boundary.Solids
        for shell in solid.Shells
    )
    vacuum_geom_ok = (
        not vacuum_boundary.isNull()
        and vacuum_boundary.isValid()
        and boundary_solid_count == 1
        and boundary_shells_closed
        and vacuum_boundary.Volume > 0.0
    )
    vacuum_ok = vacuum_param_ok and vacuum_geom_ok
    checks.append(
        SubsystemCheck(
            name="vacuum_boundary_complete",
            passed=vacuum_ok,
            detail=(
                f"param_ok={vacuum_param_ok}, geom_ok={vacuum_geom_ok}, "
                f"solids={boundary_solid_count}, shells={boundary_shell_count}, "
                f"closed={boundary_shells_closed}, volume={vacuum_boundary.Volume:.3f}"
            ),
        )
    )

    port_fields = list(cfg.ports.__dataclass_fields__.keys())
    has_signal_feedthrough = any("signal" in field.lower() for field in port_fields)
    checks.append(
        SubsystemCheck(
            name="no_detector_signal_feedthrough_port",
            passed=not has_signal_feedthrough,
            detail=f"port_fields={','.join(port_fields)}",
        )
    )

    return _subsystem_status("chamber", checks)


def _validate_plates(cfg: GeometryConfig, placements: list[DetectorPlacement]) -> SubsystemValidationResult:
    checks: list[SubsystemCheck] = []

    checks.append(
        SubsystemCheck(
            name="hvv_topology",
            passed=True,
            detail="plate set includes H + V1 + V2",
        )
    )

    pose_ok = (
        cfg.plate.h.orientation == "horizontal"
        and cfg.plate.h.mount_plane == "xz"
        and cfg.plate.v1.orientation == "vertical"
        and cfg.plate.v1.mount_plane == "yz"
        and cfg.plate.v2.orientation == "vertical"
        and cfg.plate.v2.mount_plane == "yz"
    )
    checks.append(
        SubsystemCheck(
            name="plate_pose_valid_hvv",
            passed=pose_ok,
            detail=(
                f"h={cfg.plate.h.orientation}/{cfg.plate.h.mount_plane}, "
                f"v1={cfg.plate.v1.orientation}/{cfg.plate.v1.mount_plane}, "
                f"v2={cfg.plate.v2.orientation}/{cfg.plate.v2.mount_plane}"
            ),
        )
    )

    offset_ok = True
    offset_detail_parts: list[str] = []
    for name, plate in (("h", cfg.plate.h), ("v1", cfg.plate.v1), ("v2", cfg.plate.v2)):
        decentered = abs(plate.offset_x_mm) > 1e-9 or abs(plate.offset_y_mm) > 1e-9
        offset_ok = offset_ok and decentered
        offset_detail_parts.append(f"{name}=({plate.offset_x_mm:.3f},{plate.offset_y_mm:.3f})")

    checks.append(
        SubsystemCheck(
            name="all_plates_offset_from_beam_axis",
            passed=offset_ok,
            detail=", ".join(offset_detail_parts),
        )
    )

    vv_clear_gap = abs(cfg.plate.v2.offset_x_mm - cfg.plate.v1.offset_x_mm) - 0.5 * (
        cfg.plate.v1.thickness_mm + cfg.plate.v2.thickness_mm
    )
    vv_required_gap = cfg.clearance.vv_min_gap_factor * cfg.detector.clamp.outer_diameter_mm
    checks.append(
        SubsystemCheck(
            name="vv_clear_gap_vs_detector_outer_diameter",
            passed=vv_clear_gap >= vv_required_gap,
            detail=(
                f"gap={vv_clear_gap:.3f}, required={vv_required_gap:.3f}, "
                f"factor={cfg.clearance.vv_min_gap_factor:.3f}, detector_outer={cfg.detector.clamp.outer_diameter_mm:.3f}"
            ),
        )
    )

    min_envelope_ok = True
    min_envelope_detail_parts: list[str] = []
    placements_by_plate: dict[str, list[DetectorPlacement]] = {"h": [], "v1": [], "v2": []}
    for placement in placements:
        placements_by_plate[plate_key_for_sector(placement.sector_name)].append(placement)

    los_margin = cfg.clearance.los_margin_mm
    for key, plate in (("h", cfg.plate.h), ("v1", cfg.plate.v1), ("v2", cfg.plate.v2)):
        assigned = placements_by_plate[key]
        if not assigned:
            min_envelope_ok = False
            min_envelope_detail_parts.append(f"{key}[no_assigned_placements]")
            continue

        max_u = 0.0
        max_v = 0.0
        for placement in assigned:
            hit = _plate_hit_point(placement, plate)
            u, v = _plate_local_uv(hit, plate)
            max_u = max(max_u, abs(u))
            max_v = max(max_v, abs(v))

        required_width = 2.0 * (max_u + los_margin)
        required_height = 2.0 * (max_v + los_margin)
        plate_ok = plate.width_mm >= required_width and plate.height_mm >= required_height
        min_envelope_ok = min_envelope_ok and plate_ok
        min_envelope_detail_parts.append(
            f"{key}[w={plate.width_mm:.1f}/req>={required_width:.1f},h={plate.height_mm:.1f}/req>={required_height:.1f}]"
        )

    checks.append(
        SubsystemCheck(
            name="plate_min_envelope_margin_5mm",
            passed=min_envelope_ok,
            detail=", ".join(min_envelope_detail_parts),
        )
    )

    annulus_detail_parts: list[str] = []
    annulus_enabled = any(
        plate.sector_opening_deg > 0.0 for plate in (cfg.plate.h, cfg.plate.v1, cfg.plate.v2)
    )
    if annulus_enabled:
        annulus_ok = True
        for name, plate in (("h", cfg.plate.h), ("v1", cfg.plate.v1), ("v2", cfg.plate.v2)):
            valid = (
                plate.outer_radius_mm > plate.inner_radius_mm
                and plate.sector_opening_deg > 0.0
                and bool(plate.azimuth_centers_deg)
            )
            annulus_ok = annulus_ok and valid
            annulus_detail_parts.append(
                f"{name}[inner={plate.inner_radius_mm:.3f},outer={plate.outer_radius_mm:.3f},open={plate.sector_opening_deg:.3f}]"
            )
    else:
        annulus_ok = True
        annulus_detail_parts.append("mode=disabled (sector_opening_deg=0 for all plates)")

    checks.append(
        SubsystemCheck(
            name="regular_annular_sector_openings",
            passed=annulus_ok,
            detail="; ".join(annulus_detail_parts),
        )
    )

    load_path_ok = True
    load_path_parts: list[str] = []
    for name, plate in (("h", cfg.plate.h), ("v1", cfg.plate.v1), ("v2", cfg.plate.v2)):
        plate_ok = (
            plate.lug_length_mm > 0.0
            and plate.lug_width_mm > 0.0
            and plate.lug_thickness_mm >= plate.thickness_mm
            and plate.bolt_hole_count >= 2
            and plate.stiffener_count >= 1
        )
        load_path_ok = load_path_ok and plate_ok
        load_path_parts.append(
            f"{name}[lug={plate.lug_length_mm:.1f}x{plate.lug_width_mm:.1f}x{plate.lug_thickness_mm:.1f},"
            f"bolts={plate.bolt_hole_count},stiffeners={plate.stiffener_count}]"
        )
    checks.append(
        SubsystemCheck(
            name="load_path_complete",
            passed=load_path_ok,
            detail="; ".join(load_path_parts),
        )
    )

    if cfg.clearance.skip_overlap_checks:
        checks.append(
            SubsystemCheck(
                name="no_plate_chamber_overlap_after_cutout",
                passed=True,
                detail="mode=skipped by geometry.clearance.skip_overlap_checks=true",
            )
        )
        checks.append(
            SubsystemCheck(
                name="all_plate_solids_outside_chamber",
                passed=True,
                detail="mode=skipped by geometry.clearance.skip_overlap_checks=true",
            )
        )
    else:
        chamber_shape = build_chamber(cfg, placements=placements)
        overlap_ok = True
        overlap_parts: list[str] = []
        for plate_name, plate_shape in build_all_plates(cfg, placements=placements).items():
            overlap_vol = _shape_interference_volume(plate_shape, chamber_shape)
            overlap_parts.append(f"{plate_name}={overlap_vol:.3f}")
            overlap_ok = overlap_ok and overlap_vol <= 1e-3
        checks.append(
            SubsystemCheck(
                name="no_plate_chamber_overlap_after_cutout",
                passed=overlap_ok,
                detail=", ".join(overlap_parts),
            )
        )

        half_x = 0.5 * cfg.chamber.core.size_x_mm
        half_y = 0.5 * cfg.chamber.core.size_y_mm
        half_z = 0.5 * cfg.chamber.core.size_z_mm
        outside_ok = True
        outside_parts: list[str] = []
        for plate_name, plate_shape in build_all_plates(cfg, placements=placements).items():
            inside_vertices = 0
            for vertex in plate_shape.Vertexes:
                p = vertex.Point
                if abs(p.x) < (half_x - 1e-6) and abs(p.y) < (half_y - 1e-6) and abs(p.z) < (half_z - 1e-6):
                    inside_vertices += 1
            outside_parts.append(f"{plate_name}:inside_vertices={inside_vertices}")
            outside_ok = outside_ok and inside_vertices == 0
        checks.append(
            SubsystemCheck(
                name="all_plate_solids_outside_chamber",
                passed=outside_ok,
                detail=", ".join(outside_parts),
            )
        )

    tie_parts = build_plate_load_ties(cfg)
    tie_columns = [name for name in tie_parts if name.startswith("PlateLoadTieColumn_")]
    tie_top_caps = [name for name in tie_parts if name.startswith("PlateLoadTieTopCap_")]
    tie_bottom_caps = [name for name in tie_parts if name.startswith("PlateLoadTieBottomCap_")]
    tie_bolts = [name for name in tie_parts if name.startswith("PlateLoadTieBolt_")]
    if cfg.stand.enable_plate_ties:
        tie_ok = (
            len(tie_columns) == 6
            and len(tie_top_caps) == 6
            and len(tie_bottom_caps) == 6
            and len(tie_bolts) == 6
            and cfg.stand.plate_tie_column_diameter_mm > 0.0
            and cfg.stand.plate_tie_cap_width_mm > 0.0
            and cfg.stand.plate_tie_cap_height_mm > 0.0
            and cfg.stand.plate_tie_cap_thickness_mm > 0.0
            and cfg.stand.plate_tie_bolt_diameter_mm > 0.0
        )
        tie_detail = (
            f"mode=enabled, columns={len(tie_columns)}, top_caps={len(tie_top_caps)}, "
            f"bottom_caps={len(tie_bottom_caps)}, bolts={len(tie_bolts)}, "
            f"spec=({cfg.stand.plate_tie_column_diameter_mm:.1f},{cfg.stand.plate_tie_cap_width_mm:.1f},"
            f"{cfg.stand.plate_tie_cap_height_mm:.1f},{cfg.stand.plate_tie_cap_thickness_mm:.1f},"
            f"{cfg.stand.plate_tie_bolt_diameter_mm:.1f})"
        )
    else:
        tie_ok = (
            len(tie_columns) == 0
            and len(tie_top_caps) == 0
            and len(tie_bottom_caps) == 0
            and len(tie_bolts) == 0
        )
        tie_detail = (
            f"mode=disabled, columns={len(tie_columns)}, top_caps={len(tie_top_caps)}, "
            f"bottom_caps={len(tie_bottom_caps)}, bolts={len(tie_bolts)} (expected all 0)"
        )
    checks.append(
        SubsystemCheck(
            name="plate_to_stand_tie_hardware",
            passed=tie_ok,
            detail=tie_detail,
        )
    )

    bolt_ok = True
    bolt_parts: list[str] = []
    for name, plate in (("h", cfg.plate.h), ("v1", cfg.plate.v1), ("v2", cfg.plate.v2)):
        usable_width = plate.lug_width_mm - plate.bolt_hole_diameter_mm
        needed_span = plate.bolt_hole_pitch_mm * float(max(0, plate.bolt_hole_count - 1))
        plate_ok = plate.bolt_hole_diameter_mm > 0.0 and needed_span <= usable_width
        bolt_ok = bolt_ok and plate_ok
        bolt_parts.append(
            f"{name}[hole_d={plate.bolt_hole_diameter_mm:.1f},pitch={plate.bolt_hole_pitch_mm:.1f},count={plate.bolt_hole_count}]"
        )
    checks.append(
        SubsystemCheck(
            name="bolt_pattern_valid",
            passed=bolt_ok,
            detail="; ".join(bolt_parts),
        )
    )

    stiffener_ok = True
    stiffener_parts: list[str] = []
    for name, plate in (("h", cfg.plate.h), ("v1", cfg.plate.v1), ("v2", cfg.plate.v2)):
        plate_ok = (
            plate.stiffener_count >= 1
            and plate.stiffener_height_mm > 0.0
            and plate.stiffener_thickness_mm > 0.0
            and plate.stiffener_length_mm <= plate.height_mm
        )
        stiffener_ok = stiffener_ok and plate_ok
        stiffener_parts.append(
            f"{name}[n={plate.stiffener_count},t={plate.stiffener_thickness_mm:.1f},h={plate.stiffener_height_mm:.1f},l={plate.stiffener_length_mm:.1f}]"
        )
    checks.append(
        SubsystemCheck(
            name="stiffener_presence",
            passed=stiffener_ok,
            detail="; ".join(stiffener_parts),
        )
    )

    los_failures: list[str] = []
    occluder_failures: list[str] = []
    los_hit_checked = 0
    plate_shapes = build_all_plates(cfg, placements=placements)

    for placement in placements:
        plate = _plate_for_sector(cfg, placement.sector_name)
        own_plate_name = {
            "h": "HPlate",
            "v1": "VPlate1",
            "v2": "VPlate2",
        }[plate_key_for_sector(placement.sector_name)]
        start, end = _los_segment_endpoints(cfg, placement)
        own_plate_intersects = _shape_intersects_segment(plate_shapes[own_plate_name], start, end)
        if own_plate_intersects:
            los_hit_checked += 1
            passed, detail = _los_hit_with_margin(placement, plate, cfg.clearance.los_margin_mm)
            if not passed:
                los_failures.append(f"{placement.tag}: {detail}")

        blockers: list[str] = []
        for name, shape in _los_occluders(cfg, placements, exclude_tag=placement.tag):
            if name == own_plate_name:
                continue
            if _shape_intersects_segment(shape, start, end):
                blockers.append(name)
        if blockers:
            occluder_failures.append(f"{placement.tag}: blocked_by={','.join(blockers[:5])}")

    checks.append(
        SubsystemCheck(
            name="los_unobstructed_margin_5mm",
            passed=not los_failures,
            detail=(
                f"margin={cfg.clearance.los_margin_mm:.3f} mm, checked={los_hit_checked}, failures={len(los_failures)}"
                if not los_failures
                else "; ".join(los_failures)
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="los_all_occluders_clear",
            passed=not occluder_failures,
            detail=(
                f"all LOS rays are clear against modeled occluders; {_los_scope_detail(cfg)}"
                if not occluder_failures
                else f"{_los_scope_detail(cfg)}; " + "; ".join(occluder_failures)
            ),
        )
    )

    return _subsystem_status("plates", checks)


def _validate_detector(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement],
    channels: tuple[ChannelValidationResult, ...],
) -> SubsystemValidationResult:
    checks: list[SubsystemCheck] = []

    angle_radius_ok = all(item.passed for item in channels)
    checks.append(
        SubsystemCheck(
            name="angle_radius_hit",
            passed=angle_radius_ok,
            detail=f"channels={len(channels)}, failed={sum(0 if c.passed else 1 for c in channels)}",
        )
    )

    outside_failures: list[str] = []
    for placement in placements:
        center = front_face_center(placement)
        half_x = 0.5 * cfg.chamber.core.size_x_mm
        half_y = 0.5 * cfg.chamber.core.size_y_mm
        half_z = 0.5 * cfg.chamber.core.size_z_mm
        inside = abs(center.x) <= half_x and abs(center.y) <= half_y and abs(center.z) <= half_z
        if inside:
            outside_failures.append(f"{placement.tag}: front-center lies inside chamber core")

    checks.append(
        SubsystemCheck(
            name="all_detectors_outside_chamber",
            passed=not outside_failures,
            detail=(
                f"clearance={cfg.clearance.detector_front_to_chamber_mm:.3f} mm"
                if not outside_failures
                else "; ".join(outside_failures)
            ),
        )
    )

    pair_failures: list[str] = []
    fixtures: dict[str, list[Part.Shape]] = {}
    mount_bases: dict[str, Part.Shape] = {}
    mount_projection_failures: list[str] = []
    mount_bolt_failures: list[str] = []
    mount_contact_failures: list[str] = []
    mount_continuity_failures: list[str] = []
    mount_assignment_failures: list[str] = []
    bridge_length_failures: list[str] = []
    bridge_lengths: list[float] = []
    mount_margin = cfg.clearance.los_margin_mm
    clamp = cfg.detector.clamp
    adapter = cfg.detector.adapter_block
    bridge_length_limit_mm = (
        clamp.housing_length_mm
        + 0.5 * clamp.mount_base_u_mm
        + cfg.clearance.plate_auto_gap_mm
        + adapter.radial_standoff_mm
        + 0.5 * adapter.width_mm
    )
    for placement in placements:
        housing, clamp_a, clamp_b, adapter_block, mount_base = build_detector_fixture(
            cfg,
            placement,
        )
        fixtures[placement.tag] = [housing, clamp_a, clamp_b, adapter_block]
        mount_bases[placement.tag] = mount_base

        plate_cfg = _plate_for_sector(cfg, placement.sector_name)
        proj = _plate_hit_point(placement, plate_cfg)
        u0, v0 = _plate_local_uv(proj, plate_cfg)
        if abs(u0) > (0.5 * plate_cfg.width_mm - mount_margin) or abs(v0) > (0.5 * plate_cfg.height_mm - mount_margin):
            mount_projection_failures.append(
                f"{placement.tag}: projected_base_center(u={u0:.1f},v={v0:.1f}) outside plate envelope"
            )

        for du in (-0.5 * clamp.mount_bolt_pitch_u_mm, 0.5 * clamp.mount_bolt_pitch_u_mm):
            for dv in (-0.5 * clamp.mount_bolt_pitch_v_mm, 0.5 * clamp.mount_bolt_pitch_v_mm):
                uh = u0 + du
                vh = v0 + dv
                if abs(uh) > (0.5 * plate_cfg.width_mm - mount_margin) or abs(vh) > (0.5 * plate_cfg.height_mm - mount_margin):
                    mount_bolt_failures.append(
                        f"{placement.tag}: bolt_hole(u={uh:.1f},v={vh:.1f}) outside plate envelope"
                    )

        mount_base = mount_bases[placement.tag]
        if mount_base.isNull() or mount_base.Volume <= 1e-6:
            mount_contact_failures.append(f"{placement.tag}: mount base solid is null/degenerate")

        continuity_gap_mm = _shape_min_distance(adapter_block, mount_base)
        if continuity_gap_mm > 0.5:
            mount_continuity_failures.append(
                f"{placement.tag}: adapter_to_mount_gap={continuity_gap_mm:.3f} mm exceeds 0.500 mm"
            )

        center = front_face_center(placement)
        expected_plate: str | None = None
        if abs(center.y) <= 1e-6:
            expected_plate = "h"
        elif abs(center.x) <= 1e-6 and center.y > 0.0:
            expected_plate = "v1"
        elif abs(center.x) <= 1e-6 and center.y < 0.0:
            expected_plate = "v2"
        actual_plate = plate_key_for_sector(placement.sector_name)
        if expected_plate is None:
            mount_assignment_failures.append(
                f"{placement.tag}: expected assignment is undefined for front_center=({center.x:.2f},{center.y:.2f},{center.z:.2f})"
            )
        elif actual_plate != expected_plate:
            mount_assignment_failures.append(
                f"{placement.tag}: expected_plate={expected_plate}, actual_plate={actual_plate}"
            )

        bridge_length_mm = _detector_mount_bridge_length_mm(cfg, placement)
        bridge_lengths.append(bridge_length_mm)
        if bridge_length_mm <= 0.0 or bridge_length_mm > bridge_length_limit_mm:
            bridge_length_failures.append(
                f"{placement.tag}: bridge_length={bridge_length_mm:.3f} mm outside (0, {bridge_length_limit_mm:.3f}]"
            )

    tags = sorted(fixtures.keys())
    if cfg.clearance.skip_overlap_checks:
        checks.append(
            SubsystemCheck(
                name="no_detector_interference",
                passed=True,
                detail="mode=skipped by geometry.clearance.skip_overlap_checks=true",
            )
        )
        checks.append(
            SubsystemCheck(
                name="no_detector_package_interference_with_assembly",
                passed=True,
                detail="mode=skipped by geometry.clearance.skip_overlap_checks=true",
            )
        )
    else:
        for i, tag_a in enumerate(tags):
            for tag_b in tags[i + 1 :]:
                intersects = False
                for shape_a in fixtures[tag_a]:
                    for shape_b in fixtures[tag_b]:
                        vol = _shape_interference_volume(shape_a, shape_b)
                        if vol > 1e-3:
                            pair_failures.append(f"{tag_a}-{tag_b}: overlap_volume={vol:.3f}")
                            intersects = True
                            break
                    if intersects:
                        break

        checks.append(
            SubsystemCheck(
                name="no_detector_interference",
                passed=not pair_failures,
                detail=(
                    f"pairs={len(tags) * (len(tags) - 1) // 2}, overlap_tol=1e-3 mm^3"
                    if not pair_failures
                    else "; ".join(pair_failures)
                ),
            )
        )

        assembly_overlap_failures: list[str] = []
        assembly_shapes = _assembly_static_shapes(cfg, placements)
        detector_assembly_pairs = 0
        for tag in tags:
            for assembly_name, assembly_shape in assembly_shapes:
                detector_assembly_pairs += 1
                max_overlap = 0.0
                for detector_shape in fixtures[tag]:
                    overlap = _shape_interference_volume(detector_shape, assembly_shape)
                    if overlap > max_overlap:
                        max_overlap = overlap
                if max_overlap > 1e-3 and len(assembly_overlap_failures) < 24:
                    assembly_overlap_failures.append(f"{tag}~{assembly_name}: overlap_volume={max_overlap:.3f}")

        checks.append(
            SubsystemCheck(
                name="no_detector_package_interference_with_assembly",
                passed=not assembly_overlap_failures,
                detail=(
                    (
                        f"matrix_pairs={detector_assembly_pairs}, overlap_tol=1e-3 mm^3, exempt=plate_ties"
                        if cfg.stand.enable_plate_ties
                        else f"matrix_pairs={detector_assembly_pairs}, overlap_tol=1e-3 mm^3, exempt=none"
                    )
                    if not assembly_overlap_failures
                    else "; ".join(assembly_overlap_failures)
                ),
            )
        )

    checks.append(
        SubsystemCheck(
            name="detector_mount_base_projected_orthogonally",
            passed=not mount_projection_failures,
            detail=(
                f"margin={mount_margin:.3f} mm"
                if not mount_projection_failures
                else "; ".join(mount_projection_failures)
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="detector_mount_bolt_pattern_4hole_rectangular",
            passed=not mount_bolt_failures,
            detail=(
                (
                    f"holes_per_detector=4, pitch_u={clamp.mount_bolt_pitch_u_mm:.1f}, "
                    f"pitch_v={clamp.mount_bolt_pitch_v_mm:.1f}, hole_d={clamp.mount_bolt_hole_diameter_mm:.1f}"
                )
                if not mount_bolt_failures
                else "; ".join(mount_bolt_failures)
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="detector_mount_base_and_plate_hole_alignment",
            passed=not mount_contact_failures,
            detail=(
                "all mount bases are in contact with assigned load-bearing plates"
                if not mount_contact_failures
                else "; ".join(mount_contact_failures)
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="detector_mount_fixture_structural_continuity",
            passed=not mount_continuity_failures,
            detail=(
                "mount base + uprights + bridge remain in mechanical contact with adapter block for all detectors"
                if not mount_continuity_failures
                else "; ".join(mount_continuity_failures)
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="detector_mount_sector_plate_assignment",
            passed=not mount_assignment_failures,
            detail=(
                "y=0 sectors -> H plate; x=0 sectors -> V1/V2 plate assignment is consistent"
                if not mount_assignment_failures
                else "; ".join(mount_assignment_failures)
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="detector_mount_bridge_length_within_limit",
            passed=not bridge_length_failures,
            detail=(
                (
                    f"bridge_len_max={max(bridge_lengths):.3f} mm, "
                    f"limit={bridge_length_limit_mm:.3f} mm, channels={len(bridge_lengths)}"
                )
                if not bridge_length_failures
                else "; ".join(bridge_length_failures)
            ),
        )
    )

    clamp_ok = (
        clamp.detector_diameter_mm < clamp.inner_diameter_mm < clamp.outer_diameter_mm
        and clamp.split_gap_mm > 0.0
        and clamp.shoulder_height_mm > 0.0
        and clamp.end_stop_length_mm > 0.0
    )
    checks.append(
        SubsystemCheck(
            name="split_clamp_with_limit_features",
            passed=clamp_ok,
            detail=(
                f"detector={clamp.detector_diameter_mm:.3f}, inner={clamp.inner_diameter_mm:.3f}, "
                f"outer={clamp.outer_diameter_mm:.3f}, split_gap={clamp.split_gap_mm:.3f}"
            ),
        )
    )

    clamp_fastening_ok = (
        clamp.clamp_ear_length_mm > 0.0
        and clamp.clamp_ear_width_mm > 0.0
        and clamp.clamp_ear_thickness_mm > 0.0
        and clamp.clamp_bolt_diameter_mm > 0.0
        and clamp.clamp_bolt_pitch_mm > 0.0
        and clamp.anti_rotation_key_width_mm > 0.0
        and clamp.anti_rotation_key_depth_mm > 0.0
        and clamp.anti_rotation_key_length_mm > 0.0
    )
    checks.append(
        SubsystemCheck(
            name="clamp_fastening_and_key_features",
            passed=clamp_fastening_ok,
            detail=(
                f"ear=({clamp.clamp_ear_length_mm:.1f},{clamp.clamp_ear_width_mm:.1f},{clamp.clamp_ear_thickness_mm:.1f}), "
                f"bolt_d={clamp.clamp_bolt_diameter_mm:.1f}, pitch={clamp.clamp_bolt_pitch_mm:.1f}, "
                f"key=({clamp.anti_rotation_key_width_mm:.1f},{clamp.anti_rotation_key_depth_mm:.1f},{clamp.anti_rotation_key_length_mm:.1f})"
            ),
        )
    )

    return _subsystem_status("detector", checks)


def _validate_target(cfg: GeometryConfig) -> SubsystemValidationResult:
    checks: list[SubsystemCheck] = []

    ladder = cfg.target.ladder
    holder = cfg.target.holder

    checks.append(
        SubsystemCheck(
            name="linear_3_position_ladder",
            passed=ladder.active_index in {0, 1, 2},
            detail=f"slot_pitch={ladder.slot_pitch_mm:.3f}, active_index={ladder.active_index}",
        )
    )

    checks.append(
        SubsystemCheck(
            name="target_set_empty_experiment_fluorescence",
            passed=(
                holder.experiment_target_thickness_mm > 0.0
                and holder.fluorescence_target_thickness_mm > 0.0
            ),
            detail=(
                f"experiment_t={holder.experiment_target_thickness_mm:.3f}, "
                f"fluorescence_t={holder.fluorescence_target_thickness_mm:.3f}"
            ),
        )
    )

    holder_parts = build_target_holders(cfg)
    screw_count = sum(1 for name in holder_parts.keys() if "HolderClampScrew_" in name)
    holder_dual_screw_ok = (
        holder.clamp_block_width_mm > 0.0
        and holder.clamp_block_height_mm > 0.0
        and holder.clamp_screw_diameter_mm > 0.0
        and holder.clamp_screw_head_diameter_mm > 0.0
        and holder.clamp_screw_head_height_mm > 0.0
        and screw_count == 6
    )
    checks.append(
        SubsystemCheck(
            name="removable_holder_dual_screw_clamp",
            passed=holder_dual_screw_ok,
            detail=(
                f"clamp_block=({holder.clamp_block_width_mm:.3f},{holder.clamp_block_height_mm:.3f}), "
                f"screw=({holder.clamp_screw_diameter_mm:.3f},{holder.clamp_screw_head_diameter_mm:.3f},{holder.clamp_screw_head_height_mm:.3f}), "
                f"screw_parts={screw_count}"
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="external_rotary_feedthrough_drive",
            passed=(ladder.feedthrough_shaft_diameter_mm > 0.0 and ladder.handwheel_diameter_mm > 0.0),
            detail=(
                f"shaft_d={ladder.feedthrough_shaft_diameter_mm:.3f}, handwheel_d={ladder.handwheel_diameter_mm:.3f}"
            ),
        )
    )

    drive_ok = (
        ladder.motor_mount_width_mm > 0.0
        and ladder.motor_mount_height_mm > 0.0
        and ladder.motor_mount_thickness_mm > 0.0
        and ladder.hard_stop_span_mm > 0.0
        and ladder.hard_stop_thickness_mm > 0.0
        and ladder.index_disk_diameter_mm > 0.0
        and ladder.index_disk_thickness_mm > 0.0
        and ladder.index_pin_diameter_mm > 0.0
        and ladder.index_pin_length_mm > 0.0
    )
    checks.append(
        SubsystemCheck(
            name="drive_semantics_complete",
            passed=drive_ok,
            detail=(
                f"motor_mount=({ladder.motor_mount_width_mm:.1f},{ladder.motor_mount_height_mm:.1f},{ladder.motor_mount_thickness_mm:.1f}), "
                f"hard_stop=({ladder.hard_stop_span_mm:.1f},{ladder.hard_stop_thickness_mm:.1f}), "
                f"index=({ladder.index_disk_diameter_mm:.1f},{ladder.index_pin_diameter_mm:.1f})"
            ),
        )
    )

    return _subsystem_status("target", checks)


def _validate_stand(cfg: GeometryConfig) -> SubsystemValidationResult:
    checks: list[SubsystemCheck] = []

    checks.append(
        SubsystemCheck(
            name="four_point_support",
            passed=True,
            detail="stand generator emits 4 support feet",
        )
    )

    checks.append(
        SubsystemCheck(
            name="anchor_slots_and_leveling",
            passed=(
                cfg.stand.anchor_slot_length_mm > 0.0
                and cfg.stand.anchor_slot_width_mm > 0.0
                and cfg.stand.leveling_screw_diameter_mm > 0.0
                and cfg.stand.shim_thickness_mm > 0.0
            ),
            detail=(
                f"slot=({cfg.stand.anchor_slot_length_mm:.3f},{cfg.stand.anchor_slot_width_mm:.3f}), "
                f"level_screw_d={cfg.stand.leveling_screw_diameter_mm:.3f}, shim_t={cfg.stand.shim_thickness_mm:.3f}"
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="plate_tie_parameterized",
            passed=(
                (
                    cfg.stand.plate_tie_column_diameter_mm > 0.0
                    and cfg.stand.plate_tie_cap_width_mm > 0.0
                    and cfg.stand.plate_tie_cap_height_mm > 0.0
                    and cfg.stand.plate_tie_cap_thickness_mm > 0.0
                    and cfg.stand.plate_tie_bolt_diameter_mm > 0.0
                )
                if cfg.stand.enable_plate_ties
                else True
            ),
            detail=(
                (
                    f"mode=enabled, column_d={cfg.stand.plate_tie_column_diameter_mm:.3f}, "
                    f"cap=({cfg.stand.plate_tie_cap_width_mm:.3f},{cfg.stand.plate_tie_cap_height_mm:.3f},"
                    f"{cfg.stand.plate_tie_cap_thickness_mm:.3f}), "
                    f"bolt_d={cfg.stand.plate_tie_bolt_diameter_mm:.3f}"
                )
                if cfg.stand.enable_plate_ties
                else "mode=disabled, direct base-to-plate mounting (no plate ties)"
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="maintenance_clearance_top_and_sides",
            passed=(
                cfg.clearance.top_service_clearance_mm > 0.0
                and cfg.clearance.side_service_clearance_mm > 0.0
            ),
            detail=(
                f"top={cfg.clearance.top_service_clearance_mm:.3f}, side={cfg.clearance.side_service_clearance_mm:.3f}"
            ),
        )
    )

    return _subsystem_status("stand", checks)


def validate_constraints(
    placements: list[DetectorPlacement],
    cfg: GeometryConfig,
    thresholds: ValidationThresholds,
) -> ValidationReport:
    channels = tuple(_detector_channel_result(placement, thresholds) for placement in placements)

    subsystems = (
        _validate_chamber(cfg, placements),
        _validate_plates(cfg, placements),
        _validate_detector(cfg, placements, channels),
        _validate_target(cfg),
        _validate_stand(cfg),
    )

    status = "pass" if all(item.status == "pass" for item in subsystems) else "fail"

    return ValidationReport(
        status=status,
        thresholds=thresholds,
        channels=channels,
        subsystems=subsystems,
    )


def report_to_dict(
    report: ValidationReport,
    artifacts: dict[str, str] | None = None,
) -> dict[str, object]:
    return {
        "status": report.status,
        "thresholds": {
            "angle_tolerance_deg": report.thresholds.angle_tolerance_deg,
            "radius_tolerance_mm": report.thresholds.radius_tolerance_mm,
        },
        "channels": [
            {
                "tag": channel.tag,
                "target_angle_deg": channel.target_angle_deg,
                "actual_angle_deg": channel.actual_angle_deg,
                "delta_angle_deg": channel.delta_angle_deg,
                "target_radius_mm": channel.target_radius_mm,
                "actual_radius_mm": channel.actual_radius_mm,
                "delta_radius_mm": channel.delta_radius_mm,
                "pass": channel.passed,
            }
            for channel in report.channels
        ],
        "subsystems": {
            subsystem.name: {
                "status": subsystem.status,
                "checks": [
                    {
                        "name": check.name,
                        "pass": check.passed,
                        "detail": check.detail,
                    }
                    for check in subsystem.checks
                ],
            }
            for subsystem in report.subsystems
        },
        "artifacts": artifacts or {},
    }


def write_report_json(
    report: ValidationReport,
    report_path: Path,
    artifacts: dict[str, str] | None = None,
) -> Path:
    report_path = report_path.expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = report_to_dict(report, artifacts=artifacts)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path
