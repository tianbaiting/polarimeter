from __future__ import annotations

import math
from dataclasses import dataclass

import FreeCAD as App
import Part

from .config import CIVConfig, EndModuleSideConfig, end_module_has_groove
from .layout import DetectorPlacement, dot, front_face_center, normalize, scaled


def _cylinder(radius_mm: float, length_mm: float, origin: App.Vector, axis: App.Vector | None = None) -> Part.Shape:
    if axis is None:
        axis = App.Vector(0.0, 0.0, 1.0)
    return Part.makeCylinder(radius_mm, length_mm, origin, axis)


def _tube_shape(
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    length_mm: float,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    outer = _cylinder(0.5 * outer_diameter_mm, length_mm, origin, axis)
    # [EN] The bore is extended slightly beyond the outer solid so boolean cuts do not leave coincident faces, which is the main source of unstable vacuum-boundary solids in FreeCAD/OCC. / [CN] 内孔比外实体略微加长，避免布尔切割留下共面面片；这正是 FreeCAD/OCC 中真空边界实体不稳定的主要来源。
    inner = _cylinder(
        0.5 * inner_diameter_mm,
        length_mm + 0.4,
        origin - scaled(axis, 0.2),
        axis,
    )
    return outer.cut(inner)


def _ring_shape(
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    thickness_mm: float,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    return _tube_shape(
        outer_diameter_mm=outer_diameter_mm,
        inner_diameter_mm=inner_diameter_mm,
        length_mm=thickness_mm,
        origin=origin,
        axis=axis,
    )


def vessel_z_bounds(cfg: CIVConfig) -> tuple[float, float]:
    z_min = cfg.vessel.center_z_mm - 0.5 * cfg.vessel.length_mm
    z_max = cfg.vessel.center_z_mm + 0.5 * cfg.vessel.length_mm
    return z_min, z_max


def _rectangular_shell(cfg: CIVConfig) -> Part.Shape:
    wall = cfg.vessel.wall_thickness_mm
    z_min, _ = vessel_z_bounds(cfg)
    outer_size_x_mm = cfg.vessel.inner_size_x_mm + (2.0 * wall)
    outer_size_y_mm = cfg.vessel.inner_size_y_mm + (2.0 * wall)
    outer = Part.makeBox(
        outer_size_x_mm,
        outer_size_y_mm,
        cfg.vessel.length_mm,
        App.Vector(-0.5 * outer_size_x_mm, -0.5 * outer_size_y_mm, z_min),
    )
    cavity_length_mm = cfg.vessel.length_mm - (2.0 * wall)
    if cavity_length_mm <= 0.0:
        raise ValueError("vessel.length_mm must exceed twice vessel.wall_thickness_mm")
    cavity = Part.makeBox(
        cfg.vessel.inner_size_x_mm,
        cfg.vessel.inner_size_y_mm,
        cavity_length_mm,
        App.Vector(-0.5 * cfg.vessel.inner_size_x_mm, -0.5 * cfg.vessel.inner_size_y_mm, z_min + wall),
    )
    return outer.cut(cavity)


def _cylindrical_shell(cfg: CIVConfig) -> Part.Shape:
    wall = cfg.vessel.wall_thickness_mm
    z_min, _ = vessel_z_bounds(cfg)
    inner_radius_mm = 0.5 * cfg.vessel.inner_size_x_mm
    outer_radius_mm = inner_radius_mm + wall
    outer = _cylinder(outer_radius_mm, cfg.vessel.length_mm, App.Vector(0.0, 0.0, z_min))
    cavity_length_mm = cfg.vessel.length_mm - (2.0 * wall)
    if cavity_length_mm <= 0.0:
        raise ValueError("vessel.length_mm must exceed twice vessel.wall_thickness_mm")
    cavity = _cylinder(inner_radius_mm, cavity_length_mm, App.Vector(0.0, 0.0, z_min + wall))
    return outer.cut(cavity)


def build_vessel_body(cfg: CIVConfig) -> Part.Shape:
    if cfg.vessel.cross_section == "square":
        shell = _rectangular_shell(cfg)
    elif cfg.vessel.cross_section == "cylindrical":
        shell = _cylindrical_shell(cfg)
    else:
        raise ValueError(f"unsupported vessel.cross_section {cfg.vessel.cross_section!r}")

    wall = cfg.vessel.wall_thickness_mm
    z_min, z_max = vessel_z_bounds(cfg)
    beam_bore_radius_mm = 0.5 * cfg.vessel.beam_bore_diameter_mm
    overlap_mm = 0.01
    upstream_bore = _cylinder(
        beam_bore_radius_mm,
        wall + (2.0 * overlap_mm),
        App.Vector(0.0, 0.0, z_min - overlap_mm),
    )
    downstream_bore = _cylinder(
        beam_bore_radius_mm,
        wall + (2.0 * overlap_mm),
        App.Vector(0.0, 0.0, z_max - wall - overlap_mm),
    )
    return shell.cut(upstream_bore).cut(downstream_bore)


@dataclass(frozen=True)
class _EndModuleAxialLayout:
    chamber_face_z: float
    flange_origin_z: float
    interface_face_z: float
    pipe_origin_z: float | None
    pipe_shape_length_mm: float


def _end_module_axial_layout(cfg: CIVConfig, side: str) -> _EndModuleAxialLayout:
    z_min, z_max = vessel_z_bounds(cfg)
    module = cfg.vessel.end_modules.front if side == "front" else cfg.vessel.end_modules.rear
    pipe_seat_mm = min(2.0, 0.5 * module.module_thickness_mm) if module.pipe_length_mm > 0.0 else 0.0

    if side == "front":
        chamber_face_z = z_min
        flange_origin_z = chamber_face_z - module.pipe_length_mm - module.module_thickness_mm
        interface_face_z = flange_origin_z
        pipe_origin_z = chamber_face_z - module.pipe_length_mm - pipe_seat_mm if module.pipe_length_mm > 0.0 else None
    elif side == "rear":
        chamber_face_z = z_max
        flange_origin_z = chamber_face_z + module.pipe_length_mm
        interface_face_z = flange_origin_z + module.module_thickness_mm
        pipe_origin_z = chamber_face_z - pipe_seat_mm if module.pipe_length_mm > 0.0 else None
    else:
        raise ValueError(f"unsupported side {side!r}")

    return _EndModuleAxialLayout(
        chamber_face_z=chamber_face_z,
        flange_origin_z=flange_origin_z,
        interface_face_z=interface_face_z,
        pipe_origin_z=pipe_origin_z,
        pipe_shape_length_mm=(module.pipe_length_mm + (2.0 * pipe_seat_mm)) if module.pipe_length_mm > 0.0 else 0.0,
    )


def _legacy_ring_shape(module: EndModuleSideConfig, side: str, axial: _EndModuleAxialLayout) -> Part.Shape:
    origin_z = axial.flange_origin_z if side == "front" else axial.chamber_face_z
    return _ring_shape(
        outer_diameter_mm=module.module_outer_diameter_mm,
        inner_diameter_mm=module.module_inner_diameter_mm,
        thickness_mm=module.module_thickness_mm,
        origin=App.Vector(0.0, 0.0, origin_z),
        axis=App.Vector(0.0, 0.0, 1.0),
    )


def build_end_module(cfg: CIVConfig, side: str) -> Part.Shape:
    module = cfg.vessel.end_modules.front if side == "front" else cfg.vessel.end_modules.rear
    axial = _end_module_axial_layout(cfg, side)
    axis = App.Vector(0.0, 0.0, 1.0)

    if module.standard.upper() == "LEGACY_RING":
        return _legacy_ring_shape(module, side, axial)

    flange_origin = App.Vector(0.0, 0.0, axial.flange_origin_z)
    flange = _tube_shape(
        outer_diameter_mm=module.module_outer_diameter_mm,
        inner_diameter_mm=module.module_inner_diameter_mm,
        length_mm=module.module_thickness_mm,
        origin=flange_origin,
        axis=axis,
    )

    if module.pipe_length_mm > 0.0 and axial.pipe_origin_z is not None:
        pipe = _tube_shape(
            outer_diameter_mm=module.pipe_outer_diameter_mm,
            inner_diameter_mm=module.pipe_inner_diameter_mm,
            length_mm=axial.pipe_shape_length_mm,
            origin=App.Vector(0.0, 0.0, axial.pipe_origin_z),
            axis=axis,
        )
        flange = flange.fuse(pipe)

    seal_outer_diameter_mm = min(
        module.module_outer_diameter_mm - 2.0,
        module.module_inner_diameter_mm
        + (2.0 * module.seal_face_width_mm)
        + max(0.0, module.oring_groove_outer_diameter_mm - module.oring_groove_inner_diameter_mm),
    )
    if side == "front":
        seal_origin = App.Vector(0.0, 0.0, axial.interface_face_z)
        groove_origin = App.Vector(0.0, 0.0, axial.interface_face_z)
    else:
        seal_origin = App.Vector(0.0, 0.0, axial.interface_face_z - module.seal_face_width_mm)
        groove_origin = App.Vector(0.0, 0.0, axial.interface_face_z - module.oring_groove_depth_mm)

    flange = flange.fuse(
        _tube_shape(
            outer_diameter_mm=seal_outer_diameter_mm,
            inner_diameter_mm=module.module_inner_diameter_mm,
            length_mm=module.seal_face_width_mm,
            origin=seal_origin,
            axis=axis,
        )
    )

    bolt_radius_mm = 0.5 * module.bolt_circle_diameter_mm
    for idx in range(module.bolt_count):
        angle_rad = (2.0 * math.pi * float(idx)) / float(module.bolt_count)
        x_mm = bolt_radius_mm * math.cos(angle_rad)
        y_mm = bolt_radius_mm * math.sin(angle_rad)
        hole = _cylinder(
            0.5 * module.flange_bolt_hole_diameter_mm,
            module.module_thickness_mm + 2.0,
            App.Vector(x_mm, y_mm, axial.flange_origin_z - 1.0),
        )
        flange = flange.cut(hole)

    if end_module_has_groove(module.standard) and module.oring_groove_depth_mm > 0.0:
        groove = _tube_shape(
            outer_diameter_mm=module.oring_groove_outer_diameter_mm,
            inner_diameter_mm=module.oring_groove_inner_diameter_mm,
            length_mm=module.oring_groove_depth_mm,
            origin=groove_origin,
            axis=axis,
        )
        flange = flange.cut(groove)

    return flange


def build_end_modules(cfg: CIVConfig) -> tuple[Part.Shape, Part.Shape]:
    return build_end_module(cfg, "front"), build_end_module(cfg, "rear")


def make_placement_from_direction(origin: App.Vector, direction: App.Vector) -> App.Placement:
    axis_z = App.Vector(0.0, 0.0, 1.0)
    unit_direction = normalize(direction)
    cos_angle = max(-1.0, min(1.0, dot(axis_z, unit_direction)))
    rotation_axis = axis_z.cross(unit_direction)

    if rotation_axis.Length <= 1e-12:
        if cos_angle >= 0.0:
            rotation = App.Rotation()
        else:
            rotation = App.Rotation(App.Vector(1.0, 0.0, 0.0), 180.0)
    else:
        rotation = App.Rotation(rotation_axis, math.degrees(math.acos(cos_angle)))
    return App.Placement(origin, rotation)


def build_inner_frame(cfg: CIVConfig, placements: list[DetectorPlacement]) -> Part.Shape:
    spine_radius_mm = 0.5 * cfg.inner_frame.spine_diameter_mm
    z_min, _ = vessel_z_bounds(cfg)
    spine = _cylinder(spine_radius_mm, cfg.vessel.length_mm, App.Vector(0.0, 0.0, z_min))

    arms: list[Part.Shape] = [spine]
    for placement in placements:
        arm_length_mm = placement.radius_mm - (0.5 * cfg.detector.length_mm) - spine_radius_mm
        arm_length_mm = max(arm_length_mm, 1.0)
        arm = Part.makeBox(
            cfg.inner_frame.arm_cross_width_mm,
            cfg.inner_frame.arm_cross_thickness_mm,
            arm_length_mm,
            App.Vector(
                -0.5 * cfg.inner_frame.arm_cross_width_mm,
                -0.5 * cfg.inner_frame.arm_cross_thickness_mm,
                0.0,
            ),
        )
        arm.Placement = make_placement_from_direction(scaled(placement.direction, spine_radius_mm), placement.direction)
        arms.append(arm)

    return Part.makeCompound(arms)


def build_compact_detector(cfg: CIVConfig, placement: DetectorPlacement) -> Part.Shape:
    detector_radius_mm = 0.5 * cfg.detector.diameter_mm
    detector_length_mm = cfg.detector.length_mm
    clamp_outer_radius_mm = 0.5 * cfg.detector.clamp_outer_diameter_mm
    clamp_width_mm = cfg.detector.clamp_width_mm

    detector = _cylinder(
        detector_radius_mm,
        detector_length_mm,
        App.Vector(0.0, 0.0, -0.5 * detector_length_mm),
    )

    clamp_outer = _cylinder(
        clamp_outer_radius_mm,
        clamp_width_mm,
        App.Vector(0.0, 0.0, -0.5 * detector_length_mm),
    )
    clamp_inner = _cylinder(
        detector_radius_mm,
        clamp_width_mm,
        App.Vector(0.0, 0.0, -0.5 * detector_length_mm),
    )
    clamp = clamp_outer.cut(clamp_inner)

    origin = front_face_center(placement) - scaled(placement.direction, 0.5 * detector_length_mm)
    placement_transform = make_placement_from_direction(origin, placement.direction)
    detector.Placement = placement_transform
    clamp.Placement = placement_transform

    return Part.makeCompound([detector, clamp])
