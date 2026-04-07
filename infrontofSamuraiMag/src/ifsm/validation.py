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
    build_rotary_feedthrough_vendor_reference,
    build_stand,
    build_single_rotary_target_shapes,
    build_target_holders,
    build_target_ladder,
    chamber_support_centers,
    detector_fixture_geometry,
    h_plate_support_centers,
    plate_los_plane_hit_point,
    plate_opening_local_polylines,
    plate_slot_half_width_mm,
    rotary_port_interface_geometry,
    single_rotary_target_center,
    stand_support_centers,
    target_detector_front_face_cone,
    target_detector_los_tube,
)
from .config import ChamberCoreConfig, GeometryConfig, PlateConfig
from .layout import DetectorPlacement, chamber_z_bounds, front_face_center, norm, plate_key_for_sector, ray_point_at_z, scaled


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
    # [EN] Scattering angle is measured from the +z beam axis, so the detector front-center z projection determines cos(theta). / [CN] 散射角相对 +z 束轴定义，因此探测器前端面中心在 z 方向的投影直接决定 cos(theta)。
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


def _ray_box_exit_faces(core: ChamberCoreConfig, direction: App.Vector) -> tuple[str, ...]:
    half_x = 0.5 * core.size_x_mm
    half_y = 0.5 * core.size_y_mm
    z_min, z_max = chamber_z_bounds(core)

    candidates: list[tuple[float, str]] = []
    if abs(direction.x) > 1e-12:
        candidates.append((half_x / abs(direction.x), "+x" if direction.x > 0.0 else "-x"))
    if abs(direction.y) > 1e-12:
        candidates.append((half_y / abs(direction.y), "+y" if direction.y > 0.0 else "-y"))
    if abs(direction.z) > 1e-12:
        candidates.append((((z_max / direction.z) if direction.z > 0.0 else (z_min / direction.z)), "+z" if direction.z > 0.0 else "-z"))
    if not candidates:
        raise ValueError("ray direction must have at least one non-zero component")

    # [EN] Compare parametric ray distances to each slab; the minimum identifies the first chamber face the channel can escape through. / [CN] 比较射线到各组平板的参数距离，最小者就是该通道首先能够穿出的腔体面。
    t_min = min(t for t, _ in candidates)
    return tuple(face for t, face in candidates if abs(t - t_min) <= 1e-9)


def _expected_exit_face_for_sector(sector_name: str) -> str:
    if sector_name == "left":
        return "-x"
    if sector_name == "right":
        return "+x"
    if sector_name == "up":
        return "+y"
    if sector_name == "down":
        return "-y"
    raise ValueError(f"unsupported sector_name {sector_name!r}")


def _end_module_has_groove(standard: str) -> bool:
    return standard.upper().startswith("VG")


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


def _point_segment_distance_2d(
    point_uv: tuple[float, float],
    start_uv: tuple[float, float],
    end_uv: tuple[float, float],
) -> float:
    px, py = point_uv
    x0, y0 = start_uv
    x1, y1 = end_uv
    dx = x1 - x0
    dy = y1 - y0
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-12:
        return math.hypot(px - x0, py - y0)
    t = _clamp(((px - x0) * dx + (py - y0) * dy) / length_sq, 0.0, 1.0)
    proj_x = x0 + t * dx
    proj_y = y0 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _point_polyline_distance_2d(
    point_uv: tuple[float, float],
    polyline_uv: tuple[tuple[float, float], ...],
) -> float:
    if len(polyline_uv) == 1:
        return math.hypot(point_uv[0] - polyline_uv[0][0], point_uv[1] - polyline_uv[0][1])
    return min(
        _point_segment_distance_2d(point_uv, start_uv, end_uv)
        for start_uv, end_uv in zip(polyline_uv, polyline_uv[1:])
    )


def _normalize_vector(v: App.Vector) -> App.Vector:
    n = _vector_length(v)
    if n <= 1e-12:
        raise ValueError("cannot normalize near-zero vector")
    return App.Vector(v.x / n, v.y / n, v.z / n)


def _dot(a: App.Vector, b: App.Vector) -> float:
    return (a.x * b.x) + (a.y * b.y) + (a.z * b.z)


def _detector_mount_bridge_length_mm(cfg: GeometryConfig, placement: DetectorPlacement) -> float:
    return detector_fixture_geometry(cfg, placement).upright_length_mm


def _detector_bridge_pose_signature(cfg: GeometryConfig, placement: DetectorPlacement) -> tuple[float, float, float]:
    layout = detector_fixture_geometry(cfg, placement)
    delta = layout.bridge_center - layout.front_center
    return (
        _dot(delta, layout.direction),
        _dot(delta, layout.mount_axis),
        _dot(delta, layout.mount_lateral_axis),
    )


def _detector_mount_direction_alignment_deg(cfg: GeometryConfig, placement: DetectorPlacement) -> float:
    layout = detector_fixture_geometry(cfg, placement)
    projected = layout.direction - scaled(layout.plate_normal, _dot(layout.direction, layout.plate_normal))
    projected = _normalize_vector(projected)
    cos_angle = _clamp(_dot(projected, layout.base_u_axis), -1.0, 1.0)
    return math.degrees(math.acos(cos_angle))


def _los_hit_with_margin(
    cfg: GeometryConfig,
    placement: DetectorPlacement,
    plate_key: str,
    plate: PlateConfig,
    assigned_placements: list[DetectorPlacement],
    margin_mm: float,
    plate_shape: Part.Shape | None = None,
) -> tuple[bool, str]:
    # [EN] Opening validation is geometry-driven: test the actual LOS corridor plus clearance margin against the generated plate solid instead of trusting configuration metadata alone. / [CN] 开孔校验基于几何本身：把真实 LOS 走廊连同净空裕量与生成后的板件实体相测，而不是只信任配置元数据。
    if plate.opening_style == "los_tube":
        if plate_shape is None:
            return False, "los_tube validation requires plate_shape"
        los_tube = target_detector_los_tube(cfg, placement, 0.5 * cfg.chamber.los_channels.channel_diameter_mm + margin_mm)
        if los_tube is None:
            return False, "target_detector_los_tube is degenerate"
        overlap_volume = _shape_interference_volume(plate_shape, los_tube)
        plane_hit = plate_los_plane_hit_point(cfg, placement, plate)
        if plane_hit is None:
            if overlap_volume <= 1e-3:
                return True, (
                    f"tube_radius={0.5 * cfg.chamber.los_channels.channel_diameter_mm + margin_mm:.3f} "
                    f"plane_hit=none overlap_volume={overlap_volume:.6f}"
                )
            return False, (
                f"tube_radius={0.5 * cfg.chamber.los_channels.channel_diameter_mm + margin_mm:.3f} "
                f"plane_hit=none overlap_volume={overlap_volume:.6f}"
            )

        u, v = _plate_local_uv(plane_hit, plate)
        if overlap_volume <= 1e-3:
            return True, (
                f"u={u:.3f} v={v:.3f} tube_radius={0.5 * cfg.chamber.los_channels.channel_diameter_mm + margin_mm:.3f} "
                f"overlap_volume={overlap_volume:.6f}"
            )
        return False, (
            f"u={u:.3f} v={v:.3f} tube_radius={0.5 * cfg.chamber.los_channels.channel_diameter_mm + margin_mm:.3f} "
            f"overlap_volume={overlap_volume:.6f}"
        )

    hit = _plate_hit_point(placement, plate)
    u, v = _plate_local_uv(hit, plate)

    if abs(u) > (0.5 * plate.width_mm - margin_mm):
        return False, f"|u|={abs(u):.3f} exceeds width margin at plate {plate.orientation}/{plate.mount_plane}"
    if abs(v) > (0.5 * plate.height_mm - margin_mm):
        return False, f"|v|={abs(v):.3f} exceeds height margin at plate {plate.orientation}/{plate.mount_plane}"

    if plate.opening_style == "rounded_slot":
        polylines = plate_opening_local_polylines(cfg, plate_key, plate, assigned_placements)
        if not polylines:
            return False, "rounded_slot opening has no generated centerline polylines"
        slot_half_width = plate_slot_half_width_mm(cfg)
        allowed_distance = slot_half_width - margin_mm
        if allowed_distance < 0.0:
            return False, f"slot_half_width={slot_half_width:.3f} is smaller than required margin={margin_mm:.3f}"

        min_distance = min(_point_polyline_distance_2d((u, v), polyline) for polyline in polylines)
        if min_distance <= allowed_distance + 1e-6:
            return True, (
                f"u={u:.3f} v={v:.3f} slot_half_width={slot_half_width:.3f} "
                f"centerline_distance={min_distance:.3f}"
            )
        return False, (
            f"u={u:.3f} v={v:.3f} slot_half_width={slot_half_width:.3f} "
            f"centerline_distance={min_distance:.3f} exceeds allowed={allowed_distance:.3f}"
        )

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
    # [EN] OCC can report a non-empty common solid for near-miss shell interactions, so reject pairs with finite separation before trusting boolean overlap volume. / [CN] OCC 在近邻壳体布尔运算中可能给出伪公共体，因此先用实体最小距离过滤，再信任布尔重叠体积。
    if _shape_min_distance(a, b) > 1e-6:
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
            "path=source_plane->detector_active_face; "
            "chamber_opening=cone_to_detector_front_face_circle; "
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
            detail="chamber geometry is rectangular core with welded pipe-stub end modules and planar flange interfaces",
        )
    )

    front_module = cfg.chamber.end_modules.front
    rear_module = cfg.chamber.end_modules.rear

    standards_ok = (
        front_module.standard.upper() == cfg.chamber.contract.front_standard.upper()
        and rear_module.standard.upper() == cfg.chamber.contract.rear_standard.upper()
    )
    checks.append(
        SubsystemCheck(
            name="end_module_standard",
            passed=standards_ok,
            detail=f"front={front_module.standard}, rear={rear_module.standard}",
        )
    )

    type_semantics_ok = (
        (_end_module_has_groove(front_module.standard) and front_module.oring_groove_depth_mm > 0.0)
        or (not _end_module_has_groove(front_module.standard) and front_module.oring_groove_depth_mm <= 0.0)
    ) and (
        (_end_module_has_groove(rear_module.standard) and rear_module.oring_groove_depth_mm > 0.0)
        or (not _end_module_has_groove(rear_module.standard) and rear_module.oring_groove_depth_mm <= 0.0)
    )
    checks.append(
        SubsystemCheck(
            name="end_module_type_semantics",
            passed=type_semantics_ok,
            detail=(
                f"front={front_module.standard}[groove_depth={front_module.oring_groove_depth_mm:.3f}], "
                f"rear={rear_module.standard}[groove_depth={rear_module.oring_groove_depth_mm:.3f}]"
            ),
        )
    )

    enabled_port_names = tuple(
        name
        for name, port in (
            ("main_pump", cfg.ports.main_pump),
            ("gauge_safety", cfg.ports.gauge_safety),
            ("rotary_feedthrough", cfg.ports.rotary_feedthrough),
            ("spare", cfg.ports.spare),
        )
        if port.enabled
    )
    required_ports = tuple(cfg.chamber.contract.required_ports_enabled)
    forbidden_ports = tuple(cfg.chamber.contract.forbidden_ports_enabled)
    ports_ok = all(name in enabled_port_names for name in required_ports) and all(
        name not in enabled_port_names for name in forbidden_ports
    )
    checks.append(
        SubsystemCheck(
            name="port_contract",
            passed=ports_ok,
            detail=(
                f"enabled={enabled_port_names}, required={required_ports}, forbidden={forbidden_ports}"
            ),
        )
    )

    rotary_mount = rotary_port_interface_geometry(cfg)
    rotary_mount_expected = cfg.chamber.contract.rotary_mount_standard
    rotary_mount_ok = (
        rotary_mount_expected is None
        or (
            cfg.ports.rotary_feedthrough.enabled
            and cfg.ports.rotary_feedthrough.interface is not None
            and cfg.ports.rotary_feedthrough.interface.standard.upper() == rotary_mount_expected.upper()
            and rotary_mount is not None
        )
    )
    rotary_detail = "none"
    if cfg.ports.rotary_feedthrough.interface is not None:
        rotary_detail = cfg.ports.rotary_feedthrough.interface.standard
    checks.append(
        SubsystemCheck(
            name="rotary_mount_standard",
            passed=rotary_mount_ok,
            detail=f"expected={rotary_mount_expected}, actual={rotary_detail}",
        )
    )

    pipe_stub_ok = True
    pipe_stub_parts: list[str] = []
    for side_name, module in (("front", front_module), ("rear", rear_module)):
        side_ok = (
            module.pipe_length_mm > 0.0
            and module.pipe_inner_diameter_mm >= cfg.beamline.inlet_diameter_mm
            and module.pipe_outer_diameter_mm <= module.module_inner_diameter_mm
        )
        pipe_stub_ok = pipe_stub_ok and side_ok
        pipe_stub_parts.append(
            f"{side_name}[pipe_od={module.pipe_outer_diameter_mm:.1f},pipe_id={module.pipe_inner_diameter_mm:.1f},pipe_len={module.pipe_length_mm:.1f}]"
        )
    checks.append(
        SubsystemCheck(
            name="welded_pipe_stub_to_standard_flange",
            passed=pipe_stub_ok,
            detail="; ".join(pipe_stub_parts),
        )
    )

    exit_failures: list[str] = []
    if placements:
        for placement in placements:
            actual_faces = _ray_box_exit_faces(cfg.chamber.core, placement.direction)
            expected_face = _expected_exit_face_for_sector(placement.sector_name)
            if actual_faces != (expected_face,):
                exit_failures.append(
                    f"{placement.tag}: expected={expected_face}, actual={','.join(actual_faces)}"
                )
    checks.append(
        SubsystemCheck(
            name="channel_first_exit_face_by_sector",
            passed=not exit_failures,
            detail=(
                "left/right/up/down rays exit via -x/+x/+y/-y side walls before +z"
                if not exit_failures
                else "; ".join(exit_failures)
            ),
        )
    )

    interface_ok = True
    interface_parts: list[str] = []
    for side_name, module in (("front", front_module), ("rear", rear_module)):
        side_ok = (
            module.seal_face_width_mm > 0.0
            and module.bolt_count >= 4
            and module.bolt_circle_diameter_mm > module.module_inner_diameter_mm
            and module.bolt_circle_diameter_mm < module.module_outer_diameter_mm
            and module.flange_bolt_hole_diameter_mm > module.interface_bolt_diameter_mm
        )
        if _end_module_has_groove(module.standard):
            side_ok = side_ok and module.oring_groove_depth_mm > 0.0
        else:
            side_ok = side_ok and module.oring_groove_depth_mm <= 0.0
        interface_ok = interface_ok and side_ok
        groove_detail = (
            f"groove={module.oring_groove_inner_diameter_mm:.1f}-{module.oring_groove_outer_diameter_mm:.1f}x{module.oring_groove_depth_mm:.1f}"
            if _end_module_has_groove(module.standard)
            else "groove=none"
        )
        interface_parts.append(
            f"{side_name}[std={module.standard},od={module.module_outer_diameter_mm:.1f},id={module.module_inner_diameter_mm:.1f},"
            f"pipe=({module.pipe_outer_diameter_mm:.1f},{module.pipe_inner_diameter_mm:.1f},{module.pipe_length_mm:.1f}),"
            f"bc={module.bolt_circle_diameter_mm:.1f},n={module.bolt_count},{groove_detail}]"
        )
    checks.append(
        SubsystemCheck(
            name="end_module_interface_complete",
            passed=interface_ok,
            detail="; ".join(interface_parts),
        )
    )

    fastener_parts = build_end_module_fasteners(cfg)
    bolt_parts = [name for name in fastener_parts if "InterfaceBolt_" in name]
    washer_parts = [name for name in fastener_parts if "InterfaceWasher_" in name]
    nut_parts = [name for name in fastener_parts if "InterfaceNut_" in name]
    total_bolt_count = front_module.bolt_count + rear_module.bolt_count
    fastener_ok = (
        len(bolt_parts) == total_bolt_count
        and len(washer_parts) == total_bolt_count
        and len(nut_parts) == total_bolt_count
        and front_module.interface_bolt_diameter_mm > 0.0
        and rear_module.interface_bolt_diameter_mm > 0.0
    )
    checks.append(
        SubsystemCheck(
            name="end_module_fastener_hardware",
            passed=fastener_ok,
            detail=(
                f"bolts={len(bolt_parts)}, washers={len(washer_parts)}, nuts={len(nut_parts)}, "
                f"front_spec=({front_module.interface_bolt_diameter_mm:.1f},{front_module.interface_bolt_length_mm:.1f},"
                f"{front_module.interface_nut_outer_diameter_mm:.1f},{front_module.interface_nut_thickness_mm:.1f},"
                f"{front_module.interface_washer_outer_diameter_mm:.1f},{front_module.interface_washer_thickness_mm:.1f}), "
                f"rear_spec=({rear_module.interface_bolt_diameter_mm:.1f},{rear_module.interface_bolt_length_mm:.1f},"
                f"{rear_module.interface_nut_outer_diameter_mm:.1f},{rear_module.interface_nut_thickness_mm:.1f},"
                f"{rear_module.interface_washer_outer_diameter_mm:.1f},{rear_module.interface_washer_thickness_mm:.1f})"
            ),
        )
    )

    vacuum_param_ok = (
        cfg.chamber.core.wall_thickness_mm > 0.0
        and front_module.module_inner_diameter_mm < front_module.module_outer_diameter_mm
        and rear_module.module_inner_diameter_mm < rear_module.module_outer_diameter_mm
    )
    for port in (cfg.ports.main_pump, cfg.ports.gauge_safety, cfg.ports.rotary_feedthrough, cfg.ports.spare):
        if not port.enabled:
            continue
        vacuum_param_ok = vacuum_param_ok and (port.inner_diameter_mm < port.outer_diameter_mm)
        if port.interface is not None:
            vacuum_param_ok = vacuum_param_ok and (
                port.interface.module_inner_diameter_mm < port.interface.module_outer_diameter_mm
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

    # [EN] Plate validation mixes frozen semantic checks (H/V/V pose, decentering) with generated-geometry checks (openings, overlap, LOS), because both design intent and CAD realization matter here. / [CN] 板件校验同时覆盖冻结语义检查（H/V/V 姿态、偏心）与生成几何检查（开孔、重叠、LOS），因为这里既要保证设计意图，也要保证 CAD 落地结果。
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

        # [EN] Envelope demand is measured from actual hit points on each assigned plate, then inflated by LOS margin, so panel size tracks detector acceptance rather than legacy nominal dimensions. / [CN] 板尺寸需求先由各自命中点在板面上的真实分布确定，再叠加 LOS 裕量，因此面板大小跟随探测器接受立体角，而不是沿用旧版名义尺寸。
        max_u = 0.0
        max_v = 0.0
        hit_count = 0
        for placement in assigned:
            if plate.opening_style == "los_tube":
                hit = plate_los_plane_hit_point(cfg, placement, plate)
                if hit is None:
                    continue
            else:
                hit = _plate_hit_point(placement, plate)
            u, v = _plate_local_uv(hit, plate)
            max_u = max(max_u, abs(u))
            max_v = max(max_v, abs(v))
            hit_count += 1

        required_width = 2.0 * (max_u + los_margin) if hit_count > 0 else 0.0
        required_height = 2.0 * (max_v + los_margin) if hit_count > 0 else 0.0
        plate_ok = plate.width_mm >= required_width and plate.height_mm >= required_height
        min_envelope_ok = min_envelope_ok and plate_ok
        min_envelope_detail_parts.append(
            f"{key}[hits={hit_count},w={plate.width_mm:.1f}/req>={required_width:.1f},h={plate.height_mm:.1f}/req>={required_height:.1f}]"
        )

    checks.append(
        SubsystemCheck(
            name="plate_min_envelope_margin_5mm",
            passed=min_envelope_ok,
            detail=", ".join(min_envelope_detail_parts),
        )
    )

    opening_ok = True
    opening_detail_parts: list[str] = []
    for key, plate in (("h", cfg.plate.h), ("v1", cfg.plate.v1), ("v2", cfg.plate.v2)):
        if plate.opening_style == "rounded_slot":
            polylines = plate_opening_local_polylines(cfg, key, plate, placements_by_plate[key])
            slot_count = len(polylines)
            expected_slots = 2 if key == "h" else 1
            valid = slot_count == expected_slots and slot_count > 0
            opening_ok = opening_ok and valid
            opening_detail_parts.append(
                f"{key}[style=rounded_slot,slots={slot_count},expected={expected_slots},half_width={plate_slot_half_width_mm(cfg):.1f}]"
            )
        elif plate.opening_style == "los_tube":
            # [EN] LOS-tube style is considered valid by tube radius semantics plus plane-hit reachability; the exact obstruction check happens later against the built solid. / [CN] `los_tube` 风格的有效性先由管径语义与打到板面的可达性判定，具体是否遮挡则在后续对实体的检查里完成。
            hit_count = sum(
                1
                for placement in placements_by_plate[key]
                if plate_los_plane_hit_point(cfg, placement, plate) is not None
            )
            valid = plate_slot_half_width_mm(cfg) > 0.0
            opening_ok = opening_ok and valid
            opening_detail_parts.append(
                f"{key}[style=los_tube,plane_hits={hit_count},half_width={plate_slot_half_width_mm(cfg):.1f}]"
            )
        else:
            valid = (
                plate.outer_radius_mm > plate.inner_radius_mm
                and plate.sector_opening_deg > 0.0
                and bool(plate.azimuth_centers_deg)
            )
            opening_ok = opening_ok and valid
            opening_detail_parts.append(
                f"{key}[style=annular_sector,inner={plate.inner_radius_mm:.1f},outer={plate.outer_radius_mm:.1f},open={plate.sector_opening_deg:.1f}]"
            )

    checks.append(
        SubsystemCheck(
            name="plate_opening_geometry_valid",
            passed=opening_ok,
            detail="; ".join(opening_detail_parts),
        )
    )

    h_plate_cone_clear_ok = True
    h_plate_cone_clear_parts: list[str] = []
    h_plate_shape = build_all_plates(cfg, placements=placements)["HPlate"]
    cone_front_face_radius_mm = 0.5 * cfg.detector.clamp.detector_diameter_mm
    for placement in placements:
        if plate_key_for_sector(placement.sector_name) == "h":
            continue
        cone = target_detector_front_face_cone(cfg, placement, cone_front_face_radius_mm)
        if cone is None:
            h_plate_cone_clear_ok = False
            h_plate_cone_clear_parts.append(f"{placement.tag}: cone=degenerate")
            continue
        overlap_volume = _shape_interference_volume(h_plate_shape, cone)
        h_plate_cone_clear_ok = h_plate_cone_clear_ok and overlap_volume <= 1e-3
        h_plate_cone_clear_parts.append(f"{placement.tag}[overlap={overlap_volume:.6f}]")

    checks.append(
        SubsystemCheck(
            name="h_plate_relief_cones_clear",
            passed=h_plate_cone_clear_ok,
            detail="; ".join(h_plate_cone_clear_parts),
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
        checks.append(
            SubsystemCheck(
                name="single_continuous_plate_solids",
                passed=True,
                detail="mode=skipped by geometry.clearance.skip_overlap_checks=true",
            )
        )
    else:
        chamber_shape = build_chamber(cfg, placements=placements)
        overlap_ok = True
        overlap_parts: list[str] = []
        plate_shapes = build_all_plates(cfg, placements=placements)
        for plate_name, plate_shape in plate_shapes.items():
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
        z_min, z_max = chamber_z_bounds(cfg.chamber.core)
        outside_ok = True
        outside_parts: list[str] = []
        for plate_name, plate_shape in plate_shapes.items():
            inside_vertices = 0
            for vertex in plate_shape.Vertexes:
                p = vertex.Point
                if abs(p.x) < (half_x - 1e-6) and abs(p.y) < (half_y - 1e-6) and (z_min + 1e-6) < p.z < (z_max - 1e-6):
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

        continuity_ok = True
        continuity_parts: list[str] = []
        for plate_name, plate_shape in plate_shapes.items():
            solid_count = len(plate_shape.Solids)
            continuity_ok = continuity_ok and solid_count == 1
            continuity_parts.append(f"{plate_name}:solids={solid_count}")
        checks.append(
            SubsystemCheck(
                name="single_continuous_plate_solids",
                passed=continuity_ok,
                detail=", ".join(continuity_parts),
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
        plate_key = plate_key_for_sector(placement.sector_name)
        own_plate_name = {
            "h": "HPlate",
            "v1": "VPlate1",
            "v2": "VPlate2",
        }[plate_key]
        own_plate_shape = plate_shapes[own_plate_name]
        start, end = _los_segment_endpoints(cfg, placement)
        los_hit_checked += 1
        if _shape_intersects_segment(own_plate_shape, start, end):
            los_failures.append(f"{placement.tag}: own_plate_material_blocks_los")

        passed, detail = _los_hit_with_margin(
            cfg,
            placement,
            plate_key,
            plate,
            placements_by_plate[plate_key],
            cfg.clearance.los_margin_mm,
            plate_shape=own_plate_shape,
        )
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
        z_min, z_max = chamber_z_bounds(cfg.chamber.core)
        inside = abs(center.x) <= half_x and abs(center.y) <= half_y and z_min <= center.z <= z_max
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
    mount_landing_failures: list[str] = []
    mount_direction_failures: list[str] = []
    mount_bolt_failures: list[str] = []
    mount_contact_failures: list[str] = []
    mount_continuity_failures: list[str] = []
    mount_assignment_failures: list[str] = []
    bridge_pose_failures: list[str] = []
    bridge_length_failures: list[str] = []
    bridge_lengths: list[float] = []
    bridge_signatures: list[tuple[str, tuple[float, float, float]]] = []
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
    # [EN] The bridge-length limit is derived from the continuous load path stack-up, so excessive cantilevering is flagged in terms of actual support geometry rather than a magic number. / [CN] 桥接长度上限由连续承载路径的几何叠加推得，因此过长悬挑是按真实支撑几何判定，而不是用一个神秘常数。
    for placement in placements:
        layout = detector_fixture_geometry(cfg, placement)
        housing, clamp_a, clamp_b, adapter_block, mount_base = build_detector_fixture(
            cfg,
            placement,
        )
        fixtures[placement.tag] = [housing, clamp_a, clamp_b, adapter_block]
        mount_bases[placement.tag] = mount_base

        plate_cfg = _plate_for_sector(cfg, placement.sector_name)
        u0, v0 = _plate_local_uv(layout.mount_projection, plate_cfg)
        if abs(u0) > (0.5 * plate_cfg.width_mm - mount_margin) or abs(v0) > (0.5 * plate_cfg.height_mm - mount_margin):
            mount_landing_failures.append(
                f"{placement.tag}: landing_center(u={u0:.1f},v={v0:.1f}) outside plate envelope"
            )

        direction_alignment_deg = _detector_mount_direction_alignment_deg(cfg, placement)
        if direction_alignment_deg > 1e-6:
            mount_direction_failures.append(
                f"{placement.tag}: direction_alignment_deg={direction_alignment_deg:.6f}"
            )

        for hole_center in layout.plate_hole_centers:
            uh, vh = _plate_local_uv(hole_center, plate_cfg)
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
        bridge_signatures.append((placement.tag, _detector_bridge_pose_signature(cfg, placement)))

    if bridge_signatures:
        ref_tag, ref_signature = bridge_signatures[0]
        bridge_tol_mm = 1e-6
        for tag, signature in bridge_signatures[1:]:
            deltas = tuple(abs(signature[i] - ref_signature[i]) for i in range(3))
            if max(deltas) > bridge_tol_mm:
                bridge_pose_failures.append(
                    f"{tag}: bridge_pose_delta=({deltas[0]:.6f},{deltas[1]:.6f},{deltas[2]:.6f}) mm vs {ref_tag}"
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
            name="detector_mount_bridge_pose_fixed_relative_to_detector_body",
            passed=not bridge_pose_failures,
            detail=(
                "bridge local pose is invariant across all detector placements"
                if not bridge_pose_failures
                else "; ".join(bridge_pose_failures)
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="detector_mount_hole_pattern_derived_from_fixture_direction",
            passed=not mount_direction_failures,
            detail=(
                "fixture in-plane drill axis follows detector direction for all placements"
                if not mount_direction_failures
                else "; ".join(mount_direction_failures)
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="detector_mount_plate_landing_within_envelope",
            passed=not mount_landing_failures,
            detail=(
                f"margin={mount_margin:.3f} mm"
                if not mount_landing_failures
                else "; ".join(mount_landing_failures)
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

    # [EN] Target validation branches by mechanism type because linear ladders and single-rotary holders obey different kinematic invariants even when they share the same beamline origin. / [CN] 靶机构校验按机构类型分支，因为线性靶梯和单靶旋转架即便共用同一束线原点，也服从不同的运动学不变量。
    if cfg.target.mode == "linear_ladder":
        ladder = cfg.target.ladder
        holder = cfg.target.holder
        if ladder is None or holder is None:
            raise ValueError("linear_ladder mode requires ladder and holder config")

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

    rotary = cfg.target.rotary
    holder = cfg.target.single_holder
    if rotary is None or holder is None:
        raise ValueError("single_rotary mode requires rotary and single_holder config")

    work_center = single_rotary_target_center(cfg, rotary.work_angle_deg)
    work_pose_ok = abs(work_center.x) <= 1e-6 and abs(work_center.z) <= 1e-6
    checks.append(
        SubsystemCheck(
            name="single_rotary_target_mode",
            passed=work_pose_ok and rotary.park_angle_deg > rotary.work_angle_deg,
            detail=(
                f"pivot_x={rotary.pivot_x_mm:.3f}, work_angle={rotary.work_angle_deg:.3f}, "
                f"park_angle={rotary.park_angle_deg:.3f}, work_center=({work_center.x:.3f},{work_center.z:.3f})"
            ),
        )
    )

    holder_parts = build_target_holders(cfg)
    screw_count = sum(1 for name in holder_parts.keys() if "SingleTargetHolderClampScrew_" in name)
    holder_dual_screw_ok = (
        holder.clamp_block_width_mm > 0.0
        and holder.clamp_block_height_mm > 0.0
        and holder.clamp_screw_diameter_mm > 0.0
        and holder.clamp_screw_head_diameter_mm > 0.0
        and holder.clamp_screw_head_height_mm > 0.0
        and screw_count == 2
    )
    checks.append(
        SubsystemCheck(
            name="single_target_holder_dual_screw_clamp",
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
            passed=(rotary.feedthrough_shaft_diameter_mm > 0.0 and rotary.handwheel_diameter_mm > 0.0),
            detail=(
                f"shaft_d={rotary.feedthrough_shaft_diameter_mm:.3f}, handwheel_d={rotary.handwheel_diameter_mm:.3f}"
            ),
        )
    )

    vendor_shapes = build_rotary_feedthrough_vendor_reference(cfg)
    vendor_reference_ok = (
        not rotary.vendor_reference_enabled
        or (
            rotary.vendor_reference_model_code is not None
            and rotary_port_interface_geometry(cfg) is not None
            and len(vendor_shapes) == 3
        )
    )
    checks.append(
        SubsystemCheck(
            name="vendor_rotary_feedthrough_reference",
            passed=vendor_reference_ok,
            detail=(
                f"enabled={rotary.vendor_reference_enabled}, model={rotary.vendor_reference_model_code}, "
                f"shape_count={len(vendor_shapes)}"
            ),
        )
    )

    drive_ok = (
        rotary.motor_mount_width_mm > 0.0
        and rotary.motor_mount_height_mm > 0.0
        and rotary.motor_mount_thickness_mm > 0.0
        and rotary.hard_stop_span_mm > 0.0
        and rotary.hard_stop_thickness_mm > 0.0
        and rotary.index_disk_diameter_mm > 0.0
        and rotary.index_disk_thickness_mm > 0.0
        and rotary.index_pin_diameter_mm > 0.0
        and rotary.index_pin_length_mm > 0.0
        and rotary.hub_diameter_mm > 0.0
        and rotary.arm_length_mm > 0.0
    )
    checks.append(
        SubsystemCheck(
            name="drive_semantics_complete",
            passed=drive_ok,
            detail=(
                f"motor_mount=({rotary.motor_mount_width_mm:.1f},{rotary.motor_mount_height_mm:.1f},{rotary.motor_mount_thickness_mm:.1f}), "
                f"hard_stop=({rotary.hard_stop_span_mm:.1f},{rotary.hard_stop_thickness_mm:.1f}), "
                f"hub_arm=({rotary.hub_diameter_mm:.1f},{rotary.arm_length_mm:.1f}), "
                f"index=({rotary.index_disk_diameter_mm:.1f},{rotary.index_pin_diameter_mm:.1f})"
            ),
        )
    )

    axis_extent = max(2.0 * cfg.chamber.core.size_z_mm, rotary.arm_length_mm + rotary.pivot_x_mm + 50.0)
    beam_axis = Part.makeLine(App.Vector(0.0, 0.0, -axis_extent), App.Vector(0.0, 0.0, axis_extent))
    park_drive_shapes, park_holder_shapes = build_single_rotary_target_shapes(cfg, rotary.park_angle_deg)
    beam_clear_radius = 0.5 * cfg.beamline.inlet_diameter_mm + cfg.clearance.los_margin_mm
    park_failures: list[str] = []
    for name, shape in {**park_drive_shapes, **park_holder_shapes}.items():
        clearance = _shape_min_distance(shape, beam_axis)
        if clearance < (beam_clear_radius - 1e-6):
            park_failures.append(f"{name}:{clearance:.3f}")
    checks.append(
        SubsystemCheck(
            name="park_position_clears_beam_axis",
            passed=not park_failures,
            detail=(
                f"required_clearance={beam_clear_radius:.3f} mm"
                if not park_failures
                else f"required_clearance={beam_clear_radius:.3f} mm; " + "; ".join(park_failures)
            ),
        )
    )

    return _subsystem_status("target", checks)


def _validate_stand(cfg: GeometryConfig, placements: list[DetectorPlacement]) -> SubsystemValidationResult:
    checks: list[SubsystemCheck] = []
    support_centers = stand_support_centers(cfg)
    chamber_supports = chamber_support_centers(cfg)
    h_plate_supports = h_plate_support_centers(cfg)
    support_foot_radius_mm = 0.5 * cfg.stand.support_foot_diameter_mm
    chamber_support_ok = len(chamber_supports) == 4 and all(
        (abs(center.x) + support_foot_radius_mm) <= (0.5 * cfg.chamber.core.size_x_mm + 1e-6)
        for center in chamber_supports
    )
    h_plate_support_ok = len(h_plate_supports) == 4 and all(
        (abs(center.x - cfg.plate.h.offset_x_mm) + support_foot_radius_mm) <= (0.5 * cfg.plate.h.width_mm + 1e-6)
        for center in h_plate_supports
    )
    chamber_support_zs = sorted({round(center.z, 3) for center in chamber_supports})
    h_plate_support_zs = sorted({round(center.z, 3) for center in h_plate_supports})

    # [EN] Stand checks intentionally focus on support semantics and service hardware, because the exact foot solids may move with chamber footprint tuning while those functional obligations stay fixed. / [CN] 支架检查刻意聚焦支撑语义和维护硬件，因为具体脚座实体会随腔体占位调参而变化，而这些功能义务保持不变。
    checks.append(
        SubsystemCheck(
            name="eight_point_support",
            passed=len(support_centers) == 8,
            detail=f"support_centers={len(support_centers)}",
        )
    )

    checks.append(
        SubsystemCheck(
            name="support_grids_under_chamber_and_h_plate",
            passed=chamber_support_ok and h_plate_support_ok,
            detail=(
                f"chamber_rows_z={chamber_support_zs}, x={[round(x, 3) for x in sorted({center.x for center in chamber_supports})]}; "
                f"h_rows_z={h_plate_support_zs}, x={[round(x, 3) for x in sorted({center.x for center in h_plate_supports})]}; "
                f"foot_d={cfg.stand.support_foot_diameter_mm:.3f}"
            ),
        )
    )

    stand_parts = build_stand(cfg)
    plate_shapes = build_all_plates(cfg, placements=placements)
    support_ymin = min(
        shape.BoundBox.YMin
        for name, shape in stand_parts.items()
        if name.startswith("StandSupportFoot_")
    )
    vertical_plate_ymin = min(plate_shapes["VPlate1"].BoundBox.YMin, plate_shapes["VPlate2"].BoundBox.YMin)
    checks.append(
        SubsystemCheck(
            name="support_feet_extend_below_vertical_plates",
            passed=support_ymin < (vertical_plate_ymin - 1e-6),
            detail=(
                f"support_ymin={support_ymin:.3f}, vertical_plate_ymin={vertical_plate_ymin:.3f}"
            ),
        )
    )

    checks.append(
        SubsystemCheck(
            name="anchor_slots_and_leveling",
            passed=(
                (
                    cfg.stand.anchor_slot_length_mm > 0.0
                    and cfg.stand.anchor_slot_width_mm > 0.0
                    and cfg.stand.leveling_screw_diameter_mm > 0.0
                    and cfg.stand.shim_thickness_mm > 0.0
                )
                if cfg.stand.with_base_plate
                else (cfg.stand.leveling_screw_diameter_mm > 0.0 and cfg.stand.shim_thickness_mm > 0.0)
            ),
            detail=(
                (
                    f"base_plate=enabled, slot=({cfg.stand.anchor_slot_length_mm:.3f},{cfg.stand.anchor_slot_width_mm:.3f}), "
                    f"level_screw_d={cfg.stand.leveling_screw_diameter_mm:.3f}, shim_t={cfg.stand.shim_thickness_mm:.3f}"
                )
                if cfg.stand.with_base_plate
                else (
                    f"base_plate=disabled, slot=not_instantiated, "
                    f"level_screw_d={cfg.stand.leveling_screw_diameter_mm:.3f}, shim_t={cfg.stand.shim_thickness_mm:.3f}"
                )
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
        _validate_stand(cfg, placements),
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
