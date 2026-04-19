from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def _load_cfg_and_placement():
    import FreeCAD as App  # noqa: F401
    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = build_detector_placements(cfg.layout)
    return cfg.geometry, placements[0]


def test_weldment_is_single_solid_for_first_placement() -> None:
    import FreeCAD as App
    from ifsm.components import build_weldment_load_bearing

    geom, placement = _load_cfg_and_placement()
    doc = App.newDocument("TestWeldment")
    body = build_weldment_load_bearing(doc, geom, placement)
    assert len(body.Shape.Solids) == 1, f"expected 1 solid, got {len(body.Shape.Solids)}"


def test_weldment_has_fillet_and_chamfer() -> None:
    import FreeCAD as App
    from ifsm.components import build_weldment_load_bearing

    geom, placement = _load_cfg_and_placement()
    doc = App.newDocument("TestWeldment2")
    body = build_weldment_load_bearing(doc, geom, placement)
    types = [obj.TypeId for obj in body.Group]
    assert "PartDesign::Fillet" in types, f"no Fillet in body.Group: {types}"
    assert "PartDesign::Chamfer" in types, f"no Chamfer in body.Group: {types}"


def test_weldment_all_12_placements_build() -> None:
    import FreeCAD as App
    from ifsm.components import build_weldment_load_bearing
    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = build_detector_placements(cfg.layout)
    assert len(placements) == 12
    doc = App.newDocument("TestWeldment12")
    for i, p in enumerate(placements):
        body = build_weldment_load_bearing(doc, cfg.geometry, p, name_suffix=f"_{i}")
        assert len(body.Shape.Solids) == 1, (
            f"placement {i} ({p.tag}) produced {len(body.Shape.Solids)} solids"
        )
