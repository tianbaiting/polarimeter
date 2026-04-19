"""Simplified fastener solids for review-quality visual mockup.

These are NOT drawing-class: nut chamfers and thread detail are intentionally
omitted. Use for visualizing bolt placement; BOM text carries the ISO spec.
"""
from __future__ import annotations

import math

import FreeCAD as App
import Part


_BOLT_TABLE: dict[str, dict[str, float]] = {
    "M3": {"shank_d": 3.0, "head_d": 5.5, "head_h": 3.0, "nut_afs": 5.5, "washer_od": 7.0, "washer_id": 3.2, "washer_t": 0.5},
    "M4": {"shank_d": 4.0, "head_d": 7.0, "head_h": 4.0, "nut_afs": 7.0, "washer_od": 9.0, "washer_id": 4.3, "washer_t": 0.8},
    "M5": {"shank_d": 5.0, "head_d": 8.5, "head_h": 5.0, "nut_afs": 8.0, "washer_od": 10.0, "washer_id": 5.3, "washer_t": 1.0},
    "M6": {"shank_d": 6.0, "head_d": 10.0, "head_h": 6.0, "nut_afs": 10.0, "washer_od": 12.0, "washer_id": 6.4, "washer_t": 1.6},
    "M8": {"shank_d": 8.0, "head_d": 13.0, "head_h": 8.0, "nut_afs": 13.0, "washer_od": 16.0, "washer_id": 8.4, "washer_t": 1.6},
    "M10": {"shank_d": 10.0, "head_d": 16.0, "head_h": 10.0, "nut_afs": 17.0, "washer_od": 20.0, "washer_id": 10.5, "washer_t": 2.0},
}


def _lookup(size: str) -> dict[str, float]:
    if size not in _BOLT_TABLE:
        raise KeyError(f"Unsupported fastener size: {size!r}. Known: {sorted(_BOLT_TABLE)}")
    return _BOLT_TABLE[size]


def _hex_prism(center: App.Vector, axis: App.Vector, afs: float, height: float) -> Part.Shape:
    """A hex prism centered on `center`; 'afs' is wrench across flats.

    Built on XY plane then rotated so the prism axis aligns with `axis`.
    """
    radius_across_corners = afs / math.sqrt(3.0)
    vertices = []
    for i in range(6):
        theta = math.radians(30.0 + 60.0 * i)
        vertices.append(App.Vector(radius_across_corners * math.cos(theta),
                                   radius_across_corners * math.sin(theta),
                                   0.0))
    vertices.append(vertices[0])
    wire = Part.makePolygon(vertices)
    face = Part.Face(wire)
    prism = face.extrude(App.Vector(0, 0, height))
    rot = App.Rotation(App.Vector(0, 0, 1), axis)
    prism.Placement = App.Placement(App.Vector(0, 0, 0), rot)
    prism.translate(center)
    return prism


def make_hex_socket_bolt(
    size: str,
    shank_length_mm: float,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    """Origin is the under-head seat face center; axis points from head toward tip."""
    spec = _lookup(size)
    axis_n = App.Vector(axis).normalize()
    head_origin = App.Vector(origin) - App.Vector(axis_n).multiply(spec["head_h"])
    head = Part.makeCylinder(0.5 * spec["head_d"], spec["head_h"], head_origin, axis_n)
    shank = Part.makeCylinder(0.5 * spec["shank_d"], shank_length_mm, App.Vector(origin), axis_n)
    return head.fuse(shank)


def make_hex_nut(
    size: str,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    """Origin is the seat face center; axis perpendicular to the nut face."""
    spec = _lookup(size)
    nut_height = 0.8 * spec["shank_d"]
    axis_n = App.Vector(axis).normalize()
    outer = _hex_prism(App.Vector(origin), axis_n, spec["nut_afs"], nut_height)
    bore_origin = App.Vector(origin) - App.Vector(axis_n).multiply(0.2)
    bore = Part.makeCylinder(0.5 * spec["shank_d"], nut_height + 0.4, bore_origin, axis_n)
    return outer.cut(bore)


def make_flat_washer(
    size: str,
    origin: App.Vector,
    axis: App.Vector,
) -> Part.Shape:
    spec = _lookup(size)
    axis_n = App.Vector(axis).normalize()
    outer = Part.makeCylinder(0.5 * spec["washer_od"], spec["washer_t"], App.Vector(origin), axis_n)
    bore_origin = App.Vector(origin) - App.Vector(axis_n).multiply(0.2)
    bore = Part.makeCylinder(0.5 * spec["washer_id"], spec["washer_t"] + 0.4, bore_origin, axis_n)
    return outer.cut(bore)
