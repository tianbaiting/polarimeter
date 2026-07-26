from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import math
import os
from pathlib import Path
from typing import Any, Mapping

try:
    import yaml
except ImportError as exc:  # pragma: no cover - import guard
    yaml = None
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None


_ALLOWED_SECTORS = {"left", "right", "up", "down"}
_ALLOWED_CONFIDENCE = {"high", "medium", "low"}
_ALLOWED_CROSS_SECTIONS = {"cylindrical", "square"}
_ALLOWED_PARTICLES = {"deuteron", "proton", "unspecified"}
_ALLOWED_CM_BRANCHES = {"forward", "backward"}
_ALLOWED_SELECTION_STATUS = {"provisional", "frozen"}
_ALLOWED_TECHNOLOGY_STATUS = {"undecided", "selected"}
_ALLOWED_RADIUS_REFERENCES = {"active_center"}
_ALLOWED_INTERFACE_STATUS = {"interface_envelope", "selected"}
_ALLOWED_SUPPLIER_MODEL_STATUS = {"unfrozen", "selected"}


@dataclass(frozen=True)
class EndModuleSideConfig:
    standard: str
    module_outer_diameter_mm: float
    module_inner_diameter_mm: float
    pipe_outer_diameter_mm: float
    pipe_inner_diameter_mm: float
    pipe_length_mm: float
    module_thickness_mm: float
    seal_face_width_mm: float
    bolt_circle_diameter_mm: float
    bolt_count: int
    flange_bolt_hole_diameter_mm: float
    oring_groove_inner_diameter_mm: float
    oring_groove_outer_diameter_mm: float
    oring_groove_depth_mm: float
    interface_bolt_diameter_mm: float
    interface_bolt_length_mm: float
    interface_nut_outer_diameter_mm: float
    interface_nut_thickness_mm: float
    interface_washer_outer_diameter_mm: float
    interface_washer_thickness_mm: float


@dataclass(frozen=True)
class EndModulesConfig:
    front: EndModuleSideConfig
    rear: EndModuleSideConfig


@dataclass(frozen=True)
class VesselContractConfig:
    front_standard: str
    rear_standard: str


@dataclass(frozen=True)
class VesselConfig:
    cross_section: str
    inner_size_x_mm: float
    inner_size_y_mm: float
    wall_thickness_mm: float
    length_mm: float
    center_z_mm: float
    beam_bore_diameter_mm: float
    end_modules: EndModulesConfig
    contract: VesselContractConfig


@dataclass(frozen=True)
class ChannelConfig:
    name: str
    particle: str
    cm_branches: tuple[str, ...]
    angle_deg: float
    radius_mm: float
    confidence: str


@dataclass(frozen=True)
class DetectorConfig:
    radius_reference: str
    diameter_mm: float
    length_mm: float
    clamp_outer_diameter_mm: float
    clamp_width_mm: float
    active_medium_status: str
    active_medium: str
    photosensor_status: str
    photosensor: str


@dataclass(frozen=True)
class PhysicsBeamConfig:
    particle: str
    kinetic_energy_mev: float
    axis: tuple[float, float, float]


@dataclass(frozen=True)
class PhysicsTargetConfig:
    material: str
    areal_density_g_per_m2: float
    position_mm: tuple[float, float, float]
    status: str


@dataclass(frozen=True)
class CoincidencePairConfig:
    name: str
    deuteron_channel: str
    proton_channel: str
    deuteron_cm_branch: str


@dataclass(frozen=True)
class PhysicsConfig:
    status: str
    scope: str
    reaction: str
    beam: PhysicsBeamConfig
    target: PhysicsTargetConfig
    azimuth_relation: str
    coincidence_pairs: tuple[CoincidencePairConfig, ...]
    pzz_numerator_pair: str
    pzz_denominator_pair: str
    pyy_pair: str


@dataclass(frozen=True)
class RotaryServiceConfig:
    mount_standard: str
    pivot_x_mm: float
    pivot_z_mm: float
    port_inner_diameter_mm: float
    port_outer_diameter_mm: float
    port_collar_length_mm: float
    shaft_diameter_mm: float
    work_angle_deg: float
    park_angle_deg: float
    arm_length_mm: float
    arm_width_mm: float
    arm_thickness_mm: float
    hub_diameter_mm: float
    hub_thickness_mm: float
    holder_outer_width_mm: float
    holder_outer_height_mm: float
    holder_frame_width_mm: float
    holder_thickness_mm: float
    target_diameter_mm: float
    target_thickness_mm: float
    beam_stay_clear_diameter_mm: float
    supplier_model_status: str
    supplier_reference_code: str
    external_body_diameter_mm: float
    external_body_length_mm: float
    handwheel_diameter_mm: float
    handwheel_thickness_mm: float


@dataclass(frozen=True)
class SignalServicePortConfig:
    name: str
    sector: str
    center_x_mm: float
    center_z_mm: float


@dataclass(frozen=True)
class HousekeepingServiceConfig:
    name: str
    center_x_mm: float
    center_z_mm: float
    sensor_count: int
    wires_per_sensor: int
    feedthrough_pin_count: int
    port_inner_diameter_mm: float
    port_outer_diameter_mm: float
    port_collar_length_mm: float
    equipment_envelope_diameter_mm: float
    equipment_envelope_length_mm: float


@dataclass(frozen=True)
class CableRoutingConfig:
    cable_keepout_diameter_mm: float
    minimum_static_bend_radius_mm: float
    wall_clearance_mm: float
    strain_relief_length_mm: float
    strain_relief_width_mm: float
    strain_relief_thickness_mm: float


@dataclass(frozen=True)
class GroundingConfig:
    protective_bond_required: bool
    coax_shield_bond_at_feedthrough: bool
    signal_shield_is_only_protective_earth: bool


@dataclass(frozen=True)
class ElectricalServicesConfig:
    architecture_status: str
    impedance_ohm: float
    detector_channel_count: int
    bias_on_signal_coax: bool
    active_electronics_in_vacuum: bool
    channels_per_signal_port: int
    signal_ports: tuple[SignalServicePortConfig, ...]
    signal_port_inner_diameter_mm: float
    signal_port_outer_diameter_mm: float
    signal_port_collar_length_mm: float
    signal_equipment_envelope_diameter_mm: float
    signal_equipment_envelope_length_mm: float
    housekeeping: HousekeepingServiceConfig
    routing: CableRoutingConfig
    grounding: GroundingConfig


@dataclass(frozen=True)
class TopServicesConfig:
    status: str
    icf70_interface: EndModuleSideConfig
    rotary: RotaryServiceConfig
    electrical: ElectricalServicesConfig


@dataclass(frozen=True)
class InnerFrameConfig:
    spine_diameter_mm: float
    arm_cross_width_mm: float
    arm_cross_thickness_mm: float


@dataclass(frozen=True)
class ValidationConfig:
    angle_tolerance_deg: float
    radius_tolerance_mm: float


@dataclass(frozen=True)
class CIVConfig:
    vessel: VesselConfig
    channels: tuple[ChannelConfig, ...]
    sectors: tuple[str, ...]
    detector: DetectorConfig
    physics: PhysicsConfig | None
    top_services: TopServicesConfig | None
    inner_frame: InnerFrameConfig
    validation: ValidationConfig
    doc_name: str = "compactInVacuum"


def _assert_yaml_available() -> None:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required for compactInVacuum configuration parsing. "
            "Install it with: pip install pyyaml"
        ) from _YAML_IMPORT_ERROR


def _default_config_path() -> Path:
    env_path = os.environ.get("CIV_DEFAULT_CONFIG_PATH")
    if env_path is not None and env_path.strip():
        return Path(env_path).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "config" / "default_compactInVacuum.yaml"


def _load_yaml_file(path: Path) -> dict[str, Any]:
    _assert_yaml_available()
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return loaded


def _to_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping, got {value!r}")
    return value


def _to_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list, got {value!r}")
    return value


def _to_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string, got {value!r}")
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} cannot be empty")
    return text


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric, got {value!r}") from exc


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer, got {value!r}") from exc


def _to_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean, got {value!r}")
    return value


def _to_vector3(value: Any, field_name: str) -> tuple[float, float, float]:
    raw = _to_list(value, field_name)
    if len(raw) != 3:
        raise ValueError(f"{field_name} must contain exactly three values")
    return (
        _to_float(raw[0], f"{field_name}[0]"),
        _to_float(raw[1], f"{field_name}[1]"),
        _to_float(raw[2], f"{field_name}[2]"),
    )


def _require_positive(fields: Mapping[str, float]) -> None:
    for name, value in fields.items():
        if value <= 0.0:
            raise ValueError(f"{name} must be > 0, got {value}")


def _set_deep(mapping: dict[str, Any], dotted_key: str, value: Any) -> None:
    keys = [part.strip() for part in dotted_key.split(".") if part.strip()]
    if not keys:
        raise ValueError("Override key cannot be empty")

    cursor: dict[str, Any] = mapping
    for key in keys[:-1]:
        next_value = cursor.get(key)
        if next_value is None:
            next_value = {}
            cursor[key] = next_value
        if not isinstance(next_value, dict):
            raise ValueError(f"Override path collides with non-mapping field: {dotted_key}")
        cursor = next_value
    cursor[keys[-1]] = value


def _apply_overrides(raw: dict[str, Any], overrides: Mapping[str, Any] | None) -> dict[str, Any]:
    if not overrides:
        return raw
    merged = deepcopy(raw)
    for dotted_key, value in overrides.items():
        _set_deep(merged, dotted_key, value)
    return merged


def end_module_has_groove(standard: str) -> bool:
    return standard.upper().startswith("VG")


def _legacy_ring_end_module(vessel_cross_size_mm: float, beam_bore_diameter_mm: float, wall_thickness_mm: float) -> EndModuleSideConfig:
    module_thickness_mm = max(0.5 * wall_thickness_mm, 2.0)
    module_inner_diameter_mm = beam_bore_diameter_mm + wall_thickness_mm
    module_outer_diameter_mm = vessel_cross_size_mm + (4.0 * wall_thickness_mm)
    bolt_circle_diameter_mm = 0.5 * (module_inner_diameter_mm + module_outer_diameter_mm)
    hole_diameter_mm = max(0.3 * wall_thickness_mm, 2.0)
    interface_bolt_diameter_mm = max(0.5 * hole_diameter_mm, 1.0)
    interface_bolt_length_mm = module_thickness_mm + 6.0

    return EndModuleSideConfig(
        standard="LEGACY_RING",
        module_outer_diameter_mm=module_outer_diameter_mm,
        module_inner_diameter_mm=module_inner_diameter_mm,
        pipe_outer_diameter_mm=module_inner_diameter_mm,
        pipe_inner_diameter_mm=beam_bore_diameter_mm,
        pipe_length_mm=0.0,
        module_thickness_mm=module_thickness_mm,
        seal_face_width_mm=max(0.5 * wall_thickness_mm, 2.0),
        bolt_circle_diameter_mm=bolt_circle_diameter_mm,
        bolt_count=4,
        flange_bolt_hole_diameter_mm=hole_diameter_mm,
        oring_groove_inner_diameter_mm=0.0,
        oring_groove_outer_diameter_mm=0.0,
        oring_groove_depth_mm=0.0,
        interface_bolt_diameter_mm=interface_bolt_diameter_mm,
        interface_bolt_length_mm=interface_bolt_length_mm,
        interface_nut_outer_diameter_mm=interface_bolt_diameter_mm + 5.0,
        interface_nut_thickness_mm=min(4.0, 0.5 * interface_bolt_length_mm),
        interface_washer_outer_diameter_mm=interface_bolt_diameter_mm + 7.0,
        interface_washer_thickness_mm=1.0,
    )


def _parse_end_module_side(raw: dict[str, Any], prefix: str) -> EndModuleSideConfig:
    standard = _to_str(raw.get("standard"), f"{prefix}.standard")
    module_outer_diameter_mm = _to_float(raw.get("module_outer_diameter_mm"), f"{prefix}.module_outer_diameter_mm")
    module_inner_diameter_mm = _to_float(raw.get("module_inner_diameter_mm"), f"{prefix}.module_inner_diameter_mm")
    pipe_outer_diameter_mm = _to_float(raw.get("pipe_outer_diameter_mm", module_inner_diameter_mm), f"{prefix}.pipe_outer_diameter_mm")
    pipe_inner_diameter_mm = _to_float(raw.get("pipe_inner_diameter_mm", module_inner_diameter_mm), f"{prefix}.pipe_inner_diameter_mm")
    pipe_length_mm = _to_float(raw.get("pipe_length_mm", 0.0), f"{prefix}.pipe_length_mm")
    module_thickness_mm = _to_float(raw.get("module_thickness_mm"), f"{prefix}.module_thickness_mm")
    seal_face_width_mm = _to_float(raw.get("seal_face_width_mm"), f"{prefix}.seal_face_width_mm")
    bolt_circle_diameter_mm = _to_float(raw.get("bolt_circle_diameter_mm"), f"{prefix}.bolt_circle_diameter_mm")
    bolt_count = _to_int(raw.get("bolt_count"), f"{prefix}.bolt_count")
    flange_bolt_hole_diameter_mm = _to_float(
        raw.get("flange_bolt_hole_diameter_mm"),
        f"{prefix}.flange_bolt_hole_diameter_mm",
    )
    oring_groove_inner_diameter_mm = _to_float(
        raw.get("oring_groove_inner_diameter_mm", 0.0),
        f"{prefix}.oring_groove_inner_diameter_mm",
    )
    oring_groove_outer_diameter_mm = _to_float(
        raw.get("oring_groove_outer_diameter_mm", 0.0),
        f"{prefix}.oring_groove_outer_diameter_mm",
    )
    oring_groove_depth_mm = _to_float(
        raw.get("oring_groove_depth_mm", 0.0),
        f"{prefix}.oring_groove_depth_mm",
    )

    cfg = EndModuleSideConfig(
        standard=standard,
        module_outer_diameter_mm=module_outer_diameter_mm,
        module_inner_diameter_mm=module_inner_diameter_mm,
        pipe_outer_diameter_mm=pipe_outer_diameter_mm,
        pipe_inner_diameter_mm=pipe_inner_diameter_mm,
        pipe_length_mm=pipe_length_mm,
        module_thickness_mm=module_thickness_mm,
        seal_face_width_mm=seal_face_width_mm,
        bolt_circle_diameter_mm=bolt_circle_diameter_mm,
        bolt_count=bolt_count,
        flange_bolt_hole_diameter_mm=flange_bolt_hole_diameter_mm,
        oring_groove_inner_diameter_mm=oring_groove_inner_diameter_mm,
        oring_groove_outer_diameter_mm=oring_groove_outer_diameter_mm,
        oring_groove_depth_mm=oring_groove_depth_mm,
        interface_bolt_diameter_mm=_to_float(raw.get("interface_bolt_diameter_mm"), f"{prefix}.interface_bolt_diameter_mm"),
        interface_bolt_length_mm=_to_float(raw.get("interface_bolt_length_mm"), f"{prefix}.interface_bolt_length_mm"),
        interface_nut_outer_diameter_mm=_to_float(raw.get("interface_nut_outer_diameter_mm"), f"{prefix}.interface_nut_outer_diameter_mm"),
        interface_nut_thickness_mm=_to_float(raw.get("interface_nut_thickness_mm"), f"{prefix}.interface_nut_thickness_mm"),
        interface_washer_outer_diameter_mm=_to_float(raw.get("interface_washer_outer_diameter_mm"), f"{prefix}.interface_washer_outer_diameter_mm"),
        interface_washer_thickness_mm=_to_float(raw.get("interface_washer_thickness_mm"), f"{prefix}.interface_washer_thickness_mm"),
    )

    _require_positive(
        {
            f"{prefix}.module_outer_diameter_mm": cfg.module_outer_diameter_mm,
            f"{prefix}.module_inner_diameter_mm": cfg.module_inner_diameter_mm,
            f"{prefix}.module_thickness_mm": cfg.module_thickness_mm,
            f"{prefix}.seal_face_width_mm": cfg.seal_face_width_mm,
            f"{prefix}.bolt_circle_diameter_mm": cfg.bolt_circle_diameter_mm,
            f"{prefix}.flange_bolt_hole_diameter_mm": cfg.flange_bolt_hole_diameter_mm,
            f"{prefix}.interface_bolt_diameter_mm": cfg.interface_bolt_diameter_mm,
            f"{prefix}.interface_bolt_length_mm": cfg.interface_bolt_length_mm,
            f"{prefix}.interface_nut_outer_diameter_mm": cfg.interface_nut_outer_diameter_mm,
            f"{prefix}.interface_nut_thickness_mm": cfg.interface_nut_thickness_mm,
            f"{prefix}.interface_washer_outer_diameter_mm": cfg.interface_washer_outer_diameter_mm,
            f"{prefix}.interface_washer_thickness_mm": cfg.interface_washer_thickness_mm,
        }
    )

    if cfg.module_inner_diameter_mm >= cfg.module_outer_diameter_mm:
        raise ValueError(f"{prefix}.module_inner_diameter_mm must be < module_outer_diameter_mm")
    if cfg.pipe_length_mm < 0.0:
        raise ValueError(f"{prefix}.pipe_length_mm must be >= 0")
    if cfg.pipe_length_mm > 0.0:
        _require_positive(
            {
                f"{prefix}.pipe_outer_diameter_mm": cfg.pipe_outer_diameter_mm,
                f"{prefix}.pipe_inner_diameter_mm": cfg.pipe_inner_diameter_mm,
            }
        )
        if cfg.pipe_inner_diameter_mm >= cfg.pipe_outer_diameter_mm:
            raise ValueError(f"{prefix}.pipe_inner_diameter_mm must be < pipe_outer_diameter_mm")
        if cfg.pipe_outer_diameter_mm > cfg.module_inner_diameter_mm:
            raise ValueError(f"{prefix}.pipe_outer_diameter_mm must be <= module_inner_diameter_mm")
    if cfg.bolt_count < 4:
        raise ValueError(f"{prefix}.bolt_count must be >= 4")
    if cfg.bolt_circle_diameter_mm <= cfg.module_inner_diameter_mm:
        raise ValueError(f"{prefix}.bolt_circle_diameter_mm must be > module_inner_diameter_mm")
    if cfg.bolt_circle_diameter_mm >= cfg.module_outer_diameter_mm:
        raise ValueError(f"{prefix}.bolt_circle_diameter_mm must be < module_outer_diameter_mm")
    if cfg.flange_bolt_hole_diameter_mm >= (cfg.module_outer_diameter_mm - cfg.module_inner_diameter_mm):
        raise ValueError(f"{prefix}.flange_bolt_hole_diameter_mm must fit inside the flange annulus")
    if cfg.interface_bolt_diameter_mm >= cfg.flange_bolt_hole_diameter_mm:
        raise ValueError(f"{prefix}.interface_bolt_diameter_mm must be < flange_bolt_hole_diameter_mm")
    if cfg.interface_bolt_length_mm <= cfg.module_thickness_mm:
        raise ValueError(f"{prefix}.interface_bolt_length_mm must be > module_thickness_mm")
    if cfg.interface_nut_outer_diameter_mm <= cfg.interface_bolt_diameter_mm:
        raise ValueError(f"{prefix}.interface_nut_outer_diameter_mm must be > interface_bolt_diameter_mm")
    if cfg.interface_washer_outer_diameter_mm <= cfg.interface_bolt_diameter_mm:
        raise ValueError(f"{prefix}.interface_washer_outer_diameter_mm must be > interface_bolt_diameter_mm")
    if cfg.interface_nut_outer_diameter_mm > cfg.bolt_circle_diameter_mm:
        raise ValueError(f"{prefix}.interface_nut_outer_diameter_mm must be <= bolt_circle_diameter_mm")

    if end_module_has_groove(cfg.standard):
        _require_positive(
            {
                f"{prefix}.oring_groove_inner_diameter_mm": cfg.oring_groove_inner_diameter_mm,
                f"{prefix}.oring_groove_outer_diameter_mm": cfg.oring_groove_outer_diameter_mm,
                f"{prefix}.oring_groove_depth_mm": cfg.oring_groove_depth_mm,
            }
        )
        if cfg.oring_groove_inner_diameter_mm <= cfg.module_inner_diameter_mm:
            raise ValueError(f"{prefix}.oring_groove_inner_diameter_mm must be > module_inner_diameter_mm")
        if cfg.oring_groove_outer_diameter_mm <= cfg.oring_groove_inner_diameter_mm:
            raise ValueError(f"{prefix}.oring_groove_outer_diameter_mm must be > oring_groove_inner_diameter_mm")
        if cfg.oring_groove_outer_diameter_mm >= cfg.module_outer_diameter_mm:
            raise ValueError(f"{prefix}.oring_groove_outer_diameter_mm must be < module_outer_diameter_mm")
        if cfg.oring_groove_depth_mm >= cfg.module_thickness_mm:
            raise ValueError(f"{prefix}.oring_groove_depth_mm must be < module_thickness_mm")
    else:
        groove_values = (
            cfg.oring_groove_inner_diameter_mm,
            cfg.oring_groove_outer_diameter_mm,
            cfg.oring_groove_depth_mm,
        )
        if any(abs(value) > 1e-9 for value in groove_values):
            raise ValueError(f"{prefix} non-VG modules must not define O-ring groove geometry")

    return cfg


def _parse_vessel(raw: dict[str, Any]) -> VesselConfig:
    legacy_inner_diameter_raw = raw.get("inner_diameter_mm")
    cross_section_raw = raw.get("cross_section")
    if cross_section_raw is None:
        cross_section = "cylindrical" if legacy_inner_diameter_raw is not None else "square"
    else:
        cross_section = _to_str(cross_section_raw, "vessel.cross_section").lower()
    if cross_section not in _ALLOWED_CROSS_SECTIONS:
        raise ValueError(f"vessel.cross_section must be one of {sorted(_ALLOWED_CROSS_SECTIONS)}, got {cross_section!r}")

    if legacy_inner_diameter_raw is not None:
        inner_size_x_mm = _to_float(legacy_inner_diameter_raw, "vessel.inner_diameter_mm")
        inner_size_y_mm = inner_size_x_mm
    else:
        inner_size_x_mm = _to_float(raw.get("inner_size_x_mm"), "vessel.inner_size_x_mm")
        inner_size_y_mm = _to_float(raw.get("inner_size_y_mm"), "vessel.inner_size_y_mm")

    wall_thickness_mm = _to_float(raw.get("wall_thickness_mm"), "vessel.wall_thickness_mm")
    length_mm = _to_float(raw.get("length_mm"), "vessel.length_mm")
    center_z_mm = _to_float(raw.get("center_z_mm"), "vessel.center_z_mm")
    beam_bore_diameter_mm = _to_float(raw.get("beam_bore_diameter_mm"), "vessel.beam_bore_diameter_mm")

    _require_positive(
        {
            "vessel.inner_size_x_mm": inner_size_x_mm,
            "vessel.inner_size_y_mm": inner_size_y_mm,
            "vessel.wall_thickness_mm": wall_thickness_mm,
            "vessel.length_mm": length_mm,
            "vessel.beam_bore_diameter_mm": beam_bore_diameter_mm,
        }
    )

    if cross_section == "cylindrical" and not math.isclose(inner_size_x_mm, inner_size_y_mm, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError("vessel.cylindrical cross sections require inner_size_x_mm == inner_size_y_mm")
    if beam_bore_diameter_mm >= min(inner_size_x_mm, inner_size_y_mm):
        raise ValueError("vessel.beam_bore_diameter_mm must be smaller than the vessel inner transverse span")

    end_modules_raw = raw.get("end_modules")
    if end_modules_raw is None:
        legacy_side = _legacy_ring_end_module(max(inner_size_x_mm, inner_size_y_mm), beam_bore_diameter_mm, wall_thickness_mm)
        end_modules = EndModulesConfig(front=legacy_side, rear=legacy_side)
    else:
        end_map = _to_mapping(end_modules_raw, "vessel.end_modules")
        end_modules = EndModulesConfig(
            front=_parse_end_module_side(_to_mapping(end_map.get("front"), "vessel.end_modules.front"), "vessel.end_modules.front"),
            rear=_parse_end_module_side(_to_mapping(end_map.get("rear"), "vessel.end_modules.rear"), "vessel.end_modules.rear"),
        )

    contract_raw_value = raw.get("contract", {})
    contract_raw = _to_mapping(contract_raw_value, "vessel.contract") if contract_raw_value is not None else {}
    contract = VesselContractConfig(
        front_standard=_to_str(contract_raw.get("front_standard", end_modules.front.standard), "vessel.contract.front_standard"),
        rear_standard=_to_str(contract_raw.get("rear_standard", end_modules.rear.standard), "vessel.contract.rear_standard"),
    )

    for side_name, module in (("front", end_modules.front), ("rear", end_modules.rear)):
        minimum_bore_diameter_mm = module.pipe_inner_diameter_mm if module.pipe_length_mm > 0.0 else module.module_inner_diameter_mm
        if beam_bore_diameter_mm > minimum_bore_diameter_mm:
            raise ValueError(
                f"vessel.beam_bore_diameter_mm must be <= vessel.end_modules.{side_name}.pipe_inner_diameter_mm "
                "for real replacement-module continuity"
            )

    return VesselConfig(
        cross_section=cross_section,
        inner_size_x_mm=inner_size_x_mm,
        inner_size_y_mm=inner_size_y_mm,
        wall_thickness_mm=wall_thickness_mm,
        length_mm=length_mm,
        center_z_mm=center_z_mm,
        beam_bore_diameter_mm=beam_bore_diameter_mm,
        end_modules=end_modules,
        contract=contract,
    )


def _parse_channels(raw: list[Any]) -> tuple[ChannelConfig, ...]:
    channels: list[ChannelConfig] = []
    seen_names: set[str] = set()
    for idx, entry in enumerate(raw):
        item = _to_mapping(entry, f"channels[{idx}]")
        name = _to_str(item.get("name"), f"channels[{idx}].name")
        if name in seen_names:
            raise ValueError(f"channels[{idx}].name duplicates existing channel {name!r}")
        seen_names.add(name)

        confidence = _to_str(item.get("confidence"), f"channels[{idx}].confidence").lower()
        if confidence not in _ALLOWED_CONFIDENCE:
            raise ValueError(
                f"channels[{idx}].confidence must be one of {sorted(_ALLOWED_CONFIDENCE)}, got {confidence!r}"
            )

        particle = _to_str(item.get("particle", "unspecified"), f"channels[{idx}].particle").lower()
        if particle not in _ALLOWED_PARTICLES:
            raise ValueError(
                f"channels[{idx}].particle must be one of {sorted(_ALLOWED_PARTICLES)}, got {particle!r}"
            )

        branches: list[str] = []
        for branch_idx, raw_branch in enumerate(_to_list(item.get("cm_branches", []), f"channels[{idx}].cm_branches")):
            branch = _to_str(raw_branch, f"channels[{idx}].cm_branches[{branch_idx}]").lower()
            if branch not in _ALLOWED_CM_BRANCHES:
                raise ValueError(
                    f"channels[{idx}].cm_branches[{branch_idx}] must be one of "
                    f"{sorted(_ALLOWED_CM_BRANCHES)}, got {branch!r}"
                )
            if branch in branches:
                raise ValueError(f"channels[{idx}].cm_branches duplicates branch {branch!r}")
            branches.append(branch)

        channel = ChannelConfig(
            name=name,
            particle=particle,
            cm_branches=tuple(branches),
            angle_deg=_to_float(item.get("angle_deg"), f"channels[{idx}].angle_deg"),
            radius_mm=_to_float(item.get("radius_mm"), f"channels[{idx}].radius_mm"),
            confidence=confidence,
        )
        _require_positive({f"channels[{idx}].radius_mm": channel.radius_mm})
        if not (0.0 < channel.angle_deg < 90.0):
            raise ValueError(f"channels[{idx}].angle_deg must be between 0 and 90 degrees")

        channels.append(channel)

    if not channels:
        raise ValueError("channels must contain at least one entry")
    return tuple(channels)


def _parse_sectors(raw: list[Any]) -> tuple[str, ...]:
    sectors: list[str] = []
    seen: set[str] = set()
    for idx, entry in enumerate(raw):
        sector = _to_str(entry, f"sectors[{idx}]").lower()
        if sector not in _ALLOWED_SECTORS:
            raise ValueError(f"sectors[{idx}] must be one of {sorted(_ALLOWED_SECTORS)}, got {sector!r}")
        if sector in seen:
            raise ValueError(f"sectors[{idx}] duplicates existing sector {sector!r}")
        seen.add(sector)
        sectors.append(sector)
    if not sectors:
        raise ValueError("sectors must contain at least one entry")
    return tuple(sectors)


def _parse_detector(raw: dict[str, Any]) -> DetectorConfig:
    radius_reference = _to_str(raw.get("radius_reference", "active_center"), "detector.radius_reference").lower()
    if radius_reference not in _ALLOWED_RADIUS_REFERENCES:
        raise ValueError(
            f"detector.radius_reference must be one of {sorted(_ALLOWED_RADIUS_REFERENCES)}, "
            f"got {radius_reference!r}"
        )

    active_medium_status = _to_str(
        raw.get("active_medium_status", "undecided"),
        "detector.active_medium_status",
    ).lower()
    photosensor_status = _to_str(
        raw.get("photosensor_status", "undecided"),
        "detector.photosensor_status",
    ).lower()
    for field_name, status in (
        ("detector.active_medium_status", active_medium_status),
        ("detector.photosensor_status", photosensor_status),
    ):
        if status not in _ALLOWED_TECHNOLOGY_STATUS:
            raise ValueError(
                f"{field_name} must be one of {sorted(_ALLOWED_TECHNOLOGY_STATUS)}, got {status!r}"
            )

    cfg = DetectorConfig(
        radius_reference=radius_reference,
        diameter_mm=_to_float(raw.get("diameter_mm"), "detector.diameter_mm"),
        length_mm=_to_float(raw.get("length_mm"), "detector.length_mm"),
        clamp_outer_diameter_mm=_to_float(raw.get("clamp_outer_diameter_mm"), "detector.clamp_outer_diameter_mm"),
        clamp_width_mm=_to_float(raw.get("clamp_width_mm"), "detector.clamp_width_mm"),
        active_medium_status=active_medium_status,
        active_medium=_to_str(raw.get("active_medium", "placeholder"), "detector.active_medium"),
        photosensor_status=photosensor_status,
        photosensor=_to_str(raw.get("photosensor", "placeholder"), "detector.photosensor"),
    )
    _require_positive(
        {
            "detector.diameter_mm": cfg.diameter_mm,
            "detector.length_mm": cfg.length_mm,
            "detector.clamp_outer_diameter_mm": cfg.clamp_outer_diameter_mm,
            "detector.clamp_width_mm": cfg.clamp_width_mm,
        }
    )
    if cfg.clamp_outer_diameter_mm <= cfg.diameter_mm:
        raise ValueError("detector.clamp_outer_diameter_mm must be larger than detector.diameter_mm")
    if cfg.clamp_width_mm > cfg.length_mm:
        raise ValueError("detector.clamp_width_mm must not exceed detector.length_mm")
    return cfg


def _parse_physics(
    raw: dict[str, Any] | None,
    channels: tuple[ChannelConfig, ...],
    sectors: tuple[str, ...],
) -> PhysicsConfig | None:
    if raw is None:
        return None

    status = _to_str(raw.get("status"), "physics.status").lower()
    if status not in _ALLOWED_SELECTION_STATUS:
        raise ValueError(f"physics.status must be one of {sorted(_ALLOWED_SELECTION_STATUS)}, got {status!r}")

    beam_raw = _to_mapping(raw.get("beam"), "physics.beam")
    beam_particle = _to_str(beam_raw.get("particle"), "physics.beam.particle").lower()
    if beam_particle != "deuteron":
        raise ValueError("physics.beam.particle must be deuteron for the current H1(d,d)p elastic model")
    beam_axis = _to_vector3(beam_raw.get("axis"), "physics.beam.axis")
    if any(abs(actual - expected) > 1.0e-12 for actual, expected in zip(beam_axis, (0.0, 0.0, 1.0))):
        raise ValueError("physics.beam.axis must be [0, 0, 1] for the current CAD coordinate system")
    beam = PhysicsBeamConfig(
        particle=beam_particle,
        kinetic_energy_mev=_to_float(beam_raw.get("kinetic_energy_mev"), "physics.beam.kinetic_energy_mev"),
        axis=beam_axis,
    )
    _require_positive({"physics.beam.kinetic_energy_mev": beam.kinetic_energy_mev})

    target_raw = _to_mapping(raw.get("target"), "physics.target")
    target_status = _to_str(target_raw.get("status"), "physics.target.status").lower()
    if target_status not in _ALLOWED_SELECTION_STATUS:
        raise ValueError(
            f"physics.target.status must be one of {sorted(_ALLOWED_SELECTION_STATUS)}, got {target_status!r}"
        )
    target_position = _to_vector3(target_raw.get("position_mm"), "physics.target.position_mm")
    if any(abs(value) > 1.0e-12 for value in target_position):
        raise ValueError("physics.target.position_mm must remain at the CAD origin until translated layouts are implemented")
    target = PhysicsTargetConfig(
        material=_to_str(target_raw.get("material"), "physics.target.material"),
        areal_density_g_per_m2=_to_float(
            target_raw.get("areal_density_g_per_m2"),
            "physics.target.areal_density_g_per_m2",
        ),
        position_mm=target_position,
        status=target_status,
    )
    _require_positive({"physics.target.areal_density_g_per_m2": target.areal_density_g_per_m2})

    coincidence_raw = _to_mapping(raw.get("coincidence"), "physics.coincidence")
    azimuth_relation = _to_str(
        coincidence_raw.get("azimuth_relation"),
        "physics.coincidence.azimuth_relation",
    ).lower()
    if azimuth_relation != "opposite":
        raise ValueError("physics.coincidence.azimuth_relation must be opposite for elastic two-body D-P pairing")

    channel_by_name = {channel.name: channel for channel in channels}
    pairs: list[CoincidencePairConfig] = []
    seen_pair_names: set[str] = set()
    for pair_idx, raw_pair in enumerate(
        _to_list(coincidence_raw.get("pairs"), "physics.coincidence.pairs")
    ):
        pair_raw = _to_mapping(raw_pair, f"physics.coincidence.pairs[{pair_idx}]")
        pair = CoincidencePairConfig(
            name=_to_str(pair_raw.get("name"), f"physics.coincidence.pairs[{pair_idx}].name").lower(),
            deuteron_channel=_to_str(
                pair_raw.get("deuteron_channel"),
                f"physics.coincidence.pairs[{pair_idx}].deuteron_channel",
            ),
            proton_channel=_to_str(
                pair_raw.get("proton_channel"),
                f"physics.coincidence.pairs[{pair_idx}].proton_channel",
            ),
            deuteron_cm_branch=_to_str(
                pair_raw.get("deuteron_cm_branch"),
                f"physics.coincidence.pairs[{pair_idx}].deuteron_cm_branch",
            ).lower(),
        )
        if pair.name in seen_pair_names:
            raise ValueError(f"physics.coincidence.pairs duplicates pair name {pair.name!r}")
        seen_pair_names.add(pair.name)
        if pair.deuteron_cm_branch not in _ALLOWED_CM_BRANCHES:
            raise ValueError(
                f"physics.coincidence.pairs[{pair_idx}].deuteron_cm_branch must be one of "
                f"{sorted(_ALLOWED_CM_BRANCHES)}"
            )

        deuteron_channel = channel_by_name.get(pair.deuteron_channel)
        proton_channel = channel_by_name.get(pair.proton_channel)
        if deuteron_channel is None or deuteron_channel.particle != "deuteron":
            raise ValueError(f"coincidence pair {pair.name!r} must reference a deuteron channel")
        if proton_channel is None or proton_channel.particle != "proton":
            raise ValueError(f"coincidence pair {pair.name!r} must reference a proton channel")
        if pair.deuteron_cm_branch not in deuteron_channel.cm_branches:
            raise ValueError(
                f"coincidence pair {pair.name!r} branch is not accepted by channel {deuteron_channel.name!r}"
            )
        if pair.deuteron_cm_branch not in proton_channel.cm_branches:
            raise ValueError(
                f"coincidence pair {pair.name!r} branch is not accepted by channel {proton_channel.name!r}"
            )
        pairs.append(pair)

    if set(sectors) != _ALLOWED_SECTORS:
        raise ValueError("physics-enabled compact layouts require left, right, up, and down sectors")

    observables_raw = _to_mapping(raw.get("observables"), "physics.observables")
    pzz_numerator_pair = _to_str(
        observables_raw.get("pzz_numerator_pair"),
        "physics.observables.pzz_numerator_pair",
    ).lower()
    pzz_denominator_pair = _to_str(
        observables_raw.get("pzz_denominator_pair"),
        "physics.observables.pzz_denominator_pair",
    ).lower()
    pyy_pair = _to_str(observables_raw.get("pyy_pair"), "physics.observables.pyy_pair").lower()
    for field_name, pair_name in (
        ("physics.observables.pzz_numerator_pair", pzz_numerator_pair),
        ("physics.observables.pzz_denominator_pair", pzz_denominator_pair),
        ("physics.observables.pyy_pair", pyy_pair),
    ):
        if pair_name not in seen_pair_names:
            raise ValueError(f"{field_name} references unknown coincidence pair {pair_name!r}")
    if pzz_numerator_pair == pzz_denominator_pair:
        raise ValueError("pzz numerator and denominator must use distinct coincidence pairs")

    return PhysicsConfig(
        status=status,
        scope=_to_str(raw.get("scope"), "physics.scope"),
        reaction=_to_str(raw.get("reaction"), "physics.reaction"),
        beam=beam,
        target=target,
        azimuth_relation=azimuth_relation,
        coincidence_pairs=tuple(pairs),
        pzz_numerator_pair=pzz_numerator_pair,
        pzz_denominator_pair=pzz_denominator_pair,
        pyy_pair=pyy_pair,
    )


def _parse_top_services(
    raw: dict[str, Any] | None,
    vessel: VesselConfig,
    channels: tuple[ChannelConfig, ...],
    sectors: tuple[str, ...],
) -> TopServicesConfig | None:
    if raw is None:
        return None

    status = _to_str(raw.get("status"), "top_services.status").lower()
    if status not in _ALLOWED_INTERFACE_STATUS:
        raise ValueError(
            f"top_services.status must be one of {sorted(_ALLOWED_INTERFACE_STATUS)}, got {status!r}"
        )
    interface = _parse_end_module_side(
        _to_mapping(raw.get("icf70_interface"), "top_services.icf70_interface"),
        "top_services.icf70_interface",
    )
    if interface.standard.upper() != "ICF70":
        raise ValueError("top_services.icf70_interface.standard must be ICF70")

    rotary_raw = _to_mapping(raw.get("rotary"), "top_services.rotary")
    supplier_model_status = _to_str(
        rotary_raw.get("supplier_model_status"),
        "top_services.rotary.supplier_model_status",
    ).lower()
    if supplier_model_status not in _ALLOWED_SUPPLIER_MODEL_STATUS:
        raise ValueError(
            "top_services.rotary.supplier_model_status must be one of "
            f"{sorted(_ALLOWED_SUPPLIER_MODEL_STATUS)}, got {supplier_model_status!r}"
        )
    rotary = RotaryServiceConfig(
        mount_standard=_to_str(rotary_raw.get("mount_standard"), "top_services.rotary.mount_standard"),
        pivot_x_mm=_to_float(rotary_raw.get("pivot_x_mm"), "top_services.rotary.pivot_x_mm"),
        pivot_z_mm=_to_float(rotary_raw.get("pivot_z_mm"), "top_services.rotary.pivot_z_mm"),
        port_inner_diameter_mm=_to_float(
            rotary_raw.get("port_inner_diameter_mm"),
            "top_services.rotary.port_inner_diameter_mm",
        ),
        port_outer_diameter_mm=_to_float(
            rotary_raw.get("port_outer_diameter_mm"),
            "top_services.rotary.port_outer_diameter_mm",
        ),
        port_collar_length_mm=_to_float(
            rotary_raw.get("port_collar_length_mm"),
            "top_services.rotary.port_collar_length_mm",
        ),
        shaft_diameter_mm=_to_float(rotary_raw.get("shaft_diameter_mm"), "top_services.rotary.shaft_diameter_mm"),
        work_angle_deg=_to_float(rotary_raw.get("work_angle_deg"), "top_services.rotary.work_angle_deg"),
        park_angle_deg=_to_float(rotary_raw.get("park_angle_deg"), "top_services.rotary.park_angle_deg"),
        arm_length_mm=_to_float(rotary_raw.get("arm_length_mm"), "top_services.rotary.arm_length_mm"),
        arm_width_mm=_to_float(rotary_raw.get("arm_width_mm"), "top_services.rotary.arm_width_mm"),
        arm_thickness_mm=_to_float(rotary_raw.get("arm_thickness_mm"), "top_services.rotary.arm_thickness_mm"),
        hub_diameter_mm=_to_float(rotary_raw.get("hub_diameter_mm"), "top_services.rotary.hub_diameter_mm"),
        hub_thickness_mm=_to_float(rotary_raw.get("hub_thickness_mm"), "top_services.rotary.hub_thickness_mm"),
        holder_outer_width_mm=_to_float(
            rotary_raw.get("holder_outer_width_mm"),
            "top_services.rotary.holder_outer_width_mm",
        ),
        holder_outer_height_mm=_to_float(
            rotary_raw.get("holder_outer_height_mm"),
            "top_services.rotary.holder_outer_height_mm",
        ),
        holder_frame_width_mm=_to_float(
            rotary_raw.get("holder_frame_width_mm"),
            "top_services.rotary.holder_frame_width_mm",
        ),
        holder_thickness_mm=_to_float(
            rotary_raw.get("holder_thickness_mm"),
            "top_services.rotary.holder_thickness_mm",
        ),
        target_diameter_mm=_to_float(
            rotary_raw.get("target_diameter_mm"),
            "top_services.rotary.target_diameter_mm",
        ),
        target_thickness_mm=_to_float(
            rotary_raw.get("target_thickness_mm"),
            "top_services.rotary.target_thickness_mm",
        ),
        beam_stay_clear_diameter_mm=_to_float(
            rotary_raw.get("beam_stay_clear_diameter_mm"),
            "top_services.rotary.beam_stay_clear_diameter_mm",
        ),
        supplier_model_status=supplier_model_status,
        supplier_reference_code=_to_str(
            rotary_raw.get("supplier_reference_code"),
            "top_services.rotary.supplier_reference_code",
        ),
        external_body_diameter_mm=_to_float(
            rotary_raw.get("external_body_diameter_mm"),
            "top_services.rotary.external_body_diameter_mm",
        ),
        external_body_length_mm=_to_float(
            rotary_raw.get("external_body_length_mm"),
            "top_services.rotary.external_body_length_mm",
        ),
        handwheel_diameter_mm=_to_float(
            rotary_raw.get("handwheel_diameter_mm"),
            "top_services.rotary.handwheel_diameter_mm",
        ),
        handwheel_thickness_mm=_to_float(
            rotary_raw.get("handwheel_thickness_mm"),
            "top_services.rotary.handwheel_thickness_mm",
        ),
    )
    _require_positive(
        {
            "top_services.rotary.port_inner_diameter_mm": rotary.port_inner_diameter_mm,
            "top_services.rotary.port_outer_diameter_mm": rotary.port_outer_diameter_mm,
            "top_services.rotary.port_collar_length_mm": rotary.port_collar_length_mm,
            "top_services.rotary.shaft_diameter_mm": rotary.shaft_diameter_mm,
            "top_services.rotary.arm_length_mm": rotary.arm_length_mm,
            "top_services.rotary.arm_width_mm": rotary.arm_width_mm,
            "top_services.rotary.arm_thickness_mm": rotary.arm_thickness_mm,
            "top_services.rotary.hub_diameter_mm": rotary.hub_diameter_mm,
            "top_services.rotary.hub_thickness_mm": rotary.hub_thickness_mm,
            "top_services.rotary.holder_outer_width_mm": rotary.holder_outer_width_mm,
            "top_services.rotary.holder_outer_height_mm": rotary.holder_outer_height_mm,
            "top_services.rotary.holder_frame_width_mm": rotary.holder_frame_width_mm,
            "top_services.rotary.holder_thickness_mm": rotary.holder_thickness_mm,
            "top_services.rotary.target_diameter_mm": rotary.target_diameter_mm,
            "top_services.rotary.target_thickness_mm": rotary.target_thickness_mm,
            "top_services.rotary.beam_stay_clear_diameter_mm": rotary.beam_stay_clear_diameter_mm,
            "top_services.rotary.external_body_diameter_mm": rotary.external_body_diameter_mm,
            "top_services.rotary.external_body_length_mm": rotary.external_body_length_mm,
            "top_services.rotary.handwheel_diameter_mm": rotary.handwheel_diameter_mm,
            "top_services.rotary.handwheel_thickness_mm": rotary.handwheel_thickness_mm,
        }
    )
    if rotary.mount_standard.upper() != interface.standard.upper():
        raise ValueError("top_services.rotary.mount_standard must match top_services.icf70_interface.standard")
    if rotary.shaft_diameter_mm >= rotary.port_inner_diameter_mm:
        raise ValueError("top_services.rotary.shaft_diameter_mm must be smaller than the rotary port bore")
    if rotary.port_inner_diameter_mm >= rotary.port_outer_diameter_mm:
        raise ValueError("top_services.rotary.port_inner_diameter_mm must be smaller than its outer diameter")
    if not math.isclose(rotary.pivot_x_mm, rotary.arm_length_mm, rel_tol=0.0, abs_tol=1.0e-9):
        raise ValueError("top_services.rotary.pivot_x_mm must equal arm_length_mm so the work target is at x=0")
    if not math.isclose(rotary.pivot_z_mm, 0.0, rel_tol=0.0, abs_tol=1.0e-9):
        raise ValueError("top_services.rotary.pivot_z_mm must be 0 for the current beam-target origin contract")
    if not math.isclose(rotary.work_angle_deg, 0.0, rel_tol=0.0, abs_tol=1.0e-9):
        raise ValueError("top_services.rotary.work_angle_deg must be 0 for the current target frame")
    if not (0.0 < rotary.park_angle_deg <= 180.0):
        raise ValueError("top_services.rotary.park_angle_deg must be in (0, 180]")
    if 2.0 * rotary.holder_frame_width_mm >= min(
        rotary.holder_outer_width_mm,
        rotary.holder_outer_height_mm,
    ):
        raise ValueError("top_services.rotary.holder_frame_width_mm leaves no open target aperture")
    target_aperture_mm = min(
        rotary.holder_outer_width_mm,
        rotary.holder_outer_height_mm,
    ) - 2.0 * rotary.holder_frame_width_mm
    if rotary.beam_stay_clear_diameter_mm >= target_aperture_mm:
        raise ValueError("top_services.rotary.beam_stay_clear_diameter_mm must fit through the holder aperture")

    electrical_raw = _to_mapping(raw.get("electrical"), "top_services.electrical")
    architecture_status = _to_str(
        electrical_raw.get("architecture_status"),
        "top_services.electrical.architecture_status",
    ).lower()
    if architecture_status not in _ALLOWED_SELECTION_STATUS:
        raise ValueError(
            "top_services.electrical.architecture_status must be one of "
            f"{sorted(_ALLOWED_SELECTION_STATUS)}, got {architecture_status!r}"
        )
    signal_ports: list[SignalServicePortConfig] = []
    seen_names: set[str] = set()
    seen_sectors: set[str] = set()
    for idx, raw_port in enumerate(
        _to_list(electrical_raw.get("signal_ports"), "top_services.electrical.signal_ports")
    ):
        port_raw = _to_mapping(raw_port, f"top_services.electrical.signal_ports[{idx}]")
        port = SignalServicePortConfig(
            name=_to_str(port_raw.get("name"), f"top_services.electrical.signal_ports[{idx}].name"),
            sector=_to_str(port_raw.get("sector"), f"top_services.electrical.signal_ports[{idx}].sector").lower(),
            center_x_mm=_to_float(
                port_raw.get("center_x_mm"),
                f"top_services.electrical.signal_ports[{idx}].center_x_mm",
            ),
            center_z_mm=_to_float(
                port_raw.get("center_z_mm"),
                f"top_services.electrical.signal_ports[{idx}].center_z_mm",
            ),
        )
        if port.name in seen_names:
            raise ValueError(f"top_services.electrical.signal_ports duplicates name {port.name!r}")
        if port.sector not in _ALLOWED_SECTORS:
            raise ValueError(
                f"top_services.electrical.signal_ports[{idx}].sector must be one of {sorted(_ALLOWED_SECTORS)}"
            )
        if port.sector in seen_sectors:
            raise ValueError(f"top_services.electrical.signal_ports duplicates sector {port.sector!r}")
        seen_names.add(port.name)
        seen_sectors.add(port.sector)
        signal_ports.append(port)

    housekeeping_raw = _to_mapping(
        electrical_raw.get("housekeeping"),
        "top_services.electrical.housekeeping",
    )
    housekeeping = HousekeepingServiceConfig(
        name=_to_str(housekeeping_raw.get("name"), "top_services.electrical.housekeeping.name"),
        center_x_mm=_to_float(
            housekeeping_raw.get("center_x_mm"),
            "top_services.electrical.housekeeping.center_x_mm",
        ),
        center_z_mm=_to_float(
            housekeeping_raw.get("center_z_mm"),
            "top_services.electrical.housekeeping.center_z_mm",
        ),
        sensor_count=_to_int(
            housekeeping_raw.get("sensor_count"),
            "top_services.electrical.housekeeping.sensor_count",
        ),
        wires_per_sensor=_to_int(
            housekeeping_raw.get("wires_per_sensor"),
            "top_services.electrical.housekeeping.wires_per_sensor",
        ),
        feedthrough_pin_count=_to_int(
            housekeeping_raw.get("feedthrough_pin_count"),
            "top_services.electrical.housekeeping.feedthrough_pin_count",
        ),
        port_inner_diameter_mm=_to_float(
            housekeeping_raw.get("port_inner_diameter_mm"),
            "top_services.electrical.housekeeping.port_inner_diameter_mm",
        ),
        port_outer_diameter_mm=_to_float(
            housekeeping_raw.get("port_outer_diameter_mm"),
            "top_services.electrical.housekeeping.port_outer_diameter_mm",
        ),
        port_collar_length_mm=_to_float(
            housekeeping_raw.get("port_collar_length_mm"),
            "top_services.electrical.housekeeping.port_collar_length_mm",
        ),
        equipment_envelope_diameter_mm=_to_float(
            housekeeping_raw.get("equipment_envelope_diameter_mm"),
            "top_services.electrical.housekeeping.equipment_envelope_diameter_mm",
        ),
        equipment_envelope_length_mm=_to_float(
            housekeeping_raw.get("equipment_envelope_length_mm"),
            "top_services.electrical.housekeeping.equipment_envelope_length_mm",
        ),
    )
    routing_raw = _to_mapping(electrical_raw.get("routing"), "top_services.electrical.routing")
    routing = CableRoutingConfig(
        cable_keepout_diameter_mm=_to_float(
            routing_raw.get("cable_keepout_diameter_mm"),
            "top_services.electrical.routing.cable_keepout_diameter_mm",
        ),
        minimum_static_bend_radius_mm=_to_float(
            routing_raw.get("minimum_static_bend_radius_mm"),
            "top_services.electrical.routing.minimum_static_bend_radius_mm",
        ),
        wall_clearance_mm=_to_float(
            routing_raw.get("wall_clearance_mm"),
            "top_services.electrical.routing.wall_clearance_mm",
        ),
        strain_relief_length_mm=_to_float(
            routing_raw.get("strain_relief_length_mm"),
            "top_services.electrical.routing.strain_relief_length_mm",
        ),
        strain_relief_width_mm=_to_float(
            routing_raw.get("strain_relief_width_mm"),
            "top_services.electrical.routing.strain_relief_width_mm",
        ),
        strain_relief_thickness_mm=_to_float(
            routing_raw.get("strain_relief_thickness_mm"),
            "top_services.electrical.routing.strain_relief_thickness_mm",
        ),
    )
    grounding_raw = _to_mapping(electrical_raw.get("grounding"), "top_services.electrical.grounding")
    grounding = GroundingConfig(
        protective_bond_required=_to_bool(
            grounding_raw.get("protective_bond_required"),
            "top_services.electrical.grounding.protective_bond_required",
        ),
        coax_shield_bond_at_feedthrough=_to_bool(
            grounding_raw.get("coax_shield_bond_at_feedthrough"),
            "top_services.electrical.grounding.coax_shield_bond_at_feedthrough",
        ),
        signal_shield_is_only_protective_earth=_to_bool(
            grounding_raw.get("signal_shield_is_only_protective_earth"),
            "top_services.electrical.grounding.signal_shield_is_only_protective_earth",
        ),
    )
    electrical = ElectricalServicesConfig(
        architecture_status=architecture_status,
        impedance_ohm=_to_float(electrical_raw.get("impedance_ohm"), "top_services.electrical.impedance_ohm"),
        detector_channel_count=_to_int(
            electrical_raw.get("detector_channel_count"),
            "top_services.electrical.detector_channel_count",
        ),
        bias_on_signal_coax=_to_bool(
            electrical_raw.get("bias_on_signal_coax"),
            "top_services.electrical.bias_on_signal_coax",
        ),
        active_electronics_in_vacuum=_to_bool(
            electrical_raw.get("active_electronics_in_vacuum"),
            "top_services.electrical.active_electronics_in_vacuum",
        ),
        channels_per_signal_port=_to_int(
            electrical_raw.get("channels_per_signal_port"),
            "top_services.electrical.channels_per_signal_port",
        ),
        signal_ports=tuple(signal_ports),
        signal_port_inner_diameter_mm=_to_float(
            electrical_raw.get("signal_port_inner_diameter_mm"),
            "top_services.electrical.signal_port_inner_diameter_mm",
        ),
        signal_port_outer_diameter_mm=_to_float(
            electrical_raw.get("signal_port_outer_diameter_mm"),
            "top_services.electrical.signal_port_outer_diameter_mm",
        ),
        signal_port_collar_length_mm=_to_float(
            electrical_raw.get("signal_port_collar_length_mm"),
            "top_services.electrical.signal_port_collar_length_mm",
        ),
        signal_equipment_envelope_diameter_mm=_to_float(
            electrical_raw.get("signal_equipment_envelope_diameter_mm"),
            "top_services.electrical.signal_equipment_envelope_diameter_mm",
        ),
        signal_equipment_envelope_length_mm=_to_float(
            electrical_raw.get("signal_equipment_envelope_length_mm"),
            "top_services.electrical.signal_equipment_envelope_length_mm",
        ),
        housekeeping=housekeeping,
        routing=routing,
        grounding=grounding,
    )
    _require_positive(
        {
            "top_services.electrical.impedance_ohm": electrical.impedance_ohm,
            "top_services.electrical.signal_port_inner_diameter_mm": electrical.signal_port_inner_diameter_mm,
            "top_services.electrical.signal_port_outer_diameter_mm": electrical.signal_port_outer_diameter_mm,
            "top_services.electrical.signal_port_collar_length_mm": electrical.signal_port_collar_length_mm,
            "top_services.electrical.signal_equipment_envelope_diameter_mm": electrical.signal_equipment_envelope_diameter_mm,
            "top_services.electrical.signal_equipment_envelope_length_mm": electrical.signal_equipment_envelope_length_mm,
            "top_services.electrical.housekeeping.port_inner_diameter_mm": housekeeping.port_inner_diameter_mm,
            "top_services.electrical.housekeeping.port_outer_diameter_mm": housekeeping.port_outer_diameter_mm,
            "top_services.electrical.housekeeping.port_collar_length_mm": housekeeping.port_collar_length_mm,
            "top_services.electrical.housekeeping.equipment_envelope_diameter_mm": housekeeping.equipment_envelope_diameter_mm,
            "top_services.electrical.housekeeping.equipment_envelope_length_mm": housekeeping.equipment_envelope_length_mm,
            "top_services.electrical.routing.cable_keepout_diameter_mm": routing.cable_keepout_diameter_mm,
            "top_services.electrical.routing.minimum_static_bend_radius_mm": routing.minimum_static_bend_radius_mm,
            "top_services.electrical.routing.wall_clearance_mm": routing.wall_clearance_mm,
            "top_services.electrical.routing.strain_relief_length_mm": routing.strain_relief_length_mm,
            "top_services.electrical.routing.strain_relief_width_mm": routing.strain_relief_width_mm,
            "top_services.electrical.routing.strain_relief_thickness_mm": routing.strain_relief_thickness_mm,
        }
    )
    for field_name, value in (
        ("top_services.electrical.detector_channel_count", electrical.detector_channel_count),
        ("top_services.electrical.channels_per_signal_port", electrical.channels_per_signal_port),
        ("top_services.electrical.housekeeping.sensor_count", housekeeping.sensor_count),
        ("top_services.electrical.housekeeping.wires_per_sensor", housekeeping.wires_per_sensor),
        ("top_services.electrical.housekeeping.feedthrough_pin_count", housekeeping.feedthrough_pin_count),
    ):
        if value <= 0:
            raise ValueError(f"{field_name} must be > 0, got {value}")
    expected_detector_channels = len(channels) * len(sectors)
    if electrical.detector_channel_count != expected_detector_channels:
        raise ValueError(
            "top_services.electrical.detector_channel_count must match channels x sectors "
            f"({expected_detector_channels})"
        )
    if seen_sectors != set(sectors):
        raise ValueError("top_services.electrical.signal_ports must define exactly one port per detector sector")
    if len(signal_ports) * electrical.channels_per_signal_port < electrical.detector_channel_count:
        raise ValueError("top_services.electrical.signal_ports do not provide enough coax channel capacity")
    if housekeeping.feedthrough_pin_count < housekeeping.sensor_count * housekeeping.wires_per_sensor:
        raise ValueError("top_services.electrical.housekeeping.feedthrough_pin_count is below the sensor wiring demand")
    if electrical.signal_port_inner_diameter_mm >= electrical.signal_port_outer_diameter_mm:
        raise ValueError("top_services.electrical signal port inner diameter must be smaller than outer diameter")
    if housekeeping.port_inner_diameter_mm >= housekeeping.port_outer_diameter_mm:
        raise ValueError("top_services.electrical.housekeeping port inner diameter must be smaller than outer diameter")
    if not electrical.bias_on_signal_coax or electrical.active_electronics_in_vacuum:
        raise ValueError(
            "current CompactInVacuum baseline requires external bias tees and no active electronics in vacuum"
        )
    if not grounding.protective_bond_required or not grounding.coax_shield_bond_at_feedthrough:
        raise ValueError("current CompactInVacuum baseline requires protective and coax-feedthrough bonding")
    if grounding.signal_shield_is_only_protective_earth:
        raise ValueError("the coax signal shield must not be the only protective-earth path")

    flange_radius_mm = 0.5 * interface.module_outer_diameter_mm
    x_limit_mm = 0.5 * (vessel.inner_size_x_mm + 2.0 * vessel.wall_thickness_mm) - flange_radius_mm
    z_min_mm = vessel.center_z_mm - 0.5 * vessel.length_mm + flange_radius_mm
    z_max_mm = vessel.center_z_mm + 0.5 * vessel.length_mm - flange_radius_mm
    port_centers = [
        ("rotary", rotary.pivot_x_mm, rotary.pivot_z_mm),
        *[(port.name, port.center_x_mm, port.center_z_mm) for port in signal_ports],
        (housekeeping.name, housekeeping.center_x_mm, housekeeping.center_z_mm),
    ]
    for name, x_mm, z_mm in port_centers:
        if abs(x_mm) > x_limit_mm or not (z_min_mm <= z_mm <= z_max_mm):
            raise ValueError(f"top service port {name!r} does not fit on the vessel top face")
    for idx, (name_a, x_a, z_a) in enumerate(port_centers):
        for name_b, x_b, z_b in port_centers[idx + 1 :]:
            spacing_mm = math.hypot(x_b - x_a, z_b - z_a)
            if spacing_mm < interface.module_outer_diameter_mm:
                raise ValueError(
                    f"top service ports {name_a!r} and {name_b!r} overlap their ICF70 flange envelopes"
                )

    return TopServicesConfig(
        status=status,
        icf70_interface=interface,
        rotary=rotary,
        electrical=electrical,
    )


def _parse_inner_frame(raw: dict[str, Any]) -> InnerFrameConfig:
    cfg = InnerFrameConfig(
        spine_diameter_mm=_to_float(raw.get("spine_diameter_mm"), "inner_frame.spine_diameter_mm"),
        arm_cross_width_mm=_to_float(raw.get("arm_cross_width_mm"), "inner_frame.arm_cross_width_mm"),
        arm_cross_thickness_mm=_to_float(raw.get("arm_cross_thickness_mm"), "inner_frame.arm_cross_thickness_mm"),
    )
    _require_positive(
        {
            "inner_frame.spine_diameter_mm": cfg.spine_diameter_mm,
            "inner_frame.arm_cross_width_mm": cfg.arm_cross_width_mm,
            "inner_frame.arm_cross_thickness_mm": cfg.arm_cross_thickness_mm,
        }
    )
    return cfg


def _parse_validation(raw: dict[str, Any]) -> ValidationConfig:
    cfg = ValidationConfig(
        angle_tolerance_deg=_to_float(raw.get("angle_tolerance_deg", 0.05), "validation.angle_tolerance_deg"),
        radius_tolerance_mm=_to_float(raw.get("radius_tolerance_mm", 0.2), "validation.radius_tolerance_mm"),
    )
    _require_positive(
        {
            "validation.angle_tolerance_deg": cfg.angle_tolerance_deg,
            "validation.radius_tolerance_mm": cfg.radius_tolerance_mm,
        }
    )
    return cfg


def load_config(path: str | None, overrides: Mapping[str, Any] | None = None) -> CIVConfig:
    config_path = _default_config_path() if path is None else Path(path).expanduser().resolve()
    raw = _apply_overrides(_load_yaml_file(config_path), overrides)
    channels = _parse_channels(_to_list(raw.get("channels"), "channels"))
    sectors = _parse_sectors(_to_list(raw.get("sectors"), "sectors"))
    physics_raw = raw.get("physics")
    physics = _parse_physics(
        _to_mapping(physics_raw, "physics") if physics_raw is not None else None,
        channels,
        sectors,
    )
    vessel = _parse_vessel(_to_mapping(raw.get("vessel"), "vessel"))
    top_services_raw = raw.get("top_services")
    top_services = _parse_top_services(
        _to_mapping(top_services_raw, "top_services") if top_services_raw is not None else None,
        vessel,
        channels,
        sectors,
    )

    return CIVConfig(
        vessel=vessel,
        channels=channels,
        sectors=sectors,
        detector=_parse_detector(_to_mapping(raw.get("detector"), "detector")),
        physics=physics,
        top_services=top_services,
        inner_frame=_parse_inner_frame(_to_mapping(raw.get("inner_frame"), "inner_frame")),
        validation=_parse_validation(_to_mapping(raw.get("validation", {}), "validation")),
        doc_name=_to_str(raw.get("doc_name", "compactInVacuum"), "doc_name"),
    )


def dump_config_yaml(cfg: CIVConfig) -> str:
    _assert_yaml_available()
    return yaml.safe_dump(asdict(cfg), sort_keys=False)
