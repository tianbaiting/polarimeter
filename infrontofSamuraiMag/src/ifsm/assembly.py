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
    build_rotary_feedthrough_vendor_reference,
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
    assembly_name = "".join(ch if ch.isalnum() else "_" for ch in f"{doc_name}Assembly")
    assembly = doc.addObject("App::DocumentObjectGroup", assembly_name)
    export_objects: list[App.DocumentObject] = []

    # [EN] Build the analytical placement set once and fan it out to chamber cuts, plate openings, detector fixtures, and validation metadata so every subsystem shares one channel truth. / [CN] 解析布局只生成一次，并统一供腔体开孔、板件开口、探测器夹具和校验元数据使用，保证各子系统共享同一通道真值。
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
        f"FrontEndModule_{cfg.geometry.chamber.end_modules.front.standard}",
        front_module,
        subsystem="chamber",
        role="replaceable upstream interface module",
    )
    rear_module_obj = _add_component(
        doc,
        assembly,
        export_objects,
        f"RearEndModule_{cfg.geometry.chamber.end_modules.rear.standard}",
        rear_module,
        subsystem="chamber",
        role="replaceable downstream interface module",
    )
    _set_string_property(front_module_obj, "Standard", "Interface", cfg.geometry.chamber.end_modules.front.standard)
    _set_string_property(rear_module_obj, "Standard", "Interface", cfg.geometry.chamber.end_modules.rear.standard)

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
    # [EN] Plate objects retain frozen HVV pose semantics as properties so downstream review can recover which side-exit plane each solid represents. / [CN] 板件对象保留冻结的 HVV 姿态语义属性，便于后续审查时追溯每个实体对应哪一个侧向出射安装平面。
    for name, shape in build_all_plates(cfg.geometry, placements=placements).items():
        plate_obj = _add_component(
            doc,
            assembly,
            export_objects,
            name,
            shape,
            subsystem="plates",
            role="load-bearing HVV plate with lugs/bolt pattern/stiffeners and LOS-based opening cut",
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
        housing, clamp_a, support_carrier, mount_base = build_detector_fixture(
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
        support_carrier_obj = _add_component(
            doc,
            assembly,
            export_objects,
            f"DetectorSupportCarrier_{tag}",
            support_carrier,
            subsystem="detector",
            role="integrated support-side clamp half + transition block + uprights + top bridge",
        )
        mount_obj = _add_component(
            doc,
            assembly,
            export_objects,
            f"DetectorMountBase_{tag}",
            mount_base,
            subsystem="detector",
            role="separate detector mount base plate with rectangular 4-hole bolt pattern",
        )

        # [EN] Attach the same channel metadata to every detector subpart so STEP review can trace a clamp or adapter back to the physical sector/channel it serves. / [CN] 给每个探测器子件附上统一通道元数据，使 STEP 审查时能把抱箍或过渡块追溯回其对应的物理扇区/通道。
        for obj in (housing_obj, clamp_a_obj, support_carrier_obj, mount_obj):
            _attach_layout_properties(obj, placement)

    target_drive_role = "3-position linear ladder drivetrain"
    if cfg.geometry.target.mode == "single_rotary":
        target_drive_role = "single-target rotary drivetrain"
    for name, shape in build_target_ladder(cfg.geometry).items():
        _add_component(
            doc,
            assembly,
            export_objects,
            name,
            shape,
            subsystem="target",
            role=target_drive_role,
        )

    for name, shape in build_rotary_feedthrough_vendor_reference(cfg.geometry).items():
        _add_component(
            doc,
            assembly,
            export_objects,
            name,
            shape,
            subsystem="target",
            role="external vendor rotary-feedthrough reference envelope",
        )

    for name, shape in build_target_holders(cfg.geometry).items():
        role = "removable holder and target set"
        if cfg.geometry.target.mode == "single_rotary":
            role = "single-target holder and target set"
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

    # [EN] Stand solids are added last because they react to the frozen detector/chamber footprint instead of driving detector layout themselves. / [CN] 支架实体最后加入，因为它们响应的是已冻结的探测器/腔体占位，而不是反向决定探测器布局。
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
