from __future__ import annotations

from dataclasses import dataclass
import math

import FreeCAD as App
import Part

from ..cassette import build_detector_head, detector_connector_segment
from ..cartridge import _local_nest_shapes, _placed_local_shape, _physical_solids_only
from ..chamber import build_chamber
from ..feedthrough import build_feedthrough_port
from ..detector import build_active_acceptance_cone
from ..target import build_target_system
from ..layout import (
    build_detector_placements,
    detector_center,
    normalize,
    placement_from_direction,
    scaled,
)
from .config import BoxSpec

V = App.Vector


def moved(shape, delta=V(), angle=0.0, pivot=V()):
    result = shape.copy()
    if angle:
        result.rotate(pivot, V(0, 0, 1), angle)
    if delta.Length:
        result.translate(delta)
    return result


def fused(shapes):
    shapes = list(shapes)
    return shapes[0].multiFuse(shapes[1:]) if len(shapes) > 1 else shapes[0]


def tube(start, end, radius):
    delta = end - start
    return Part.makeCylinder(radius, delta.Length, start, delta)


def rect_xz(x, z, width, height, radius, y, thickness):
    pieces = [
        Part.makeBox(width - 2 * radius, thickness, height, V(x + radius, y, z)),
        Part.makeBox(width, thickness, height - 2 * radius, V(x, y, z + radius)),
    ]
    pieces.extend(
        Part.makeCylinder(radius, thickness, V(a, y, b), V(0, 1, 0))
        for a in (x + radius, x + width - radius)
        for b in (z + radius, z + height - radius)
    )
    return fused(pieces).removeSplitter()


def rounded_cable(points, radius, bend_radius):
    points = list(points)
    corners = []
    for a, p, b in zip(points, points[1:], points[2:]):
        incoming, outgoing = normalize(p - a), normalize(b - p)
        angle = math.acos(max(-1.0, min(1.0, incoming.dot(outgoing))))
        if angle < 1e-8:
            corners.append((p, None, p, 0.0))
            continue
        setback = bend_radius * math.tan(angle / 2)
        start, end = p - scaled(incoming, setback), p + scaled(outgoing, setback)
        center = p + scaled(
            normalize(outgoing - incoming), bend_radius / math.cos(angle / 2)
        )
        mid = center + scaled(normalize(start + end - scaled(center, 2)), bend_radius)
        corners.append((start, mid, end, setback))
    setbacks = [0.0, *(c[3] for c in corners), 0.0]
    for index, (a, b) in enumerate(zip(points, points[1:])):
        if setbacks[index] + setbacks[index + 1] > (b - a).Length + 1e-6:
            raise ValueError(
                f"cable segment {index} cannot fit its specified bend radius"
            )
    edges, last = [], points[0]
    for start, mid, end, _ in corners:
        if (start - last).Length > 1e-7:
            edges.append(Part.makeLine(last, start))
        if mid is not None:
            edges.append(Part.Arc(start, mid, end).toShape())
        last = end
    if (points[-1] - last).Length > 1e-7:
        edges.append(Part.makeLine(last, points[-1]))
    path = Part.Wire(edges)
    profile = Part.Wire(
        Part.makeCircle(radius, points[0], normalize(points[1] - points[0]))
    )
    solid = path.makePipeShell([profile], True, False)
    if not solid.isValid() or len(solid.Solids) != 1:
        raise ValueError("pigtail sweep did not produce one valid solid")
    return solid, path


@dataclass
class StudyGeometry:
    actor: dict
    actor_materials: dict
    structural: tuple[str, ...]
    heads: dict
    head_parts: dict
    removal: dict
    purchased: set[str]
    fixed: dict
    fixed_regions: dict
    neighbors: dict
    other_heads: dict
    chamber: object
    target: object
    ports: dict
    plugs: dict
    ground: dict
    parked_looms: dict
    tool: dict
    draw_screw: dict
    screwdriver: object
    cable_paths: dict
    grip: object
    screw_point: object
    screw_axis: object
    pin_sweeps: dict


def build_geometry(cfg, s: BoxSpec) -> StudyGeometry:
    placements = build_detector_placements(cfg)
    selected = [p for p in placements if p.sector_name == s.sector]
    actor, head_parts, heads, removal, paths = {}, {}, {}, {}, {}
    actor_materials = {}
    purchased, structural = set(), []

    def structure(name, shape):
        actor[name] = _physical_solids_only(shape)
        structural.append(name)

    cheek = rect_xz(
        s.carrier_r_min_mm,
        s.carrier_z_min_mm,
        s.carrier_r_max_mm - s.carrier_r_min_mm,
        s.carrier_z_max_mm - s.carrier_z_min_mm,
        s.cheek_corner_radius_mm,
        s.cheek_inner_half_width_mm,
        s.cheek_thickness_mm,
    )
    for x, z, w, h, r in s.cheek_windows_mm:
        cheek = cheek.cut(
            rect_xz(x, z, w, h, r, -s.half_width - 1, 2 * s.half_width + 2)
        )
    grip = V(*s.grip_center_mm)
    relief_start = s.grip_fork_anchor_r_mm + s.grip_fork_half_width_mm
    relief = Part.makeBox(
        s.carrier_r_max_mm - relief_start + 2,
        2 * s.half_width + 2,
        2 * s.grip_relief_z_half_span_mm,
        V(relief_start, -s.half_width - 1, grip.z - s.grip_relief_z_half_span_mm),
    )
    cheek = cheek.cut(relief)
    structure("CarrierCheekPositive", cheek)
    structure(
        "CarrierCheekNegative",
        moved(cheek, V(0, -2 * s.cheek_inner_half_width_mm - s.cheek_thickness_mm, 0)),
    )
    x, z, w, h = s.front_brace_mm
    structure(
        "CarrierFrontCrossmember",
        Part.makeBox(
            w, 2 * s.cheek_inner_half_width_mm, h, V(x, -s.cheek_inner_half_width_mm, z)
        ),
    )
    structure(
        "CarrierRearCrossmember",
        Part.makeBox(
            s.carrier_r_max_mm - s.carrier_r_min_mm,
            2 * s.cheek_inner_half_width_mm,
            s.rear_bridge_depth_mm,
            V(
                s.carrier_r_min_mm,
                -s.cheek_inner_half_width_mm,
                s.carrier_z_max_mm - s.rear_bridge_depth_mm,
            ),
        ),
    )
    structure(
        "CarrierDockFoot",
        Part.makeBox(
            s.dock_depth_mm,
            2 * s.cheek_inner_half_width_mm,
            s.dock_z_max_mm - s.dock_z_min_mm,
            V(
                s.dock_plane_r_mm - s.dock_depth_mm,
                -s.cheek_inner_half_width_mm,
                s.dock_z_min_mm,
            ),
        ),
    )

    # [EN] The grip fork joins the inner cheek rim; its outer quadrant remains open for the vertical handling rod during a 90-degree turn. / [CN] 抓取叉连接内侧颊板边框，并为竖直操作杆在九十度转向中的相对扫掠留出外侧象限。
    half_pin = s.grip_pin_length_mm / 2
    for label, zbase in [
        ("Front", grip.z - half_pin - s.grip_fork_plate_depth_mm),
        ("Rear", grip.z + half_pin),
    ]:
        structure(
            f"GripFork{label}",
            Part.makeBox(
                grip.x + s.grip_fork_half_width_mm - s.grip_fork_anchor_r_mm,
                2 * s.cheek_inner_half_width_mm,
                s.grip_fork_plate_depth_mm,
                V(s.grip_fork_anchor_r_mm, -s.cheek_inner_half_width_mm, zbase),
            ),
        )
    structure(
        "GripTrunnion",
        Part.makeCylinder(
            s.grip_pin_radius_mm, s.grip_pin_length_mm, grip - V(0, 0, half_pin)
        ),
    )

    old_cradle, _, _ = _local_nest_shapes(cfg, False)
    detector = cfg.compact_one.detector
    holder = cfg.compact_one.sector_holder
    rear = detector.rear_housing_offset_mm
    stop = rear - detector.head.rear_cap_wall_mm
    nest_start = stop - holder.nest_axial_depth_mm
    nest_outer = (
        detector.housing_outer_diameter_mm / 2
        + holder.nest_clearance_mm
        + holder.nest_radial_wall_mm
    )
    local_cradle = old_cradle.common(
        Part.makeCylinder(nest_outer, rear - nest_start, V(0, 0, nest_start))
    )
    for sign in (-1, 1):
        local_cradle = local_cradle.fuse(
            Part.makeCylinder(
                s.nest_boss_radius_mm,
                holder.nest_axial_depth_mm,
                V(0, sign * s.nest_boss_tangent_mm, nest_start),
            )
        )
        y = 11.0 if sign > 0 else -s.cheek_inner_half_width_mm
        local_cradle = local_cradle.fuse(
            Part.makeBox(
                6.0,
                s.cheek_inner_half_width_mm - 11,
                holder.nest_axial_depth_mm,
                V(s.side_attachment_local_x_mm - 3, y, nest_start),
            )
        )
        local_cradle = local_cradle.cut(
            Part.makeCylinder(
                holder.clamp_fastener_clearance_diameter_mm / 2,
                rear - nest_start + 1,
                V(0, sign * s.nest_boss_tangent_mm, nest_start - 0.2),
            )
        )
    clamp_half_t = min(
        s.cheek_inner_half_width_mm - 0.2,
        s.nest_boss_tangent_mm + s.nest_boss_radius_mm - 0.2,
    )
    local_clamp = Part.makeBox(
        s.clamp_width_local_x_mm,
        2 * clamp_half_t,
        holder.clamp_bridge_thickness_mm,
        V(-s.clamp_width_local_x_mm / 2, -clamp_half_t, rear),
    )
    local_clamp = local_clamp.cut(
        Part.makeCylinder(
            detector.head.cable_exit_diameter_mm / 2 + 1,
            holder.clamp_bridge_thickness_mm + 0.4,
            V(0, 0, rear - 0.2),
        )
    )
    for sign in (-1, 1):
        local_clamp = local_clamp.cut(
            Part.makeCylinder(
                holder.clamp_fastener_clearance_diameter_mm / 2,
                holder.clamp_bridge_thickness_mm + 0.4,
                V(0, sign * s.nest_boss_tangent_mm, rear - 0.2),
            )
        )

    attachment_centers = []
    for index, placement in enumerate(selected):
        head = build_detector_head(cfg, placement)
        prefix = placement.tag
        head_parts[prefix] = {}
        for name, shape in head.physical.items():
            key = f"{prefix}_{name}"
            actor[key] = shape
            actor_materials[key] = head.materials.get(name, "unresolved")
            head_parts[prefix][key] = shape
        heads[prefix] = Part.makeCompound(list(head.physical.values()))
        removal[prefix] = head.keepouts["DetectorRemovalEnvelope"]
        structure(
            f"{prefix}_DetectorNestCradle", _placed_local_shape(local_cradle, placement)
        )
        actor[f"{prefix}_RemovableClampBridge"] = _placed_local_shape(
            local_clamp, placement
        )
        for sign in (-1, 1):
            point = V(
                0,
                sign * s.nest_boss_tangent_mm,
                rear + holder.clamp_bridge_thickness_mm,
            )
            shaft = Part.makeCylinder(
                1.5,
                holder.clamp_bridge_thickness_mm
                + detector.head.rear_cap_wall_mm
                + holder.nest_axial_depth_mm,
                point,
                V(0, 0, -1),
            )
            bolt = shaft.fuse(Part.makeCylinder(2.3, 2.0, point))
            key = f"{prefix}_M3ClampScrew_{sign}"
            actor[key] = _placed_local_shape(bolt, placement)
            purchased.add(key)
        transform = placement_from_direction(
            detector_center(placement), placement.direction
        )
        point = transform.multVec(
            V(
                s.side_attachment_local_x_mm,
                0,
                nest_start + holder.nest_axial_depth_mm / 2,
            )
        )
        attachment_centers.append((f"{prefix}_SideAttachment", point.x, point.z))

        cable_start = detector_connector_segment(cfg, placement)[0]
        bend = s.cable_bend_radius_mm
        first_corner = cable_start + scaled(placement.direction, bend)
        lane_y = s.cable_lane_y_mm[index]
        second_corner = first_corner + V(0, lane_y, 0)
        destination_z = s.connector_z_mm[index]
        route = [cable_start, first_corner, second_corner]
        if abs(destination_z - first_corner.z) >= 2 * bend:
            turn_r = s.cable_turn_r_mm[index]
            if first_corner.x > s.connector_r_mm:
                route.extend(
                    [
                        V(first_corner.x, lane_y, s.large_angle_cable_turn_z_mm),
                        V(turn_r, lane_y, s.large_angle_cable_turn_z_mm),
                    ]
                )
            else:
                route.append(V(turn_r, lane_y, first_corner.z))
            route.append(V(turn_r, lane_y, destination_z))
            if lane_y != 2 * bend:
                route.append(V(s.cable_lane_merge_r_mm[index], 2 * bend, destination_z))
        route.extend(
            [
                V(s.connector_r_mm, 2 * bend, destination_z),
                V(s.connector_r_mm, 3 * bend, destination_z),
            ]
        )
        cable, path = rounded_cable(route, s.cable_radius_mm, bend)
        actor[f"{prefix}_PassiveCoax"] = cable
        paths[f"{prefix}_PassiveCoaxPath"] = path
        connector = Part.makeCylinder(
            s.connector_radius_mm,
            s.connector_body_length_mm,
            V(
                s.connector_r_mm,
                s.half_width - s.connector_body_length_mm,
                destination_z,
            ),
            V(0, 1, 0),
        )
        connector = connector.fuse(
            Part.makeCylinder(
                s.connector_radius_mm + 1,
                1.0,
                V(s.connector_r_mm, s.cheek_inner_half_width_mm - 1, destination_z),
                V(0, 1, 0),
            )
        )
        key = f"{prefix}_PanelCoaxConnectorEnvelope"
        actor[key] = connector
        purchased.add(key)
        connector_cut = Part.makeCylinder(
            s.connector_radius_mm + s.fastener_clearance_mm,
            2 * s.half_width + 2,
            V(s.connector_r_mm, -s.half_width - 1, destination_z),
            V(0, 1, 0),
        )
        actor["CarrierCheekPositive"] = actor["CarrierCheekPositive"].cut(connector_cut)
        actor["CarrierRearCrossmember"] = (
            actor["CarrierRearCrossmember"]
            .cut(connector_cut)
            .cut(
                Part.makeCylinder(
                    s.connector_radius_mm + 1.25,
                    1.2,
                    V(
                        s.connector_r_mm,
                        s.cheek_inner_half_width_mm - 1.1,
                        destination_z,
                    ),
                    V(0, 1, 0),
                )
            )
        )

    # [EN] Rear access slots clear head withdrawal and expose the pigtail groove for machining and assembly. / [CN] 后部开槽为探头抽出留空，并使短同轴线槽可加工和装配。
    for name in structural:
        shape = actor[name]
        for envelope in removal.values():
            if shape.BoundBox.intersect(envelope.BoundBox):
                shape = shape.cut(envelope)
        if name == "CarrierRearCrossmember":
            shape = shape.cut(
                Part.makeBox(
                    s.connector_r_mm - 40 + 4,
                    2 * s.cable_radius_mm + 1,
                    s.rear_bridge_depth_mm + 1,
                    V(
                        40,
                        2 * s.cable_bend_radius_mm - s.cable_radius_mm - 0.5,
                        s.carrier_z_max_mm - s.rear_bridge_depth_mm - 0.5,
                    ),
                )
            )
            shape = shape.cut(
                Part.makeBox(
                    s.cable_bend_radius_mm + 5,
                    s.cable_bend_radius_mm + 2,
                    s.rear_bridge_depth_mm + 1,
                    V(
                        s.connector_r_mm - s.cable_bend_radius_mm - 1,
                        2 * s.cable_bend_radius_mm - 1,
                        s.carrier_z_max_mm - s.rear_bridge_depth_mm - 0.5,
                    ),
                )
            )
        if name.endswith("DetectorNestCradle"):
            for placement in placements:
                cone = build_active_acceptance_cone(
                    cfg, placement, radial_clearance_mm=holder.acceptance_clearance_mm
                )
                if shape.BoundBox.intersect(cone.BoundBox):
                    shape = shape.cut(cone)
        actor[name] = _physical_solids_only(shape)

    attachment_centers += [
        ("FrontBraceAttachment", x + w / 2, z + h / 2),
        (
            "RearBraceAttachment",
            s.rear_bridge_attachment_r_mm,
            s.carrier_z_max_mm - s.rear_bridge_depth_mm / 2,
        ),
    ]
    for label, x0, z0 in attachment_centers:
        for sign in (-1, 1):
            axis = V(0, sign, 0)
            shaft_start = V(x0, sign * 14.0, z0)
            head_start = V(x0, sign * (s.half_width - s.side_bolt_head_depth_mm), z0)
            shaft_hole = Part.makeCylinder(
                s.side_bolt_radius_mm + s.fastener_clearance_mm,
                s.half_width - 14 + 1,
                shaft_start,
                axis,
            )
            head_hole = Part.makeCylinder(
                s.side_bolt_head_radius_mm + 0.1,
                s.side_bolt_head_depth_mm + 0.2,
                head_start,
                axis,
            )
            for name in structural:
                if actor[name].BoundBox.intersect(shaft_hole.BoundBox):
                    actor[name] = _physical_solids_only(
                        actor[name].cut(shaft_hole).cut(head_hole)
                    )
            bolt = Part.makeCylinder(
                s.side_bolt_radius_mm,
                s.half_width - 14 - s.side_bolt_head_depth_mm / 2,
                shaft_start,
                axis,
            ).fuse(
                Part.makeCylinder(
                    s.side_bolt_head_radius_mm,
                    s.side_bolt_head_depth_mm,
                    head_start,
                    axis,
                )
            )
            key = f"{label}_M2Screw_{sign}"
            actor[key] = bolt
            purchased.add(key)

    ring = Part.makeCylinder(
        s.ring_outer_radius_mm, s.ring_depth_mm, V(0, 0, s.ring_front_z_mm)
    ).cut(
        Part.makeCylinder(
            s.ring_inner_radius_mm, s.ring_depth_mm + 2, V(0, 0, s.ring_front_z_mm - 1)
        )
    )
    half_x, half_y = cfg.vessel.inner_size_x_mm / 2, cfg.vessel.inner_size_y_mm / 2
    foot = s.wall_foot_width_mm
    additions = [
        Part.makeBox(
            half_x - s.ring_outer_radius_mm + 2,
            foot,
            s.ring_depth_mm,
            V(s.ring_outer_radius_mm - 2, -foot / 2, s.ring_front_z_mm),
        ),
        Part.makeBox(
            half_x - s.ring_outer_radius_mm + 2,
            foot,
            s.ring_depth_mm,
            V(-half_x, -foot / 2, s.ring_front_z_mm),
        ),
        Part.makeBox(
            foot,
            half_y - s.ring_outer_radius_mm + 2,
            s.ring_depth_mm,
            V(-foot / 2, -half_y, s.ring_front_z_mm),
        ),
    ]
    right_socket = Part.makeBox(
        13,
        2 * s.cheek_inner_half_width_mm,
        s.dock_z_max_mm - s.ring_front_z_mm,
        V(s.dock_plane_r_mm, -s.cheek_inner_half_width_mm, s.ring_front_z_mm),
    )
    ring_web = fused([ring, *additions])
    sockets = {
        f"Socket_{name}": moved(right_socket, angle=a)
        for name, a in [("right", 0), ("up", 90), ("left", 180), ("down", 270)]
    }
    additions += list(sockets.values())
    ring = fused([ring, *additions])
    fixed, pin_sweeps = {}, {}
    for sign in (-1, 1):
        base = V(
            s.dock_plane_r_mm - s.pin_projection_mm,
            sign * s.pin_tangent_spacing_mm / 2,
            s.pin_center_z_mm,
        )
        pin = Part.makeCylinder(
            s.pin_diameter_mm / 2, s.pin_projection_mm + 2, base, V(1, 0, 0)
        )
        fixed[f"DockPin_{sign}"] = pin
        pin_sweeps[f"DockPin_{sign}"] = Part.makeCylinder(
            s.pin_diameter_mm / 2,
            s.pin_projection_mm + 2 + s.radial_release_mm,
            base,
            V(1, 0, 0),
        )
        bore = Part.makeCylinder(
            s.pin_bore_diameter_mm / 2,
            s.pin_projection_mm + s.radial_release_mm + 5,
            base - V(1, 0, 0),
            V(1, 0, 0),
        )
        if sign > 0:
            offset = (s.slot_length_mm - s.pin_bore_diameter_mm) / 2
            bore = fused(
                [
                    moved(bore, V(0, -offset, 0)),
                    moved(bore, V(0, offset, 0)),
                    Part.makeBox(
                        s.pin_projection_mm + s.radial_release_mm + 5,
                        2 * offset,
                        s.pin_bore_diameter_mm,
                        V(
                            base.x - 1,
                            base.y - offset,
                            base.z - s.pin_bore_diameter_mm / 2,
                        ),
                    ),
                ]
            )
        for name in structural:
            if actor[name].BoundBox.intersect(bore.BoundBox):
                actor[name] = _physical_solids_only(actor[name].cut(bore))
    screw_point, screw_axis = V(*s.draw_screw_head_mm), normalize(
        V(*s.draw_screw_access_direction)
    )
    shaft_cut = Part.makeCylinder(
        s.draw_screw_shaft_radius_mm + s.fastener_clearance_mm,
        s.draw_screw_shaft_length_mm + 100,
        screw_point - scaled(screw_axis, s.draw_screw_shaft_length_mm),
        screw_axis,
    )
    counterbore = Part.makeCylinder(
        max(s.draw_screw_head_radius_mm, s.screwdriver_radius_mm)
        + s.fastener_clearance_mm,
        100,
        screw_point,
        screw_axis,
    )
    for name in structural:
        if actor[name].BoundBox.intersect(shaft_cut.BoundBox):
            actor[name] = _physical_solids_only(
                actor[name].cut(shaft_cut).cut(counterbore)
            )
    fixed["AnnularSupportWeldment"] = ring.cut(shaft_cut)
    fixed_regions = {
        "RingWeb": ring_web.cut(shaft_cut),
        **{name: shape.cut(shaft_cut) for name, shape in sockets.items()},
        **{name: shape for name, shape in fixed.items() if name.startswith("DockPin")},
    }
    draw_screw = {
        "DrawScrewShaft": Part.makeCylinder(
            s.draw_screw_shaft_radius_mm,
            s.draw_screw_shaft_length_mm,
            screw_point,
            -screw_axis,
        ),
        "DrawScrewHead": Part.makeCylinder(
            s.draw_screw_head_radius_mm,
            s.draw_screw_head_depth_mm,
            screw_point,
            screw_axis,
        ),
    }
    screwdriver = Part.makeCylinder(
        s.screwdriver_radius_mm,
        s.screwdriver_length_mm,
        screw_point + scaled(screw_axis, s.draw_screw_head_depth_mm),
        screw_axis,
    )

    bearing_center = grip + V(0, s.grip_bearing_clearance_mm, 0)
    outer = Part.makeCylinder(
        s.grip_head_radius_mm,
        s.grip_head_depth_mm,
        bearing_center - V(0, 0, s.grip_head_depth_mm / 2),
    )
    inner = Part.makeCylinder(
        s.grip_pin_radius_mm + s.grip_bearing_clearance_mm,
        s.grip_head_depth_mm + 2,
        bearing_center - V(0, 0, s.grip_head_depth_mm / 2 + 1),
    )
    bearing = outer.cut(inner)
    upper = Part.makeBox(
        2 * s.grip_head_radius_mm + 2,
        s.grip_head_radius_mm + 1,
        s.grip_head_depth_mm + 2,
        bearing_center
        + V(-s.grip_head_radius_mm - 1, 0, -s.grip_head_depth_mm / 2 - 1),
    )
    tool = {
        "CaptureUpperJaw": bearing.common(upper),
        "CaptureLowerJaw": bearing.cut(upper),
        "HandlingRod": Part.makeCylinder(
            s.grip_rod_radius_mm,
            s.grip_rod_length_mm,
            bearing_center + V(0, s.grip_head_radius_mm - 0.5, 0),
            V(0, 1, 0),
        ),
    }
    # [EN] The rod sweeps the outer positive-tangent quadrant relative to the carrier; the pin itself is the declared rotating mating pair. / [CN] 操作杆相对载体扫过外侧正切向象限，销轴本身是明确声明的转动接触副。

    neighbors, other_heads = {}, {}
    base_box = Part.makeBox(
        s.neighbor_r_max_mm - s.neighbor_r_min_mm,
        2 * s.neighbor_half_width_mm,
        s.neighbor_z_max_mm - s.neighbor_z_min_mm,
        V(s.neighbor_r_min_mm, -s.neighbor_half_width_mm, s.neighbor_z_min_mm),
    )
    for sector, angle in [("up", 90), ("left", 180), ("down", 270)]:
        neighbors[f"{sector}_ReservedModuleEnvelope"] = moved(base_box, angle=angle)
    for placement in placements:
        if placement.sector_name != s.sector:
            for name, shape in build_detector_head(cfg, placement).physical.items():
                other_heads[f"{placement.tag}_{name}"] = shape
    chamber = build_chamber(cfg)
    target = build_target_system(cfg)
    ports = {
        p.name: build_feedthrough_port(cfg, p)
        for p in cfg.compact_one.deployment.service_ports
    }
    plugs, parked_looms = {}, {}
    for index, placement in enumerate(selected):
        zlevel = s.connector_z_mm[index]
        key = f"{placement.tag}_MatingPlug"
        plugs[key] = Part.makeCylinder(
            s.connector_radius_mm,
            s.connector_plug_length_mm,
            V(s.connector_r_mm, s.half_width, zlevel),
            V(0, 1, 0),
        )
        plugs[key] = plugs[key].fuse(
            Part.makeCylinder(
                s.connector_plug_collar_radius_mm,
                s.connector_plug_collar_depth_mm,
                V(
                    s.connector_r_mm,
                    s.half_width
                    + s.connector_plug_length_mm
                    - s.connector_plug_collar_depth_mm,
                    zlevel,
                ),
                V(0, 1, 0),
            )
        )
        port = ports["sector_right"]
        entry = port.channel_entry_points[index]
        lane_y = cfg.vessel.inner_size_y_mm / 2 - 20
        route = [
            V(
                s.connector_parking_x_mm,
                s.connector_parking_y_mm + s.connector_plug_length_mm,
                zlevel,
            ),
            V(s.connector_parking_x_mm, lane_y, zlevel),
            V(s.connector_parking_x_mm, lane_y, port.wall_center.z),
            V(entry.x, lane_y, port.wall_center.z),
            entry,
        ]
        cable, _ = rounded_cable(route, s.cable_radius_mm, s.cable_bend_radius_mm)
        parked_looms[f"{placement.tag}_ParkedFixedLoom"] = cable
    x0, y0, y1, z0, z1 = s.parking_backplate_mm
    parking_parts = [Part.makeBox(half_x - x0, y1 - y0, z1 - z0, V(x0, y0, z0))]
    clip_lo, clip_hi = s.parking_clip_y_mm
    for zlevel in s.connector_z_mm:
        base = V(s.connector_parking_x_mm, clip_lo, zlevel)
        parking_parts.append(
            Part.makeCylinder(
                s.parking_clip_outer_radius_mm, clip_hi - clip_lo, base, V(0, 1, 0)
            ).cut(
                Part.makeCylinder(
                    s.parking_clip_bore_radius_mm,
                    clip_hi - clip_lo + 2,
                    base - V(0, 1, 0),
                    V(0, 1, 0),
                )
            )
        )
    fixed["ServiceParkingComb"] = fused(parking_parts)
    fixed_regions["ServiceParkingComb"] = fixed["ServiceParkingComb"]
    x0, y0, y1, z0, z1 = s.ground_parking_backplate_mm
    ground_fixture = [Part.makeBox(half_x - x0, y1 - y0, z1 - z0, V(x0, y0, z0))]
    x1, x2, peg_y, peg_z0, peg_z1 = s.ground_parking_pegs_mm
    for x in (x1, x2):
        ground_fixture.append(
            Part.makeCylinder(
                s.ground_parking_peg_radius_mm, peg_z1 - peg_z0, V(x, peg_y, peg_z0)
            )
        )
    fixed["GroundParkingFixture"] = fused(ground_fixture)
    fixed_regions["GroundParkingFixture"] = fixed["GroundParkingFixture"]
    ground = {
        "GroundModuleLeg": tube(
            V(178, s.half_width, 155), V(178, 27, 155), s.ground_bond_radius_mm
        ),
        "GroundBridge": tube(V(178, 27, 155), V(190, 27, 155), s.ground_bond_radius_mm),
        "GroundRingLeg": tube(
            V(190, 18, 155), V(190, 27, 155), s.ground_bond_radius_mm
        ),
        "GroundBendA": Part.makeSphere(s.ground_bond_radius_mm, V(178, 27, 155)),
        "GroundBendB": Part.makeSphere(s.ground_bond_radius_mm, V(190, 27, 155)),
    }
    for name in actor:
        if name not in actor_materials:
            actor_materials[name] = (
                "microcoax_provisional"
                if name.endswith("PassiveCoax")
                else (
                    "purchased_connector_provisional"
                    if "PanelCoax" in name
                    else (
                        "stainless_fastener_provisional"
                        if "Screw" in name
                        else "aluminum_6061_provisional"
                    )
                )
            )
    return StudyGeometry(
        actor,
        actor_materials,
        tuple(structural),
        heads,
        head_parts,
        removal,
        purchased,
        fixed,
        fixed_regions,
        neighbors,
        other_heads,
        chamber,
        target,
        ports,
        plugs,
        ground,
        parked_looms,
        tool,
        draw_screw,
        screwdriver,
        paths,
        grip,
        screw_point,
        screw_axis,
        pin_sweeps,
    )
