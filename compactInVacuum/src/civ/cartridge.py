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
from .support import build_sector_mount


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
    stationary_physical_names: tuple[str, ...]
    stationary_purchased_interface_names: tuple[str, ...]
    loaded_maintenance_bounds_mm: tuple[float, float, float, float, float, float]
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


def _physical_solids_only(shape: Part.Shape) -> Part.Shape:
    solids = [solid.copy() for solid in shape.Solids]
    if not solids:
        return shape
    if len(solids) == 1:
        return solids[0]
    # [EN] Boolean cuts against ruled acceptance lofts can retain non-solid cutter residue in an OCC compound; manufactured geometry and its bounds must contain solids only. / [CN] OCC 对规则接收放样体做布尔切除时可能在复合体中残留非实体刀具；制造几何及其边界必须只包含实体。
    return Part.makeCompound(solids)


def _sector_outward(sector: str) -> App.Vector:
    return {
        "left": App.Vector(-1.0, 0.0, 0.0),
        "right": App.Vector(1.0, 0.0, 0.0),
        "up": App.Vector(0.0, 1.0, 0.0),
        "down": App.Vector(0.0, -1.0, 0.0),
    }[sector]


def _aggregate_bounds_mm(
    shapes: tuple[Part.Shape, ...] | list[Part.Shape],
) -> tuple[float, float, float, float, float, float]:
    if not shapes:
        raise ValueError("loaded sector maintenance envelope requires physical shapes")
    return (
        min(float(shape.BoundBox.XMin) for shape in shapes),
        max(float(shape.BoundBox.XMax) for shape in shapes),
        min(float(shape.BoundBox.YMin) for shape in shapes),
        max(float(shape.BoundBox.YMax) for shape in shapes),
        min(float(shape.BoundBox.ZMin) for shape in shapes),
        max(float(shape.BoundBox.ZMax) for shape in shapes),
    )


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


def _sector_removal_poses(
    physical: dict[str, Part.Shape],
    release_direction: App.Vector,
    clearance_mm: float,
) -> tuple[Part.Shape, ...]:
    sample_count = 4
    samples: list[Part.Shape] = []
    for index in range(sample_count + 1):
        distance_mm = clearance_mm * float(index) / float(sample_count)
        offset = scaled(release_direction, distance_mm)
        placed_components: list[Part.Shape] = []
        for shape in physical.values():
            placed = shape.copy()
            placed.Placement = App.Placement(
                offset,
                App.Rotation(),
            ).multiply(shape.Placement)
            placed_components.append(placed)
        samples.append(Part.makeCompound(placed_components))
    # [EN] Rebuilding every pose from independent component copies prevents OpenCASCADE compound placement from mutating the source holder; the first motion disengages the fixed-wall locating interface inward before any top-port reorientation. / [CN] 每个姿态都由独立零件副本重建，避免 OpenCASCADE 复合体位姿反向修改源支架；第一阶段先向内脱离固定壁定位接口，再进行顶口转向。
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
    stationary_physical_names: list[str] = []
    stationary_purchased_interface_names: list[str] = []
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
    mount = cfg.compact_one.deployment.sector_mount(sector)
    mount_geometry = build_sector_mount(
        cfg,
        sector,
        sum(point.z for point in node_centers) / len(node_centers),
    )
    mount_outward = mount_geometry.outward
    mount_tangent = mount_geometry.tangent
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

    interface_center = mount_geometry.interface_center
    outer_node = max(
        node_centers,
        key=lambda point: point.dot(outward),
    )
    plate_parts.append(
        _web_between(
            outer_node,
            interface_center,
            (
                tangent
                if (mount_outward - outward).Length <= 1.0e-9
                else App.Vector(0.0, 0.0, 1.0)
            ),
            holder.common_bracket_width_mm,
            holder.carrier_plate_thickness_mm,
        )
    )
    carrier_plate = plate_parts[0]
    for part in plate_parts[1:]:
        carrier_plate = carrier_plate.fuse(part)
    carrier_plate_maintenance_envelope = carrier_plate.copy()

    # [EN] Machine the detector withdrawal bores and expanded acceptance windows into the one-piece plate; this keeps the carrier coherent without placing material in any full-disc particle cone. / [CN] 在整体载板上加工探测器抽出孔和扩张后的接收窗；既保持载板连贯，又避免材料进入任何完整灵敏圆面的粒子锥。
    for placement in placements:
        removal_envelope = keepouts[f"{placement.tag}_DetectorRemovalEnvelope"]
        if carrier_plate.distToShape(removal_envelope)[0] <= 1.0e-7:
            carrier_plate = _physical_solids_only(
                carrier_plate.cut(removal_envelope)
            )
        acceptance_window = build_active_acceptance_cone(
            cfg,
            placement,
            radial_clearance_mm=holder.acceptance_clearance_mm,
            extend_past_active_mm=(
                detector.physical_depth_mm
                + holder.nest_axial_depth_mm
                + holder.acceptance_clearance_mm
            ),
        )
        if carrier_plate.distToShape(acceptance_window)[0] <= 1.0e-7:
            carrier_plate = _physical_solids_only(
                carrier_plate.cut(acceptance_window)
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

    interface_block = mount_geometry.interface_block
    holder_dock_plane = mount_geometry.holder_dock_plane
    stationary_support = mount_geometry.stationary_support
    chamber_mount_plane = mount_geometry.chamber_mount_plane
    purchased = mount_geometry.stationary_purchased_interfaces
    interface_datums = mount_geometry.datums
    block_name = f"{sector}_SectorInterfaceBlock"
    dock_name = f"{sector}_HolderDockInterface"
    support_name = f"{sector}_PermanentWallSupport"
    interface_name = f"{sector}_ChamberMountInterface"
    physical[block_name] = interface_block
    physical[support_name] = stationary_support
    materials[block_name] = "aluminum_6061_provisional"
    materials[support_name] = "stainless_304L"
    holder_physical_names.append(block_name)
    stationary_physical_names.append(support_name)
    interfaces[dock_name] = holder_dock_plane
    interfaces[interface_name] = chamber_mount_plane
    purchased_interfaces.update(purchased)
    stationary_purchased_interface_names.extend(purchased)
    datums.update(interface_datums)
    thermal_connections.extend(
        (
            (plate_name, block_name),
            (block_name, dock_name),
            (dock_name, support_name),
            (support_name, interface_name),
        )
    )

    # [EN] Capture the complete loaded holder before acceptance-window Booleans; subtraction can only reduce this conservative envelope, and the metadata remains stable across OCC residual-edge behavior. / [CN] 在接收窗布尔切除前记录装载完整探测器的支架包络；减法只会缩小这一保守包络，且该元数据不受 OCC 残余边行为影响。
    loaded_maintenance_bounds_mm = _aggregate_bounds_mm(
        [
            *(
                shape
                for name, shape in physical.items()
                if name != plate_name and name not in stationary_physical_names
            ),
            carrier_plate_maintenance_envelope,
            *(
                shape
                for name, shape in purchased_interfaces.items()
                if name not in stationary_purchased_interface_names
            ),
        ]
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
            if shape.distToShape(window)[0] <= 1.0e-7:
                shape = _physical_solids_only(shape.cut(window))
        physical[name] = shape

    service_junction = (
        interface_center
        - scaled(mount_outward, 0.5 * holder.interface_block_mm[0] + 6.0)
        + scaled(mount_tangent, holder.service_lane_offset_mm)
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
        shape = physical[name]
        if shape.distToShape(rear_cable_lane)[0] <= 1.0e-7:
            physical[name] = _physical_solids_only(shape.cut(rear_cable_lane))
        # [EN] A disjoint Boolean cut is skipped because some FreeCAD/OpenCASCADE builds return a compound carrying the cutter envelope, corrupting the part bounds used for access sizing. / [CN] 对不相交实体跳过布尔切除，因为部分 FreeCAD/OpenCASCADE 版本会返回携带刀具体包络的复合体，进而污染操作口定尺寸所用的零件边界。

    removal_poses = _sector_removal_poses(
        {
            **{
                name: shape
                for name, shape in physical.items()
                if name not in stationary_physical_names
            },
            **{
                name: shape
                for name, shape in purchased_interfaces.items()
                if name not in stationary_purchased_interface_names
            },
        },
        mount_geometry.release_direction,
        mount.release_clearance_mm,
    )
    keepouts[f"{sector}_SectorRemovalEnvelope"] = _sector_removal_envelope(
        removal_poses
    )
    keepouts[f"{sector}_ToolAccessEnvelope"] = Part.makeCylinder(
        0.5 * holder.interface_block_mm[1],
        holder.tool_clearance_mm,
        interface_center - scaled(
            mount_outward,
            0.5 * holder.interface_block_mm[0],
        ),
        scaled(mount_outward, -1.0),
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
        stationary_physical_names=tuple(stationary_physical_names),
        stationary_purchased_interface_names=tuple(
            stationary_purchased_interface_names
        ),
        loaded_maintenance_bounds_mm=loaded_maintenance_bounds_mm,
        removal_poses=removal_poses,
    )


def sector_holder_compound(geometry: SectorHolderGeometry) -> Part.Shape:
    return Part.makeCompound(list(geometry.physical.values()))
