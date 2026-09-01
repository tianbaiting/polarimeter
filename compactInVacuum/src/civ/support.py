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
        datums=datums,
    )
