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


def ray_box_exit_distance(core: ChamberCoreConfig, direction: App.Vector) -> float:
    d = normalize(direction)
    half_x = 0.5 * core.size_x_mm
    half_y = 0.5 * core.size_y_mm
    half_z = 0.5 * core.size_z_mm

    candidates: list[float] = []
    if abs(d.x) > 1e-12:
        candidates.append(half_x / abs(d.x))
    if abs(d.y) > 1e-12:
        candidates.append(half_y / abs(d.y))
    if abs(d.z) > 1e-12:
        candidates.append(half_z / abs(d.z))

    if not candidates:
        raise ValueError("direction vector has no non-zero component")

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
