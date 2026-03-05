from __future__ import annotations

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
