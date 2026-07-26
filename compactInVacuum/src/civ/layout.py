from __future__ import annotations

import math
from dataclasses import dataclass

import FreeCAD as App

from .config import CIVConfig


@dataclass(frozen=True)
class DetectorPlacement:
    channel_name: str
    sector_name: str
    particle: str
    cm_branches: tuple[str, ...]
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
    length = norm(v)
    if length <= 0.0:
        raise ValueError("cannot normalize zero vector")
    return scaled(v, 1.0 / length)


def sector_direction_from_theta(angle_deg: float, sector_name: str) -> App.Vector:
    theta = math.radians(angle_deg)
    transverse_basis = {
        "left": App.Vector(-1.0, 0.0, 0.0),
        "right": App.Vector(1.0, 0.0, 0.0),
        "up": App.Vector(0.0, 1.0, 0.0),
        "down": App.Vector(0.0, -1.0, 0.0),
    }
    basis = transverse_basis.get(sector_name)
    if basis is None:
        raise ValueError(f"unsupported sector_name: {sector_name}")
    return normalize(
        App.Vector(
            basis.x * math.sin(theta),
            basis.y * math.sin(theta),
            math.cos(theta),
        )
    )


def build_detector_placements(cfg: CIVConfig) -> list[DetectorPlacement]:
    placements: list[DetectorPlacement] = []
    for channel in cfg.channels:
        for sector in cfg.sectors:
            placements.append(
                DetectorPlacement(
                    channel_name=channel.name,
                    sector_name=sector,
                    particle=channel.particle,
                    cm_branches=channel.cm_branches,
                    angle_deg=channel.angle_deg,
                    radius_mm=channel.radius_mm,
                    confidence=channel.confidence,
                    direction=sector_direction_from_theta(channel.angle_deg, sector),
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


def detector_center(placement: DetectorPlacement) -> App.Vector:
    return scaled(placement.direction, placement.radius_mm)


def target_facing_active_face_center(
    placement: DetectorPlacement,
    detector_length_mm: float,
) -> App.Vector:
    return scaled(placement.direction, placement.radius_mm - (0.5 * detector_length_mm))


def detector_outer_face_center(
    placement: DetectorPlacement,
    detector_length_mm: float,
) -> App.Vector:
    return scaled(placement.direction, placement.radius_mm + (0.5 * detector_length_mm))
