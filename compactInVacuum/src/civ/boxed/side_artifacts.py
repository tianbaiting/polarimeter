from __future__ import annotations

from pathlib import Path
import FreeCAD as App

from ..assembly import _new_document
from ..export import export_fcstd, export_step
from ..visual import finalize_document, PHYSICAL, PURCHASED
from .artifacts import add
from .deployment import chamber_environment, flatten


def export_support_installation(cfg, s, d, f, output, basename):
    removable = set(flatten(f.support_bodies)) | set(flatten(f.mount_bolts))
    environment = {
        n: sh for n, sh in chamber_environment(f).items() if n not in removable
    }
    result, standalone = {}, {}
    for sector, poses in f.support_poses.items():
        doc = _new_document(f"{basename}_LocalSupport_{sector}")
        for n, sh in {**f.support_bodies[sector], **f.mount_bolts[sector]}.items():
            add(
                doc,
                n,
                sh,
                "FixedSupport",
                PURCHASED if "Screw" in n else PHYSICAL,
                "stainless_304L",
            )
        finalize_document(doc)
        name = f"{basename}_LocalSupport_{sector}"
        destination = Path(output) / "supports"
        standalone[sector] = {
            "fcstd": export_fcstd(doc, str(destination), name),
            "step": export_step(doc, str(destination), name),
        }
        App.closeDocument(doc.Name)
        result[sector] = {}
        for label, parts in poses.items():
            name = f"{basename}_{label}"
            doc = _new_document(name)
            scope = doc.addObject("App::DocumentObjectGroup", "InstallationScope")
            scope.addProperty("App::PropertyString", "Description")
            scope.Description = "Support insertion into the empty instrument; target parked; factory welded pads and service fixtures present; mounting-tool qualification separate."
            for n, sh in {**environment, **parts}.items():
                group = (
                    "Chamber"
                    if n.startswith(
                        ("ProjectChamber", "MaintenanceAccess", "Front", "Rear")
                    )
                    else "FixedSupport"
                )
                if n in f.base.target.stationary or n.startswith("Target_"):
                    group = "Target"
                material = f.base.chamber.materials.get(n, "stainless_304L")
                if group == "Target":
                    material = f.base.target.materials.get(
                        n.removeprefix("Target_"),
                        f.base.target.materials.get(n, "unresolved"),
                    )
                add(
                    doc,
                    n,
                    sh,
                    group,
                    (
                        PURCHASED
                        if "Purchased" in n or "Flange" in n or "Screw" in n
                        else PHYSICAL
                    ),
                    material,
                )
            finalize_document(doc)
            result[sector][label] = export_fcstd(
                doc, str(Path(output) / "support_installation" / sector), name
            )
            App.closeDocument(doc.Name)
        environment.update(f.support_bodies[sector])
        environment.update(f.mount_bolts[sector])
    return {"support_installation_fcstd": result, "support_artifacts": standalone}
