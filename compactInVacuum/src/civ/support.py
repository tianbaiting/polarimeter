from __future__ import annotations

from dataclasses import dataclass

import FreeCAD as App
import Part

from .config import CIVConfig
from .layout import scaled


@dataclass(frozen=True)
class SectorMountGeometry:
    interface_center: App.Vector
    outward: App.Vector
    tangent: App.Vector
    release_direction: App.Vector
    interface_block: Part.Shape
    holder_dock_plane: Part.Shape
    stationary_support: Part.Shape
    chamber_mount_plane: Part.Shape
    stationary_purchased_interfaces: dict[str, Part.Shape]
    holder_fasteners: dict[str, Part.Shape]
    datums: dict[str, Part.Shape]


def _mount_axes(cfg: CIVConfig, sector: str) -> tuple[App.Vector, App.Vector]:
    mount = cfg.compact_one.deployment.sector_mount(sector)
    return {
        "negative_x": (App.Vector(-1.0, 0.0, 0.0), App.Vector(0.0, 1.0, 0.0)),
        "positive_x": (App.Vector(1.0, 0.0, 0.0), App.Vector(0.0, 1.0, 0.0)),
        "positive_y": (App.Vector(0.0, 1.0, 0.0), App.Vector(1.0, 0.0, 0.0)),
        "negative_y": (App.Vector(0.0, -1.0, 0.0), App.Vector(1.0, 0.0, 0.0)),
    }[mount.wall]


def _oriented_interface_block(
    center: App.Vector,
    outward: App.Vector,
    tangent: App.Vector,
    radial_depth_mm: float,
    tangent_width_mm: float,
    height_mm: float,
) -> Part.Shape:
    half_radial = scaled(outward, 0.5 * radial_depth_mm)
    half_tangent = scaled(tangent, 0.5 * tangent_width_mm)
    lower_center = center - App.Vector(0.0, 0.0, 0.5 * height_mm)
    points = [
        lower_center - half_radial - half_tangent,
        lower_center + half_radial - half_tangent,
        lower_center + half_radial + half_tangent,
        lower_center - half_radial + half_tangent,
    ]
    wire = Part.makePolygon([*points, points[0]])
    return Part.Face(wire).extrude(App.Vector(0.0, 0.0, height_mm))


def build_sector_mount(
    cfg: CIVConfig,
    sector: str,
    axial_center_z_mm: float,
) -> SectorMountGeometry:
    if cfg.compact_one.deployment.support_frame is not None:
        return _build_frame_dock(cfg, sector)
    holder = cfg.compact_one.sector_holder
    mount = cfg.compact_one.deployment.sector_mount(sector)
    outward, tangent = _mount_axes(cfg, sector)
    radial_depth_mm, tangent_width_mm, height_mm = holder.interface_block_mm
    mount_half_size_mm = 0.5 * (
        cfg.vessel.inner_size_x_mm
        if abs(outward.x) > 0.5
        else cfg.vessel.inner_size_y_mm
    )
    interface_center = (
        scaled(
            outward,
            mount_half_size_mm
            - mount.wall_standoff_mm
            - 0.5 * radial_depth_mm,
        )
        + scaled(tangent, mount.tangent_coordinate_mm)
        + App.Vector(0.0, 0.0, axial_center_z_mm)
    )
    block = _oriented_interface_block(
        interface_center,
        outward,
        tangent,
        radial_depth_mm,
        tangent_width_mm,
        height_mm,
    )
    bore_start = interface_center - scaled(
        outward,
        0.5 * radial_depth_mm + 0.2,
    )
    pin_center = bore_start - scaled(tangent, 10.0) - App.Vector(0.0, 0.0, 12.0)
    slot_center = bore_start + scaled(tangent, 10.0) + App.Vector(0.0, 0.0, 12.0)
    round_bore = Part.makeCylinder(
        0.5 * holder.locating_pin_diameter_mm,
        radial_depth_mm + 0.4,
        pin_center,
        outward,
    )
    slot_delta_mm = max(
        0.0,
        holder.locating_slot_length_mm - holder.locating_slot_width_mm,
    )
    slot_a = Part.makeCylinder(
        0.5 * holder.locating_slot_width_mm,
        radial_depth_mm + 0.4,
        slot_center - App.Vector(0.0, 0.0, 0.5 * slot_delta_mm),
        outward,
    )
    slot_b = Part.makeCylinder(
        0.5 * holder.locating_slot_width_mm,
        radial_depth_mm + 0.4,
        slot_center + App.Vector(0.0, 0.0, 0.5 * slot_delta_mm),
        outward,
    )
    slot_bore = slot_a.fuse(slot_b)
    block = block.cut(round_bore).cut(slot_bore)
    dock_plane_center = interface_center + scaled(outward, 0.5 * radial_depth_mm)
    holder_dock_plane = _oriented_interface_block(
        dock_plane_center,
        outward,
        tangent,
        0.05,
        tangent_width_mm,
        height_mm,
    )
    support_center = dock_plane_center + scaled(
        outward,
        0.5 * mount.wall_standoff_mm,
    )
    stationary_support = _oriented_interface_block(
        support_center,
        outward,
        tangent,
        mount.wall_standoff_mm,
        tangent_width_mm,
        height_mm,
    )
    chamber_plane_center = dock_plane_center + scaled(
        outward,
        mount.wall_standoff_mm,
    )
    chamber_mount_plane = _oriented_interface_block(
        chamber_plane_center,
        outward,
        tangent,
        0.05,
        tangent_width_mm,
        height_mm,
    )
    purchased = {
        f"{sector}_RoundLocatingPinEnvelope": Part.makeCylinder(
            0.5 * holder.locating_pin_diameter_mm - 0.1,
            radial_depth_mm,
            pin_center + scaled(outward, 0.2),
            outward,
        ),
        f"{sector}_SlotLocatingPinEnvelope": Part.makeCylinder(
            0.5 * holder.locating_slot_width_mm - 0.2,
            radial_depth_mm,
            slot_center + scaled(outward, 0.2),
            outward,
        ),
    }
    datums = {
        f"{sector}_PrimaryPlaneDatum": holder_dock_plane.copy(),
        f"{sector}_PermanentWallPlaneDatum": chamber_mount_plane.copy(),
        f"{sector}_RoundPinAxisDatum": round_bore.copy(),
        f"{sector}_ClockingSlotDatum": slot_bore.copy(),
        f"{sector}_SurveyDatumA": Part.makeSphere(
            1.0,
            interface_center - scaled(tangent, 0.35 * tangent_width_mm),
        ),
        f"{sector}_SurveyDatumB": Part.makeSphere(
            1.0,
            interface_center + scaled(tangent, 0.35 * tangent_width_mm),
        ),
        f"{sector}_SurveyDatumC": Part.makeSphere(
            1.0,
            interface_center + App.Vector(0.0, 0.0, 0.35 * height_mm),
        ),
    }
    # [EN] The long wall-reaching support and locating pins are stationary; only the compact block remains with the removable holder. / [CN] 长壁侧支座和定位销属于固定件；仅紧凑接口块随可拆载架移动。
    return SectorMountGeometry(
        interface_center=interface_center,
        outward=outward,
        tangent=tangent,
        release_direction=scaled(outward, -1.0),
        interface_block=block,
        holder_dock_plane=holder_dock_plane,
        stationary_support=stationary_support,
        chamber_mount_plane=chamber_mount_plane,
        stationary_purchased_interfaces=purchased,
        holder_fasteners={},
        datums=datums,
    )


def _frame_radial(sector: str) -> App.Vector:
    return {
        "left": App.Vector(-1, 0, 0), "right": App.Vector(1, 0, 0),
        "up": App.Vector(0, 1, 0), "down": App.Vector(0, -1, 0),
    }[sector]


def _frame_box(
    center: App.Vector,
    tangent: App.Vector,
    radial: App.Vector,
    width: float,
    height: float,
    z_depth: float,
) -> Part.Shape:
    corners = [
        center + scaled(tangent, sx * width / 2) + scaled(radial, sy * height / 2)
        for sx, sy in [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    ]
    return Part.Face(Part.makePolygon([*corners, corners[0]])).extrude(App.Vector(0, 0, z_depth))


def _build_frame_dock(cfg: CIVConfig, sector: str) -> SectorMountGeometry:
    frame = cfg.compact_one.deployment.support_frame
    holder = cfg.compact_one.sector_holder
    depth, width, height = holder.interface_block_mm
    radial = _frame_radial(sector)
    tangent = App.Vector(-radial.y, radial.x, 0)
    normal = App.Vector(0, 0, 1)
    face = scaled(radial, frame.mount_radius_mm) + App.Vector(0, 0, frame.dock_face_z_mm)
    front = face - App.Vector(0, 0, depth)
    block = _frame_box(front, tangent, radial, width, height, depth)
    socket = _frame_box(face, tangent, radial, width, height, frame.socket_depth_mm)
    pins = {}
    datums = {}
    for kind, t, r, diameter in [
        ("Round", -10.0, -12.0, holder.locating_pin_diameter_mm),
        ("Slot", 10.0, 12.0, holder.locating_slot_width_mm),
    ]:
        point = front + scaled(tangent, t) + scaled(radial, r)
        bore = Part.makeCylinder(diameter / 2, depth + 0.4, point - scaled(normal, 0.2), normal)
        if kind == "Slot":
            offset = scaled(radial, (holder.locating_slot_length_mm - diameter) / 2)
            a, b = bore.copy(), bore.copy()
            a.translate(offset)
            b.translate(-offset)
            bridge = _frame_box(point - scaled(normal, 0.2), tangent, radial, diameter, holder.locating_slot_length_mm - diameter, depth + 0.4)
            bore = a.fuse(b).fuse(bridge)
        block = block.cut(bore)
        pins[f"{sector}_{kind}LocatingPinEnvelope"] = Part.makeCylinder(diameter / 2 - 0.1, depth, point, normal)
        datums[f"{sector}_{kind}PinAxisDatum"] = bore
        if kind == "Slot":
            datums[f"{sector}_ClockingSlotDatum"] = bore
    fasteners = {}
    for index, t in enumerate((-14.0, 14.0), 1):
        point = front + scaled(tangent, t)
        hole = Part.makeCylinder(2.25, depth + frame.socket_depth_mm, point, normal)
        block = block.cut(hole)
        socket = socket.cut(hole)
        # [EN] M4 envelopes demonstrate a separate clamping load path; threads and preload remain provisional. / [CN] M4 包络展示独立夹紧载荷路径；螺纹和预紧力仍为暂定。
        fasteners[f"{sector}_M4DockClampEnvelope_{index}"] = Part.makeCylinder(2.0, depth + 6.0, point, normal).fuse(
            Part.makeCylinder(3.5, 3.0, point - scaled(normal, 3.0), normal)
        )
    dock = _frame_box(face - scaled(normal, 0.025), tangent, radial, width, height, 0.05)
    back = _frame_box(face + scaled(normal, frame.socket_depth_mm - 0.025), tangent, radial, width, height, 0.05)
    datums[f"{sector}_PrimaryPlaneDatum"] = dock
    for index, (t, r) in enumerate([(-width * .35, 0), (width * .35, 0), (0, height * .35)]):
        datums[f"{sector}_SurveyDatum{chr(65 + index)}"] = Part.makeSphere(1.0, face + scaled(tangent, t) + scaled(radial, r))
    return SectorMountGeometry(
        interface_center=face - scaled(normal, depth / 2), outward=normal,
        tangent=tangent, release_direction=-normal, interface_block=block,
        holder_dock_plane=dock, stationary_support=socket, chamber_mount_plane=back,
        stationary_purchased_interfaces=pins, holder_fasteners=fasteners, datums=datums,
    )


def build_common_support_frame(cfg: CIVConfig) -> Part.Shape | None:
    frame = cfg.compact_one.deployment.support_frame
    if frame is None:
        return None
    radius, half_width = frame.mount_radius_mm, frame.rail_width_mm / 2
    z = frame.dock_face_z_mm + frame.socket_depth_mm
    depth = frame.frame_depth_mm
    points = [(0, radius), (-radius, radius), (-radius, -radius), (radius, -radius), (radius, radius)]
    parts = [Part.makeCylinder(half_width, depth, App.Vector(x, y, z)) for x, y in points]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if x1 == x2:
            parts.append(Part.makeBox(2 * half_width, abs(y2 - y1), depth, App.Vector(x1 - half_width, min(y1, y2), z)))
        else:
            parts.append(Part.makeBox(abs(x2 - x1), 2 * half_width, depth, App.Vector(min(x1, x2), y1 - half_width, z)))
    # [EN] Feet belong to one stationary frame and terminate on permanent side/bottom walls, never the access closure. / [CN] 接脚属于同一固定基架并终止于永久侧壁和底壁，绝不连接操作口盖板。
    foot = frame.wall_foot_width_mm
    half_x, half_y = cfg.vessel.inner_size_x_mm / 2, cfg.vessel.inner_size_y_mm / 2
    for sign in (-1, 1):
        for y in (-radius, radius):
            parts.append(Part.makeBox(half_x - radius, foot, depth, App.Vector(-half_x if sign < 0 else radius, y - foot / 2, z)))
        parts.append(Part.makeBox(foot, half_y - radius, depth, App.Vector(sign * radius - foot / 2, -half_y, z)))
    shape = parts[0].multiFuse(parts[1:]).removeSplitter()
    if not shape.isValid() or len(shape.Solids) != 1:
        raise ValueError("common support frame must be one connected valid solid")
    return shape
