"""ISO 10642 countersunk hex-socket bolt primitive (v1.33)."""
from __future__ import annotations

import sys
from pathlib import Path

import math

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


@pytest.fixture(scope="module")
def freecad():
    import FreeCAD  # noqa: F401
    import Part  # noqa: F401
    return None


def test_csk_bolt_m4_solid_count(freecad) -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_csk_bolt

    bolt = make_csk_bolt("M4", 30.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    assert len(bolt.Solids) == 1
    # Convention (matches make_hex_socket_bolt): origin = under-head seat face,
    # axis = head→tip. Shank extrudes from origin in +axis (z=0..+30); head
    # extrudes from origin in -axis (z=-head_h..0). For M4, head_h = 4 mm.
    bbox = bolt.BoundBox
    assert bbox.ZMin == pytest.approx(-4.0, abs=1e-4), "head height 4 mm above seat plane"
    assert bbox.ZMax == pytest.approx(30.0, abs=1e-4), "shank length 30 mm below seat plane"
    # Head OD comes from _BOLT_TABLE; for M4 it is 7.0 mm (matches make_hex_socket_bolt).
    # Detector clamp Sketch uses the separate countersink_head_factor cfg field,
    # not this primitive's head_d, to size the plate counterbore.
    assert bbox.XLength == pytest.approx(7.0, abs=0.01)


def test_csk_bolt_m25_solid_count(freecad) -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_csk_bolt

    bolt = make_csk_bolt("M2.5", 8.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    assert len(bolt.Solids) == 1
    bbox = bolt.BoundBox
    assert bbox.ZMin == pytest.approx(-1.5, abs=1e-4), "M2.5 head_h = 1.5 mm"
    assert bbox.ZMax == pytest.approx(8.0, abs=1e-4)


def test_csk_bolt_volume_less_than_cylinder_head_equivalent(freecad) -> None:
    """csk head is a cone (smaller volume than equivalent cylinder head)."""
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_csk_bolt, make_hex_socket_bolt

    csk = make_csk_bolt("M4", 30.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    hex_ = make_hex_socket_bolt("M4", 30.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    # Equal shank, but cone head has roughly 1/3 the volume of a cylinder head
    assert csk.Volume < hex_.Volume
