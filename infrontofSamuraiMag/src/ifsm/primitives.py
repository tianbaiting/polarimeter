from __future__ import annotations

import math

import FreeCAD as App
import Part

from .layout import local_basis_from_direction, scaled


def slit_prism(
    center: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_w: App.Vector,
    length_mm: float,
    width_mm: float,
    height_mm: float,
) -> Part.Shape:
    # [EN] Build the prism in a caller-supplied local basis so rotated plates, ribs, and fixture blocks reuse one extrusion primitive without re-deriving face topology each time. / [CN] 在调用方提供的局部坐标系中构造棱柱，使旋转板件、加劲肋和夹具块体复用同一个拉伸原语，无需每次重新推导面拓扑。
    start_center = center - scaled(axis_u, 0.5 * length_mm)
    p1 = start_center + scaled(axis_v, -0.5 * width_mm) + scaled(axis_w, -0.5 * height_mm)
    p2 = start_center + scaled(axis_v, 0.5 * width_mm) + scaled(axis_w, -0.5 * height_mm)
    p3 = start_center + scaled(axis_v, 0.5 * width_mm) + scaled(axis_w, 0.5 * height_mm)
    p4 = start_center + scaled(axis_v, -0.5 * width_mm) + scaled(axis_w, 0.5 * height_mm)
    wire = Part.makePolygon([p1, p2, p3, p4, p1])
    face = Part.Face(wire)
    return face.extrude(scaled(axis_u, length_mm))


def tube_shape(
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    length_mm: float,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    outer = Part.makeCylinder(0.5 * outer_diameter_mm, length_mm, origin, axis)
    # [EN] Extend the inner bore slightly past the outer solid to avoid coincident boolean faces, which are a common source of unstable OCC shell results. / [CN] 让内孔比外实体略微超出一些，避免布尔运算出现共面面片，这是 OCC 壳体不稳定的常见来源。
    inner = Part.makeCylinder(
        0.5 * inner_diameter_mm,
        length_mm + 0.4,
        origin - scaled(axis, 0.2),
        axis,
    )
    return outer.cut(inner)


def ring_shape(
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    thickness_mm: float,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    return tube_shape(
        outer_diameter_mm=outer_diameter_mm,
        inner_diameter_mm=inner_diameter_mm,
        length_mm=thickness_mm,
        origin=origin,
        axis=axis,
    )


def square_ring_shape(
    outer_size_mm: float,
    inner_size_mm: float,
    thickness_mm: float,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    axis_u, axis_v, axis_w = local_basis_from_direction(axis)
    # [EN] Square rings preserve Cartesian clearance around a circular beam/fixture axis when the surrounding hardware is plate-like rather than rotationally symmetric. / [CN] 当周边硬件是板式而非旋转对称结构时，方环能在圆形束流/夹具轴周围保留笛卡尔方向净空。
    center = origin + scaled(axis_u, 0.5 * thickness_mm)
    outer = slit_prism(
        center=center,
        axis_u=axis_u,
        axis_v=axis_v,
        axis_w=axis_w,
        length_mm=thickness_mm,
        width_mm=outer_size_mm,
        height_mm=outer_size_mm,
    )
    inner = slit_prism(
        center=center,
        axis_u=axis_u,
        axis_v=axis_v,
        axis_w=axis_w,
        length_mm=thickness_mm + 0.4,
        width_mm=inner_size_mm,
        height_mm=inner_size_mm,
    )
    return outer.cut(inner)


def rectangular_channel_cut(
    length_mm: float,
    width_mm: float,
    height_mm: float,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    axis_u, axis_v, axis_w = local_basis_from_direction(axis)
    # [EN] Channel cuts follow the ray-aligned local basis so vacuum/clearance corridors stay centered on the physical flight direction instead of a global axis shortcut. / [CN] 通道切口沿射线方向局部坐标系生成，使真空/净空走廊始终对准真实飞行方向，而不是简化成全局轴向近似。
    center = origin + scaled(axis_u, 0.5 * length_mm)
    return slit_prism(
        center=center,
        axis_u=axis_u,
        axis_v=axis_v,
        axis_w=axis_w,
        length_mm=length_mm,
        width_mm=width_mm,
        height_mm=height_mm,
    )


def add_feature(doc: App.Document, name: str, shape: Part.Shape) -> App.DocumentObject:
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


# --- PartDesign helpers (added for Sub-2 detector clamp weldment redesign) ---

import Sketcher  # type: ignore  # noqa: E402


def _ensure_partdesign() -> None:
    """Ensure the PartDesign workbench C++ extension is loaded.

    FreeCAD ships PartDesign in /usr/share/freecad/Mod/PartDesign (a Python
    package that loads the _PartDesign.so extension). When running headless
    (e.g. under pytest with PYTHONPATH=/usr/lib/freecad-python3/lib only), that
    directory is not automatically on sys.path. This function adds it once so
    that `doc.addObject('PartDesign::Body', ...)` succeeds without requiring
    callers to extend PYTHONPATH manually.
    """
    import importlib
    import sys
    if importlib.util.find_spec("PartDesign") is None:
        _freecad_share_mod = "/usr/share/freecad/Mod"
        if _freecad_share_mod not in sys.path:
            sys.path.insert(0, _freecad_share_mod)
    # Trigger the import so the C++ extension registers PartDesign::Body
    try:
        import PartDesign  # type: ignore  # noqa: F401
    except ImportError:
        pass  # Best-effort — let the caller surface the error naturally


def new_partdesign_body(doc: App.Document, name: str):
    """Create a PartDesign::Body attached to the active document."""
    _ensure_partdesign()
    return doc.addObject("PartDesign::Body", name)


def pad_rectangle(
    body,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_w: App.Vector,
    width_mm: float,
    height_mm: float,
    pad_length_mm: float,
    name: str,
):
    """Sketch an axis-aligned rectangle on the (u,v) plane at origin, pad along axis_w.

    Rectangle is centered at origin in the sketch plane. Pad is symmetric
    (Midplane=True) so the solid is centered on the sketch plane along `axis_w`.
    """
    sketch = body.newObject("Sketcher::SketchObject", f"Sketch_{name}")
    placement = App.Placement()
    placement.Base = App.Vector(origin)
    rot = App.Rotation(App.Vector(0, 0, 1), App.Vector(axis_w))
    placement.Rotation = rot
    sketch.Placement = placement
    half_w = 0.5 * width_mm
    half_h = 0.5 * height_mm
    p1 = App.Vector(-half_w, -half_h, 0)
    p2 = App.Vector(half_w, -half_h, 0)
    p3 = App.Vector(half_w, half_h, 0)
    p4 = App.Vector(-half_w, half_h, 0)
    sketch.addGeometry(Part.LineSegment(p1, p2), False)
    sketch.addGeometry(Part.LineSegment(p2, p3), False)
    sketch.addGeometry(Part.LineSegment(p3, p4), False)
    sketch.addGeometry(Part.LineSegment(p4, p1), False)
    for i in range(4):
        sketch.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
    pad = body.newObject("PartDesign::Pad", f"Pad_{name}")
    pad.Profile = sketch
    pad.Length = pad_length_mm
    pad.Midplane = True
    body.Document.recompute()
    return pad


def pad_half_annulus(
    body,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_w: App.Vector,
    outer_diameter_mm: float,
    inner_diameter_mm: float,
    pad_length_mm: float,
    name: str,
):
    """Sketch a half-annulus and pad symmetrically along `axis_u`."""
    sketch = body.newObject("Sketcher::SketchObject", f"Sketch_{name}")
    placement = App.Placement()
    placement.Base = App.Vector(origin)
    rot = App.Rotation(App.Vector(0, 0, 1), App.Vector(axis_u))
    placement.Rotation = rot
    sketch.Placement = placement
    ro = 0.5 * outer_diameter_mm
    ri = 0.5 * inner_diameter_mm
    outer_arc = Part.ArcOfCircle(
        Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ro),
        0.0, math.pi,
    )
    inner_arc = Part.ArcOfCircle(
        Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), ri),
        0.0, math.pi,
    )
    left_seg = Part.LineSegment(App.Vector(-ro, 0, 0), App.Vector(-ri, 0, 0))
    right_seg = Part.LineSegment(App.Vector(ri, 0, 0), App.Vector(ro, 0, 0))
    sketch.addGeometry(outer_arc, False)
    sketch.addGeometry(left_seg, False)
    sketch.addGeometry(inner_arc, False)
    sketch.addGeometry(right_seg, False)
    sketch.addConstraint(Sketcher.Constraint("Coincident", 0, 1, 1, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", 1, 2, 2, 2))
    sketch.addConstraint(Sketcher.Constraint("Coincident", 2, 1, 3, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", 3, 2, 0, 2))
    pad = body.newObject("PartDesign::Pad", f"Pad_{name}")
    pad.Profile = sketch
    pad.Length = pad_length_mm
    pad.Midplane = True
    body.Document.recompute()
    return pad


def add_fillet(body, radius_mm: float, edge_names: list[str], name: str):
    """Add PartDesign::Fillet on specified edges. Base is (body, edges)."""
    fillet = body.newObject("PartDesign::Fillet", f"Fillet_{name}")
    fillet.Base = (body, edge_names)
    fillet.Radius = radius_mm
    body.Document.recompute()
    return fillet


def add_chamfer(body, size_mm: float, edge_names: list[str], name: str):
    chamfer = body.newObject("PartDesign::Chamfer", f"Chamfer_{name}")
    chamfer.Base = (body, edge_names)
    chamfer.Size = size_mm
    body.Document.recompute()
    return chamfer


_CLEARANCE_D: dict[str, float] = {
    "M2.5": 2.9,
    "M3": 3.4,
    "M4": 4.5,
    "M5": 5.5,
    "M6": 6.6,
    "M8": 9.0,
    "M10": 11.0,
}


def add_hole(
    body,
    center: App.Vector,
    axis: App.Vector,
    thread_size: str,
    depth_mm: float,
    name: str,
):
    """Cut a clearance hole at `center` normal to `axis`.

    Implemented as PartDesign::Pocket on a circular sketch — PartDesign::Hole
    is a headless no-op per Phase 0 spike. Thread metadata is NOT represented
    in geometry; it belongs on drawings/BOM. Clearance diameter from a fixed
    ISO-ish table keyed by `thread_size`.
    """
    sketch = body.newObject("Sketcher::SketchObject", f"Sketch_{name}")
    placement = App.Placement()
    placement.Base = App.Vector(center)
    rot = App.Rotation(App.Vector(0, 0, 1), App.Vector(axis))
    placement.Rotation = rot
    sketch.Placement = placement
    clearance_d = _CLEARANCE_D[thread_size]
    sketch.addGeometry(
        Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 0.5 * clearance_d),
        False,
    )
    pocket = body.newObject("PartDesign::Pocket", f"Hole_{name}")
    pocket.Profile = sketch
    pocket.Length = depth_mm
    pocket.Type = 0
    body.Document.recompute()
    return pocket


def pocket_cradle_through_axis(
    body,
    center: App.Vector,
    axis_along: App.Vector,
    cradle_radius_mm: float,
    cradle_depth_mm: float,
    plate_length_mm: float,
    name: str,
):
    """Shallow cradle (circular-segment) trough pocket running the full plate length.

    Sketches a circular arc segment profile on the plane perpendicular to
    `axis_along` at `center`. The flat chord lies on the mating face (top face
    of the lower half-clamp); the arc bulges into the plate by `cradle_depth_mm`.
    The pocket extrudes symmetrically in both ±axis_along directions
    (Midplane=True, total length = plate_length_mm) producing a U-shaped trough
    open at both ends.

    `center` should be placed at the detector-axis / mating-face intersection.

    Sketch local frame after rotation taking local-Z → axis_along = X (global):
      - local X → global -Z  (moving in +local_X = going INTO the plate)
      - local Y → global  Y  (plate width direction)
      - local Z → global  X  (extrusion / axis_along direction)

    Circle center is at local (-(R-depth), 0) so the deepest arc point sits
    at local (+depth, 0) = depth below the mating face (into the plate).
    The arc spans the SHORT path from local (0, -a) → (+depth, 0) → (0, +a),
    i.e., ArcOfCircle from angle -half_angle to +half_angle (CCW through 0).
    a = sqrt(R^2 - (R-depth)^2) is the chord half-width.
    """
    R = cradle_radius_mm
    d = cradle_depth_mm
    a = math.sqrt(R * R - (R - d) * (R - d))  # chord half-width
    half_angle = math.acos((R - d) / R)        # arc half-angle from 0

    # Circle center: local (-(R-d), 0) so arc's rightmost (deepest into plate) point
    # is at local (-(R-d)+R, 0) = (+d, 0). Chord endpoints: local (0, ±a).
    cx = -(R - d)  # e.g. -20.1 for R=25.1, d=5

    sketch = body.newObject("Sketcher::SketchObject", f"Sketch_{name}")
    placement = App.Placement()
    placement.Base = App.Vector(center)
    rot = App.Rotation(App.Vector(0, 0, 1), App.Vector(axis_along))
    placement.Rotation = rot
    sketch.Placement = placement

    # Arc CCW from -half_angle to +half_angle, passing through 0 (deepest point).
    # StartPoint at angle -half_angle: center + R*(cos(-α), sin(-α)) = (0, -a)
    # EndPoint at angle +half_angle:   center + R*(cos(+α), sin(+α)) = (0, +a)
    arc = Part.ArcOfCircle(
        Part.Circle(App.Vector(cx, 0, 0), App.Vector(0, 0, 1), R),
        -half_angle,   # start: (0, -a)
        +half_angle,   # end:   (0, +a)
    )
    # Chord closes the profile: from arc.EndPoint (0, +a) back to arc.StartPoint (0, -a)
    chord = Part.LineSegment(App.Vector(0, a, 0), App.Vector(0, -a, 0))
    sketch.addGeometry(arc, False)
    sketch.addGeometry(chord, False)
    sketch.addConstraint(Sketcher.Constraint("Coincident", 0, 2, 1, 1))  # arc end → chord start
    sketch.addConstraint(Sketcher.Constraint("Coincident", 1, 2, 0, 1))  # chord end → arc start

    pocket = body.newObject("PartDesign::Pocket", f"Pocket_{name}")
    pocket.Profile = sketch
    pocket.Length = plate_length_mm
    pocket.Midplane = True
    body.Document.recompute()
    return pocket


def add_csk_hole(
    body,
    center: App.Vector,
    axis: App.Vector,
    thread_size: str,
    head_diameter_mm: float,
    head_depth_mm: float,
    depth_mm: float,
    name: str,
):
    """Countersunk through-hole: clearance shank + conical/cylindrical countersink.

    Implemented as two chained PartDesign::Pocket features:
    1. Full-depth clearance hole (diameter = _CLEARANCE_D[thread_size])
    2. Countersink pocket (diameter = head_diameter_mm, depth = head_depth_mm)
       on the entry face (center).

    Both pockets share the same sketch placement (axis normal at `center`).
    The countersink pocket is cut second so it widens the entry end only.
    """
    clearance_d = _CLEARANCE_D[thread_size]

    # 1. Full-depth clearance hole
    sk_shank = body.newObject("Sketcher::SketchObject", f"Sketch_{name}_shank")
    placement = App.Placement()
    placement.Base = App.Vector(center)
    rot = App.Rotation(App.Vector(0, 0, 1), App.Vector(axis))
    placement.Rotation = rot
    sk_shank.Placement = placement
    sk_shank.addGeometry(
        Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 0.5 * clearance_d),
        False,
    )
    pocket_shank = body.newObject("PartDesign::Pocket", f"Hole_{name}_shank")
    pocket_shank.Profile = sk_shank
    pocket_shank.Length = depth_mm
    pocket_shank.Type = 0
    body.Document.recompute()

    # 2. Countersink (entry-face widening)
    sk_csk = body.newObject("Sketcher::SketchObject", f"Sketch_{name}_csk")
    sk_csk.Placement = placement  # same placement — entry face
    sk_csk.addGeometry(
        Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), 0.5 * head_diameter_mm),
        False,
    )
    pocket_csk = body.newObject("PartDesign::Pocket", f"Hole_{name}_csk")
    pocket_csk.Profile = sk_csk
    pocket_csk.Length = head_depth_mm
    pocket_csk.Type = 0
    body.Document.recompute()

    return pocket_csk


def select_edges_by_predicate(body, predicate) -> list[str]:
    """Return edge names ('Edge1', 'Edge2', ...) passing the predicate on edge shape."""
    names: list[str] = []
    for idx, edge in enumerate(body.Shape.Edges, start=1):
        if predicate(edge):
            names.append(f"Edge{idx}")
    return names
