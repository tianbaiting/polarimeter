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
    angle_deg: float
    radius_mm: float
    confidence: str


@dataclass(frozen=True)
class DetectorConfig:
    diameter_mm: float
    length_mm: float
    clamp_outer_diameter_mm: float
    clamp_width_mm: float


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

        channel = ChannelConfig(
            name=name,
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
    cfg = DetectorConfig(
        diameter_mm=_to_float(raw.get("diameter_mm"), "detector.diameter_mm"),
        length_mm=_to_float(raw.get("length_mm"), "detector.length_mm"),
        clamp_outer_diameter_mm=_to_float(raw.get("clamp_outer_diameter_mm"), "detector.clamp_outer_diameter_mm"),
        clamp_width_mm=_to_float(raw.get("clamp_width_mm"), "detector.clamp_width_mm"),
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

    return CIVConfig(
        vessel=_parse_vessel(_to_mapping(raw.get("vessel"), "vessel")),
        channels=_parse_channels(_to_list(raw.get("channels"), "channels")),
        sectors=_parse_sectors(_to_list(raw.get("sectors"), "sectors")),
        detector=_parse_detector(_to_mapping(raw.get("detector"), "detector")),
        inner_frame=_parse_inner_frame(_to_mapping(raw.get("inner_frame"), "inner_frame")),
        validation=_parse_validation(_to_mapping(raw.get("validation", {}), "validation")),
        doc_name=_to_str(raw.get("doc_name", "compactInVacuum"), "doc_name"),
    )


def dump_config_yaml(cfg: CIVConfig) -> str:
    _assert_yaml_available()
    return yaml.safe_dump(asdict(cfg), sort_keys=False)
