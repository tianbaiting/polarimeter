from __future__ import annotations

import math
from dataclasses import dataclass

import FreeCAD as App
import Part

from .config import CIVConfig, EndModuleSideConfig, end_module_has_groove
from .layout import (
    DetectorPlacement,
    detector_center,
    detector_outer_face_center,
    placement_from_direction,
    scaled,
)


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


@dataclass(frozen=True)
class TopServicePortSpec:
    name: str
    role: str
    center_x_mm: float
    center_z_mm: float
    inner_diameter_mm: float
    outer_diameter_mm: float
    collar_length_mm: float


def top_service_port_specs(cfg: CIVConfig) -> tuple[TopServicePortSpec, ...]:
    services = cfg.top_services
    if services is None:
        return ()

    electrical = services.electrical
    specs = [
        TopServicePortSpec(
            name="RotaryTarget",
            role="rotary",
            center_x_mm=services.rotary.pivot_x_mm,
            center_z_mm=services.rotary.pivot_z_mm,
            inner_diameter_mm=services.rotary.port_inner_diameter_mm,
            outer_diameter_mm=services.rotary.port_outer_diameter_mm,
            collar_length_mm=services.rotary.port_collar_length_mm,
        )
    ]
    specs.extend(
        TopServicePortSpec(
            name=f"Signal_{port.name}",
            role="signal",
            center_x_mm=port.center_x_mm,
            center_z_mm=port.center_z_mm,
            inner_diameter_mm=electrical.signal_port_inner_diameter_mm,
            outer_diameter_mm=electrical.signal_port_outer_diameter_mm,
            collar_length_mm=electrical.signal_port_collar_length_mm,
        )
        for port in electrical.signal_ports
    )
    housekeeping = electrical.housekeeping
    specs.append(
        TopServicePortSpec(
            name=f"Housekeeping_{housekeeping.name}",
            role="housekeeping",
            center_x_mm=housekeeping.center_x_mm,
            center_z_mm=housekeeping.center_z_mm,
            inner_diameter_mm=housekeeping.port_inner_diameter_mm,
            outer_diameter_mm=housekeeping.port_outer_diameter_mm,
            collar_length_mm=housekeeping.port_collar_length_mm,
        )
    )
    return tuple(specs)


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
    shell = shell.cut(upstream_bore).cut(downstream_bore)

    # [EN] Every enabled top-service bore is cut from the pressure shell before its welded collar is fused, preserving a traceable vacuum path instead of drawing decorative hardware on an unpierced wall. / [CN] 每个启用的顶部服务孔先从压力壳体切除，再熔合焊接短管，从而形成可追踪的真空通道，而不是在未开孔壁面上叠加装饰性硬件。
    top_inner_y_mm = 0.5 * cfg.vessel.inner_size_y_mm
    for spec in top_service_port_specs(cfg):
        bore = _cylinder(
            0.5 * spec.inner_diameter_mm,
            wall + (2.0 * overlap_mm),
            App.Vector(spec.center_x_mm, top_inner_y_mm - overlap_mm, spec.center_z_mm),
            App.Vector(0.0, 1.0, 0.0),
        )
        shell = shell.cut(bore)
    return shell


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


def _top_interface_face_y(cfg: CIVConfig, spec: TopServicePortSpec) -> float:
    if cfg.top_services is None:
        raise ValueError("top service geometry requires top_services configuration")
    top_outer_y_mm = 0.5 * cfg.vessel.inner_size_y_mm + cfg.vessel.wall_thickness_mm
    return (
        top_outer_y_mm
        + spec.collar_length_mm
        + cfg.top_services.icf70_interface.module_thickness_mm
    )


def _build_top_service_mount(cfg: CIVConfig, spec: TopServicePortSpec) -> Part.Shape:
    if cfg.top_services is None:
        raise ValueError("top service geometry requires top_services configuration")
    module = cfg.top_services.icf70_interface
    axis = App.Vector(0.0, 1.0, 0.0)
    top_outer_y_mm = 0.5 * cfg.vessel.inner_size_y_mm + cfg.vessel.wall_thickness_mm
    collar_origin = App.Vector(spec.center_x_mm, top_outer_y_mm, spec.center_z_mm)
    collar = _tube_shape(
        spec.outer_diameter_mm,
        spec.inner_diameter_mm,
        spec.collar_length_mm,
        collar_origin,
        axis,
    )
    flange_origin = collar_origin + scaled(axis, spec.collar_length_mm)
    flange = _tube_shape(
        module.module_outer_diameter_mm,
        module.module_inner_diameter_mm,
        module.module_thickness_mm,
        flange_origin,
        axis,
    )

    bolt_radius_mm = 0.5 * module.bolt_circle_diameter_mm
    for idx in range(module.bolt_count):
        angle_rad = 2.0 * math.pi * float(idx) / float(module.bolt_count)
        x_mm = spec.center_x_mm + bolt_radius_mm * math.cos(angle_rad)
        z_mm = spec.center_z_mm + bolt_radius_mm * math.sin(angle_rad)
        bolt_hole = _cylinder(
            0.5 * module.flange_bolt_hole_diameter_mm,
            module.module_thickness_mm + 2.0,
            App.Vector(x_mm, flange_origin.y - 1.0, z_mm),
            axis,
        )
        flange = flange.cut(bolt_hole)

    # [EN] The common ICF70 flange is an interface contract only; its knife edge remains governed by the signed supplier drawing and is intentionally not reverse-engineered here. / [CN] 共用 ICF70 法兰在此仅表示接口合同；刀口仍以供应商签字图纸为准，本模型不反向仿制刀口。
    return collar.fuse(flange)


def build_top_service_mounts(cfg: CIVConfig) -> dict[str, Part.Shape]:
    return {
        f"TopServiceMount_{spec.name}_ICF70": _build_top_service_mount(cfg, spec)
        for spec in top_service_port_specs(cfg)
    }


def build_top_service_equipment_envelopes(cfg: CIVConfig) -> dict[str, Part.Shape]:
    services = cfg.top_services
    if services is None:
        return {}

    electrical = services.electrical
    spec_by_name = {spec.name: spec for spec in top_service_port_specs(cfg)}
    axis = App.Vector(0.0, 1.0, 0.0)
    out: dict[str, Part.Shape] = {}
    for port in electrical.signal_ports:
        spec = spec_by_name[f"Signal_{port.name}"]
        face_y_mm = _top_interface_face_y(cfg, spec)
        body = _cylinder(
            0.5 * electrical.signal_equipment_envelope_diameter_mm,
            electrical.signal_equipment_envelope_length_mm,
            App.Vector(port.center_x_mm, face_y_mm, port.center_z_mm),
            axis,
        )
        out[f"SignalFeedthroughEnvelope_{port.name}_4ch"] = body

    housekeeping = electrical.housekeeping
    housekeeping_spec = spec_by_name[f"Housekeeping_{housekeeping.name}"]
    housekeeping_face_y_mm = _top_interface_face_y(cfg, housekeeping_spec)
    out[f"HousekeepingFeedthroughEnvelope_{housekeeping.name}_{housekeeping.feedthrough_pin_count}pin"] = _cylinder(
        0.5 * housekeeping.equipment_envelope_diameter_mm,
        housekeeping.equipment_envelope_length_mm,
        App.Vector(housekeeping.center_x_mm, housekeeping_face_y_mm, housekeeping.center_z_mm),
        axis,
    )

    rotary = services.rotary
    rotary_spec = spec_by_name["RotaryTarget"]
    rotary_face_y_mm = _top_interface_face_y(cfg, rotary_spec)
    body = _cylinder(
        0.5 * rotary.external_body_diameter_mm,
        rotary.external_body_length_mm,
        App.Vector(rotary.pivot_x_mm, rotary_face_y_mm, rotary.pivot_z_mm),
        axis,
    )
    handwheel = _cylinder(
        0.5 * rotary.handwheel_diameter_mm,
        rotary.handwheel_thickness_mm,
        App.Vector(
            rotary.pivot_x_mm,
            rotary_face_y_mm + rotary.external_body_length_mm,
            rotary.pivot_z_mm,
        ),
        axis,
    )
    out[f"RotaryFeedthroughEnvelope_{rotary.supplier_reference_code}"] = Part.makeCompound([body, handwheel])
    return out


def build_inner_frame(cfg: CIVConfig, placements: list[DetectorPlacement]) -> Part.Shape:
    wall_clearance_mm = (
        cfg.top_services.electrical.routing.wall_clearance_mm
        if cfg.top_services is not None
        else 20.0
    )
    x_limit_mm = 0.5 * cfg.vessel.inner_size_x_mm - wall_clearance_mm
    y_limit_mm = 0.5 * cfg.vessel.inner_size_y_mm - wall_clearance_mm
    _, vessel_z_max_mm = vessel_z_bounds(cfg)
    z_limit_mm = vessel_z_max_mm - wall_clearance_mm
    support_shapes: list[Part.Shape] = []

    for placement in placements:
        start = detector_outer_face_center(placement, cfg.detector.length_mm)
        candidates: list[float] = []
        if abs(placement.direction.x) > 1.0e-12:
            boundary_x_mm = math.copysign(x_limit_mm, placement.direction.x)
            candidates.append((boundary_x_mm - start.x) / placement.direction.x)
        if abs(placement.direction.y) > 1.0e-12:
            boundary_y_mm = math.copysign(y_limit_mm, placement.direction.y)
            candidates.append((boundary_y_mm - start.y) / placement.direction.y)
        if placement.direction.z > 1.0e-12:
            candidates.append((z_limit_mm - start.z) / placement.direction.z)
        positive_candidates = [distance for distance in candidates if distance > 1.0]
        if not positive_candidates:
            raise ValueError(f"detector support ray for {placement.tag} does not reach an internal service wall")
        arm_length_mm = min(positive_candidates)

        # [EN] Supports start at the detector back face and continue away from the target to the first service wall, so no support material is placed in the incoming elastic-particle path. / [CN] 支撑从探测器背面开始并远离靶点延伸到首个服务壁面，因此入射到探测器的弹性散射粒子路径中不再放置支撑材料。
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
        arm.Placement = placement_from_direction(start, placement.direction)
        support_shapes.append(arm)

        anchor_depth_mm = min(6.0, arm_length_mm)
        anchor_origin = start + scaled(placement.direction, arm_length_mm - anchor_depth_mm)
        anchor = _cylinder(
            0.5 * cfg.inner_frame.spine_diameter_mm,
            anchor_depth_mm,
            anchor_origin,
            placement.direction,
        )
        support_shapes.append(anchor)

    return Part.makeCompound(support_shapes)


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

    origin = detector_center(placement)
    placement_transform = placement_from_direction(origin, placement.direction)
    detector.Placement = placement_transform
    clamp.Placement = placement_transform

    return Part.makeCompound([detector, clamp])


def _rotated_shape(shape: Part.Shape, center: App.Vector, axis: App.Vector, angle_deg: float) -> Part.Shape:
    if abs(angle_deg) <= 1.0e-9:
        return shape
    rotated = shape.copy()
    rotated.rotate(center, axis, angle_deg)
    return rotated


def rotary_target_center(cfg: CIVConfig, angle_deg: float) -> App.Vector:
    if cfg.top_services is None:
        raise ValueError("rotary target geometry requires top_services configuration")
    rotary = cfg.top_services.rotary
    theta_rad = math.radians(angle_deg)
    return App.Vector(
        rotary.pivot_x_mm - rotary.arm_length_mm * math.cos(theta_rad),
        0.0,
        rotary.pivot_z_mm + rotary.arm_length_mm * math.sin(theta_rad),
    )


def build_rotary_target_shapes(cfg: CIVConfig, angle_deg: float) -> dict[str, Part.Shape]:
    if cfg.top_services is None:
        return {}
    rotary = cfg.top_services.rotary
    pivot = App.Vector(rotary.pivot_x_mm, 0.0, rotary.pivot_z_mm)
    axis_y = App.Vector(0.0, 1.0, 0.0)
    arm_center_y_mm = 0.5 * rotary.holder_outer_height_mm + 0.5 * rotary.arm_width_mm - 2.0
    rotary_spec = next(spec for spec in top_service_port_specs(cfg) if spec.role == "rotary")
    shaft_length_mm = _top_interface_face_y(cfg, rotary_spec)
    shaft = _cylinder(
        0.5 * rotary.shaft_diameter_mm,
        shaft_length_mm,
        pivot,
        axis_y,
    )
    hub = _cylinder(
        0.5 * rotary.hub_diameter_mm,
        rotary.hub_thickness_mm,
        pivot + App.Vector(0.0, arm_center_y_mm - 0.5 * rotary.hub_thickness_mm, 0.0),
        axis_y,
    )
    arm = Part.makeBox(
        rotary.arm_length_mm,
        rotary.arm_width_mm,
        rotary.arm_thickness_mm,
        App.Vector(
            rotary.pivot_x_mm - rotary.arm_length_mm,
            arm_center_y_mm - 0.5 * rotary.arm_width_mm,
            rotary.pivot_z_mm - 0.5 * rotary.arm_thickness_mm,
        ),
    )

    holder_outer = Part.makeBox(
        rotary.holder_outer_width_mm,
        rotary.holder_outer_height_mm,
        rotary.holder_thickness_mm,
        App.Vector(
            -0.5 * rotary.holder_outer_width_mm,
            -0.5 * rotary.holder_outer_height_mm,
            -0.5 * rotary.holder_thickness_mm,
        ),
    )
    holder_inner_width_mm = rotary.holder_outer_width_mm - 2.0 * rotary.holder_frame_width_mm
    holder_inner_height_mm = rotary.holder_outer_height_mm - 2.0 * rotary.holder_frame_width_mm
    holder_inner = Part.makeBox(
        holder_inner_width_mm,
        holder_inner_height_mm,
        rotary.holder_thickness_mm + 0.4,
        App.Vector(
            -0.5 * holder_inner_width_mm,
            -0.5 * holder_inner_height_mm,
            -0.5 * rotary.holder_thickness_mm - 0.2,
        ),
    )
    holder = holder_outer.cut(holder_inner)
    target = _cylinder(
        0.5 * rotary.target_diameter_mm,
        rotary.target_thickness_mm,
        App.Vector(0.0, 0.0, -0.5 * rotary.target_thickness_mm),
    )

    # [EN] Work and park poses share the same analytical Y-axis pivot, allowing collision and beam-clearance checks without duplicating independent placement assumptions. / [CN] 工作位与停靠位共用同一个解析 Y 轴枢轴，可在不复制独立定位假设的情况下检查碰撞和束流净空。
    return {
        "RotaryTargetShaft": shaft,
        "RotaryTargetHub": _rotated_shape(hub, pivot, axis_y, angle_deg),
        "RotaryTargetArm": _rotated_shape(arm, pivot, axis_y, angle_deg),
        "RotaryTargetHolder": _rotated_shape(holder, pivot, axis_y, angle_deg),
        "RotaryTargetFoil": _rotated_shape(target, pivot, axis_y, angle_deg),
    }


def build_rotary_target_work_shapes(cfg: CIVConfig) -> dict[str, Part.Shape]:
    if cfg.top_services is None:
        return {}
    return build_rotary_target_shapes(cfg, cfg.top_services.rotary.work_angle_deg)


def build_rotary_target_park_keepout(cfg: CIVConfig) -> Part.Shape | None:
    if cfg.top_services is None:
        return None
    shapes = build_rotary_target_shapes(cfg, cfg.top_services.rotary.park_angle_deg)
    return Part.makeCompound(
        [
            shape
            for name, shape in shapes.items()
            if name in {"RotaryTargetArm", "RotaryTargetHolder", "RotaryTargetFoil"}
        ]
    )


def _segment_keepout(start: App.Vector, end: App.Vector, radius_mm: float) -> Part.Shape:
    delta = end - start
    length_mm = delta.Length
    if length_mm <= 1.0e-9:
        return Part.makeSphere(radius_mm, start)
    return _cylinder(radius_mm, length_mm, start, delta)


def _cable_route_points(
    cfg: CIVConfig,
    placement: DetectorPlacement,
    port_x_mm: float,
    port_z_mm: float,
    lane_offset_mm: float,
) -> list[App.Vector]:
    if cfg.top_services is None:
        raise ValueError("cable routes require top_services configuration")
    routing = cfg.top_services.electrical.routing
    x_wall_mm = 0.5 * cfg.vessel.inner_size_x_mm - routing.wall_clearance_mm
    y_wall_mm = 0.5 * cfg.vessel.inner_size_y_mm - routing.wall_clearance_mm
    start = detector_outer_face_center(placement, cfg.detector.length_mm)
    lane_z_mm = start.z + lane_offset_mm
    endpoint = App.Vector(port_x_mm + lane_offset_mm, y_wall_mm, port_z_mm)

    if placement.sector_name == "left":
        return [
            start,
            App.Vector(-x_wall_mm, start.y, lane_z_mm),
            App.Vector(-x_wall_mm, y_wall_mm, lane_z_mm),
            endpoint,
        ]
    if placement.sector_name == "right":
        return [
            start,
            App.Vector(x_wall_mm, start.y, lane_z_mm),
            App.Vector(x_wall_mm, y_wall_mm, lane_z_mm),
            endpoint,
        ]
    if placement.sector_name == "up":
        return [
            start,
            App.Vector(start.x, y_wall_mm, lane_z_mm),
            endpoint,
        ]
    return [
        start,
        App.Vector(start.x, -y_wall_mm, lane_z_mm),
        App.Vector(x_wall_mm, -y_wall_mm, lane_z_mm),
        App.Vector(x_wall_mm, y_wall_mm, lane_z_mm),
        endpoint,
    ]


def build_cable_route_keepouts(
    cfg: CIVConfig,
    placements: list[DetectorPlacement],
) -> dict[str, Part.Shape]:
    if cfg.top_services is None:
        return {}
    electrical = cfg.top_services.electrical
    routing = electrical.routing
    radius_mm = 0.5 * routing.cable_keepout_diameter_mm
    port_by_sector = {port.sector: port for port in electrical.signal_ports}
    channel_lane = {
        channel.name: (float(idx) - 0.5 * float(len(cfg.channels) - 1)) * routing.cable_keepout_diameter_mm
        for idx, channel in enumerate(cfg.channels)
    }
    out: dict[str, Part.Shape] = {}
    for placement in placements:
        port = port_by_sector[placement.sector_name]
        points = _cable_route_points(
            cfg,
            placement,
            port.center_x_mm,
            port.center_z_mm,
            channel_lane[placement.channel_name],
        )
        segments = [
            _segment_keepout(start, end, radius_mm)
            for start, end in zip(points, points[1:])
        ]
        joints = [Part.makeSphere(radius_mm, point) for point in points]
        out[f"CableRouteKeepout_{placement.tag}"] = Part.makeCompound([*segments, *joints])
    return out


def build_housekeeping_harness_keepouts(cfg: CIVConfig) -> dict[str, Part.Shape]:
    if cfg.top_services is None:
        return {}
    electrical = cfg.top_services.electrical
    routing = electrical.routing
    radius_mm = 0.5 * routing.cable_keepout_diameter_mm
    y_wall_mm = 0.5 * cfg.vessel.inner_size_y_mm - routing.wall_clearance_mm
    housekeeping = electrical.housekeeping
    destination = App.Vector(housekeeping.center_x_mm, y_wall_mm, housekeeping.center_z_mm)
    out: dict[str, Part.Shape] = {}
    for port in electrical.signal_ports:
        origin = App.Vector(port.center_x_mm, y_wall_mm, port.center_z_mm)
        midpoint = App.Vector(port.center_x_mm, y_wall_mm, housekeeping.center_z_mm)
        out[f"HousekeepingHarnessKeepout_{port.sector}"] = Part.makeCompound(
            [
                _segment_keepout(origin, midpoint, radius_mm),
                _segment_keepout(midpoint, destination, radius_mm),
                Part.makeSphere(radius_mm, midpoint),
            ]
        )
    return out


def build_strain_relief_envelopes(
    cfg: CIVConfig,
    placements: list[DetectorPlacement],
) -> dict[str, Part.Shape]:
    if cfg.top_services is None:
        return {}
    electrical = cfg.top_services.electrical
    routing = electrical.routing
    out: dict[str, Part.Shape] = {}
    for placement in placements:
        origin = detector_outer_face_center(placement, cfg.detector.length_mm)
        out[f"DetectorStrainRelief_{placement.tag}"] = _cylinder(
            0.5 * routing.strain_relief_width_mm,
            routing.strain_relief_length_mm,
            origin,
            placement.direction,
        )

    y_wall_mm = 0.5 * cfg.vessel.inner_size_y_mm - routing.wall_clearance_mm
    for port in electrical.signal_ports:
        out[f"FeedthroughStrainRelief_{port.sector}"] = Part.makeBox(
            routing.strain_relief_width_mm,
            routing.strain_relief_thickness_mm,
            routing.strain_relief_length_mm,
            App.Vector(
                port.center_x_mm - 0.5 * routing.strain_relief_width_mm,
                y_wall_mm - routing.strain_relief_thickness_mm,
                port.center_z_mm - 0.5 * routing.strain_relief_length_mm,
            ),
        )
    return out


def build_grounding_envelopes(cfg: CIVConfig) -> dict[str, Part.Shape]:
    if cfg.top_services is None:
        return {}
    housekeeping = cfg.top_services.electrical.housekeeping
    top_outer_y_mm = 0.5 * cfg.vessel.inner_size_y_mm + cfg.vessel.wall_thickness_mm
    stud_x_mm = housekeeping.center_x_mm - 50.0
    stud = _cylinder(
        5.0,
        20.0,
        App.Vector(stud_x_mm, top_outer_y_mm, housekeeping.center_z_mm),
        App.Vector(0.0, 1.0, 0.0),
    )
    return {"ProtectiveEarthBondStudEnvelope": stud}
