from __future__ import annotations

from dataclasses import dataclass
import math

import FreeCAD as App
import Part

from .access import (
    annular_tube,
    build_maintenance_access_boundary,
    build_maintenance_access_components,
)
from .config import CIVConfig
from .feedthrough import service_wall_y_mm
from .platform import (
    ChamberCandidateSpec,
    PurchasedBeamInterfaceSpec,
)


@dataclass(frozen=True)
class ChamberCandidateMetrics:
    name: str
    cross_section: str
    status: str
    internal_envelope_mm: tuple[float, float, float]
    internal_volume_mm3: float
    material_volume_screening_mm3: float
    approximate_mass_screening_kg: float
    service_accessibility: str
    service_plate_concept: str
    wall_thickness_mm: float
    wall_thickness_status: str


@dataclass(frozen=True)
class ChamberGeometry:
    candidate: ChamberCandidateSpec
    physical: dict[str, Part.Shape]
    purchased_interfaces: dict[str, Part.Shape]
    keepouts: dict[str, Part.Shape]
    datums: dict[str, Part.Shape]
    materials: dict[str, str]
    vacuum_control_volume: Part.Shape
    metrics: ChamberCandidateMetrics


def screen_chamber_candidate(
    candidate: ChamberCandidateSpec,
    density_g_per_cm3: float = 7.90,
) -> ChamberCandidateMetrics:
    wall_mm = candidate.wall_thickness_mm
    internal_length_mm = candidate.length_mm - 2.0 * wall_mm
    if internal_length_mm <= 0.0:
        raise ValueError("chamber length must exceed twice the wall thickness")
    if candidate.cross_section == "cylindrical":
        if not math.isclose(
            candidate.inner_size_x_mm,
            candidate.inner_size_y_mm,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        ):
            raise ValueError("current cylindrical screening requires a circular section")
        inner_radius_mm = 0.5 * candidate.inner_size_x_mm
        outer_radius_mm = inner_radius_mm + wall_mm
        internal_volume_mm3 = (
            math.pi * inner_radius_mm * inner_radius_mm * internal_length_mm
        )
        material_volume_mm3 = (
            math.pi
            * outer_radius_mm
            * outer_radius_mm
            * candidate.length_mm
            - internal_volume_mm3
        )
    elif candidate.cross_section == "square":
        internal_volume_mm3 = (
            candidate.inner_size_x_mm
            * candidate.inner_size_y_mm
            * internal_length_mm
        )
        material_volume_mm3 = (
            (candidate.inner_size_x_mm + 2.0 * wall_mm)
            * (candidate.inner_size_y_mm + 2.0 * wall_mm)
            * candidate.length_mm
            - internal_volume_mm3
        )
    else:
        raise ValueError(f"unsupported chamber cross section: {candidate.cross_section}")
    return ChamberCandidateMetrics(
        name=candidate.name,
        cross_section=candidate.cross_section,
        status=candidate.status,
        internal_envelope_mm=(
            candidate.inner_size_x_mm,
            candidate.inner_size_y_mm,
            internal_length_mm,
        ),
        internal_volume_mm3=internal_volume_mm3,
        material_volume_screening_mm3=material_volume_mm3,
        approximate_mass_screening_kg=(
            material_volume_mm3 * density_g_per_cm3 / 1.0e6
        ),
        service_accessibility=candidate.service_accessibility,
        service_plate_concept=candidate.service_plate_concept,
        wall_thickness_mm=wall_mm,
        wall_thickness_status=candidate.wall_thickness_status,
    )


def _beam_interface_envelope(
    interface: PurchasedBeamInterfaceSpec,
    base: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    return Part.makeCylinder(
        0.5 * interface.module_outer_diameter_mm,
        interface.module_thickness_mm,
        base,
        axis,
    )


def _selected_body_and_vacuum(cfg: CIVConfig) -> tuple[Part.Shape, Part.Shape]:
    candidate = cfg.compact_one.deployment.chamber
    wall_mm = candidate.wall_thickness_mm
    z_min_mm = candidate.center_z_mm - 0.5 * candidate.length_mm
    z_max_mm = candidate.center_z_mm + 0.5 * candidate.length_mm
    internal_z_min_mm = z_min_mm + wall_mm
    internal_length_mm = candidate.length_mm - 2.0 * wall_mm
    if candidate.cross_section == "cylindrical":
        inner_radius_mm = 0.5 * candidate.inner_size_x_mm
        outer = Part.makeCylinder(
            inner_radius_mm + wall_mm,
            candidate.length_mm,
            App.Vector(0.0, 0.0, z_min_mm),
        )
        cavity = Part.makeCylinder(
            inner_radius_mm,
            internal_length_mm,
            App.Vector(0.0, 0.0, internal_z_min_mm),
        )
    else:
        outer = Part.makeBox(
            candidate.inner_size_x_mm + 2.0 * wall_mm,
            candidate.inner_size_y_mm + 2.0 * wall_mm,
            candidate.length_mm,
            App.Vector(
                -0.5 * candidate.inner_size_x_mm - wall_mm,
                -0.5 * candidate.inner_size_y_mm - wall_mm,
                z_min_mm,
            ),
        )
        cavity = Part.makeBox(
            candidate.inner_size_x_mm,
            candidate.inner_size_y_mm,
            internal_length_mm,
            App.Vector(
                -0.5 * candidate.inner_size_x_mm,
                -0.5 * candidate.inner_size_y_mm,
                internal_z_min_mm,
            ),
        )
    body = outer.cut(cavity)
    vacuum = cavity

    deployment = cfg.compact_one.deployment
    front = deployment.front_interface
    rear = deployment.rear_interface
    beam_bore_mm = min(
        front.nominal_clear_bore_mm,
        rear.nominal_clear_bore_mm,
        front.transition_inner_diameter_mm,
        rear.transition_inner_diameter_mm,
    )
    front_bore = Part.makeCylinder(
        0.5 * beam_bore_mm,
        wall_mm + front.transition_length_mm,
        App.Vector(0.0, 0.0, z_min_mm - front.transition_length_mm),
    )
    rear_bore = Part.makeCylinder(
        0.5 * beam_bore_mm,
        wall_mm + rear.transition_length_mm,
        App.Vector(0.0, 0.0, z_max_mm - wall_mm),
    )
    body = body.cut(front_bore).cut(rear_bore)
    vacuum = vacuum.fuse(front_bore).fuse(rear_bore)

    access_boundary = build_maintenance_access_boundary(cfg)
    if access_boundary is not None:
        body = body.cut(access_boundary.body_cut)
        vacuum = vacuum.fuse(access_boundary.vacuum_extension)

    for port in deployment.service_ports:
        wall_center = App.Vector(
            port.center_x_mm,
            service_wall_y_mm(cfg, port.center_x_mm),
            port.center_z_mm,
        )
        bore = Part.makeCylinder(
            0.5 * port.bore_diameter_mm,
            port.collar_length_mm + 2.0 * wall_mm + 0.4,
            wall_center - App.Vector(0.0, wall_mm + 0.2, 0.0),
            App.Vector(0.0, 1.0, 0.0),
        )
        body = body.cut(bore)
        vacuum = vacuum.fuse(bore)
    return body, vacuum


def build_chamber(cfg: CIVConfig) -> ChamberGeometry:
    if cfg.compact_one is None:
        raise ValueError("chamber geometry requires a CompactOne schema-v3 configuration")
    candidate = cfg.compact_one.deployment.chamber
    deployment = cfg.compact_one.deployment
    body, vacuum = _selected_body_and_vacuum(cfg)
    z_min_mm = candidate.center_z_mm - 0.5 * candidate.length_mm
    z_max_mm = candidate.center_z_mm + 0.5 * candidate.length_mm
    front_transition = annular_tube(
        deployment.front_interface.transition_outer_diameter_mm,
        deployment.front_interface.transition_inner_diameter_mm,
        deployment.front_interface.transition_length_mm,
        App.Vector(
            0.0,
            0.0,
            z_min_mm - deployment.front_interface.transition_length_mm,
        ),
        App.Vector(0.0, 0.0, 1.0),
    )
    rear_transition = annular_tube(
        deployment.rear_interface.transition_outer_diameter_mm,
        deployment.rear_interface.transition_inner_diameter_mm,
        deployment.rear_interface.transition_length_mm,
        App.Vector(0.0, 0.0, z_max_mm),
        App.Vector(0.0, 0.0, 1.0),
    )
    physical = {
        "ProjectChamberBody": body,
        "FrontProjectWeldTransition": front_transition,
        "RearProjectWeldTransition": rear_transition,
    }
    (
        access_physical,
        access_purchased,
        access_keepouts,
        access_datums,
        access_materials,
    ) = build_maintenance_access_components(cfg)
    physical.update(access_physical)
    front_interface_base = App.Vector(
        0.0,
        0.0,
        z_min_mm
        - deployment.front_interface.transition_length_mm
        - deployment.front_interface.module_thickness_mm,
    )
    rear_interface_base = App.Vector(
        0.0,
        0.0,
        z_max_mm + deployment.rear_interface.transition_length_mm,
    )
    purchased = {
        "FrontPurchasedBeamInterface": _beam_interface_envelope(
            deployment.front_interface,
            front_interface_base,
            App.Vector(0.0, 0.0, 1.0),
        ),
        "RearPurchasedBeamInterface": _beam_interface_envelope(
            deployment.rear_interface,
            rear_interface_base,
            App.Vector(0.0, 0.0, 1.0),
        ),
    }
    purchased.update(access_purchased)
    beam_clear_diameter_mm = deployment.beam_stay_clear_diameter_mm
    beam_keepout = Part.makeCylinder(
        0.5 * beam_clear_diameter_mm,
        (
            candidate.length_mm
            + deployment.front_interface.transition_length_mm
            + deployment.rear_interface.transition_length_mm
        ),
        App.Vector(
            0.0,
            0.0,
            z_min_mm - deployment.front_interface.transition_length_mm,
        ),
    )
    return ChamberGeometry(
        candidate=candidate,
        physical=physical,
        purchased_interfaces=purchased,
        keepouts={"BeamStayClear": beam_keepout, **access_keepouts},
        datums={
            "BeamAxisDatum": Part.makeLine(
                App.Vector(0.0, 0.0, z_min_mm),
                App.Vector(0.0, 0.0, z_max_mm),
            ),
            "TargetCenterDatum": Part.makeSphere(0.75, App.Vector(0.0, 0.0, 0.0)),
            **access_datums,
        },
        materials={
            **{name: candidate.material for name in physical},
            **access_materials,
        },
        vacuum_control_volume=vacuum,
        metrics=screen_chamber_candidate(candidate),
    )
