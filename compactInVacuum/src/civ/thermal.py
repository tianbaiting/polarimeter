from __future__ import annotations

from dataclasses import dataclass
from collections import deque

import Part

from .config import CIVConfig
from .internal import InternalAssemblyGeometry


@dataclass(frozen=True)
class ChannelThermalPath:
    channel_tag: str
    connected: bool
    component_path: tuple[str, ...]
    maximum_contact_gap_mm: float


@dataclass(frozen=True)
class ThermalPathReport:
    status: str
    floating_allowed: bool
    channels: tuple[ChannelThermalPath, ...]


def _find_path(
    graph: dict[str, set[str]],
    start: str,
    destination: str,
) -> tuple[str, ...]:
    queue: deque[tuple[str, ...]] = deque([(start,)])
    visited = {start}
    while queue:
        path = queue.popleft()
        node = path[-1]
        if node == destination:
            return path
        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((*path, neighbor))
    return ()


def evaluate_thermal_paths(
    cfg: CIVConfig,
    internal: InternalAssemblyGeometry,
) -> ThermalPathReport:
    if cfg.compact_one is None:
        raise ValueError("thermal audit requires a CompactOne schema-v2 configuration")
    graph: dict[str, set[str]] = {}
    for name_a, name_b in internal.thermal_connections:
        graph.setdefault(name_a, set()).add(name_b)
        graph.setdefault(name_b, set()).add(name_a)
    shapes: dict[str, Part.Shape] = {
        **internal.physical,
        **internal.interfaces,
    }
    channel_reports: list[ChannelThermalPath] = []
    for placement in internal.placements:
        start = f"{placement.tag}_SiPM"
        destination = f"{placement.sector_name}_ChamberMountInterface"
        path = _find_path(graph, start, destination)
        gaps = tuple(
            float(shapes[name_a].distToShape(shapes[name_b])[0])
            for name_a, name_b in zip(path, path[1:])
        )
        channel_reports.append(
            ChannelThermalPath(
                channel_tag=placement.tag,
                connected=bool(path),
                component_path=path,
                maximum_contact_gap_mm=max(gaps, default=float("inf")),
            )
        )
    passed = all(
        item.connected and item.maximum_contact_gap_mm <= 1.0e-6
        for item in channel_reports
    )
    return ThermalPathReport(
        status="pass" if passed else "fail",
        floating_allowed=cfg.compact_one.thermal.floating_allowed,
        channels=tuple(channel_reports),
    )
