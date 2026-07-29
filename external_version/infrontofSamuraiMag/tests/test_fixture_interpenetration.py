from __future__ import annotations
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def test_validator_passes_on_clean_fixture() -> None:
    import FreeCAD as App
    from ifsm.components import build_detector_fixture
    from ifsm.config import load_build_config
    from ifsm.layout import build_detector_placements
    from ifsm.validation import detector_fixture_no_interpenetration

    cfg = load_build_config(ROOT / "config" / "default_infront.yaml")
    placements = build_detector_placements(cfg.layout)
    doc = App.newDocument("TestValPass")
    try:
        result = build_detector_fixture(doc, cfg.geometry, placements[0])
        status, detail = detector_fixture_no_interpenetration(result, placement_tag=placements[0].tag)
        assert status == "pass", detail
    finally:
        App.closeDocument(doc.Name)


def test_validator_fails_when_weldment_overlaps_base() -> None:
    import FreeCAD as App
    import Part
    from ifsm.validation import detector_fixture_no_interpenetration

    class FakeBody:
        def __init__(self, shape):
            self.Shape = shape

    cyl_a = Part.makeCylinder(5.0, 20.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    cyl_b = Part.makeCylinder(5.0, 20.0, App.Vector(0, 0, 10), App.Vector(0, 0, 1))
    result = {
        "weldment": FakeBody(cyl_a),
        "upper_clamp": FakeBody(Part.makeBox(1, 1, 1, App.Vector(-50, -50, -50))),
        "base_plate": FakeBody(cyl_b),
        "fasteners": [],
    }
    status, detail = detector_fixture_no_interpenetration(result, placement_tag="synthetic")
    assert status == "fail"
    assert "weldment" in detail and "base_plate" in detail


def test_validator_whitelists_bolt_through_hole() -> None:
    import FreeCAD as App
    import Part
    from ifsm.validation import detector_fixture_no_interpenetration

    class FakeBody:
        def __init__(self, shape):
            self.Shape = shape

    plate = Part.makeBox(20, 20, 5, App.Vector(0, 0, 0)).cut(
        Part.makeCylinder(3.0, 5.2, App.Vector(10, 10, -0.1), App.Vector(0, 0, 1))
    )
    bolt = Part.makeCylinder(3.0, 5.0, App.Vector(10, 10, 0), App.Vector(0, 0, 1))
    # [EN] Keep the three named bodies spatially disjoint so only the
    # bolt-vs-base-plate through-hole pair exercises the whitelist. / [CN]
    # 三个命名主体放在空间不相交的位置，仅让螺栓与底板的穿孔配合触发白名单。
    result = {
        "weldment": FakeBody(Part.makeBox(1, 1, 1, App.Vector(-50, -50, -50))),
        "upper_clamp": FakeBody(Part.makeBox(1, 1, 1, App.Vector(-50, 50, -50))),
        "base_plate": FakeBody(plate),
        "fasteners": [
            {"kind": "bolt", "size": "M6", "solid": bolt, "placement": "x", "subtype": "plate_side"}
        ],
    }
    status, detail = detector_fixture_no_interpenetration(result, placement_tag="synthetic")
    assert status == "pass", detail
