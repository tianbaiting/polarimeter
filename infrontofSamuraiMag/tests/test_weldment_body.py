"""Regression tests for Weldment_LoadBearing (Sub-2 Task 7, Path B).

[EN] Path B wraps build_detector_fixture's support_carrier fused shape into a
Part::Feature named `Weldment_LoadBearing_<tag>`. These tests verify:
  - the returned object is a Part::Feature with a single solid;
  - the wrapped shape has positive volume;
  - all 12 BLP_v1 placements build successfully in a single document.
/ [CN] Path B 把 build_detector_fixture 的 support_carrier 包成名为
`Weldment_LoadBearing_<tag>` 的 Part::Feature。测试验证：
  - 返回对象类型正确且为单体 (single solid)；
  - 体积为正；
  - 12 个 BLP_v1 位置在同一文档中都能构建成功。
"""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.freecad_runtime

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "default_infront.yaml"


def _load_context():
    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements

    cfg = load_build_config(CONFIG)
    placements = build_detector_placements(cfg.layout)
    return cfg, placements


def test_weldment_is_single_solid_for_first_placement():
    import FreeCAD as App

    from ifsm.components import build_weldment_load_bearing

    cfg, placements = _load_context()
    doc = App.newDocument("TestWeldmentSingle")
    try:
        feat = build_weldment_load_bearing(doc, cfg.geometry, placements[0])
        assert feat.TypeId == "Part::Feature"
        assert feat.Name.startswith("Weldment_LoadBearing_")
        assert len(feat.Shape.Solids) == 1
        assert feat.Shape.Volume > 0.0
    finally:
        App.closeDocument(doc.Name)


def test_weldment_all_12_placements_build():
    import FreeCAD as App

    from ifsm.components import build_weldment_load_bearing

    cfg, placements = _load_context()
    assert len(placements) == 12, f"expected 12 BLP_v1 placements, got {len(placements)}"
    doc = App.newDocument("TestWeldment12")
    try:
        for i, placement in enumerate(placements):
            feat = build_weldment_load_bearing(
                doc, cfg.geometry, placement, name_suffix=f"_{i}"
            )
            assert len(feat.Shape.Solids) == 1, (
                f"placement {i} ({placement.tag}): "
                f"{len(feat.Shape.Solids)} solids"
            )
            assert feat.Shape.Volume > 0.0
    finally:
        App.closeDocument(doc.Name)
