from __future__ import annotations

from dataclasses import dataclass
import math

import FreeCAD as App
import Part

from .config import CIVConfig
from .platform import MaintenanceAccessFlangeSpec


@dataclass(frozen=True)
class MaintenanceAccessBoundaryGeometry:
    body_cut: Part.Shape
    vacuum_extension: Part.Shape


def annular_tube(
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    length_mm: float,
    base: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    outer = Part.makeCylinder(0.5 * outer_diameter_mm, length_mm, base, axis)
    inner = Part.makeCylinder(
        0.5 * inner_diameter_mm,
        length_mm + 0.4,
        base - axis * 0.2,
        axis,
    )
    return outer.cut(inner)


def _bolt_hole_centers(
    spec: MaintenanceAccessFlangeSpec,
    y_mm: float,
) -> tuple[App.Vector, ...]:
    radius_mm = 0.5 * spec.bolt_circle_diameter_mm
    return tuple(
        App.Vector(
            spec.center_x_mm
            + radius_mm * math.cos(2.0 * math.pi * index / spec.bolt_count),
            y_mm,
            spec.center_z_mm
            + radius_mm * math.sin(2.0 * math.pi * index / spec.bolt_count),
        )
        for index in range(spec.bolt_count)
    )


def _icf_flange_shape(
    spec: MaintenanceAccessFlangeSpec,
    base_y_mm: float,
    *,
    blank: bool,
) -> Part.Shape:
    axis = App.Vector(0.0, 1.0, 0.0)
    base = App.Vector(spec.center_x_mm, base_y_mm, spec.center_z_mm)
    flange = Part.makeCylinder(
        0.5 * spec.flange_outer_diameter_mm,
        spec.flange_thickness_mm,
        base,
        axis,
    )
    if not blank:
        bore = Part.makeCylinder(
            0.5 * spec.clear_bore_diameter_mm,
            spec.flange_thickness_mm + 0.4,
            base - App.Vector(0.0, 0.2, 0.0),
            axis,
        )
        counterbore = Part.makeCylinder(
            0.5 * spec.counterbore_diameter_mm,
            spec.counterbore_depth_mm + 0.2,
            base - App.Vector(0.0, 0.1, 0.0),
            axis,
        )
        flange = flange.cut(bore).cut(counterbore)
    # [EN] Explicit holes keep the purchased ICF envelope auditable without claiming fabrication-ready knife-edge detail. / [CN] 显式孔阵列使采购 ICF 包络可审计，但不声称已具备可制造的刀口细节。
    for center in _bolt_hole_centers(spec, base_y_mm - 0.2):
        hole = Part.makeCylinder(
            0.5 * spec.bolt_hole_diameter_mm,
            spec.flange_thickness_mm + 0.4,
            center,
            axis,
        )
        flange = flange.cut(hole)
    return flange


def build_maintenance_access_boundary(
    cfg: CIVConfig,
) -> MaintenanceAccessBoundaryGeometry | None:
    access = cfg.compact_one.deployment.maintenance_access
    if access is None or not access.enabled:
        return None
    spec = access.selected
    candidate = cfg.compact_one.deployment.chamber
    inner_y_mm = 0.5 * candidate.inner_size_y_mm
    outer_y_mm = inner_y_mm + candidate.wall_thickness_mm
    seal_plane_y_mm = (
        outer_y_mm
        + spec.weld_neck_length_mm
        + spec.flange_thickness_mm
        + spec.gasket_thickness_mm
    )
    body_cut = Part.makeCylinder(
        0.5 * spec.clear_bore_diameter_mm,
        candidate.wall_thickness_mm + 0.4,
        App.Vector(spec.center_x_mm, inner_y_mm - 0.2, spec.center_z_mm),
        App.Vector(0.0, 1.0, 0.0),
    )
    vacuum_extension = Part.makeCylinder(
        0.5 * spec.clear_bore_diameter_mm,
        seal_plane_y_mm - inner_y_mm + 0.2,
        App.Vector(spec.center_x_mm, inner_y_mm - 0.2, spec.center_z_mm),
        App.Vector(0.0, 1.0, 0.0),
    )
    # [EN] Cutting overtravel and vacuum extent are separate so the vacuum stops exactly at the blank seal plane. / [CN] 切孔余量与真空体范围分离，使真空精确终止于盲板密封面。
    return MaintenanceAccessBoundaryGeometry(
        body_cut=body_cut,
        vacuum_extension=vacuum_extension,
    )


def build_maintenance_access_components(
    cfg: CIVConfig,
) -> tuple[
    dict[str, Part.Shape],
    dict[str, Part.Shape],
    dict[str, Part.Shape],
    dict[str, Part.Shape],
    dict[str, str],
]:
    access = cfg.compact_one.deployment.maintenance_access
    if access is None or not access.enabled:
        return {}, {}, {}, {}, {}
    spec = access.selected
    candidate = cfg.compact_one.deployment.chamber
    outer_y_mm = 0.5 * candidate.inner_size_y_mm + candidate.wall_thickness_mm
    axis = App.Vector(0.0, 1.0, 0.0)
    center = App.Vector(spec.center_x_mm, outer_y_mm, spec.center_z_mm)
    neck = annular_tube(
        spec.pipe_outer_diameter_mm,
        spec.clear_bore_diameter_mm,
        spec.weld_neck_length_mm,
        center,
        axis,
    )
    fixed_base_y_mm = outer_y_mm + spec.weld_neck_length_mm
    weld_bead = annular_tube(
        spec.counterbore_diameter_mm + 4.0,
        max(spec.clear_bore_diameter_mm, spec.pipe_outer_diameter_mm - 2.0),
        3.0,
        App.Vector(spec.center_x_mm, fixed_base_y_mm - 1.5, spec.center_z_mm),
        axis,
    )
    gasket_base_y_mm = fixed_base_y_mm + spec.flange_thickness_mm
    blank_base_y_mm = gasket_base_y_mm + spec.gasket_thickness_mm
    fixed_flange = _icf_flange_shape(spec, fixed_base_y_mm, blank=False)
    blank_flange = _icf_flange_shape(spec, blank_base_y_mm, blank=True)
    gasket = annular_tube(
        spec.gasket_outer_diameter_mm,
        spec.gasket_inner_diameter_mm,
        spec.gasket_thickness_mm,
        App.Vector(spec.center_x_mm, gasket_base_y_mm, spec.center_z_mm),
        axis,
    )
    inner_y_mm = 0.5 * candidate.inner_size_y_mm
    open_envelope = Part.makeCylinder(
        0.5 * spec.clear_bore_diameter_mm,
        (
            candidate.wall_thickness_mm
            + spec.weld_neck_length_mm
            + 2.0 * spec.flange_thickness_mm
            + spec.gasket_thickness_mm
            + 100.0
        ),
        App.Vector(spec.center_x_mm, inner_y_mm, spec.center_z_mm),
        axis,
    )
    internal_lift_corridor = Part.makeCylinder(
        0.5 * spec.clear_bore_diameter_mm,
        blank_base_y_mm,
        App.Vector(spec.center_x_mm, 0.0, spec.center_z_mm),
        axis,
    )
    blind_removal = Part.makeCylinder(
        0.5 * spec.flange_outer_diameter_mm,
        spec.flange_thickness_mm + 100.0,
        App.Vector(spec.center_x_mm, blank_base_y_mm, spec.center_z_mm),
        axis,
    )
    return (
        {
            "MaintenanceAccessProjectWeldNeck": neck,
            "MaintenanceAccessProjectWeldBead": weld_bead,
        },
        {
            "MaintenanceAccessFixedICFFlange": fixed_flange,
            "MaintenanceAccessCopperGasket": gasket,
            "MaintenanceAccessBlindFlange": blank_flange,
        },
        {
            "MaintenanceAccessOpenPassage": open_envelope,
            "MaintenanceAccessInternalLiftCorridor": internal_lift_corridor,
            "MaintenanceAccessBlindRemovalEnvelope": blind_removal,
        },
        {
            "MaintenanceAccessSealPlaneDatum": Part.makeSphere(
                0.75,
                App.Vector(spec.center_x_mm, blank_base_y_mm, spec.center_z_mm),
            )
        },
        {
            "MaintenanceAccessProjectWeldNeck": candidate.material,
            "MaintenanceAccessProjectWeldBead": candidate.material,
        },
    )
