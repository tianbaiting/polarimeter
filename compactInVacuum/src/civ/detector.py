from __future__ import annotations

from dataclasses import dataclass
import math

import FreeCAD as App
import Part

from .config import CIVConfig
from .layout import DetectorPlacement, detector_center, placement_from_direction


@dataclass(frozen=True)
class DetectorCoreGeometry:
    physical: dict[str, Part.Shape]
    interfaces: dict[str, Part.Shape]
    materials: dict[str, str]
    thermal_connections: tuple[tuple[str, str], ...]


def _box(size: tuple[float, float, float], center_z_mm: float) -> Part.Shape:
    return Part.makeBox(
        size[0],
        size[1],
        size[2],
        App.Vector(
            -0.5 * size[0],
            -0.5 * size[1],
            center_z_mm - 0.5 * size[2],
        ),
    )


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


def build_detector_core(
    cfg: CIVConfig,
    placement: DetectorPlacement | None = None,
) -> DetectorCoreGeometry:
    if cfg.compact_one is None:
        raise ValueError("detector core requires a CompactOne schema-v2 configuration")
    detector = cfg.compact_one.detector
    active = detector.active
    optics = detector.optics
    sipm = detector.sipm
    cassette = detector.cassette

    active_front_z_mm = -0.5 * active.thickness_mm
    active_back_z_mm = 0.5 * active.thickness_mm
    active_shape = Part.makeCylinder(
        0.5 * active.diameter_mm,
        active.thickness_mm,
        App.Vector(0.0, 0.0, active_front_z_mm),
    )
    reflector_outer = Part.makeCylinder(
        0.5 * active.diameter_mm + optics.reflector_envelope_thickness_mm,
        active.thickness_mm,
        App.Vector(0.0, 0.0, active_front_z_mm),
    )
    reflector = reflector_outer.cut(active_shape)

    coupling_center_z_mm = active_back_z_mm + 0.5 * optics.coupling_thickness_mm
    coupling = _box(
        (
            sipm.active_size_mm[0],
            sipm.active_size_mm[1],
            optics.coupling_thickness_mm,
        ),
        coupling_center_z_mm,
    )
    sipm_center_z_mm = (
        active_back_z_mm
        + optics.coupling_thickness_mm
        + 0.5 * sipm.package_envelope_mm[2]
    )
    sipm_shape = _box(sipm.package_envelope_mm, sipm_center_z_mm)
    carrier_center_z_mm = (
        active_back_z_mm
        + optics.coupling_thickness_mm
        + sipm.package_envelope_mm[2]
        + 0.5 * cassette.sensor_carrier_mm[2]
    )
    carrier = _box(cassette.sensor_carrier_mm, carrier_center_z_mm)
    spreader_center_z_mm = (
        carrier_center_z_mm
        + 0.5 * cassette.sensor_carrier_mm[2]
        + 0.5 * cassette.thermal_spreader_mm[2]
    )
    spreader = _box(cassette.thermal_spreader_mm, spreader_center_z_mm)

    bridge_start_z_mm = spreader_center_z_mm + 0.5 * cassette.thermal_spreader_mm[2]
    bridge_end_z_mm = (
        cassette.front_offset_from_active_center_mm
        + cassette.outer_envelope_mm[2]
        - cassette.shell_wall_mm
    )
    bridge_length_mm = bridge_end_z_mm - bridge_start_z_mm
    if bridge_length_mm <= 0.0:
        raise ValueError("cassette mounting datum must lie behind the thermal spreader")
    thermal_bridge = Part.makeBox(
        8.0,
        2.0,
        bridge_length_mm,
        App.Vector(-4.0, -1.0, bridge_start_z_mm),
    )

    temperature_sensor = Part.makeBox(
        3.0,
        2.0,
        1.0,
        App.Vector(
            0.5 * cassette.sensor_carrier_mm[0] - 3.0,
            -1.0,
            carrier_center_z_mm - 0.5,
        ),
    )
    physical = {
        "ActivePlastic": active_shape,
        "ReflectorEnvelope": reflector,
        "OpticalCoupling": coupling,
        "SiPM": sipm_shape,
        "SensorCarrier": carrier,
        "ThermalSpreader": spreader,
        "CassetteThermalBridge": thermal_bridge,
        "TemperatureSensor": temperature_sensor,
    }
    interface_disc = Part.makeCylinder(
        0.5 * active.diameter_mm,
        0.05,
        App.Vector(0.0, 0.0, active_front_z_mm - 0.05),
    )
    interfaces = {"ActiveEntranceDatum": interface_disc}
    materials = {
        "ActivePlastic": active.material,
        "ReflectorEnvelope": optics.reflector,
        "OpticalCoupling": optics.coupling,
        "SiPM": "silicon_package",
        "SensorCarrier": cassette.sensor_carrier_material,
        "ThermalSpreader": cassette.thermal_spreader_material,
        "CassetteThermalBridge": cassette.thermal_spreader_material,
        "TemperatureSensor": cassette.temperature_sensor,
    }
    return DetectorCoreGeometry(
        physical=_place_shapes(physical, placement),
        interfaces=_place_shapes(interfaces, placement),
        materials=materials,
        thermal_connections=(
            ("SiPM", "SensorCarrier"),
            ("SensorCarrier", "ThermalSpreader"),
            ("ThermalSpreader", "CassetteThermalBridge"),
        ),
    )


def active_geometry_metrics(cfg: CIVConfig) -> dict[str, float]:
    if cfg.compact_one is None:
        raise ValueError("active metrics require a CompactOne schema-v2 configuration")
    active = cfg.compact_one.detector.active
    radius_mm = 0.5 * active.diameter_mm
    return {
        "diameter_mm": active.diameter_mm,
        "thickness_mm": active.thickness_mm,
        "area_mm2": math.pi * radius_mm * radius_mm,
        "volume_mm3": math.pi * radius_mm * radius_mm * active.thickness_mm,
    }
