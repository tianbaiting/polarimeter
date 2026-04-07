from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - import guard for runtime environment
    yaml = None
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None


_ALLOWED_SECTORS = {"left", "right", "up", "down"}
_ALLOWED_CONFIDENCE = {"high", "medium", "low"}
_ALLOWED_OUTPUT_FORMATS = {"fcstd", "step"}
_ALLOWED_PORT_SIDES = {"right", "left", "top", "bottom"}
_ALLOWED_PORT_NAMES = ("main_pump", "gauge_safety", "rotary_feedthrough", "spare")
_ALLOWED_PLATE_ORIENTATIONS = {"horizontal", "vertical"}
_ALLOWED_PLATE_MOUNT_PLANES = {"xy", "xz", "yz"}
_ALLOWED_PLATE_OFFSET_MODES = {"manual", "auto"}
_ALLOWED_PLATE_OPENING_STYLES = {"annular_sector", "rounded_slot", "los_tube"}
_ALLOWED_LOS_SCOPES = {"v1_conceptual", "v2_fullpath"}
_ALLOWED_TARGET_MODES = {"linear_ladder", "single_rotary"}


@dataclass(frozen=True)
class DetectorChannel:
    name: str
    angle_deg: float
    radius_mm: float
    confidence: str


@dataclass(frozen=True)
class LayoutConfig:
    sectors: tuple[str, ...]
    channels: tuple[DetectorChannel, ...]


@dataclass(frozen=True)
class BeamlineConfig:
    axis: str
    inlet_diameter_mm: float


@dataclass(frozen=True)
class ChamberCoreConfig:
    size_x_mm: float
    size_y_mm: float
    size_z_mm: float
    center_z_mm: float
    wall_thickness_mm: float


@dataclass(frozen=True)
class ChamberEndModuleSideConfig:
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
class ChamberEndModulesConfig:
    front: ChamberEndModuleSideConfig
    rear: ChamberEndModuleSideConfig

    @property
    def front_standard(self) -> str:
        return self.front.standard

    @property
    def rear_standard(self) -> str:
        return self.rear.standard


@dataclass(frozen=True)
class ChamberLOSChannelsConfig:
    enabled: bool
    channel_diameter_mm: float
    channel_start_z_mm: float
    channel_length_mm: float


@dataclass(frozen=True)
class ChamberConfig:
    core: ChamberCoreConfig
    end_modules: ChamberEndModulesConfig
    los_channels: ChamberLOSChannelsConfig
    contract: "ChamberContractConfig"


@dataclass(frozen=True)
class ChamberContractConfig:
    front_standard: str
    rear_standard: str
    required_ports_enabled: tuple[str, ...]
    forbidden_ports_enabled: tuple[str, ...]
    rotary_mount_standard: str | None


@dataclass(frozen=True)
class PortConfig:
    enabled: bool
    side: str
    center_x_mm: float
    center_y_mm: float
    center_z_mm: float
    inner_diameter_mm: float
    outer_diameter_mm: float
    length_mm: float
    interface: ChamberEndModuleSideConfig | None


@dataclass(frozen=True)
class PortsConfig:
    main_pump: PortConfig
    gauge_safety: PortConfig
    rotary_feedthrough: PortConfig
    spare: PortConfig


@dataclass(frozen=True)
class PlateConfig:
    orientation: str
    mount_plane: str
    offset_mode: str
    opening_style: str
    z_mm: float
    offset_x_mm: float
    offset_y_mm: float
    width_mm: float
    height_mm: float
    thickness_mm: float
    inner_radius_mm: float
    outer_radius_mm: float
    sector_opening_deg: float
    azimuth_centers_deg: tuple[float, ...]
    lug_length_mm: float
    lug_width_mm: float
    lug_thickness_mm: float
    bolt_hole_diameter_mm: float
    bolt_hole_pitch_mm: float
    bolt_hole_count: int
    stiffener_count: int
    stiffener_thickness_mm: float
    stiffener_height_mm: float
    stiffener_length_mm: float


@dataclass(frozen=True)
class PlateGroupConfig:
    h: PlateConfig
    v1: PlateConfig
    v2: PlateConfig


@dataclass(frozen=True)
class DetectorClampConfig:
    detector_diameter_mm: float
    housing_length_mm: float
    outer_diameter_mm: float
    inner_diameter_mm: float
    width_mm: float
    split_gap_mm: float
    shoulder_height_mm: float
    end_stop_length_mm: float
    clamp_ear_length_mm: float
    clamp_ear_width_mm: float
    clamp_ear_thickness_mm: float
    clamp_bolt_diameter_mm: float
    clamp_bolt_pitch_mm: float
    anti_rotation_key_width_mm: float
    anti_rotation_key_depth_mm: float
    anti_rotation_key_length_mm: float
    support_overlap_mm: float
    mount_base_u_mm: float
    mount_base_v_mm: float
    mount_base_thickness_mm: float
    mount_bolt_hole_diameter_mm: float
    mount_bolt_pitch_u_mm: float
    mount_bolt_pitch_v_mm: float


@dataclass(frozen=True)
class DetectorAdapterBlockConfig:
    length_mm: float
    width_mm: float
    height_mm: float
    tilt_deg: float
    radial_standoff_mm: float


@dataclass(frozen=True)
class DetectorConfig:
    clamp: DetectorClampConfig
    adapter_block: DetectorAdapterBlockConfig


@dataclass(frozen=True)
class TargetLadderConfig:
    carriage_thickness_mm: float
    carriage_width_mm: float
    carriage_height_mm: float
    slot_pitch_mm: float
    slot_window_diameter_mm: float
    rail_diameter_mm: float
    rail_span_mm: float
    feedthrough_shaft_diameter_mm: float
    feedthrough_length_mm: float
    handwheel_diameter_mm: float
    motor_mount_width_mm: float
    motor_mount_height_mm: float
    motor_mount_thickness_mm: float
    hard_stop_span_mm: float
    hard_stop_thickness_mm: float
    index_disk_diameter_mm: float
    index_disk_thickness_mm: float
    index_pin_diameter_mm: float
    index_pin_length_mm: float
    active_index: int


@dataclass(frozen=True)
class TargetHolderConfig:
    frame_outer_width_mm: float
    frame_outer_height_mm: float
    frame_thickness_mm: float
    clamp_block_width_mm: float
    clamp_block_height_mm: float
    clamp_screw_diameter_mm: float
    clamp_screw_head_diameter_mm: float
    clamp_screw_head_height_mm: float
    experiment_target_thickness_mm: float
    fluorescence_target_thickness_mm: float


@dataclass(frozen=True)
class TargetRotaryConfig:
    pivot_x_mm: float
    work_angle_deg: float
    park_angle_deg: float
    active_angle_deg: float
    feedthrough_shaft_diameter_mm: float
    feedthrough_length_mm: float
    handwheel_diameter_mm: float
    motor_mount_width_mm: float
    motor_mount_height_mm: float
    motor_mount_thickness_mm: float
    hub_diameter_mm: float
    hub_thickness_mm: float
    arm_length_mm: float
    arm_width_mm: float
    arm_thickness_mm: float
    hard_stop_span_mm: float
    hard_stop_thickness_mm: float
    index_disk_diameter_mm: float
    index_disk_thickness_mm: float
    index_pin_diameter_mm: float
    index_pin_length_mm: float
    vendor_reference_enabled: bool
    vendor_reference_model_code: str | None
    vendor_reference_body_diameter_mm: float
    vendor_reference_body_length_mm: float
    vendor_reference_handwheel_diameter_mm: float
    vendor_reference_handwheel_thickness_mm: float


@dataclass(frozen=True)
class SingleTargetHolderConfig:
    frame_outer_width_mm: float
    frame_outer_height_mm: float
    frame_thickness_mm: float
    clamp_block_width_mm: float
    clamp_block_height_mm: float
    clamp_screw_diameter_mm: float
    clamp_screw_head_diameter_mm: float
    clamp_screw_head_height_mm: float
    target_thickness_mm: float


@dataclass(frozen=True)
class TargetConfig:
    mode: str
    ladder: TargetLadderConfig | None
    holder: TargetHolderConfig | None
    rotary: TargetRotaryConfig | None
    single_holder: SingleTargetHolderConfig | None


@dataclass(frozen=True)
class StandConfig:
    with_base_plate: bool
    base_length_mm: float
    base_width_mm: float
    base_thickness_mm: float
    chamber_support_height_mm: float
    support_foot_diameter_mm: float
    chamber_support_end_margin_mm: float
    chamber_support_pair_half_span_x_mm: float
    h_plate_support_end_margin_mm: float
    h_plate_support_pair_half_span_x_mm: float
    enable_plate_ties: bool
    plate_tie_column_diameter_mm: float
    plate_tie_cap_width_mm: float
    plate_tie_cap_height_mm: float
    plate_tie_cap_thickness_mm: float
    plate_tie_bolt_diameter_mm: float
    anchor_slot_length_mm: float
    anchor_slot_width_mm: float
    leveling_screw_diameter_mm: float
    shim_thickness_mm: float


@dataclass(frozen=True)
class ClearanceConfig:
    los_scope: str
    los_margin_mm: float
    vv_min_gap_factor: float
    plate_auto_gap_mm: float
    plate_chamber_cutout_margin_mm: float
    disable_plate_cuts: bool
    skip_overlap_checks: bool
    los_detector_active_face_offset_mm: float
    detector_front_to_chamber_mm: float
    detector_pair_min_gap_mm: float
    top_service_clearance_mm: float
    side_service_clearance_mm: float


@dataclass(frozen=True)
class GeometryConfig:
    beamline: BeamlineConfig
    chamber: ChamberConfig
    ports: PortsConfig
    plate: PlateGroupConfig
    detector: DetectorConfig
    target: TargetConfig
    stand: StandConfig
    clearance: ClearanceConfig


@dataclass(frozen=True)
class OutputConfig:
    output_dir: Path
    basename: str
    formats: tuple[str, ...]


@dataclass(frozen=True)
class BuildConfig:
    geometry: GeometryConfig
    layout: LayoutConfig
    output: OutputConfig


def _assert_yaml_available() -> None:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required for YAML configuration parsing. "
            "Install it with: pip install pyyaml"
        ) from _YAML_IMPORT_ERROR


def _load_yaml_file(path: Path) -> dict[str, Any]:
    _assert_yaml_available()
    if not path.exists():
        raise FileNotFoundError(f"Config file does not exist: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric, got {value!r}") from exc


def _to_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be int, got {value!r}")
    try:
        out = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be int, got {value!r}") from exc
    return out


def _to_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be bool, got {value!r}")


def _to_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string, got {value!r}")
    out = value.strip()
    if not out:
        raise ValueError(f"{field_name} cannot be empty")
    return out


def _to_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping, got {value!r}")
    return value


def _to_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list, got {value!r}")
    return value


def _set_deep(mapping: dict[str, Any], dotted_key: str, value: Any) -> None:
    cursor: dict[str, Any] = mapping
    keys = [k.strip() for k in dotted_key.split(".") if k.strip()]
    if not keys:
        raise ValueError("Override key cannot be empty")
    for key in keys[:-1]:
        next_value = cursor.get(key)
        if next_value is None:
            next_value = {}
            cursor[key] = next_value
        if not isinstance(next_value, dict):
            raise ValueError(f"Override path collides with non-mapping field: {dotted_key}")
        cursor = next_value
    cursor[keys[-1]] = value


def _apply_overrides(raw: dict[str, Any], overrides: list[str]) -> dict[str, Any]:
    if not overrides:
        return raw
    _assert_yaml_available()
    merged = yaml.safe_load(yaml.safe_dump(raw))
    if merged is None:
        merged = {}
    for override in overrides:
        if "=" not in override:
            raise ValueError(f"Invalid override syntax: {override!r}. Expected key=value")
        key, value_raw = override.split("=", 1)
        parsed_value = yaml.safe_load(value_raw)
        _set_deep(merged, key.strip(), parsed_value)
    return merged


def _require_positive(fields: dict[str, float]) -> None:
    for name, value in fields.items():
        if value <= 0.0:
            raise ValueError(f"{name} must be > 0, got {value}")


def _parse_beamline(raw: dict[str, Any]) -> BeamlineConfig:
    cfg = BeamlineConfig(
        axis=_to_str(raw.get("axis"), "geometry.beamline.axis").lower(),
        inlet_diameter_mm=_to_float(raw.get("inlet_diameter_mm"), "geometry.beamline.inlet_diameter_mm"),
    )
    _require_positive(
        {
            "geometry.beamline.inlet_diameter_mm": cfg.inlet_diameter_mm,
        }
    )
    if cfg.axis != "z":
        raise ValueError("geometry.beamline.axis must be 'z' in BLP v1 baseline")
    return cfg


def _end_module_has_groove(module: ChamberEndModuleSideConfig) -> bool:
    return module.standard.upper().startswith("VG")


def _parse_end_module_side(
    raw: dict[str, Any],
    prefix: str,
    *,
    standard_override: str | None = None,
) -> ChamberEndModuleSideConfig:
    standard = standard_override if standard_override is not None else _to_str(raw.get("standard"), f"{prefix}.standard")

    module_outer_diameter_mm = _to_float(raw.get("module_outer_diameter_mm"), f"{prefix}.module_outer_diameter_mm")
    module_inner_diameter_mm = _to_float(raw.get("module_inner_diameter_mm"), f"{prefix}.module_inner_diameter_mm")
    pipe_outer_diameter_mm = _to_float(
        raw.get("pipe_outer_diameter_mm", module_inner_diameter_mm),
        f"{prefix}.pipe_outer_diameter_mm",
    )
    pipe_inner_diameter_mm = _to_float(
        raw.get("pipe_inner_diameter_mm", module_inner_diameter_mm),
        f"{prefix}.pipe_inner_diameter_mm",
    )
    pipe_length_mm = _to_float(
        raw.get("pipe_length_mm", 0.0),
        f"{prefix}.pipe_length_mm",
    )
    module_thickness_mm = _to_float(raw.get("module_thickness_mm"), f"{prefix}.module_thickness_mm")
    seal_face_width_mm = _to_float(raw.get("seal_face_width_mm"), f"{prefix}.seal_face_width_mm")
    bolt_circle_diameter_mm = _to_float(raw.get("bolt_circle_diameter_mm"), f"{prefix}.bolt_circle_diameter_mm")
    bolt_count = _to_int(raw.get("bolt_count"), f"{prefix}.bolt_count")
    flange_bolt_hole_diameter_mm = _to_float(
        raw.get(
            "flange_bolt_hole_diameter_mm",
            min(0.6 * seal_face_width_mm, 0.2 * (module_outer_diameter_mm - module_inner_diameter_mm)),
        ),
        f"{prefix}.flange_bolt_hole_diameter_mm",
    )

    legacy_groove_width = raw.get("oring_groove_width_mm")
    groove_inner_raw = raw.get("oring_groove_inner_diameter_mm")
    groove_outer_raw = raw.get("oring_groove_outer_diameter_mm")
    # [EN] Groove dimensions are normalized here so VG/VF sealing semantics follow the declared interface standard instead of historical front/rear assumptions. / [CN] 在这里统一归一化 groove 尺寸，使 VG/VF 密封语义跟随声明的接口标准，而不是沿用历史上的前后端假设。
    if groove_inner_raw is None or groove_outer_raw is None:
        groove_width = _to_float(
            0.0 if legacy_groove_width is None else legacy_groove_width,
            f"{prefix}.oring_groove_width_mm",
        )
        oring_groove_inner_diameter_mm = module_inner_diameter_mm + groove_width if groove_width > 0.0 else 0.0
        oring_groove_outer_diameter_mm = (
            oring_groove_inner_diameter_mm + 2.0 * groove_width if groove_width > 0.0 else 0.0
        )
    else:
        oring_groove_inner_diameter_mm = _to_float(
            groove_inner_raw,
            f"{prefix}.oring_groove_inner_diameter_mm",
        )
        oring_groove_outer_diameter_mm = _to_float(
            groove_outer_raw,
            f"{prefix}.oring_groove_outer_diameter_mm",
        )
    oring_groove_depth_mm = _to_float(
        raw.get("oring_groove_depth_mm", 0.0),
        f"{prefix}.oring_groove_depth_mm",
    )

    cfg = ChamberEndModuleSideConfig(
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
        interface_bolt_diameter_mm=_to_float(
            raw.get("interface_bolt_diameter_mm"),
            f"{prefix}.interface_bolt_diameter_mm",
        ),
        interface_bolt_length_mm=_to_float(
            raw.get("interface_bolt_length_mm"),
            f"{prefix}.interface_bolt_length_mm",
        ),
        interface_nut_outer_diameter_mm=_to_float(
            raw.get("interface_nut_outer_diameter_mm"),
            f"{prefix}.interface_nut_outer_diameter_mm",
        ),
        interface_nut_thickness_mm=_to_float(
            raw.get("interface_nut_thickness_mm"),
            f"{prefix}.interface_nut_thickness_mm",
        ),
        interface_washer_outer_diameter_mm=_to_float(
            raw.get("interface_washer_outer_diameter_mm"),
            f"{prefix}.interface_washer_outer_diameter_mm",
        ),
        interface_washer_thickness_mm=_to_float(
            raw.get("interface_washer_thickness_mm"),
            f"{prefix}.interface_washer_thickness_mm",
        ),
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
        raise ValueError(f"{prefix}.module_inner_diameter_mm must be < outer")
    if cfg.pipe_length_mm < 0.0:
        raise ValueError(f"{prefix}.pipe_length_mm must be >= 0")
    if cfg.pipe_length_mm > 0.0:
        _require_positive(
            {
                f"{prefix}.pipe_outer_diameter_mm": cfg.pipe_outer_diameter_mm,
                f"{prefix}.pipe_inner_diameter_mm": cfg.pipe_inner_diameter_mm,
                f"{prefix}.pipe_length_mm": cfg.pipe_length_mm,
            }
        )
        if cfg.pipe_inner_diameter_mm >= cfg.pipe_outer_diameter_mm:
            raise ValueError(f"{prefix}.pipe_inner_diameter_mm must be < pipe_outer_diameter_mm")
        if cfg.pipe_outer_diameter_mm > cfg.module_inner_diameter_mm:
            raise ValueError(f"{prefix}.pipe_outer_diameter_mm must be <= module_inner_diameter_mm")
    if cfg.bolt_count < 4:
        raise ValueError(f"{prefix}.bolt_count must be >= 4")
    if cfg.bolt_circle_diameter_mm >= cfg.module_outer_diameter_mm:
        raise ValueError(f"{prefix}.bolt_circle_diameter_mm must be < module_outer_diameter_mm")
    if cfg.bolt_circle_diameter_mm <= cfg.module_inner_diameter_mm:
        raise ValueError(f"{prefix}.bolt_circle_diameter_mm must be > module_inner_diameter_mm")
    if cfg.flange_bolt_hole_diameter_mm >= (cfg.module_outer_diameter_mm - cfg.module_inner_diameter_mm):
        raise ValueError(f"{prefix}.flange_bolt_hole_diameter_mm must fit inside flange annulus")
    if cfg.interface_bolt_diameter_mm >= cfg.flange_bolt_hole_diameter_mm:
        raise ValueError(f"{prefix}.interface_bolt_diameter_mm must be < flange_bolt_hole_diameter_mm")
    if cfg.interface_bolt_length_mm <= cfg.module_thickness_mm:
        raise ValueError(f"{prefix}.interface_bolt_length_mm must be > module_thickness_mm")
    if cfg.interface_nut_outer_diameter_mm <= cfg.interface_bolt_diameter_mm:
        raise ValueError(f"{prefix}.interface_nut_outer_diameter_mm must be > interface_bolt_diameter_mm")
    if cfg.interface_washer_outer_diameter_mm <= cfg.interface_bolt_diameter_mm:
        raise ValueError(f"{prefix}.interface_washer_outer_diameter_mm must be > interface_bolt_diameter_mm")
    if cfg.interface_nut_thickness_mm >= cfg.interface_bolt_length_mm:
        raise ValueError(f"{prefix}.interface_nut_thickness_mm must be < interface_bolt_length_mm")
    if cfg.interface_washer_thickness_mm >= cfg.interface_bolt_length_mm:
        raise ValueError(f"{prefix}.interface_washer_thickness_mm must be < interface_bolt_length_mm")
    if cfg.interface_washer_outer_diameter_mm >= cfg.module_outer_diameter_mm:
        raise ValueError(f"{prefix}.interface_washer_outer_diameter_mm must be < module_outer_diameter_mm")
    if cfg.interface_nut_outer_diameter_mm > cfg.bolt_circle_diameter_mm:
        raise ValueError(f"{prefix}.interface_nut_outer_diameter_mm must be <= bolt_circle_diameter_mm")

    if _end_module_has_groove(cfg):
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
            raise ValueError(f"{prefix}.oring_groove_outer_diameter_mm must be > inner")
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
            raise ValueError(f"{prefix} VF-type modules must not define O-ring groove geometry")

    return cfg


def _parse_chamber(raw: dict[str, Any]) -> ChamberConfig:
    core_raw = _to_mapping(raw.get("core"), "geometry.chamber.core")
    end_raw = _to_mapping(raw.get("end_modules"), "geometry.chamber.end_modules")
    los_raw_value = raw.get("los_channels", {})
    los_raw = _to_mapping(los_raw_value, "geometry.chamber.los_channels") if los_raw_value is not None else {}
    contract_raw_value = raw.get("contract", {})
    contract_raw = (
        _to_mapping(contract_raw_value, "geometry.chamber.contract")
        if contract_raw_value is not None
        else {}
    )

    core = ChamberCoreConfig(
        size_x_mm=_to_float(core_raw.get("size_x_mm"), "geometry.chamber.core.size_x_mm"),
        size_y_mm=_to_float(core_raw.get("size_y_mm"), "geometry.chamber.core.size_y_mm"),
        size_z_mm=_to_float(core_raw.get("size_z_mm"), "geometry.chamber.core.size_z_mm"),
        center_z_mm=_to_float(core_raw.get("center_z_mm", 0.0), "geometry.chamber.core.center_z_mm"),
        wall_thickness_mm=_to_float(core_raw.get("wall_thickness_mm"), "geometry.chamber.core.wall_thickness_mm"),
    )

    has_split_side_schema = "front" in end_raw or "rear" in end_raw
    if has_split_side_schema:
        front = _parse_end_module_side(
            _to_mapping(end_raw.get("front"), "geometry.chamber.end_modules.front"),
            "geometry.chamber.end_modules.front",
        )
        rear = _parse_end_module_side(
            _to_mapping(end_raw.get("rear"), "geometry.chamber.end_modules.rear"),
            "geometry.chamber.end_modules.rear",
        )
    else:
        front = _parse_end_module_side(
            end_raw,
            "geometry.chamber.end_modules",
            standard_override=_to_str(end_raw.get("front_standard"), "geometry.chamber.end_modules.front_standard"),
        )
        legacy_rear_raw = dict(end_raw)
        legacy_rear_raw["oring_groove_width_mm"] = 0.0
        legacy_rear_raw["oring_groove_depth_mm"] = 0.0
        legacy_rear_raw["oring_groove_inner_diameter_mm"] = 0.0
        legacy_rear_raw["oring_groove_outer_diameter_mm"] = 0.0
        rear = _parse_end_module_side(
            legacy_rear_raw,
            "geometry.chamber.end_modules",
            standard_override=_to_str(end_raw.get("rear_standard"), "geometry.chamber.end_modules.rear_standard"),
        )
    end_modules = ChamberEndModulesConfig(front=front, rear=rear)

    los_channels = ChamberLOSChannelsConfig(
        enabled=_to_bool(
            los_raw.get("enabled", False),
            "geometry.chamber.los_channels.enabled",
        ),
        channel_diameter_mm=_to_float(
            los_raw.get("channel_diameter_mm", 72.0),
            "geometry.chamber.los_channels.channel_diameter_mm",
        ),
        channel_start_z_mm=_to_float(
            los_raw.get("channel_start_z_mm", 8.0),
            "geometry.chamber.los_channels.channel_start_z_mm",
        ),
        channel_length_mm=_to_float(
            los_raw.get("channel_length_mm", 1400.0),
            "geometry.chamber.los_channels.channel_length_mm",
        ),
    )

    _require_positive(
        {
            "geometry.chamber.core.size_x_mm": core.size_x_mm,
            "geometry.chamber.core.size_y_mm": core.size_y_mm,
            "geometry.chamber.core.size_z_mm": core.size_z_mm,
            "geometry.chamber.core.wall_thickness_mm": core.wall_thickness_mm,
            "geometry.chamber.los_channels.channel_diameter_mm": los_channels.channel_diameter_mm,
            "geometry.chamber.los_channels.channel_length_mm": los_channels.channel_length_mm,
        }
    )

    if 2.0 * core.wall_thickness_mm >= min(core.size_x_mm, core.size_y_mm, core.size_z_mm):
        raise ValueError("geometry.chamber.core.wall_thickness_mm is too large for core dimensions")
    half_z = 0.5 * core.size_z_mm
    z_min = core.center_z_mm - half_z
    z_max = core.center_z_mm + half_z
    if abs(core.center_z_mm) >= half_z:
        raise ValueError("geometry.chamber.core.center_z_mm must keep z=0 inside chamber span")
    if not (z_min < los_channels.channel_start_z_mm < z_max):
        raise ValueError("geometry.chamber.los_channels.channel_start_z_mm must lie inside chamber z-span")
    if los_channels.channel_diameter_mm >= min(core.size_x_mm, core.size_y_mm):
        raise ValueError("geometry.chamber.los_channels.channel_diameter_mm must be smaller than chamber transverse span")

    required_ports_raw = contract_raw.get("required_ports_enabled", list(_ALLOWED_PORT_NAMES))
    forbidden_ports_raw = contract_raw.get("forbidden_ports_enabled", [])
    required_ports_enabled = tuple(_parse_port_name_list(required_ports_raw, "geometry.chamber.contract.required_ports_enabled"))
    forbidden_ports_enabled = tuple(_parse_port_name_list(forbidden_ports_raw, "geometry.chamber.contract.forbidden_ports_enabled"))
    if set(required_ports_enabled) & set(forbidden_ports_enabled):
        raise ValueError("geometry.chamber.contract required/forbidden port sets must be disjoint")

    rotary_mount_standard_raw = contract_raw.get("rotary_mount_standard")
    rotary_mount_standard = (
        _to_str(rotary_mount_standard_raw, "geometry.chamber.contract.rotary_mount_standard")
        if rotary_mount_standard_raw is not None
        else None
    )

    contract = ChamberContractConfig(
        front_standard=_to_str(
            contract_raw.get("front_standard", front.standard),
            "geometry.chamber.contract.front_standard",
        ),
        rear_standard=_to_str(
            contract_raw.get("rear_standard", rear.standard),
            "geometry.chamber.contract.rear_standard",
        ),
        required_ports_enabled=required_ports_enabled,
        forbidden_ports_enabled=forbidden_ports_enabled,
        rotary_mount_standard=rotary_mount_standard,
    )

    return ChamberConfig(core=core, end_modules=end_modules, los_channels=los_channels, contract=contract)


def _parse_port(raw: dict[str, Any], field_prefix: str) -> PortConfig:
    cfg = PortConfig(
        enabled=_to_bool(raw.get("enabled", True), f"{field_prefix}.enabled"),
        side=_to_str(raw.get("side"), f"{field_prefix}.side").lower(),
        center_x_mm=_to_float(raw.get("center_x_mm", 0.0), f"{field_prefix}.center_x_mm"),
        center_y_mm=_to_float(raw.get("center_y_mm", 0.0), f"{field_prefix}.center_y_mm"),
        center_z_mm=_to_float(raw.get("center_z_mm"), f"{field_prefix}.center_z_mm"),
        inner_diameter_mm=_to_float(raw.get("inner_diameter_mm"), f"{field_prefix}.inner_diameter_mm"),
        outer_diameter_mm=_to_float(raw.get("outer_diameter_mm"), f"{field_prefix}.outer_diameter_mm"),
        length_mm=_to_float(raw.get("length_mm"), f"{field_prefix}.length_mm"),
        interface=(
            _parse_end_module_side(
                _to_mapping(raw.get("interface"), f"{field_prefix}.interface"),
                f"{field_prefix}.interface",
            )
            if raw.get("interface") is not None
            else None
        ),
    )

    _require_positive(
        {
            f"{field_prefix}.inner_diameter_mm": cfg.inner_diameter_mm,
            f"{field_prefix}.outer_diameter_mm": cfg.outer_diameter_mm,
        }
    )
    if cfg.length_mm < 0.0:
        raise ValueError(f"{field_prefix}.length_mm must be >= 0")

    if cfg.side not in _ALLOWED_PORT_SIDES:
        raise ValueError(f"{field_prefix}.side must be one of {sorted(_ALLOWED_PORT_SIDES)}, got {cfg.side!r}")

    if cfg.inner_diameter_mm >= cfg.outer_diameter_mm:
        raise ValueError(f"{field_prefix}.inner_diameter_mm must be < outer_diameter_mm")
    if not cfg.enabled and cfg.interface is not None:
        raise ValueError(f"{field_prefix}.interface requires {field_prefix}.enabled=true")

    return cfg


def _parse_port_name_list(value: Any, field_name: str) -> list[str]:
    items = _to_list(value, field_name)
    out: list[str] = []
    for idx, item in enumerate(items):
        name = _to_str(item, f"{field_name}[{idx}]")
        if name not in _ALLOWED_PORT_NAMES:
            raise ValueError(f"{field_name}[{idx}] must be one of {list(_ALLOWED_PORT_NAMES)}, got {name!r}")
        out.append(name)
    return out


def _parse_ports(raw: dict[str, Any]) -> PortsConfig:
    cfg = PortsConfig(
        main_pump=_parse_port(_to_mapping(raw.get("main_pump"), "geometry.ports.main_pump"), "geometry.ports.main_pump"),
        gauge_safety=_parse_port(_to_mapping(raw.get("gauge_safety"), "geometry.ports.gauge_safety"), "geometry.ports.gauge_safety"),
        rotary_feedthrough=_parse_port(
            _to_mapping(raw.get("rotary_feedthrough"), "geometry.ports.rotary_feedthrough"),
            "geometry.ports.rotary_feedthrough",
        ),
        spare=_parse_port(_to_mapping(raw.get("spare"), "geometry.ports.spare"), "geometry.ports.spare"),
    )

    if cfg.main_pump.enabled and cfg.main_pump.side != "right":
        raise ValueError("geometry.ports.main_pump.side must be 'right' per BLP v1 baseline")
    if cfg.gauge_safety.enabled and cfg.gauge_safety.side != "left":
        raise ValueError("geometry.ports.gauge_safety.side must be 'left' per BLP v1 baseline")

    enabled_sides = [
        port.side
        for port in (cfg.main_pump, cfg.gauge_safety, cfg.rotary_feedthrough, cfg.spare)
        if port.enabled
    ]
    if len(enabled_sides) != len(set(enabled_sides)):
        raise ValueError("geometry.ports enabled ports must use distinct chamber sides")

    return cfg


def _parse_plate(raw: dict[str, Any], prefix: str) -> PlateConfig:
    az_raw = _to_list(raw.get("azimuth_centers_deg"), f"{prefix}.azimuth_centers_deg")
    azimuth_centers = tuple(_to_float(item, f"{prefix}.azimuth_centers_deg[]") for item in az_raw)
    if not azimuth_centers:
        raise ValueError(f"{prefix}.azimuth_centers_deg cannot be empty")

    cfg = PlateConfig(
        orientation=_to_str(raw.get("orientation"), f"{prefix}.orientation").lower(),
        mount_plane=_to_str(raw.get("mount_plane"), f"{prefix}.mount_plane").lower(),
        offset_mode=_to_str(raw.get("offset_mode", "manual"), f"{prefix}.offset_mode").lower(),
        opening_style=_to_str(raw.get("opening_style", "annular_sector"), f"{prefix}.opening_style").lower(),
        z_mm=_to_float(raw.get("z_mm"), f"{prefix}.z_mm"),
        offset_x_mm=_to_float(raw.get("offset_x_mm"), f"{prefix}.offset_x_mm"),
        offset_y_mm=_to_float(raw.get("offset_y_mm"), f"{prefix}.offset_y_mm"),
        width_mm=_to_float(raw.get("width_mm"), f"{prefix}.width_mm"),
        height_mm=_to_float(raw.get("height_mm"), f"{prefix}.height_mm"),
        thickness_mm=_to_float(raw.get("thickness_mm"), f"{prefix}.thickness_mm"),
        inner_radius_mm=_to_float(raw.get("inner_radius_mm"), f"{prefix}.inner_radius_mm"),
        outer_radius_mm=_to_float(raw.get("outer_radius_mm"), f"{prefix}.outer_radius_mm"),
        sector_opening_deg=_to_float(raw.get("sector_opening_deg"), f"{prefix}.sector_opening_deg"),
        azimuth_centers_deg=azimuth_centers,
        lug_length_mm=_to_float(raw.get("lug_length_mm"), f"{prefix}.lug_length_mm"),
        lug_width_mm=_to_float(raw.get("lug_width_mm"), f"{prefix}.lug_width_mm"),
        lug_thickness_mm=_to_float(raw.get("lug_thickness_mm"), f"{prefix}.lug_thickness_mm"),
        bolt_hole_diameter_mm=_to_float(raw.get("bolt_hole_diameter_mm"), f"{prefix}.bolt_hole_diameter_mm"),
        bolt_hole_pitch_mm=_to_float(raw.get("bolt_hole_pitch_mm"), f"{prefix}.bolt_hole_pitch_mm"),
        bolt_hole_count=_to_int(raw.get("bolt_hole_count"), f"{prefix}.bolt_hole_count"),
        stiffener_count=_to_int(raw.get("stiffener_count"), f"{prefix}.stiffener_count"),
        stiffener_thickness_mm=_to_float(raw.get("stiffener_thickness_mm"), f"{prefix}.stiffener_thickness_mm"),
        stiffener_height_mm=_to_float(raw.get("stiffener_height_mm"), f"{prefix}.stiffener_height_mm"),
        stiffener_length_mm=_to_float(raw.get("stiffener_length_mm"), f"{prefix}.stiffener_length_mm"),
    )

    _require_positive(
        {
            f"{prefix}.width_mm": cfg.width_mm,
            f"{prefix}.height_mm": cfg.height_mm,
            f"{prefix}.thickness_mm": cfg.thickness_mm,
            f"{prefix}.inner_radius_mm": cfg.inner_radius_mm,
            f"{prefix}.outer_radius_mm": cfg.outer_radius_mm,
            f"{prefix}.lug_length_mm": cfg.lug_length_mm,
            f"{prefix}.lug_width_mm": cfg.lug_width_mm,
            f"{prefix}.lug_thickness_mm": cfg.lug_thickness_mm,
            f"{prefix}.bolt_hole_diameter_mm": cfg.bolt_hole_diameter_mm,
            f"{prefix}.bolt_hole_pitch_mm": cfg.bolt_hole_pitch_mm,
            f"{prefix}.stiffener_thickness_mm": cfg.stiffener_thickness_mm,
            f"{prefix}.stiffener_height_mm": cfg.stiffener_height_mm,
            f"{prefix}.stiffener_length_mm": cfg.stiffener_length_mm,
        }
    )

    if cfg.outer_radius_mm <= cfg.inner_radius_mm:
        raise ValueError(f"{prefix}.outer_radius_mm must be > inner_radius_mm")
    if cfg.sector_opening_deg < 0.0:
        raise ValueError(f"{prefix}.sector_opening_deg must be >= 0 deg")
    if cfg.sector_opening_deg >= 180.0:
        raise ValueError(f"{prefix}.sector_opening_deg must be < 180 deg")
    if cfg.orientation not in _ALLOWED_PLATE_ORIENTATIONS:
        raise ValueError(
            f"{prefix}.orientation must be one of {sorted(_ALLOWED_PLATE_ORIENTATIONS)}, got {cfg.orientation!r}"
        )
    if cfg.mount_plane not in _ALLOWED_PLATE_MOUNT_PLANES:
        raise ValueError(
            f"{prefix}.mount_plane must be one of {sorted(_ALLOWED_PLATE_MOUNT_PLANES)}, got {cfg.mount_plane!r}"
        )
    if cfg.offset_mode not in _ALLOWED_PLATE_OFFSET_MODES:
        raise ValueError(
            f"{prefix}.offset_mode must be one of {sorted(_ALLOWED_PLATE_OFFSET_MODES)}, got {cfg.offset_mode!r}"
        )
    if cfg.opening_style not in _ALLOWED_PLATE_OPENING_STYLES:
        raise ValueError(
            f"{prefix}.opening_style must be one of {sorted(_ALLOWED_PLATE_OPENING_STYLES)}, got {cfg.opening_style!r}"
        )
    if cfg.bolt_hole_count < 2:
        raise ValueError(f"{prefix}.bolt_hole_count must be >= 2 for load-bearing connection")
    if cfg.stiffener_count < 1:
        raise ValueError(f"{prefix}.stiffener_count must be >= 1 for load-bearing plate")
    if cfg.bolt_hole_diameter_mm >= cfg.lug_width_mm:
        raise ValueError(f"{prefix}.bolt_hole_diameter_mm must be < lug_width_mm")
    if cfg.bolt_hole_pitch_mm * (cfg.bolt_hole_count - 1) >= (cfg.lug_width_mm - cfg.bolt_hole_diameter_mm):
        raise ValueError(f"{prefix}.bolt_hole_pitch_mm is too large for lug_width_mm and bolt_hole_count")

    # [EN] Manual plate pose must be decentered from beam axis to preserve the frozen HVV layout semantics. / [CN] 手工板位必须偏离束流中心轴，以保持冻结的 HVV 布局语义。
    if cfg.offset_mode == "manual" and abs(cfg.offset_x_mm) < 1e-9 and abs(cfg.offset_y_mm) < 1e-9:
        raise ValueError(f"{prefix} must be offset from beam axis (offset_x_mm/offset_y_mm cannot both be zero)")

    return cfg


def _parse_detector(raw: dict[str, Any]) -> DetectorConfig:
    clamp_raw = _to_mapping(raw.get("clamp"), "geometry.detector.clamp")
    adapter_raw = _to_mapping(raw.get("adapter_block"), "geometry.detector.adapter_block")

    clamp = DetectorClampConfig(
        detector_diameter_mm=_to_float(clamp_raw.get("detector_diameter_mm"), "geometry.detector.clamp.detector_diameter_mm"),
        housing_length_mm=_to_float(clamp_raw.get("housing_length_mm"), "geometry.detector.clamp.housing_length_mm"),
        outer_diameter_mm=_to_float(clamp_raw.get("outer_diameter_mm"), "geometry.detector.clamp.outer_diameter_mm"),
        inner_diameter_mm=_to_float(clamp_raw.get("inner_diameter_mm"), "geometry.detector.clamp.inner_diameter_mm"),
        width_mm=_to_float(clamp_raw.get("width_mm"), "geometry.detector.clamp.width_mm"),
        split_gap_mm=_to_float(clamp_raw.get("split_gap_mm"), "geometry.detector.clamp.split_gap_mm"),
        shoulder_height_mm=_to_float(clamp_raw.get("shoulder_height_mm"), "geometry.detector.clamp.shoulder_height_mm"),
        end_stop_length_mm=_to_float(clamp_raw.get("end_stop_length_mm"), "geometry.detector.clamp.end_stop_length_mm"),
        clamp_ear_length_mm=_to_float(
            clamp_raw.get("clamp_ear_length_mm"),
            "geometry.detector.clamp.clamp_ear_length_mm",
        ),
        clamp_ear_width_mm=_to_float(
            clamp_raw.get("clamp_ear_width_mm"),
            "geometry.detector.clamp.clamp_ear_width_mm",
        ),
        clamp_ear_thickness_mm=_to_float(
            clamp_raw.get("clamp_ear_thickness_mm"),
            "geometry.detector.clamp.clamp_ear_thickness_mm",
        ),
        clamp_bolt_diameter_mm=_to_float(
            clamp_raw.get("clamp_bolt_diameter_mm"),
            "geometry.detector.clamp.clamp_bolt_diameter_mm",
        ),
        clamp_bolt_pitch_mm=_to_float(
            clamp_raw.get("clamp_bolt_pitch_mm"),
            "geometry.detector.clamp.clamp_bolt_pitch_mm",
        ),
        anti_rotation_key_width_mm=_to_float(
            clamp_raw.get("anti_rotation_key_width_mm"),
            "geometry.detector.clamp.anti_rotation_key_width_mm",
        ),
        anti_rotation_key_depth_mm=_to_float(
            clamp_raw.get("anti_rotation_key_depth_mm"),
            "geometry.detector.clamp.anti_rotation_key_depth_mm",
        ),
        anti_rotation_key_length_mm=_to_float(
            clamp_raw.get("anti_rotation_key_length_mm"),
            "geometry.detector.clamp.anti_rotation_key_length_mm",
        ),
        support_overlap_mm=_to_float(clamp_raw.get("support_overlap_mm"), "geometry.detector.clamp.support_overlap_mm"),
        mount_base_u_mm=_to_float(clamp_raw.get("mount_base_u_mm"), "geometry.detector.clamp.mount_base_u_mm"),
        mount_base_v_mm=_to_float(clamp_raw.get("mount_base_v_mm"), "geometry.detector.clamp.mount_base_v_mm"),
        mount_base_thickness_mm=_to_float(
            clamp_raw.get("mount_base_thickness_mm"),
            "geometry.detector.clamp.mount_base_thickness_mm",
        ),
        mount_bolt_hole_diameter_mm=_to_float(
            clamp_raw.get("mount_bolt_hole_diameter_mm"),
            "geometry.detector.clamp.mount_bolt_hole_diameter_mm",
        ),
        mount_bolt_pitch_u_mm=_to_float(
            clamp_raw.get("mount_bolt_pitch_u_mm"),
            "geometry.detector.clamp.mount_bolt_pitch_u_mm",
        ),
        mount_bolt_pitch_v_mm=_to_float(
            clamp_raw.get("mount_bolt_pitch_v_mm"),
            "geometry.detector.clamp.mount_bolt_pitch_v_mm",
        ),
    )

    adapter = DetectorAdapterBlockConfig(
        length_mm=_to_float(adapter_raw.get("length_mm"), "geometry.detector.adapter_block.length_mm"),
        width_mm=_to_float(adapter_raw.get("width_mm"), "geometry.detector.adapter_block.width_mm"),
        height_mm=_to_float(adapter_raw.get("height_mm"), "geometry.detector.adapter_block.height_mm"),
        tilt_deg=_to_float(adapter_raw.get("tilt_deg"), "geometry.detector.adapter_block.tilt_deg"),
        radial_standoff_mm=_to_float(
            adapter_raw.get("radial_standoff_mm"),
            "geometry.detector.adapter_block.radial_standoff_mm",
        ),
    )

    _require_positive(
        {
            "geometry.detector.clamp.detector_diameter_mm": clamp.detector_diameter_mm,
            "geometry.detector.clamp.housing_length_mm": clamp.housing_length_mm,
            "geometry.detector.clamp.outer_diameter_mm": clamp.outer_diameter_mm,
            "geometry.detector.clamp.inner_diameter_mm": clamp.inner_diameter_mm,
            "geometry.detector.clamp.width_mm": clamp.width_mm,
            "geometry.detector.clamp.split_gap_mm": clamp.split_gap_mm,
            "geometry.detector.clamp.shoulder_height_mm": clamp.shoulder_height_mm,
            "geometry.detector.clamp.end_stop_length_mm": clamp.end_stop_length_mm,
            "geometry.detector.clamp.clamp_ear_length_mm": clamp.clamp_ear_length_mm,
            "geometry.detector.clamp.clamp_ear_width_mm": clamp.clamp_ear_width_mm,
            "geometry.detector.clamp.clamp_ear_thickness_mm": clamp.clamp_ear_thickness_mm,
            "geometry.detector.clamp.clamp_bolt_diameter_mm": clamp.clamp_bolt_diameter_mm,
            "geometry.detector.clamp.clamp_bolt_pitch_mm": clamp.clamp_bolt_pitch_mm,
            "geometry.detector.clamp.anti_rotation_key_width_mm": clamp.anti_rotation_key_width_mm,
            "geometry.detector.clamp.anti_rotation_key_depth_mm": clamp.anti_rotation_key_depth_mm,
            "geometry.detector.clamp.anti_rotation_key_length_mm": clamp.anti_rotation_key_length_mm,
            "geometry.detector.clamp.support_overlap_mm": clamp.support_overlap_mm,
            "geometry.detector.clamp.mount_base_u_mm": clamp.mount_base_u_mm,
            "geometry.detector.clamp.mount_base_v_mm": clamp.mount_base_v_mm,
            "geometry.detector.clamp.mount_base_thickness_mm": clamp.mount_base_thickness_mm,
            "geometry.detector.clamp.mount_bolt_hole_diameter_mm": clamp.mount_bolt_hole_diameter_mm,
            "geometry.detector.clamp.mount_bolt_pitch_u_mm": clamp.mount_bolt_pitch_u_mm,
            "geometry.detector.clamp.mount_bolt_pitch_v_mm": clamp.mount_bolt_pitch_v_mm,
            "geometry.detector.adapter_block.length_mm": adapter.length_mm,
            "geometry.detector.adapter_block.width_mm": adapter.width_mm,
            "geometry.detector.adapter_block.height_mm": adapter.height_mm,
            "geometry.detector.adapter_block.radial_standoff_mm": adapter.radial_standoff_mm,
        }
    )

    if clamp.detector_diameter_mm >= clamp.inner_diameter_mm:
        raise ValueError("geometry.detector.clamp.detector_diameter_mm must be < inner_diameter_mm")
    if clamp.inner_diameter_mm >= clamp.outer_diameter_mm:
        raise ValueError("geometry.detector.clamp.inner_diameter_mm must be < outer_diameter_mm")
    if clamp.clamp_bolt_diameter_mm >= min(clamp.clamp_ear_width_mm, clamp.clamp_ear_thickness_mm):
        raise ValueError("geometry.detector.clamp.clamp_bolt_diameter_mm must be < min(clamp_ear_width_mm, clamp_ear_thickness_mm)")
    if clamp.clamp_bolt_pitch_mm > clamp.width_mm:
        raise ValueError("geometry.detector.clamp.clamp_bolt_pitch_mm must be <= width_mm")
    if clamp.clamp_ear_length_mm > clamp.width_mm:
        raise ValueError("geometry.detector.clamp.clamp_ear_length_mm must be <= width_mm")
    key_radial_budget = 0.5 * (clamp.inner_diameter_mm - clamp.detector_diameter_mm)
    if clamp.anti_rotation_key_depth_mm >= key_radial_budget:
        raise ValueError("geometry.detector.clamp.anti_rotation_key_depth_mm is too large for clamp radial clearance")
    if clamp.anti_rotation_key_length_mm > clamp.width_mm:
        raise ValueError("geometry.detector.clamp.anti_rotation_key_length_mm must be <= width_mm")
    if clamp.mount_bolt_hole_diameter_mm >= min(clamp.mount_base_u_mm, clamp.mount_base_v_mm):
        raise ValueError("geometry.detector.clamp.mount_bolt_hole_diameter_mm must be < min(mount_base_u_mm, mount_base_v_mm)")
    if clamp.mount_bolt_pitch_u_mm >= (clamp.mount_base_u_mm - clamp.mount_bolt_hole_diameter_mm):
        raise ValueError("geometry.detector.clamp.mount_bolt_pitch_u_mm too large for mount_base_u_mm and hole diameter")
    if clamp.mount_bolt_pitch_v_mm >= (clamp.mount_base_v_mm - clamp.mount_bolt_hole_diameter_mm):
        raise ValueError("geometry.detector.clamp.mount_bolt_pitch_v_mm too large for mount_base_v_mm and hole diameter")
    if abs(adapter.tilt_deg) > 45.0:
        raise ValueError("geometry.detector.adapter_block.tilt_deg absolute value must be <= 45 deg")

    return DetectorConfig(clamp=clamp, adapter_block=adapter)


def _parse_target_ladder(raw: dict[str, Any]) -> TargetLadderConfig:
    ladder = TargetLadderConfig(
        carriage_thickness_mm=_to_float(
            raw.get("carriage_thickness_mm"),
            "geometry.target.ladder.carriage_thickness_mm",
        ),
        carriage_width_mm=_to_float(raw.get("carriage_width_mm"), "geometry.target.ladder.carriage_width_mm"),
        carriage_height_mm=_to_float(
            raw.get("carriage_height_mm"),
            "geometry.target.ladder.carriage_height_mm",
        ),
        slot_pitch_mm=_to_float(raw.get("slot_pitch_mm"), "geometry.target.ladder.slot_pitch_mm"),
        slot_window_diameter_mm=_to_float(
            raw.get("slot_window_diameter_mm"),
            "geometry.target.ladder.slot_window_diameter_mm",
        ),
        rail_diameter_mm=_to_float(raw.get("rail_diameter_mm"), "geometry.target.ladder.rail_diameter_mm"),
        rail_span_mm=_to_float(raw.get("rail_span_mm"), "geometry.target.ladder.rail_span_mm"),
        feedthrough_shaft_diameter_mm=_to_float(
            raw.get("feedthrough_shaft_diameter_mm"),
            "geometry.target.ladder.feedthrough_shaft_diameter_mm",
        ),
        feedthrough_length_mm=_to_float(
            raw.get("feedthrough_length_mm"),
            "geometry.target.ladder.feedthrough_length_mm",
        ),
        handwheel_diameter_mm=_to_float(
            raw.get("handwheel_diameter_mm"),
            "geometry.target.ladder.handwheel_diameter_mm",
        ),
        motor_mount_width_mm=_to_float(
            raw.get("motor_mount_width_mm"),
            "geometry.target.ladder.motor_mount_width_mm",
        ),
        motor_mount_height_mm=_to_float(
            raw.get("motor_mount_height_mm"),
            "geometry.target.ladder.motor_mount_height_mm",
        ),
        motor_mount_thickness_mm=_to_float(
            raw.get("motor_mount_thickness_mm"),
            "geometry.target.ladder.motor_mount_thickness_mm",
        ),
        hard_stop_span_mm=_to_float(
            raw.get("hard_stop_span_mm"),
            "geometry.target.ladder.hard_stop_span_mm",
        ),
        hard_stop_thickness_mm=_to_float(
            raw.get("hard_stop_thickness_mm"),
            "geometry.target.ladder.hard_stop_thickness_mm",
        ),
        index_disk_diameter_mm=_to_float(
            raw.get("index_disk_diameter_mm"),
            "geometry.target.ladder.index_disk_diameter_mm",
        ),
        index_disk_thickness_mm=_to_float(
            raw.get("index_disk_thickness_mm"),
            "geometry.target.ladder.index_disk_thickness_mm",
        ),
        index_pin_diameter_mm=_to_float(
            raw.get("index_pin_diameter_mm"),
            "geometry.target.ladder.index_pin_diameter_mm",
        ),
        index_pin_length_mm=_to_float(
            raw.get("index_pin_length_mm"),
            "geometry.target.ladder.index_pin_length_mm",
        ),
        active_index=_to_int(raw.get("active_index"), "geometry.target.ladder.active_index"),
    )

    _require_positive(
        {
            "geometry.target.ladder.carriage_thickness_mm": ladder.carriage_thickness_mm,
            "geometry.target.ladder.carriage_width_mm": ladder.carriage_width_mm,
            "geometry.target.ladder.carriage_height_mm": ladder.carriage_height_mm,
            "geometry.target.ladder.slot_pitch_mm": ladder.slot_pitch_mm,
            "geometry.target.ladder.slot_window_diameter_mm": ladder.slot_window_diameter_mm,
            "geometry.target.ladder.rail_diameter_mm": ladder.rail_diameter_mm,
            "geometry.target.ladder.rail_span_mm": ladder.rail_span_mm,
            "geometry.target.ladder.feedthrough_shaft_diameter_mm": ladder.feedthrough_shaft_diameter_mm,
            "geometry.target.ladder.feedthrough_length_mm": ladder.feedthrough_length_mm,
            "geometry.target.ladder.handwheel_diameter_mm": ladder.handwheel_diameter_mm,
            "geometry.target.ladder.motor_mount_width_mm": ladder.motor_mount_width_mm,
            "geometry.target.ladder.motor_mount_height_mm": ladder.motor_mount_height_mm,
            "geometry.target.ladder.motor_mount_thickness_mm": ladder.motor_mount_thickness_mm,
            "geometry.target.ladder.hard_stop_span_mm": ladder.hard_stop_span_mm,
            "geometry.target.ladder.hard_stop_thickness_mm": ladder.hard_stop_thickness_mm,
            "geometry.target.ladder.index_disk_diameter_mm": ladder.index_disk_diameter_mm,
            "geometry.target.ladder.index_disk_thickness_mm": ladder.index_disk_thickness_mm,
            "geometry.target.ladder.index_pin_diameter_mm": ladder.index_pin_diameter_mm,
            "geometry.target.ladder.index_pin_length_mm": ladder.index_pin_length_mm,
        }
    )

    if ladder.active_index not in {0, 1, 2}:
        raise ValueError("geometry.target.ladder.active_index must be 0, 1, or 2 for 3-position ladder")
    if ladder.index_pin_diameter_mm >= ladder.index_disk_diameter_mm:
        raise ValueError("geometry.target.ladder.index_pin_diameter_mm must be < index_disk_diameter_mm")
    if ladder.hard_stop_span_mm >= ladder.handwheel_diameter_mm:
        raise ValueError("geometry.target.ladder.hard_stop_span_mm must be < handwheel_diameter_mm")

    return ladder


def _parse_target_holder(raw: dict[str, Any]) -> TargetHolderConfig:
    holder = TargetHolderConfig(
        frame_outer_width_mm=_to_float(
            raw.get("frame_outer_width_mm"),
            "geometry.target.holder.frame_outer_width_mm",
        ),
        frame_outer_height_mm=_to_float(
            raw.get("frame_outer_height_mm"),
            "geometry.target.holder.frame_outer_height_mm",
        ),
        frame_thickness_mm=_to_float(raw.get("frame_thickness_mm"), "geometry.target.holder.frame_thickness_mm"),
        clamp_block_width_mm=_to_float(
            raw.get("clamp_block_width_mm"),
            "geometry.target.holder.clamp_block_width_mm",
        ),
        clamp_block_height_mm=_to_float(
            raw.get("clamp_block_height_mm"),
            "geometry.target.holder.clamp_block_height_mm",
        ),
        clamp_screw_diameter_mm=_to_float(
            raw.get("clamp_screw_diameter_mm"),
            "geometry.target.holder.clamp_screw_diameter_mm",
        ),
        clamp_screw_head_diameter_mm=_to_float(
            raw.get("clamp_screw_head_diameter_mm"),
            "geometry.target.holder.clamp_screw_head_diameter_mm",
        ),
        clamp_screw_head_height_mm=_to_float(
            raw.get("clamp_screw_head_height_mm"),
            "geometry.target.holder.clamp_screw_head_height_mm",
        ),
        experiment_target_thickness_mm=_to_float(
            raw.get("experiment_target_thickness_mm"),
            "geometry.target.holder.experiment_target_thickness_mm",
        ),
        fluorescence_target_thickness_mm=_to_float(
            raw.get("fluorescence_target_thickness_mm"),
            "geometry.target.holder.fluorescence_target_thickness_mm",
        ),
    )

    _require_positive(
        {
            "geometry.target.holder.frame_outer_width_mm": holder.frame_outer_width_mm,
            "geometry.target.holder.frame_outer_height_mm": holder.frame_outer_height_mm,
            "geometry.target.holder.frame_thickness_mm": holder.frame_thickness_mm,
            "geometry.target.holder.clamp_block_width_mm": holder.clamp_block_width_mm,
            "geometry.target.holder.clamp_block_height_mm": holder.clamp_block_height_mm,
            "geometry.target.holder.clamp_screw_diameter_mm": holder.clamp_screw_diameter_mm,
            "geometry.target.holder.clamp_screw_head_diameter_mm": holder.clamp_screw_head_diameter_mm,
            "geometry.target.holder.clamp_screw_head_height_mm": holder.clamp_screw_head_height_mm,
            "geometry.target.holder.experiment_target_thickness_mm": holder.experiment_target_thickness_mm,
            "geometry.target.holder.fluorescence_target_thickness_mm": holder.fluorescence_target_thickness_mm,
        }
    )

    if holder.clamp_screw_diameter_mm >= min(holder.clamp_block_width_mm, holder.clamp_block_height_mm):
        raise ValueError("geometry.target.holder.clamp_screw_diameter_mm must be < min(clamp_block_width_mm, clamp_block_height_mm)")
    if holder.clamp_screw_head_diameter_mm > holder.clamp_block_width_mm:
        raise ValueError("geometry.target.holder.clamp_screw_head_diameter_mm must be <= clamp_block_width_mm")
    if holder.clamp_screw_head_height_mm >= holder.frame_thickness_mm:
        raise ValueError("geometry.target.holder.clamp_screw_head_height_mm must be < frame_thickness_mm")

    return holder


def _parse_target_rotary(raw: dict[str, Any]) -> TargetRotaryConfig:
    rotary = TargetRotaryConfig(
        pivot_x_mm=_to_float(raw.get("pivot_x_mm"), "geometry.target.rotary.pivot_x_mm"),
        work_angle_deg=_to_float(raw.get("work_angle_deg", 0.0), "geometry.target.rotary.work_angle_deg"),
        park_angle_deg=_to_float(raw.get("park_angle_deg"), "geometry.target.rotary.park_angle_deg"),
        active_angle_deg=_to_float(raw.get("active_angle_deg", 0.0), "geometry.target.rotary.active_angle_deg"),
        feedthrough_shaft_diameter_mm=_to_float(
            raw.get("feedthrough_shaft_diameter_mm"),
            "geometry.target.rotary.feedthrough_shaft_diameter_mm",
        ),
        feedthrough_length_mm=_to_float(
            raw.get("feedthrough_length_mm"),
            "geometry.target.rotary.feedthrough_length_mm",
        ),
        handwheel_diameter_mm=_to_float(
            raw.get("handwheel_diameter_mm"),
            "geometry.target.rotary.handwheel_diameter_mm",
        ),
        motor_mount_width_mm=_to_float(
            raw.get("motor_mount_width_mm"),
            "geometry.target.rotary.motor_mount_width_mm",
        ),
        motor_mount_height_mm=_to_float(
            raw.get("motor_mount_height_mm"),
            "geometry.target.rotary.motor_mount_height_mm",
        ),
        motor_mount_thickness_mm=_to_float(
            raw.get("motor_mount_thickness_mm"),
            "geometry.target.rotary.motor_mount_thickness_mm",
        ),
        hub_diameter_mm=_to_float(raw.get("hub_diameter_mm"), "geometry.target.rotary.hub_diameter_mm"),
        hub_thickness_mm=_to_float(raw.get("hub_thickness_mm"), "geometry.target.rotary.hub_thickness_mm"),
        arm_length_mm=_to_float(raw.get("arm_length_mm"), "geometry.target.rotary.arm_length_mm"),
        arm_width_mm=_to_float(raw.get("arm_width_mm"), "geometry.target.rotary.arm_width_mm"),
        arm_thickness_mm=_to_float(raw.get("arm_thickness_mm"), "geometry.target.rotary.arm_thickness_mm"),
        hard_stop_span_mm=_to_float(raw.get("hard_stop_span_mm"), "geometry.target.rotary.hard_stop_span_mm"),
        hard_stop_thickness_mm=_to_float(
            raw.get("hard_stop_thickness_mm"),
            "geometry.target.rotary.hard_stop_thickness_mm",
        ),
        index_disk_diameter_mm=_to_float(
            raw.get("index_disk_diameter_mm"),
            "geometry.target.rotary.index_disk_diameter_mm",
        ),
        index_disk_thickness_mm=_to_float(
            raw.get("index_disk_thickness_mm"),
            "geometry.target.rotary.index_disk_thickness_mm",
        ),
        index_pin_diameter_mm=_to_float(
            raw.get("index_pin_diameter_mm"),
            "geometry.target.rotary.index_pin_diameter_mm",
        ),
        index_pin_length_mm=_to_float(
            raw.get("index_pin_length_mm"),
            "geometry.target.rotary.index_pin_length_mm",
        ),
        vendor_reference_enabled=_to_bool(
            raw.get("vendor_reference_enabled", False),
            "geometry.target.rotary.vendor_reference_enabled",
        ),
        vendor_reference_model_code=(
            _to_str(raw.get("vendor_reference_model_code"), "geometry.target.rotary.vendor_reference_model_code")
            if raw.get("vendor_reference_model_code") is not None
            else None
        ),
        vendor_reference_body_diameter_mm=_to_float(
            raw.get("vendor_reference_body_diameter_mm", 36.0),
            "geometry.target.rotary.vendor_reference_body_diameter_mm",
        ),
        vendor_reference_body_length_mm=_to_float(
            raw.get("vendor_reference_body_length_mm", 70.0),
            "geometry.target.rotary.vendor_reference_body_length_mm",
        ),
        vendor_reference_handwheel_diameter_mm=_to_float(
            raw.get("vendor_reference_handwheel_diameter_mm", 52.0),
            "geometry.target.rotary.vendor_reference_handwheel_diameter_mm",
        ),
        vendor_reference_handwheel_thickness_mm=_to_float(
            raw.get("vendor_reference_handwheel_thickness_mm", 12.0),
            "geometry.target.rotary.vendor_reference_handwheel_thickness_mm",
        ),
    )

    _require_positive(
        {
            "geometry.target.rotary.pivot_x_mm": rotary.pivot_x_mm,
            "geometry.target.rotary.feedthrough_shaft_diameter_mm": rotary.feedthrough_shaft_diameter_mm,
            "geometry.target.rotary.feedthrough_length_mm": rotary.feedthrough_length_mm,
            "geometry.target.rotary.handwheel_diameter_mm": rotary.handwheel_diameter_mm,
            "geometry.target.rotary.motor_mount_width_mm": rotary.motor_mount_width_mm,
            "geometry.target.rotary.motor_mount_height_mm": rotary.motor_mount_height_mm,
            "geometry.target.rotary.motor_mount_thickness_mm": rotary.motor_mount_thickness_mm,
            "geometry.target.rotary.hub_diameter_mm": rotary.hub_diameter_mm,
            "geometry.target.rotary.hub_thickness_mm": rotary.hub_thickness_mm,
            "geometry.target.rotary.arm_length_mm": rotary.arm_length_mm,
            "geometry.target.rotary.arm_width_mm": rotary.arm_width_mm,
            "geometry.target.rotary.arm_thickness_mm": rotary.arm_thickness_mm,
            "geometry.target.rotary.hard_stop_span_mm": rotary.hard_stop_span_mm,
            "geometry.target.rotary.hard_stop_thickness_mm": rotary.hard_stop_thickness_mm,
            "geometry.target.rotary.index_disk_diameter_mm": rotary.index_disk_diameter_mm,
            "geometry.target.rotary.index_disk_thickness_mm": rotary.index_disk_thickness_mm,
            "geometry.target.rotary.index_pin_diameter_mm": rotary.index_pin_diameter_mm,
            "geometry.target.rotary.index_pin_length_mm": rotary.index_pin_length_mm,
            "geometry.target.rotary.vendor_reference_body_diameter_mm": rotary.vendor_reference_body_diameter_mm,
            "geometry.target.rotary.vendor_reference_body_length_mm": rotary.vendor_reference_body_length_mm,
            "geometry.target.rotary.vendor_reference_handwheel_diameter_mm": rotary.vendor_reference_handwheel_diameter_mm,
            "geometry.target.rotary.vendor_reference_handwheel_thickness_mm": rotary.vendor_reference_handwheel_thickness_mm,
        }
    )

    if abs(rotary.work_angle_deg) > 1e-9:
        raise ValueError("geometry.target.rotary.work_angle_deg must be 0 deg for the frozen single-rotary work pose")
    if rotary.park_angle_deg <= 0.0 or rotary.park_angle_deg >= 180.0:
        raise ValueError("geometry.target.rotary.park_angle_deg must lie in (0, 180)")
    if rotary.active_angle_deg < rotary.work_angle_deg or rotary.active_angle_deg > rotary.park_angle_deg:
        raise ValueError("geometry.target.rotary.active_angle_deg must lie within [work_angle_deg, park_angle_deg]")
    if rotary.index_pin_diameter_mm >= rotary.index_disk_diameter_mm:
        raise ValueError("geometry.target.rotary.index_pin_diameter_mm must be < index_disk_diameter_mm")
    if rotary.hard_stop_span_mm >= rotary.handwheel_diameter_mm:
        raise ValueError("geometry.target.rotary.hard_stop_span_mm must be < handwheel_diameter_mm")
    if rotary.vendor_reference_enabled and rotary.vendor_reference_model_code is None:
        raise ValueError(
            "geometry.target.rotary.vendor_reference_model_code is required when vendor_reference_enabled=true"
        )

    return rotary


def _parse_single_target_holder(raw: dict[str, Any]) -> SingleTargetHolderConfig:
    holder = SingleTargetHolderConfig(
        frame_outer_width_mm=_to_float(
            raw.get("frame_outer_width_mm"),
            "geometry.target.single_holder.frame_outer_width_mm",
        ),
        frame_outer_height_mm=_to_float(
            raw.get("frame_outer_height_mm"),
            "geometry.target.single_holder.frame_outer_height_mm",
        ),
        frame_thickness_mm=_to_float(
            raw.get("frame_thickness_mm"),
            "geometry.target.single_holder.frame_thickness_mm",
        ),
        clamp_block_width_mm=_to_float(
            raw.get("clamp_block_width_mm"),
            "geometry.target.single_holder.clamp_block_width_mm",
        ),
        clamp_block_height_mm=_to_float(
            raw.get("clamp_block_height_mm"),
            "geometry.target.single_holder.clamp_block_height_mm",
        ),
        clamp_screw_diameter_mm=_to_float(
            raw.get("clamp_screw_diameter_mm"),
            "geometry.target.single_holder.clamp_screw_diameter_mm",
        ),
        clamp_screw_head_diameter_mm=_to_float(
            raw.get("clamp_screw_head_diameter_mm"),
            "geometry.target.single_holder.clamp_screw_head_diameter_mm",
        ),
        clamp_screw_head_height_mm=_to_float(
            raw.get("clamp_screw_head_height_mm"),
            "geometry.target.single_holder.clamp_screw_head_height_mm",
        ),
        target_thickness_mm=_to_float(
            raw.get("target_thickness_mm"),
            "geometry.target.single_holder.target_thickness_mm",
        ),
    )

    _require_positive(
        {
            "geometry.target.single_holder.frame_outer_width_mm": holder.frame_outer_width_mm,
            "geometry.target.single_holder.frame_outer_height_mm": holder.frame_outer_height_mm,
            "geometry.target.single_holder.frame_thickness_mm": holder.frame_thickness_mm,
            "geometry.target.single_holder.clamp_block_width_mm": holder.clamp_block_width_mm,
            "geometry.target.single_holder.clamp_block_height_mm": holder.clamp_block_height_mm,
            "geometry.target.single_holder.clamp_screw_diameter_mm": holder.clamp_screw_diameter_mm,
            "geometry.target.single_holder.clamp_screw_head_diameter_mm": holder.clamp_screw_head_diameter_mm,
            "geometry.target.single_holder.clamp_screw_head_height_mm": holder.clamp_screw_head_height_mm,
            "geometry.target.single_holder.target_thickness_mm": holder.target_thickness_mm,
        }
    )

    if holder.clamp_screw_diameter_mm >= min(holder.clamp_block_width_mm, holder.clamp_block_height_mm):
        raise ValueError("geometry.target.single_holder.clamp_screw_diameter_mm must be < min(clamp_block_width_mm, clamp_block_height_mm)")
    if holder.clamp_screw_head_diameter_mm > holder.clamp_block_width_mm:
        raise ValueError("geometry.target.single_holder.clamp_screw_head_diameter_mm must be <= clamp_block_width_mm")
    if holder.clamp_screw_head_height_mm >= holder.frame_thickness_mm:
        raise ValueError("geometry.target.single_holder.clamp_screw_head_height_mm must be < frame_thickness_mm")

    return holder


def _parse_target(raw: dict[str, Any]) -> TargetConfig:
    mode = _to_str(raw.get("mode", "linear_ladder"), "geometry.target.mode").lower()
    if mode not in _ALLOWED_TARGET_MODES:
        raise ValueError(f"geometry.target.mode must be one of {sorted(_ALLOWED_TARGET_MODES)}, got {mode!r}")

    if mode == "linear_ladder":
        ladder_raw = _to_mapping(raw.get("ladder"), "geometry.target.ladder")
        holder_raw = _to_mapping(raw.get("holder"), "geometry.target.holder")
        return TargetConfig(
            mode=mode,
            ladder=_parse_target_ladder(ladder_raw),
            holder=_parse_target_holder(holder_raw),
            rotary=None,
            single_holder=None,
        )

    rotary_raw = _to_mapping(raw.get("rotary"), "geometry.target.rotary")
    single_holder_raw = _to_mapping(raw.get("single_holder"), "geometry.target.single_holder")
    return TargetConfig(
        mode=mode,
        ladder=None,
        holder=None,
        rotary=_parse_target_rotary(rotary_raw),
        single_holder=_parse_single_target_holder(single_holder_raw),
    )


def _parse_stand(raw: dict[str, Any]) -> StandConfig:
    cfg = StandConfig(
        with_base_plate=_to_bool(raw.get("with_base_plate", True), "geometry.stand.with_base_plate"),
        base_length_mm=_to_float(raw.get("base_length_mm"), "geometry.stand.base_length_mm"),
        base_width_mm=_to_float(raw.get("base_width_mm"), "geometry.stand.base_width_mm"),
        base_thickness_mm=_to_float(raw.get("base_thickness_mm"), "geometry.stand.base_thickness_mm"),
        chamber_support_height_mm=_to_float(
            raw.get("chamber_support_height_mm"),
            "geometry.stand.chamber_support_height_mm",
        ),
        support_foot_diameter_mm=_to_float(
            raw.get("support_foot_diameter_mm"),
            "geometry.stand.support_foot_diameter_mm",
        ),
        chamber_support_end_margin_mm=_to_float(
            raw.get("chamber_support_end_margin_mm", 100.0),
            "geometry.stand.chamber_support_end_margin_mm",
        ),
        chamber_support_pair_half_span_x_mm=_to_float(
            raw.get("chamber_support_pair_half_span_x_mm", 50.0),
            "geometry.stand.chamber_support_pair_half_span_x_mm",
        ),
        h_plate_support_end_margin_mm=_to_float(
            raw.get("h_plate_support_end_margin_mm", 100.0),
            "geometry.stand.h_plate_support_end_margin_mm",
        ),
        h_plate_support_pair_half_span_x_mm=_to_float(
            raw.get("h_plate_support_pair_half_span_x_mm", 160.0),
            "geometry.stand.h_plate_support_pair_half_span_x_mm",
        ),
        enable_plate_ties=_to_bool(raw.get("enable_plate_ties", True), "geometry.stand.enable_plate_ties"),
        plate_tie_column_diameter_mm=_to_float(
            raw.get("plate_tie_column_diameter_mm"),
            "geometry.stand.plate_tie_column_diameter_mm",
        ),
        plate_tie_cap_width_mm=_to_float(
            raw.get("plate_tie_cap_width_mm"),
            "geometry.stand.plate_tie_cap_width_mm",
        ),
        plate_tie_cap_height_mm=_to_float(
            raw.get("plate_tie_cap_height_mm"),
            "geometry.stand.plate_tie_cap_height_mm",
        ),
        plate_tie_cap_thickness_mm=_to_float(
            raw.get("plate_tie_cap_thickness_mm"),
            "geometry.stand.plate_tie_cap_thickness_mm",
        ),
        plate_tie_bolt_diameter_mm=_to_float(
            raw.get("plate_tie_bolt_diameter_mm"),
            "geometry.stand.plate_tie_bolt_diameter_mm",
        ),
        anchor_slot_length_mm=_to_float(raw.get("anchor_slot_length_mm"), "geometry.stand.anchor_slot_length_mm"),
        anchor_slot_width_mm=_to_float(raw.get("anchor_slot_width_mm"), "geometry.stand.anchor_slot_width_mm"),
        leveling_screw_diameter_mm=_to_float(
            raw.get("leveling_screw_diameter_mm"),
            "geometry.stand.leveling_screw_diameter_mm",
        ),
        shim_thickness_mm=_to_float(raw.get("shim_thickness_mm"), "geometry.stand.shim_thickness_mm"),
    )

    positive_fields = {
        "geometry.stand.base_length_mm": cfg.base_length_mm,
        "geometry.stand.base_width_mm": cfg.base_width_mm,
        "geometry.stand.base_thickness_mm": cfg.base_thickness_mm,
        "geometry.stand.chamber_support_height_mm": cfg.chamber_support_height_mm,
        "geometry.stand.support_foot_diameter_mm": cfg.support_foot_diameter_mm,
        "geometry.stand.chamber_support_end_margin_mm": cfg.chamber_support_end_margin_mm,
        "geometry.stand.chamber_support_pair_half_span_x_mm": cfg.chamber_support_pair_half_span_x_mm,
        "geometry.stand.h_plate_support_end_margin_mm": cfg.h_plate_support_end_margin_mm,
        "geometry.stand.h_plate_support_pair_half_span_x_mm": cfg.h_plate_support_pair_half_span_x_mm,
        "geometry.stand.leveling_screw_diameter_mm": cfg.leveling_screw_diameter_mm,
        "geometry.stand.shim_thickness_mm": cfg.shim_thickness_mm,
    }
    if cfg.with_base_plate:
        positive_fields.update(
            {
                "geometry.stand.anchor_slot_length_mm": cfg.anchor_slot_length_mm,
                "geometry.stand.anchor_slot_width_mm": cfg.anchor_slot_width_mm,
            }
        )
    if cfg.enable_plate_ties:
        positive_fields.update(
            {
                "geometry.stand.plate_tie_column_diameter_mm": cfg.plate_tie_column_diameter_mm,
                "geometry.stand.plate_tie_cap_width_mm": cfg.plate_tie_cap_width_mm,
                "geometry.stand.plate_tie_cap_height_mm": cfg.plate_tie_cap_height_mm,
                "geometry.stand.plate_tie_cap_thickness_mm": cfg.plate_tie_cap_thickness_mm,
                "geometry.stand.plate_tie_bolt_diameter_mm": cfg.plate_tie_bolt_diameter_mm,
            }
        )
    _require_positive(positive_fields)

    if cfg.enable_plate_ties:
        if cfg.plate_tie_bolt_diameter_mm >= cfg.plate_tie_column_diameter_mm:
            raise ValueError("geometry.stand.plate_tie_bolt_diameter_mm must be < plate_tie_column_diameter_mm")
        if cfg.plate_tie_bolt_diameter_mm >= min(cfg.plate_tie_cap_width_mm, cfg.plate_tie_cap_height_mm):
            raise ValueError("geometry.stand.plate_tie_bolt_diameter_mm must be < min(plate_tie_cap_width_mm, plate_tie_cap_height_mm)")

    return cfg


def _parse_clearance(raw: dict[str, Any]) -> ClearanceConfig:
    cfg = ClearanceConfig(
        los_scope=_to_str(raw.get("los_scope", "v1_conceptual"), "geometry.clearance.los_scope").lower(),
        los_margin_mm=_to_float(raw.get("los_margin_mm"), "geometry.clearance.los_margin_mm"),
        vv_min_gap_factor=_to_float(raw.get("vv_min_gap_factor", 2.0), "geometry.clearance.vv_min_gap_factor"),
        plate_auto_gap_mm=_to_float(raw.get("plate_auto_gap_mm", 5.0), "geometry.clearance.plate_auto_gap_mm"),
        plate_chamber_cutout_margin_mm=_to_float(
            raw.get("plate_chamber_cutout_margin_mm", 5.0),
            "geometry.clearance.plate_chamber_cutout_margin_mm",
        ),
        disable_plate_cuts=_to_bool(raw.get("disable_plate_cuts", False), "geometry.clearance.disable_plate_cuts"),
        skip_overlap_checks=_to_bool(raw.get("skip_overlap_checks", False), "geometry.clearance.skip_overlap_checks"),
        los_detector_active_face_offset_mm=_to_float(
            raw.get("los_detector_active_face_offset_mm", 0.0),
            "geometry.clearance.los_detector_active_face_offset_mm",
        ),
        detector_front_to_chamber_mm=_to_float(
            raw.get("detector_front_to_chamber_mm"),
            "geometry.clearance.detector_front_to_chamber_mm",
        ),
        detector_pair_min_gap_mm=_to_float(
            raw.get("detector_pair_min_gap_mm"),
            "geometry.clearance.detector_pair_min_gap_mm",
        ),
        top_service_clearance_mm=_to_float(
            raw.get("top_service_clearance_mm"),
            "geometry.clearance.top_service_clearance_mm",
        ),
        side_service_clearance_mm=_to_float(
            raw.get("side_service_clearance_mm"),
            "geometry.clearance.side_service_clearance_mm",
        ),
    )

    _require_positive(
        {
            "geometry.clearance.los_margin_mm": cfg.los_margin_mm,
            "geometry.clearance.vv_min_gap_factor": cfg.vv_min_gap_factor,
            "geometry.clearance.plate_auto_gap_mm": cfg.plate_auto_gap_mm,
            "geometry.clearance.plate_chamber_cutout_margin_mm": cfg.plate_chamber_cutout_margin_mm,
            "geometry.clearance.detector_front_to_chamber_mm": cfg.detector_front_to_chamber_mm,
            "geometry.clearance.detector_pair_min_gap_mm": cfg.detector_pair_min_gap_mm,
            "geometry.clearance.top_service_clearance_mm": cfg.top_service_clearance_mm,
            "geometry.clearance.side_service_clearance_mm": cfg.side_service_clearance_mm,
        }
    )
    if cfg.los_scope not in _ALLOWED_LOS_SCOPES:
        raise ValueError(f"geometry.clearance.los_scope must be one of {sorted(_ALLOWED_LOS_SCOPES)}")
    if cfg.los_detector_active_face_offset_mm < 0.0:
        raise ValueError("geometry.clearance.los_detector_active_face_offset_mm must be >= 0")
    if cfg.vv_min_gap_factor < 1.0:
        raise ValueError("geometry.clearance.vv_min_gap_factor must be >= 1.0")

    return cfg


def _resolve_auto_plate_offset(
    plate: PlateConfig,
    *,
    core: ChamberCoreConfig,
    clearance: ClearanceConfig,
) -> PlateConfig:
    if plate.offset_mode != "auto":
        return plate

    # [EN] Auto mode only solves plate-normal standoff to the minimum outside-chamber position plus configured safety gap; in-plane offsets remain user-owned. / [CN] 自动模式仅解算板法向外置距离（腔体外最小距离+安全间隙），板内平移仍由用户控制。
    if plate.mount_plane == "xy":
        sign = 1.0 if plate.z_mm >= core.center_z_mm else -1.0
        if abs(plate.z_mm) < 1e-9:
            sign = 1.0
        face_z = core.center_z_mm + sign * (0.5 * core.size_z_mm)
        z_mm = face_z + sign * (0.5 * plate.thickness_mm + clearance.plate_auto_gap_mm)
        return replace(plate, z_mm=z_mm)

    if plate.mount_plane == "xz":
        sign = 1.0 if plate.offset_y_mm >= 0.0 else -1.0
        if abs(plate.offset_y_mm) < 1e-9:
            sign = 1.0
        offset_y_mm = sign * (0.5 * core.size_y_mm + 0.5 * plate.thickness_mm + clearance.plate_auto_gap_mm)
        return replace(plate, offset_y_mm=offset_y_mm)

    if plate.mount_plane == "yz":
        sign = 1.0 if plate.offset_x_mm >= 0.0 else -1.0
        if abs(plate.offset_x_mm) < 1e-9:
            sign = 1.0
        offset_x_mm = sign * (0.5 * core.size_x_mm + 0.5 * plate.thickness_mm + clearance.plate_auto_gap_mm)
        return replace(plate, offset_x_mm=offset_x_mm)

    raise ValueError(f"geometry.plate mount_plane unsupported for auto offset: {plate.mount_plane!r}")


def _resolve_auto_plate_group(
    plate: PlateGroupConfig,
    *,
    core: ChamberCoreConfig,
    clearance: ClearanceConfig,
) -> PlateGroupConfig:
    return PlateGroupConfig(
        h=_resolve_auto_plate_offset(plate.h, core=core, clearance=clearance),
        v1=_resolve_auto_plate_offset(plate.v1, core=core, clearance=clearance),
        v2=_resolve_auto_plate_offset(plate.v2, core=core, clearance=clearance),
    )


def _parse_geometry(raw: dict[str, Any]) -> GeometryConfig:
    beamline = _parse_beamline(_to_mapping(raw.get("beamline"), "geometry.beamline"))
    chamber = _parse_chamber(_to_mapping(raw.get("chamber"), "geometry.chamber"))
    ports = _parse_ports(_to_mapping(raw.get("ports"), "geometry.ports"))

    plate_raw = _to_mapping(raw.get("plate"), "geometry.plate")
    plate = PlateGroupConfig(
        h=_parse_plate(_to_mapping(plate_raw.get("h"), "geometry.plate.h"), "geometry.plate.h"),
        v1=_parse_plate(_to_mapping(plate_raw.get("v1"), "geometry.plate.v1"), "geometry.plate.v1"),
        v2=_parse_plate(_to_mapping(plate_raw.get("v2"), "geometry.plate.v2"), "geometry.plate.v2"),
    )

    detector = _parse_detector(_to_mapping(raw.get("detector"), "geometry.detector"))
    target = _parse_target(_to_mapping(raw.get("target"), "geometry.target"))
    stand = _parse_stand(_to_mapping(raw.get("stand"), "geometry.stand"))
    clearance = _parse_clearance(_to_mapping(raw.get("clearance"), "geometry.clearance"))
    plate = _resolve_auto_plate_group(plate, core=chamber.core, clearance=clearance)

    cfg = GeometryConfig(
        beamline=beamline,
        chamber=chamber,
        ports=ports,
        plate=plate,
        detector=detector,
        target=target,
        stand=stand,
        clearance=clearance,
    )

    _validate_geometry(cfg)
    return cfg


def _validate_geometry(cfg: GeometryConfig) -> None:
    core = cfg.chamber.core
    half_x = 0.5 * core.size_x_mm
    half_y = 0.5 * core.size_y_mm
    half_z = 0.5 * core.size_z_mm
    z_min = core.center_z_mm - half_z
    z_max = core.center_z_mm + half_z
    skip_overlap = cfg.clearance.skip_overlap_checks
    # [EN] Validate frozen HVV pose semantics and outside-chamber placement numerically before any CAD is built, so configuration errors fail fast without relying on expensive booleans. / [CN] 在生成 CAD 之前先用数值方式验证冻结的 HVV 姿态语义和板件外置条件，让配置错误尽早失败，而不是依赖代价更高的布尔运算。
    for name, plate in (("h", cfg.plate.h), ("v1", cfg.plate.v1), ("v2", cfg.plate.v2)):
        if name == "h":
            if plate.orientation != "horizontal" or plate.mount_plane != "xz":
                raise ValueError("geometry.plate.h must be horizontal on xz plane")
        else:
            if plate.orientation != "vertical" or plate.mount_plane != "yz":
                raise ValueError(f"geometry.plate.{name} must be vertical on yz plane")

        if not skip_overlap:
            if plate.mount_plane == "xy":
                if z_min <= plate.z_mm <= z_max:
                    raise ValueError(f"geometry.plate.{name}.z_mm must place full plate outside chamber volume")
                sign = 1.0 if plate.z_mm >= core.center_z_mm else -1.0
                face_z = z_max if sign > 0.0 else z_min
                min_center_distance = 0.5 * plate.thickness_mm + cfg.clearance.plate_auto_gap_mm
                if sign > 0.0 and plate.z_mm < face_z + min_center_distance:
                    raise ValueError(f"geometry.plate.{name}.z_mm must place full plate outside chamber volume")
                if sign < 0.0 and plate.z_mm > face_z - min_center_distance:
                    raise ValueError(f"geometry.plate.{name}.z_mm must place full plate outside chamber volume")
            elif plate.mount_plane == "xz":
                min_center_distance = half_y + 0.5 * plate.thickness_mm + cfg.clearance.plate_auto_gap_mm
                if abs(plate.offset_y_mm) < min_center_distance:
                    raise ValueError(f"geometry.plate.{name}.offset_y_mm must place full plate outside chamber volume")
            elif plate.mount_plane == "yz":
                min_center_distance = half_x + 0.5 * plate.thickness_mm + cfg.clearance.plate_auto_gap_mm
                if abs(plate.offset_x_mm) < min_center_distance:
                    raise ValueError(f"geometry.plate.{name}.offset_x_mm must place full plate outside chamber volume")
            else:
                raise ValueError(f"geometry.plate.{name}.mount_plane unsupported: {plate.mount_plane!r}")

        if abs(plate.offset_x_mm) < 1e-9 and abs(plate.offset_y_mm) < 1e-9:
            raise ValueError(f"geometry.plate.{name} must be offset from beam axis after offset resolution")

        if plate.stiffener_length_mm > plate.height_mm:
            raise ValueError(f"geometry.plate.{name}.stiffener_length_mm must be <= plate.height_mm")
        if plate.lug_width_mm > plate.height_mm:
            raise ValueError(f"geometry.plate.{name}.lug_width_mm must be <= plate.height_mm")
        if plate.bolt_hole_diameter_mm >= plate.lug_thickness_mm:
            raise ValueError(f"geometry.plate.{name}.bolt_hole_diameter_mm must be < lug_thickness_mm")
        if plate.lug_thickness_mm < plate.thickness_mm:
            raise ValueError(f"geometry.plate.{name}.lug_thickness_mm must be >= plate.thickness_mm")

    for name, port in (
        ("main_pump", cfg.ports.main_pump),
        ("gauge_safety", cfg.ports.gauge_safety),
        ("rotary_feedthrough", cfg.ports.rotary_feedthrough),
        ("spare", cfg.ports.spare),
    ):
        if not port.enabled:
            continue
        # [EN] Port centers are constrained to stay fully inside their wall footprint so the chamber shell retains a realizable sealing annulus around every nozzle. / [CN] 端口中心必须完全落在所属壁面可用范围内，确保每个接管周围都保留可制造、可密封的壳体环带。
        if not (z_min < port.center_z_mm < z_max):
            raise ValueError(f"geometry.ports.{name}.center_z_mm must lie on chamber side wall span")
        port_radius = 0.5 * port.outer_diameter_mm
        if port.side in {"right", "left"}:
            if abs(port.center_x_mm) > 1e-9:
                raise ValueError(f"geometry.ports.{name}.center_x_mm must be 0 for {port.side} wall ports")
            if abs(port.center_y_mm) + port_radius >= half_y:
                raise ValueError(f"geometry.ports.{name}.center_y_mm places the port footprint outside chamber wall span")
        else:
            if abs(port.center_y_mm) > 1e-9:
                raise ValueError(f"geometry.ports.{name}.center_y_mm must be 0 for {port.side} wall ports")
            if abs(port.center_x_mm) + port_radius >= half_x:
                raise ValueError(f"geometry.ports.{name}.center_x_mm places the port footprint outside chamber wall span")
        if port.center_z_mm - port_radius <= z_min or port.center_z_mm + port_radius >= z_max:
            raise ValueError(f"geometry.ports.{name}.center_z_mm places the port footprint outside chamber wall span")

    enabled_port_names = {
        name
        for name, port in (
            ("main_pump", cfg.ports.main_pump),
            ("gauge_safety", cfg.ports.gauge_safety),
            ("rotary_feedthrough", cfg.ports.rotary_feedthrough),
            ("spare", cfg.ports.spare),
        )
        if port.enabled
    }
    missing_required_ports = [name for name in cfg.chamber.contract.required_ports_enabled if name not in enabled_port_names]
    if missing_required_ports:
        raise ValueError(
            "geometry.chamber.contract.required_ports_enabled are not enabled in geometry.ports: "
            + ", ".join(missing_required_ports)
        )
    forbidden_enabled_ports = [name for name in cfg.chamber.contract.forbidden_ports_enabled if name in enabled_port_names]
    if forbidden_enabled_ports:
        raise ValueError(
            "geometry.chamber.contract.forbidden_ports_enabled must stay disabled in geometry.ports: "
            + ", ".join(forbidden_enabled_ports)
        )
    if cfg.chamber.contract.rotary_mount_standard is not None:
        rotary_port = cfg.ports.rotary_feedthrough
        if not rotary_port.enabled:
            raise ValueError("geometry.chamber.contract.rotary_mount_standard requires geometry.ports.rotary_feedthrough.enabled=true")
        if rotary_port.interface is None:
            raise ValueError("geometry.chamber.contract.rotary_mount_standard requires geometry.ports.rotary_feedthrough.interface")
        if rotary_port.interface.standard.upper() != cfg.chamber.contract.rotary_mount_standard.upper():
            raise ValueError(
                "geometry.ports.rotary_feedthrough.interface.standard must match "
                "geometry.chamber.contract.rotary_mount_standard"
            )

    clamp = cfg.detector.clamp
    if clamp.anti_rotation_key_width_mm >= clamp.inner_diameter_mm:
        raise ValueError("geometry.detector.clamp.anti_rotation_key_width_mm must be < inner_diameter_mm")
    if clamp.clamp_ear_width_mm <= clamp.clamp_bolt_diameter_mm:
        raise ValueError("geometry.detector.clamp.clamp_ear_width_mm must be > clamp_bolt_diameter_mm")

    for side_name, module in (("front", cfg.chamber.end_modules.front), ("rear", cfg.chamber.end_modules.rear)):
        if module.pipe_length_mm > 0.0 and module.pipe_inner_diameter_mm < cfg.beamline.inlet_diameter_mm:
            raise ValueError(
                f"geometry.chamber.end_modules.{side_name}.pipe_inner_diameter_mm must be >= geometry.beamline.inlet_diameter_mm"
            )
        if _end_module_has_groove(module):
            flange_annulus = module.module_outer_diameter_mm - module.module_inner_diameter_mm
            groove_span = module.oring_groove_outer_diameter_mm - module.oring_groove_inner_diameter_mm
            if groove_span >= flange_annulus:
                raise ValueError(
                    f"geometry.chamber.end_modules.{side_name}.oring_groove_outer_diameter_mm - "
                    f"geometry.chamber.end_modules.{side_name}.oring_groove_inner_diameter_mm is too large for flange annulus"
                )
        if module.interface_nut_outer_diameter_mm > module.bolt_circle_diameter_mm:
            raise ValueError(
                f"geometry.chamber.end_modules.{side_name}.interface_nut_outer_diameter_mm must be <= bolt_circle_diameter_mm"
            )

    stand = cfg.stand
    support_foot_radius_mm = 0.5 * stand.support_foot_diameter_mm
    if (stand.chamber_support_pair_half_span_x_mm + support_foot_radius_mm) > (0.5 * core.size_x_mm):
        raise ValueError(
            "geometry.stand.chamber_support_pair_half_span_x_mm must keep chamber support feet inside chamber x footprint"
        )
    chamber_half_z = 0.5 * core.size_z_mm
    if stand.chamber_support_end_margin_mm < support_foot_radius_mm:
        raise ValueError(
            "geometry.stand.chamber_support_end_margin_mm must keep chamber support feet inside chamber z footprint"
        )
    if stand.chamber_support_end_margin_mm > (chamber_half_z - support_foot_radius_mm):
        raise ValueError(
            "geometry.stand.chamber_support_end_margin_mm leaves no distinct front/rear chamber support rows"
        )
    if (stand.h_plate_support_pair_half_span_x_mm + support_foot_radius_mm) > (0.5 * cfg.plate.h.width_mm):
        raise ValueError(
            "geometry.stand.h_plate_support_pair_half_span_x_mm must keep H-plate support feet inside plate.h width footprint"
        )
    h_plate_half_height = 0.5 * cfg.plate.h.height_mm
    if stand.h_plate_support_end_margin_mm < support_foot_radius_mm:
        raise ValueError(
            "geometry.stand.h_plate_support_end_margin_mm must keep H-plate support feet inside plate.h height footprint"
        )
    if stand.h_plate_support_end_margin_mm > (h_plate_half_height - support_foot_radius_mm):
        raise ValueError(
            "geometry.stand.h_plate_support_end_margin_mm leaves no distinct front/rear H-plate support rows"
        )
    if stand.with_base_plate:
        chamber_support_front_z = core.center_z_mm - chamber_half_z + stand.chamber_support_end_margin_mm
        chamber_support_rear_z = core.center_z_mm + chamber_half_z - stand.chamber_support_end_margin_mm
        h_support_front_z = cfg.plate.h.z_mm - (h_plate_half_height - stand.h_plate_support_end_margin_mm)
        h_support_rear_z = cfg.plate.h.z_mm + (h_plate_half_height - stand.h_plate_support_end_margin_mm)
        max_support_z = max(
            abs(chamber_support_front_z),
            abs(chamber_support_rear_z),
            abs(h_support_front_z),
            abs(h_support_rear_z),
        )
        max_support_x = max(
            stand.chamber_support_pair_half_span_x_mm,
            abs(cfg.plate.h.offset_x_mm) + stand.h_plate_support_pair_half_span_x_mm,
        )
        if (max_support_x + support_foot_radius_mm) > (0.5 * stand.base_length_mm):
            raise ValueError(
                "geometry.stand.base_length_mm must span the centered chamber/H support rows when base plate is enabled"
            )
        if (max_support_z + support_foot_radius_mm) > (0.5 * stand.base_width_mm):
            raise ValueError(
                "geometry.stand.base_width_mm must span the centered chamber/H support rows when base plate is enabled"
            )
    if stand.enable_plate_ties:
        if stand.plate_tie_cap_width_mm >= min(stand.base_length_mm, stand.base_width_mm):
            raise ValueError("geometry.stand.plate_tie_cap_width_mm must be smaller than stand base span")
        if stand.plate_tie_cap_height_mm >= min(core.size_x_mm, core.size_z_mm):
            raise ValueError("geometry.stand.plate_tie_cap_height_mm must be smaller than chamber transverse span")

    vv_clear_gap = abs(cfg.plate.v2.offset_x_mm - cfg.plate.v1.offset_x_mm) - 0.5 * (
        cfg.plate.v1.thickness_mm + cfg.plate.v2.thickness_mm
    )
    vv_required_gap = cfg.clearance.vv_min_gap_factor * cfg.detector.clamp.outer_diameter_mm
    if vv_clear_gap < vv_required_gap:
        raise ValueError(
            "geometry.plate.v1/v2 clear gap must satisfy "
            f"gap >= vv_min_gap_factor*detector.clamp.outer_diameter_mm "
            f"(gap={vv_clear_gap:.3f}, required={vv_required_gap:.3f})"
        )

    if cfg.clearance.los_scope == "v2_fullpath" and not cfg.chamber.los_channels.enabled:
        raise ValueError("geometry.chamber.los_channels.enabled must be true when geometry.clearance.los_scope=v2_fullpath")

    if cfg.target.mode == "single_rotary":
        rotary = cfg.target.rotary
        holder = cfg.target.single_holder
        if rotary is None or holder is None:
            raise ValueError("geometry.target.single_rotary mode requires rotary and single_holder sections")
        if rotary.pivot_x_mm >= half_x:
            raise ValueError("geometry.target.rotary.pivot_x_mm must lie inside the chamber transverse span")
        # [EN] Arm length is forced to equal pivot offset so the work pose lands the single target exactly on the beam axis by pure rotation, without hidden translational compensation. / [CN] 强制臂长等于转轴偏置量，使单靶工作位仅靠纯旋转就能精确落到束轴上，而不依赖隐藏的平移补偿。
        if rotary.arm_length_mm != rotary.pivot_x_mm:
            raise ValueError("geometry.target.rotary.arm_length_mm must equal pivot_x_mm so the work pose centers the target on beam")


def _parse_layout(raw: dict[str, Any]) -> LayoutConfig:
    sectors_raw = _to_list(raw.get("sectors"), "layout.sectors")
    channels_raw = _to_list(raw.get("channels"), "layout.channels")

    # [EN] The layout contract is intentionally closed to the frozen 4 sectors, because many chamber/plate validators assume exactly one exit side per sector family. / [CN] 布局契约刻意限制为冻结的 4 个扇区，因为许多腔体/板件校验都默认每个扇区族只对应一个首出腔侧面。
    sectors = tuple(_to_str(item, "layout.sectors[]").lower() for item in sectors_raw)
    if set(sectors) != _ALLOWED_SECTORS or len(sectors) != 4:
        raise ValueError("layout.sectors must contain exactly [left, right, up, down]")

    channels: list[DetectorChannel] = []
    for idx, entry in enumerate(channels_raw):
        row = _to_mapping(entry, f"layout.channels[{idx}]")
        confidence = _to_str(row.get("confidence"), f"layout.channels[{idx}].confidence").lower()
        if confidence not in _ALLOWED_CONFIDENCE:
            raise ValueError(
                f"layout.channels[{idx}].confidence must be one of {sorted(_ALLOWED_CONFIDENCE)}, got {confidence!r}"
            )

        channels.append(
            DetectorChannel(
                name=_to_str(row.get("name"), f"layout.channels[{idx}].name"),
                angle_deg=_to_float(row.get("angle_deg"), f"layout.channels[{idx}].angle_deg"),
                radius_mm=_to_float(row.get("radius_mm"), f"layout.channels[{idx}].radius_mm"),
                confidence=confidence,
            )
        )

    # [EN] BLP v1 keeps exactly three scattering-radius families, which expand with the four sectors into the canonical 12 detector stations. / [CN] BLP v1 固定为 3 组散射半径通道，再与 4 个扇区展开成标准的 12 个探测器工位。
    if len(channels) != 3:
        raise ValueError("layout.channels must contain exactly 3 channels for BLP v1")

    seen: set[str] = set()
    for channel in channels:
        if channel.name in seen:
            raise ValueError(f"Duplicate channel name: {channel.name}")
        seen.add(channel.name)

        if not (0.0 < channel.angle_deg < 89.0):
            raise ValueError(f"Channel angle must be in (0, 89), got {channel.angle_deg} for {channel.name}")
        if channel.radius_mm <= 0.0:
            raise ValueError(f"Channel radius must be > 0, got {channel.radius_mm} for {channel.name}")

    return LayoutConfig(sectors=sectors, channels=tuple(channels))


def _parse_output(raw: dict[str, Any], config_path: Path) -> OutputConfig:
    output_dir_raw = _to_str(raw.get("dir"), "output.dir")
    output_dir = Path(output_dir_raw)
    if not output_dir.is_absolute():
        output_dir = (config_path.parent / output_dir).resolve()

    basename = _to_str(raw.get("basename"), "output.basename")

    formats_raw = _to_list(raw.get("formats"), "output.formats")
    formats = tuple(_to_str(item, "output.formats[]").lower() for item in formats_raw)
    if not formats:
        raise ValueError("output.formats cannot be empty")

    for fmt in formats:
        if fmt not in _ALLOWED_OUTPUT_FORMATS:
            raise ValueError(f"Unsupported output format {fmt!r}, allowed: {sorted(_ALLOWED_OUTPUT_FORMATS)}")

    return OutputConfig(output_dir=output_dir, basename=basename, formats=formats)


def load_build_config(config_path: str | Path, overrides: list[str] | None = None) -> BuildConfig:
    path = Path(config_path).expanduser().resolve()
    raw = _load_yaml_file(path)
    raw = _apply_overrides(raw, overrides or [])

    geometry = _parse_geometry(_to_mapping(raw.get("geometry"), "geometry"))
    layout = _parse_layout(_to_mapping(raw.get("layout"), "layout"))
    output = _parse_output(_to_mapping(raw.get("output"), "output"), path)
    return BuildConfig(geometry=geometry, layout=layout, output=output)


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        data: dict[str, Any] = {}
        for key in obj.__dataclass_fields__.keys():
            data[key] = _dataclass_to_dict(getattr(obj, key))
        return data
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, Path):
        return str(obj)
    return obj


def build_config_snapshot(cfg: BuildConfig) -> dict[str, Any]:
    # [EN] Keep config snapshot schema-identical to runtime parsing so requirement drift is diff-detectable. / [CN] 参数快照与运行期解析结构保持同构，便于对需求漂移做差异审查。
    return {
        "geometry": _dataclass_to_dict(cfg.geometry),
        "layout": {
            "sectors": list(cfg.layout.sectors),
            "channels": [_dataclass_to_dict(channel) for channel in cfg.layout.channels],
        },
        "output": {
            "dir": str(cfg.output.output_dir),
            "basename": cfg.output.basename,
            "formats": list(cfg.output.formats),
        },
    }


def dump_snapshot_yaml(cfg: BuildConfig) -> str:
    _assert_yaml_available()
    return yaml.safe_dump(build_config_snapshot(cfg), sort_keys=False)
