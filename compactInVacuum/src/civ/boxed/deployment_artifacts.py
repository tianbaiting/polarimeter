from __future__ import annotations

import json
from pathlib import Path

import FreeCAD as App

from ..assembly import _new_document
from ..artifacts import document_geometry_metrics
from ..export import export_fcstd, export_step
from ..visual import ensure_gui_session, finalize_document, PHYSICAL, PURCHASED
from .artifacts import add, actor_group
from .deployment import ANGLES


def export_deployment(cfg, s, d, f, output, basename):
    ensure_gui_session()
    if App.GuiUp:
        import FreeCADGui as Gui

        # [EN] Retain native view providers without exposing the batch worker to desktop close-window actions. / [CN] 保留原生视图提供器，同时避免桌面关闭窗口操作中断批量导出。
        Gui.getMainWindow().hide()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    result, sectors, keyposes = {}, {}, {}

    def metadata(doc, kind):
        obj = doc.addObject("App::DocumentObjectGroup", "Configuration")
        for prop, value in {
            "Instrument": cfg.compact_one.deployment.instrument_name,
            "GeometryScope": kind,
            "RemovalOrder": "UP -> RIGHT -> LEFT -> DOWN",
            "Coordinates": "Beam +Z; vertical +Y",
            "ReleaseStatus": "Provisional geometry; complete maintenance preparation and fabrication evidence remain open",
            "BoxedDeploymentParameters": json.dumps(d, sort_keys=True),
        }.items():
            obj.addProperty("App::PropertyString", prop)
            setattr(obj, prop, value)

    def finish(doc):
        finalize_document(doc)
        if App.GuiUp:
            import FreeCADGui as Gui

            # [EN] Save a Y-up isometric camera consistent with the physical beam coordinates. / [CN] 保存与物理束流坐标一致、以 Y 为上方的等轴测相机。
            outward = App.Vector(1, 1, -1)
            outward.normalize()
            right = App.Vector(0, 1, 0).cross(outward)
            right.normalize()
            up = outward.cross(right)
            view = Gui.getDocument(doc.Name).activeView()
            view.setCameraOrientation(App.Rotation(right, up, outward, "ZXY").Q)
            view.fitAll()

    def actor(doc, parts):
        for name, shape in parts.items():
            sector, local = name.split("_", 1)
            group = (
                "CaptureTool"
                if local.startswith(("Capture", "HandlingRod"))
                else actor_group(local)
            )
            purchased = "Screw" in name or "Connector" in name or group == "CaptureTool"
            obj = add(
                doc,
                name,
                shape,
                group,
                PURCHASED if purchased else PHYSICAL,
                f.materials.get(name),
            )
            obj.Label = f"{sector.upper()} | {local}"
            obj.addProperty("App::PropertyString", "Sector")
            obj.Sector = sector

    def assembly(doc, open_lid, current=None, pose=None, removed=frozenset()):
        metadata(
            doc,
            (
                "four detailed physical sectors / twelve complete detector heads"
                if not current
                else f"maintenance step: {current}"
            ),
        )
        for sector in ANGLES:
            if sector in removed:
                continue
            actor(doc, pose if sector == current else f.sectors[sector])
            if sector != current:
                for n, sh in f.retainers[sector].items():
                    add(
                        doc,
                        n,
                        sh,
                        "Docking",
                        PURCHASED if "Screw" in n else PHYSICAL,
                        "stainless_304L",
                    )
        for n, sh in f.fixed.items():
            add(doc, n, sh, "FixedSupport", material="stainless_304L")
        for sector in ANGLES:
            parked = sector in removed or sector == current
            for mapping, role, material in (
                (
                    f.parked_plugs if parked else f.plugs,
                    PURCHASED,
                    "purchased_connector_provisional",
                ),
                (
                    f.parked_grounds if parked else f.grounds,
                    PHYSICAL,
                    "oxygen_free_copper",
                ),
                (
                    f.parked_looms if parked else f.looms,
                    PHYSICAL,
                    "microcoax_provisional",
                ),
            ):
                for n, sh in mapping[sector].items():
                    add(doc, n, sh, "PassiveServices", role, material)
        g = f.base
        for n, sh in g.chamber.physical.items():
            add(
                doc,
                n,
                sh,
                "Chamber",
                material=g.chamber.materials.get(n, "stainless_304L"),
            )
        for n, sh in g.chamber.purchased_interfaces.items():
            if open_lid and n in {
                "MaintenanceAccessBlindFlange",
                "MaintenanceAccessCopperGasket",
            }:
                continue
            add(
                doc,
                n,
                sh,
                "Chamber",
                PURCHASED,
                "oxygen_free_copper" if "Gasket" in n else "stainless_304L",
            )
        for port in g.ports.values():
            for n, sh in port.physical.items():
                add(doc, n, sh, "Services", material="stainless_304L")
            for n, sh in port.purchased_interfaces.items():
                add(
                    doc,
                    n,
                    sh,
                    "Services",
                    PURCHASED,
                    "purchased_feedthrough_provisional",
                )
        for n, sh in g.target.stationary.items():
            add(doc, n, sh, "Target", material=g.target.materials.get(n, "unresolved"))
        for n, sh in (g.target.park if open_lid else g.target.work).physical.items():
            add(doc, n, sh, "Target", material=g.target.materials.get(n, "unresolved"))

    for sector in ANGLES:
        name = f"{basename}_BoxedSector_{sector.upper()}"
        doc = _new_document(name)
        metadata(doc, f"complete loaded {sector.upper()} sector")
        actor(doc, f.sectors[sector])
        finish(doc)
        sectors[sector] = dict(
            fcstd=export_fcstd(doc, str(output / "sectors"), name),
            step=export_step(doc, str(output / "sectors"), name),
        )
        App.closeDocument(doc.Name)
    for open_lid in (False, True):
        name = basename + ("_MaintenanceOpen" if open_lid else "")
        doc = _new_document(name)
        assembly(doc, open_lid)
        finish(doc)
        fcstd = export_fcstd(doc, str(output), name)
        if open_lid:
            result["maintenance_fcstd"] = fcstd
        else:
            result["fcstd"] = fcstd
            result["step"] = export_step(doc, str(output), name)
            path = output / f"{basename}.geometry_metrics.json"
            path.write_text(
                json.dumps(
                    document_geometry_metrics(
                        cfg, doc, "complete_four_boxed_sector_deployment"
                    ),
                    indent=2,
                )
                + "\n"
            )
            result["geometry_metrics"] = str(path)
        App.closeDocument(doc.Name)
    removed = set()
    for sector in d["removal_order"]:
        keyposes[sector] = {}
        for label, pose in f.poses[sector].items():
            doc = _new_document(f"{basename}_{label}")
            assembly(doc, True, sector, pose, removed)
            finish(doc)
            keyposes[sector][label] = export_fcstd(
                doc, str(output / "keyposes" / sector), f"{basename}_{label}"
            )
            App.closeDocument(doc.Name)
        removed.add(sector)
    result["sector_artifacts"] = sectors
    result["keypose_fcstd"] = keyposes
    return result
