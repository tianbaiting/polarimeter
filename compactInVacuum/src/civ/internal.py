from __future__ import annotations

from dataclasses import dataclass

import Part

from .cartridge import SectorHolderGeometry, build_sector_holder
from .config import CIVConfig
from .layout import DetectorPlacement
from .target import TargetSystemGeometry, build_target_system


@dataclass(frozen=True)
class InternalAssemblyGeometry:
    placements: tuple[DetectorPlacement, ...]
    sector_holders: dict[str, SectorHolderGeometry]
    target: TargetSystemGeometry
    physical: dict[str, Part.Shape]
    purchased_interfaces: dict[str, Part.Shape]
    interfaces: dict[str, Part.Shape]
    keepouts: dict[str, Part.Shape]
    datums: dict[str, Part.Shape]
    materials: dict[str, str]
    thermal_connections: tuple[tuple[str, str], ...]


def build_internal_assembly(cfg: CIVConfig) -> InternalAssemblyGeometry:
    if cfg.compact_one is None:
        raise ValueError("internal assembly requires a CompactOne schema-v3 configuration")
    sector_holders = {
        sector: build_sector_holder(cfg, sector)
        for sector in cfg.sectors
    }
    target = build_target_system(cfg)
    physical: dict[str, Part.Shape] = {}
    purchased_interfaces: dict[str, Part.Shape] = {}
    interfaces: dict[str, Part.Shape] = {}
    keepouts: dict[str, Part.Shape] = {}
    datums: dict[str, Part.Shape] = {}
    materials: dict[str, str] = {}
    thermal_connections: list[tuple[str, str]] = []
    placements: list[DetectorPlacement] = []

    for holder in sector_holders.values():
        placements.extend(holder.placements)
        physical.update(holder.physical)
        purchased_interfaces.update(holder.purchased_interfaces)
        interfaces.update(holder.interfaces)
        keepouts.update(holder.keepouts)
        datums.update(holder.datums)
        materials.update(holder.materials)
        thermal_connections.extend(holder.thermal_connections)

    physical.update(target.stationary)
    materials.update(
        {
            name: target.materials[name]
            for name in target.stationary
        }
    )
    for name, shape in target.work.physical.items():
        key = f"TargetWork_{name}"
        physical[key] = shape
        materials[key] = target.materials[name]
    interfaces.update(target.interfaces)
    keepouts.update(target.keepouts)
    datums.update(target.datums)
    return InternalAssemblyGeometry(
        placements=tuple(placements),
        sector_holders=sector_holders,
        target=target,
        physical=physical,
        purchased_interfaces=purchased_interfaces,
        interfaces=interfaces,
        keepouts=keepouts,
        datums=datums,
        materials=materials,
        thermal_connections=tuple(thermal_connections),
    )


def internal_compound(geometry: InternalAssemblyGeometry) -> Part.Shape:
    return Part.makeCompound(list(geometry.physical.values()))
