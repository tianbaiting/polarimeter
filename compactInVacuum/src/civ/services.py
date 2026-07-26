from __future__ import annotations

from dataclasses import dataclass

import FreeCAD as App
import Part

from .config import CIVConfig
from .feedthrough import FeedthroughPortGeometry, build_feedthrough_port
from .internal import InternalAssemblyGeometry


@dataclass(frozen=True)
class ServicesGeometry:
    ports: dict[str, FeedthroughPortGeometry]
    physical: dict[str, Part.Shape]
    purchased_interfaces: dict[str, Part.Shape]
    keepouts: dict[str, Part.Shape]
    centerlines: dict[str, Part.Shape]
    datums: dict[str, Part.Shape]
    materials: dict[str, str]
    fast_signal_paths: tuple[str, ...]
    temperature_harnesses: tuple[str, ...]
    grounding_connections: tuple[str, ...]


def _segment_tube(
    start: App.Vector,
    end: App.Vector,
    radius_mm: float,
) -> Part.Shape:
    delta = end - start
    if delta.Length <= 1.0e-9:
        return Part.makeSphere(radius_mm, start)
    return Part.makeCylinder(radius_mm, delta.Length, start, delta)


def _polyline_keepout(
    points: tuple[App.Vector, ...],
    radius_mm: float,
) -> tuple[Part.Shape, Part.Shape]:
    if len(points) < 2:
        raise ValueError("service route requires at least two centerline points")
    segments = [
        _segment_tube(start, end, radius_mm)
        for start, end in zip(points, points[1:])
    ]
    elbows = [
        Part.makeSphere(radius_mm, point)
        for point in points[1:-1]
    ]
    centerline = Part.makePolygon(list(points))
    return Part.makeCompound([*segments, *elbows]), centerline


def _port_by_role_sector(
    ports: dict[str, FeedthroughPortGeometry],
    role: str,
    sector: str | None,
) -> FeedthroughPortGeometry:
    matches = [
        geometry
        for geometry in ports.values()
        if geometry.port.role == role and geometry.port.sector == sector
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one {role} service port for sector {sector}, found {len(matches)}"
        )
    return matches[0]


def _ground_strap(
    cfg: CIVConfig,
    sector: str,
    start: App.Vector,
) -> Part.Shape:
    if sector == "left":
        end = App.Vector(-0.5 * cfg.vessel.inner_size_x_mm, start.y, start.z)
    elif sector == "right":
        end = App.Vector(0.5 * cfg.vessel.inner_size_x_mm, start.y, start.z)
    elif sector == "up":
        end = App.Vector(start.x, 0.5 * cfg.vessel.inner_size_y_mm, start.z)
    else:
        end = App.Vector(start.x, -0.5 * cfg.vessel.inner_size_y_mm, start.z)
    return _segment_tube(start, end, 2.5)


def _sector_tangent(sector: str) -> App.Vector:
    return (
        App.Vector(0.0, 1.0, 0.0)
        if sector in {"left", "right"}
        else App.Vector(1.0, 0.0, 0.0)
    )


def build_services(
    cfg: CIVConfig,
    internal: InternalAssemblyGeometry,
) -> ServicesGeometry:
    if cfg.compact_one is None:
        raise ValueError("services require a CompactOne schema-v2 configuration")
    services = cfg.compact_one.services
    routing = services.routing
    ports = {
        port.name: build_feedthrough_port(cfg, port)
        for port in cfg.compact_one.deployment.service_ports
    }
    physical: dict[str, Part.Shape] = {}
    purchased_interfaces: dict[str, Part.Shape] = {}
    keepouts: dict[str, Part.Shape] = {}
    centerlines: dict[str, Part.Shape] = {}
    datums: dict[str, Part.Shape] = {}
    materials: dict[str, str] = {}
    for port in ports.values():
        physical.update(port.physical)
        purchased_interfaces.update(port.purchased_interfaces)
        keepouts.update(port.keepouts)
        datums.update(port.datums)
        materials.update(port.materials)

    signal_paths: list[str] = []
    temperature_harnesses: list[str] = []
    grounding_connections: list[str] = []
    cable_radius_mm = 0.5 * routing.cable_keepout_diameter_mm
    housekeeping = _port_by_role_sector(ports, "housekeeping", None)
    housekeeping_lane = (
        housekeeping.wall_center
        - App.Vector(0.0, routing.minimum_static_bend_radius_mm, 0.0)
    )
    service_lane_z_mm = (
        cfg.vessel.center_z_mm
        + 0.5 * cfg.vessel.length_mm
        - routing.minimum_static_bend_radius_mm
    )

    for sector, cartridge in internal.cartridges.items():
        signal_port = _port_by_role_sector(ports, "signal", sector)
        signal_lane = (
            signal_port.wall_center
            - App.Vector(0.0, routing.minimum_static_bend_radius_mm, 0.0)
        )
        if len(signal_port.channel_entry_points) < len(cartridge.placements):
            raise ValueError(f"signal feedthrough for {sector} has insufficient entries")
        sector_high_lane = App.Vector(
            cartridge.service_junction.x,
            cartridge.service_junction.y,
            service_lane_z_mm,
        )
        port_high_lane = App.Vector(
            signal_lane.x,
            signal_lane.y,
            service_lane_z_mm,
        )
        tangent = _sector_tangent(sector)
        for index, placement in enumerate(cartridge.placements):
            offset = tangent * (2.5 * (index - 1))
            points = (
                cartridge.service_junction + offset,
                sector_high_lane + offset,
                port_high_lane + offset,
                signal_lane + offset,
                signal_port.channel_entry_points[index],
            )
            route, centerline = _polyline_keepout(points, cable_radius_mm)
            name = f"{placement.tag}_FastSignalPath"
            keepouts[name] = route
            centerlines[f"{name}_Centerline"] = centerline
            signal_paths.append(name)

        housekeeping_entry = housekeeping.channel_entry_points[
            8 * tuple(cfg.sectors).index(sector)
        ]
        harness_points = (
            cartridge.service_junction + App.Vector(0.0, 0.0, 8.0),
            sector_high_lane,
            port_high_lane,
            App.Vector(
                housekeeping_lane.x,
                housekeeping_lane.y,
                service_lane_z_mm,
            ),
            housekeeping_lane,
            housekeeping_entry,
        )
        harness, harness_centerline = _polyline_keepout(
            harness_points,
            cable_radius_mm,
        )
        harness_name = f"{sector}_TemperatureHarness"
        keepouts[harness_name] = harness
        centerlines[f"{harness_name}_Centerline"] = harness_centerline
        temperature_harnesses.append(harness_name)

        mount_interface = cartridge.interfaces[f"{sector}_ChamberMountInterface"]
        start = App.Vector(
            mount_interface.BoundBox.Center.x,
            mount_interface.BoundBox.Center.y,
            mount_interface.BoundBox.Center.z,
        )
        ground_name = f"{sector}_ProtectiveGroundStrap"
        physical[ground_name] = _ground_strap(cfg, sector, start)
        materials[ground_name] = "oxygen_free_copper"
        grounding_connections.append(ground_name)

    keepouts["ExternalServiceManifoldEnvelope"] = Part.makeCompound(
        [
            *purchased_interfaces.values(),
            *(
                shape
                for name, shape in keepouts.items()
                if name.endswith("ExternalConnectorKeepout")
            ),
        ]
    )
    datums["ChamberGroundReferenceDatum"] = Part.makeSphere(
        1.0,
        housekeeping.wall_center,
    )
    return ServicesGeometry(
        ports=ports,
        physical=physical,
        purchased_interfaces=purchased_interfaces,
        keepouts=keepouts,
        centerlines=centerlines,
        datums=datums,
        materials=materials,
        fast_signal_paths=tuple(signal_paths),
        temperature_harnesses=tuple(temperature_harnesses),
        grounding_connections=tuple(grounding_connections),
    )
