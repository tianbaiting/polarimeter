from __future__ import annotations

from dataclasses import dataclass
import math

import FreeCAD as App
import Part

from .config import CIVConfig
from .platform import FeedthroughInterfaceSpec, ServicePortPlacementSpec


@dataclass(frozen=True)
class FeedthroughPortGeometry:
    port: ServicePortPlacementSpec
    wall_center: App.Vector
    physical: dict[str, Part.Shape]
    purchased_interfaces: dict[str, Part.Shape]
    keepouts: dict[str, Part.Shape]
    datums: dict[str, Part.Shape]
    materials: dict[str, str]
    channel_entry_points: tuple[App.Vector, ...]


def service_wall_y_mm(cfg: CIVConfig, x_mm: float) -> float:
    half_x_mm = 0.5 * cfg.vessel.inner_size_x_mm
    half_y_mm = 0.5 * cfg.vessel.inner_size_y_mm
    if cfg.vessel.cross_section == "square":
        return half_y_mm
    normalized_x = x_mm / half_x_mm
    if abs(normalized_x) >= 1.0:
        raise ValueError("service port lies outside the cylindrical chamber chord")
    return half_y_mm * math.sqrt(1.0 - normalized_x * normalized_x)


def _interface_for_role(
    cfg: CIVConfig,
    role: str,
) -> FeedthroughInterfaceSpec | None:
    services = cfg.compact_one.services
    if role == "signal":
        return services.signal_interface
    return None


def _channel_points(
    center: App.Vector,
    count: int,
    clear_bore_mm: float,
) -> tuple[App.Vector, ...]:
    if count <= 0:
        return ()
    radius_mm = min(0.22 * clear_bore_mm, 7.0)
    return tuple(
        center
        + App.Vector(
            radius_mm * math.cos(2.0 * math.pi * index / count),
            0.0,
            radius_mm * math.sin(2.0 * math.pi * index / count),
        )
        for index in range(count)
    )


def build_feedthrough_port(
    cfg: CIVConfig,
    port: ServicePortPlacementSpec,
) -> FeedthroughPortGeometry:
    if cfg.compact_one is None:
        raise ValueError("feedthrough geometry requires a CompactOne schema-v3 configuration")
    services = cfg.compact_one.services
    routing = services.routing
    wall_center = App.Vector(
        port.center_x_mm,
        service_wall_y_mm(cfg, port.center_x_mm),
        port.center_z_mm,
    )
    axis = App.Vector(0.0, 1.0, 0.0)
    collar_outer = Part.makeCylinder(
        0.5 * port.collar_outer_diameter_mm,
        port.collar_length_mm,
        wall_center,
        axis,
    )
    collar_bore = Part.makeCylinder(
        0.5 * port.bore_diameter_mm,
        port.collar_length_mm + 0.4,
        wall_center - App.Vector(0.0, 0.2, 0.0),
        axis,
    )
    collar = collar_outer.cut(collar_bore)
    interface_spec = _interface_for_role(cfg, port.role)
    if interface_spec is None:
        interface_outer_mm = port.collar_outer_diameter_mm
        interface_thickness_mm = 15.0
        clear_bore_mm = port.bore_diameter_mm
        channel_count = 1
    else:
        interface_outer_mm = interface_spec.module_outer_diameter_mm
        interface_thickness_mm = interface_spec.module_thickness_mm
        clear_bore_mm = interface_spec.nominal_clear_bore_mm
        channel_count = services.channels_per_signal_feedthrough
    interface_base = wall_center + App.Vector(0.0, port.collar_length_mm, 0.0)
    interface_envelope = Part.makeCylinder(
        0.5 * interface_outer_mm,
        interface_thickness_mm,
        interface_base,
        axis,
    )
    connector_base = interface_base + App.Vector(0.0, interface_thickness_mm, 0.0)
    connector_keepout = Part.makeCylinder(
        0.5 * routing.connector_keepout_diameter_mm,
        routing.connector_keepout_length_mm,
        connector_base,
        axis,
    )
    clear_bore = Part.makeCylinder(
        0.5 * min(clear_bore_mm, port.bore_diameter_mm),
        port.collar_length_mm + interface_thickness_mm,
        wall_center,
        axis,
    )
    return FeedthroughPortGeometry(
        port=port,
        wall_center=wall_center,
        physical={f"{port.name}_ProjectWeldCollar": collar},
        purchased_interfaces={
            f"{port.name}_PurchasedFeedthroughEnvelope": interface_envelope,
        },
        keepouts={
            f"{port.name}_ClearBore": clear_bore,
            f"{port.name}_ExternalConnectorKeepout": connector_keepout,
        },
        datums={
            f"{port.name}_InterfaceCenterDatum": Part.makeSphere(
                0.75,
                interface_base,
            )
        },
        materials={f"{port.name}_ProjectWeldCollar": "stainless_304L"},
        channel_entry_points=_channel_points(
            wall_center - App.Vector(0.0, 0.5, 0.0),
            channel_count,
            min(clear_bore_mm, port.bore_diameter_mm),
        ),
    )
