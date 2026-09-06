from __future__ import annotations

import json
from pathlib import Path

import FreeCAD as App
import Part

from ..assembly import _new_document
from ..artifacts import document_geometry_metrics
from ..export import export_fcstd, export_step
from ..visual import (
    add_feature,
    finalize_document,
    ensure_gui_session,
    PHYSICAL,
    PURCHASED,
    KEEPOUT,
)
from .geometry import moved, V
from .motion import main_motion_phases, plug_parking_delta, ground_parking_delta


def add(doc, name, shape, group, role=PHYSICAL, material=None):
    material = material or (
        "stainless_304L"
        if group in {"FixedSupport", "CaptureTool", "Docking"}
        else "aluminum_6061_provisional"
    )
    obj = add_feature(doc, name, shape, role=role, group_name=group, material=material)
    if getattr(obj, "ViewObject", None) is not None:
        if group == "Carrier":
            obj.ViewObject.ShapeColor = (0.45, 0.64, 0.76)
        if group == "FixedSupport":
            obj.ViewObject.ShapeColor = (0.35, 0.43, 0.48)
        if group == "CaptureTool":
            obj.ViewObject.ShapeColor = (0.52, 0.36, 0.70)
        if group == "PassiveServices":
            obj.ViewObject.ShapeColor = (0.68, 0.40, 0.20)
    return obj


def actor_group(name):
    if name.startswith(("Carrier", "GripFork", "GripTrunnion")) or "Attachment" in name:
        return "Carrier"
    if "PassiveCoax" in name or "PanelCoax" in name:
        return "PassiveServices"
    if "NestCradle" in name or "Clamp" in name:
        return "DetectorMounts"
    return "DetectorHeads"


def export_artifacts(cfg, s, g, output_dir, basename):
    ensure_gui_session()
    if App.GuiUp:
        import FreeCADGui as Gui

        # [EN] Keep the worker's GUI hidden while retaining native view providers; desktop window actions must not interrupt batch document export. / [CN] 保留原生视图提供器但隐藏工作进程窗口，避免桌面窗口操作中断批量文档导出。
        Gui.getMainWindow().hide()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    doc = _new_document("BoxedSector_RIGHT")
    for name, shape in g.actor.items():
        add(
            doc,
            name,
            shape,
            actor_group(name),
            PURCHASED if name in g.purchased else PHYSICAL,
            g.actor_materials[name],
        )
    for name, path in g.cable_paths.items():
        add(doc, name, path, "CableCenterlines", KEEPOUT)
    finalize_document(doc)
    result["sector_fcstd"] = export_fcstd(doc, str(output_dir), "BoxedSector_RIGHT")
    result["sector_step"] = export_step(doc, str(output_dir), "BoxedSector_RIGHT")
    metrics = output_dir / "BoxedSector_RIGHT.geometry_metrics.json"
    metrics.write_text(
        json.dumps(document_geometry_metrics(cfg, doc, "single_boxed_sector"), indent=2)
        + "\n"
    )
    result["sector_metrics"] = str(metrics)

    phases = main_motion_phases(g, s)
    views = [("installed", g.actor, {})]
    for phase in phases:
        parts = phase.at(1)
        if phase.name == "11_controlled_turn":
            tools = {
                name: moved(
                    shape, V(-s.radial_release_mm, 0, s.downstream_translation_mm)
                )
                for name, shape in g.tool.items()
            }
            parts = {**parts, **tools}
        views.append((phase.name, parts, {}))
    keyposes = {}
    for label, parts, _ in views:
        doc = _new_document(f"{basename}_{label}")
        metadata = doc.addObject("App::DocumentObjectGroup", "StudyScope")
        metadata.addProperty("App::PropertyString", "Description")
        metadata.Description = "One detailed RIGHT sector; three neighbors are conservative reservations; no fabrication release."
        for name, shape in parts.items():
            group = "CaptureTool" if name in g.tool else actor_group(name)
            add(
                doc,
                name,
                shape,
                group,
                PURCHASED if name in g.purchased or name in g.tool else PHYSICAL,
                g.actor_materials.get(name),
            )
        for name, shape in g.fixed.items():
            add(doc, name, shape, "FixedSupport")
        for name, shape in g.chamber.physical.items():
            add_feature(
                doc,
                name,
                shape,
                group_name="Chamber",
                material=g.chamber.materials.get(name, "stainless_304L"),
            )
        for name, shape in g.chamber.purchased_interfaces.items():
            if name in {
                "MaintenanceAccessBlindFlange",
                "MaintenanceAccessCopperGasket",
            }:
                continue
            add_feature(doc, name, shape, role=PURCHASED, group_name="Chamber")
        for port in g.ports.values():
            for name, shape in port.physical.items():
                add(doc, name, shape, "Services", material="stainless_304L")
            for name, shape in port.purchased_interfaces.items():
                add(
                    doc,
                    name,
                    shape,
                    "Services",
                    PURCHASED,
                    "purchased_feedthrough_provisional",
                )
        for name, shape in g.target.stationary.items():
            add(
                doc,
                name,
                shape,
                "Target",
                material=g.target.materials.get(name, "unresolved"),
            )
        for name, shape in g.target.park.physical.items():
            add(
                doc,
                f"TargetPark_{name}",
                shape,
                "Target",
                material=g.target.materials.get(name, "unresolved"),
            )
        for name, shape in g.neighbors.items():
            add(doc, name, shape, "NeighborReservations", KEEPOUT)
        for name, shape in g.plugs.items():
            add(
                doc,
                name,
                moved(shape, plug_parking_delta(s)) if label != "installed" else shape,
                "PassiveServices",
                PURCHASED,
                "purchased_connector_provisional",
            )
        for name, shape in g.ground.items():
            add(
                doc,
                name,
                (
                    moved(shape, ground_parking_delta(s))
                    if label != "installed"
                    else shape
                ),
                "PassiveServices",
                material="oxygen_free_copper",
            )
        for name, shape in g.draw_screw.items():
            if label == "installed":
                add(doc, name, shape, "Docking", PURCHASED)
        if label != "installed":
            for name, shape in g.parked_looms.items():
                add(
                    doc,
                    name,
                    shape,
                    "PassiveServices",
                    material="microcoax_provisional",
                )
        finalize_document(doc)
        destination = (
            output_dir if label == "installed" else output_dir / "keyposes" / label
        )
        name = basename if label == "installed" else f"{basename}_{label}"
        path = export_fcstd(doc, str(destination), name)
        keyposes[label] = path
        if label == "installed":
            result["fcstd"] = path
            result["step"] = export_step(doc, str(destination), name)
    result["keypose_fcstd"] = keyposes
    return result
