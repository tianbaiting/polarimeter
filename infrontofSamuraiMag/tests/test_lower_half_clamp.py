"""LowerHalfClamp Body geometry (v1.33 spec §4.1, §4.3, §4.5)."""
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


def _make_lower(cfg, *, mount_mode: str = "combined"):
    import FreeCAD as App
    from dataclasses import replace
    from ifsm.components import build_lower_half_clamp

    clamp_cfg = replace(cfg.geometry.detector.clamp, mount_mode=mount_mode)
    doc = App.newDocument("test_lower")
    body = build_lower_half_clamp(doc, clamp_cfg, placement_tag="proton_large_left")
    return doc, body


def test_lower_single_solid(freecad, cfg) -> None:
    doc, body = _make_lower(cfg)
    assert len(body.Shape.Solids) == 1


def test_lower_outer_dimensions(freecad, cfg) -> None:
    doc, body = _make_lower(cfg)
    bbox = body.Shape.BoundBox
    assert bbox.XLength == pytest.approx(70.0, abs=0.01)  # plate_length
    assert bbox.YLength == pytest.approx(60.0, abs=0.01)  # plate_width
    assert bbox.ZLength == pytest.approx(10.0, abs=0.01)  # plate_thickness


def test_lower_pocket_depth_equals_half_plate_thickness(freecad, cfg) -> None:
    """Cradle pocket depth = plate_t/2 = 5 mm; the residual floor is 5 mm thick."""
    doc, body = _make_lower(cfg)
    expected_floor_z = -5.0  # below origin if top face is at z=0
    # Ask the Body for the lowest point of the pocket curve
    # Strategy: minimum Z over all face vertices that lie above z=-plate_t/2 + 1e-6
    zs = [v.Z for f in body.Shape.Faces for v in f.Vertexes]
    # The pocket floor must be present at z ≈ expected_floor_z
    assert any(abs(z - expected_floor_z) < 0.05 for z in zs), (
        f"expected pocket floor at z={expected_floor_z}; got {sorted(set(zs))[:5]}"
    )


def test_lower_cradle_radius_with_clearance(freecad, cfg) -> None:
    """Cradle radius must equal det_od/2 + cradle_clearance = 25 + 0.1 = 25.1 mm."""
    doc, body = _make_lower(cfg)
    # Find the cylindrical pocket face: a face whose Surface is a Part.Cylinder
    import Part
    cyl_faces = [f for f in body.Shape.Faces if isinstance(f.Surface, Part.Cylinder)]
    assert cyl_faces, "expected at least one cylindrical face (cradle pocket)"
    radii = [f.Surface.Radius for f in cyl_faces]
    assert any(abs(r - 25.1) < 1e-3 for r in radii), f"no cradle face at R=25.1; got {radii}"


def test_lower_clamp_holes_count_combined(freecad, cfg) -> None:
    """In combined mode: 4 csk through-holes for M4 clamp bolts only."""
    doc, body = _make_lower(cfg, mount_mode="combined")
    # Count cylindrical faces with radius near M4 clearance/2 = 2.25 mm
    # M4 clearance hole diameter = 4.5 mm, radius = 2.25 mm
    import Part
    cyl_faces = [f for f in body.Shape.Faces if isinstance(f.Surface, Part.Cylinder)]
    m4_holes = sum(1 for f in cyl_faces if abs(f.Surface.Radius - 2.25) < 0.1)
    assert m4_holes == 4, f"expected 4 M4 clearance holes; got {m4_holes} (radii: {sorted(set(round(f.Surface.Radius,3) for f in cyl_faces))})"


def test_lower_split_mode_adds_mount_holes(freecad, cfg) -> None:
    doc, body = _make_lower(cfg, mount_mode="split")
    import Part
    cyl_faces = [f for f in body.Shape.Faces if isinstance(f.Surface, Part.Cylinder)]
    # M4 clearance r=2.25, M2.5 clearance r=1.45
    m4 = sum(1 for f in cyl_faces if abs(f.Surface.Radius - 2.25) < 0.1)
    m25 = sum(1 for f in cyl_faces if abs(f.Surface.Radius - 1.45) < 0.1)
    assert m4 == 4, f"expected 4 M4 holes in split mode; got {m4}"
    assert m25 == 4, f"expected 4 M2.5 holes in split mode; got {m25}"
