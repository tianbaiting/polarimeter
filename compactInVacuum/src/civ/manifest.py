from __future__ import annotations

import json
from pathlib import Path

from .config import CIVConfig
from .layout import (
    DetectorPlacement,
    detector_center,
    target_facing_active_face_center,
)


OPPOSITE_SECTOR = {
    "left": "right",
    "right": "left",
    "up": "down",
    "down": "up",
}

SECTOR_TRANSVERSE_AXIS = {
    "left": [-1.0, 0.0, 0.0],
    "right": [1.0, 0.0, 0.0],
    "up": [0.0, 1.0, 0.0],
    "down": [0.0, -1.0, 0.0],
}


def _vector_payload(vector) -> list[float]:
    return [float(vector.x), float(vector.y), float(vector.z)]


def _lrud_group(sector: str) -> str:
    if sector in {"left", "right"}:
        return "lr"
    if sector in {"up", "down"}:
        return "ud"
    raise ValueError(f"unsupported sector: {sector}")


def build_channel_manifest(
    cfg: CIVConfig,
    placements: list[DetectorPlacement],
) -> dict[str, object]:
    if cfg.physics is None:
        raise ValueError("physics configuration is required to build a channel manifest")

    placement_by_key = {
        (placement.channel_name, placement.sector_name): placement
        for placement in placements
    }
    service_port_by_sector = {}
    service_slot_by_channel = {}
    if cfg.top_services is not None:
        service_port_by_sector = {
            port.sector: port
            for port in cfg.top_services.electrical.signal_ports
        }
        service_slot_by_channel = {
            channel.name: idx + 1
            for idx, channel in enumerate(cfg.channels)
        }

    channels: list[dict[str, object]] = []
    for placement in placements:
        center = detector_center(placement)
        target_face = target_facing_active_face_center(placement, cfg.detector.length_mm)
        channel_payload: dict[str, object] = {
                "channel_id": placement.tag,
                "cad_object_name": placement.tag,
                "base_channel": placement.channel_name,
                "particle": placement.particle,
                "cm_branches": list(placement.cm_branches),
                "sector": placement.sector_name,
                "angle_deg": placement.angle_deg,
                "active_center_radius_mm": placement.radius_mm,
                "active_center_mm": _vector_payload(center),
                "target_facing_active_face_radius_mm": (
                    placement.radius_mm - (0.5 * cfg.detector.length_mm)
                ),
                "target_facing_active_face_center_mm": _vector_payload(target_face),
                "outward_unit_direction": _vector_payload(placement.direction),
                "active_shape": "cylinder",
                "active_diameter_mm": cfg.detector.diameter_mm,
                "active_length_mm": cfg.detector.length_mm,
                "geometry_confidence": placement.confidence,
            }
        if cfg.top_services is not None:
            service_port = service_port_by_sector[placement.sector_name]
            channel_payload["electrical_service"] = {
                "signal_feedthrough_port": service_port.name,
                "signal_feedthrough_slot": service_slot_by_channel[placement.channel_name],
                "signal_impedance_ohm": cfg.top_services.electrical.impedance_ohm,
                "sipm_bias_on_signal_coax": cfg.top_services.electrical.bias_on_signal_coax,
            }
        channels.append(channel_payload)

    coincidence_pairs: list[dict[str, object]] = []
    pzz_numerator_ids: list[str] = []
    pzz_denominator_ids: list[str] = []
    pyy_lr_ids: list[str] = []
    pyy_ud_ids: list[str] = []

    for pair in cfg.physics.coincidence_pairs:
        for deuteron_sector in cfg.sectors:
            proton_sector = OPPOSITE_SECTOR[deuteron_sector]
            deuteron = placement_by_key[(pair.deuteron_channel, deuteron_sector)]
            proton = placement_by_key[(pair.proton_channel, proton_sector)]
            pair_id = f"{pair.name}_{deuteron_sector}"
            pyy_group = _lrud_group(deuteron_sector)
            pzz_role = "none"
            if pair.name == cfg.physics.pzz_numerator_pair:
                pzz_role = "numerator"
                pzz_numerator_ids.append(pair_id)
            elif pair.name == cfg.physics.pzz_denominator_pair:
                pzz_role = "denominator"
                pzz_denominator_ids.append(pair_id)

            pyy_role = "none"
            if pair.name == cfg.physics.pyy_pair:
                pyy_role = pyy_group
                if pyy_group == "lr":
                    pyy_lr_ids.append(pair_id)
                else:
                    pyy_ud_ids.append(pair_id)

            coincidence_pairs.append(
                {
                    "pair_id": pair_id,
                    "branch": pair.deuteron_cm_branch,
                    "deuteron_channel_id": deuteron.tag,
                    "proton_channel_id": proton.tag,
                    "deuteron_sector": deuteron_sector,
                    "proton_sector": proton_sector,
                    "azimuth_relation": cfg.physics.azimuth_relation,
                    "pzz_role": pzz_role,
                    "pyy_role": pyy_role,
                }
            )

    payload: dict[str, object] = {
        "schema_version": 3,
        "module": "compactInVacuum",
        "coordinate_system": {
            "origin": "target",
            "target_position_mm": list(cfg.physics.target.position_mm),
            "beam_axis": list(cfg.physics.beam.axis),
            "sector_transverse_axes": SECTOR_TRANSVERSE_AXIS,
        },
        "physics": {
            "status": cfg.physics.status,
            "scope": cfg.physics.scope,
            "reaction": cfg.physics.reaction,
            "beam_particle": cfg.physics.beam.particle,
            "beam_kinetic_energy_mev": cfg.physics.beam.kinetic_energy_mev,
            "target_material": cfg.physics.target.material,
            "target_areal_density_g_per_m2": cfg.physics.target.areal_density_g_per_m2,
            "target_status": cfg.physics.target.status,
        },
        "detector_model": {
            "radius_reference": cfg.detector.radius_reference,
            "active_medium_status": cfg.detector.active_medium_status,
            "active_medium": cfg.detector.active_medium,
            "photosensor_status": cfg.detector.photosensor_status,
            "photosensor": cfg.detector.photosensor,
        },
        "channels": channels,
        "coincidence_pairs": coincidence_pairs,
        "observables": {
            "pzz": {
                "definition": "N_forward/N_backward",
                "numerator_pair_name": cfg.physics.pzz_numerator_pair,
                "denominator_pair_name": cfg.physics.pzz_denominator_pair,
                "numerator_pair_ids": pzz_numerator_ids,
                "denominator_pair_ids": pzz_denominator_ids,
            },
            "pyy": {
                "definition": "(N_LR-N_UD)/(N_LR+N_UD)",
                "pair_name": cfg.physics.pyy_pair,
                "lr_pair_ids": pyy_lr_ids,
                "ud_pair_ids": pyy_ud_ids,
            },
        },
    }
    if cfg.top_services is not None:
        electrical = cfg.top_services.electrical
        used_slots = len(cfg.channels)
        payload["electrical_services"] = {
            "status": electrical.architecture_status,
            "active_electronics_in_vacuum": electrical.active_electronics_in_vacuum,
            "bias_on_signal_coax": electrical.bias_on_signal_coax,
            "signal_impedance_ohm": electrical.impedance_ohm,
            "signal_ports": [
                {
                    "name": port.name,
                    "sector": port.sector,
                    "standard": cfg.top_services.icf70_interface.standard,
                    "center_x_mm": port.center_x_mm,
                    "center_z_mm": port.center_z_mm,
                    "channel_capacity": electrical.channels_per_signal_port,
                    "used_slots": list(range(1, used_slots + 1)),
                    "spare_slots": list(
                        range(used_slots + 1, electrical.channels_per_signal_port + 1)
                    ),
                }
                for port in electrical.signal_ports
            ],
            "routing": {
                "cable_keepout_diameter_mm": electrical.routing.cable_keepout_diameter_mm,
                "minimum_static_bend_radius_mm": electrical.routing.minimum_static_bend_radius_mm,
                "strain_relief_at_detector": True,
                "strain_relief_at_feedthrough": True,
            },
            "grounding": {
                "protective_bond_required": electrical.grounding.protective_bond_required,
                "coax_shield_bond_at_feedthrough": electrical.grounding.coax_shield_bond_at_feedthrough,
                "signal_shield_is_only_protective_earth": (
                    electrical.grounding.signal_shield_is_only_protective_earth
                ),
            },
        }
    return payload


def export_channel_manifest(
    cfg: CIVConfig,
    placements: list[DetectorPlacement],
    output_path: str | Path,
) -> str:
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_channel_manifest(cfg, placements)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)
