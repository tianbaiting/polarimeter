from __future__ import annotations

import FreeCAD as App

from .components import build_compact_detector, build_end_modules, build_inner_frame, build_vessel_body
from .config import CIVConfig
from .layout import build_detector_placements


def _add_feature(doc: App.Document, name: str, shape) -> App.DocumentObject:
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
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
    _add_feature(doc, "InnerFrame", build_inner_frame(cfg, placements))
    for placement in placements:
        _add_feature(doc, placement.tag, build_compact_detector(cfg, placement))

    doc.recompute()
    return doc
