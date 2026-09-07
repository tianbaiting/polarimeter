from __future__ import annotations

import math
from pathlib import Path
import sys
import tempfile

import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from civ.config import load_config
from civ.layout import build_detector_placements, detector_center
from civ.boxed.config import load_spec, load_deployment
from civ.boxed.deployment import build_deployment, flatten
from civ.boxed.deployment_validation import collisions
from civ.boxed.motion import Phase, certify_phase
from civ.boxed.runner import complete_artifact_set
from civ.boxed.validation import contact_area


def main():
    path = ROOT / "config/reference_afterSRC_top_boxed.yaml"
    cfg, s, d = load_config(str(path)), load_spec(path), load_deployment(path)
    f = build_deployment(cfg, s, d)
    actors = flatten(f.sectors)
    active = {n: sh for n, sh in actors.items() if n.endswith("_ActivePlastic")}
    assert len(f.sectors) == 4 and len(active) == 12
    assert len(flatten(f.looms)) == len(flatten(f.parked_looms)) == 12
    for placement in build_detector_placements(cfg):
        shape = active[f"{placement.tag}_ActivePlastic"]
        assert (shape.CenterOfMass - detector_center(placement)).Length < 1e-6
        assert abs(shape.Volume - math.pi * 10**2 * 5.5) < 1e-5
    for sector in f.sectors:
        journal = {f"{sector}_GripRearJournal": actors[f"{sector}_GripRearJournal"]}
        crossmember = {
            f"{sector}_CarrierRearCrossmember": actors[
                f"{sector}_CarrierRearCrossmember"
            ]
        }
        assert not collisions(journal, crossmember)
        # [EN] Refilling the journal passage reproduces the real crossmember collision found during integration. / [CN] 填回轴颈通孔可复现整机集成时发现的后横梁碰撞。
        obstruction = Part.makeCylinder(
            4,
            6,
            App.Vector(
                journal[next(iter(journal))].CenterOfMass.x,
                journal[next(iter(journal))].CenterOfMass.y,
                199,
            ),
        )
        assert collisions(journal, {"filled_journal_passage": obstruction})
    fixture = f.fixed["up_ServiceParkingComb"]
    assert contact_area(fixture, f.base.chamber.physical["ProjectChamberBody"]) > 1
    assert fixture.BoundBox.XMin <= -219.999
    assert not collisions(flatten(f.parked_looms))
    head = active["right_deuteron_ActivePlastic"]
    center = head.CenterOfMass
    blocker = Part.makeBox(40, 40, 0.001, center + App.Vector(-20, -20, 47.37))
    motion = Phase(
        "real_detector_thin_blocker",
        {"head": head},
        {"blocker": blocker},
        delta=App.Vector(0, 0, 100),
    )
    assert certify_phase(motion, s)["status"] == "fail"
    with tempfile.TemporaryDirectory() as folder:
        files = []
        for index in range(11):
            file = Path(folder) / f"artifact_{index}.FCStd"
            file.write_bytes(b"artifact-presence-contract")
            files.append(str(file))
        names = list(f.sectors)
        artifacts = dict(
            fcstd=files[0],
            step=files[1],
            maintenance_fcstd=files[2],
            sector_artifacts={
                name: {"fcstd": files[3 + i]} for i, name in enumerate(names)
            },
            keypose_fcstd={
                name: {"lift": files[7 + i]} for i, name in enumerate(names)
            },
        )
        assert complete_artifact_set(artifacts, True)
        artifacts["sector_artifacts"]["down"]["fcstd"] = str(
            Path(folder) / "missing.FCStd"
        )
        assert not complete_artifact_set(artifacts, True)
    print(
        "PASS: four physical sectors, twelve frozen active volumes/centers, all installed/parked looms, real journal collision regression, upper wall parking, continuous thin obstruction, incomplete-delivery skip guard",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
