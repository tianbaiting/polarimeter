from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


def test_hex_socket_bolt_is_single_solid() -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_hex_socket_bolt

    shape = make_hex_socket_bolt(
        size="M6",
        shank_length_mm=25.0,
        origin=App.Vector(0, 0, 0),
        axis=App.Vector(0, 0, 1),
    )
    assert len(shape.Solids) == 1
    assert shape.Volume > 0.0


def test_hex_nut_is_single_solid() -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_hex_nut

    shape = make_hex_nut(
        size="M6",
        origin=App.Vector(0, 0, 0),
        axis=App.Vector(0, 0, 1),
    )
    assert len(shape.Solids) == 1
    assert shape.Volume > 0.0


def test_flat_washer_is_single_solid() -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_flat_washer

    shape = make_flat_washer(
        size="M6",
        origin=App.Vector(0, 0, 0),
        axis=App.Vector(0, 0, 1),
    )
    assert len(shape.Solids) == 1
    assert shape.Volume > 0.0


def test_unknown_size_raises() -> None:
    import FreeCAD as App
    from ifsm.primitives_fasteners import make_hex_socket_bolt

    with pytest.raises(KeyError):
        make_hex_socket_bolt("M99", 10.0, App.Vector(0, 0, 0), App.Vector(0, 0, 1))
