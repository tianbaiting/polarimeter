from __future__ import annotations

from dataclasses import dataclass
import math

import FreeCAD as App
import Part

from .config import CIVConfig
from .layout import (
    DetectorPlacement,
    detector_center,
    placement_from_direction,
    scaled,
    target_facing_active_face_center,
)


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
        raise ValueError("detector core requires a CompactOne schema-v3 configuration")
    detector = cfg.compact_one.detector
    active = detector.active
    optics = detector.optics
    sipm = detector.sipm
    head = detector.head

    active_front_z_mm = detector.front_face_offset_mm
    active_back_z_mm = active_front_z_mm + active.thickness_mm
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
        + 0.5 * head.carrier_envelope_mm[2]
    )
    carrier = _box(head.carrier_envelope_mm, carrier_center_z_mm)

    physical = {
        "ActivePlastic": active_shape,
        "ReflectorEnvelope": reflector,
        "OpticalCoupling": coupling,
        "SiPMPackage": sipm_shape,
        "SensorPCBCarrier": carrier,
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
        "SiPMPackage": "silicon_package",
        "SensorPCBCarrier": head.carrier_material,
    }
    # [EN] The SiPM package directly contacts the metallic-backed carrier; no artificial long bridge is introduced between the sensor and the rear mounting face. / [CN] SiPM 封装直接接触金属背衬载板；传感器与后安装面之间不引入人为的长导热桥。
    return DetectorCoreGeometry(
        physical=_place_shapes(physical, placement),
        interfaces=_place_shapes(interfaces, placement),
        materials=materials,
        thermal_connections=(("SiPMPackage", "SensorPCBCarrier"),),
    )


def detector_stack_metrics(cfg: CIVConfig) -> dict[str, object]:
    if cfg.compact_one is None:
        raise ValueError("detector stack metrics require a CompactOne schema-v3 configuration")
    detector = cfg.compact_one.detector
    return {
        "components_mm": {
            "active_plastic": detector.active.thickness_mm,
            "optical_coupling": detector.optics.coupling_thickness_mm,
            "sipm_package": detector.sipm.package_envelope_mm[2],
            "sensor_pcb_carrier": detector.head.carrier_envelope_mm[2],
            "rear_clearance": detector.head.rear_clearance_mm,
            "rear_cap": detector.head.rear_cap_wall_mm,
        },
        "calculated_physical_depth_mm": detector.physical_depth_mm,
        "maximum_physical_depth_mm": detector.head.maximum_physical_depth_mm,
        "front_face_offset_mm": detector.front_face_offset_mm,
        "rear_housing_offset_mm": detector.rear_housing_offset_mm,
        "housing_outer_diameter_mm": detector.housing_outer_diameter_mm,
        "excludes": (
            "CableExit",
            "ConnectorKeepout",
            "DetectorRemovalEnvelope",
        ),
    }


def active_geometry_metrics(cfg: CIVConfig) -> dict[str, float]:
    if cfg.compact_one is None:
        raise ValueError("active metrics require a CompactOne schema-v3 configuration")
    active = cfg.compact_one.detector.active
    radius_mm = 0.5 * active.diameter_mm
    return {
        "diameter_mm": active.diameter_mm,
        "thickness_mm": active.thickness_mm,
        "area_mm2": math.pi * radius_mm * radius_mm,
        "volume_mm3": math.pi * radius_mm * radius_mm * active.thickness_mm,
    }


def build_active_acceptance_cone(
    cfg: CIVConfig,
    placement: DetectorPlacement,
    radial_clearance_mm: float = 0.0,
    extend_past_active_mm: float = 0.0,
) -> Part.Shape:
    if cfg.compact_one is None:
        raise ValueError("acceptance cone requires a CompactOne schema-v3 configuration")
    active = cfg.compact_one.detector.active
    target = cfg.compact_one.target.foil
    if cfg.physics is None:
        raise ValueError("acceptance cone requires the physics beam-axis contract")
    face_center = target_facing_active_face_center(
        placement,
        active.thickness_mm,
    ) + scaled(placement.direction, extend_past_active_mm)
    length_mm = face_center.Length
    if length_mm <= 0.0:
        raise ValueError("detector active face must lie downstream of the target")
    source_center = App.Vector(*cfg.physics.target.position_mm)
    source_normal = App.Vector(*cfg.physics.beam.axis)
    source_wire = Part.Wire(
        [
            Part.makeCircle(
                0.5 * target.diameter_mm + radial_clearance_mm,
                source_center,
                source_normal,
            )
        ]
    )
    detector_wire = Part.Wire(
        [
            Part.makeCircle(
                0.5 * active.diameter_mm + radial_clearance_mm,
                face_center,
                scaled(face_center, 1.0 / length_mm),
            )
        ]
    )
    # [EN] The ruled solid joins the complete target region to the complete active disc and can be expanded for mechanical clearance cuts without changing nominal physics directions. / [CN] 该直纹实体连接完整靶区与完整灵敏圆面，并可为机械避让切口扩张，而不改变名义物理方向。
    return Part.makeLoft(
        [source_wire, detector_wire],
        True,
        True,
    )
