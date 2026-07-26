from __future__ import annotations

from dataclasses import dataclass

import FreeCAD as App
import Part

from .config import CIVConfig
from .detector import DetectorCoreGeometry, build_detector_core
from .layout import (
    DetectorPlacement,
    cassette_axis_position,
    detector_center,
    placement_from_direction,
    scaled,
)


@dataclass(frozen=True)
class CassetteGeometry:
    physical: dict[str, Part.Shape]
    interfaces: dict[str, Part.Shape]
    keepouts: dict[str, Part.Shape]
    datums: dict[str, Part.Shape]
    materials: dict[str, str]
    thermal_connections: tuple[tuple[str, str], ...]


def _place_shapes(
    shapes: dict[str, Part.Shape],
    placement: DetectorPlacement | None,
) -> dict[str, Part.Shape]:
    if placement is None:
        return shapes
    transform = placement_from_direction(detector_center(placement), placement.direction)
    placed: dict[str, Part.Shape] = {}
    for name, shape in shapes.items():
        copy = shape.copy()
        copy.Placement = transform.multiply(copy.Placement)
        placed[name] = copy
    return placed


def _cassette_shell(cfg: CIVConfig) -> Part.Shape:
    detector = cfg.compact_one.detector
    active = detector.active
    optics = detector.optics
    cassette = detector.cassette
    width_mm, height_mm, length_mm = cassette.outer_envelope_mm
    nose_width_mm, nose_height_mm, nose_length_mm = (
        cassette.front_nose_envelope_mm
    )
    front_z_mm = cassette.front_offset_from_active_center_mm
    wall_mm = cassette.shell_wall_mm
    rear_start_z_mm = front_z_mm + nose_length_mm
    rear_length_mm = length_mm - nose_length_mm
    if rear_length_mm <= wall_mm:
        raise ValueError("cassette front nose must be shorter than the outer envelope")
    if abs(nose_width_mm - nose_height_mm) > 1.0e-9:
        raise ValueError("cassette front nose must be circular in the current design")
    nose_outer = Part.makeCylinder(
        0.5 * nose_width_mm,
        nose_length_mm,
        App.Vector(0.0, 0.0, front_z_mm),
    )
    rear_outer = Part.makeBox(
        width_mm,
        height_mm,
        rear_length_mm,
        App.Vector(-0.5 * width_mm, -0.5 * height_mm, rear_start_z_mm),
    )
    outer = nose_outer.fuse(rear_outer)
    nose_cavity = Part.makeCylinder(
        0.5 * nose_width_mm - wall_mm,
        nose_length_mm,
        App.Vector(0.0, 0.0, front_z_mm + wall_mm),
    )
    rear_cavity = Part.makeBox(
        width_mm - 2.0 * wall_mm,
        height_mm - 2.0 * wall_mm,
        rear_length_mm,
        App.Vector(
            -0.5 * width_mm + wall_mm,
            -0.5 * height_mm + wall_mm,
            rear_start_z_mm - wall_mm,
        ),
    )
    shell = outer.cut(nose_cavity.fuse(rear_cavity))

    aperture_radius_mm = (
        0.5 * active.diameter_mm
        + optics.reflector_envelope_thickness_mm
        + 0.5
    )
    front_aperture = Part.makeCylinder(
        aperture_radius_mm,
        wall_mm + 0.4,
        App.Vector(0.0, 0.0, front_z_mm - 0.2),
    )
    rear_z_mm = front_z_mm + length_mm
    cable_hole = Part.makeCylinder(
        0.5 * cassette.cable_exit_diameter_mm,
        wall_mm + 0.4,
        App.Vector(0.0, 0.0, rear_z_mm - wall_mm - 0.2),
    )
    return shell.cut(front_aperture).cut(cable_hole)


def cassette_connector_segment(
    cfg: CIVConfig,
    placement: DetectorPlacement,
) -> tuple[App.Vector, App.Vector]:
    cassette = cfg.compact_one.detector.cassette
    rear_offset_mm = (
        cassette.front_offset_from_active_center_mm
        + cassette.outer_envelope_mm[2]
        + cassette.strain_relief_length_mm
    )
    start = cassette_axis_position(placement, rear_offset_mm)
    tangent = (
        App.Vector(0.0, 1.0, 0.0)
        if placement.sector_name in {"left", "right"}
        else App.Vector(1.0, 0.0, 0.0)
    )
    end = start + scaled(tangent, cassette.connector_keepout_length_mm)
    return start, end


def build_detector_cassette(
    cfg: CIVConfig,
    placement: DetectorPlacement | None = None,
) -> CassetteGeometry:
    if cfg.compact_one is None:
        raise ValueError("detector cassette requires a CompactOne schema-v2 configuration")
    detector = cfg.compact_one.detector
    cassette = detector.cassette
    core: DetectorCoreGeometry = build_detector_core(cfg)
    front_z_mm = cassette.front_offset_from_active_center_mm
    rear_z_mm = front_z_mm + cassette.outer_envelope_mm[2]

    shell = _cassette_shell(cfg)
    stop_width_mm, stop_height_mm, stop_thickness_mm = cassette.insertion_stop_mm
    stop_outer = Part.makeBox(
        stop_width_mm,
        stop_height_mm,
        stop_thickness_mm,
        App.Vector(
            -0.5 * stop_width_mm,
            -0.5 * stop_height_mm,
            cassette.insertion_stop_offset_mm - 0.5 * stop_thickness_mm,
        ),
    )
    stop_inner = Part.makeBox(
        cassette.outer_envelope_mm[0] - 0.2,
        cassette.outer_envelope_mm[1] - 0.2,
        stop_thickness_mm + 0.4,
        App.Vector(
            -0.5 * cassette.outer_envelope_mm[0] + 0.1,
            -0.5 * cassette.outer_envelope_mm[1] + 0.1,
            cassette.insertion_stop_offset_mm - 0.5 * stop_thickness_mm - 0.2,
        ),
    )
    insertion_stop = stop_outer.cut(stop_inner)

    key_width_mm, key_height_mm, key_length_mm = cassette.anti_rotation_key_mm
    if placement is not None and placement.sector_name in {"left", "right"}:
        key_origin = App.Vector(
            -0.5 * key_width_mm,
            0.5 * cassette.outer_envelope_mm[1],
            cassette.insertion_stop_offset_mm - 0.5 * key_length_mm,
        )
    else:
        key_origin = App.Vector(
            0.5 * cassette.outer_envelope_mm[0],
            -0.5 * key_height_mm,
            cassette.insertion_stop_offset_mm - 0.5 * key_length_mm,
        )
    anti_rotation_key = Part.makeBox(
        key_width_mm,
        key_height_mm,
        key_length_mm,
        key_origin,
    )
    strain_relief = Part.makeCylinder(
        0.5 * cassette.cable_exit_diameter_mm + 1.5,
        cassette.strain_relief_length_mm,
        App.Vector(0.0, 0.0, rear_z_mm),
    )
    connector_keepout = Part.makeCylinder(
        0.5 * cassette.connector_keepout_diameter_mm,
        cassette.connector_keepout_length_mm,
        App.Vector(
            0.0,
            0.0,
            rear_z_mm + cassette.strain_relief_length_mm,
        ),
    )
    mounting_datum = Part.makeBox(
        stop_width_mm,
        stop_height_mm,
        0.05,
        App.Vector(
            -0.5 * stop_width_mm,
            -0.5 * stop_height_mm,
            cassette.mounting_datum_offset_mm - 0.025,
        ),
    )
    removal_envelope = Part.makeBox(
        stop_width_mm + 4.0,
        stop_height_mm + 4.0,
        cassette.outer_envelope_mm[2] + cassette.connector_keepout_length_mm,
        App.Vector(
            -0.5 * stop_width_mm - 2.0,
            -0.5 * stop_height_mm - 2.0,
            front_z_mm,
        ),
    )

    physical = {
        **core.physical,
        "LightTightShell": shell,
        "InsertionStop": insertion_stop,
        "AntiRotationKey": anti_rotation_key,
        "CableStrainRelief": strain_relief,
    }
    interfaces = {
        **core.interfaces,
        "CassetteMountingInterface": mounting_datum,
    }
    keepouts = {
        "ConnectorKeepout": connector_keepout,
        "CassetteRemovalEnvelope": removal_envelope,
    }
    datums = {
        "ActiveCenterDatum": Part.makeSphere(0.5, App.Vector(0.0, 0.0, 0.0)),
        "MountingDatum": mounting_datum.copy(),
        "AntiRotationDatum": anti_rotation_key.copy(),
    }
    materials = {
        **core.materials,
        "LightTightShell": cassette.shell_material,
        "InsertionStop": cassette.shell_material,
        "AntiRotationKey": cassette.shell_material,
        "CableStrainRelief": "vacuum_compatible_strain_relief",
    }
    thermal_connections = (
        *core.thermal_connections,
        ("CassetteThermalBridge", "LightTightShell"),
        ("LightTightShell", "CassetteMountingInterface"),
    )
    placed_keepouts = _place_shapes(keepouts, placement)
    if placement is not None:
        connector_start, connector_end = cassette_connector_segment(cfg, placement)
        connector_delta = connector_end - connector_start
        placed_keepouts["ConnectorKeepout"] = Part.makeCylinder(
            0.5 * cassette.connector_keepout_diameter_mm,
            connector_delta.Length,
            connector_start,
            connector_delta,
        )
    return CassetteGeometry(
        physical=_place_shapes(physical, placement),
        interfaces=_place_shapes(interfaces, placement),
        keepouts=placed_keepouts,
        datums=_place_shapes(datums, placement),
        materials=materials,
        thermal_connections=thermal_connections,
    )


def cassette_compound(geometry: CassetteGeometry) -> Part.Shape:
    return Part.makeCompound(list(geometry.physical.values()))
