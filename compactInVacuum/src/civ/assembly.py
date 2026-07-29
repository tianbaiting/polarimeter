from __future__ import annotations

import FreeCAD as App

from .components import (
    build_cable_route_keepouts,
    build_compact_detector,
    build_end_modules,
    build_grounding_envelopes,
    build_inner_frame,
    build_rotary_target_park_keepout,
    build_rotary_target_work_shapes,
    build_strain_relief_envelopes,
    build_top_service_equipment_envelopes,
    build_top_service_mounts,
    build_vessel_body,
)
from .config import CIVConfig
from .cassette import build_detector_head
from .cartridge import build_sector_holder
from .chamber import build_chamber
from .detector import build_active_acceptance_cone
from .internal import build_internal_assembly
from .services import build_services
from .layout import build_detector_placements
from .visual import (
    DATUM,
    KEEPOUT,
    OPTIONAL_REFERENCE,
    PHYSICS_ACCEPTANCE,
    PURCHASED,
    SERVICE_CENTERLINE,
    add_feature,
    ensure_gui_session,
    finalize_document,
)


def _new_document(name: str) -> App.Document:
    ensure_gui_session()
    if name in App.listDocuments():
        App.closeDocument(name)
    doc = App.newDocument(name)
    if "__CIVGuiBootstrap" in App.listDocuments():
        App.closeDocument("__CIVGuiBootstrap")
    return doc


def build_assembly(cfg: CIVConfig) -> App.Document:
    doc = _new_document(cfg.doc_name)
    placements = build_detector_placements(cfg)

    add_feature(doc, "VesselBody", build_vessel_body(cfg), group_name="Chamber")
    front_module, rear_module = build_end_modules(cfg)
    add_feature(
        doc,
        f"FrontEndModule_{cfg.vessel.end_modules.front.standard}",
        front_module,
        group_name="Chamber",
    )
    add_feature(
        doc,
        f"RearEndModule_{cfg.vessel.end_modules.rear.standard}",
        rear_module,
        group_name="Chamber",
    )
    for name, shape in build_top_service_mounts(cfg).items():
        add_feature(doc, name, shape, group_name="Services")
    for name, shape in build_top_service_equipment_envelopes(cfg).items():
        add_feature(
            doc,
            name,
            shape,
            role=PURCHASED,
            group_name="Services",
        )
    for name, shape in build_rotary_target_work_shapes(cfg).items():
        add_feature(doc, name, shape, group_name="Target")
    park_keepout = build_rotary_target_park_keepout(cfg)
    if park_keepout is not None:
        add_feature(
            doc,
            "RotaryTargetParkKeepout",
            park_keepout,
            role=KEEPOUT,
            group_name="Keepouts",
        )
    add_feature(
        doc,
        "InnerFrame",
        build_inner_frame(cfg, placements),
        group_name="SectorHolder",
    )
    for placement in placements:
        add_feature(
            doc,
            placement.tag,
            build_compact_detector(cfg, placement),
            group_name="DetectorHead",
        )
    for name, shape in build_cable_route_keepouts(cfg, placements).items():
        add_feature(doc, name, shape, role=KEEPOUT, group_name="Keepouts")
    for name, shape in build_strain_relief_envelopes(cfg, placements).items():
        add_feature(
            doc,
            name,
            shape,
            role=OPTIONAL_REFERENCE,
            group_name="OptionalReference",
        )
    for name, shape in build_grounding_envelopes(cfg).items():
        add_feature(
            doc,
            name,
            shape,
            role=OPTIONAL_REFERENCE,
            group_name="OptionalReference",
        )
    finalize_document(doc)
    return doc


def build_detector_head_document(cfg: CIVConfig) -> App.Document:
    doc = _new_document(f"{cfg.doc_name}_DetectorHead")
    geometry = build_detector_head(cfg)
    for name, shape in geometry.physical.items():
        add_feature(
            doc,
            name,
            shape,
            group_name="DetectorHead",
            material=geometry.materials.get(name, "unresolved"),
        )
    for name, shape in geometry.interfaces.items():
        add_feature(
            doc,
            name,
            shape,
            role=OPTIONAL_REFERENCE,
            group_name="OptionalReference",
        )
    for name, shape in geometry.keepouts.items():
        add_feature(doc, name, shape, role=KEEPOUT, group_name="Keepouts")
    for name, shape in geometry.datums.items():
        add_feature(doc, name, shape, role=DATUM, group_name="Datums")
    finalize_document(doc)
    return doc


def build_transparent_detector_head_document(cfg: CIVConfig) -> App.Document:
    doc = build_detector_head_document(cfg)
    sleeve = doc.getObject("LightTightSleeve")
    if sleeve is not None and getattr(sleeve, "ViewObject", None) is not None:
        sleeve.ViewObject.Transparency = 82
    rear_face = doc.getObject("RearMountingFace")
    if rear_face is not None and getattr(rear_face, "ViewObject", None) is not None:
        rear_face.ViewObject.Transparency = 68
    finalize_document(doc)
    return doc


def build_sector_holder_document(
    cfg: CIVConfig,
    sector: str = "left",
) -> App.Document:
    doc = _new_document(f"{cfg.doc_name}_SectorHolder_{sector}")
    geometry = build_sector_holder(cfg, sector)
    holder_names = set(geometry.holder_physical_names)
    for name, shape in geometry.physical.items():
        add_feature(
            doc,
            name,
            shape,
            group_name="SectorHolder" if name in holder_names else "DetectorHead",
            material=geometry.materials.get(name, "unresolved"),
        )
    for name, shape in geometry.purchased_interfaces.items():
        add_feature(
            doc,
            name,
            shape,
            role=PURCHASED,
            group_name="SectorHolder",
        )
    for name, shape in geometry.interfaces.items():
        add_feature(
            doc,
            name,
            shape,
            role=OPTIONAL_REFERENCE,
            group_name="OptionalReference",
        )
    for name, shape in geometry.keepouts.items():
        add_feature(doc, name, shape, role=KEEPOUT, group_name="Keepouts")
    for name, shape in geometry.datums.items():
        add_feature(doc, name, shape, role=DATUM, group_name="Datums")
    for placement in geometry.placements:
        add_feature(
            doc,
            f"{placement.tag}_FullActiveAcceptance",
            build_active_acceptance_cone(cfg, placement),
            role=PHYSICS_ACCEPTANCE,
            group_name="PhysicsAcceptance",
        )
    finalize_document(doc)
    return doc


def _add_internal_geometry(
    doc: App.Document,
    cfg: CIVConfig,
    geometry,
) -> None:
    holder_names = {
        name
        for holder in geometry.sector_holders.values()
        for name in holder.holder_physical_names
    }
    for name, shape in geometry.physical.items():
        if name.startswith("Target"):
            group_name = "Target"
        elif name in holder_names:
            group_name = "SectorHolder"
        else:
            group_name = "DetectorHead"
        add_feature(
            doc,
            name,
            shape,
            group_name=group_name,
            material=geometry.materials.get(name, "unresolved"),
        )
    for name, shape in geometry.purchased_interfaces.items():
        add_feature(
            doc,
            name,
            shape,
            role=PURCHASED,
            group_name="SectorHolder",
        )
    for name, shape in geometry.interfaces.items():
        add_feature(
            doc,
            name,
            shape,
            role=OPTIONAL_REFERENCE,
            group_name="OptionalReference",
        )
    for name, shape in geometry.keepouts.items():
        add_feature(doc, name, shape, role=KEEPOUT, group_name="Keepouts")
    for name, shape in geometry.datums.items():
        add_feature(doc, name, shape, role=DATUM, group_name="Datums")
    for placement in geometry.placements:
        add_feature(
            doc,
            f"{placement.tag}_FullActiveAcceptance",
            build_active_acceptance_cone(cfg, placement),
            role=PHYSICS_ACCEPTANCE,
            group_name="PhysicsAcceptance",
        )


def build_internal_document(cfg: CIVConfig) -> App.Document:
    doc = _new_document(f"{cfg.doc_name}_FourSectorInternal")
    geometry = build_internal_assembly(cfg)
    _add_internal_geometry(doc, cfg, geometry)
    finalize_document(doc)
    return doc


def build_serviced_internal_document(cfg: CIVConfig) -> App.Document:
    doc = build_internal_document(cfg)
    internal = build_internal_assembly(cfg)
    services = build_services(cfg, internal)
    for name, shape in services.physical.items():
        add_feature(
            doc,
            name,
            shape,
            group_name="Services",
            material=services.materials.get(name, "unresolved"),
        )
    for name, shape in services.purchased_interfaces.items():
        add_feature(
            doc,
            name,
            shape,
            role=PURCHASED,
            group_name="Services",
        )
    for name, shape in services.keepouts.items():
        add_feature(doc, name, shape, role=KEEPOUT, group_name="Keepouts")
    for name, shape in services.centerlines.items():
        add_feature(
            doc,
            name,
            shape,
            role=SERVICE_CENTERLINE,
            group_name="Services",
        )
    for name, shape in services.datums.items():
        add_feature(doc, name, shape, role=DATUM, group_name="Datums")
    finalize_document(doc)
    return doc


def build_compact_one_document(cfg: CIVConfig) -> App.Document:
    if cfg.compact_one is None:
        raise ValueError("CompactOne document requires a schema-v3 configuration")
    doc = _new_document(cfg.doc_name)
    internal = build_internal_assembly(cfg)
    services = build_services(cfg, internal)
    chamber = build_chamber(cfg)

    for name, shape in chamber.physical.items():
        add_feature(
            doc,
            name,
            shape,
            group_name="Chamber",
            material=chamber.materials.get(name, "unresolved"),
        )
    for name, shape in chamber.purchased_interfaces.items():
        add_feature(
            doc,
            name,
            shape,
            role=PURCHASED,
            group_name="Chamber",
        )
    for name, shape in chamber.keepouts.items():
        add_feature(doc, name, shape, role=KEEPOUT, group_name="Keepouts")
    for name, shape in chamber.datums.items():
        add_feature(doc, name, shape, role=DATUM, group_name="Datums")

    _add_internal_geometry(doc, cfg, internal)
    for name, shape in services.physical.items():
        add_feature(
            doc,
            name,
            shape,
            group_name="Services",
            material=services.materials.get(name, "unresolved"),
        )
    for name, shape in services.purchased_interfaces.items():
        add_feature(
            doc,
            name,
            shape,
            role=PURCHASED,
            group_name="Services",
        )
    for name, shape in services.keepouts.items():
        add_feature(doc, name, shape, role=KEEPOUT, group_name="Keepouts")
    for name, shape in services.centerlines.items():
        add_feature(
            doc,
            name,
            shape,
            role=SERVICE_CENTERLINE,
            group_name="Services",
        )
    for name, shape in services.datums.items():
        add_feature(doc, name, shape, role=DATUM, group_name="Datums")
    finalize_document(doc)
    return doc
