from __future__ import annotations

import math
from dataclasses import dataclass

import FreeCAD as App
import Part

from .config import GeometryConfig, PlateConfig, PortConfig
from .layout import (
    DetectorPlacement,
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


def _chamber_halves(cfg: GeometryConfig) -> tuple[float, float, float]:
    core = cfg.chamber.core
    return (0.5 * core.size_x_mm, 0.5 * core.size_y_mm, 0.5 * core.size_z_mm)


def _port_pose(cfg: GeometryConfig, port: PortConfig) -> tuple[App.Vector, App.Vector]:
    half_x, half_y, _ = _chamber_halves(cfg)

    if port.side == "right":
        return App.Vector(half_x, 0.0, port.center_z_mm), App.Vector(1.0, 0.0, 0.0)
    if port.side == "left":
        return App.Vector(-half_x, 0.0, port.center_z_mm), App.Vector(-1.0, 0.0, 0.0)
    if port.side == "top":
        return App.Vector(0.0, half_y, port.center_z_mm), App.Vector(0.0, 1.0, 0.0)
    if port.side == "bottom":
        return App.Vector(0.0, -half_y, port.center_z_mm), App.Vector(0.0, -1.0, 0.0)
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

    cuts: list[Part.Shape] = []
    start = App.Vector(0.0, 0.0, los_cfg.channel_start_z_mm)
    for placement in placements:
        cuts.append(
            Part.makeCylinder(
                0.5 * los_cfg.channel_diameter_mm,
                los_cfg.channel_length_mm,
                start,
                placement.direction,
            )
        )
    return cuts


def build_chamber(cfg: GeometryConfig, placements: list[DetectorPlacement] | None = None) -> Part.Shape:
    core = cfg.chamber.core
    half_x, half_y, half_z = _chamber_halves(cfg)

    outer = Part.makeBox(
        core.size_x_mm,
        core.size_y_mm,
        core.size_z_mm,
        App.Vector(-half_x, -half_y, -half_z),
    )
    inner = Part.makeBox(
        core.size_x_mm - 2.0 * core.wall_thickness_mm,
        core.size_y_mm - 2.0 * core.wall_thickness_mm,
        core.size_z_mm - 2.0 * core.wall_thickness_mm,
        App.Vector(
            -half_x + core.wall_thickness_mm,
            -half_y + core.wall_thickness_mm,
            -half_z + core.wall_thickness_mm,
        ),
    )
    chamber = outer.cut(inner)

    beam_cut = Part.makeCylinder(
        0.5 * cfg.beamline.inlet_diameter_mm,
        core.size_z_mm + 4.0,
        App.Vector(0.0, 0.0, -half_z - 2.0),
        App.Vector(0.0, 0.0, 1.0),
    )
    chamber = chamber.cut(beam_cut)

    for port in (
        cfg.ports.main_pump,
        cfg.ports.gauge_safety,
        cfg.ports.rotary_feedthrough,
        cfg.ports.spare,
    ):
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


def _build_end_module(
    cfg: GeometryConfig,
    side: str,
    placements: list[DetectorPlacement] | None = None,
) -> Part.Shape:
    half_z = 0.5 * cfg.chamber.core.size_z_mm
    module = cfg.chamber.end_modules
    axis = App.Vector(0.0, 0.0, 1.0)

    if side == "front":
        origin = App.Vector(0.0, 0.0, -half_z - module.module_thickness_mm)
        chamber_face_z = -half_z
        groove_origin = App.Vector(0.0, 0.0, chamber_face_z - module.oring_groove_depth_mm)
        seal_origin = App.Vector(0.0, 0.0, chamber_face_z - module.seal_face_width_mm)
    elif side == "rear":
        origin = App.Vector(0.0, 0.0, half_z)
        chamber_face_z = half_z
        groove_origin = App.Vector(0.0, 0.0, chamber_face_z)
        seal_origin = App.Vector(0.0, 0.0, chamber_face_z)
    else:
        raise ValueError(f"unsupported side {side!r}")

    flange = tube_shape(
        outer_diameter_mm=module.module_outer_diameter_mm,
        inner_diameter_mm=module.module_inner_diameter_mm,
        length_mm=module.module_thickness_mm,
        origin=origin,
        axis=axis,
    )

    seal_outer = min(
        module.module_outer_diameter_mm - 2.0,
        module.module_inner_diameter_mm + (2.0 * module.seal_face_width_mm) + (2.0 * module.oring_groove_width_mm),
    )
    seal_ring = tube_shape(
        outer_diameter_mm=seal_outer,
        inner_diameter_mm=module.module_inner_diameter_mm,
        length_mm=module.seal_face_width_mm,
        origin=seal_origin,
        axis=axis,
    )
    flange = flange.fuse(seal_ring)

    bolt_hole_diameter = min(
        0.6 * module.seal_face_width_mm,
        0.2 * (module.module_outer_diameter_mm - module.module_inner_diameter_mm),
    )
    bolt_radius = 0.5 * module.bolt_circle_diameter_mm
    for idx in range(module.bolt_count):
        angle = (2.0 * math.pi * float(idx)) / float(module.bolt_count)
        x = bolt_radius * math.cos(angle)
        y = bolt_radius * math.sin(angle)
        hole = Part.makeCylinder(
            0.5 * bolt_hole_diameter,
            module.module_thickness_mm + 2.0,
            App.Vector(x, y, origin.z - 1.0),
            axis,
        )
        flange = flange.cut(hole)

    groove_inner = module.module_inner_diameter_mm + module.oring_groove_width_mm
    groove_outer = groove_inner + (2.0 * module.oring_groove_width_mm)
    groove_cut = tube_shape(
        outer_diameter_mm=groove_outer,
        inner_diameter_mm=groove_inner,
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
    half_z = 0.5 * cfg.chamber.core.size_z_mm
    module = cfg.chamber.end_modules
    bolt_radius = 0.5 * module.bolt_circle_diameter_mm
    bolt_clearance_d = module.interface_bolt_diameter_mm + 0.8

    if side == "front":
        face_origin = App.Vector(0.0, 0.0, -half_z)
        axis = App.Vector(0.0, 0.0, -1.0)
        prefix = "FrontInterface"
    elif side == "rear":
        face_origin = App.Vector(0.0, 0.0, half_z)
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


def build_ports(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    out: dict[str, Part.Shape] = {}
    for name, port in (
        ("MainPumpPort", cfg.ports.main_pump),
        ("GaugeSafetyPort", cfg.ports.gauge_safety),
        ("RotaryFeedthroughPort", cfg.ports.rotary_feedthrough),
        ("SparePort", cfg.ports.spare),
    ):
        wall_point, axis = _port_pose(cfg, port)
        out[name] = tube_shape(
            outer_diameter_mm=port.outer_diameter_mm,
            inner_diameter_mm=port.inner_diameter_mm,
            length_mm=port.length_mm,
            origin=wall_point,
            axis=axis,
        )
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


def _build_plate_lugs_with_bolt_holes(plate: PlateConfig) -> Part.Shape:
    center, axis_t, axis_v, axis_w = _plate_axes(plate)

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


def build_load_bearing_plate(plate: PlateConfig) -> Part.Shape:
    # [EN] Fused base+lugs+stiffeners encode a deterministic structural load path for validation and assembly mapping. / [CN] 融合主板+连接耳+加劲肋，形成可验证且可装配映射的确定性承载路径。
    base = _build_plate_base_with_openings(plate)
    lugs = _build_plate_lugs_with_bolt_holes(plate)
    stiffeners = _build_plate_stiffeners(plate)
    return base.fuse(lugs).fuse(stiffeners)


def _chamber_plate_cutout(cfg: GeometryConfig) -> Part.Shape:
    core = cfg.chamber.core
    margin = cfg.clearance.plate_chamber_cutout_margin_mm
    return Part.makeBox(
        core.size_x_mm + 2.0 * margin,
        core.size_y_mm + 2.0 * margin,
        core.size_z_mm + 2.0 * margin,
        App.Vector(
            -0.5 * core.size_x_mm - margin,
            -0.5 * core.size_y_mm - margin,
            -0.5 * core.size_z_mm - margin,
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
        for center in layout.plate_hole_centers:
            hole = Part.makeCylinder(
                0.5 * clamp_cfg.mount_bolt_hole_diameter_mm,
                plate.thickness_mm + 2.0,
                center - scaled(layout.plate_normal, 0.5 * plate.thickness_mm + 1.0),
                layout.plate_normal,
            )
            holes[plate_key_for_sector(placement.sector_name)].append(hole)
    return holes


def build_all_plates(
    cfg: GeometryConfig,
    placements: list[DetectorPlacement] | None = None,
) -> dict[str, Part.Shape]:
    plates = {
        "HPlate": build_load_bearing_plate(cfg.plate.h),
        "VPlate1": build_load_bearing_plate(cfg.plate.v1),
        "VPlate2": build_load_bearing_plate(cfg.plate.v2),
    }

    if cfg.clearance.disable_plate_cuts:
        # [EN] Preview mode keeps load-bearing plates as full solids to compare legacy panel placement/size before opening strategy is finalized. / [CN] 预览模式保留完整承重板实体，用于在确定开孔策略前先对齐旧版板位与尺寸。
        return plates

    cutout = _chamber_plate_cutout(cfg)
    for name, plate in list(plates.items()):
        # [EN] Remove chamber overlap from full load-bearing solids (base+lugs+stiffeners), preserving strict no-overlap assembly gate. / [CN] 对完整承重实体（主板+连接耳+加劲肋）执行去腔体干涉挖孔，满足严格零重叠装配门。
        plates[name] = plate.cut(cutout)

    if placements:
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
    pitch = cfg.target.ladder.slot_pitch_mm
    return (-pitch, 0.0, pitch)


def build_target_ladder(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    ladder = cfg.target.ladder
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


def build_target_holders(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    slots = _target_slot_positions_x(cfg)
    holder = cfg.target.holder

    empty_frame = _target_holder_frame(cfg, slots[0])
    experiment_frame = _target_holder_frame(cfg, slots[1])
    fluorescence_frame = _target_holder_frame(cfg, slots[2])

    experiment_target = Part.makeCylinder(
        0.5 * cfg.target.ladder.slot_window_diameter_mm,
        holder.experiment_target_thickness_mm,
        App.Vector(slots[1], 0.0, -0.5 * holder.experiment_target_thickness_mm),
        App.Vector(0.0, 0.0, 1.0),
    )
    fluorescence_target = Part.makeCylinder(
        0.5 * cfg.target.ladder.slot_window_diameter_mm,
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


def build_stand(cfg: GeometryConfig) -> dict[str, Part.Shape]:
    stand = cfg.stand
    core = cfg.chamber.core

    chamber_bottom_y = -0.5 * core.size_y_mm
    base_bottom_y = chamber_bottom_y - stand.chamber_support_height_mm - stand.base_thickness_mm

    base = Part.makeBox(
        stand.base_length_mm,
        stand.base_thickness_mm,
        stand.base_width_mm,
        App.Vector(-0.5 * stand.base_length_mm, base_bottom_y, -0.5 * stand.base_width_mm),
    )

    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            slot_cut = slit_prism(
                center=App.Vector(
                    sx * 0.35 * stand.base_length_mm,
                    base_bottom_y + 0.5 * stand.base_thickness_mm,
                    sz * 0.35 * stand.base_width_mm,
                ),
                axis_u=App.Vector(0.0, 1.0, 0.0),
                axis_v=App.Vector(1.0, 0.0, 0.0),
                axis_w=App.Vector(0.0, 0.0, 1.0),
                length_mm=stand.base_thickness_mm + 2.0,
                width_mm=stand.anchor_slot_length_mm,
                height_mm=stand.anchor_slot_width_mm,
            )
            base = base.cut(slot_cut)

    foot_x = 0.5 * core.size_x_mm - 50.0
    foot_z = 0.5 * core.size_z_mm - 50.0
    foot_base_y = base_bottom_y + stand.base_thickness_mm

    feet: dict[str, Part.Shape] = {}
    for idx, (sx, sz) in enumerate(((-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0), (1.0, 1.0)), start=1):
        x = sx * foot_x
        z = sz * foot_z
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

    out: dict[str, Part.Shape] = {
        "StandBasePlate": base,
    }
    out.update(feet)
    return out
