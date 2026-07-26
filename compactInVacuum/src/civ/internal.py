from __future__ import annotations

from dataclasses import dataclass

import Part

from .cartridge import SectorCartridgeGeometry, build_sector_cartridge
from .config import CIVConfig
from .layout import DetectorPlacement
from .target import TargetSystemGeometry, build_target_system


@dataclass(frozen=True)
class InternalAssemblyGeometry:
    placements: tuple[DetectorPlacement, ...]
    cartridges: dict[str, SectorCartridgeGeometry]
    target: TargetSystemGeometry
    physical: dict[str, Part.Shape]
    interfaces: dict[str, Part.Shape]
    keepouts: dict[str, Part.Shape]
    datums: dict[str, Part.Shape]
    materials: dict[str, str]
    thermal_connections: tuple[tuple[str, str], ...]


def build_internal_assembly(cfg: CIVConfig) -> InternalAssemblyGeometry:
    if cfg.compact_one is None:
        raise ValueError("internal assembly requires a CompactOne schema-v2 configuration")
    cartridges = {
        sector: build_sector_cartridge(cfg, sector)
        for sector in cfg.sectors
    }
    target = build_target_system(cfg)
    physical: dict[str, Part.Shape] = {}
    interfaces: dict[str, Part.Shape] = {}
    keepouts: dict[str, Part.Shape] = {}
    datums: dict[str, Part.Shape] = {}
    materials: dict[str, str] = {}
    thermal_connections: list[tuple[str, str]] = []
    placements: list[DetectorPlacement] = []

    for cartridge in cartridges.values():
        placements.extend(cartridge.placements)
        physical.update(cartridge.physical)
        interfaces.update(cartridge.interfaces)
        keepouts.update(cartridge.keepouts)
        datums.update(cartridge.datums)
        materials.update(cartridge.materials)
        thermal_connections.extend(cartridge.thermal_connections)

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
        cartridges=cartridges,
        target=target,
        physical=physical,
        interfaces=interfaces,
        keepouts=keepouts,
        datums=datums,
        materials=materials,
        thermal_connections=tuple(thermal_connections),
    )


def internal_compound(geometry: InternalAssemblyGeometry) -> Part.Shape:
    return Part.makeCompound(list(geometry.physical.values()))
