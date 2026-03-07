from __future__ import annotations

from dataclasses import dataclass

import FreeCAD as App
import Part

from .components import (
    build_all_plates,
    build_chamber,
    build_detector_fixture,
    build_end_module_fasteners,
    build_end_modules,
    build_plate_load_ties,
    build_ports,
    build_stand,
    build_target_holders,
    build_target_ladder,
)
from .config import BuildConfig
from .layout import DetectorPlacement, build_detector_placements
from .primitives import add_feature


@dataclass
class BuildResult:
    document: App.Document
    export_objects: list[App.DocumentObject]
    placements: list[DetectorPlacement]


def _set_string_property(obj: App.DocumentObject, prop: str, group: str, value: str) -> None:
    if not hasattr(obj, prop):
        obj.addProperty("App::PropertyString", prop, group)
    setattr(obj, prop, value)


def _set_float_property(obj: App.DocumentObject, prop: str, group: str, value: float) -> None:
    if not hasattr(obj, prop):
        obj.addProperty("App::PropertyFloat", prop, group)
    setattr(obj, prop, value)


def _register_object(
    assembly_group: App.DocumentObjectGroup,
    export_objects: list[App.DocumentObject],
    obj: App.DocumentObject,
) -> None:
    assembly_group.addObject(obj)
    export_objects.append(obj)


def _attach_layout_properties(obj: App.DocumentObject, placement: DetectorPlacement) -> None:
    _set_float_property(obj, "AngleDeg", "Layout", placement.angle_deg)
    _set_float_property(obj, "RadiusMM", "Layout", placement.radius_mm)
    _set_string_property(obj, "Sector", "Layout", placement.sector_name)
    _set_string_property(obj, "Channel", "Layout", placement.channel_name)
    _set_string_property(obj, "Confidence", "Layout", placement.confidence)


def _attach_plate_pose_properties(obj: App.DocumentObject, *, orientation: str, mount_plane: str) -> None:
    _set_string_property(obj, "PoseType", "Layout", orientation)
    _set_string_property(obj, "MountPlane", "Layout", mount_plane)


def _add_component(
    doc: App.Document,
    assembly: App.DocumentObjectGroup,
    export_objects: list[App.DocumentObject],
    name: str,
    shape: Part.Shape,
    subsystem: str,
    role: str,
) -> App.DocumentObject:
    obj = add_feature(doc, name, shape)
    _set_string_property(obj, "Subsystem", "Design", subsystem)
    _set_string_property(obj, "Role", "Design", role)
    _register_object(assembly, export_objects, obj)
    return obj


def build_document(cfg: BuildConfig, doc_name: str = "infrontofSamuraiMag") -> BuildResult:
    doc = App.newDocument(doc_name)
    assembly = doc.addObject("App::DocumentObjectGroup", "InfrontOfSamuraiMagAssembly")
    export_objects: list[App.DocumentObject] = []

    placements = build_detector_placements(cfg.layout)

    chamber_obj = _add_component(
        doc,
        assembly,
        export_objects,
        "TargetChamberBody",
        build_chamber(cfg.geometry, placements=placements),
        subsystem="chamber",
        role="rectangular vacuum chamber without detector signal feedthrough",
    )
    _set_string_property(chamber_obj, "BeamAxis", "Design", cfg.geometry.beamline.axis)

    front_module, rear_module = build_end_modules(cfg.geometry, placements=placements)
    front_module_obj = _add_component(
        doc,
        assembly,
        export_objects,
        "FrontEndModule_VG150",
        front_module,
        subsystem="chamber",
        role="replaceable upstream interface module",
    )
    rear_module_obj = _add_component(
        doc,
        assembly,
        export_objects,
        "RearEndModule_VF150",
        rear_module,
        subsystem="chamber",
        role="replaceable downstream interface module",
    )
    _set_string_property(front_module_obj, "Standard", "Interface", cfg.geometry.chamber.end_modules.front_standard)
    _set_string_property(rear_module_obj, "Standard", "Interface", cfg.geometry.chamber.end_modules.rear_standard)

    for name, shape in build_end_module_fasteners(cfg.geometry).items():
        _add_component(
            doc,
            assembly,
            export_objects,
            name,
            shape,
            subsystem="chamber",
            role="replaceable interface fastening hardware",
        )

    for name, shape in build_ports(cfg.geometry).items():
        _add_component(
            doc,
            assembly,
            export_objects,
            name,
            shape,
            subsystem="chamber",
            role="fixed vacuum interface port",
        )

    plate_cfg_map = {
        "HPlate": cfg.geometry.plate.h,
        "VPlate1": cfg.geometry.plate.v1,
        "VPlate2": cfg.geometry.plate.v2,
    }
    for name, shape in build_all_plates(cfg.geometry, placements=placements).items():
        plate_obj = _add_component(
            doc,
            assembly,
            export_objects,
            name,
            shape,
            subsystem="plates",
            role="load-bearing HVV plate with lugs/bolt pattern/stiffeners and annular-sector LOS opening",
        )
        plate_cfg = plate_cfg_map[name]
        _attach_plate_pose_properties(
            plate_obj,
            orientation=plate_cfg.orientation,
            mount_plane=plate_cfg.mount_plane,
        )

    for name, shape in build_plate_load_ties(cfg.geometry).items():
        role = "plate-to-stand load transfer tie"
        if "TopCap_" in name or "BottomCap_" in name:
            role = "plate-to-stand tie clamp cap"
        elif "TieBolt_" in name:
            role = "plate-to-stand tie bolt"
        elif "TieColumn_" in name:
            role = "plate-to-stand tie column"
        _add_component(
            doc,
            assembly,
            export_objects,
            name,
            shape,
            subsystem="plates",
            role=role,
        )

    for placement in placements:
        tag = placement.tag
        housing, clamp_a, clamp_b, adapter_block, mount_base = build_detector_fixture(
            cfg.geometry,
            placement,
        )

        housing_obj = _add_component(
            doc,
            assembly,
            export_objects,
            f"DetectorHousing_{tag}",
            housing,
            subsystem="detector",
            role="external detector body",
        )
        clamp_a_obj = _add_component(
            doc,
            assembly,
            export_objects,
            f"DetectorClampHalfA_{tag}",
            clamp_a,
            subsystem="detector",
            role="split clamp half A with anti-rotation shoulder/key and clamp-bolt ear",
        )
        clamp_b_obj = _add_component(
            doc,
            assembly,
            export_objects,
            f"DetectorClampHalfB_{tag}",
            clamp_b,
            subsystem="detector",
            role="split clamp half B with end-stop and clamp-bolt ear",
        )
        adapter_obj = _add_component(
            doc,
            assembly,
            export_objects,
            f"DetectorAdapterBlock_{tag}",
            adapter_block,
            subsystem="detector",
            role="fixed-angle transition block",
        )
        mount_obj = _add_component(
            doc,
            assembly,
            export_objects,
            f"DetectorMountBase_{tag}",
            mount_base,
            subsystem="detector",
            role="orthogonally projected detector mount base with rectangular 4-hole bolt pattern",
        )

        for obj in (housing_obj, clamp_a_obj, clamp_b_obj, adapter_obj, mount_obj):
            _attach_layout_properties(obj, placement)

    for name, shape in build_target_ladder(cfg.geometry).items():
        _add_component(
            doc,
            assembly,
            export_objects,
            name,
            shape,
            subsystem="target",
            role="3-position linear ladder drivetrain",
        )

    for name, shape in build_target_holders(cfg.geometry).items():
        role = "removable holder and target set"
        if "ClampScrew_" in name:
            role = "holder dual-screw clamp fastener"
        _add_component(
            doc,
            assembly,
            export_objects,
            name,
            shape,
            subsystem="target",
            role=role,
        )

    for name, shape in build_stand(cfg.geometry).items():
        _add_component(
            doc,
            assembly,
            export_objects,
            name,
            shape,
            subsystem="stand",
            role="base/support/anchor-leveling constraint",
        )

    doc.recompute()
    return BuildResult(document=doc, export_objects=export_objects, placements=placements)
