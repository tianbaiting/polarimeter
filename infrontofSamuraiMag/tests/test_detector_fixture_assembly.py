"""Runtime tests for the Path B build_detector_fixture composition contract.

[EN] Task 10 rewrites ``build_detector_fixture`` to return a dict of three
named Part::Feature bodies (``weldment``, ``upper_clamp``, ``base_plate``)
plus the detector housing and a list of fastener solids. These tests
exercise the contract against every placement in default_infront.yaml.
/ [CN] Task 10 把 ``build_detector_fixture`` 重构为返回含三件命名
Part::Feature（``weldment``、``upper_clamp``、``base_plate``）加探测器外壳
与紧固件列表的字典。以下测试针对 default_infront.yaml 的所有放置点校验契约。
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.freecad_runtime


def _load_cfg_and_placements():
    pytest.importorskip("FreeCAD")
    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = build_detector_placements(cfg.layout)
    return cfg, placements


def _new_doc(name: str):
    import FreeCAD as App

    try:
        App.closeDocument(name)
    except Exception:
        pass
    return App.newDocument(name)


def test_fixture_returns_three_bodies_and_fasteners() -> None:
    from ifsm.components import build_detector_fixture

    cfg, placements = _load_cfg_and_placements()
    placement = placements[0]
    doc = _new_doc("task10_contract")
    try:
        result = build_detector_fixture(doc, cfg.geometry, placement)
        for key in ("housing", "weldment", "upper_clamp", "base_plate", "fasteners"):
            assert key in result, f"missing key {key!r} in fixture result"
        for body_key in ("housing", "weldment", "upper_clamp", "base_plate"):
            feat = result[body_key]
            assert feat.TypeId == "Part::Feature", (
                f"{body_key} expected Part::Feature, got {feat.TypeId}"
            )
            assert len(feat.Shape.Solids) == 1, (
                f"{body_key} expected 1 solid, got {len(feat.Shape.Solids)}"
            )
            assert feat.Shape.Volume > 1e-6, f"{body_key} has near-zero volume"
        assert isinstance(result["fasteners"], list)
        assert len(result["fasteners"]) > 0, "expected at least one fastener solid"
    finally:
        import FreeCAD as App

        App.closeDocument(doc.Name)


def test_fixture_bolt_count_matches_config() -> None:
    from ifsm.components import build_detector_fixture

    cfg, placements = _load_cfg_and_placements()
    placement = placements[0]
    doc = _new_doc("task10_bolt_count")
    try:
        result = build_detector_fixture(doc, cfg.geometry, placement)
        bolts = [f for f in result["fasteners"] if f["kind"] == "bolt"]
        washers = [f for f in result["fasteners"] if f["kind"] == "washer"]
        nuts = [f for f in result["fasteners"] if f["kind"] == "nut"]
        clamp_bolts = [f for f in bolts if f["subtype"] == "clamp"]
        plate_bolts = [f for f in bolts if f["subtype"] == "plate_side"]
        weld_bolts = [f for f in bolts if f["subtype"] == "weldment_side"]
        # 4 clamp bolts (2 pitches x 2 sides) + 4 plate-side bolts + 4 weldment-side bolts.
        assert len(clamp_bolts) == 4
        assert len(plate_bolts) == 4
        assert len(weld_bolts) == 4
        assert len(bolts) == 12
        # plate-side bolts each paired with a washer.
        assert len(washers) == 4
        # weldment-side bolts each paired with a nut.
        assert len(nuts) == 4
        # every entry's placement tag matches the one we asked for.
        for entry in result["fasteners"]:
            assert entry["placement"] == placement.tag
    finally:
        import FreeCAD as App

        App.closeDocument(doc.Name)


def test_all_12_fixtures_build_cleanly() -> None:
    from ifsm.components import build_detector_fixture

    cfg, placements = _load_cfg_and_placements()
    assert len(placements) == 12, f"expected 12 placements, got {len(placements)}"
    doc = _new_doc("task10_all_placements")
    try:
        for placement in placements:
            result = build_detector_fixture(doc, cfg.geometry, placement)
            for body_key in ("housing", "weldment", "upper_clamp", "base_plate"):
                feat = result[body_key]
                assert len(feat.Shape.Solids) == 1, (
                    f"{placement.tag}.{body_key}: expected 1 solid, got {len(feat.Shape.Solids)}"
                )
                assert feat.Shape.Volume > 1e-6, (
                    f"{placement.tag}.{body_key}: near-zero volume"
                )
            # fastener solids should all be valid.
            for entry in result["fasteners"]:
                solid = entry["solid"]
                assert not solid.isNull()
                assert solid.Volume > 1e-6
    finally:
        import FreeCAD as App

        App.closeDocument(doc.Name)


def test_fixture_honors_draw_fasteners_flag() -> None:
    import copy

    from ifsm.components import build_detector_fixture

    cfg, placements = _load_cfg_and_placements()
    placement = placements[0]
    # Copy the geometry config and flip the flag without mutating the cached
    # cfg for any later test. The clamp config is a frozen dataclass, so
    # dataclasses.replace is the safe path.
    import dataclasses

    geometry = cfg.geometry
    new_clamp = dataclasses.replace(
        geometry.detector.clamp,
        draw_fasteners_as_solids=False,
    )
    new_detector = dataclasses.replace(geometry.detector, clamp=new_clamp)
    new_geometry = dataclasses.replace(geometry, detector=new_detector)

    doc = _new_doc("task10_flag_off")
    try:
        result = build_detector_fixture(doc, new_geometry, placement)
        assert result["fasteners"] == [], "fasteners should be empty when flag is False"
        # Bodies are still present.
        for body_key in ("housing", "weldment", "upper_clamp", "base_plate"):
            assert len(result[body_key].Shape.Solids) == 1
    finally:
        import FreeCAD as App

        App.closeDocument(doc.Name)
