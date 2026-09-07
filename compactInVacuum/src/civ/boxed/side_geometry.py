from __future__ import annotations

from dataclasses import replace
import Part

from ..chamber import build_chamber
from ..feedthrough import build_feedthrough_port
from .geometry import V, moved, fused, rounded_cable
from .deployment import build_deployment, vector, ANGLES, capture_tool


def reference_config(cfg):
    dep = cfg.compact_one.deployment
    access = replace(dep.maintenance_access, wall="positive_y_top")
    ports = tuple(
        replace(
            p,
            wall="positive_y_top",
            center_x_mm=p.center_x_mm if p.role == "rotary" else p.center_y_mm,
        )
        for p in dep.service_ports
    )
    return replace(
        cfg,
        compact_one=replace(
            cfg.compact_one,
            deployment=replace(dep, maintenance_access=access, service_ports=ports),
        ),
    )


def prism_rz(points, t0, thickness):
    vertices = [V(r, t0, z) for r, z in points]
    return Part.Face(Part.makePolygon(vertices + [vertices[0]])).extrude(
        V(0, thickness, 0)
    )


def weld_pad(radius, t, z0, z1, thickness, leg):
    pad = Part.makeBox(thickness, 2 * t, z1 - z0, V(radius - thickness, -t, z0))
    beads = []
    for sign in (-1, 1):
        points = [
            V(radius, sign * t, z0),
            V(radius - leg, sign * t, z0),
            V(radius, sign * (t + leg), z0),
        ]
        beads.append(
            Part.Face(Part.makePolygon(points + [points[0]])).extrude(V(0, 0, z1 - z0))
        )
    return fused([pad, *beads])


def clean_route(points):
    cleaned = []
    for p in points:
        if cleaned and (p - cleaned[-1]).Length < 1e-6:
            continue
        while (
            len(cleaned) > 1
            and (cleaned[-1] - cleaned[-2]).cross(p - cleaned[-1]).Length < 1e-6
            and (cleaned[-1] - cleaned[-2]).dot(p - cleaned[-1]) > 0
        ):
            cleaned.pop()
        cleaned.append(p)
    return cleaned


def build_side_geometry(cfg, s, d, q):
    f = build_deployment(reference_config(cfg), s, d)
    g = f.base
    old_fixed = dict(f.fixed)
    g.chamber = build_chamber(cfg)
    g.ports = {
        p.name: build_feedthrough_port(cfg, p)
        for p in cfg.compact_one.deployment.service_ports
    }
    fixed, bodies, pads, bolts, drivers = {}, {}, {}, {}, {}
    for sector in ANGLES:
        radius = (
            cfg.vessel.inner_size_x_mm
            if sector in {"right", "left"}
            else cfg.vessel.inner_size_y_mm
        ) / 2
        pad_inner = radius - q["wall_pad_thickness_mm"]
        flange_inner = pad_inner - q["support_flange_thickness_mm"]
        z0, z1 = q["window_pad_z_mm"] if sector == "right" else q["wall_pad_z_mm"]
        pad = weld_pad(
            radius,
            q["wall_pad_half_width_mm"],
            z0,
            z1,
            q["wall_pad_thickness_mm"],
            q["wall_weld_leg_mm"],
        )
        socket = moved(f.fixed_regions[f"Socket_{sector}"], angle=-ANGLES[sector])
        flange = Part.makeBox(
            q["support_flange_thickness_mm"],
            2 * q["support_flange_half_width_mm"],
            z1 - z0,
            V(flange_inner, -q["support_flange_half_width_mm"], z0),
        )
        back = Part.makeBox(
            pad_inner - 195,
            2 * s.cheek_inner_half_width_mm,
            s.dock_z_max_mm - s.ring_front_z_mm,
            V(195, -s.cheek_inner_half_width_mm, s.ring_front_z_mm),
        )
        parts = [socket, flange, back]
        if sector == "right":
            parts.append(
                Part.makeBox(
                    q["support_flange_thickness_mm"],
                    2 * s.cheek_inner_half_width_mm,
                    s.dock_z_max_mm - z1,
                    V(flange_inner, -s.cheek_inner_half_width_mm, z1),
                )
            )
            for t0 in (
                -s.cheek_inner_half_width_mm,
                s.cheek_inner_half_width_mm - q["window_rib_thickness_mm"],
            ):
                parts.append(
                    prism_rz(
                        [
                            (flange_inner, z1),
                            (flange_inner, s.dock_z_max_mm),
                            (s.dock_plane_r_mm, s.dock_z_max_mm),
                        ],
                        t0,
                        q["window_rib_thickness_mm"],
                    )
                )
        body = fused(parts)
        # [EN] Press-fit locating pins have real bores; local support bodies remain removable from the factory-welded wall pads. / [CN] 定位销具有真实配合孔，局部支座可从工厂预焊的腔壁安装垫上拆下。
        for n, pin in g.fixed.items():
            if n.startswith("DockPin"):
                body = body.cut(pin)
                fixed[f"{sector}_{n}"] = moved(pin, angle=ANGLES[sector])
        bolts[sector], drivers[sector] = {}, {}
        center_z = (
            q["window_screw_center_z_mm"]
            if sector == "right"
            else q["mount_screw_center_z_mm"]
        )
        for t in q["mount_screw_t_mm"]:
            for dz in q["mount_screw_z_offsets_mm"]:
                zz = center_z + dz
                head = V(flange_inner, t, zz)
                shaft_start = flange_inner - q["mount_screw_head_depth_mm"] / 2
                end = radius - q["mount_screw_blind_end_offset_mm"]
                bore = Part.makeCylinder(
                    q["mount_screw_radius_mm"] + s.fastener_clearance_mm,
                    end - shaft_start,
                    V(shaft_start, t, zz),
                    V(1, 0, 0),
                )
                body, pad = body.cut(bore), pad.cut(bore)
                bolt = Part.makeCylinder(
                    q["mount_screw_radius_mm"],
                    end - shaft_start,
                    V(shaft_start, t, zz),
                    V(1, 0, 0),
                ).fuse(
                    Part.makeCylinder(
                        q["mount_screw_head_radius_mm"],
                        q["mount_screw_head_depth_mm"],
                        head,
                        V(-1, 0, 0),
                    )
                )
                key = f"{sector}_SupportMountScrew_{len(bolts[sector])}"
                bolts[sector][key] = moved(bolt, angle=ANGLES[sector])
                probe = Part.makeCylinder(
                    q["mount_driver_radius_mm"],
                    q["mount_driver_length_mm"],
                    head - V(q["mount_screw_head_depth_mm"], 0, 0),
                    V(-1, 0, 0),
                )
                drivers[sector][key + "_DriverAccess"] = moved(
                    probe, angle=ANGLES[sector]
                )
        bodies[sector] = {
            f"LocalWallSupport_{sector}": moved(body, angle=ANGLES[sector]),
            **{n: sh for n, sh in fixed.items() if n.startswith(sector + "_DockPin")},
        }
        pads[f"FactoryWeldedWallPad_{sector}"] = moved(pad, angle=ANGLES[sector])
        fixed.update(bodies[sector])
        fixed.update(bolts[sector])
    fixed.update(pads)
    for sector in ANGLES:
        for suffix in ("ServiceParkingComb", "GroundParkingFixture"):
            if sector == "right":
                shape = moved(old_fixed[f"up_{suffix}"], angle=-90)
            else:
                shape = moved(g.fixed[suffix], angle=ANGLES[sector])
            fixed[f"{sector}_{suffix}"] = shape
        rr, tt = (
            d["upper_plug_parking_rt_mm"]
            if sector == "right"
            else (s.connector_parking_x_mm, s.connector_parking_y_mm)
        )
        dr, dt = (
            d["upper_ground_parking_delta_rt_mm"]
            if sector == "right"
            else s.ground_parking_translation_mm[:2]
        )
        f.plug_delta[sector] = vector(sector, rr - s.connector_r_mm, tt - s.half_width)
        f.ground_delta[sector] = vector(sector, dr, dt)
        f.parked_plugs[sector] = {
            n: moved(sh, f.plug_delta[sector]) for n, sh in f.plugs[sector].items()
        }
        f.parked_grounds[sector] = {
            n: moved(sh, f.ground_delta[sector]) for n, sh in f.grounds[sector].items()
        }
        port = g.ports[f"sector_{sector}"]
        radial = (
            d["upper_loom_radial_lanes_mm"]
            if sector == "right"
            else d["loom_radial_lanes_mm"]
        )
        tangent = (
            d["upper_loom_tangent_lanes_mm"]
            if sector == "right"
            else d["loom_tangent_lanes_mm"]
        )
        for parked, destination in ((False, f.looms), (True, f.parked_looms)):
            destination[sector] = {}
            for i, zz in enumerate(s.connector_z_mm):
                r0, t0 = (rr, tt) if parked else (s.connector_r_mm, s.half_width)
                route = [
                    vector(sector, r0, t0 + s.connector_plug_length_mm, zz),
                    vector(sector, r0, tangent[i], zz),
                ]
                turn_z = zz
                if parked and sector == "right":
                    turn_z = d["upper_parked_loom_turn_z_mm"][i]
                    route.append(vector(sector, r0, tangent[i], turn_z))
                corner = vector(sector, radial[i], tangent[i], turn_z)
                entry = port.channel_entry_points[i]
                sign = 1 if entry.y > 0 else -1
                front_z = q["loom_front_z_mm"][sector][i]
                approach_x = (
                    q["loom_approach_x_mm"][sector]
                    - sign * i * q["loom_approach_step_mm"]
                )
                turn_y = sign * q["loom_entry_turn_abs_y_mm"]
                route += [
                    corner,
                    V(corner.x, corner.y, front_z),
                    V(approach_x, corner.y, front_z),
                    V(approach_x, turn_y, front_z),
                    V(approach_x, turn_y, entry.z),
                    V(approach_x, entry.y, entry.z),
                    entry,
                ]
                try:
                    cable, _ = rounded_cable(
                        clean_route(route), s.cable_radius_mm, s.cable_bend_radius_mm
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"side {sector} loom {i} parked={parked}: {exc}; {route}"
                    ) from exc
                destination[sector][f"{sector}_FixedLoom_{i}"] = cable
        tool = capture_tool(f.grips[sector], s, d["handling_rod_length_mm"])
        tool["HandlingRod"] = Part.makeCylinder(
            s.grip_rod_radius_mm,
            d["handling_rod_length_mm"],
            f.grips[sector] + V(0, q["capture_rod_y_offset_mm"], 0),
            V(1, 0, 0),
        )
        f.tools[sector] = {f"{sector}_{n}": sh for n, sh in tool.items()}
    f.fixed, f.fixed_regions = fixed, dict(fixed)
    f.support_bodies, f.wall_pads, f.mount_bolts, f.mount_drivers = (
        bodies,
        pads,
        bolts,
        drivers,
    )
    f.support_poses = {}
    return f
