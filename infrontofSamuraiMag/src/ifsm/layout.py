from __future__ import annotations

import math
from dataclasses import dataclass

import FreeCAD as App

from .config import ChamberCoreConfig, LayoutConfig


@dataclass(frozen=True)
class DetectorPlacement:
    channel_name: str
    sector_name: str
    angle_deg: float
    radius_mm: float
    confidence: str
    direction: App.Vector

    @property
    def tag(self) -> str:
        return f"{self.sector_name}_{self.channel_name}"


def scaled(v: App.Vector, s: float) -> App.Vector:
    return App.Vector(v.x * s, v.y * s, v.z * s)


def dot(a: App.Vector, b: App.Vector) -> float:
    return (a.x * b.x) + (a.y * b.y) + (a.z * b.z)


def norm(v: App.Vector) -> float:
    return math.sqrt(dot(v, v))


def normalize(v: App.Vector) -> App.Vector:
    n = norm(v)
    if n <= 0.0:
        raise ValueError("cannot normalize zero vector")
    return scaled(v, 1.0 / n)


def sector_direction_from_theta(angle_deg: float, sector_name: str) -> App.Vector:
    theta = math.radians(angle_deg)
    s = math.sin(theta)
    c = math.cos(theta)

    # [EN] The four sectors are frozen as side exits around the +z beam axis, so only one transverse component changes sign while the forward z component stays positive. / [CN] 四个扇区被冻结为围绕 +z 束轴的侧向出射，因此只改变一个横向分量的符号，而前向 z 分量始终保持为正。
    if sector_name == "left":
        return App.Vector(-s, 0.0, c)
    if sector_name == "right":
        return App.Vector(s, 0.0, c)
    if sector_name == "up":
        return App.Vector(0.0, s, c)
    if sector_name == "down":
        return App.Vector(0.0, -s, c)
    raise ValueError(f"unsupported sector_name: {sector_name}")


def build_detector_placements(layout_cfg: LayoutConfig) -> list[DetectorPlacement]:
    # [EN] BLP v1 layout is the Cartesian product of 3 channel radii/angles with 4 sectors, yielding the full 12-detector placement set used everywhere else. / [CN] BLP v1 布局是 3 条通道半径/角度与 4 个扇区的笛卡尔积，得到后续各处统一使用的 12 个探测器落位。
    placements: list[DetectorPlacement] = []
    for channel in layout_cfg.channels:
        for sector in layout_cfg.sectors:
            placements.append(
                DetectorPlacement(
                    channel_name=channel.name,
                    sector_name=sector,
                    angle_deg=channel.angle_deg,
                    radius_mm=channel.radius_mm,
                    confidence=channel.confidence,
                    direction=normalize(sector_direction_from_theta(channel.angle_deg, sector)),
                )
            )
    return placements


def local_basis_from_direction(direction: App.Vector) -> tuple[App.Vector, App.Vector, App.Vector]:
    u = normalize(direction)
    ref = App.Vector(0.0, 1.0, 0.0)
    # [EN] Swap the reference axis near parallel cases so the local frame remains numerically stable for extrusions around shallow/steep detector directions. / [CN] 当方向几乎平行时切换参考轴，保证围绕浅角或陡角探测器方向建立的局部坐标系仍然数值稳定。
    if abs(dot(u, ref)) > 0.95:
        ref = App.Vector(1.0, 0.0, 0.0)
    v = normalize(ref.cross(u))
    w = normalize(u.cross(v))
    return u, v, w


def front_face_center(placement: DetectorPlacement) -> App.Vector:
    # [EN] Front-face center is the invariant detector constraint from channel angle/radius, independent from fixture details. / [CN] 前端面中心由通道角度与半径唯一约束，与夹具细节解耦。
    return scaled(placement.direction, placement.radius_mm)


def azimuth_deg(point: App.Vector) -> float:
    return math.degrees(math.atan2(point.y, point.x))


def plate_key_for_sector(sector_name: str) -> str:
    if sector_name in {"left", "right"}:
        return "h"
    if sector_name == "up":
        return "v1"
    if sector_name == "down":
        return "v2"
    raise ValueError(f"unsupported sector_name: {sector_name}")


def chamber_z_bounds(core: ChamberCoreConfig) -> tuple[float, float]:
    half_z = 0.5 * core.size_z_mm
    return (core.center_z_mm - half_z, core.center_z_mm + half_z)


def ray_box_exit_distance(core: ChamberCoreConfig, direction: App.Vector) -> float:
    d = normalize(direction)
    half_x = 0.5 * core.size_x_mm
    half_y = 0.5 * core.size_y_mm
    z_min, z_max = chamber_z_bounds(core)

    candidates: list[float] = []
    if abs(d.x) > 1e-12:
        candidates.append(half_x / abs(d.x))
    if abs(d.y) > 1e-12:
        candidates.append(half_y / abs(d.y))
    if abs(d.z) > 1e-12:
        candidates.append((z_max / d.z) if d.z > 0.0 else (z_min / d.z))

    if not candidates:
        raise ValueError("direction vector has no non-zero component")

    # [EN] The first chamber wall hit is the minimum positive ray parameter among x/y/z slab crossings. / [CN] 射线首先撞到的腔体壁面，就是 x/y/z 三组平板相交参数里最小的正值。
    return min(candidates)


def ray_point_at_z(direction: App.Vector, z_mm: float) -> App.Vector:
    d = normalize(direction)
    if abs(d.z) < 1e-9:
        raise ValueError("ray_point_at_z is undefined for direction with dz ~ 0")
    t = z_mm / d.z
    return scaled(d, t)


def ray_point_at_y(direction: App.Vector, y_mm: float) -> App.Vector:
    d = normalize(direction)
    if abs(d.y) < 1e-9:
        raise ValueError("ray_point_at_y is undefined for direction with dy ~ 0")
    t = y_mm / d.y
    return scaled(d, t)


def ray_point_at_x(direction: App.Vector, x_mm: float) -> App.Vector:
    d = normalize(direction)
    if abs(d.x) < 1e-9:
        raise ValueError("ray_point_at_x is undefined for direction with dx ~ 0")
    t = x_mm / d.x
    return scaled(d, t)
