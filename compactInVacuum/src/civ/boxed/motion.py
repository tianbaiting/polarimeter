from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
import math

import FreeCAD as App
import Part

from ..layout import scaled
from .geometry import moved, V


def bbox_distance(a, b):
    return math.sqrt(
        sum(
            max(0.0, lo_b - hi_a, lo_a - hi_b) ** 2
            for lo_a, hi_a, lo_b, hi_b in (
                (a.XMin, a.XMax, b.XMin, b.XMax),
                (a.YMin, a.YMax, b.YMin, b.YMax),
                (a.ZMin, a.ZMax, b.ZMin, b.ZMax),
            )
        )
    )


def overlap(a, b):
    if bbox_distance(a.BoundBox, b.BoundBox) > 1e-8:
        return 0.0
    result = a.common(b)
    return 0.0 if result.isNull() else float(result.Volume)


def radius_about_z(shape, pivot):
    b = shape.optimalBoundingBox(False, False)
    return max(
        math.hypot(x - pivot.x, y - pivot.y)
        for x in (b.XMin, b.XMax)
        for y in (b.YMin, b.YMax)
    )


def rotation_box(box, pivot, angle_deg):
    # [EN] Every coordinate extremum of a rotated bounding rectangle occurs at a corner endpoint or a sine/cosine stationary angle. / [CN] 旋转包围矩形的坐标极值必定位于角点轨迹的端点或正余弦驻点。
    lo, hi = sorted((0.0, math.radians(angle_deg)))
    points = []
    quarter = math.pi / 2
    for x in (box.XMin, box.XMax):
        for y in (box.YMin, box.YMax):
            u, v = x - pivot.x, y - pivot.y
            phi = math.atan2(v, u)
            angles = [lo, hi]
            angles.extend(
                k * quarter - phi
                for k in range(
                    math.floor((lo + phi) / quarter) - 1,
                    math.ceil((hi + phi) / quarter) + 2,
                )
                if lo <= k * quarter - phi <= hi
            )
            points.extend(
                (
                    pivot.x + u * math.cos(a) - v * math.sin(a),
                    pivot.y + u * math.sin(a) + v * math.cos(a),
                )
                for a in angles
            )
    return App.BoundBox(
        min(x for x, y in points),
        min(y for x, y in points),
        box.ZMin,
        max(x for x, y in points),
        max(y for x, y in points),
        box.ZMax,
    )


@dataclass(frozen=True)
class VoidRegion:
    kind: str
    values: tuple

    def shape(self):
        if self.kind == "box":
            x0, x1, y0, y1, z0, z1 = self.values
            return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))
        a, b, r, lo, hi = self.values
        return (
            Part.makeCylinder(r, hi - lo, V(a, lo, b), V(0, 1, 0))
            if self.kind == "cylinder_y"
            else Part.makeCylinder(r, hi - lo, V(a, b, lo))
        )

    def lower_bound(self, box):
        if self.kind == "box":
            x0, x1, y0, y1, z0, z1 = self.values
            return min(
                box.XMin - x0,
                x1 - box.XMax,
                box.YMin - y0,
                y1 - box.YMax,
                box.ZMin - z0,
                z1 - box.ZMax,
            )
        a, b, r, lo, hi = self.values
        if self.kind == "cylinder_y":
            radial = max(
                math.hypot(x - a, z - b)
                for x in (box.XMin, box.XMax)
                for z in (box.ZMin, box.ZMax)
            )
            return min(r - radial, box.YMin - lo, hi - box.YMax)
        radial = max(
            math.hypot(x - a, y - b)
            for x in (box.XMin, box.XMax)
            for y in (box.YMin, box.YMax)
        )
        return min(r - radial, box.ZMin - lo, hi - box.ZMax)


def verify_void_regions(candidates, obstacles, tolerance):
    certified = {}
    records = []
    for name, regions in candidates.items():
        for region in regions:
            volume = overlap(region.shape(), obstacles[name])
            passed = volume <= tolerance
            records.append(
                {
                    "obstacle": name,
                    "kind": region.kind,
                    "values": region.values,
                    "intersection_volume_mm3": volume,
                    "status": "pass" if passed else "fail",
                }
            )
            if passed:
                certified.setdefault(name, []).append(region)
    return certified, records


def study_void_candidates(g, s):
    c = g.chamber.candidate
    half_x, half_y = c.inner_size_x_mm / 2, c.inner_size_y_mm / 2
    box = VoidRegion(
        "box",
        (
            -half_x,
            half_x,
            -half_y,
            half_y,
            c.center_z_mm - c.length_mm / 2 + c.wall_thickness_mm,
            c.center_z_mm + c.length_mm / 2 - c.wall_thickness_mm,
        ),
    )
    access = g.chamber.keepouts["MaintenanceAccessOpenPassage"].BoundBox
    center_x = (access.XMin + access.XMax) / 2
    center_z = (access.ZMin + access.ZMax) / 2
    radius = access.XLength / 2
    extent = s.grip_rod_length_mm + s.lift_mm + 1000
    port = VoidRegion("cylinder_y", (center_x, center_z, radius, -half_y, extent))
    result = {
        "ProjectChamberBody": [box, port],
        "RingWeb": [
            VoidRegion("cylinder_z", (0, 0, s.ring_inner_radius_mm, -extent, extent))
        ],
    }
    for name in (
        "MaintenanceAccessProjectWeldNeck",
        "MaintenanceAccessProjectWeldBead",
        "MaintenanceAccessFixedICFFlange",
    ):
        result[name] = [port]
    return result


@dataclass
class Phase:
    name: str
    starts: dict
    obstacles: dict
    delta: object = None
    pivot: object = None
    angle: float = 0.0
    excluded_pairs: frozenset = frozenset()
    contacts: frozenset = frozenset()

    @cached_property
    def rotation_radii(self):
        return {
            name: radius_about_z(shape, self.pivot)
            for name, shape in self.starts.items()
        }

    def at(self, fraction):
        return {
            name: moved(
                shape,
                scaled(self.delta, fraction) if self.delta is not None else V(),
                self.angle * fraction,
                self.pivot or V(),
            )
            for name, shape in self.starts.items()
        }

    def displacement_bound(self, name, a, b):
        if self.delta is not None:
            return self.delta.Length * (b - a) / 2
        radius = self.rotation_radii[name]
        return 2 * radius * math.sin(math.radians(abs(self.angle)) * (b - a) / 4)


def translation_plane_certificate(start, end, obstacle):
    # [EN] A common separating plane at both endpoints separates every intermediate translation, including an intended zero-gap mating contact. / [CN] 平移两端共有的分离平面也分离所有中间位置，包括指定的零间隙装配接触。
    # [EN] Trimmed cylindrical holes can inflate the default bounds; use exact non-triangulated OCC bounds for the separating-plane certificate. / [CN] 修剪圆柱孔会放大默认包围盒，因此分离平面证明采用不依赖三角网格的精确 OCC 边界。
    a, b, c = (sh.optimalBoundingBox(False, False) for sh in (start, end, obstacle))
    for axis in "XYZ":
        lo, hi = axis + "Min", axis + "Max"
        if max(getattr(a, hi), getattr(b, hi)) <= getattr(c, lo) + 1e-7:
            return True
        if min(getattr(a, lo), getattr(b, lo)) >= getattr(c, hi) - 1e-7:
            return True
    return False


def certify_phase(
    phase: Phase, spec, certified_mates=frozenset(), certified_regions=None
):
    certified_regions = certified_regions or {}
    missing = phase.excluded_pairs - set(certified_mates)
    if missing:
        return {
            "name": phase.name,
            "status": "fail",
            "certified_intervals": 0,
            "failures": [
                {"kind": "missing_mating_certificate", "pairs": sorted(missing)}
            ],
        }
    stack = [(0.0, 1.0, 0)]
    accepted = 0
    evaluations = 0
    exact_distances = 0
    minimum_certified_gap = float("inf")
    failures = []
    end = phase.at(1)
    plane_pairs = set()
    swept_pairs = set()
    start_bounds = {
        n: sh.optimalBoundingBox(False, False) for n, sh in phase.starts.items()
    }
    obstacle_bounds = {
        n: sh.optimalBoundingBox(False, False) for n, sh in phase.obstacles.items()
    }
    if phase.delta is None:
        # [EN] The complete configured angular sweep is enclosed without extending the arc into unused quadrants. / [CN] 包围完整指定转角的扫掠范围，无需扩展到并未经过的象限。
        for name, start in phase.starts.items():
            sweep_box = rotation_box(start_bounds[name], phase.pivot, phase.angle)
            for obstacle_name, obstacle in phase.obstacles.items():
                distance = bbox_distance(sweep_box, obstacle_bounds[obstacle_name])
                for region in certified_regions.get(obstacle_name, ()):
                    distance = max(distance, region.lower_bound(sweep_box))
                if distance > spec.continuous_clearance_mm:
                    swept_pairs.add((name, obstacle_name))
    if phase.delta is not None:
        # [EN] A translation stays inside the union bounds of its endpoints; an obstacle separated from that entire prism needs no temporal subdivision. / [CN] 平移始终位于两端包围盒的并集棱柱内，与整个棱柱分离的障碍物无需再进行时间细分。
        for name, start in phase.starts.items():
            sweep_box = App.BoundBox(start_bounds[name])
            sweep_box.add(end[name].optimalBoundingBox(False, False))
            for obstacle_name, obstacle in phase.obstacles.items():
                distance = bbox_distance(sweep_box, obstacle_bounds[obstacle_name])
                for region in certified_regions.get(obstacle_name, ()):
                    distance = max(distance, region.lower_bound(sweep_box))
                if distance > spec.continuous_clearance_mm:
                    swept_pairs.add((name, obstacle_name))
        for actor_name, obstacle_name in phase.contacts:
            if translation_plane_certificate(
                phase.starts[actor_name],
                end[actor_name],
                phase.obstacles[obstacle_name],
            ):
                plane_pairs.add((actor_name, obstacle_name))
    while stack:
        a, b, depth = stack.pop()
        mid = phase.at((a + b) / 2)
        evaluations += 1
        unresolved = None
        for name, shape in mid.items():
            bound = phase.displacement_bound(name, a, b)
            for obstacle_name, obstacle in phase.obstacles.items():
                pair = (name, obstacle_name)
                if (
                    pair in phase.excluded_pairs
                    or pair in plane_pairs
                    or pair in swept_pairs
                ):
                    continue
                distance = bbox_distance(shape.BoundBox, obstacle_bounds[obstacle_name])
                # [EN] A region independently proved empty supplies a lower bound on distance to this obstacle; it does not remove any obstacle or relax the motion bound. / [CN] 独立证明为空的区域提供到该障碍物的距离下界，并未删除障碍物或放宽运动界。
                for region in certified_regions.get(obstacle_name, ()):
                    distance = max(distance, region.lower_bound(shape.BoundBox))
                if distance <= bound + spec.continuous_clearance_mm:
                    distance = float(shape.distToShape(obstacle)[0])
                    exact_distances += 1
                # [EN] Distance is 1-Lipschitz under bounded point displacement; this inequality certifies the entire interval, not just its midpoint. / [CN] 最小距离对有界点位移满足 1-Lipschitz 界，因此该不等式证明整个区间而非仅中点。
                if distance > bound + spec.continuous_clearance_mm:
                    minimum_certified_gap = min(minimum_certified_gap, distance - bound)
                    continue
                if distance <= 1e-7:
                    volume = overlap(shape, obstacle)
                    if volume > spec.collision_volume_tolerance_mm3:
                        failures.append(
                            {
                                "kind": "collision",
                                "actor": name,
                                "obstacle": obstacle_name,
                                "fraction": (a + b) / 2,
                                "volume_mm3": volume,
                            }
                        )
                        break
                unresolved = (name, obstacle_name, distance, bound)
                break
            if failures or unresolved:
                break
        if failures:
            break
        if unresolved is None:
            accepted += 1
        elif depth >= spec.interval_max_depth or b - a <= spec.interval_min_fraction:
            name, obstacle_name, distance, bound = unresolved
            failures.append(
                {
                    "kind": "uncertified_interval",
                    "actor": name,
                    "obstacle": obstacle_name,
                    "interval": [a, b],
                    "distance_mm": distance,
                    "motion_bound_mm": bound,
                }
            )
            break
        else:
            middle = (a + b) / 2
            stack.extend([(middle, b, depth + 1), (a, middle, depth + 1)])
    return {
        "name": phase.name,
        "status": "pass" if not failures else "fail",
        "method": "distance_displacement_interval_certificate",
        "certified_intervals": accepted,
        "interval_evaluations": evaluations,
        "exact_distance_calls": exact_distances,
        "minimum_certified_gap_mm": (
            None if minimum_certified_gap == float("inf") else minimum_certified_gap
        ),
        "plane_contact_certificates": sorted(plane_pairs),
        "swept_bounding_region_certificate_count": len(swept_pairs),
        "analytic_mating_pairs": sorted(phase.excluded_pairs),
        "failures": failures,
    }


def environment(g, s):
    result = {**g.fixed_regions, **g.neighbors, **g.chamber.physical}
    result.update(g.target.stationary)
    result.update(
        {f"TargetPark_{name}": shape for name, shape in g.target.park.physical.items()}
    )
    result.update(
        {
            name: shape
            for name, shape in g.chamber.purchased_interfaces.items()
            if name
            not in {"MaintenanceAccessBlindFlange", "MaintenanceAccessCopperGasket"}
        }
    )
    for port in g.ports.values():
        result.update(port.physical)
        result.update(port.purchased_interfaces)
    return result


def plug_parking_delta(s):
    return V(
        s.connector_parking_x_mm - s.connector_r_mm,
        s.connector_parking_y_mm - s.half_width,
        0,
    )


def ground_parking_delta(s):
    return V(*s.ground_parking_translation_mm)


def parked_environment(g, s):
    result = environment(g, s)
    result.update(
        {name: moved(shape, plug_parking_delta(s)) for name, shape in g.plugs.items()}
    )
    result.update(
        {
            name: moved(shape, ground_parking_delta(s))
            for name, shape in g.ground.items()
        }
    )
    result.update(g.parked_looms)
    # [EN] Circular fillets remain inside their corner triangles, so these per-channel slabs conservatively bound the flexible loom while its plug is moved to the parking location. / [CN] 圆角位于各自转角三角形内，因此逐路薄层可保守包络插头移入停放位置时的柔性线束。
    for index, z in enumerate(s.connector_z_mm):
        lane_y = g.chamber.candidate.inner_size_y_mm / 2 - 20
        low_y = s.connector_parking_y_mm + s.connector_plug_length_mm
        result[f"FixedLoomWorkspace_{index}"] = Part.makeBox(
            s.connector_parking_x_mm - s.connector_r_mm + 2 * s.cable_radius_mm,
            lane_y - low_y + 2 * s.cable_radius_mm,
            2 * s.cable_radius_mm,
            V(
                s.connector_r_mm - s.cable_radius_mm,
                low_y - s.cable_radius_mm,
                z - s.cable_radius_mm,
            ),
        )
        result[f"FixedLoomWorkspaceUnplug_{index}"] = Part.makeBox(
            2 * s.cable_radius_mm,
            lane_y
            - (s.half_width + s.connector_plug_length_mm)
            + 2 * s.cable_radius_mm,
            2 * s.cable_radius_mm,
            V(
                s.connector_r_mm - s.cable_radius_mm,
                s.half_width + s.connector_plug_length_mm - s.cable_radius_mm,
                z - s.cable_radius_mm,
            ),
        )
    return result


def main_motion_phases(g, s):
    fixed = parked_environment(g, s)
    combined = {**g.actor, **g.tool}
    actor_names = set(g.actor)
    pin_pairs = {(a, p) for a in actor_names for p in g.pin_sweeps}
    contacts = {(a, "Socket_right") for a in actor_names}
    release = Phase(
        "09_radial_release",
        combined,
        fixed,
        delta=V(-s.radial_release_mm, 0, 0),
        excluded_pairs=frozenset(pin_pairs),
        contacts=frozenset(contacts),
    )
    after_release = release.at(1)
    transfer = Phase(
        "10_downstream_transfer",
        after_release,
        fixed,
        delta=V(0, 0, s.downstream_translation_mm),
    )
    after_transfer = transfer.at(1)
    pivot = g.grip + V(-s.radial_release_mm, 0, s.downstream_translation_mm)
    actor_transfer = {n: sh for n, sh in after_transfer.items() if n in actor_names}
    turn = Phase(
        "11_controlled_turn", actor_transfer, fixed, pivot=pivot, angle=s.rotation_deg
    )
    after_turn = {
        **turn.at(1),
        **{n: sh for n, sh in after_transfer.items() if n not in actor_names},
    }
    center = Phase("12_center_below_port", after_turn, fixed, delta=V(-pivot.x, 0, 0))
    lift = Phase("13_lift_through_port", center.at(1), fixed, delta=V(0, s.lift_mm, 0))
    return [release, transfer, turn, center, lift]


def preparation_phases(g, s):
    fixed = environment(g, s)
    installed = {**fixed, **g.actor, **g.draw_screw}
    plug_contacts = frozenset(
        (name, name.replace("MatingPlug", "PanelCoaxConnectorEnvelope"))
        for name in g.plugs
    )
    plugs = Phase(
        "01_disconnect_signal_plugs",
        g.plugs,
        {**installed, **g.ground},
        delta=V(0, s.connector_withdrawal_mm, 0),
        contacts=plug_contacts,
    )
    plug_park = Phase(
        "02_park_signal_plugs",
        plugs.at(1),
        {**installed, **g.ground},
        delta=V(s.connector_parking_x_mm - s.connector_r_mm, 0, 0),
    )
    plug_seat = Phase(
        "02b_seat_signal_plugs",
        plug_park.at(1),
        {**installed, **g.ground},
        delta=V(
            0, s.connector_parking_y_mm - s.half_width - s.connector_withdrawal_mm, 0
        ),
        excluded_pairs=frozenset((name, "ServiceParkingComb") for name in g.plugs),
    )
    ground_contacts = frozenset(
        {("GroundModuleLeg", "CarrierCheekPositive"), ("GroundRingLeg", "Socket_right")}
    )
    ground = Phase(
        "03_disconnect_ground",
        g.ground,
        {**installed, **plug_seat.at(1)},
        delta=V(0, s.connector_withdrawal_mm, 0),
        contacts=ground_contacts,
    )
    ground_park = Phase(
        "04_park_ground",
        ground.at(1),
        {**installed, **plug_seat.at(1)},
        delta=V(ground_parking_delta(s).x, 0, 0),
    )
    ground_seat = Phase(
        "04b_seat_ground_on_fixture",
        ground_park.at(1),
        {**installed, **plug_seat.at(1)},
        delta=V(0, ground_parking_delta(s).y - s.connector_withdrawal_mm, 0),
        contacts=frozenset({("GroundBridge", "GroundParkingFixture")}),
    )
    parked = parked_environment(g, s)
    jaw_open = {
        **g.tool,
        "CaptureLowerJaw": moved(
            g.tool["CaptureLowerJaw"], V(*s.grip_jaw_open_offset_mm)
        ),
    }
    entry = Phase(
        "05_insert_capture_tool",
        {n: moved(sh, V(0, 350, 0)) for n, sh in jaw_open.items()},
        {**parked, **g.actor, **g.draw_screw},
        delta=V(0, -350, 0),
    )
    jaw_offset = V(*s.grip_jaw_open_offset_mm)
    jaw_lateral = Phase(
        "06_align_capture_jaw",
        {"CaptureLowerJaw": jaw_open["CaptureLowerJaw"]},
        {
            **parked,
            **g.actor,
            **g.draw_screw,
            **{n: sh for n, sh in g.tool.items() if n != "CaptureLowerJaw"},
        },
        delta=V(-jaw_offset.x, 0, 0),
    )
    jaw_close = Phase(
        "07_close_capture_jaw",
        jaw_lateral.at(1),
        jaw_lateral.obstacles,
        delta=V(0, -jaw_offset.y, 0),
        excluded_pairs=frozenset({("CaptureLowerJaw", "GripTrunnion")}),
        contacts=frozenset({("CaptureLowerJaw", "CaptureUpperJaw")}),
    )
    return [
        plugs,
        plug_park,
        plug_seat,
        ground,
        ground_park,
        ground_seat,
        entry,
        jaw_lateral,
        jaw_close,
    ]
