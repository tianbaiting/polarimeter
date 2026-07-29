from __future__ import annotations

from dataclasses import dataclass

import FreeCAD as App
import Part

from .cassette import (
    DetectorHeadGeometry,
    build_detector_head,
    detector_connector_segment,
)
from .config import CIVConfig
from .detector import build_active_acceptance_cone
from .layout import (
    DetectorPlacement,
    build_detector_placements,
    cassette_axis_position,
    detector_center,
    normalize,
    placement_from_direction,
    scaled,
)


@dataclass(frozen=True)
class SectorHolderGeometry:
    sector: str
    placements: tuple[DetectorPlacement, ...]
    service_junction: App.Vector
    physical: dict[str, Part.Shape]
    purchased_interfaces: dict[str, Part.Shape]
    interfaces: dict[str, Part.Shape]
    keepouts: dict[str, Part.Shape]
    datums: dict[str, Part.Shape]
    materials: dict[str, str]
    thermal_connections: tuple[tuple[str, str], ...]
    holder_physical_names: tuple[str, ...]
    removal_poses: tuple[Part.Shape, ...]


def _segment_keepout(
    start: App.Vector,
    end: App.Vector,
    radius_mm: float,
) -> Part.Shape:
    delta = end - start
    if delta.Length <= 1.0e-9:
        return Part.makeSphere(radius_mm, start)
    return Part.makeCylinder(radius_mm, delta.Length, start, delta)


def _sector_outward(sector: str) -> App.Vector:
    return {
        "left": App.Vector(-1.0, 0.0, 0.0),
        "right": App.Vector(1.0, 0.0, 0.0),
        "up": App.Vector(0.0, 1.0, 0.0),
        "down": App.Vector(0.0, -1.0, 0.0),
    }[sector]


def _sector_tangent(sector: str) -> App.Vector:
    return (
        App.Vector(0.0, 1.0, 0.0)
        if sector in {"left", "right"}
        else App.Vector(1.0, 0.0, 0.0)
    )


def _web_between(
    start: App.Vector,
    end: App.Vector,
    tangent: App.Vector,
    width_mm: float,
    thickness_mm: float,
) -> Part.Shape:
    delta = end - start
    if delta.Length <= 1.0e-9:
        raise ValueError("sector carrier web endpoints must be distinct")
    axis = normalize(delta)
    side = normalize(tangent.cross(axis))
    half_width = scaled(side, 0.5 * width_mm)
    half_thickness = scaled(tangent, 0.5 * thickness_mm)
    points = [
        start - half_width - half_thickness,
        end - half_width - half_thickness,
        end + half_width - half_thickness,
        start + half_width - half_thickness,
    ]
    wire = Part.makePolygon([*points, points[0]])
    return Part.Face(wire).extrude(scaled(tangent, thickness_mm))


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


def _placed_local_shape(
    shape: Part.Shape,
    placement: DetectorPlacement,
) -> Part.Shape:
    copy = shape.copy()
    copy.Placement = placement_from_direction(
        detector_center(placement),
        placement.direction,
    ).multiply(copy.Placement)
    return copy


def _local_nest_shapes(
    cfg: CIVConfig,
    screws_along_local_x: bool,
) -> tuple[Part.Shape, Part.Shape, tuple[Part.Shape, Part.Shape]]:
    detector = cfg.compact_one.detector
    head = detector.head
    holder = cfg.compact_one.sector_holder
    rear_z_mm = detector.rear_housing_offset_mm
    stop_z_mm = rear_z_mm - head.rear_cap_wall_mm
    inner_radius_mm = (
        0.5 * detector.housing_outer_diameter_mm
        + holder.nest_clearance_mm
    )
    outer_radius_mm = inner_radius_mm + holder.nest_radial_wall_mm
    nest_start_z_mm = stop_z_mm - holder.nest_axial_depth_mm
    cradle = Part.makeCylinder(
        outer_radius_mm,
        holder.nest_axial_depth_mm,
        App.Vector(0.0, 0.0, nest_start_z_mm),
    ).cut(
        Part.makeCylinder(
            inner_radius_mm,
            holder.nest_axial_depth_mm + 0.4,
            App.Vector(0.0, 0.0, nest_start_z_mm - 0.2),
        )
    )

    boss_offset_mm = outer_radius_mm + 2.5
    boss_radius_mm = 3.5
    screw_radius_mm = 0.5 * holder.clamp_fastener_clearance_diameter_mm
    screw_positions = (-boss_offset_mm, boss_offset_mm)
    for coordinate_mm in screw_positions:
        x_mm = coordinate_mm if screws_along_local_x else 0.0
        y_mm = 0.0 if screws_along_local_x else coordinate_mm
        boss = Part.makeCylinder(
            boss_radius_mm,
            holder.nest_axial_depth_mm,
            App.Vector(x_mm, y_mm, nest_start_z_mm),
        )
        hole = Part.makeCylinder(
            screw_radius_mm,
            holder.nest_axial_depth_mm + 0.4,
            App.Vector(x_mm, y_mm, nest_start_z_mm - 0.2),
        )
        cradle = cradle.fuse(boss).cut(hole)

    flat_depth_mm = head.anti_rotation_flat_depth_mm
    flat_land = Part.makeBox(
        flat_depth_mm,
        2.0
        * (
            (0.5 * head.mounting_flange_diameter_mm) ** 2
            - (
                0.5 * head.mounting_flange_diameter_mm
                - flat_depth_mm
            )
            ** 2
        )
        ** 0.5,
        head.rear_cap_wall_mm,
        App.Vector(
            0.5 * head.mounting_flange_diameter_mm - flat_depth_mm,
            -(
                (0.5 * head.mounting_flange_diameter_mm) ** 2
                - (
                    0.5 * head.mounting_flange_diameter_mm
                    - flat_depth_mm
                )
                ** 2
            )
            ** 0.5,
            rear_z_mm - head.rear_cap_wall_mm,
        ),
    )
    cradle = cradle.fuse(flat_land)

    clamp_width_mm = 2.0 * (
        boss_offset_mm + boss_radius_mm
        if screws_along_local_x
        else boss_radius_mm
    )
    clamp_height_mm = 2.0 * (
        boss_radius_mm
        if screws_along_local_x
        else boss_offset_mm + boss_radius_mm
    )
    clamp = Part.makeBox(
        clamp_width_mm,
        clamp_height_mm,
        holder.clamp_bridge_thickness_mm,
        App.Vector(
            -0.5 * clamp_width_mm,
            -0.5 * clamp_height_mm,
            rear_z_mm,
        ),
    )
    cable_hole = Part.makeCylinder(
        0.5 * head.cable_exit_diameter_mm + 1.0,
        holder.clamp_bridge_thickness_mm + 0.4,
        App.Vector(0.0, 0.0, rear_z_mm - 0.2),
    )
    clamp = clamp.cut(cable_hole)
    fasteners: list[Part.Shape] = []
    for coordinate_mm in screw_positions:
        x_mm = coordinate_mm if screws_along_local_x else 0.0
        y_mm = 0.0 if screws_along_local_x else coordinate_mm
        hole = Part.makeCylinder(
            screw_radius_mm,
            holder.clamp_bridge_thickness_mm + 0.4,
            App.Vector(x_mm, y_mm, rear_z_mm - 0.2),
        )
        clamp = clamp.cut(hole)
        fasteners.append(
            Part.makeCylinder(
                0.5 * 3.0,
                (
                    holder.clamp_bridge_thickness_mm
                    + head.rear_cap_wall_mm
                    + holder.nest_axial_depth_mm
                ),
                App.Vector(
                    x_mm,
                    y_mm,
                    rear_z_mm + holder.clamp_bridge_thickness_mm,
                ),
                App.Vector(0.0, 0.0, -1.0),
            )
        )
    return cradle, clamp, (fasteners[0], fasteners[1])


def _interface_features(
    cfg: CIVConfig,
    sector: str,
    interface_center: App.Vector,
) -> tuple[
    Part.Shape,
    Part.Shape,
    dict[str, Part.Shape],
    dict[str, Part.Shape],
]:
    holder = cfg.compact_one.sector_holder
    outward = _sector_outward(sector)
    tangent = _sector_tangent(sector)
    radial_depth_mm, tangent_width_mm, height_mm = holder.interface_block_mm
    block = _oriented_interface_block(
        interface_center,
        outward,
        tangent,
        radial_depth_mm,
        tangent_width_mm,
        height_mm,
    )
    bore_start = (
        interface_center
        - scaled(outward, 0.5 * radial_depth_mm + 0.2)
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

    plane_center = interface_center + scaled(outward, 0.5 * radial_depth_mm)
    plane = _oriented_interface_block(
        plane_center,
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
        f"{sector}_PrimaryPlaneDatum": plane.copy(),
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
    return block, plane, purchased, datums


def _sector_removal_poses(
    physical: dict[str, Part.Shape],
    sector: str,
    clearance_mm: float,
) -> tuple[Part.Shape, ...]:
    compound = Part.makeCompound(list(physical.values()))
    sample_count = 4
    samples: list[Part.Shape] = []
    for index in range(sample_count + 1):
        distance_mm = clearance_mm * float(index) / float(sample_count)
        sample = compound.copy()
        sample.translate(scaled(_sector_outward(sector), distance_mm))
        samples.append(sample)
    # [EN] Five exact solid poses audit the straight radial extraction without the false corner occupancy of a swept axis-aligned bounding box; the motion is purely translational between poses. / [CN] 五个精确实体姿态用于检查直线径向抽出，避免轴对齐扫掠包围盒造成虚假角部占位；姿态之间为纯平移运动。
    return tuple(samples)


def _sector_removal_envelope(
    poses: tuple[Part.Shape, ...],
) -> Part.Shape:
    boxes = []
    for pose in poses:
        bounds = pose.BoundBox
        boxes.append(
            Part.makeBox(
                bounds.XLength,
                bounds.YLength,
                bounds.ZLength,
                App.Vector(bounds.XMin, bounds.YMin, bounds.ZMin),
            )
        )
    # [EN] Lightweight pose boxes are a display-only diagnostic; collision validation uses the exact sampled holder solids retained separately. / [CN] 轻量姿态盒仅用于显示诊断；碰撞验证使用单独保留的精确采样载架实体。
    return Part.makeCompound(boxes)


def build_sector_holder(
    cfg: CIVConfig,
    sector: str,
) -> SectorHolderGeometry:
    if cfg.compact_one is None:
        raise ValueError("sector holder requires a CompactOne schema-v3 configuration")
    if sector not in cfg.sectors:
        raise ValueError(f"sector {sector!r} is not configured")
    holder = cfg.compact_one.sector_holder
    detector = cfg.compact_one.detector
    routing = cfg.compact_one.services.routing
    placements = tuple(
        placement
        for placement in build_detector_placements(cfg)
        if placement.sector_name == sector
    )
    if tuple(placement.channel_name for placement in placements) != holder.detector_mounts:
        raise ValueError("sector holder detector nests do not match configured channel order")

    physical: dict[str, Part.Shape] = {}
    purchased_interfaces: dict[str, Part.Shape] = {}
    interfaces: dict[str, Part.Shape] = {}
    keepouts: dict[str, Part.Shape] = {}
    datums: dict[str, Part.Shape] = {}
    materials: dict[str, str] = {}
    thermal_connections: list[tuple[str, str]] = []
    holder_physical_names: list[str] = []
    route_starts: dict[str, App.Vector] = {}
    node_centers: list[App.Vector] = []

    stop_offset_mm = (
        detector.rear_housing_offset_mm - detector.head.rear_cap_wall_mm
    )
    for placement in placements:
        head_geometry: DetectorHeadGeometry = build_detector_head(cfg, placement)
        prefix = placement.tag
        for name, shape in head_geometry.physical.items():
            key = f"{prefix}_{name}"
            physical[key] = shape
            materials[key] = head_geometry.materials.get(name, "unresolved")
        for name, shape in head_geometry.interfaces.items():
            interfaces[f"{prefix}_{name}"] = shape
        for name, shape in head_geometry.keepouts.items():
            keepouts[f"{prefix}_{name}"] = shape
        for name, shape in head_geometry.datums.items():
            datums[f"{prefix}_{name}"] = shape
        thermal_connections.extend(
            (f"{prefix}_{name_a}", f"{prefix}_{name_b}")
            for name_a, name_b in head_geometry.thermal_connections
        )
        route_starts[prefix] = detector_connector_segment(cfg, placement)[1]
        node_centers.append(
            cassette_axis_position(
                placement,
                stop_offset_mm - 0.5 * holder.nest_axial_depth_mm,
            )
        )

    outward = _sector_outward(sector)
    tangent = _sector_tangent(sector)
    plate_parts: list[Part.Shape] = [
        Part.makeCylinder(
            holder.carrier_node_radius_mm,
            holder.carrier_plate_thickness_mm,
            center - scaled(tangent, 0.5 * holder.carrier_plate_thickness_mm),
            tangent,
        )
        for center in node_centers
    ]
    for start, end in (
        (node_centers[0], node_centers[1]),
        (node_centers[1], node_centers[2]),
        (node_centers[2], node_centers[0]),
    ):
        plate_parts.append(
            _web_between(
                start,
                end,
                tangent,
                holder.carrier_web_width_mm,
                holder.carrier_plate_thickness_mm,
            )
        )

    transverse_half_size_mm = (
        0.5
        * (
            cfg.vessel.inner_size_x_mm
            if sector in {"left", "right"}
            else cfg.vessel.inner_size_y_mm
        )
    )
    interface_center = (
        scaled(outward, transverse_half_size_mm - routing.wall_clearance_mm)
        + App.Vector(
            0.0,
            0.0,
            sum(point.z for point in node_centers) / len(node_centers),
        )
    )
    outer_node = max(
        node_centers,
        key=lambda point: point.dot(outward),
    )
    plate_parts.append(
        _web_between(
            outer_node,
            interface_center,
            tangent,
            holder.common_bracket_width_mm,
            holder.carrier_plate_thickness_mm,
        )
    )
    carrier_plate = plate_parts[0]
    for part in plate_parts[1:]:
        carrier_plate = carrier_plate.fuse(part)

    # [EN] Machine the detector withdrawal bores and expanded acceptance windows into the one-piece plate; this keeps the carrier coherent without placing material in any full-disc particle cone. / [CN] 在整体载板上加工探测器抽出孔和扩张后的接收窗；既保持载板连贯，又避免材料进入任何完整灵敏圆面的粒子锥。
    for placement in placements:
        carrier_plate = carrier_plate.cut(
            keepouts[f"{placement.tag}_DetectorRemovalEnvelope"]
        )
        carrier_plate = carrier_plate.cut(
            build_active_acceptance_cone(
                cfg,
                placement,
                radial_clearance_mm=holder.acceptance_clearance_mm,
                extend_past_active_mm=(
                    detector.physical_depth_mm
                    + holder.nest_axial_depth_mm
                    + holder.acceptance_clearance_mm
                ),
            )
        )

    plate_name = f"{sector}_SectorCarrierPlate"
    physical[plate_name] = carrier_plate
    materials[plate_name] = "aluminum_6061_provisional"
    holder_physical_names.append(plate_name)

    for placement in placements:
        local_cradle, local_clamp, local_fasteners = _local_nest_shapes(
            cfg,
            screws_along_local_x=sector in {"up", "down"},
        )
        prefix = placement.tag
        cradle_name = f"{prefix}_DetectorNestCradle"
        clamp_name = f"{prefix}_RemovableClampBridge"
        physical[cradle_name] = _placed_local_shape(local_cradle, placement)
        physical[clamp_name] = _placed_local_shape(local_clamp, placement)
        materials[cradle_name] = "aluminum_6061_provisional"
        materials[clamp_name] = "aluminum_6061_provisional"
        holder_physical_names.extend((cradle_name, clamp_name))
        for index, fastener in enumerate(local_fasteners, start=1):
            fastener_name = f"{prefix}_M3ClampFastenerEnvelope_{index}"
            purchased_interfaces[fastener_name] = _placed_local_shape(
                fastener,
                placement,
            )
        thermal_connections.extend(
            (
                (f"{prefix}_RearMountingFace", cradle_name),
                (cradle_name, plate_name),
            )
        )

    interface_block, mount_plane, purchased, interface_datums = _interface_features(
        cfg,
        sector,
        interface_center,
    )
    block_name = f"{sector}_SectorInterfaceBlock"
    interface_name = f"{sector}_ChamberMountInterface"
    physical[block_name] = interface_block
    materials[block_name] = "aluminum_6061_provisional"
    holder_physical_names.append(block_name)
    interfaces[interface_name] = mount_plane
    purchased_interfaces.update(purchased)
    datums.update(interface_datums)
    thermal_connections.extend(
        (
            (plate_name, block_name),
            (block_name, interface_name),
        )
    )

    # [EN] Every nest and clamp is machined against all three complete-disc acceptance windows in its sector, so nearby channels cannot be shadowed by a generous raw stock profile. / [CN] 每个巢座和压桥均按本扇区三个完整灵敏圆面接收窗加工避让，避免宽裕毛坯轮廓遮挡相邻通道。
    expanded_acceptance = [
        build_active_acceptance_cone(
            cfg,
            placement,
            radial_clearance_mm=holder.acceptance_clearance_mm,
            extend_past_active_mm=(
                detector.physical_depth_mm
                + holder.nest_axial_depth_mm
                + holder.acceptance_clearance_mm
            ),
        )
        for placement in placements
    ]
    for name in holder_physical_names:
        shape = physical[name]
        for window in expanded_acceptance:
            shape = shape.cut(window)
        physical[name] = shape

    service_junction = (
        interface_center
        - scaled(outward, 0.5 * holder.interface_block_mm[0] + 6.0)
        + scaled(tangent, holder.service_lane_offset_mm)
    )
    cable_radius_mm = 0.5 * routing.cable_keepout_diameter_mm
    for index, placement in enumerate(placements):
        start = route_starts[placement.tag]
        tangent_offset = scaled(
            tangent,
            (float(index) - 1.0) * routing.cable_keepout_diameter_mm,
        )
        lane_anchor = (
            service_junction
            + tangent_offset
            + App.Vector(0.0, 0.0, start.z - service_junction.z)
        )
        route = Part.makeCompound(
            [
                _segment_keepout(start, lane_anchor, cable_radius_mm),
                _segment_keepout(
                    lane_anchor,
                    service_junction + tangent_offset,
                    cable_radius_mm,
                ),
                Part.makeSphere(cable_radius_mm, lane_anchor),
            ]
        )
        keepouts[f"{placement.tag}_SectorCableRoute"] = route

    lane_bottom = service_junction - App.Vector(
        0.0,
        0.0,
        0.5 * cfg.vessel.length_mm,
    )
    lane_top = service_junction + App.Vector(
        0.0,
        0.0,
        0.5 * cfg.vessel.length_mm,
    )
    rear_cable_lane = _segment_keepout(
        lane_bottom,
        lane_top,
        (
            cable_radius_mm
            + 2.5
            + holder.acceptance_clearance_mm
        ),
    )
    keepouts[f"{sector}_RearCableLane"] = rear_cable_lane
    # [EN] A common rear lane is cut through the carrier at the service junction; twelve independent rails are not recreated as cable supports. / [CN] 在服务汇合点为公共后部走线槽加工载板避让；不会以电缆支撑之名重新生成十二根独立导轨。
    for name in holder_physical_names:
        physical[name] = physical[name].cut(rear_cable_lane)

    removal_poses = _sector_removal_poses(
        {
            name: shape
            for name, shape in physical.items()
            if name in holder_physical_names
        },
        sector,
        holder.sector_removal_clearance_mm,
    )
    keepouts[f"{sector}_SectorRemovalEnvelope"] = _sector_removal_envelope(
        removal_poses
    )
    keepouts[f"{sector}_ToolAccessEnvelope"] = Part.makeCylinder(
        0.5 * holder.interface_block_mm[1],
        holder.tool_clearance_mm,
        interface_center + scaled(outward, 0.5 * holder.interface_block_mm[0]),
        outward,
    )
    return SectorHolderGeometry(
        sector=sector,
        placements=placements,
        service_junction=service_junction,
        physical=physical,
        purchased_interfaces=purchased_interfaces,
        interfaces=interfaces,
        keepouts=keepouts,
        datums=datums,
        materials=materials,
        thermal_connections=tuple(thermal_connections),
        holder_physical_names=tuple(holder_physical_names),
        removal_poses=removal_poses,
    )


def sector_holder_compound(geometry: SectorHolderGeometry) -> Part.Shape:
    return Part.makeCompound(list(geometry.physical.values()))
