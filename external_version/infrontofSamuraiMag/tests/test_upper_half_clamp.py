"""UpperHalfClamp Body geometry (v1.33 spec §4.1, §4.3)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytestmark = pytest.mark.freecad_runtime


@pytest.fixture(scope="module")
def freecad():
    import FreeCAD  # noqa: F401
    return None


@pytest.fixture()
def cfg():
    from ifsm.config import load_target
    return load_target("infrontofSamuraiMag/config/default_infront.yaml")


def _make_upper(cfg, *, mount_mode: str = "combined"):
    import FreeCAD as App
    from dataclasses import replace
    from ifsm.components import build_upper_half_clamp

    clamp_cfg = replace(cfg.geometry.detector.clamp, mount_mode=mount_mode)
    doc = App.newDocument("test_upper")
    body = build_upper_half_clamp(doc, clamp_cfg, placement_tag="proton_large_left")
    return doc, body


def test_upper_single_solid(freecad, cfg) -> None:
    doc, body = _make_upper(cfg)
    assert len(body.Shape.Solids) == 1


def test_upper_dimensions_match_lower(freecad, cfg) -> None:
    doc, body = _make_upper(cfg)
    bbox = body.Shape.BoundBox
    assert bbox.XLength == pytest.approx(70.0, abs=0.01)
    assert bbox.YLength == pytest.approx(60.0, abs=0.01)
    assert bbox.ZLength == pytest.approx(10.0, abs=0.01)


def test_upper_cradle_radius(freecad, cfg) -> None:
    import Part
    doc, body = _make_upper(cfg)
    cyl_faces = [f for f in body.Shape.Faces if isinstance(f.Surface, Part.Cylinder)]
    assert any(abs(f.Surface.Radius - 25.1) < 1e-3 for f in cyl_faces)


def test_upper_has_no_mount_holes_in_split_mode(freecad, cfg) -> None:
    """Spec §4.1: only the lower body carries mount holes."""
    import Part
    doc, body = _make_upper(cfg, mount_mode="split")
    cyl_faces = [f for f in body.Shape.Faces if isinstance(f.Surface, Part.Cylinder)]
    m25_holes = sum(1 for f in cyl_faces if abs(f.Surface.Radius - 1.45) < 0.1)
    assert m25_holes == 0


def test_upper_clamp_holes_count(freecad, cfg) -> None:
    import Part
    doc, body = _make_upper(cfg, mount_mode="combined")
    cyl_faces = [f for f in body.Shape.Faces if isinstance(f.Surface, Part.Cylinder)]
    m4_holes = sum(1 for f in cyl_faces if abs(f.Surface.Radius - 2.25) < 0.1)
    assert m4_holes == 4
