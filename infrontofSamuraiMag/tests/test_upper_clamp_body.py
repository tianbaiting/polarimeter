"""Regression tests for UpperClamp_Detachable (Sub-2 Task 8, Path B).

[EN] Path B wraps build_detector_fixture's clamp_half_a (upper half of the
split clamp ring) into a Part::Feature named `UpperClamp_Detachable_<tag>`.
Tests mirror the weldment tests: single solid, positive volume, and all 12
BLP_v1 placements build without error.
/ [CN] Path B 把 build_detector_fixture 的 clamp_half_a（分体抱箍上半圈）
包成名为 `UpperClamp_Detachable_<tag>` 的 Part::Feature。测试与焊件一致：
单体、体积为正、12 个 BLP_v1 位置都能成功构建。
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


def test_upper_clamp_is_single_solid_for_first_placement():
    import FreeCAD as App

    from ifsm.components import build_upper_clamp_detachable

    cfg, placements = _load_context()
    doc = App.newDocument("TestUpperClampSingle")
    try:
        feat = build_upper_clamp_detachable(doc, cfg.geometry, placements[0])
        assert feat.TypeId == "Part::Feature"
        assert feat.Name.startswith("UpperClamp_Detachable_")
        assert len(feat.Shape.Solids) == 1
        assert feat.Shape.Volume > 0.0
    finally:
        App.closeDocument(doc.Name)


def test_upper_clamp_all_12_placements_build():
    import FreeCAD as App

    from ifsm.components import build_upper_clamp_detachable

    cfg, placements = _load_context()
    assert len(placements) == 12, f"expected 12 BLP_v1 placements, got {len(placements)}"
    doc = App.newDocument("TestUpperClamp12")
    try:
        for i, placement in enumerate(placements):
            feat = build_upper_clamp_detachable(
                doc, cfg.geometry, placement, name_suffix=f"_{i}"
            )
            assert len(feat.Shape.Solids) == 1, (
                f"placement {i} ({placement.tag}): "
                f"{len(feat.Shape.Solids)} solids"
            )
            assert feat.Shape.Volume > 0.0
    finally:
        App.closeDocument(doc.Name)
