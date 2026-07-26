from __future__ import annotations

from dataclasses import dataclass

import FreeCAD as App
import Part

from .cassette import (
    CassetteGeometry,
    build_detector_cassette,
    cassette_connector_segment,
)
from .config import CIVConfig
from .layout import (
    DetectorPlacement,
    build_detector_placements,
    cassette_axis_position,
    placement_from_direction,
    scaled,
)


@dataclass(frozen=True)
class SectorCartridgeGeometry:
    sector: str
    placements: tuple[DetectorPlacement, ...]
    service_junction: App.Vector
    physical: dict[str, Part.Shape]
    interfaces: dict[str, Part.Shape]
    keepouts: dict[str, Part.Shape]
    datums: dict[str, Part.Shape]
    materials: dict[str, str]
    thermal_connections: tuple[tuple[str, str], ...]


def _beam_between(
    start: App.Vector,
    end: App.Vector,
    width_mm: float,
    thickness_mm: float,
) -> Part.Shape:
    delta = end - start
    if delta.Length <= 1.0e-9:
        raise ValueError("cartridge beam endpoints must be distinct")
    beam = Part.makeBox(
        width_mm,
        thickness_mm,
        delta.Length,
        App.Vector(-0.5 * width_mm, -0.5 * thickness_mm, 0.0),
    )
    beam.Placement = placement_from_direction(start, delta)
    return beam


def _segment_keepout(
    start: App.Vector,
    end: App.Vector,
    radius_mm: float,
) -> Part.Shape:
    delta = end - start
    if delta.Length <= 1.0e-9:
        return Part.makeSphere(radius_mm, start)
    return Part.makeCylinder(radius_mm, delta.Length, start, delta)


def _placed_mount_pad(
    cfg: CIVConfig,
    placement: DetectorPlacement,
) -> Part.Shape:
    cartridge = cfg.compact_one.sector_cartridge
    cassette = cfg.compact_one.detector.cassette
    width_mm, height_mm, thickness_mm = cartridge.mount_pad_mm
    pad = Part.makeBox(
        width_mm,
        height_mm,
        thickness_mm,
        App.Vector(
            -0.5 * width_mm,
            -0.5 * height_mm,
            cassette.mounting_datum_offset_mm,
        ),
    )
    cable_bore = Part.makeCylinder(
        0.5 * cassette.connector_keepout_diameter_mm,
        thickness_mm + 0.4,
        App.Vector(
            0.0,
            0.0,
            cassette.mounting_datum_offset_mm - 0.2,
        ),
    )
    pad = pad.cut(cable_bore)
    pad.Placement = placement_from_direction(
        scaled(placement.direction, placement.radius_mm),
        placement.direction,
    )
    return pad


def _sector_tangent(sector: str) -> App.Vector:
    return (
        App.Vector(0.0, 1.0, 0.0)
        if sector in {"left", "right"}
        else App.Vector(1.0, 0.0, 0.0)
    )


def _sector_inward(sector: str) -> App.Vector:
    return {
        "left": App.Vector(1.0, 0.0, 0.0),
        "right": App.Vector(-1.0, 0.0, 0.0),
        "up": App.Vector(0.0, -1.0, 0.0),
        "down": App.Vector(0.0, 1.0, 0.0),
    }[sector]


def _sector_wall_anchor(
    cfg: CIVConfig,
    placement: DetectorPlacement,
    start: App.Vector,
) -> App.Vector:
    cartridge = cfg.compact_one.sector_cartridge
    routing = cfg.compact_one.services.routing
    z_min_mm = cfg.vessel.center_z_mm - 0.5 * cfg.vessel.length_mm
    z_max_mm = cfg.vessel.center_z_mm + 0.5 * cfg.vessel.length_mm
    anchor_z_mm = min(
        max(start.z + 30.0, z_min_mm + cartridge.backbone_margin_mm),
        z_max_mm - cartridge.backbone_margin_mm,
    )
    if placement.sector_name in {"left", "right"}:
        sign = -1.0 if placement.sector_name == "left" else 1.0
        wall_x_mm = sign * (
            0.5 * cfg.vessel.inner_size_x_mm - routing.wall_clearance_mm
        )
        return App.Vector(wall_x_mm, 0.0, anchor_z_mm)
    sign = 1.0 if placement.sector_name == "up" else -1.0
    wall_y_mm = sign * (
        0.5 * cfg.vessel.inner_size_y_mm - routing.wall_clearance_mm
    )
    return App.Vector(0.0, wall_y_mm, anchor_z_mm)


def _backbone_shape(
    cfg: CIVConfig,
    sector: str,
    anchors: tuple[App.Vector, ...],
) -> tuple[Part.Shape, Part.Shape, App.Vector]:
    cartridge = cfg.compact_one.sector_cartridge
    routing = cfg.compact_one.services.routing
    z_min_mm = min(point.z for point in anchors) - cartridge.backbone_margin_mm
    z_max_mm = max(point.z for point in anchors) + cartridge.backbone_margin_mm
    length_mm = z_max_mm - z_min_mm
    depth_mm = cartridge.backbone_depth_mm
    width_mm = cartridge.backbone_width_mm

    if sector in {"left", "right"}:
        sign = -1.0 if sector == "left" else 1.0
        inner_face_x_mm = sign * (
            0.5 * cfg.vessel.inner_size_x_mm - routing.wall_clearance_mm
        )
        x_origin_mm = inner_face_x_mm if sign > 0.0 else inner_face_x_mm - depth_mm
        backbone = Part.makeBox(
            depth_mm,
            width_mm,
            length_mm,
            App.Vector(x_origin_mm, -0.5 * width_mm, z_min_mm),
        )
        bus_x_mm = inner_face_x_mm - sign * cartridge.thermal_bus_thickness_mm
        thermal_bus = Part.makeBox(
            cartridge.thermal_bus_thickness_mm,
            cartridge.thermal_bus_width_mm,
            length_mm,
            App.Vector(
                min(inner_face_x_mm, bus_x_mm),
                -0.5 * cartridge.thermal_bus_width_mm,
                z_min_mm,
            ),
        )
        interface_center = App.Vector(
            inner_face_x_mm + sign * depth_mm,
            0.0,
            0.5 * (z_min_mm + z_max_mm),
        )
    else:
        sign = 1.0 if sector == "up" else -1.0
        inner_face_y_mm = sign * (
            0.5 * cfg.vessel.inner_size_y_mm - routing.wall_clearance_mm
        )
        y_origin_mm = inner_face_y_mm if sign > 0.0 else inner_face_y_mm - depth_mm
        backbone = Part.makeBox(
            width_mm,
            depth_mm,
            length_mm,
            App.Vector(-0.5 * width_mm, y_origin_mm, z_min_mm),
        )
        bus_y_mm = inner_face_y_mm - sign * cartridge.thermal_bus_thickness_mm
        thermal_bus = Part.makeBox(
            cartridge.thermal_bus_width_mm,
            cartridge.thermal_bus_thickness_mm,
            length_mm,
            App.Vector(
                -0.5 * cartridge.thermal_bus_width_mm,
                min(inner_face_y_mm, bus_y_mm),
                z_min_mm,
            ),
        )
        interface_center = App.Vector(
            0.0,
            inner_face_y_mm + sign * depth_mm,
            0.5 * (z_min_mm + z_max_mm),
        )
    return backbone, thermal_bus, interface_center


def _removal_envelope(
    physical: dict[str, Part.Shape],
    sector: str,
    clearance_mm: float,
) -> Part.Shape:
    compound = Part.makeCompound(list(physical.values()))
    box = compound.BoundBox
    if sector in {"left", "right"}:
        x_min_mm = box.XMin - (clearance_mm if sector == "left" else 0.0)
        x_length_mm = box.XLength + clearance_mm
        return Part.makeBox(
            x_length_mm,
            box.YLength,
            box.ZLength,
            App.Vector(x_min_mm, box.YMin, box.ZMin),
        )
    y_min_mm = box.YMin - (clearance_mm if sector == "down" else 0.0)
    y_length_mm = box.YLength + clearance_mm
    return Part.makeBox(
        box.XLength,
        y_length_mm,
        box.ZLength,
        App.Vector(box.XMin, y_min_mm, box.ZMin),
    )


def build_sector_cartridge(
    cfg: CIVConfig,
    sector: str,
) -> SectorCartridgeGeometry:
    if cfg.compact_one is None:
        raise ValueError("sector cartridge requires a CompactOne schema-v2 configuration")
    if sector not in cfg.sectors:
        raise ValueError(f"sector {sector!r} is not configured")
    cartridge = cfg.compact_one.sector_cartridge
    cassette_spec = cfg.compact_one.detector.cassette
    routing = cfg.compact_one.services.routing
    placements = tuple(
        placement
        for placement in build_detector_placements(cfg)
        if placement.sector_name == sector
    )
    if tuple(placement.channel_name for placement in placements) != cartridge.detector_mounts:
        raise ValueError("sector cartridge detector mounts do not match configured channel order")

    physical: dict[str, Part.Shape] = {}
    interfaces: dict[str, Part.Shape] = {}
    keepouts: dict[str, Part.Shape] = {}
    datums: dict[str, Part.Shape] = {}
    materials: dict[str, str] = {}
    thermal_connections: list[tuple[str, str]] = []
    anchors: list[App.Vector] = []
    route_starts: dict[str, App.Vector] = {}

    for placement in placements:
        cassette: CassetteGeometry = build_detector_cassette(cfg, placement)
        prefix = placement.tag
        for name, shape in cassette.physical.items():
            key = f"{prefix}_{name}"
            physical[key] = shape
            materials[key] = cassette.materials.get(name, "unresolved")
        for name, shape in cassette.interfaces.items():
            interfaces[f"{prefix}_{name}"] = shape
        for name, shape in cassette.keepouts.items():
            if name == "ConnectorKeepout":
                keepouts[f"{prefix}_{name}"] = shape
        for name, shape in cassette.datums.items():
            datums[f"{prefix}_{name}"] = shape
        thermal_connections.extend(
            (f"{prefix}_{name_a}", f"{prefix}_{name_b}")
            for name_a, name_b in cassette.thermal_connections
        )

        pad = _placed_mount_pad(cfg, placement)
        pad_name = f"{prefix}_CartridgeMountPad"
        physical[pad_name] = pad
        materials[pad_name] = cassette_spec.thermal_spreader_material

        rail_start = (
            cassette_axis_position(
                placement,
                cassette_spec.mounting_datum_offset_mm + cartridge.mount_pad_mm[2],
            )
            + scaled(_sector_tangent(sector), 10.0)
        )
        anchor = _sector_wall_anchor(cfg, placement, rail_start)
        anchors.append(anchor)
        rail_name = f"{prefix}_StructuralRail"
        strap_name = f"{prefix}_ThermalStrap"
        strap = Part.makeCylinder(
            1.5,
            (anchor - rail_start).Length,
            rail_start,
            anchor - rail_start,
        )
        physical[rail_name] = _beam_between(
            rail_start,
            anchor,
            cartridge.rail_width_mm,
            cartridge.rail_thickness_mm,
        ).cut(strap)
        materials[rail_name] = "stainless_304L"
        physical[strap_name] = strap
        materials[strap_name] = cassette_spec.thermal_spreader_material
        route_starts[placement.tag] = cassette_connector_segment(cfg, placement)[1]
        thermal_connections.extend(
            (
                (f"{prefix}_LightTightShell", pad_name),
                (pad_name, strap_name),
            )
        )

    anchor_tuple = tuple(anchors)
    backbone, thermal_bus, interface_center = _backbone_shape(
        cfg,
        sector,
        anchor_tuple,
    )
    physical[f"{sector}_CartridgeBackbone"] = backbone
    physical[f"{sector}_SectorThermalBus"] = thermal_bus
    materials[f"{sector}_CartridgeBackbone"] = "stainless_304L"
    materials[f"{sector}_SectorThermalBus"] = cassette_spec.thermal_spreader_material

    for placement, anchor in zip(placements, anchors):
        strap_name = f"{placement.tag}_ThermalStrap"
        thermal_connections.append((strap_name, f"{sector}_SectorThermalBus"))

    tangent = _sector_tangent(sector)
    service_inset_mm = (
        cartridge.thermal_bus_thickness_mm
        + 0.5 * routing.cable_keepout_diameter_mm
        + 2.0
    )
    junction = (
        anchors[-1]
        + scaled(tangent, cartridge.service_lane_offset_mm)
        + scaled(_sector_inward(sector), service_inset_mm)
        + App.Vector(0.0, 0.0, cartridge.backbone_margin_mm)
    )
    cable_radius_mm = 0.5 * routing.cable_keepout_diameter_mm
    for placement, anchor in zip(placements, anchors):
        start = route_starts[placement.tag]
        lane_anchor = (
            anchor
            + scaled(tangent, cartridge.service_lane_offset_mm)
            + scaled(_sector_inward(sector), service_inset_mm)
        )
        route = Part.makeCompound(
            [
                _segment_keepout(start, lane_anchor, cable_radius_mm),
                _segment_keepout(lane_anchor, junction, cable_radius_mm),
                Part.makeSphere(cable_radius_mm, lane_anchor),
            ]
        )
        keepouts[f"{placement.tag}_SectorCableRoute"] = route

    interface_size_mm = cartridge.backbone_width_mm
    if sector in {"left", "right"}:
        mount_interface = Part.makeBox(
            0.1,
            interface_size_mm,
            interface_size_mm,
            App.Vector(
                interface_center.x - 0.05,
                interface_center.y - 0.5 * interface_size_mm,
                interface_center.z - 0.5 * interface_size_mm,
            ),
        )
    else:
        mount_interface = Part.makeBox(
            interface_size_mm,
            0.1,
            interface_size_mm,
            App.Vector(
                interface_center.x - 0.5 * interface_size_mm,
                interface_center.y - 0.05,
                interface_center.z - 0.5 * interface_size_mm,
            ),
        )
    interfaces[f"{sector}_ChamberMountInterface"] = mount_interface
    datums[f"{sector}_PrimarySurveyDatum"] = Part.makeSphere(1.0, interface_center)
    datums[f"{sector}_RadialSurveyDatum"] = Part.makeSphere(
        1.0,
        interface_center + App.Vector(0.0, 0.0, 20.0),
    )
    keepouts[f"{sector}_CartridgeRemovalEnvelope"] = _removal_envelope(
        physical,
        sector,
        cartridge.removal_clearance_mm,
    )
    thermal_connections.extend(
        (
            (
                f"{sector}_SectorThermalBus",
                f"{sector}_CartridgeBackbone",
            ),
            (
                f"{sector}_CartridgeBackbone",
                f"{sector}_ChamberMountInterface",
            ),
        )
    )
    return SectorCartridgeGeometry(
        sector=sector,
        placements=placements,
        service_junction=junction,
        physical=physical,
        interfaces=interfaces,
        keepouts=keepouts,
        datums=datums,
        materials=materials,
        thermal_connections=tuple(thermal_connections),
    )


def cartridge_compound(geometry: SectorCartridgeGeometry) -> Part.Shape:
    return Part.makeCompound(list(geometry.physical.values()))
