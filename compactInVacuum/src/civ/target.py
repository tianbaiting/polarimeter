from __future__ import annotations

from dataclasses import dataclass
import math

import FreeCAD as App
import Part

from .config import CIVConfig
from .layout import normalize, scaled


@dataclass(frozen=True)
class TargetPoseGeometry:
    angle_deg: float
    target_center: App.Vector
    physical: dict[str, Part.Shape]


@dataclass(frozen=True)
class TargetSystemGeometry:
    work: TargetPoseGeometry
    park: TargetPoseGeometry
    motion_samples: tuple[TargetPoseGeometry, ...]
    stationary: dict[str, Part.Shape]
    interfaces: dict[str, Part.Shape]
    keepouts: dict[str, Part.Shape]
    datums: dict[str, Part.Shape]
    materials: dict[str, str]


def _rotate(
    shape: Part.Shape,
    pivot: App.Vector,
    axis: App.Vector,
    angle_deg: float,
) -> Part.Shape:
    if abs(angle_deg) <= 1.0e-12:
        return shape
    rotated = shape.copy()
    rotated.rotate(pivot, axis, angle_deg)
    return rotated


def _ray_to_chamber_wall_mm(
    cfg: CIVConfig,
    origin: App.Vector,
    direction: App.Vector,
) -> float:
    unit = normalize(direction)
    candidates: list[float] = []
    half_x_mm = 0.5 * cfg.vessel.inner_size_x_mm
    half_y_mm = 0.5 * cfg.vessel.inner_size_y_mm
    half_z_mm = 0.5 * cfg.vessel.length_mm
    center_z_mm = cfg.vessel.center_z_mm

    if cfg.vessel.cross_section == "cylindrical":
        a = (
            (unit.x / half_x_mm) ** 2
            + (unit.y / half_y_mm) ** 2
        )
        b = 2.0 * (
            origin.x * unit.x / (half_x_mm * half_x_mm)
            + origin.y * unit.y / (half_y_mm * half_y_mm)
        )
        c = (
            (origin.x / half_x_mm) ** 2
            + (origin.y / half_y_mm) ** 2
            - 1.0
        )
        if a > 1.0e-15:
            discriminant = b * b - 4.0 * a * c
            if discriminant >= 0.0:
                for value in (
                    (-b - math.sqrt(discriminant)) / (2.0 * a),
                    (-b + math.sqrt(discriminant)) / (2.0 * a),
                ):
                    if value > 1.0e-9:
                        candidates.append(value)
    else:
        for coordinate, component, half_size in (
            (origin.x, unit.x, half_x_mm),
            (origin.y, unit.y, half_y_mm),
        ):
            if component > 1.0e-15:
                candidates.append((half_size - coordinate) / component)
            elif component < -1.0e-15:
                candidates.append((-half_size - coordinate) / component)

    if unit.z > 1.0e-15:
        candidates.append((center_z_mm + half_z_mm - origin.z) / unit.z)
    elif unit.z < -1.0e-15:
        candidates.append((center_z_mm - half_z_mm - origin.z) / unit.z)
    positive = tuple(value for value in candidates if value > 1.0e-9)
    if not positive:
        raise ValueError("target shaft axis does not intersect the chamber wall")
    return min(positive)


def target_center_at_angle(cfg: CIVConfig, angle_deg: float) -> App.Vector:
    if cfg.compact_one is None:
        raise ValueError("target kinematics require a CompactOne schema-v2 configuration")
    rotary = cfg.compact_one.target.rotary
    pivot = App.Vector(*rotary.pivot_mm)
    initial = pivot + App.Vector(-rotary.arm_length_mm, 0.0, 0.0)
    point = Part.Vertex(initial)
    point.rotate(pivot, App.Vector(*rotary.axis), angle_deg)
    return point.Point


def _holder_and_foil(cfg: CIVConfig) -> tuple[Part.Shape, Part.Shape]:
    target = cfg.compact_one.target
    holder = target.holder
    foil = target.foil
    target_center = target_center_at_angle(cfg, 0.0)
    opening_width_mm = holder.outer_width_mm - 2.0 * holder.frame_width_mm
    opening_height_mm = holder.outer_height_mm - 2.0 * holder.frame_width_mm
    if min(opening_width_mm, opening_height_mm) <= foil.diameter_mm:
        raise ValueError("target holder opening must be larger than the active foil")
    frame_origin_z_mm = target_center.z - 0.5 * holder.thickness_mm
    if holder.architecture == "open_c_frame":
        right = Part.makeBox(
            holder.frame_width_mm,
            holder.outer_height_mm,
            holder.thickness_mm,
            App.Vector(
                target_center.x + 0.5 * opening_width_mm,
                target_center.y - 0.5 * holder.outer_height_mm,
                frame_origin_z_mm,
            ),
        )
        top = Part.makeBox(
            holder.outer_width_mm - holder.frame_width_mm,
            holder.frame_width_mm,
            holder.thickness_mm,
            App.Vector(
                target_center.x - 0.5 * holder.outer_width_mm,
                target_center.y + 0.5 * opening_height_mm,
                frame_origin_z_mm,
            ),
        )
        bottom = Part.makeBox(
            holder.outer_width_mm - holder.frame_width_mm,
            holder.frame_width_mm,
            holder.thickness_mm,
            App.Vector(
                target_center.x - 0.5 * holder.outer_width_mm,
                target_center.y - 0.5 * holder.outer_height_mm,
                frame_origin_z_mm,
            ),
        )
        frame = right.fuse(top).fuse(bottom)
    elif holder.architecture == "closed_frame":
        holder_outer = Part.makeBox(
            holder.outer_width_mm,
            holder.outer_height_mm,
            holder.thickness_mm,
            App.Vector(
                target_center.x - 0.5 * holder.outer_width_mm,
                target_center.y - 0.5 * holder.outer_height_mm,
                frame_origin_z_mm,
            ),
        )
        holder_opening = Part.makeBox(
            opening_width_mm,
            opening_height_mm,
            holder.thickness_mm + 0.4,
            App.Vector(
                target_center.x - 0.5 * opening_width_mm,
                target_center.y - 0.5 * opening_height_mm,
                frame_origin_z_mm - 0.2,
            ),
        )
        frame = holder_outer.cut(holder_opening)
    else:
        raise ValueError(f"unsupported target holder architecture: {holder.architecture}")
    foil_shape = Part.makeCylinder(
        0.5 * foil.diameter_mm,
        foil.thickness_mm,
        target_center - App.Vector(0.0, 0.0, 0.5 * foil.thickness_mm),
    )
    return frame, foil_shape


def build_target_pose(cfg: CIVConfig, angle_deg: float) -> TargetPoseGeometry:
    if cfg.compact_one is None:
        raise ValueError("target pose requires a CompactOne schema-v2 configuration")
    target = cfg.compact_one.target
    rotary = target.rotary
    holder = target.holder
    pivot = App.Vector(*rotary.pivot_mm)
    axis = normalize(App.Vector(*rotary.axis))
    initial_target_center = target_center_at_angle(cfg, 0.0)
    frame, foil = _holder_and_foil(cfg)

    arm_axis_offset_mm = (
        0.5 * holder.outer_height_mm
        + 0.5 * rotary.arm_width_mm
        - 2.0
    )
    arm = Part.makeBox(
        rotary.arm_length_mm,
        rotary.arm_width_mm,
        rotary.arm_thickness_mm,
        App.Vector(
            initial_target_center.x,
            initial_target_center.y + arm_axis_offset_mm - 0.5 * rotary.arm_width_mm,
            initial_target_center.z - 0.5 * rotary.arm_thickness_mm,
        ),
    )
    hub = Part.makeCylinder(
        0.5 * rotary.hub_diameter_mm,
        rotary.hub_thickness_mm,
        pivot + scaled(axis, arm_axis_offset_mm - 0.5 * rotary.hub_thickness_mm),
        axis,
    )
    return TargetPoseGeometry(
        angle_deg=angle_deg,
        target_center=target_center_at_angle(cfg, angle_deg),
        physical={
            "TargetPivotHub": _rotate(hub, pivot, axis, angle_deg),
            "TargetRotaryArm": _rotate(arm, pivot, axis, angle_deg),
            "TargetHolderFrame": _rotate(frame, pivot, axis, angle_deg),
            "TargetFoil": _rotate(foil, pivot, axis, angle_deg),
        },
    )


def _motion_angles(start_deg: float, end_deg: float, step_deg: float) -> tuple[float, ...]:
    direction = 1.0 if end_deg >= start_deg else -1.0
    step = direction * step_deg
    values: list[float] = [start_deg]
    current = start_deg
    while (end_deg - current) * direction > step_deg:
        current += step
        values.append(current)
    if abs(values[-1] - end_deg) > 1.0e-9:
        values.append(end_deg)
    return tuple(values)


def build_target_system(cfg: CIVConfig) -> TargetSystemGeometry:
    if cfg.compact_one is None:
        raise ValueError("target system requires a CompactOne schema-v2 configuration")
    target = cfg.compact_one.target
    rotary = target.rotary
    pivot = App.Vector(*rotary.pivot_mm)
    axis = normalize(App.Vector(*rotary.axis))
    shaft_length_mm = _ray_to_chamber_wall_mm(cfg, pivot, axis)
    shaft = Part.makeCylinder(
        0.5 * rotary.shaft_diameter_mm,
        shaft_length_mm,
        pivot,
        axis,
    )
    angles = _motion_angles(
        rotary.work_angle_deg,
        rotary.park_angle_deg,
        rotary.motion_sample_step_deg,
    )
    samples = tuple(build_target_pose(cfg, angle_deg) for angle_deg in angles)
    work = samples[0]
    park = samples[-1]
    moving_names = (
        "TargetPivotHub",
        "TargetRotaryArm",
        "TargetHolderFrame",
        "TargetFoil",
    )
    sweep = Part.makeCompound(
        [
            pose.physical[name]
            for pose in samples
            for name in moving_names
        ]
    )
    stop_radius_mm = 0.5 * rotary.hub_diameter_mm + 4.0
    interfaces: dict[str, Part.Shape] = {}
    for name, angle_deg in zip(
        ("WorkHardStopInterface", "ParkHardStopInterface"),
        rotary.hard_stop_angles_deg,
    ):
        angle_rad = math.radians(angle_deg)
        point = pivot + App.Vector(
            -stop_radius_mm * math.cos(angle_rad),
            -0.5 * rotary.hub_thickness_mm,
            stop_radius_mm * math.sin(angle_rad),
        )
        interfaces[name] = Part.makeSphere(2.0, point)
    datums = {
        "TargetPivotDatum": Part.makeSphere(0.75, pivot),
        "TargetCenterWorkDatum": Part.makeSphere(0.75, work.target_center),
        "TargetCenterParkDatum": Part.makeSphere(0.75, park.target_center),
        "RotaryAxisDatum": Part.makeCylinder(0.25, shaft_length_mm, pivot, axis),
    }
    materials = {
        "TargetRotaryShaft": "stainless_304L",
        "TargetPivotHub": "stainless_304L",
        "TargetRotaryArm": "stainless_304L",
        "TargetHolderFrame": "stainless_304L",
        "TargetFoil": target.foil.material,
    }
    return TargetSystemGeometry(
        work=work,
        park=park,
        motion_samples=samples,
        stationary={"TargetRotaryShaft": shaft},
        interfaces=interfaces,
        keepouts={
            "TargetCompleteMotionSweep": sweep,
            "TargetParkEnvelope": Part.makeCompound(list(park.physical.values())),
        },
        datums=datums,
        materials=materials,
    )
