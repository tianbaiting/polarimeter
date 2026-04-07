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
