from pathlib import Path
import sys
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from civ.config import load_config
from civ.boxed.config import load_spec, load_deployment
from civ.boxed.side_config import load_side_spec
from civ.boxed.side_geometry import build_side_geometry
from civ.boxed.side_installation import (
    side_void_candidates,
    validate_support_installation,
)
from civ.boxed.deployment import flatten, chamber_environment
from civ.boxed.deployment_validation import collisions
from civ.boxed.motion import verify_void_regions


def main():
    path = ROOT / "config/afterSRC_compact.yaml"
    cfg, s, d, q = (
        load_config(str(path)),
        load_spec(path),
        load_deployment(path),
        load_side_spec(path),
    )
    f = build_side_geometry(cfg, s, d, q)
    wall = f.base.chamber.physical["ProjectChamberBody"]
    assert wall.isInside(App.Vector(0, 224, 190), 1e-7, True)
    assert not wall.isInside(App.Vector(224, 0, 190), 1e-7, True)
    assert not wall.isInside(App.Vector(-224, 175, 10), 1e-7, True)
    assert not wall.isInside(App.Vector(70, 224, 0), 1e-7, True)
    assert "AnnularSupportWeldment" not in f.fixed
    assert len(f.support_bodies) == 4 and len(flatten(f.mount_bolts)) == 16
    assert len([n for n in flatten(f.sectors) if n.endswith("_ActivePlastic")]) == 12
    assert not collisions(f.fixed)
    assert all(
        p.wall_center.x < -219.9
        for p in f.base.ports.values()
        if p.port.role == "signal"
    )
    assert f.base.ports["rotary_target"].wall_center.y == 220
    voids, _ = verify_void_regions(
        side_void_candidates(f, s),
        chamber_environment(f),
        s.collision_volume_tolerance_mm3,
    )
    records = []

    def record(name, passed, detail, failures=None):
        records.append((name, passed))

    _, passed = validate_support_installation(f, s, q, record, voids)
    assert passed and all(ok for name, ok in records)
    # [EN] A real entrance obstruction must invalidate support installation, even when the installed pose remains unchanged. / [CN] 即使最终安装位置不变，真实入口障碍也必须使支座装入检查失败。
    f.fixed_regions["DeliberateWindowBlocker"] = Part.makeBox(
        10, 240, 240, App.Vector(240, -120, 70)
    )
    records.clear()
    _, passed = validate_support_installation(f, s, q, record, voids)
    assert not passed
    print(
        "PASS: top rotary / left signals / right opening, four local supports, 16 mounting screws, twelve frozen detectors, complete support insertion and deliberate window-obstruction rejection",
        flush=True,
    )
    return 0
