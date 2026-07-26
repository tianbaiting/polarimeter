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
