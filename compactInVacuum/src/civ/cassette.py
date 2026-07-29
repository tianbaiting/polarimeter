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
)


@dataclass(frozen=True)
class DetectorHeadGeometry:
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


def _light_tight_sleeve(cfg: CIVConfig) -> Part.Shape:
    detector = cfg.compact_one.detector
    head = detector.head
    front_z_mm = detector.front_face_offset_mm
    cap_start_z_mm = detector.rear_housing_offset_mm - head.rear_cap_wall_mm
    sleeve_depth_mm = cap_start_z_mm - front_z_mm
    inner_radius_mm = (
        0.5 * detector.active.diameter_mm
        + detector.optics.reflector_envelope_thickness_mm
        + head.housing_radial_clearance_mm
    )
    outer_radius_mm = inner_radius_mm + head.shell_wall_mm
    outer = Part.makeCylinder(
        outer_radius_mm,
        sleeve_depth_mm,
        App.Vector(0.0, 0.0, front_z_mm),
    )
    cavity = Part.makeCylinder(
        inner_radius_mm,
        sleeve_depth_mm + 0.2,
        App.Vector(0.0, 0.0, front_z_mm - 0.1),
    )
    return outer.cut(cavity)


def detector_connector_segment(
    cfg: CIVConfig,
    placement: DetectorPlacement,
) -> tuple[App.Vector, App.Vector]:
    detector = cfg.compact_one.detector
    head = detector.head
    start_offset_mm = detector.rear_housing_offset_mm + head.cable_exit_length_mm
    end_offset_mm = start_offset_mm + head.connector_keepout_length_mm
    return (
        cassette_axis_position(placement, start_offset_mm),
        cassette_axis_position(placement, end_offset_mm),
    )


def _local_detector_removal_envelope(cfg: CIVConfig) -> Part.Shape:
    detector = cfg.compact_one.detector
    head = detector.head
    front_z_mm = detector.front_face_offset_mm
    rear_z_mm = detector.rear_housing_offset_mm
    flange_start_z_mm = rear_z_mm - head.rear_cap_wall_mm
    sleeve_radius_mm = 0.5 * detector.housing_outer_diameter_mm
    radial_clearance_mm = cfg.compact_one.sector_holder.nest_clearance_mm
    sleeve_sweep = Part.makeCylinder(
        sleeve_radius_mm + radial_clearance_mm,
        rear_z_mm - front_z_mm + head.detector_removal_clearance_mm,
        App.Vector(0.0, 0.0, front_z_mm),
    )
    flange_sweep = Part.makeCylinder(
        0.5 * head.mounting_flange_diameter_mm + radial_clearance_mm,
        head.rear_cap_wall_mm + head.detector_removal_clearance_mm,
        App.Vector(0.0, 0.0, flange_start_z_mm),
    )
    flat_x_mm = (
        0.5 * head.mounting_flange_diameter_mm
        - head.anti_rotation_flat_depth_mm
    )
    flat_relief = Part.makeBox(
        head.anti_rotation_flat_depth_mm + radial_clearance_mm + 1.0,
        head.mounting_flange_diameter_mm + 2.0,
        head.rear_cap_wall_mm + head.detector_removal_clearance_mm + 0.4,
        App.Vector(
            flat_x_mm,
            -0.5 * head.mounting_flange_diameter_mm - 1.0,
            flange_start_z_mm - 0.2,
        ),
    )
    flange_sweep = flange_sweep.cut(flat_relief)
    return Part.makeCompound([sleeve_sweep, flange_sweep])


def build_detector_head(
    cfg: CIVConfig,
    placement: DetectorPlacement | None = None,
) -> DetectorHeadGeometry:
    if cfg.compact_one is None:
        raise ValueError("detector head requires a CompactOne schema-v3 configuration")
    detector = cfg.compact_one.detector
    head = detector.head
    core: DetectorCoreGeometry = build_detector_core(cfg)
    rear_z_mm = detector.rear_housing_offset_mm
    cap_start_z_mm = rear_z_mm - head.rear_cap_wall_mm

    sleeve = _light_tight_sleeve(cfg)
    rear_face = Part.makeCylinder(
        0.5 * head.mounting_flange_diameter_mm,
        head.rear_cap_wall_mm,
        App.Vector(0.0, 0.0, cap_start_z_mm),
    )
    cable_bore = Part.makeCylinder(
        0.5 * head.cable_exit_diameter_mm + 0.2,
        head.rear_cap_wall_mm + 0.4,
        App.Vector(0.0, 0.0, cap_start_z_mm - 0.2),
    )
    rear_face = rear_face.cut(cable_bore)

    flange_radius_mm = 0.5 * head.mounting_flange_diameter_mm
    flat_depth_mm = head.anti_rotation_flat_depth_mm
    flat_cut = Part.makeBox(
        flat_depth_mm + 0.5,
        head.mounting_flange_diameter_mm + 1.0,
        head.rear_cap_wall_mm + 0.4,
        App.Vector(
            flange_radius_mm - flat_depth_mm,
            -flange_radius_mm - 0.5,
            cap_start_z_mm - 0.2,
        ),
    )
    rear_face = rear_face.cut(flat_cut)
    anti_rotation_flat = Part.makeBox(
        0.05,
        2.0
        * (
            flange_radius_mm * flange_radius_mm
            - (flange_radius_mm - flat_depth_mm) ** 2
        )
        ** 0.5,
        head.rear_cap_wall_mm,
        App.Vector(
            flange_radius_mm - flat_depth_mm - 0.025,
            -(
                flange_radius_mm * flange_radius_mm
                - (flange_radius_mm - flat_depth_mm) ** 2
            )
            ** 0.5,
            cap_start_z_mm,
        ),
    )
    cable_exit = Part.makeCylinder(
        0.5 * head.cable_exit_diameter_mm,
        head.cable_exit_length_mm,
        App.Vector(0.0, 0.0, rear_z_mm),
    )
    connector_keepout = Part.makeCylinder(
        0.5 * head.connector_keepout_diameter_mm,
        head.connector_keepout_length_mm,
        App.Vector(0.0, 0.0, rear_z_mm + head.cable_exit_length_mm),
    )
    mounting_datum = Part.makeCylinder(
        0.5 * head.mounting_flange_diameter_mm,
        0.05,
        App.Vector(0.0, 0.0, rear_z_mm - 0.025),
    )

    physical = {
        **core.physical,
        "LightTightSleeve": sleeve,
        "RearMountingFace": rear_face,
        "CableExit": cable_exit,
    }
    interfaces = {
        **core.interfaces,
        "RearMountingInterface": mounting_datum,
    }
    keepouts = {
        "ConnectorKeepout": connector_keepout,
        "DetectorRemovalEnvelope": _local_detector_removal_envelope(cfg),
    }
    datums = {
        "ActiveCenterDatum": Part.makeSphere(0.5, App.Vector(0.0, 0.0, 0.0)),
        "RearMountingPlaneDatum": mounting_datum.copy(),
        "AntiRotationFlatDatum": anti_rotation_flat,
    }
    materials = {
        **core.materials,
        "LightTightSleeve": head.shell_material,
        "RearMountingFace": head.carrier_material,
        "CableExit": "vacuum_compatible_cable_exit_provisional",
    }
    thermal_connections = (
        *core.thermal_connections,
        ("SensorPCBCarrier", "RearMountingFace"),
    )
    placed_keepouts = _place_shapes(keepouts, placement)
    if placement is not None:
        connector_start, connector_end = detector_connector_segment(cfg, placement)
        connector_delta = connector_end - connector_start
        placed_keepouts["ConnectorKeepout"] = Part.makeCylinder(
            0.5 * head.connector_keepout_diameter_mm,
            connector_delta.Length,
            connector_start,
            connector_delta,
        )
    # [EN] The rear mounting face is the insertion stop and conductive datum; the cable exit remains a separately reported service part outside the housing-depth gate. / [CN] 后安装面同时作为插入止挡和导电基准；电缆出口作为独立服务部件报告，不计入壳体深度门限。
    return DetectorHeadGeometry(
        physical=_place_shapes(physical, placement),
        interfaces=_place_shapes(interfaces, placement),
        keepouts=placed_keepouts,
        datums=_place_shapes(datums, placement),
        materials=materials,
        thermal_connections=thermal_connections,
    )


def detector_head_compound(geometry: DetectorHeadGeometry) -> Part.Shape:
    return Part.makeCompound(list(geometry.physical.values()))
