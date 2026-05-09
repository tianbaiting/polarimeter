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
    # bbox: head sinks above origin (cone going up), shank hangs below 30 mm
    bbox = bolt.BoundBox
    assert bbox.ZMin == pytest.approx(-30.0, abs=1e-4), "shank length 30 below origin"
    # head OD ≈ 8.0 mm for M4 ISO 10642
    expected_head_od = 4.0 * 2.0
    assert bbox.XLength == pytest.approx(expected_head_od, abs=0.01)


def test_csk_bolt_m25_solid_count(freecad) -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_csk_bolt

    bolt = make_csk_bolt("M2.5", 8.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    assert len(bolt.Solids) == 1
    bbox = bolt.BoundBox
    assert bbox.ZMin == pytest.approx(-8.0, abs=1e-4)


def test_csk_bolt_volume_less_than_cylinder_head_equivalent(freecad) -> None:
    """csk head is a cone (smaller volume than equivalent cylinder head)."""
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_csk_bolt, make_hex_socket_bolt

    csk = make_csk_bolt("M4", 30.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    hex_ = make_hex_socket_bolt("M4", 30.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
    # Equal shank, but cone head has roughly 1/3 the volume of a cylinder head
    assert csk.Volume < hex_.Volume
