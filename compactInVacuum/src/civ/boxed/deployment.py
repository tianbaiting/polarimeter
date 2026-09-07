from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import math

import FreeCAD as App
import Part

from .config import load_deployment
from .geometry import build_geometry, moved, fused, rounded_cable, V

ANGLES = {"right": 0, "up": 90, "left": 180, "down": 270}


def vector(sector, r, t, z=0):
    return App.Rotation(V(0, 0, 1), ANGLES[sector]).multVec(V(r, t, z))


def rotate_parts(parts, sector, prefix=True):
    return {
        part_name(sector, name) if prefix else name: moved(shape, angle=ANGLES[sector])
        for name, shape in parts.items()
    }


def part_name(sector, name):
    return f"{sector}_{name[6:] if name.startswith('right_') else name}"


def capture_tool(center, s, length):
    bearing = center + V(0, s.grip_bearing_clearance_mm, 0)
    outer = Part.makeCylinder(
        s.grip_head_radius_mm,
        s.grip_head_depth_mm,
        bearing - V(0, 0, s.grip_head_depth_mm / 2),
    )
    inner = Part.makeCylinder(
        s.grip_pin_radius_mm + s.grip_bearing_clearance_mm,
        s.grip_head_depth_mm + 2,
        bearing - V(0, 0, s.grip_head_depth_mm / 2 + 1),
    )
    annulus = outer.cut(inner)
    upper = Part.makeBox(
        2 * s.grip_head_radius_mm + 2,
        s.grip_head_radius_mm + 1,
        s.grip_head_depth_mm + 2,
        bearing + V(-s.grip_head_radius_mm - 1, 0, -s.grip_head_depth_mm / 2 - 1),
    )
    return {
        "CaptureUpperJaw": annulus.common(upper),
        "CaptureLowerJaw": annulus.cut(upper),
        "HandlingRod": Part.makeCylinder(
            s.grip_rod_radius_mm,
            length,
            bearing + V(0, s.grip_head_radius_mm - 0.5, 0),
            V(0, 1, 0),
        ),
    }


@dataclass
class FullGeometry:
    base: object
    sectors: dict
    materials: dict
    fixed: dict
    fixed_regions: dict
    retainers: dict
    plugs: dict
    grounds: dict
    parked_plugs: dict
    parked_grounds: dict
    looms: dict
    parked_looms: dict
    tools: dict
    grips: dict
    plug_delta: dict
    ground_delta: dict
    poses: dict


def build_deployment(cfg, s, d):
    g = build_geometry(cfg, s, axial_retainer=True)
    actor = dict(g.actor)
    zbase = s.grip_center_mm[2] + s.grip_pin_length_mm / 2 + s.grip_fork_plate_depth_mm
    # [EN] A rear journal places the vertical pickup behind every detector, so the final lower sector can be reached through the space vacated by the upper sector. / [CN] 后伸轴颈使竖直抓取杆位于全部探头之后，最后取下方模块时可利用上方模块已腾出的空间。
    actor["GripRearJournal"] = Part.makeCylinder(
        s.grip_pin_radius_mm,
        d["journal_end_z_mm"] - zbase,
        V(s.grip_center_mm[0], 0, zbase),
    )
    actor["CarrierRearCrossmember"] = actor["CarrierRearCrossmember"].cut(
        Part.makeCylinder(
            s.grip_pin_radius_mm + s.fastener_clearance_mm,
            d["journal_end_z_mm"] - zbase,
            V(s.grip_center_mm[0], 0, zbase),
        )
    )
    g.actor_materials["GripRearJournal"] = "stainless_304L"
    r0, r1 = d["retainer_r_mm"]
    t = d["retainer_half_width_mm"]
    z = s.dock_z_max_mm
    plate = Part.makeBox(r1 - r0, 2 * t, d["retainer_depth_mm"], V(r0, -t, z))
    bolts = {}
    socket = g.fixed_regions["Socket_right"]
    for index, t0 in enumerate(d["retainer_screw_t_mm"]):
        center = V(d["retainer_screw_r_mm"], t0, z + d["retainer_depth_mm"])
        radius = d["retainer_screw_radius_mm"]
        bore = Part.makeCylinder(
            radius + s.fastener_clearance_mm,
            d["retainer_screw_length_mm"] + 2,
            center - V(0, 0, d["retainer_screw_length_mm"]),
            V(0, 0, 1),
        )
        plate, socket = plate.cut(bore), socket.cut(bore)
        bolts[f"RetainerScrew_{index}"] = Part.makeCylinder(
            radius, d["retainer_screw_length_mm"], center, V(0, 0, -1)
        ).fuse(
            Part.makeCylinder(
                d["retainer_screw_head_radius_mm"],
                d["retainer_screw_head_depth_mm"],
                center,
            )
        )
    regions = {"RingWeb": g.fixed_regions["RingWeb"]}
    regions.update(
        {
            f"Socket_{sector}": moved(socket, angle=angle)
            for sector, angle in ANGLES.items()
        }
    )
    fixed = {"AnnularSupportWeldment": fused(regions.values())}
    for sector in ANGLES:
        pins = rotate_parts(
            {n: sh for n, sh in g.fixed.items() if n.startswith("DockPin")}, sector
        )
        fixed.update(pins)
        regions.update(pins)

    sectors, materials, retainers, tools, grips = {}, {}, {}, {}, {}
    plugs, grounds, parked_plugs, parked_grounds = {}, {}, {}, {}
    plug_delta, ground_delta, looms, parked_looms = {}, {}, {}, {}
    for sector in ANGLES:
        sectors[sector] = rotate_parts(actor, sector)
        materials.update(
            {part_name(sector, n): m for n, m in g.actor_materials.items()}
        )
        retainers[sector] = rotate_parts({"RetainerBridge": plate, **bolts}, sector)
        grips[sector] = vector(sector, s.grip_center_mm[0], 0, d["journal_center_z_mm"])
        tools[sector] = {
            f"{sector}_{n}": sh
            for n, sh in capture_tool(
                grips[sector], s, d["handling_rod_length_mm"]
            ).items()
        }
        plugs[sector] = rotate_parts(g.plugs, sector)
        grounds[sector] = rotate_parts(g.ground, sector)
        if sector != "up":
            park_r, park_t = s.connector_parking_x_mm, s.connector_parking_y_mm
            ground_r, ground_t = s.ground_parking_translation_mm[:2]
            parking = {
                n: sh
                for n, sh in g.fixed.items()
                if n in {"ServiceParkingComb", "GroundParkingFixture"}
            }
        else:
            park_r, park_t = d["upper_plug_parking_rt_mm"]
            ground_r, ground_t = d["upper_ground_parking_delta_rt_mm"]
            # [EN] Upper-sector services attach to the left permanent wall, because the circular top aperture removes the former radial attachment surface. / [CN] 上扇区服务件固定到永久左壁，因为圆形顶口切除了原径向支座的承载面。
            wall_t = cfg.vessel.inner_size_x_mm / 2
            clip_lo = park_t + 4
            clip_hi = (
                park_t + s.connector_plug_length_mm - s.connector_plug_collar_depth_mm
            )
            comb = [
                Part.makeBox(11.5, wall_t - clip_lo, 54, V(park_r + 4.5, clip_lo, 153))
            ]
            for zz in s.connector_z_mm:
                comb.append(
                    Part.makeCylinder(
                        s.parking_clip_outer_radius_mm,
                        clip_hi - clip_lo,
                        V(park_r, clip_lo, zz),
                        V(0, 1, 0),
                    ).cut(
                        Part.makeCylinder(
                            s.parking_clip_bore_radius_mm,
                            clip_hi - clip_lo + 2,
                            V(park_r, clip_lo - 1, zz),
                            V(0, 1, 0),
                        )
                    )
                )
            peg_y = (
                27 + ground_t - s.ground_bond_radius_mm - s.ground_parking_peg_radius_mm
            )
            hanger = [
                Part.makeBox(
                    26, wall_t - (peg_y - 4.2), 2, V(175 + ground_r, peg_y - 4.2, 150)
                )
            ]
            for rr in (181 + ground_r, 185 + ground_r):
                hanger.append(
                    Part.makeCylinder(
                        s.ground_parking_peg_radius_mm, 6, V(rr, peg_y, 152)
                    )
                )
            parking = {
                "ServiceParkingComb": fused(comb),
                "GroundParkingFixture": fused(hanger),
            }
        transformed = rotate_parts(parking, sector)
        fixed.update(transformed)
        regions.update(transformed)
        plug_delta[sector] = vector(
            sector, park_r - s.connector_r_mm, park_t - s.half_width
        )
        ground_delta[sector] = vector(sector, ground_r, ground_t)
        parked_plugs[sector] = {
            n: moved(sh, plug_delta[sector]) for n, sh in plugs[sector].items()
        }
        parked_grounds[sector] = {
            n: moved(sh, ground_delta[sector]) for n, sh in grounds[sector].items()
        }
        port = g.ports[f"sector_{sector}"]
        radial = (
            d["upper_loom_radial_lanes_mm"]
            if sector == "up"
            else d["loom_radial_lanes_mm"]
        )
        tangent = (
            d["upper_loom_tangent_lanes_mm"]
            if sector == "up"
            else d["loom_tangent_lanes_mm"]
        )
        for parked, destination in ((False, looms), (True, parked_looms)):
            destination[sector] = {}
            for index, zz in enumerate(s.connector_z_mm):
                start_r, start_t = (
                    (park_r, park_t) if parked else (s.connector_r_mm, s.half_width)
                )
                entry = port.channel_entry_points[index]
                corner = vector(sector, radial[index], tangent[index], zz)
                front_z = d["loom_front_z_mm"][sector][index]
                top_y = (
                    cfg.vessel.inner_size_y_mm / 2
                    - d["loom_top_margin_mm"]
                    + (index if entry.x > 0 else 2 - index)
                    * d["loom_top_lane_spacing_mm"]
                )
                approach_x = math.copysign(d["loom_entry_approach_abs_x_mm"], entry.x)
                first = [
                    vector(sector, start_r, start_t + s.connector_plug_length_mm, zz),
                    vector(sector, start_r, tangent[index], zz),
                ]
                if parked and sector == "up":
                    # [EN] Leave the upper parking comb behind its backplate before turning radially toward the fixed loom lanes. / [CN] 上扇区停放线缆先绕到停放座背板之后，再径向转入固定线槽。
                    turn_z = d["upper_parked_loom_turn_z_mm"][index]
                    first.append(vector(sector, start_r, tangent[index], turn_z))
                    corner = vector(sector, radial[index], tangent[index], turn_z)
                points = [
                    *first,
                    corner,
                    V(corner.x, corner.y, front_z),
                    V(corner.x, top_y, front_z),
                    V(approach_x, top_y, front_z),
                    V(approach_x, top_y, entry.z),
                    V(entry.x, top_y, entry.z),
                    entry,
                ]
                # [EN] Drop collinear or zero segments before constructing true circular cable bends. / [CN] 在生成真实圆弧线缆弯曲前去掉共线或零长度段。
                cleaned = []
                for point in points:
                    if cleaned and (point - cleaned[-1]).Length < 1e-6:
                        continue
                    while (
                        len(cleaned) >= 2
                        and (cleaned[-1] - cleaned[-2])
                        .cross(point - cleaned[-1])
                        .Length
                        < 1e-6
                        and (cleaned[-1] - cleaned[-2]).dot(point - cleaned[-1]) > 0
                    ):
                        cleaned.pop()
                    cleaned.append(point)
                try:
                    cable, _ = rounded_cable(
                        cleaned, s.cable_radius_mm, s.cable_bend_radius_mm
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"{sector} loom {index} parked={parked}: {exc}; points={cleaned}"
                    ) from exc
                destination[sector][f"{sector}_FixedLoom_{index}"] = cable
    return FullGeometry(
        g,
        sectors,
        materials,
        fixed,
        regions,
        retainers,
        plugs,
        grounds,
        parked_plugs,
        parked_grounds,
        looms,
        parked_looms,
        tools,
        grips,
        plug_delta,
        ground_delta,
        {},
    )


def flatten(mapping):
    return {n: sh for group in mapping.values() for n, sh in group.items()}


def chamber_environment(full, work=False, closed=False):
    g = full.base
    result = {**full.fixed_regions, **g.chamber.physical, **g.target.stationary}
    result.update(
        {
            f"Target_{n}": sh
            for n, sh in (g.target.work if work else g.target.park).physical.items()
        }
    )
    result.update(
        {
            n: sh
            for n, sh in g.chamber.purchased_interfaces.items()
            if closed
            or n
            not in {"MaintenanceAccessBlindFlange", "MaintenanceAccessCopperGasket"}
        }
    )
    for port in g.ports.values():
        result.update(port.physical)
        result.update(port.purchased_interfaces)
    return result
