from __future__ import annotations

import FreeCAD as App

from .components import (
    build_cable_route_keepouts,
    build_compact_detector,
    build_end_modules,
    build_grounding_envelopes,
    build_housekeeping_harness_keepouts,
    build_inner_frame,
    build_rotary_target_park_keepout,
    build_rotary_target_work_shapes,
    build_strain_relief_envelopes,
    build_top_service_equipment_envelopes,
    build_top_service_mounts,
    build_vessel_body,
)
from .config import CIVConfig
from .cassette import build_detector_cassette
from .cartridge import build_sector_cartridge
from .internal import build_internal_assembly
from .services import build_services
from .layout import build_detector_placements


def _add_feature(
    doc: App.Document,
    name: str,
    shape,
    engineering_role: str = "physical",
) -> App.DocumentObject:
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "EngineeringRole", "CompactInVacuum")
    obj.EngineeringRole = engineering_role
    return obj


def build_assembly(cfg: CIVConfig) -> App.Document:
    if cfg.doc_name in App.listDocuments():
        App.closeDocument(cfg.doc_name)

    doc = App.newDocument(cfg.doc_name)
    placements = build_detector_placements(cfg)

    _add_feature(doc, "VesselBody", build_vessel_body(cfg))
    front_module, rear_module = build_end_modules(cfg)
    _add_feature(doc, f"FrontEndModule_{cfg.vessel.end_modules.front.standard}", front_module)
    _add_feature(doc, f"RearEndModule_{cfg.vessel.end_modules.rear.standard}", rear_module)
    for name, shape in build_top_service_mounts(cfg).items():
        _add_feature(doc, name, shape)
    for name, shape in build_top_service_equipment_envelopes(cfg).items():
        _add_feature(doc, name, shape, engineering_role="supplier_interface_envelope")
    for name, shape in build_rotary_target_work_shapes(cfg).items():
        _add_feature(doc, name, shape)
    park_keepout = build_rotary_target_park_keepout(cfg)
    if park_keepout is not None:
        _add_feature(doc, "RotaryTargetParkKeepout", park_keepout, engineering_role="keepout")
    _add_feature(doc, "InnerFrame", build_inner_frame(cfg, placements))
    for placement in placements:
        _add_feature(doc, placement.tag, build_compact_detector(cfg, placement))
    for name, shape in build_cable_route_keepouts(cfg, placements).items():
        _add_feature(doc, name, shape, engineering_role="keepout")
    for name, shape in build_housekeeping_harness_keepouts(cfg).items():
        _add_feature(doc, name, shape, engineering_role="keepout")
    for name, shape in build_strain_relief_envelopes(cfg, placements).items():
        _add_feature(doc, name, shape, engineering_role="interface_envelope")
    for name, shape in build_grounding_envelopes(cfg).items():
        _add_feature(doc, name, shape, engineering_role="interface_envelope")

    doc.recompute()
    return doc


def build_cassette_document(cfg: CIVConfig) -> App.Document:
    doc_name = f"{cfg.doc_name}_GoldenCassette"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    geometry = build_detector_cassette(cfg)
    for name, shape in geometry.physical.items():
        obj = _add_feature(doc, name, shape)
        obj.addProperty("App::PropertyString", "MaterialName", "CompactOne")
        obj.MaterialName = geometry.materials.get(name, "unresolved")
    for name, shape in geometry.interfaces.items():
        _add_feature(doc, name, shape, engineering_role="interface_envelope")
    for name, shape in geometry.keepouts.items():
        _add_feature(doc, name, shape, engineering_role="keepout")
    for name, shape in geometry.datums.items():
        _add_feature(doc, name, shape, engineering_role="datum")
    doc.recompute()
    return doc


def build_sector_document(cfg: CIVConfig, sector: str = "left") -> App.Document:
    doc_name = f"{cfg.doc_name}_GoldenSector_{sector}"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    geometry = build_sector_cartridge(cfg, sector)
    for name, shape in geometry.physical.items():
        obj = _add_feature(doc, name, shape)
        obj.addProperty("App::PropertyString", "MaterialName", "CompactOne")
        obj.MaterialName = geometry.materials.get(name, "unresolved")
    for name, shape in geometry.interfaces.items():
        _add_feature(doc, name, shape, engineering_role="interface_envelope")
    for name, shape in geometry.keepouts.items():
        _add_feature(doc, name, shape, engineering_role="keepout")
    for name, shape in geometry.datums.items():
        _add_feature(doc, name, shape, engineering_role="datum")
    doc.recompute()
    return doc


def build_internal_document(cfg: CIVConfig) -> App.Document:
    doc_name = f"{cfg.doc_name}_FourSectorInternal"
    if doc_name in App.listDocuments():
        App.closeDocument(doc_name)
    doc = App.newDocument(doc_name)
    geometry = build_internal_assembly(cfg)
    for name, shape in geometry.physical.items():
        obj = _add_feature(doc, name, shape)
        obj.addProperty("App::PropertyString", "MaterialName", "CompactOne")
        obj.MaterialName = geometry.materials.get(name, "unresolved")
    for name, shape in geometry.interfaces.items():
        _add_feature(doc, name, shape, engineering_role="interface_envelope")
    for name, shape in geometry.keepouts.items():
        _add_feature(doc, name, shape, engineering_role="keepout")
    for name, shape in geometry.datums.items():
        _add_feature(doc, name, shape, engineering_role="datum")
    doc.recompute()
    return doc


def build_serviced_internal_document(cfg: CIVConfig) -> App.Document:
    doc = build_internal_document(cfg)
    internal = build_internal_assembly(cfg)
    services = build_services(cfg, internal)
    for name, shape in services.physical.items():
        obj = _add_feature(doc, name, shape)
        obj.addProperty("App::PropertyString", "MaterialName", "CompactOne")
        obj.MaterialName = services.materials.get(name, "unresolved")
    for name, shape in services.purchased_interfaces.items():
        _add_feature(
            doc,
            name,
            shape,
            engineering_role="purchased_part_interface",
        )
    for name, shape in services.keepouts.items():
        _add_feature(doc, name, shape, engineering_role="keepout")
    for name, shape in services.centerlines.items():
        _add_feature(doc, name, shape, engineering_role="service_centerline")
    for name, shape in services.datums.items():
        _add_feature(doc, name, shape, engineering_role="datum")
    doc.recompute()
    return doc
