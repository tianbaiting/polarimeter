from __future__ import annotations

import math
from dataclasses import dataclass

import FreeCAD as App
import Part

from .config import GeometryConfig, PlateConfig, PortConfig
from .layout import (
    DetectorPlacement,
    chamber_z_bounds,
    front_face_center,
    local_basis_from_direction,
    plate_key_for_sector,
    scaled,
)
from .primitives import ring_shape, slit_prism, tube_shape


@dataclass(frozen=True)
class DetectorFixtureGeometry:
    front_center: App.Vector
    direction: App.Vector
    mount_axis: App.Vector
    mount_lateral_axis: App.Vector
    plate_normal: App.Vector
    base_u_axis: App.Vector
    base_v_axis: App.Vector
    mount_projection: App.Vector
    mount_base_center: App.Vector
    mount_base_top_center: App.Vector
    clamp_center: App.Vector
    block_center: App.Vector
    bridge_center: App.Vector
    bridge_plate_face_center: App.Vector
    bridge_thickness_mm: float
    bridge_span_mm: float
    bridge_depth_mm: float
    upright_offsets: tuple[float, ...]
    upright_length_mm: float
    upright_width_mm: float
    upright_depth_mm: float
    plate_hole_centers: tuple[App.Vector, ...]
    base_hole_centers: tuple[App.Vector, ...]


@dataclass(frozen=True)
class _EndModuleAxialLayout:
    chamber_face_z: float
    flange_origin_z: float
    flange_chamber_face_z: float
    interface_face_z: float
    pipe_origin_z: float | None
    pipe_shape_length_mm: float


@dataclass(frozen=True)
class _MountedPortInterface:
    shape: Part.Shape
    interface_face_center: App.Vector
    axis: App.Vector


def _enabled_ports(cfg: GeometryConfig) -> tuple[tuple[str, PortConfig], ...]:
    return tuple(
        (name, port)
        for name, port in (
            ("main_pump", cfg.ports.main_pump),
            ("gauge_safety", cfg.ports.gauge_safety),
            ("rotary_feedthrough", cfg.ports.rotary_feedthrough),
            ("spare", cfg.ports.spare),
        )
        if port.enabled
    )


def chamber_support_centers(cfg: GeometryConfig) -> tuple[App.Vector, ...]:
    stand = cfg.stand
    core = cfg.chamber.core
    z_min, z_max = chamber_z_bounds(core)
    front_z = z_min + stand.chamber_support_end_margin_mm
    rear_z = z_max - stand.chamber_support_end_margin_mm

    # [EN] Chamber support is now a self-contained four-post grid: two posts near the upstream end and two near the downstream end, each row staying 100 mm off the chamber end faces while x stays close to the chamber load path. / [CN] chamber 支撑现改为独立四柱网格：上游端附近两根、下游端附近两根，各排离端面 100 mm，同时 x 向仍贴近 chamber 主承载路径。
    return (
        App.Vector(-stand.chamber_support_pair_half_span_x_mm, 0.0, front_z),
        App.Vector(stand.chamber_support_pair_half_span_x_mm, 0.0, front_z),
        App.Vector(-stand.chamber_support_pair_half_span_x_mm, 0.0, rear_z),
        App.Vector(stand.chamber_support_pair_half_span_x_mm, 0.0, rear_z),
    )


def h_plate_support_centers(cfg: GeometryConfig) -> tuple[App.Vector, ...]:
    stand = cfg.stand
    plate_h = cfg.plate.h
    front_z = plate_h.z_mm - (0.5 * plate_h.height_mm - stand.h_plate_support_end_margin_mm)
    rear_z = plate_h.z_mm + (0.5 * plate_h.height_mm - stand.h_plate_support_end_margin_mm)

    # [EN] The H plate gets its own independent four-post grid so the detector-carrying service panel no longer borrows the chamber posts; two rows track the plate height while the x pair stays near the loaded detector zone instead of running out to remote corners. / [CN] `H` 板改为独立四柱支撑，不再借用 chamber 立柱；前后两排跟随板高布置，而 x 向两列仍贴近探测器受力区，不再跑到很远的外角。
    return (
        App.Vector(plate_h.offset_x_mm - stand.h_plate_support_pair_half_span_x_mm, 0.0, front_z),
        App.Vector(plate_h.offset_x_mm + stand.h_plate_support_pair_half_span_x_mm, 0.0, front_z),
        App.Vector(plate_h.offset_x_mm - stand.h_plate_support_pair_half_span_x_mm, 0.0, rear_z),
        App.Vector(plate_h.offset_x_mm + stand.h_plate_support_pair_half_span_x_mm, 0.0, rear_z),
    )


def stand_support_centers(cfg: GeometryConfig) -> tuple[App.Vector, ...]:
    return chamber_support_centers(cfg) + h_plate_support_centers(cfg)


def _chamber_halves(cfg: GeometryConfig) -> tuple[float, float, float]:
    core = cfg.chamber.core
    return (0.5 * core.size_x_mm, 0.5 * core.size_y_mm, 0.5 * core.size_z_mm)


def _port_pose(cfg: GeometryConfig, port: PortConfig) -> tuple[App.Vector, App.Vector]:
    half_x, half_y, _ = _chamber_halves(cfg)

    if port.side == "right":
        return App.Vector(half_x, port.center_y_mm, port.center_z_mm), App.Vector(1.0, 0.0, 0.0)
    if port.side == "left":
        return App.Vector(-half_x, port.center_y_mm, port.center_z_mm), App.Vector(-1.0, 0.0, 0.0)
    if port.side == "top":
        return App.Vector(port.center_x_mm, half_y, port.center_z_mm), App.Vector(0.0, 1.0, 0.0)
    if port.side == "bottom":
        return App.Vector(port.center_x_mm, -half_y, port.center_z_mm), App.Vector(0.0, -1.0, 0.0)
    raise ValueError(f"unsupported side: {port.side}")


def _plate_axes(plate: PlateConfig) -> tuple[App.Vector, App.Vector, App.Vector, App.Vector]:
    center = App.Vector(plate.offset_x_mm, plate.offset_y_mm, plate.z_mm)
    if plate.mount_plane == "xy":
        return center, App.Vector(0.0, 0.0, 1.0), App.Vector(1.0, 0.0, 0.0), App.Vector(0.0, 1.0, 0.0)
    if plate.mount_plane == "xz":
        return center, App.Vector(0.0, 1.0, 0.0), App.Vector(1.0, 0.0, 0.0), App.Vector(0.0, 0.0, 1.0)
    if plate.mount_plane == "yz":
        return center, App.Vector(1.0, 0.0, 0.0), App.Vector(0.0, 1.0, 0.0), App.Vector(0.0, 0.0, 1.0)
    raise ValueError(f"Unsupported plate orientation/mount_plane: {plate.orientation}/{plate.mount_plane}")


def _vector_length(v: App.Vector) -> float:
    return math.sqrt((v.x * v.x) + (v.y * v.y) + (v.z * v.z))


def _normalize_vector(v: App.Vector) -> App.Vector:
    n = _vector_length(v)
    if n <= 1e-12:
        raise ValueError("cannot normalize near-zero vector")
    return App.Vector(v.x / n, v.y / n, v.z / n)


def _dot(a: App.Vector, b: App.Vector) -> float:
    return (a.x * b.x) + (a.y * b.y) + (a.z * b.z)


def _axis_distance(target: App.Vector, origin: App.Vector, axis: App.Vector) -> float:
    delta = target - origin
    return _dot(delta, axis)


def _midpoint(a: App.Vector, b: App.Vector) -> App.Vector:
    return App.Vector(0.5 * (a.x + b.x), 0.5 * (a.y + b.y), 0.5 * (a.z + b.z))


def _plate_hit_point_on_mount_plane(placement: DetectorPlacement, plate: PlateConfig) -> App.Vector:
    center = front_face_center(placement)
    if plate.mount_plane == "xy":
        return App.Vector(center.x, center.y, plate.z_mm)
    if plate.mount_plane == "xz":
        return App.Vector(center.x, plate.offset_y_mm, center.z)
    if plate.mount_plane == "yz":
        return App.Vector(plate.offset_x_mm, center.y, center.z)
    raise ValueError(f"unsupported mount_plane {plate.mount_plane!r}")


def _plate_local_uv_from_world(plate: PlateConfig, point: App.Vector) -> tuple[float, float]:
    center, _axis_t, axis_v, axis_w = _plate_axes(plate)
    delta = point - center
    return _dot(delta, axis_v), _dot(delta, axis_w)


def _plate_world_from_local_uv(plate: PlateConfig, u_mm: float, v_mm: float) -> App.Vector:
    center, _axis_t, axis_v, axis_w = _plate_axes(plate)
    return center + scaled(axis_v, u_mm) + scaled(axis_w, v_mm)


def _segment_plane_hit_point(
    start: App.Vector,
    end: App.Vector,
    plane_point: App.Vector,
    plane_normal: App.Vector,
) -> App.Vector | None:
    delta = end - start
    denom = _dot(delta, plane_normal)
    if abs(denom) <= 1e-9:
        return None
    t = _dot(plane_point - start, plane_normal) / denom
    if t < -1e-9 or t > 1.0 + 1e-9:
        return None
    return start + scaled(delta, t)


def plate_slot_half_width_mm(cfg: GeometryConfig) -> float:
    # [EN] Rounded-slot half-width freezes LOS channel radius plus clearance margin into the plate opening itself, avoiding a second interpretation layer during validation. / [CN] 圆角槽半宽直接固化“LOS 通道半径 + 裕量”，避免生成与校验各自再解释一次开口宽度。
    return 0.5 * cfg.chamber.los_channels.channel_diameter_mm + cfg.clearance.los_margin_mm


def active_target_los_source_point(cfg: GeometryConfig) -> App.Vector:
    # [EN] Plate LOS openings must reference the active scattering target instead of detector-to-plate orthogonal projections, otherwise material between fixtures gets cut spuriously. / [CN] 板上 LOS 开口必须参考当前有效散射靶点，而不是探测器到板的正交投影，否则会错误切掉夹具之间的材料。
    if cfg.target.mode == "single_rotary":
        rotary = cfg.target.rotary
        if rotary is None:
            raise ValueError("single_rotary target config requires geometry.target.rotary")
        return single_rotary_target_center(cfg, rotary.active_angle_deg)

    ladder = cfg.target.ladder
    if ladder is None:
        raise ValueError("linear_ladder target config requires geometry.target.ladder")
    return App.Vector(_target_slot_positions_x(cfg)[ladder.active_index], 0.0, 0.0)


def target_detector_los_segment_endpoints(
    cfg: GeometryConfig,
    placement: DetectorPlacement,
) -> tuple[App.Vector, App.Vector]:
    start = active_target_los_source_point(cfg)
    # [EN] Extend the LOS endpoint to the detector active-face offset rather than the fixture nose so plate openings are sized to sensing geometry, not housing cosmetics. / [CN] LOS 终点延伸到探测器有效面偏移处，而不是夹具外形前端，使板上开孔针对的是探测几何而非外壳外观。
    end = front_face_center(placement) + scaled(placement.direction, cfg.clearance.los_detector_active_face_offset_mm)
    return start, end


def target_detector_los_tube(
    cfg: GeometryConfig,
    placement: DetectorPlacement,
    radius_mm: float,
    overshoot_mm: float = 1.0,
) -> Part.Shape | None:
    start, end = target_detector_los_segment_endpoints(cfg, placement)
    delta = end - start
    length = _vector_length(delta)
    if length <= 1e-9:
        return None
    axis = _normalize_vector(delta)
    return Part.makeCylinder(radius_mm, length + 2.0 * overshoot_mm, start - scaled(axis, overshoot_mm), axis)


def target_detector_front_face_cone(
    cfg: GeometryConfig,
    placement: DetectorPlacement,
    front_face_radius_mm: float,
) -> Part.Shape | None:
    start = active_target_los_source_point(cfg)
    end = front_face_center(placement)
    delta = end - start
    length = _vector_length(delta)
    if length <= 1e-9:
        return None
    axis = _normalize_vector(delta)
    # [EN] Chamber side-exit openings follow the exact ruled surface from the active target point to the detector front-face circle, so the vacuum cut matches the physical acceptance cone instead of a constant-radius shortcut. / [CN] 腔体侧向开口按“有效靶点到探测器前表面圆”的真实母线面生成，使真空切口匹配物理接受圆锥，而不是固定半径近似。
    return Part.makeCone(0.0, front_face_radius_mm, length, start, axis)


def _cone_band_local_uv_bounds(
    cfg: GeometryConfig,
    placement: DetectorPlacement,
    plate: PlateConfig,
    band_half_thickness_mm: float,
    front_face_radius_mm: float,
    sample_count: int = 96,
) -> tuple[float, float, float, float] | None:
    start = active_target_los_source_point(cfg)
    front_center = front_face_center(placement)
    _axis_u, face_v, face_w = local_basis_from_direction(placement.direction)
    center, axis_t, _axis_v, _axis_w = _plate_axes(plate)
    local_points: list[tuple[float, float]] = []

    # [EN] The local H-plate relief must clear the full oblique cone through the plate thickness, so sample the detector entrance circle and intersect each ruled ray with both plate-band faces instead of approximating the cone by a mid-plane circle. / [CN] H 板局部长方形让位必须清掉整个斜穿圆锥在板厚方向上的范围，因此对探测器前表面圆做采样，并把每条母线与板厚带前后两面求交，而不是用板中面的圆截面近似。
    for face_offset_mm in (-band_half_thickness_mm, band_half_thickness_mm):
        plane_point = center + scaled(axis_t, face_offset_mm)
        for sample_idx in range(sample_count):
            phi = (2.0 * math.pi * float(sample_idx)) / float(sample_count)
            circle_point = (
                front_center
                + scaled(face_v, front_face_radius_mm * math.cos(phi))
                + scaled(face_w, front_face_radius_mm * math.sin(phi))
            )
            hit = _segment_plane_hit_point(start, circle_point, plane_point, axis_t)
            if hit is None:
                continue
            local_points.append(_plate_local_uv_from_world(plate, hit))

    if not local_points:
        return None

    u_values = [u for u, _ in local_points]
    v_values = [v for _, v in local_points]
    return min(u_values), max(u_values), min(v_values), max(v_values)


def plate_los_plane_hit_point(
    cfg: GeometryConfig,
    placement: DetectorPlacement,
    plate: PlateConfig,
) -> App.Vector | None:
    start, end = target_detector_los_segment_endpoints(cfg, placement)
    delta = end - start
    center, axis_t, _axis_v, _axis_w = _plate_axes(plate)
    denom = _dot(delta, axis_t)
    if abs(denom) <= 1e-9:
        return None
    t = _dot(center - start, axis_t) / denom
    if t < -1e-9 or t > 1.0 + 1e-9:
        return None
    return start + scaled(delta, t)


def plate_opening_local_polylines(
    cfg: GeometryConfig,
    plate_key: str,
    plate: PlateConfig,
    placements: list[DetectorPlacement],
) -> tuple[tuple[tuple[float, float], ...], ...]:
    if plate.opening_style != "rounded_slot":
        return ()

    # [EN] Group placements by the physical side served by each plate so rounded slots connect only channels that share one continuous service panel, not unrelated detector families. / [CN] 按每块板实际服务的物理侧面对落位分组，使圆角槽只连接同一维护板上的通道，而不会把无关探测器族连成一片。
    if plate_key == "h":
        grouped = [
            [placement for placement in placements if placement.sector_name == "left"],
            [placement for placement in placements if placement.sector_name == "right"],
        ]
    elif plate_key == "v1":
        grouped = [[placement for placement in placements if placement.sector_name == "up"]]
    elif plate_key == "v2":
        grouped = [[placement for placement in placements if placement.sector_name == "down"]]
    else:
        raise ValueError(f"unsupported plate_key {plate_key!r}")

    polylines: list[tuple[tuple[float, float], ...]] = []
    for group in grouped:
        ordered = sorted(group, key=lambda placement: front_face_center(placement).z)
        local_points: list[tuple[float, float]] = []
        for placement in ordered:
            hit = _plate_hit_point_on_mount_plane(placement, plate)
            local_points.append(_plate_local_uv_from_world(plate, hit))
        if local_points:
            polylines.append(tuple(local_points))
    return tuple(polylines)


def _annular_sector_cut(plate: PlateConfig) -> list[Part.Shape]:
    if plate.sector_opening_deg <= 0.0:
        return []

    center, axis_t, _, _ = _plate_axes(plate)
    cut_length = plate.lug_thickness_mm + 2.0
    base = center - scaled(axis_t, 0.5 * cut_length)

    cuts: list[Part.Shape] = []
    for az_center in plate.azimuth_centers_deg:
        outer = Part.makeCylinder(
            plate.outer_radius_mm,
            cut_length,
            base,
            axis_t,
            plate.sector_opening_deg,
        )
        inner = Part.makeCylinder(
            plate.inner_radius_mm,
            cut_length + 0.4,
            base - scaled(axis_t, 0.2),
            axis_t,
            plate.sector_opening_deg,
        )
        sector = outer.cut(inner)
        # [EN] Keep annular-sector geometry in each plate local cross-plane so LOS acceptance remains comparable across H/V/V plate poses. / [CN] 在各板局部截面内保持扇形环带几何，使 H/V/V 不同姿态下 LOS 验收可比。
        sector.rotate(center, axis_t, az_center - 0.5 * plate.sector_opening_deg)
        cuts.append(sector)

    return cuts


def _los_channel_cuts(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement] | None,
) -> list[Part.Shape]:
    los_cfg = cfg.chamber.los_channels
    if cfg.clearance.los_scope != "v2_fullpath" or not los_cfg.enabled or not placements:
        return []

    # [EN] v2 full-path validation models chamber corridors from the active target point to each detector entrance circle, so chamber and rear-interface cuts match the actual side-exit acceptance cone instead of a fixed-radius proxy. / [CN] v2 全路径校验按“有效靶点到各探测器入射圆面”的通道建模，因此腔体与后端接口的切口跟随真实侧向接受圆锥，而不是固定半径近似。
    cuts: list[Part.Shape] = []
    front_face_radius_mm = 0.5 * cfg.detector.clamp.detector_diameter_mm
    for placement in placements:
        cone = target_detector_front_face_cone(cfg, placement, front_face_radius_mm)
        if cone is not None:
            cuts.append(cone)
    return cuts


def build_chamber(cfg: GeometryConfig, placements: list[DetectorPlacement] | None = None) -> Part.Shape:
    core = cfg.chamber.core
    half_x, half_y, _ = _chamber_halves(cfg)
    z_min, z_max = chamber_z_bounds(core)

    # [EN] Start from a rectangular shell and subtract beam, ports, and optional LOS corridors so the vacuum boundary stays a single solid under all side-exit variants. / [CN] 先构造长方体壳体，再减去束流孔、端口和可选 LOS 通道，使真空边界在各类侧向出射方案下都保持为单一实体。
    outer = Part.makeBox(
        core.size_x_mm,
        core.size_y_mm,
        core.size_z_mm,
        App.Vector(-half_x, -half_y, z_min),
    )
    inner = Part.makeBox(
        core.size_x_mm - 2.0 * core.wall_thickness_mm,
        core.size_y_mm - 2.0 * core.wall_thickness_mm,
        core.size_z_mm - 2.0 * core.wall_thickness_mm,
        App.Vector(
            -half_x + core.wall_thickness_mm,
            -half_y + core.wall_thickness_mm,
            z_min + core.wall_thickness_mm,
        ),
    )
    chamber = outer.cut(inner)

    beam_cut = Part.makeCylinder(
        0.5 * cfg.beamline.inlet_diameter_mm,
        core.size_z_mm + 4.0,
        App.Vector(0.0, 0.0, z_min - 2.0),
        App.Vector(0.0, 0.0, 1.0),
    )
    chamber = chamber.cut(beam_cut)

    for _name, port in _enabled_ports(cfg):
        wall_point, axis = _port_pose(cfg, port)
        cut_origin = wall_point - scaled(axis, core.wall_thickness_mm + 1.0)
        cut = Part.makeCylinder(
            0.5 * port.inner_diameter_mm,
            core.wall_thickness_mm + 2.0,
            cut_origin,
            axis,
        )
        chamber = chamber.cut(cut)

    for cut in _los_channel_cuts(cfg, placements):
        chamber = chamber.cut(cut)

    return chamber


def _end_module_has_groove(standard: str) -> bool:
    return standard.upper().startswith("VG")


def _end_module_side_cfg(cfg: GeometryConfig, side: str):
    if side == "front":
        return cfg.chamber.end_modules.front
    if side == "rear":
        return cfg.chamber.end_modules.rear
    raise ValueError(f"unsupported side {side!r}")


def _end_module_axial_layout(cfg: GeometryConfig, side: str) -> _EndModuleAxialLayout:
    z_min, z_max = chamber_z_bounds(cfg.chamber.core)
    module = _end_module_side_cfg(cfg, side)
    # [EN] The welded pipe is seated slightly into both the flange bore and the chamber wall so boolean fusion gets finite overlap volume instead of a numerically fragile face-only touch. / [CN] 焊接短管会同时少量插入法兰内孔和 chamber 壁厚，使布尔并体获得有限重叠体积，而不是数值上脆弱的纯贴面接触。
    pipe_seat_mm = min(2.0, 0.5 * module.module_thickness_mm) if module.pipe_length_mm > 0.0 else 0.0

    if side == "front":
        chamber_face_z = z_min
        flange_origin_z = chamber_face_z - module.pipe_length_mm - module.module_thickness_mm
        flange_chamber_face_z = chamber_face_z - module.pipe_length_mm
        interface_face_z = flange_origin_z
        pipe_origin_z = chamber_face_z - module.pipe_length_mm - pipe_seat_mm if module.pipe_length_mm > 0.0 else None
    elif side == "rear":
        chamber_face_z = z_max
        flange_origin_z = chamber_face_z + module.pipe_length_mm
        flange_chamber_face_z = chamber_face_z + module.pipe_length_mm
        interface_face_z = flange_origin_z + module.module_thickness_mm
        pipe_origin_z = chamber_face_z - pipe_seat_mm if module.pipe_length_mm > 0.0 else None
    else:
        raise ValueError(f"unsupported side {side!r}")

    return _EndModuleAxialLayout(
        chamber_face_z=chamber_face_z,
        flange_origin_z=flange_origin_z,
        flange_chamber_face_z=flange_chamber_face_z,
        interface_face_z=interface_face_z,
        pipe_origin_z=pipe_origin_z,
        pipe_shape_length_mm=(module.pipe_length_mm + 2.0 * pipe_seat_mm) if module.pipe_length_mm > 0.0 else 0.0,
    )


def _build_end_module(
    cfg: GeometryConfig,
    side: str,
    placements: list[DetectorPlacement] | None = None,
) -> Part.Shape:
    module = _end_module_side_cfg(cfg, side)
    axial = _end_module_axial_layout(cfg, side)
    axis = App.Vector(0.0, 0.0, 1.0)

    # [EN] Both interfaces now follow the same manufacturing stack: chamber shell -> welded round pipe stub -> JIS flange -> mating equipment, so the external sealing face is always on the outward side of the flange. / [CN] 现在前后接口都遵循同一制造堆栈：腔体壳体 -> 焊接圆管短节 -> JIS 法兰 -> 外部设备，因此密封面始终放在法兰对外的一侧。
    origin = App.Vector(0.0, 0.0, axial.flange_origin_z)
    if side == "front":
        groove_origin = App.Vector(0.0, 0.0, axial.interface_face_z)
        seal_origin = App.Vector(0.0, 0.0, axial.interface_face_z)
    elif side == "rear":
        groove_origin = App.Vector(0.0, 0.0, axial.interface_face_z - module.oring_groove_depth_mm)
        seal_origin = App.Vector(0.0, 0.0, axial.interface_face_z - module.seal_face_width_mm)
    else:
        raise ValueError(f"unsupported side {side!r}")

    flange = tube_shape(
        outer_diameter_mm=module.module_outer_diameter_mm,
        inner_diameter_mm=module.module_inner_diameter_mm,
        length_mm=module.module_thickness_mm,
        origin=origin,
        axis=axis,
    )

    if module.pipe_length_mm > 0.0 and axial.pipe_origin_z is not None:
        pipe = tube_shape(
            outer_diameter_mm=module.pipe_outer_diameter_mm,
            inner_diameter_mm=module.pipe_inner_diameter_mm,
            length_mm=axial.pipe_shape_length_mm,
            origin=App.Vector(0.0, 0.0, axial.pipe_origin_z),
            axis=axis,
        )
        flange = flange.fuse(pipe)

    seal_outer = min(
        module.module_outer_diameter_mm - 2.0,
        module.module_inner_diameter_mm
        + (2.0 * module.seal_face_width_mm)
        + max(0.0, module.oring_groove_outer_diameter_mm - module.oring_groove_inner_diameter_mm),
    )
    seal_ring = tube_shape(
        outer_diameter_mm=seal_outer,
        inner_diameter_mm=module.module_inner_diameter_mm,
        length_mm=module.seal_face_width_mm,
        origin=seal_origin,
        axis=axis,
    )
    flange = flange.fuse(seal_ring)

    bolt_radius = 0.5 * module.bolt_circle_diameter_mm
    for idx in range(module.bolt_count):
        angle = (2.0 * math.pi * float(idx)) / float(module.bolt_count)
        x = bolt_radius * math.cos(angle)
        y = bolt_radius * math.sin(angle)
        hole = Part.makeCylinder(
            0.5 * module.flange_bolt_hole_diameter_mm,
            module.module_thickness_mm + 2.0,
            App.Vector(x, y, origin.z - 1.0),
            axis,
        )
        flange = flange.cut(hole)

    if _end_module_has_groove(module.standard) and module.oring_groove_depth_mm > 0.0:
        groove_cut = tube_shape(
            outer_diameter_mm=module.oring_groove_outer_diameter_mm,
            inner_diameter_mm=module.oring_groove_inner_diameter_mm,
            length_mm=module.oring_groove_depth_mm,
            origin=groove_origin,
            axis=axis,
        )
        flange = flange.cut(groove_cut)

    if side == "rear":
        for cut in _los_channel_cuts(cfg, placements):
            flange = flange.cut(cut)

    return flange


def build_end_modules(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement] | None = None,
) -> tuple[Part.Shape, Part.Shape]:
    return _build_end_module(cfg, "front", placements=placements), _build_end_module(cfg, "rear", placements=placements)


def _build_end_module_fasteners_for_side(cfg: GeometryConfig, side: str) -> dict[str, Part.Shape]:
    module = _end_module_side_cfg(cfg, side)
    axial = _end_module_axial_layout(cfg, side)
    bolt_radius = 0.5 * module.bolt_circle_diameter_mm
    bolt_clearance_d = module.interface_bolt_diameter_mm + 0.8

    if side == "front":
        face_origin = App.Vector(0.0, 0.0, axial.flange_chamber_face_z)
        axis = App.Vector(0.0, 0.0, -1.0)
        prefix = "FrontInterface"
    elif side == "rear":
        face_origin = App.Vector(0.0, 0.0, axial.flange_chamber_face_z)
        axis = App.Vector(0.0, 0.0, 1.0)
        prefix = "RearInterface"
    else:
        raise ValueError(f"unsupported side {side!r}")

    out: dict[str, Part.Shape] = {}
    for idx in range(module.bolt_count):
        angle = (2.0 * math.pi * float(idx)) / float(module.bolt_count)
        x = bolt_radius * math.cos(angle)
        y = bolt_radius * math.sin(angle)
        bolt_origin = App.Vector(x, y, face_origin.z)

        bolt = Part.makeCylinder(
            0.5 * module.interface_bolt_diameter_mm,
            module.interface_bolt_length_mm,
            bolt_origin,
            axis,
        )

        washer = ring_shape(
            outer_diameter_mm=module.interface_washer_outer_diameter_mm,
            inner_diameter_mm=bolt_clearance_d,
            thickness_mm=module.interface_washer_thickness_mm,
            origin=bolt_origin,
            axis=axis,
        )

        nut_origin = bolt_origin + scaled(axis, module.interface_bolt_length_mm - module.interface_nut_thickness_mm)
        nut = ring_shape(
            outer_diameter_mm=module.interface_nut_outer_diameter_mm,
            inner_diameter_mm=bolt_clearance_d,
            thickness_mm=module.interface_nut_thickness_mm,
            origin=nut_origin,
            axis=axis,
        )

        part_idx = idx + 1
        out[f"{prefix}Bolt_{part_idx}"] = bolt
        out[f"{prefix}Washer_{part_idx}"] = washer
        out[f"{prefix}Nut_{part_idx}"] = nut

    return out


def build_end_module_fasteners(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    # [EN] Interface fasteners are explicit solids so replacement-module assembly and downstream checks operate on geometry instead of inferred metadata. / [CN] 将接口紧固件建成实体，便于可更换模块装配与后续校验基于几何而非元数据推断。
    out: dict[str, Part.Shape] = {}
    out.update(_build_end_module_fasteners_for_side(cfg, "front"))
    out.update(_build_end_module_fasteners_for_side(cfg, "rear"))
    return out


def _build_port_interface(
    cfg: GeometryConfig,
    port: PortConfig,
) -> _MountedPortInterface | None:
    if port.interface is None:
        return None

    module = port.interface
    wall_point, axis = _port_pose(cfg, port)
    axis_u, axis_v, axis_w = local_basis_from_direction(axis)
    base_origin = wall_point + scaled(axis_u, port.length_mm)
    flange_origin = base_origin + scaled(axis_u, module.pipe_length_mm)
    interface_face_center = flange_origin + scaled(axis_u, module.module_thickness_mm)

    flange = tube_shape(
        outer_diameter_mm=module.module_outer_diameter_mm,
        inner_diameter_mm=module.module_inner_diameter_mm,
        length_mm=module.module_thickness_mm,
        origin=flange_origin,
        axis=axis_u,
    )
    if module.pipe_length_mm > 0.0:
        pipe = tube_shape(
            outer_diameter_mm=module.pipe_outer_diameter_mm,
            inner_diameter_mm=module.pipe_inner_diameter_mm,
            length_mm=module.pipe_length_mm,
            origin=base_origin,
            axis=axis_u,
        )
        flange = flange.fuse(pipe)

    seal_outer = min(
        module.module_outer_diameter_mm - 2.0,
        module.module_inner_diameter_mm
        + (2.0 * module.seal_face_width_mm)
        + max(0.0, module.oring_groove_outer_diameter_mm - module.oring_groove_inner_diameter_mm),
    )
    seal_origin = interface_face_center - scaled(axis_u, module.seal_face_width_mm)
    flange = flange.fuse(
        tube_shape(
            outer_diameter_mm=seal_outer,
            inner_diameter_mm=module.module_inner_diameter_mm,
            length_mm=module.seal_face_width_mm,
            origin=seal_origin,
            axis=axis_u,
        )
    )

    bolt_radius = 0.5 * module.bolt_circle_diameter_mm
    for idx in range(module.bolt_count):
        angle = (2.0 * math.pi * float(idx)) / float(module.bolt_count)
        radial = scaled(axis_v, bolt_radius * math.cos(angle)) + scaled(axis_w, bolt_radius * math.sin(angle))
        hole_origin = flange_origin + radial - scaled(axis_u, 1.0)
        hole = Part.makeCylinder(
            0.5 * module.flange_bolt_hole_diameter_mm,
            module.module_thickness_mm + 2.0,
            hole_origin,
            axis_u,
        )
        flange = flange.cut(hole)

    if _end_module_has_groove(module.standard) and module.oring_groove_depth_mm > 0.0:
        groove_origin = interface_face_center - scaled(axis_u, module.oring_groove_depth_mm)
        groove_cut = tube_shape(
            outer_diameter_mm=module.oring_groove_outer_diameter_mm,
            inner_diameter_mm=module.oring_groove_inner_diameter_mm,
            length_mm=module.oring_groove_depth_mm,
            origin=groove_origin,
            axis=axis_u,
        )
        flange = flange.cut(groove_cut)

    return _MountedPortInterface(
        shape=flange,
        interface_face_center=interface_face_center,
        axis=axis_u,
    )


def build_ports(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    out: dict[str, Part.Shape] = {}
    for name, port in (
        ("MainPumpPort", cfg.ports.main_pump),
        ("GaugeSafetyPort", cfg.ports.gauge_safety),
        ("RotaryFeedthroughPort", cfg.ports.rotary_feedthrough),
        ("SparePort", cfg.ports.spare),
    ):
        if not port.enabled:
            continue
        wall_point, axis = _port_pose(cfg, port)
        shape: Part.Shape | None = None
        if port.length_mm > 0.0:
            shape = tube_shape(
                outer_diameter_mm=port.outer_diameter_mm,
                inner_diameter_mm=port.inner_diameter_mm,
                length_mm=port.length_mm,
                origin=wall_point,
                axis=axis,
            )
        mounted_interface = _build_port_interface(cfg, port)
        if mounted_interface is not None:
            shape = mounted_interface.shape if shape is None else shape.fuse(mounted_interface.shape)
        if shape is not None:
            out[name] = shape
    return out


def _build_plate_base_with_openings(plate: PlateConfig) -> Part.Shape:
    center, axis_t, axis_v, axis_w = _plate_axes(plate)
    base = slit_prism(
        center=center,
        axis_u=axis_t,
        axis_v=axis_v,
        axis_w=axis_w,
        length_mm=plate.thickness_mm,
        width_mm=plate.width_mm,
        height_mm=plate.height_mm,
    )

    for cut in _annular_sector_cut(plate):
        base = base.cut(cut)

    return base


def _rounded_slot_cut(
    plate: PlateConfig,
    local_polyline: tuple[tuple[float, float], ...],
    half_width_mm: float,
) -> Part.Shape:
    center, axis_t, _axis_v, _axis_w = _plate_axes(plate)
    cut_length = plate.thickness_mm + 4.0

    parts: list[Part.Shape] = []
    world_points = [_plate_world_from_local_uv(plate, u_mm, v_mm) for u_mm, v_mm in local_polyline]
    for point in world_points:
        parts.append(
            Part.makeCylinder(
                half_width_mm,
                cut_length,
                point - scaled(axis_t, 0.5 * cut_length),
                axis_t,
            )
        )

    for start, end in zip(world_points, world_points[1:]):
        delta = end - start
        segment_length = _vector_length(delta)
        if segment_length <= 1e-9:
            continue
        axis_segment = _normalize_vector(delta)
        axis_perp = _normalize_vector(axis_t.cross(axis_segment))
        parts.append(
            slit_prism(
                center=_midpoint(start, end),
                axis_u=axis_t,
                axis_v=axis_segment,
                axis_w=axis_perp,
                length_mm=cut_length + 0.2,
                width_mm=segment_length + 0.2,
                height_mm=2.0 * half_width_mm + 0.2,
            )
        )

    out = parts[0]
    for part in parts[1:]:
        out = out.fuse(part)
    return out


def _build_plate_lugs_with_bolt_holes(plate: PlateConfig) -> Part.Shape:
    center, axis_t, axis_v, axis_w = _plate_axes(plate)

    # [EN] Mirror lugs on both sides of the plate so fixture loads bypass the central LOS opening and enter the stand path symmetrically. / [CN] 在板两侧对称布置连接耳，使夹具载荷绕开中央 LOS 开口并对称地传入支撑路径。
    left_center = center - scaled(axis_v, 0.5 * (plate.width_mm + plate.lug_length_mm))
    right_center = center + scaled(axis_v, 0.5 * (plate.width_mm + plate.lug_length_mm))

    left_lug = slit_prism(
        center=left_center,
        axis_u=axis_t,
        axis_v=axis_v,
        axis_w=axis_w,
        length_mm=plate.lug_thickness_mm,
        width_mm=plate.lug_length_mm,
        height_mm=plate.lug_width_mm,
    )
    right_lug = slit_prism(
        center=right_center,
        axis_u=axis_t,
        axis_v=axis_v,
        axis_w=axis_w,
        length_mm=plate.lug_thickness_mm,
        width_mm=plate.lug_length_mm,
        height_mm=plate.lug_width_mm,
    )

    lugs = left_lug.fuse(right_lug)

    h_start = -0.5 * (plate.bolt_hole_count - 1) * plate.bolt_hole_pitch_mm
    for idx in range(plate.bolt_hole_count):
        h_pos = h_start + idx * plate.bolt_hole_pitch_mm
        for base_center in (left_center, right_center):
            hole_center = base_center + scaled(axis_w, h_pos)
            hole = Part.makeCylinder(
                0.5 * plate.bolt_hole_diameter_mm,
                plate.lug_thickness_mm + 1.0,
                hole_center - scaled(axis_t, 0.5 * plate.lug_thickness_mm + 0.5),
                axis_t,
            )
            lugs = lugs.cut(hole)

    return lugs


def _build_plate_stiffeners(plate: PlateConfig) -> Part.Shape:
    center, axis_t, axis_v, axis_w = _plate_axes(plate)
    if plate.stiffener_count == 1:
        offsets = [0.0]
    else:
        span = plate.width_mm - plate.stiffener_thickness_mm - (2.0 * plate.lug_thickness_mm)
        step = span / float(plate.stiffener_count - 1)
        offsets = [(-0.5 * span) + (step * float(i)) for i in range(plate.stiffener_count)]

    # [EN] Place ribs on the outward normal side of each mount plane so the LOS opening remains on the source-facing side. / [CN] 加劲肋放在各安装平面的外法向一侧，保证 LOS 开孔位于源点朝向侧。
    side_sign = 1.0
    if plate.mount_plane == "xz":
        side_sign = 1.0 if plate.offset_y_mm >= 0.0 else -1.0
    elif plate.mount_plane == "xy":
        side_sign = 1.0 if plate.z_mm >= 0.0 else -1.0
    elif plate.mount_plane == "yz":
        side_sign = 1.0 if plate.offset_x_mm >= 0.0 else -1.0
    rib_center_base = center + scaled(axis_t, side_sign * 0.5 * (plate.thickness_mm + plate.stiffener_height_mm))

    ribs: list[Part.Shape] = []
    for v_offset in offsets:
        rib = slit_prism(
            center=rib_center_base + scaled(axis_v, v_offset),
            axis_u=axis_t,
            axis_v=axis_v,
            axis_w=axis_w,
            length_mm=plate.stiffener_height_mm,
            width_mm=plate.stiffener_thickness_mm,
            height_mm=plate.stiffener_length_mm,
        )
        ribs.append(rib)

    out = ribs[0]
    for rib in ribs[1:]:
        out = out.fuse(rib)
    return out


def build_load_bearing_plate(
    cfg: GeometryConfig,
    plate_key: str,
    plate: PlateConfig,
    placements: list[DetectorPlacement],
) -> Part.Shape:
    # [EN] Fused base+lugs+stiffeners encode a deterministic structural load path for validation and assembly mapping. / [CN] 融合主板+连接耳+加劲肋，形成可验证且可装配映射的确定性承载路径。
    if plate.opening_style == "annular_sector":
        base = _build_plate_base_with_openings(plate)
    elif plate.opening_style == "rounded_slot":
        center, axis_t, axis_v, axis_w = _plate_axes(plate)
        base = slit_prism(
            center=center,
            axis_u=axis_t,
            axis_v=axis_v,
            axis_w=axis_w,
            length_mm=plate.thickness_mm,
            width_mm=plate.width_mm,
            height_mm=plate.height_mm,
        )
        for polyline in plate_opening_local_polylines(cfg, plate_key, plate, placements):
            base = base.cut(_rounded_slot_cut(plate, polyline, plate_slot_half_width_mm(cfg)))
    elif plate.opening_style == "los_tube":
        center, axis_t, axis_v, axis_w = _plate_axes(plate)
        base = slit_prism(
            center=center,
            axis_u=axis_t,
            axis_v=axis_v,
            axis_w=axis_w,
            length_mm=plate.thickness_mm,
            width_mm=plate.width_mm,
            height_mm=plate.height_mm,
        )
        for placement in placements:
            cut = target_detector_los_tube(cfg, placement, plate_slot_half_width_mm(cfg))
            if cut is not None:
                base = base.cut(cut)
    else:
        raise ValueError(f"unsupported opening_style {plate.opening_style!r}")
    lugs = _build_plate_lugs_with_bolt_holes(plate)
    stiffeners = _build_plate_stiffeners(plate)
    return base.fuse(lugs).fuse(stiffeners)


def _chamber_plate_cutout(cfg: GeometryConfig) -> Part.Shape:
    core = cfg.chamber.core
    margin = cfg.clearance.plate_chamber_cutout_margin_mm
    z_min, _ = chamber_z_bounds(core)
    return Part.makeBox(
        core.size_x_mm + 2.0 * margin,
        core.size_y_mm + 2.0 * margin,
        core.size_z_mm + 2.0 * margin,
        App.Vector(
            -0.5 * core.size_x_mm - margin,
            -0.5 * core.size_y_mm - margin,
            z_min - margin,
        ),
    )


def _detector_mount_plate_holes(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement],
) -> dict[str, list[Part.Shape]]:
    holes: dict[str, list[Part.Shape]] = {"h": [], "v1": [], "v2": []}
    clamp_cfg = cfg.detector.clamp
    for placement in placements:
        layout = detector_fixture_geometry(cfg, placement)
        plate = _plate_cfg_from_sector(cfg, placement.sector_name)
        # [EN] Plate drilling follows the resolved fixture geometry so the 4-hole rectangle is derived from the actual detector support pose, not from a plate-local template detached from assembly reality. / [CN] 板上钻孔跟随已解算的夹具几何，因此四孔矩形来自真实探测器支撑姿态，而不是脱离装配现实的板面模板。
        for center in layout.plate_hole_centers:
            hole = Part.makeCylinder(
                0.5 * clamp_cfg.mount_bolt_hole_diameter_mm,
                plate.thickness_mm + 2.0,
                center - scaled(layout.plate_normal, 0.5 * plate.thickness_mm + 1.0),
                layout.plate_normal,
            )
            holes[plate_key_for_sector(placement.sector_name)].append(hole)
    return holes


def _plate_rectangular_relief_cuts(
    cfg: GeometryConfig,
    plate: PlateConfig,
    placements: list[DetectorPlacement],
) -> list[Part.Shape]:
    if not placements:
        return []

    center, axis_t, axis_v, axis_w = _plate_axes(plate)
    cut_depth_mm = plate.thickness_mm + plate.lug_thickness_mm + plate.stiffener_height_mm + 20.0
    relief_margin_mm = max(cfg.clearance.los_margin_mm, 6.0)
    half_plate_width = 0.5 * plate.width_mm
    half_plate_height = 0.5 * plate.height_mm
    package_band_half_mm = 0.5 * plate.thickness_mm + relief_margin_mm
    plate_band_min = center.y - package_band_half_mm
    plate_band_max = center.y + package_band_half_mm
    cone_front_face_radius_mm = 0.5 * cfg.detector.clamp.detector_diameter_mm

    cuts: list[Part.Shape] = []
    for placement in placements:
        housing, clamp_a, clamp_b, adapter_block, mount_base = build_detector_fixture(cfg, placement)
        local_min_u: float | None = None
        local_max_u = 0.0
        local_min_v: float | None = None
        local_max_v = 0.0

        # [EN] Relief windows are estimated from actual fixture bounding boxes intersecting the H-plate thickness band, which keeps the cut local to interfering service hardware. / [CN] 让位窗按实际夹具包围盒与 H 板厚度带的相交来估算，使切口局限在真正干涉的维护硬件附近。
        for contributor in (housing, clamp_a, clamp_b, adapter_block, mount_base):
            bbox = contributor.BoundBox
            if bbox.YMax < plate_band_min or bbox.YMin > plate_band_max:
                continue

            contributor_min_u = bbox.XMin - plate.offset_x_mm
            contributor_max_u = bbox.XMax - plate.offset_x_mm
            contributor_min_v = bbox.ZMin - plate.z_mm
            contributor_max_v = bbox.ZMax - plate.z_mm

            if local_min_u is None or local_min_v is None:
                local_min_u = contributor_min_u
                local_max_u = contributor_max_u
                local_min_v = contributor_min_v
                local_max_v = contributor_max_v
            else:
                local_min_u = min(local_min_u, contributor_min_u)
                local_max_u = max(local_max_u, contributor_max_u)
                local_min_v = min(local_min_v, contributor_min_v)
                local_max_v = max(local_max_v, contributor_max_v)

        cone_bounds = _cone_band_local_uv_bounds(
            cfg,
            placement,
            plate,
            package_band_half_mm,
            cone_front_face_radius_mm,
        )
        if cone_bounds is not None:
            cone_min_u, cone_max_u, cone_min_v, cone_max_v = cone_bounds
            if local_min_u is None or local_min_v is None:
                local_min_u = cone_min_u
                local_max_u = cone_max_u
                local_min_v = cone_min_v
                local_max_v = cone_max_v
            else:
                local_min_u = min(local_min_u, cone_min_u)
                local_max_u = max(local_max_u, cone_max_u)
                local_min_v = min(local_min_v, cone_min_v)
                local_max_v = max(local_max_v, cone_max_v)
        else:
            los_hit = plate_los_plane_hit_point(cfg, placement, plate)
            if los_hit is not None:
                hit_u, hit_v = _plate_local_uv_from_world(plate, los_hit)
                if abs(hit_u) <= half_plate_width and abs(hit_v) <= half_plate_height:
                    los_radius_mm = plate_slot_half_width_mm(cfg)
                    los_min_u = hit_u - los_radius_mm
                    los_max_u = hit_u + los_radius_mm
                    los_min_v = hit_v - los_radius_mm
                    los_max_v = hit_v + los_radius_mm
                    if local_min_u is None or local_min_v is None:
                        local_min_u = los_min_u
                        local_max_u = los_max_u
                        local_min_v = los_min_v
                        local_max_v = los_max_v
                    else:
                        local_min_u = min(local_min_u, los_min_u)
                        local_max_u = max(local_max_u, los_max_u)
                        local_min_v = min(local_min_v, los_min_v)
                        local_max_v = max(local_max_v, los_max_v)

        if local_min_u is None or local_min_v is None:
            continue

        min_u = max(-half_plate_width, local_min_u - relief_margin_mm)
        max_u = min(half_plate_width, local_max_u + relief_margin_mm)
        min_v = max(-half_plate_height, local_min_v - relief_margin_mm)
        max_v = min(half_plate_height, local_max_v + relief_margin_mm)
        if (max_u - min_u) <= 1e-6 or (max_v - min_v) <= 1e-6:
            continue

        # [EN] Rectangular reliefs follow the actual detector package plus target-to-detector LOS overlap with the H plate, matching the photographed service-panel style without linking unrelated material. / [CN] 长方形让位孔按探测器包络与靶到探测器真实 LOS 对 H 板的实际相交范围生成，贴近照片里的维护面板做法，不再把无关区域连成槽口。
        cuts.append(
            slit_prism(
                center=_plate_world_from_local_uv(plate, 0.5 * (min_u + max_u), 0.5 * (min_v + max_v)),
                axis_u=axis_t,
                axis_v=axis_v,
                axis_w=axis_w,
                length_mm=cut_depth_mm,
                width_mm=max_u - min_u,
                height_mm=max_v - min_v,
            )
        )

    return cuts


def build_all_plates(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement] | None = None,
) -> dict[str, Part.Shape]:
    if placements is None:
        raise ValueError("build_all_plates requires detector placements for plate opening generation")

    placements_by_plate: dict[str, list[DetectorPlacement]] = {"h": [], "v1": [], "v2": []}
    for placement in placements:
        placements_by_plate[plate_key_for_sector(placement.sector_name)].append(placement)

    plates = {
        "HPlate": build_load_bearing_plate(cfg, "h", cfg.plate.h, placements_by_plate["h"]),
        "VPlate1": build_load_bearing_plate(cfg, "v1", cfg.plate.v1, placements_by_plate["v1"]),
        "VPlate2": build_load_bearing_plate(cfg, "v2", cfg.plate.v2, placements_by_plate["v2"]),
    }

    if cfg.clearance.disable_plate_cuts:
        # [EN] Preview mode keeps load-bearing plates as full solids to compare legacy panel placement/size before opening strategy is finalized. / [CN] 预览模式保留完整承重板实体，用于在确定开孔策略前先对齐旧版板位与尺寸。
        return plates

    cutout = _chamber_plate_cutout(cfg)
    plate_cfg_map = {"HPlate": cfg.plate.h, "VPlate1": cfg.plate.v1, "VPlate2": cfg.plate.v2}
    for name, plate in list(plates.items()):
        if plate_cfg_map[name].opening_style == "rounded_slot":
            continue
        # [EN] Remove chamber overlap from full load-bearing solids (base+lugs+stiffeners), preserving strict no-overlap assembly gate. / [CN] 对完整承重实体（主板+连接耳+加劲肋）执行去腔体干涉挖孔，满足严格零重叠装配门。
        plates[name] = plate.cut(cutout)

    h_relief_placements = [placement for placement in placements if plate_key_for_sector(placement.sector_name) != "h"]
    for cut in _plate_rectangular_relief_cuts(cfg, cfg.plate.h, h_relief_placements):
        plates["HPlate"] = plates["HPlate"].cut(cut)

    holes_by_plate = _detector_mount_plate_holes(cfg, placements)
    plate_key_map = {"HPlate": "h", "VPlate1": "v1", "VPlate2": "v2"}
    for plate_name, key in plate_key_map.items():
        for hole in holes_by_plate[key]:
            plates[plate_name] = plates[plate_name].cut(hole)
    return plates


def _plate_cfg_from_sector(cfg: GeometryConfig, sector_name: str) -> PlateConfig:
    key = plate_key_for_sector(sector_name)
    if key == "h":
        return cfg.plate.h
    if key == "v1":
        return cfg.plate.v1
    if key == "v2":
        return cfg.plate.v2
    raise ValueError(f"unsupported sector_name: {sector_name}")


def _project_point_to_plate(point: App.Vector, plate: PlateConfig) -> App.Vector:
    # [EN] Detector base centers are defined by orthogonal projection onto plate mount planes to match the frozen mounting semantics. / [CN] 探测器底座中心按板法向正交投影到安装平面，匹配冻结安装语义。
    if plate.mount_plane == "xy":
        return App.Vector(point.x, point.y, plate.z_mm)
    if plate.mount_plane == "xz":
        return App.Vector(point.x, plate.offset_y_mm, point.z)
    if plate.mount_plane == "yz":
        return App.Vector(plate.offset_x_mm, point.y, point.z)
    raise ValueError(f"unsupported mount_plane: {plate.mount_plane}")


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
    raise ValueError(f"unsupported mount_plane: {plate.mount_plane}")


def _detector_mount_axes(
    direction: App.Vector,
    plate: PlateConfig,
    fallback_lateral_axis: App.Vector,
) -> tuple[App.Vector, App.Vector, App.Vector]:
    plate_normal = _plate_outward_normal(plate)
    inward_normal = scaled(plate_normal, -1.0)
    projected = inward_normal - scaled(direction, _dot(inward_normal, direction))
    if _vector_length(projected) <= 1e-9:
        projected = inward_normal

    mount_axis = _normalize_vector(projected)
    lateral_axis = direction.cross(mount_axis)
    if _vector_length(lateral_axis) <= 1e-9:
        lateral_axis = fallback_lateral_axis
    else:
        lateral_axis = _normalize_vector(lateral_axis)

    return mount_axis, lateral_axis, plate_normal


def _detector_mount_base_axes(
    direction: App.Vector,
    plate_normal: App.Vector,
    fallback_u_axis: App.Vector,
) -> tuple[App.Vector, App.Vector]:
    in_plane_direction = direction - scaled(plate_normal, _dot(direction, plate_normal))
    if _vector_length(in_plane_direction) <= 1e-9:
        in_plane_direction = fallback_u_axis

    base_u_axis = _normalize_vector(in_plane_direction)
    base_v_axis = plate_normal.cross(base_u_axis)
    if _vector_length(base_v_axis) <= 1e-9:
        base_v_axis = fallback_u_axis.cross(plate_normal)
    base_v_axis = _normalize_vector(base_v_axis)
    return base_u_axis, base_v_axis


def detector_fixture_geometry(
    cfg: GeometryConfig,
    placement: DetectorPlacement,
) -> DetectorFixtureGeometry:
    clamp_cfg = cfg.detector.clamp
    adapter_cfg = cfg.detector.adapter_block
    plate = _plate_cfg_from_sector(cfg, placement.sector_name)

    front_center = front_face_center(placement)
    direction, _axis_v, axis_w = local_basis_from_direction(placement.direction)
    _, _, plate_u_axis, _plate_v_axis = _plate_axes(plate)
    mount_axis, mount_lateral_axis, plate_normal = _detector_mount_axes(direction, plate, axis_w)
    base_u_axis, base_v_axis = _detector_mount_base_axes(direction, plate_normal, plate_u_axis)

    clamp_center = front_center + scaled(direction, clamp_cfg.support_overlap_mm)

    effective_radial_standoff = adapter_cfg.radial_standoff_mm
    if not cfg.stand.enable_plate_ties:
        # [EN] Direct-mount mode keeps detector support compact to avoid visually long cantilever connectors. / [CN] 直连模式下缩短径向悬挑，避免出现过长悬臂连接件的观感。
        effective_radial_standoff = max(4.0, min(adapter_cfg.radial_standoff_mm, 0.5 * adapter_cfg.radial_standoff_mm + 2.0))
    support_to_block_center = 0.5 * clamp_cfg.outer_diameter_mm + effective_radial_standoff + 0.5 * adapter_cfg.width_mm
    block_center = clamp_center - scaled(mount_axis, support_to_block_center)

    bridge_thickness = max(8.0, min(16.0, 0.25 * adapter_cfg.height_mm))
    bridge_axis_offset = (0.25 * adapter_cfg.width_mm) if not cfg.stand.enable_plate_ties else (0.5 * adapter_cfg.width_mm)
    bridge_center = block_center - scaled(mount_axis, bridge_axis_offset + 0.5 * bridge_thickness)
    bridge_plate_face_center = bridge_center - scaled(mount_axis, 0.5 * bridge_thickness)

    mount_projection = _project_point_to_plate(front_center, plate)
    mount_base_center = mount_projection + scaled(
        plate_normal,
        0.5 * (plate.thickness_mm + clamp_cfg.mount_base_thickness_mm),
    )
    mount_base_top_center = mount_base_center + scaled(plate_normal, 0.5 * clamp_cfg.mount_base_thickness_mm)

    upright_width = max(12.0, min(24.0, 0.2 * clamp_cfg.mount_base_u_mm))
    upright_depth = max(8.0, min(18.0, 0.22 * clamp_cfg.mount_base_v_mm))
    max_upright_offset = 0.5 * (clamp_cfg.mount_base_u_mm - upright_width - 6.0)
    upright_offset = min(max_upright_offset, 0.2 * clamp_cfg.mount_base_u_mm, 26.0)
    if upright_offset < 6.0:
        upright_offsets = (0.0,)
    else:
        upright_offsets = (-upright_offset, upright_offset)

    upright_length = _axis_distance(bridge_plate_face_center, mount_base_top_center, mount_axis)
    bridge_span = max(upright_width + 6.0, 2.0 * abs(upright_offsets[0]) + upright_width - 6.0)
    bridge_depth = max(upright_depth, min(20.0, 1.1 * upright_depth))

    plate_hole_centers: list[App.Vector] = []
    base_hole_centers: list[App.Vector] = []
    for du in (-0.5 * clamp_cfg.mount_bolt_pitch_u_mm, 0.5 * clamp_cfg.mount_bolt_pitch_u_mm):
        for dv in (-0.5 * clamp_cfg.mount_bolt_pitch_v_mm, 0.5 * clamp_cfg.mount_bolt_pitch_v_mm):
            in_plane_offset = scaled(base_u_axis, du) + scaled(base_v_axis, dv)
            plate_hole_centers.append(mount_projection + in_plane_offset)
            base_hole_centers.append(mount_base_center + in_plane_offset)

    return DetectorFixtureGeometry(
        front_center=front_center,
        direction=direction,
        mount_axis=mount_axis,
        mount_lateral_axis=mount_lateral_axis,
        plate_normal=plate_normal,
        base_u_axis=base_u_axis,
        base_v_axis=base_v_axis,
        mount_projection=mount_projection,
        mount_base_center=mount_base_center,
        mount_base_top_center=mount_base_top_center,
        clamp_center=clamp_center,
        block_center=block_center,
        bridge_center=bridge_center,
        bridge_plate_face_center=bridge_plate_face_center,
        bridge_thickness_mm=bridge_thickness,
        bridge_span_mm=bridge_span,
        bridge_depth_mm=bridge_depth,
        upright_offsets=upright_offsets,
        upright_length_mm=upright_length,
        upright_width_mm=upright_width,
        upright_depth_mm=upright_depth,
        plate_hole_centers=tuple(plate_hole_centers),
        base_hole_centers=tuple(base_hole_centers),
    )


def build_plate_load_ties(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    out: dict[str, Part.Shape] = {}
    # [EN] When direct mount mode is enabled, detector bases are bolted to plates without auxiliary plate-to-stand ties. / [CN] 直连模式下探测器底座直接固定到板件，不生成板到支架的辅助拉杆件。
    if not cfg.stand.enable_plate_ties:
        return out

    core = cfg.chamber.core
    stand = cfg.stand

    chamber_bottom_y = -0.5 * core.size_y_mm
    base_top_y = chamber_bottom_y - stand.chamber_support_height_mm

    for key, plate in (("H", cfg.plate.h), ("V1", cfg.plate.v1), ("V2", cfg.plate.v2)):
        center, _, axis_v, axis_w = _plate_axes(plate)
        lug_axis = axis_v
        lug_offset_half = 0.5 * (plate.width_mm + plate.lug_length_mm)
        if plate.mount_plane == "xz":
            # [EN] Route xz-plate ties along z-edge pickups so columns stay outside up/down detector corridors crossing near x~0. / [CN] xz 板拉杆改为 z 向边缘取点，避开在 x~0 穿越的上下探测器通道。
            lug_axis = axis_w
            lug_offset_half = 0.9 * 0.5 * (plate.height_mm + plate.lug_length_mm)
        if plate.mount_plane == "yz":
            # [EN] Compress tie pickup span on yz plates to keep tie columns out of dominant detector flight corridor while preserving two-point load transfer. / [CN] 对 yz 板压缩拉杆取点跨度，在保持双点传力的同时避开主要探测器飞行通道。
            lug_axis = axis_w
            lug_offset_half = 0.5 * (plate.height_mm + plate.lug_length_mm)
            lug_offset_half *= 0.4
        lug_offsets = (-lug_offset_half, lug_offset_half)

        for idx, v_offset in enumerate(lug_offsets, start=1):
            lug_center = center + scaled(lug_axis, v_offset)
            tie_len = max(20.0, lug_center.y - base_top_y)
            tie_axis = App.Vector(0.0, -1.0, 0.0)

            column = Part.makeCylinder(
                0.5 * stand.plate_tie_column_diameter_mm,
                tie_len,
                App.Vector(lug_center.x, lug_center.y, lug_center.z),
                tie_axis,
            )

            top_cap_center = App.Vector(
                lug_center.x,
                lug_center.y - 0.5 * stand.plate_tie_cap_thickness_mm,
                lug_center.z,
            )
            top_cap = slit_prism(
                center=top_cap_center,
                axis_u=App.Vector(0.0, 1.0, 0.0),
                axis_v=lug_axis,
                axis_w=App.Vector(0.0, 0.0, 1.0),
                length_mm=stand.plate_tie_cap_thickness_mm,
                width_mm=stand.plate_tie_cap_width_mm,
                height_mm=stand.plate_tie_cap_height_mm,
            )

            bottom_cap_center = App.Vector(
                lug_center.x,
                base_top_y + 0.5 * stand.plate_tie_cap_thickness_mm,
                lug_center.z,
            )
            bottom_cap = slit_prism(
                center=bottom_cap_center,
                axis_u=App.Vector(0.0, 1.0, 0.0),
                axis_v=lug_axis,
                axis_w=App.Vector(0.0, 0.0, 1.0),
                length_mm=stand.plate_tie_cap_thickness_mm,
                width_mm=stand.plate_tie_cap_width_mm,
                height_mm=stand.plate_tie_cap_height_mm,
            )

            bolt_length = tie_len + 2.0 * stand.plate_tie_cap_thickness_mm
            bolt_origin = App.Vector(
                lug_center.x,
                lug_center.y + 0.5 * stand.plate_tie_cap_thickness_mm,
                lug_center.z,
            )
            bolt = Part.makeCylinder(
                0.5 * stand.plate_tie_bolt_diameter_mm,
                bolt_length,
                bolt_origin,
                tie_axis,
            )

            hole = Part.makeCylinder(
                0.5 * (stand.plate_tie_bolt_diameter_mm + 0.8),
                stand.plate_tie_cap_thickness_mm + 1.0,
                top_cap_center + App.Vector(0.0, 0.5 * stand.plate_tie_cap_thickness_mm + 0.5, 0.0),
                tie_axis,
            )
            top_cap = top_cap.cut(hole)
            hole_bottom = Part.makeCylinder(
                0.5 * (stand.plate_tie_bolt_diameter_mm + 0.8),
                stand.plate_tie_cap_thickness_mm + 1.0,
                bottom_cap_center + App.Vector(0.0, 0.5 * stand.plate_tie_cap_thickness_mm + 0.5, 0.0),
                tie_axis,
            )
            bottom_cap = bottom_cap.cut(hole_bottom)

            out[f"PlateLoadTieColumn_{key}_{idx}"] = column
            out[f"PlateLoadTieTopCap_{key}_{idx}"] = top_cap
            out[f"PlateLoadTieBottomCap_{key}_{idx}"] = bottom_cap
            out[f"PlateLoadTieBolt_{key}_{idx}"] = bolt

    return out


def build_detector_fixture(
    cfg: GeometryConfig,
    placement: DetectorPlacement,
) -> tuple[Part.Shape, Part.Shape, Part.Shape, Part.Shape, Part.Shape]:
    clamp_cfg = cfg.detector.clamp
    adapter_cfg = cfg.detector.adapter_block

    front_center = front_face_center(placement)
    direction, axis_v, axis_w = local_basis_from_direction(placement.direction)

    housing = Part.makeCylinder(
        0.5 * clamp_cfg.detector_diameter_mm,
        clamp_cfg.housing_length_mm,
        front_center,
        direction,
    )

    clamp_center = front_center + scaled(direction, clamp_cfg.support_overlap_mm)
    clamp_origin = clamp_center - scaled(direction, 0.5 * clamp_cfg.width_mm)
    clamp_ring = tube_shape(
        outer_diameter_mm=clamp_cfg.outer_diameter_mm,
        inner_diameter_mm=clamp_cfg.inner_diameter_mm,
        length_mm=clamp_cfg.width_mm,
        origin=clamp_origin,
        axis=direction,
    )

    split_cut = slit_prism(
        center=clamp_center,
        axis_u=direction,
        axis_v=axis_v,
        axis_w=axis_w,
        length_mm=clamp_cfg.width_mm + 2.0,
        width_mm=clamp_cfg.split_gap_mm,
        height_mm=2.2 * clamp_cfg.outer_diameter_mm,
    )
    split_ring = clamp_ring.cut(split_cut)

    key_center = (
        clamp_center
        + scaled(axis_w, 0.5 * clamp_cfg.inner_diameter_mm - 0.5 * clamp_cfg.anti_rotation_key_depth_mm)
        + scaled(axis_v, 0.25 * clamp_cfg.anti_rotation_key_width_mm)
    )
    key_rib = slit_prism(
        center=key_center,
        axis_u=direction,
        axis_v=axis_v,
        axis_w=axis_w,
        length_mm=clamp_cfg.anti_rotation_key_length_mm,
        width_mm=clamp_cfg.anti_rotation_key_width_mm,
        height_mm=clamp_cfg.anti_rotation_key_depth_mm,
    )
    # [EN] The anti-rotation key is fused before half-splitting so key and bore remain geometrically tied under all channel poses. / [CN] 防转键在分半前并入抱箍，确保各通道姿态下键位与内孔几何关系恒定。
    split_ring = split_ring.fuse(key_rib)

    half_mask = 1.1 * clamp_cfg.outer_diameter_mm
    mask_a = slit_prism(
        center=clamp_center + scaled(axis_v, 0.25 * clamp_cfg.outer_diameter_mm),
        axis_u=direction,
        axis_v=axis_v,
        axis_w=axis_w,
        length_mm=clamp_cfg.width_mm + 3.0,
        width_mm=half_mask,
        height_mm=2.4 * clamp_cfg.outer_diameter_mm,
    )
    mask_b = slit_prism(
        center=clamp_center - scaled(axis_v, 0.25 * clamp_cfg.outer_diameter_mm),
        axis_u=direction,
        axis_v=axis_v,
        axis_w=axis_w,
        length_mm=clamp_cfg.width_mm + 3.0,
        width_mm=half_mask,
        height_mm=2.4 * clamp_cfg.outer_diameter_mm,
    )

    shoulder = tube_shape(
        outer_diameter_mm=clamp_cfg.inner_diameter_mm + 2.0 * clamp_cfg.shoulder_height_mm,
        inner_diameter_mm=clamp_cfg.inner_diameter_mm,
        length_mm=clamp_cfg.end_stop_length_mm,
        origin=clamp_center + scaled(direction, 0.5 * clamp_cfg.width_mm),
        axis=direction,
    )
    end_stop = Part.makeCylinder(
        0.5 * (clamp_cfg.inner_diameter_mm + 2.0 * clamp_cfg.shoulder_height_mm),
        clamp_cfg.end_stop_length_mm,
        clamp_center - scaled(direction, 0.5 * clamp_cfg.width_mm + clamp_cfg.end_stop_length_mm),
        direction,
    )

    clamp_half_a = split_ring.common(mask_a).fuse(shoulder.common(mask_a)).fuse(end_stop.common(mask_a))
    clamp_half_b = split_ring.common(mask_b).fuse(shoulder.common(mask_b)).fuse(end_stop.common(mask_b))

    ear_offsets_u = (
        -0.5 * clamp_cfg.clamp_bolt_pitch_mm,
        0.5 * clamp_cfg.clamp_bolt_pitch_mm,
    )
    for side_sign in (1.0, -1.0):
        for u_offset in ear_offsets_u:
            ear_center = (
                clamp_center
                + scaled(direction, u_offset)
                + scaled(axis_v, side_sign * (0.5 * clamp_cfg.outer_diameter_mm + 0.5 * clamp_cfg.clamp_ear_width_mm))
            )
            ear = slit_prism(
                center=ear_center,
                axis_u=direction,
                axis_v=axis_v,
                axis_w=axis_w,
                length_mm=clamp_cfg.clamp_ear_length_mm,
                width_mm=clamp_cfg.clamp_ear_width_mm,
                height_mm=clamp_cfg.clamp_ear_thickness_mm,
            )
            if side_sign > 0.0:
                clamp_half_a = clamp_half_a.fuse(ear)
            else:
                clamp_half_b = clamp_half_b.fuse(ear)

    bolt_span = clamp_cfg.outer_diameter_mm + 2.0 * clamp_cfg.clamp_ear_width_mm + 2.0
    for u_offset in ear_offsets_u:
        bolt_hole = Part.makeCylinder(
            0.5 * clamp_cfg.clamp_bolt_diameter_mm,
            bolt_span,
            clamp_center + scaled(direction, u_offset) - scaled(axis_v, 0.5 * bolt_span),
            axis_v,
        )
        clamp_half_a = clamp_half_a.cut(bolt_hole)
        clamp_half_b = clamp_half_b.cut(bolt_hole)

    layout = detector_fixture_geometry(cfg, placement)
    adapter_block = slit_prism(
        center=layout.block_center,
        axis_u=direction,
        axis_v=layout.mount_axis,
        axis_w=layout.mount_lateral_axis,
        length_mm=adapter_cfg.length_mm,
        width_mm=adapter_cfg.width_mm,
        height_mm=adapter_cfg.height_mm,
    )
    adapter_block.rotate(layout.block_center, layout.mount_lateral_axis, adapter_cfg.tilt_deg)

    mount_base_plate = slit_prism(
        center=layout.mount_base_center,
        axis_u=layout.plate_normal,
        axis_v=layout.base_u_axis,
        axis_w=layout.base_v_axis,
        length_mm=clamp_cfg.mount_base_thickness_mm,
        width_mm=clamp_cfg.mount_base_u_mm,
        height_mm=clamp_cfg.mount_base_v_mm,
    )
    hole_length = clamp_cfg.mount_base_thickness_mm + 1.0
    for hole_center in layout.base_hole_centers:
        hole = Part.makeCylinder(
            0.5 * clamp_cfg.mount_bolt_hole_diameter_mm,
            hole_length,
            hole_center - scaled(layout.plate_normal, 0.5 * hole_length),
            layout.plate_normal,
        )
        mount_base_plate = mount_base_plate.cut(hole)

    # [EN] The base-uprights-bridge stack is intentionally continuous so the detector fixture has a load path to the assigned HVV plate instead of a floating projected pad. / [CN] 底座-立板-桥接件保持连续实体，确保探测器夹具对指定 HVV 板形成承载路径，而非仅有投影落点。
    uprights: list[Part.Shape] = []
    for offset in layout.upright_offsets:
        upright = slit_prism(
            center=layout.mount_base_top_center + scaled(layout.mount_axis, 0.5 * layout.upright_length_mm) + scaled(direction, offset),
            axis_u=layout.mount_axis,
            axis_v=direction,
            axis_w=layout.mount_lateral_axis,
            length_mm=layout.upright_length_mm,
            width_mm=layout.upright_width_mm,
            height_mm=layout.upright_depth_mm,
        )
        uprights.append(upright)

    top_bridge = slit_prism(
        center=layout.bridge_center,
        axis_u=layout.mount_axis,
        axis_v=direction,
        axis_w=layout.mount_lateral_axis,
        length_mm=layout.bridge_thickness_mm,
        width_mm=layout.bridge_span_mm,
        height_mm=layout.bridge_depth_mm,
    )

    mount_base = mount_base_plate
    for upright in uprights:
        mount_base = mount_base.fuse(upright)
    mount_base = mount_base.fuse(top_bridge)

    return housing, clamp_half_a, clamp_half_b, adapter_block, mount_base


def _target_slot_positions_x(cfg: GeometryConfig) -> tuple[float, float, float]:
    ladder = cfg.target.ladder
    if ladder is None:
        raise ValueError("linear ladder target config is required for slot-based holder positions")
    pitch = ladder.slot_pitch_mm
    return (-pitch, 0.0, pitch)


def _rotated_shape(shape: Part.Shape, center: App.Vector, axis: App.Vector, angle_deg: float) -> Part.Shape:
    if abs(angle_deg) <= 1e-9:
        return shape
    rotated = shape.copy()
    rotated.rotate(center, axis, angle_deg)
    return rotated


def _single_rotary_pivot_center(cfg: GeometryConfig) -> App.Vector:
    rotary = cfg.target.rotary
    if rotary is None:
        raise ValueError("single_rotary target config requires geometry.target.rotary")
    return App.Vector(rotary.pivot_x_mm, 0.0, 0.0)


def single_rotary_target_center(cfg: GeometryConfig, angle_deg: float) -> App.Vector:
    rotary = cfg.target.rotary
    if rotary is None:
        raise ValueError("single_rotary target config requires geometry.target.rotary")
    theta = math.radians(angle_deg)
    pivot = _single_rotary_pivot_center(cfg)
    # [EN] The single target swings in the xz plane about the top-mounted Y-axis feedthrough so work and park poses remain analytically traceable. / [CN] 单靶绕顶部 Y 轴馈通在 xz 平面摆转，使工作位与停靠位都能用解析几何稳定追踪。
    return pivot + App.Vector(
        -rotary.arm_length_mm * math.cos(theta),
        0.0,
        rotary.arm_length_mm * math.sin(theta),
    )


def _build_linear_target_ladder(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    ladder = cfg.target.ladder
    if ladder is None:
        raise ValueError("linear_ladder mode requires geometry.target.ladder")
    slots = _target_slot_positions_x(cfg)

    carriage = Part.makeBox(
        ladder.carriage_width_mm,
        ladder.carriage_height_mm,
        ladder.carriage_thickness_mm,
        App.Vector(
            -0.5 * ladder.carriage_width_mm,
            -0.5 * ladder.carriage_height_mm,
            -0.5 * ladder.carriage_thickness_mm,
        ),
    )

    for x_pos in slots:
        window = Part.makeCylinder(
            0.5 * ladder.slot_window_diameter_mm,
            ladder.carriage_thickness_mm + 1.0,
            App.Vector(x_pos, 0.0, -0.5 * ladder.carriage_thickness_mm - 0.5),
            App.Vector(0.0, 0.0, 1.0),
        )
        carriage = carriage.cut(window)

    rail_origin_x = -0.5 * ladder.carriage_width_mm
    rail_1 = Part.makeCylinder(
        0.5 * ladder.rail_diameter_mm,
        ladder.carriage_width_mm,
        App.Vector(rail_origin_x, 0.5 * ladder.rail_span_mm, 0.0),
        App.Vector(1.0, 0.0, 0.0),
    )
    rail_2 = Part.makeCylinder(
        0.5 * ladder.rail_diameter_mm,
        ladder.carriage_width_mm,
        App.Vector(rail_origin_x, -0.5 * ladder.rail_span_mm, 0.0),
        App.Vector(1.0, 0.0, 0.0),
    )

    shaft_origin = App.Vector(0.0, 0.5 * cfg.chamber.core.size_y_mm, 0.0)
    shaft = Part.makeCylinder(
        0.5 * ladder.feedthrough_shaft_diameter_mm,
        ladder.feedthrough_length_mm,
        shaft_origin,
        App.Vector(0.0, 1.0, 0.0),
    )
    handwheel = Part.makeCylinder(
        0.5 * ladder.handwheel_diameter_mm,
        8.0,
        shaft_origin + App.Vector(0.0, ladder.feedthrough_length_mm, 0.0),
        App.Vector(0.0, 1.0, 0.0),
    )

    motor_mount = Part.makeBox(
        ladder.motor_mount_width_mm,
        ladder.motor_mount_thickness_mm,
        ladder.motor_mount_height_mm,
        App.Vector(
            -0.5 * ladder.motor_mount_width_mm,
            0.5 * cfg.chamber.core.size_y_mm + 0.5 * ladder.feedthrough_length_mm,
            -0.5 * ladder.motor_mount_height_mm,
        ),
    )

    stop_y = 0.5 * cfg.chamber.core.size_y_mm + ladder.feedthrough_length_mm - ladder.hard_stop_thickness_mm
    hard_stop_a = Part.makeBox(
        ladder.hard_stop_thickness_mm,
        ladder.hard_stop_thickness_mm,
        26.0,
        App.Vector(
            -0.5 * ladder.hard_stop_span_mm,
            stop_y,
            -13.0,
        ),
    )
    hard_stop_b = Part.makeBox(
        ladder.hard_stop_thickness_mm,
        ladder.hard_stop_thickness_mm,
        26.0,
        App.Vector(
            0.5 * ladder.hard_stop_span_mm - ladder.hard_stop_thickness_mm,
            stop_y,
            -13.0,
        ),
    )

    index_disk = Part.makeCylinder(
        0.5 * ladder.index_disk_diameter_mm,
        ladder.index_disk_thickness_mm,
        shaft_origin + App.Vector(0.0, ladder.feedthrough_length_mm - ladder.index_disk_thickness_mm, 0.0),
        App.Vector(0.0, 1.0, 0.0),
    )
    index_pin = Part.makeCylinder(
        0.5 * ladder.index_pin_diameter_mm,
        ladder.index_pin_length_mm,
        shaft_origin
        + App.Vector(
            0.5 * ladder.index_disk_diameter_mm,
            ladder.feedthrough_length_mm - ladder.index_disk_thickness_mm,
            0.0,
        ),
        App.Vector(0.0, 1.0, 0.0),
    )

    return {
        "TargetLadderCarriage": carriage,
        "TargetLadderRail_A": rail_1,
        "TargetLadderRail_B": rail_2,
        "TargetRotaryFeedthroughShaft": shaft,
        "TargetEmergencyHandwheel": handwheel,
        "TargetDriveMotorMount": motor_mount,
        "TargetDriveHardStop_A": hard_stop_a,
        "TargetDriveHardStop_B": hard_stop_b,
        "TargetDriveIndexDisk": index_disk,
        "TargetDriveIndexPin": index_pin,
    }


def _target_holder_frame(cfg: GeometryConfig, x_pos: float) -> Part.Shape:
    holder = cfg.target.holder
    if holder is None:
        raise ValueError("linear_ladder mode requires geometry.target.holder")
    outer = Part.makeBox(
        holder.frame_outer_width_mm,
        holder.frame_outer_height_mm,
        holder.frame_thickness_mm,
        App.Vector(
            x_pos - 0.5 * holder.frame_outer_width_mm,
            -0.5 * holder.frame_outer_height_mm,
            -0.5 * holder.frame_thickness_mm,
        ),
    )

    inner_w = holder.frame_outer_width_mm - 2.0 * holder.clamp_block_width_mm
    inner_h = holder.frame_outer_height_mm - 2.0 * holder.clamp_block_height_mm
    inner = Part.makeBox(
        inner_w,
        inner_h,
        holder.frame_thickness_mm + 0.4,
        App.Vector(
            x_pos - 0.5 * inner_w,
            -0.5 * inner_h,
            -0.5 * holder.frame_thickness_mm - 0.2,
        ),
    )

    frame = outer.cut(inner)

    clamp_top = Part.makeBox(
        holder.clamp_block_width_mm,
        holder.clamp_block_height_mm,
        holder.frame_thickness_mm,
        App.Vector(
            x_pos - 0.5 * holder.clamp_block_width_mm,
            0.5 * holder.frame_outer_height_mm,
            -0.5 * holder.frame_thickness_mm,
        ),
    )
    clamp_bottom = Part.makeBox(
        holder.clamp_block_width_mm,
        holder.clamp_block_height_mm,
        holder.frame_thickness_mm,
        App.Vector(
            x_pos - 0.5 * holder.clamp_block_width_mm,
            -0.5 * holder.frame_outer_height_mm - holder.clamp_block_height_mm,
            -0.5 * holder.frame_thickness_mm,
        ),
    )
    return frame.fuse(clamp_top).fuse(clamp_bottom)


def _holder_clamp_screws(cfg: GeometryConfig, x_pos: float, holder_name: str) -> dict[str, Part.Shape]:
    holder = cfg.target.holder
    if holder is None:
        raise ValueError("linear_ladder mode requires geometry.target.holder")
    shank_len = holder.frame_thickness_mm + holder.clamp_screw_head_height_mm
    z_top = 0.5 * holder.frame_thickness_mm

    out: dict[str, Part.Shape] = {}
    for label, y_pos in (
        ("Top", 0.5 * holder.frame_outer_height_mm + 0.5 * holder.clamp_block_height_mm),
        ("Bottom", -0.5 * holder.frame_outer_height_mm - 0.5 * holder.clamp_block_height_mm),
    ):
        shank = Part.makeCylinder(
            0.5 * holder.clamp_screw_diameter_mm,
            shank_len,
            App.Vector(x_pos, y_pos, z_top),
            App.Vector(0.0, 0.0, -1.0),
        )
        head = Part.makeCylinder(
            0.5 * holder.clamp_screw_head_diameter_mm,
            holder.clamp_screw_head_height_mm,
            App.Vector(x_pos, y_pos, z_top),
            App.Vector(0.0, 0.0, 1.0),
        )
        out[f"{holder_name}ClampScrew_{label}"] = shank.fuse(head)
    return out


def _build_linear_target_holders(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    slots = _target_slot_positions_x(cfg)
    holder = cfg.target.holder
    ladder = cfg.target.ladder
    if holder is None or ladder is None:
        raise ValueError("linear_ladder mode requires geometry.target.ladder and geometry.target.holder")

    empty_frame = _target_holder_frame(cfg, slots[0])
    experiment_frame = _target_holder_frame(cfg, slots[1])
    fluorescence_frame = _target_holder_frame(cfg, slots[2])

    experiment_target = Part.makeCylinder(
        0.5 * ladder.slot_window_diameter_mm,
        holder.experiment_target_thickness_mm,
        App.Vector(slots[1], 0.0, -0.5 * holder.experiment_target_thickness_mm),
        App.Vector(0.0, 0.0, 1.0),
    )
    fluorescence_target = Part.makeCylinder(
        0.5 * ladder.slot_window_diameter_mm,
        holder.fluorescence_target_thickness_mm,
        App.Vector(slots[2], 0.0, -0.5 * holder.fluorescence_target_thickness_mm),
        App.Vector(0.0, 0.0, 1.0),
    )

    out = {
        "EmptyTargetHolder": empty_frame,
        "ExperimentTargetHolder": experiment_frame,
        "FluorescenceTargetHolder": fluorescence_frame,
        "ExperimentTarget": experiment_target,
        "FluorescenceTarget": fluorescence_target,
    }
    out.update(_holder_clamp_screws(cfg, slots[0], "EmptyTargetHolder"))
    out.update(_holder_clamp_screws(cfg, slots[1], "ExperimentTargetHolder"))
    out.update(_holder_clamp_screws(cfg, slots[2], "FluorescenceTargetHolder"))
    return out


def _single_target_holder_frame(holder) -> Part.Shape:
    outer = Part.makeBox(
        holder.frame_outer_width_mm,
        holder.frame_outer_height_mm,
        holder.frame_thickness_mm,
        App.Vector(
            -0.5 * holder.frame_outer_width_mm,
            -0.5 * holder.frame_outer_height_mm,
            -0.5 * holder.frame_thickness_mm,
        ),
    )
    inner_w = holder.frame_outer_width_mm - 2.0 * holder.clamp_block_width_mm
    inner_h = holder.frame_outer_height_mm - 2.0 * holder.clamp_block_height_mm
    inner = Part.makeBox(
        inner_w,
        inner_h,
        holder.frame_thickness_mm + 0.4,
        App.Vector(
            -0.5 * inner_w,
            -0.5 * inner_h,
            -0.5 * holder.frame_thickness_mm - 0.2,
        ),
    )
    frame = outer.cut(inner)
    clamp_top = Part.makeBox(
        holder.clamp_block_width_mm,
        holder.clamp_block_height_mm,
        holder.frame_thickness_mm,
        App.Vector(
            -0.5 * holder.clamp_block_width_mm,
            0.5 * holder.frame_outer_height_mm,
            -0.5 * holder.frame_thickness_mm,
        ),
    )
    clamp_bottom = Part.makeBox(
        holder.clamp_block_width_mm,
        holder.clamp_block_height_mm,
        holder.frame_thickness_mm,
        App.Vector(
            -0.5 * holder.clamp_block_width_mm,
            -0.5 * holder.frame_outer_height_mm - holder.clamp_block_height_mm,
            -0.5 * holder.frame_thickness_mm,
        ),
    )
    return frame.fuse(clamp_top).fuse(clamp_bottom)


def _single_target_holder_screws(holder, holder_name: str) -> dict[str, Part.Shape]:
    shank_len = holder.frame_thickness_mm + holder.clamp_screw_head_height_mm
    z_top = 0.5 * holder.frame_thickness_mm
    out: dict[str, Part.Shape] = {}
    for label, y_pos in (
        ("Top", 0.5 * holder.frame_outer_height_mm + 0.5 * holder.clamp_block_height_mm),
        ("Bottom", -0.5 * holder.frame_outer_height_mm - 0.5 * holder.clamp_block_height_mm),
    ):
        shank = Part.makeCylinder(
            0.5 * holder.clamp_screw_diameter_mm,
            shank_len,
            App.Vector(0.0, y_pos, z_top),
            App.Vector(0.0, 0.0, -1.0),
        )
        head = Part.makeCylinder(
            0.5 * holder.clamp_screw_head_diameter_mm,
            holder.clamp_screw_head_height_mm,
            App.Vector(0.0, y_pos, z_top),
            App.Vector(0.0, 0.0, 1.0),
        )
        out[f"{holder_name}ClampScrew_{label}"] = shank.fuse(head)
    return out


def rotary_port_interface_geometry(cfg: GeometryConfig) -> _MountedPortInterface | None:
    rotary_port = cfg.ports.rotary_feedthrough
    if not rotary_port.enabled:
        return None
    return _build_port_interface(cfg, rotary_port)


def build_rotary_feedthrough_vendor_reference(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    rotary = cfg.target.rotary
    if rotary is None or not rotary.vendor_reference_enabled:
        return {}

    mounted_interface = rotary_port_interface_geometry(cfg)
    if mounted_interface is None or rotary.vendor_reference_model_code is None:
        return {}

    axis = mounted_interface.axis
    mount_face_center = mounted_interface.interface_face_center
    body = Part.makeCylinder(
        0.5 * rotary.vendor_reference_body_diameter_mm,
        rotary.vendor_reference_body_length_mm,
        mount_face_center,
        axis,
    )
    handwheel_origin = mount_face_center + scaled(axis, rotary.vendor_reference_body_length_mm)
    handwheel = Part.makeCylinder(
        0.5 * rotary.vendor_reference_handwheel_diameter_mm,
        rotary.vendor_reference_handwheel_thickness_mm,
        handwheel_origin,
        axis,
    )
    shaft = Part.makeCylinder(
        0.5 * rotary.feedthrough_shaft_diameter_mm,
        rotary.vendor_reference_body_length_mm + rotary.vendor_reference_handwheel_thickness_mm,
        mount_face_center,
        axis,
    )

    # [EN] The supplier reference is modeled as an external envelope aligned to the flange mating face so the chamber-side interface stack and maintenance clearance can be reviewed even when the vendor login-gated native CAD is unavailable during automated runs. / [CN] 供应商参考件按法兰配合面对齐建成外部包络，使自动化运行期间即使拿不到供应商登录受限的原生 CAD，也能审查腔体接口堆栈与维护净空。
    return {
        f"TargetRotaryVendorBody_{rotary.vendor_reference_model_code}": body,
        f"TargetRotaryVendorHandwheel_{rotary.vendor_reference_model_code}": handwheel,
        f"TargetRotaryVendorShaft_{rotary.vendor_reference_model_code}": shaft,
    }


def build_single_rotary_target_shapes(
    cfg: GeometryConfig,
    angle_deg: float,
) -> tuple[dict[str, Part.Shape], dict[str, Part.Shape]]:
    rotary = cfg.target.rotary
    holder = cfg.target.single_holder
    if rotary is None or holder is None:
        raise ValueError("single_rotary mode requires geometry.target.rotary and geometry.target.single_holder")

    pivot = _single_rotary_pivot_center(cfg)
    axis_y = App.Vector(0.0, 1.0, 0.0)
    half_y = 0.5 * cfg.chamber.core.size_y_mm
    mounted_interface = rotary_port_interface_geometry(cfg) if rotary.vendor_reference_enabled else None
    shaft_length = half_y if mounted_interface is not None else (half_y + rotary.feedthrough_length_mm)

    shaft = Part.makeCylinder(
        0.5 * rotary.feedthrough_shaft_diameter_mm,
        shaft_length,
        pivot,
        axis_y,
    )
    hub = Part.makeCylinder(
        0.5 * rotary.hub_diameter_mm,
        rotary.hub_thickness_mm,
        pivot - App.Vector(0.0, 0.5 * rotary.hub_thickness_mm, 0.0),
        axis_y,
    )
    arm = slit_prism(
        center=pivot + App.Vector(-0.5 * rotary.arm_length_mm, 0.0, 0.0),
        axis_u=App.Vector(-1.0, 0.0, 0.0),
        axis_v=axis_y,
        axis_w=App.Vector(0.0, 0.0, 1.0),
        length_mm=rotary.arm_length_mm,
        width_mm=rotary.arm_width_mm,
        height_mm=rotary.arm_thickness_mm,
    )

    holder_frame = _single_target_holder_frame(holder)
    inner_w = holder.frame_outer_width_mm - 2.0 * holder.clamp_block_width_mm
    inner_h = holder.frame_outer_height_mm - 2.0 * holder.clamp_block_height_mm
    target = Part.makeCylinder(
        0.5 * min(inner_w, inner_h),
        holder.target_thickness_mm,
        App.Vector(0.0, 0.0, -0.5 * holder.target_thickness_mm),
        App.Vector(0.0, 0.0, 1.0),
    )

    drive_shapes = {
        "TargetRotaryFeedthroughShaft": shaft,
        "TargetRotaryPivotHub": _rotated_shape(hub, pivot, axis_y, angle_deg),
        "TargetRotaryArm": _rotated_shape(arm, pivot, axis_y, angle_deg),
    }
    if mounted_interface is None:
        handwheel = Part.makeCylinder(
            0.5 * rotary.handwheel_diameter_mm,
            8.0,
            pivot + App.Vector(0.0, shaft_length, 0.0),
            axis_y,
        )
        motor_mount = Part.makeBox(
            rotary.motor_mount_width_mm,
            rotary.motor_mount_thickness_mm,
            rotary.motor_mount_height_mm,
            App.Vector(
                rotary.pivot_x_mm - 0.5 * rotary.motor_mount_width_mm,
                half_y + 0.5 * rotary.feedthrough_length_mm,
                -0.5 * rotary.motor_mount_height_mm,
            ),
        )
        stop_y = half_y + rotary.feedthrough_length_mm - rotary.hard_stop_thickness_mm
        hard_stop_a = Part.makeBox(
            26.0,
            rotary.hard_stop_thickness_mm,
            rotary.hard_stop_thickness_mm,
            App.Vector(
                rotary.pivot_x_mm - 13.0,
                stop_y,
                -0.5 * rotary.hard_stop_span_mm,
            ),
        )
        hard_stop_b = Part.makeBox(
            26.0,
            rotary.hard_stop_thickness_mm,
            rotary.hard_stop_thickness_mm,
            App.Vector(
                rotary.pivot_x_mm - 13.0,
                stop_y,
                0.5 * rotary.hard_stop_span_mm - rotary.hard_stop_thickness_mm,
            ),
        )
        index_disk = Part.makeCylinder(
            0.5 * rotary.index_disk_diameter_mm,
            rotary.index_disk_thickness_mm,
            pivot + App.Vector(0.0, shaft_length - rotary.index_disk_thickness_mm, 0.0),
            axis_y,
        )
        index_pin = Part.makeCylinder(
            0.5 * rotary.index_pin_diameter_mm,
            rotary.index_pin_length_mm,
            pivot
            + App.Vector(
                0.5 * rotary.index_disk_diameter_mm,
                shaft_length - rotary.index_disk_thickness_mm,
                0.0,
            ),
            axis_y,
        )
        drive_shapes.update(
            {
                "TargetEmergencyHandwheel": handwheel,
                "TargetDriveMotorMount": motor_mount,
                "TargetDriveHardStop_A": hard_stop_a,
                "TargetDriveHardStop_B": hard_stop_b,
                "TargetDriveIndexDisk": index_disk,
                "TargetDriveIndexPin": index_pin,
            }
        )

    holder_shapes = {
        "SingleTargetHolder": _rotated_shape(holder_frame, pivot, axis_y, angle_deg),
        "SingleTarget": _rotated_shape(target, pivot, axis_y, angle_deg),
    }
    for name, shape in _single_target_holder_screws(holder, "SingleTargetHolder").items():
        holder_shapes[name] = _rotated_shape(shape, pivot, axis_y, angle_deg)

    return drive_shapes, holder_shapes


def build_target_ladder(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    if cfg.target.mode == "single_rotary":
        drive_shapes, _ = build_single_rotary_target_shapes(cfg, cfg.target.rotary.active_angle_deg)
        return drive_shapes
    return _build_linear_target_ladder(cfg)


def build_target_holders(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    if cfg.target.mode == "single_rotary":
        _, holder_shapes = build_single_rotary_target_shapes(cfg, cfg.target.rotary.active_angle_deg)
        return holder_shapes
    return _build_linear_target_holders(cfg)


def build_stand(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    stand = cfg.stand
    core = cfg.chamber.core

    chamber_bottom_y = -0.5 * core.size_y_mm
    base_bottom_y = chamber_bottom_y - stand.chamber_support_height_mm - stand.base_thickness_mm
    foot_base_y = base_bottom_y + stand.base_thickness_mm

    feet: dict[str, Part.Shape] = {}
    for idx, center in enumerate(stand_support_centers(cfg), start=1):
        x = center.x
        z = center.z
        foot = Part.makeCylinder(
            0.5 * stand.support_foot_diameter_mm,
            stand.chamber_support_height_mm,
            App.Vector(x, foot_base_y, z),
            App.Vector(0.0, 1.0, 0.0),
        )
        screw = Part.makeCylinder(
            0.5 * stand.leveling_screw_diameter_mm,
            stand.chamber_support_height_mm + 12.0,
            App.Vector(x, foot_base_y - 12.0, z),
            App.Vector(0.0, 1.0, 0.0),
        )
        shim = Part.makeCylinder(
            0.3 * stand.support_foot_diameter_mm,
            stand.shim_thickness_mm,
            App.Vector(x, foot_base_y - stand.shim_thickness_mm, z),
            App.Vector(0.0, 1.0, 0.0),
        )

        feet[f"StandSupportFoot_{idx}"] = foot
        feet[f"StandLevelingScrew_{idx}"] = screw
        feet[f"StandShim_{idx}"] = shim

    out: dict[str, Part.Shape] = {}
    if stand.with_base_plate:
        base = Part.makeBox(
            stand.base_length_mm,
            stand.base_thickness_mm,
            stand.base_width_mm,
            App.Vector(-0.5 * stand.base_length_mm, base_bottom_y, -0.5 * stand.base_width_mm),
        )

        for center in stand_support_centers(cfg):
            slot_cut = slit_prism(
                center=App.Vector(
                    center.x,
                    base_bottom_y + 0.5 * stand.base_thickness_mm,
                    center.z,
                ),
                axis_u=App.Vector(0.0, 1.0, 0.0),
                axis_v=App.Vector(1.0, 0.0, 0.0),
                axis_w=App.Vector(0.0, 0.0, 1.0),
                length_mm=stand.base_thickness_mm + 2.0,
                width_mm=stand.anchor_slot_length_mm,
                height_mm=stand.anchor_slot_width_mm,
            )
            base = base.cut(slot_cut)

        out["StandBasePlate"] = base
    out.update(feet)
    return out
