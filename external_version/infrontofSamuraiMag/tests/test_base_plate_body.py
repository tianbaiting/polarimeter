"""Regression tests for BasePlate_Bolted (Sub-2 Task 9, Path B).

[EN] Path B wraps build_detector_fixture's `mount_base` (the plate-mounted
base independent of the load-bearing weldment) into a Part::Feature named
`BasePlate_Bolted_<tag>`. Tests mirror the weldment/upper-clamp tests.
/ [CN] Path B 把 build_detector_fixture 的 mount_base 包成
`BasePlate_Bolted_<tag>` 的 Part::Feature。测试与焊件/上抱箍一致。
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


def test_base_plate_is_single_solid_for_first_placement():
    import FreeCAD as App

    from ifsm.components import build_base_plate_bolted

    cfg, placements = _load_context()
    doc = App.newDocument("TestBasePlateSingle")
    try:
        feat = build_base_plate_bolted(doc, cfg.geometry, placements[0])
        assert feat.TypeId == "Part::Feature"
        assert feat.Name.startswith("BasePlate_Bolted_")
        assert len(feat.Shape.Solids) == 1
        assert feat.Shape.Volume > 0.0
    finally:
        App.closeDocument(doc.Name)


def test_base_plate_all_12_placements_build():
    import FreeCAD as App

    from ifsm.components import build_base_plate_bolted

    cfg, placements = _load_context()
    assert len(placements) == 12, f"expected 12 BLP_v1 placements, got {len(placements)}"
    doc = App.newDocument("TestBasePlate12")
    try:
        for i, placement in enumerate(placements):
            feat = build_base_plate_bolted(
                doc, cfg.geometry, placement, name_suffix=f"_{i}"
            )
            assert len(feat.Shape.Solids) == 1, (
                f"placement {i} ({placement.tag}): "
                f"{len(feat.Shape.Solids)} solids"
            )
            assert feat.Shape.Volume > 0.0
    finally:
        App.closeDocument(doc.Name)
