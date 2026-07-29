from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def test_new_body_returns_fresh_body() -> None:
    import FreeCAD as App
    from ifsm.primitives import new_partdesign_body

    doc = App.newDocument("TestDoc")
    body = new_partdesign_body(doc, "TestBody")
    assert body.TypeId == "PartDesign::Body"
    assert body.Name == "TestBody"


def test_pad_rectangle_profile_produces_single_solid() -> None:
    import FreeCAD as App
    from ifsm.primitives import new_partdesign_body, pad_rectangle

    doc = App.newDocument("TestPad")
    body = new_partdesign_body(doc, "B")
    pad_rectangle(
        body,
        origin=App.Vector(0, 0, 0),
        axis_u=App.Vector(1, 0, 0),
        axis_v=App.Vector(0, 1, 0),
        axis_w=App.Vector(0, 0, 1),
        width_mm=20.0,
        height_mm=10.0,
        pad_length_mm=5.0,
        name="PadRect",
    )
    doc.recompute()
    assert len(body.Shape.Solids) == 1


def test_add_hole_actually_removes_material() -> None:
    """Hole→Pocket carve-out regression: the hole MUST shrink the body volume."""
    import FreeCAD as App
    from ifsm.primitives import new_partdesign_body, pad_rectangle, add_hole

    doc = App.newDocument("TestHole")
    body = new_partdesign_body(doc, "B")
    pad_rectangle(
        body, App.Vector(0, 0, 0),
        App.Vector(1, 0, 0), App.Vector(0, 1, 0), App.Vector(0, 0, 1),
        20.0, 20.0, 10.0, "PadRect",
    )
    doc.recompute()
    pre_volume = body.Shape.Volume
    add_hole(
        body,
        center=App.Vector(0, 0, 0),
        axis=App.Vector(0, 0, 1),
        thread_size="M6",
        depth_mm=5.0,
        name="H0",
    )
    doc.recompute()
    post_volume = body.Shape.Volume
    assert post_volume < pre_volume - 1e-3, (
        f"add_hole did not remove material: pre={pre_volume:.3f}, post={post_volume:.3f}"
    )


def test_select_edges_by_predicate_finds_edges() -> None:
    import FreeCAD as App
    from ifsm.primitives import new_partdesign_body, pad_rectangle, select_edges_by_predicate

    doc = App.newDocument("TestEdges")
    body = new_partdesign_body(doc, "B")
    pad_rectangle(body, App.Vector(0, 0, 0),
                  App.Vector(1, 0, 0), App.Vector(0, 1, 0), App.Vector(0, 0, 1),
                  20.0, 10.0, 5.0, "PadRect")
    doc.recompute()
    edges = select_edges_by_predicate(body, lambda e: True)
    assert len(edges) > 0
    for name in edges:
        assert name.startswith("Edge")
