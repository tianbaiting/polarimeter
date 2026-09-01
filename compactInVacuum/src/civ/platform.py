from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


DECISION_STATES = {
    "frozen",
    "provisional",
    "recommended",
    "placeholder",
    "purchased-part-contract",
}


@dataclass(frozen=True)
class ActiveDetectorSpec:
    material: str
    material_status: str
    diameter_mm: float
    diameter_status: str
    thickness_mm: float
    thickness_status: str
    thickness_candidates_mm: tuple[float, ...]


@dataclass(frozen=True)
class OpticalPackageSpec:
    coupling: str
    coupling_status: str
    coupling_thickness_mm: float
    reflector: str
    reflector_status: str
    reflector_envelope_thickness_mm: float
    collection_efficiency_target: tuple[float, float]
    collection_efficiency_status: str


@dataclass(frozen=True)
class SiPMSpec:
    model: str
    status: str
    active_size_mm: tuple[float, float]
    microcell_pitch_um: float
    microcell_count: int
    package_envelope_mm: tuple[float, float, float]
    alternatives: tuple[str, ...]


@dataclass(frozen=True)
class DetectorHeadSpec:
    status: str
    carrier_envelope_mm: tuple[float, float, float]
    carrier_material: str
    carrier_status: str
    housing_radial_clearance_mm: float
    shell_wall_mm: float
    shell_material: str
    rear_clearance_mm: float
    rear_cap_wall_mm: float
    mounting_flange_diameter_mm: float
    anti_rotation_feature: str
    anti_rotation_flat_depth_mm: float
    mounting_datum: str
    detector_removal_direction: str
    detector_removal_clearance_mm: float
    cable_exit: str
    cable_exit_diameter_mm: float
    cable_exit_length_mm: float
    cable_exit_status: str
    connector_keepout_diameter_mm: float
    connector_keepout_length_mm: float
    maximum_physical_depth_mm: float


@dataclass(frozen=True)
class DetectorPlatformSpec:
    status: str
    radius_reference: str
    active: ActiveDetectorSpec
    optics: OpticalPackageSpec
    sipm: SiPMSpec
    head: DetectorHeadSpec

    @property
    def physical_depth_mm(self) -> float:
        # [EN] The housing depth is the explicit axial stack; cable and connector volumes are service geometry and cannot inflate this mechanical metric. / [CN] 壳体深度由明确的轴向堆栈计算；电缆和连接器体积属于服务几何，不能抬高该机械指标。
        return (
            self.active.thickness_mm
            + self.optics.coupling_thickness_mm
            + self.sipm.package_envelope_mm[2]
            + self.head.carrier_envelope_mm[2]
            + self.head.rear_clearance_mm
            + self.head.rear_cap_wall_mm
        )

    @property
    def front_face_offset_mm(self) -> float:
        return -0.5 * self.active.thickness_mm

    @property
    def rear_housing_offset_mm(self) -> float:
        return self.front_face_offset_mm + self.physical_depth_mm

    @property
    def housing_outer_diameter_mm(self) -> float:
        return (
            self.active.diameter_mm
            + 2.0 * self.optics.reflector_envelope_thickness_mm
            + 2.0 * self.head.housing_radial_clearance_mm
            + 2.0 * self.head.shell_wall_mm
        )


@dataclass(frozen=True)
class SectorHolderSpec:
    status: str
    architecture: str
    detector_mounts: tuple[str, ...]
    mounting_datum: str
    survey_datums: tuple[str, ...]
    chamber_interface: str
    detector_removal_direction: str
    sector_removal_direction: str
    sector_removal_clearance_mm: float
    carrier_plate_thickness_mm: float
    carrier_web_width_mm: float
    carrier_node_radius_mm: float
    common_bracket_width_mm: float
    nest_axial_depth_mm: float
    nest_radial_wall_mm: float
    nest_clearance_mm: float
    clamp_bridge_thickness_mm: float
    clamp_fastener_class: str
    clamp_fastener_clearance_diameter_mm: float
    fastener_status: str
    interface_block_mm: tuple[float, float, float]
    locating_pin_diameter_mm: float
    locating_slot_width_mm: float
    locating_slot_length_mm: float
    service_lane_offset_mm: float
    acceptance_clearance_mm: float
    tool_clearance_mm: float


@dataclass(frozen=True)
class TargetFoilSpec:
    material: str
    material_status: str
    diameter_mm: float
    thickness_mm: float
    thickness_status: str


@dataclass(frozen=True)
class TargetHolderSpec:
    status: str
    architecture: str
    outer_width_mm: float
    outer_height_mm: float
    frame_width_mm: float
    thickness_mm: float
    removable: bool
    target_center_datum: str


@dataclass(frozen=True)
class TargetRotarySpec:
    status: str
    mount_standard: str
    pivot_mm: tuple[float, float, float]
    axis: tuple[float, float, float]
    shaft_diameter_mm: float
    arm_length_mm: float
    arm_width_mm: float
    arm_thickness_mm: float
    hub_diameter_mm: float
    hub_thickness_mm: float
    work_angle_deg: float
    park_angle_deg: float
    hard_stop_angles_deg: tuple[float, float]
    motion_sample_step_deg: float


@dataclass(frozen=True)
class TargetSystemSpec:
    status: str
    mode: str
    foil: TargetFoilSpec
    holder: TargetHolderSpec
    rotary: TargetRotarySpec


@dataclass(frozen=True)
class FeedthroughInterfaceSpec:
    standard: str
    status: str
    supplier: str
    part_number: str
    certified_drawing_reference: str
    dimensions_status: str
    module_outer_diameter_mm: float
    module_inner_diameter_mm: float
    module_thickness_mm: float
    seal_face_width_mm: float
    bolt_circle_diameter_mm: float
    bolt_count: int
    bolt_hole_diameter_mm: float
    nominal_clear_bore_mm: float
    knife_edge_protected_zone_mm: float


@dataclass(frozen=True)
class ServiceRoutingSpec:
    status: str
    cable_keepout_diameter_mm: float
    minimum_static_bend_radius_mm: float
    wall_clearance_mm: float
    strain_relief_length_mm: float
    strain_relief_width_mm: float
    strain_relief_thickness_mm: float
    connector_keepout_diameter_mm: float
    connector_keepout_length_mm: float


@dataclass(frozen=True)
class GroundingSpec:
    status: str
    reference: str
    protective_bond_required: bool
    coax_shield_bond_at_feedthrough: bool
    signal_shield_is_only_protective_earth: bool


@dataclass(frozen=True)
class ServicesSpec:
    status: str
    fast_signal_channels: int
    coax_impedance_ohm: float
    bias_architecture: str
    active_electronics_in_vacuum: bool
    signal_feedthrough_count: int
    channels_per_signal_feedthrough: int
    signal_interface: FeedthroughInterfaceSpec
    routing: ServiceRoutingSpec
    grounding: GroundingSpec


@dataclass(frozen=True)
class ThermalSpec:
    status: str
    path: tuple[str, ...]
    required_connections: tuple[str, ...]
    spreader_material: str
    chamber_sink_interface: str
    floating_allowed: bool


@dataclass(frozen=True)
class MaterialSpec:
    name: str
    density_g_per_cm3: float | None
    vacuum_compatibility_status: str
    physics_sensitive: bool


@dataclass(frozen=True)
class PurchasedBeamInterfaceSpec:
    side: str
    standard: str
    status: str
    supplier: str
    part_number: str
    certified_drawing_reference: str
    dimensions_status: str
    nominal_clear_bore_mm: float
    module_outer_diameter_mm: float
    module_inner_diameter_mm: float
    module_thickness_mm: float
    seal_face_width_mm: float
    bolt_circle_diameter_mm: float
    bolt_count: int
    bolt_hole_diameter_mm: float
    oring_groove_inner_diameter_mm: float
    oring_groove_outer_diameter_mm: float
    oring_groove_depth_mm: float
    knife_edge_protected_zone_mm: float
    weld_interface: str
    transition_outer_diameter_mm: float
    transition_inner_diameter_mm: float
    transition_length_mm: float
    transition_status: str


@dataclass(frozen=True)
class ChamberCandidateSpec:
    name: str
    cross_section: str
    status: str
    inner_size_x_mm: float
    inner_size_y_mm: float
    length_mm: float
    center_z_mm: float
    wall_thickness_mm: float
    wall_thickness_status: str
    material: str
    service_accessibility: str
    service_plate_concept: str


@dataclass(frozen=True)
class MaintenanceAccessFlangeSpec:
    standard: str
    status: str
    disposition: str
    chamber_candidate: str
    center_x_mm: float
    center_z_mm: float
    flange_outer_diameter_mm: float
    clear_bore_diameter_mm: float
    counterbore_diameter_mm: float
    counterbore_depth_mm: float
    pipe_outer_diameter_mm: float
    flange_thickness_mm: float
    bolt_circle_diameter_mm: float
    bolt_count: int
    bolt_hole_diameter_mm: float
    gasket_outer_diameter_mm: float
    gasket_inner_diameter_mm: float
    gasket_thickness_mm: float
    weld_neck_length_mm: float


@dataclass(frozen=True)
class MaintenanceAccessSpec:
    enabled: bool
    status: str
    wall: str
    selected_candidate: str
    supplier: str
    fixed_flange_part_number: str
    blank_flange_part_number: str
    certified_drawing_reference: str
    dimensions_status: str
    seal_type: str
    seal_material: str
    elastomer_seal_allowed: bool
    helium_leak_rate_max_pa_m3_s: float
    flange_edge_margin_mm: float
    service_port_clearance_mm: float
    passage_diametral_clearance_mm: float
    complete_extraction_status: str
    candidates: tuple[MaintenanceAccessFlangeSpec, ...]

    @property
    def selected(self) -> MaintenanceAccessFlangeSpec:
        matches = [
            candidate
            for candidate in self.candidates
            if candidate.standard == self.selected_candidate
        ]
        if len(matches) != 1:
            raise ValueError(
                "deployment.maintenance_access.selected_candidate must identify "
                "exactly one flange candidate"
            )
        return matches[0]


@dataclass(frozen=True)
class SectorMountSpec:
    sector: str
    wall: str
    tangent_coordinate_mm: float
    wall_standoff_mm: float
    release_clearance_mm: float


@dataclass(frozen=True)
class ServicePortPlacementSpec:
    name: str
    role: str
    sector: str | None
    center_x_mm: float
    center_z_mm: float
    bore_diameter_mm: float
    collar_outer_diameter_mm: float
    collar_length_mm: float


@dataclass(frozen=True)
class DeploymentSpec:
    name: str
    instrument_name: str
    location: str
    status: str
    external_route_module: str
    selected_chamber_candidate: str
    chamber_candidates: tuple[ChamberCandidateSpec, ...]
    beam_stay_clear_diameter_mm: float
    beam_stay_clear_status: str
    available_envelope_mm: tuple[float, float, float] | None
    available_envelope_status: str
    front_interface: PurchasedBeamInterfaceSpec
    rear_interface: PurchasedBeamInterfaceSpec
    target_feedthrough_standard: str
    target_feedthrough_status: str
    pump_gauge_requirements: tuple[str, ...]
    support_alignment_status: str
    external_service_envelope_status: str
    maintenance_access: MaintenanceAccessSpec | None
    sector_mounts: tuple[SectorMountSpec, ...]
    service_ports: tuple[ServicePortPlacementSpec, ...]

    @property
    def chamber(self) -> ChamberCandidateSpec:
        matches = [
            candidate
            for candidate in self.chamber_candidates
            if candidate.name == self.selected_chamber_candidate
        ]
        if len(matches) != 1:
            raise ValueError(
                "deployment.selected_chamber_candidate must identify exactly one candidate"
            )
        return matches[0]

    def sector_mount(self, sector: str) -> SectorMountSpec:
        matches = [item for item in self.sector_mounts if item.sector == sector]
        if len(matches) == 1:
            return matches[0]
        if matches:
            raise ValueError(f"deployment.sector_mounts duplicates sector {sector!r}")
        default_wall = {
            "left": "negative_x",
            "right": "positive_x",
            "up": "positive_y",
            "down": "negative_y",
        }.get(sector)
        if default_wall is None:
            raise ValueError(f"unsupported sector mount: {sector!r}")
        return SectorMountSpec(
            sector=sector,
            wall=default_wall,
            tangent_coordinate_mm=0.0,
            wall_standoff_mm=16.0,
            release_clearance_mm=12.0,
        )


@dataclass(frozen=True)
class CompactOnePlatformConfig:
    schema_version: int
    architecture_mode: str
    detector: DetectorPlatformSpec
    sector_holder: SectorHolderSpec
    target: TargetSystemSpec
    services: ServicesSpec
    thermal: ThermalSpec
    materials: tuple[MaterialSpec, ...]
    deployment: DeploymentSpec


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def _items(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _number(value: Any, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    return result


def _integer(value: Any, name: str) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    return result


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    return value


def _state(value: Any, name: str) -> str:
    state = _text(value, name).lower()
    if state not in DECISION_STATES:
        raise ValueError(f"{name} must be one of {sorted(DECISION_STATES)}")
    return state


def _vector(
    value: Any,
    name: str,
    length: int,
) -> tuple[float, ...]:
    raw = _items(value, name)
    if len(raw) != length:
        raise ValueError(f"{name} must contain {length} values")
    return tuple(_number(item, f"{name}[{idx}]") for idx, item in enumerate(raw))


def _positive(value: float, name: str) -> float:
    if value <= 0.0:
        raise ValueError(f"{name} must be > 0")
    return value


def _parse_active(raw: Mapping[str, Any]) -> ActiveDetectorSpec:
    candidates = tuple(
        _positive(_number(item, f"detector.active.thickness_candidates_mm[{idx}]"), "candidate thickness")
        for idx, item in enumerate(
            _items(raw.get("thickness_candidates_mm"), "detector.active.thickness_candidates_mm")
        )
    )
    spec = ActiveDetectorSpec(
        material=_text(raw.get("material"), "detector.active.material"),
        material_status=_state(raw.get("material_status"), "detector.active.material_status"),
        diameter_mm=_positive(
            _number(raw.get("diameter_mm"), "detector.active.diameter_mm"),
            "detector.active.diameter_mm",
        ),
        diameter_status=_state(raw.get("diameter_status"), "detector.active.diameter_status"),
        thickness_mm=_positive(
            _number(raw.get("thickness_mm"), "detector.active.thickness_mm"),
            "detector.active.thickness_mm",
        ),
        thickness_status=_state(raw.get("thickness_status"), "detector.active.thickness_status"),
        thickness_candidates_mm=candidates,
    )
    if spec.thickness_mm not in spec.thickness_candidates_mm:
        raise ValueError("detector.active.thickness_mm must be one of the prototype candidates")
    return spec


def _parse_optics(raw: Mapping[str, Any]) -> OpticalPackageSpec:
    efficiency = _vector(
        raw.get("collection_efficiency_target"),
        "detector.optics.collection_efficiency_target",
        2,
    )
    if not (0.0 < efficiency[0] <= efficiency[1] <= 1.0):
        raise ValueError("detector.optics.collection_efficiency_target must lie in (0, 1]")
    return OpticalPackageSpec(
        coupling=_text(raw.get("coupling"), "detector.optics.coupling"),
        coupling_status=_state(raw.get("coupling_status"), "detector.optics.coupling_status"),
        coupling_thickness_mm=_positive(
            _number(raw.get("coupling_thickness_mm"), "detector.optics.coupling_thickness_mm"),
            "detector.optics.coupling_thickness_mm",
        ),
        reflector=_text(raw.get("reflector"), "detector.optics.reflector"),
        reflector_status=_state(raw.get("reflector_status"), "detector.optics.reflector_status"),
        reflector_envelope_thickness_mm=_positive(
            _number(
                raw.get("reflector_envelope_thickness_mm"),
                "detector.optics.reflector_envelope_thickness_mm",
            ),
            "detector.optics.reflector_envelope_thickness_mm",
        ),
        collection_efficiency_target=(efficiency[0], efficiency[1]),
        collection_efficiency_status=_state(
            raw.get("collection_efficiency_status"),
            "detector.optics.collection_efficiency_status",
        ),
    )


def _parse_sipm(raw: Mapping[str, Any]) -> SiPMSpec:
    active_size = _vector(raw.get("active_size_mm"), "detector.sipm.active_size_mm", 2)
    package = _vector(raw.get("package_envelope_mm"), "detector.sipm.package_envelope_mm", 3)
    return SiPMSpec(
        model=_text(raw.get("model"), "detector.sipm.model"),
        status=_state(raw.get("status"), "detector.sipm.status"),
        active_size_mm=(active_size[0], active_size[1]),
        microcell_pitch_um=_positive(
            _number(raw.get("microcell_pitch_um"), "detector.sipm.microcell_pitch_um"),
            "detector.sipm.microcell_pitch_um",
        ),
        microcell_count=_integer(raw.get("microcell_count"), "detector.sipm.microcell_count"),
        package_envelope_mm=(package[0], package[1], package[2]),
        alternatives=tuple(
            _text(item, f"detector.sipm.alternatives[{idx}]")
            for idx, item in enumerate(_items(raw.get("alternatives"), "detector.sipm.alternatives"))
        ),
    )


def _nonnegative(value: float, name: str) -> float:
    if value < 0.0:
        raise ValueError(f"{name} must be >= 0")
    return value


def _parse_detector_head(raw: Mapping[str, Any]) -> DetectorHeadSpec:
    carrier = _vector(
        raw.get("carrier_envelope_mm"),
        "detector.head.carrier_envelope_mm",
        3,
    )
    return DetectorHeadSpec(
        status=_state(raw.get("status"), "detector.head.status"),
        carrier_envelope_mm=(carrier[0], carrier[1], carrier[2]),
        carrier_material=_text(
            raw.get("carrier_material"),
            "detector.head.carrier_material",
        ),
        carrier_status=_state(
            raw.get("carrier_status"),
            "detector.head.carrier_status",
        ),
        housing_radial_clearance_mm=_nonnegative(
            _number(
                raw.get("housing_radial_clearance_mm"),
                "detector.head.housing_radial_clearance_mm",
            ),
            "detector.head.housing_radial_clearance_mm",
        ),
        shell_wall_mm=_positive(
            _number(raw.get("shell_wall_mm"), "detector.head.shell_wall_mm"),
            "detector.head.shell_wall_mm",
        ),
        shell_material=_text(
            raw.get("shell_material"),
            "detector.head.shell_material",
        ),
        rear_clearance_mm=_nonnegative(
            _number(raw.get("rear_clearance_mm"), "detector.head.rear_clearance_mm"),
            "detector.head.rear_clearance_mm",
        ),
        rear_cap_wall_mm=_positive(
            _number(raw.get("rear_cap_wall_mm"), "detector.head.rear_cap_wall_mm"),
            "detector.head.rear_cap_wall_mm",
        ),
        mounting_flange_diameter_mm=_positive(
            _number(
                raw.get("mounting_flange_diameter_mm"),
                "detector.head.mounting_flange_diameter_mm",
            ),
            "detector.head.mounting_flange_diameter_mm",
        ),
        anti_rotation_feature=_text(
            raw.get("anti_rotation_feature"),
            "detector.head.anti_rotation_feature",
        ),
        anti_rotation_flat_depth_mm=_positive(
            _number(
                raw.get("anti_rotation_flat_depth_mm"),
                "detector.head.anti_rotation_flat_depth_mm",
            ),
            "detector.head.anti_rotation_flat_depth_mm",
        ),
        mounting_datum=_text(
            raw.get("mounting_datum"),
            "detector.head.mounting_datum",
        ),
        detector_removal_direction=_text(
            raw.get("detector_removal_direction"),
            "detector.head.detector_removal_direction",
        ),
        detector_removal_clearance_mm=_positive(
            _number(
                raw.get("detector_removal_clearance_mm"),
                "detector.head.detector_removal_clearance_mm",
            ),
            "detector.head.detector_removal_clearance_mm",
        ),
        cable_exit=_text(raw.get("cable_exit"), "detector.head.cable_exit"),
        cable_exit_diameter_mm=_positive(
            _number(
                raw.get("cable_exit_diameter_mm"),
                "detector.head.cable_exit_diameter_mm",
            ),
            "detector.head.cable_exit_diameter_mm",
        ),
        cable_exit_length_mm=_positive(
            _number(
                raw.get("cable_exit_length_mm"),
                "detector.head.cable_exit_length_mm",
            ),
            "detector.head.cable_exit_length_mm",
        ),
        cable_exit_status=_state(
            raw.get("cable_exit_status"),
            "detector.head.cable_exit_status",
        ),
        connector_keepout_diameter_mm=_positive(
            _number(
                raw.get("connector_keepout_diameter_mm"),
                "detector.head.connector_keepout_diameter_mm",
            ),
            "detector.head.connector_keepout_diameter_mm",
        ),
        connector_keepout_length_mm=_positive(
            _number(
                raw.get("connector_keepout_length_mm"),
                "detector.head.connector_keepout_length_mm",
            ),
            "detector.head.connector_keepout_length_mm",
        ),
        maximum_physical_depth_mm=_positive(
            _number(
                raw.get("maximum_physical_depth_mm"),
                "detector.head.maximum_physical_depth_mm",
            ),
            "detector.head.maximum_physical_depth_mm",
        ),
    )


def _parse_detector(raw: Mapping[str, Any]) -> DetectorPlatformSpec:
    spec = DetectorPlatformSpec(
        status=_state(raw.get("status"), "detector.status"),
        radius_reference=_text(raw.get("radius_reference"), "detector.radius_reference"),
        active=_parse_active(_mapping(raw.get("active"), "detector.active")),
        optics=_parse_optics(_mapping(raw.get("optics"), "detector.optics")),
        sipm=_parse_sipm(_mapping(raw.get("sipm"), "detector.sipm")),
        head=_parse_detector_head(_mapping(raw.get("head"), "detector.head")),
    )
    if spec.physical_depth_mm > spec.head.maximum_physical_depth_mm:
        raise ValueError(
            "detector calculated physical depth exceeds detector.head.maximum_physical_depth_mm"
        )
    if spec.head.mounting_flange_diameter_mm <= spec.housing_outer_diameter_mm:
        raise ValueError(
            "detector.head.mounting_flange_diameter_mm must exceed the calculated housing diameter"
        )
    return spec


def _parse_sector_holder(raw: Mapping[str, Any]) -> SectorHolderSpec:
    interface_block = _vector(
        raw.get("interface_block_mm"),
        "sector_holder.interface_block_mm",
        3,
    )
    return SectorHolderSpec(
        status=_state(raw.get("status"), "sector_holder.status"),
        architecture=_text(raw.get("architecture"), "sector_holder.architecture"),
        detector_mounts=tuple(
            _text(item, f"sector_holder.detector_mounts[{idx}]")
            for idx, item in enumerate(
                _items(raw.get("detector_mounts"), "sector_holder.detector_mounts")
            )
        ),
        mounting_datum=_text(raw.get("mounting_datum"), "sector_holder.mounting_datum"),
        survey_datums=tuple(
            _text(item, f"sector_holder.survey_datums[{idx}]")
            for idx, item in enumerate(
                _items(raw.get("survey_datums"), "sector_holder.survey_datums")
            )
        ),
        chamber_interface=_text(
            raw.get("chamber_interface"),
            "sector_holder.chamber_interface",
        ),
        detector_removal_direction=_text(
            raw.get("detector_removal_direction"),
            "sector_holder.detector_removal_direction",
        ),
        sector_removal_direction=_text(
            raw.get("sector_removal_direction"),
            "sector_holder.sector_removal_direction",
        ),
        sector_removal_clearance_mm=_positive(
            _number(
                raw.get("sector_removal_clearance_mm"),
                "sector_holder.sector_removal_clearance_mm",
            ),
            "sector_holder.sector_removal_clearance_mm",
        ),
        carrier_plate_thickness_mm=_positive(
            _number(
                raw.get("carrier_plate_thickness_mm"),
                "sector_holder.carrier_plate_thickness_mm",
            ),
            "sector_holder.carrier_plate_thickness_mm",
        ),
        carrier_web_width_mm=_positive(
            _number(
                raw.get("carrier_web_width_mm"),
                "sector_holder.carrier_web_width_mm",
            ),
            "sector_holder.carrier_web_width_mm",
        ),
        carrier_node_radius_mm=_positive(
            _number(
                raw.get("carrier_node_radius_mm"),
                "sector_holder.carrier_node_radius_mm",
            ),
            "sector_holder.carrier_node_radius_mm",
        ),
        common_bracket_width_mm=_positive(
            _number(
                raw.get("common_bracket_width_mm"),
                "sector_holder.common_bracket_width_mm",
            ),
            "sector_holder.common_bracket_width_mm",
        ),
        nest_axial_depth_mm=_positive(
            _number(
                raw.get("nest_axial_depth_mm"),
                "sector_holder.nest_axial_depth_mm",
            ),
            "sector_holder.nest_axial_depth_mm",
        ),
        nest_radial_wall_mm=_positive(
            _number(
                raw.get("nest_radial_wall_mm"),
                "sector_holder.nest_radial_wall_mm",
            ),
            "sector_holder.nest_radial_wall_mm",
        ),
        nest_clearance_mm=_positive(
            _number(
                raw.get("nest_clearance_mm"),
                "sector_holder.nest_clearance_mm",
            ),
            "sector_holder.nest_clearance_mm",
        ),
        clamp_bridge_thickness_mm=_positive(
            _number(
                raw.get("clamp_bridge_thickness_mm"),
                "sector_holder.clamp_bridge_thickness_mm",
            ),
            "sector_holder.clamp_bridge_thickness_mm",
        ),
        clamp_fastener_class=_text(
            raw.get("clamp_fastener_class"),
            "sector_holder.clamp_fastener_class",
        ),
        clamp_fastener_clearance_diameter_mm=_positive(
            _number(
                raw.get("clamp_fastener_clearance_diameter_mm"),
                "sector_holder.clamp_fastener_clearance_diameter_mm",
            ),
            "sector_holder.clamp_fastener_clearance_diameter_mm",
        ),
        fastener_status=_state(
            raw.get("fastener_status"),
            "sector_holder.fastener_status",
        ),
        interface_block_mm=(
            interface_block[0],
            interface_block[1],
            interface_block[2],
        ),
        locating_pin_diameter_mm=_positive(
            _number(
                raw.get("locating_pin_diameter_mm"),
                "sector_holder.locating_pin_diameter_mm",
            ),
            "sector_holder.locating_pin_diameter_mm",
        ),
        locating_slot_width_mm=_positive(
            _number(
                raw.get("locating_slot_width_mm"),
                "sector_holder.locating_slot_width_mm",
            ),
            "sector_holder.locating_slot_width_mm",
        ),
        locating_slot_length_mm=_positive(
            _number(
                raw.get("locating_slot_length_mm"),
                "sector_holder.locating_slot_length_mm",
            ),
            "sector_holder.locating_slot_length_mm",
        ),
        service_lane_offset_mm=_number(
            raw.get("service_lane_offset_mm"),
            "sector_holder.service_lane_offset_mm",
        ),
        acceptance_clearance_mm=_positive(
            _number(
                raw.get("acceptance_clearance_mm"),
                "sector_holder.acceptance_clearance_mm",
            ),
            "sector_holder.acceptance_clearance_mm",
        ),
        tool_clearance_mm=_positive(
            _number(
                raw.get("tool_clearance_mm"),
                "sector_holder.tool_clearance_mm",
            ),
            "sector_holder.tool_clearance_mm",
        ),
    )


def _parse_target(raw: Mapping[str, Any]) -> TargetSystemSpec:
    foil_raw = _mapping(raw.get("foil"), "target.foil")
    holder_raw = _mapping(raw.get("holder"), "target.holder")
    rotary_raw = _mapping(raw.get("rotary"), "target.rotary")
    pivot = _vector(rotary_raw.get("pivot_mm"), "target.rotary.pivot_mm", 3)
    axis = _vector(rotary_raw.get("axis"), "target.rotary.axis", 3)
    stops = _vector(
        rotary_raw.get("hard_stop_angles_deg"),
        "target.rotary.hard_stop_angles_deg",
        2,
    )
    return TargetSystemSpec(
        status=_state(raw.get("status"), "target.status"),
        mode=_text(raw.get("mode"), "target.mode"),
        foil=TargetFoilSpec(
            material=_text(foil_raw.get("material"), "target.foil.material"),
            material_status=_state(foil_raw.get("material_status"), "target.foil.material_status"),
            diameter_mm=_positive(
                _number(foil_raw.get("diameter_mm"), "target.foil.diameter_mm"),
                "target.foil.diameter_mm",
            ),
            thickness_mm=_positive(
                _number(foil_raw.get("thickness_mm"), "target.foil.thickness_mm"),
                "target.foil.thickness_mm",
            ),
            thickness_status=_state(
                foil_raw.get("thickness_status"),
                "target.foil.thickness_status",
            ),
        ),
        holder=TargetHolderSpec(
            status=_state(holder_raw.get("status"), "target.holder.status"),
            architecture=_text(
                holder_raw.get("architecture"),
                "target.holder.architecture",
            ),
            outer_width_mm=_positive(
                _number(holder_raw.get("outer_width_mm"), "target.holder.outer_width_mm"),
                "target.holder.outer_width_mm",
            ),
            outer_height_mm=_positive(
                _number(holder_raw.get("outer_height_mm"), "target.holder.outer_height_mm"),
                "target.holder.outer_height_mm",
            ),
            frame_width_mm=_positive(
                _number(holder_raw.get("frame_width_mm"), "target.holder.frame_width_mm"),
                "target.holder.frame_width_mm",
            ),
            thickness_mm=_positive(
                _number(holder_raw.get("thickness_mm"), "target.holder.thickness_mm"),
                "target.holder.thickness_mm",
            ),
            removable=_boolean(holder_raw.get("removable"), "target.holder.removable"),
            target_center_datum=_text(
                holder_raw.get("target_center_datum"),
                "target.holder.target_center_datum",
            ),
        ),
        rotary=TargetRotarySpec(
            status=_state(rotary_raw.get("status"), "target.rotary.status"),
            mount_standard=_text(
                rotary_raw.get("mount_standard"),
                "target.rotary.mount_standard",
            ),
            pivot_mm=(pivot[0], pivot[1], pivot[2]),
            axis=(axis[0], axis[1], axis[2]),
            shaft_diameter_mm=_positive(
                _number(rotary_raw.get("shaft_diameter_mm"), "target.rotary.shaft_diameter_mm"),
                "target.rotary.shaft_diameter_mm",
            ),
            arm_length_mm=_positive(
                _number(rotary_raw.get("arm_length_mm"), "target.rotary.arm_length_mm"),
                "target.rotary.arm_length_mm",
            ),
            arm_width_mm=_positive(
                _number(rotary_raw.get("arm_width_mm"), "target.rotary.arm_width_mm"),
                "target.rotary.arm_width_mm",
            ),
            arm_thickness_mm=_positive(
                _number(rotary_raw.get("arm_thickness_mm"), "target.rotary.arm_thickness_mm"),
                "target.rotary.arm_thickness_mm",
            ),
            hub_diameter_mm=_positive(
                _number(rotary_raw.get("hub_diameter_mm"), "target.rotary.hub_diameter_mm"),
                "target.rotary.hub_diameter_mm",
            ),
            hub_thickness_mm=_positive(
                _number(rotary_raw.get("hub_thickness_mm"), "target.rotary.hub_thickness_mm"),
                "target.rotary.hub_thickness_mm",
            ),
            work_angle_deg=_number(
                rotary_raw.get("work_angle_deg"),
                "target.rotary.work_angle_deg",
            ),
            park_angle_deg=_number(
                rotary_raw.get("park_angle_deg"),
                "target.rotary.park_angle_deg",
            ),
            hard_stop_angles_deg=(stops[0], stops[1]),
            motion_sample_step_deg=_positive(
                _number(
                    rotary_raw.get("motion_sample_step_deg"),
                    "target.rotary.motion_sample_step_deg",
                ),
                "target.rotary.motion_sample_step_deg",
            ),
        ),
    )


def _parse_feedthrough(raw: Mapping[str, Any], prefix: str) -> FeedthroughInterfaceSpec:
    return FeedthroughInterfaceSpec(
        standard=_text(raw.get("standard"), f"{prefix}.standard"),
        status=_state(raw.get("status"), f"{prefix}.status"),
        supplier=_text(raw.get("supplier"), f"{prefix}.supplier"),
        part_number=_text(raw.get("part_number"), f"{prefix}.part_number"),
        certified_drawing_reference=_text(
            raw.get("certified_drawing_reference"),
            f"{prefix}.certified_drawing_reference",
        ),
        dimensions_status=_state(raw.get("dimensions_status"), f"{prefix}.dimensions_status"),
        module_outer_diameter_mm=_positive(
            _number(raw.get("module_outer_diameter_mm"), f"{prefix}.module_outer_diameter_mm"),
            f"{prefix}.module_outer_diameter_mm",
        ),
        module_inner_diameter_mm=_positive(
            _number(raw.get("module_inner_diameter_mm"), f"{prefix}.module_inner_diameter_mm"),
            f"{prefix}.module_inner_diameter_mm",
        ),
        module_thickness_mm=_positive(
            _number(raw.get("module_thickness_mm"), f"{prefix}.module_thickness_mm"),
            f"{prefix}.module_thickness_mm",
        ),
        seal_face_width_mm=_positive(
            _number(raw.get("seal_face_width_mm"), f"{prefix}.seal_face_width_mm"),
            f"{prefix}.seal_face_width_mm",
        ),
        bolt_circle_diameter_mm=_positive(
            _number(raw.get("bolt_circle_diameter_mm"), f"{prefix}.bolt_circle_diameter_mm"),
            f"{prefix}.bolt_circle_diameter_mm",
        ),
        bolt_count=_integer(raw.get("bolt_count"), f"{prefix}.bolt_count"),
        bolt_hole_diameter_mm=_positive(
            _number(raw.get("bolt_hole_diameter_mm"), f"{prefix}.bolt_hole_diameter_mm"),
            f"{prefix}.bolt_hole_diameter_mm",
        ),
        nominal_clear_bore_mm=_positive(
            _number(raw.get("nominal_clear_bore_mm"), f"{prefix}.nominal_clear_bore_mm"),
            f"{prefix}.nominal_clear_bore_mm",
        ),
        knife_edge_protected_zone_mm=_positive(
            _number(
                raw.get("knife_edge_protected_zone_mm"),
                f"{prefix}.knife_edge_protected_zone_mm",
            ),
            f"{prefix}.knife_edge_protected_zone_mm",
        ),
    )


def _parse_services(raw: Mapping[str, Any]) -> ServicesSpec:
    routing_raw = _mapping(raw.get("routing"), "services.routing")
    grounding_raw = _mapping(raw.get("grounding"), "services.grounding")
    return ServicesSpec(
        status=_state(raw.get("status"), "services.status"),
        fast_signal_channels=_integer(
            raw.get("fast_signal_channels"),
            "services.fast_signal_channels",
        ),
        coax_impedance_ohm=_positive(
            _number(raw.get("coax_impedance_ohm"), "services.coax_impedance_ohm"),
            "services.coax_impedance_ohm",
        ),
        bias_architecture=_text(raw.get("bias_architecture"), "services.bias_architecture"),
        active_electronics_in_vacuum=_boolean(
            raw.get("active_electronics_in_vacuum"),
            "services.active_electronics_in_vacuum",
        ),
        signal_feedthrough_count=_integer(
            raw.get("signal_feedthrough_count"),
            "services.signal_feedthrough_count",
        ),
        channels_per_signal_feedthrough=_integer(
            raw.get("channels_per_signal_feedthrough"),
            "services.channels_per_signal_feedthrough",
        ),
        signal_interface=_parse_feedthrough(
            _mapping(raw.get("signal_interface"), "services.signal_interface"),
            "services.signal_interface",
        ),
        routing=ServiceRoutingSpec(
            status=_state(routing_raw.get("status"), "services.routing.status"),
            cable_keepout_diameter_mm=_positive(
                _number(
                    routing_raw.get("cable_keepout_diameter_mm"),
                    "services.routing.cable_keepout_diameter_mm",
                ),
                "services.routing.cable_keepout_diameter_mm",
            ),
            minimum_static_bend_radius_mm=_positive(
                _number(
                    routing_raw.get("minimum_static_bend_radius_mm"),
                    "services.routing.minimum_static_bend_radius_mm",
                ),
                "services.routing.minimum_static_bend_radius_mm",
            ),
            wall_clearance_mm=_positive(
                _number(
                    routing_raw.get("wall_clearance_mm"),
                    "services.routing.wall_clearance_mm",
                ),
                "services.routing.wall_clearance_mm",
            ),
            strain_relief_length_mm=_positive(
                _number(
                    routing_raw.get("strain_relief_length_mm"),
                    "services.routing.strain_relief_length_mm",
                ),
                "services.routing.strain_relief_length_mm",
            ),
            strain_relief_width_mm=_positive(
                _number(
                    routing_raw.get("strain_relief_width_mm"),
                    "services.routing.strain_relief_width_mm",
                ),
                "services.routing.strain_relief_width_mm",
            ),
            strain_relief_thickness_mm=_positive(
                _number(
                    routing_raw.get("strain_relief_thickness_mm"),
                    "services.routing.strain_relief_thickness_mm",
                ),
                "services.routing.strain_relief_thickness_mm",
            ),
            connector_keepout_diameter_mm=_positive(
                _number(
                    routing_raw.get("connector_keepout_diameter_mm"),
                    "services.routing.connector_keepout_diameter_mm",
                ),
                "services.routing.connector_keepout_diameter_mm",
            ),
            connector_keepout_length_mm=_positive(
                _number(
                    routing_raw.get("connector_keepout_length_mm"),
                    "services.routing.connector_keepout_length_mm",
                ),
                "services.routing.connector_keepout_length_mm",
            ),
        ),
        grounding=GroundingSpec(
            status=_state(grounding_raw.get("status"), "services.grounding.status"),
            reference=_text(grounding_raw.get("reference"), "services.grounding.reference"),
            protective_bond_required=_boolean(
                grounding_raw.get("protective_bond_required"),
                "services.grounding.protective_bond_required",
            ),
            coax_shield_bond_at_feedthrough=_boolean(
                grounding_raw.get("coax_shield_bond_at_feedthrough"),
                "services.grounding.coax_shield_bond_at_feedthrough",
            ),
            signal_shield_is_only_protective_earth=_boolean(
                grounding_raw.get("signal_shield_is_only_protective_earth"),
                "services.grounding.signal_shield_is_only_protective_earth",
            ),
        ),
    )


def _parse_thermal(raw: Mapping[str, Any]) -> ThermalSpec:
    return ThermalSpec(
        status=_state(raw.get("status"), "thermal.status"),
        path=tuple(
            _text(item, f"thermal.path[{idx}]")
            for idx, item in enumerate(_items(raw.get("path"), "thermal.path"))
        ),
        required_connections=tuple(
            _text(item, f"thermal.required_connections[{idx}]")
            for idx, item in enumerate(
                _items(raw.get("required_connections"), "thermal.required_connections")
            )
        ),
        spreader_material=_text(raw.get("spreader_material"), "thermal.spreader_material"),
        chamber_sink_interface=_text(
            raw.get("chamber_sink_interface"),
            "thermal.chamber_sink_interface",
        ),
        floating_allowed=_boolean(raw.get("floating_allowed"), "thermal.floating_allowed"),
    )


def _parse_materials(raw: list[Any]) -> tuple[MaterialSpec, ...]:
    materials: list[MaterialSpec] = []
    names: set[str] = set()
    for idx, item in enumerate(raw):
        entry = _mapping(item, f"materials[{idx}]")
        name = _text(entry.get("name"), f"materials[{idx}].name")
        if name in names:
            raise ValueError(f"materials duplicates {name!r}")
        names.add(name)
        density_raw = entry.get("density_g_per_cm3")
        density = None if density_raw is None else _positive(
            _number(density_raw, f"materials[{idx}].density_g_per_cm3"),
            f"materials[{idx}].density_g_per_cm3",
        )
        materials.append(
            MaterialSpec(
                name=name,
                density_g_per_cm3=density,
                vacuum_compatibility_status=_state(
                    entry.get("vacuum_compatibility_status"),
                    f"materials[{idx}].vacuum_compatibility_status",
                ),
                physics_sensitive=_boolean(
                    entry.get("physics_sensitive"),
                    f"materials[{idx}].physics_sensitive",
                ),
            )
        )
    return tuple(materials)


def _parse_beam_interface(raw: Mapping[str, Any], prefix: str) -> PurchasedBeamInterfaceSpec:
    return PurchasedBeamInterfaceSpec(
        side=_text(raw.get("side"), f"{prefix}.side"),
        standard=_text(raw.get("standard"), f"{prefix}.standard"),
        status=_state(raw.get("status"), f"{prefix}.status"),
        supplier=_text(raw.get("supplier"), f"{prefix}.supplier"),
        part_number=_text(raw.get("part_number"), f"{prefix}.part_number"),
        certified_drawing_reference=_text(
            raw.get("certified_drawing_reference"),
            f"{prefix}.certified_drawing_reference",
        ),
        dimensions_status=_state(raw.get("dimensions_status"), f"{prefix}.dimensions_status"),
        nominal_clear_bore_mm=_positive(
            _number(raw.get("nominal_clear_bore_mm"), f"{prefix}.nominal_clear_bore_mm"),
            f"{prefix}.nominal_clear_bore_mm",
        ),
        module_outer_diameter_mm=_positive(
            _number(raw.get("module_outer_diameter_mm"), f"{prefix}.module_outer_diameter_mm"),
            f"{prefix}.module_outer_diameter_mm",
        ),
        module_inner_diameter_mm=_positive(
            _number(raw.get("module_inner_diameter_mm"), f"{prefix}.module_inner_diameter_mm"),
            f"{prefix}.module_inner_diameter_mm",
        ),
        module_thickness_mm=_positive(
            _number(raw.get("module_thickness_mm"), f"{prefix}.module_thickness_mm"),
            f"{prefix}.module_thickness_mm",
        ),
        seal_face_width_mm=_positive(
            _number(raw.get("seal_face_width_mm"), f"{prefix}.seal_face_width_mm"),
            f"{prefix}.seal_face_width_mm",
        ),
        bolt_circle_diameter_mm=_positive(
            _number(raw.get("bolt_circle_diameter_mm"), f"{prefix}.bolt_circle_diameter_mm"),
            f"{prefix}.bolt_circle_diameter_mm",
        ),
        bolt_count=_integer(raw.get("bolt_count"), f"{prefix}.bolt_count"),
        bolt_hole_diameter_mm=_positive(
            _number(raw.get("bolt_hole_diameter_mm"), f"{prefix}.bolt_hole_diameter_mm"),
            f"{prefix}.bolt_hole_diameter_mm",
        ),
        oring_groove_inner_diameter_mm=_number(
            raw.get("oring_groove_inner_diameter_mm", 0.0),
            f"{prefix}.oring_groove_inner_diameter_mm",
        ),
        oring_groove_outer_diameter_mm=_number(
            raw.get("oring_groove_outer_diameter_mm", 0.0),
            f"{prefix}.oring_groove_outer_diameter_mm",
        ),
        oring_groove_depth_mm=_number(
            raw.get("oring_groove_depth_mm", 0.0),
            f"{prefix}.oring_groove_depth_mm",
        ),
        knife_edge_protected_zone_mm=_positive(
            _number(
                raw.get("knife_edge_protected_zone_mm"),
                f"{prefix}.knife_edge_protected_zone_mm",
            ),
            f"{prefix}.knife_edge_protected_zone_mm",
        ),
        weld_interface=_text(raw.get("weld_interface"), f"{prefix}.weld_interface"),
        transition_outer_diameter_mm=_positive(
            _number(
                raw.get("transition_outer_diameter_mm"),
                f"{prefix}.transition_outer_diameter_mm",
            ),
            f"{prefix}.transition_outer_diameter_mm",
        ),
        transition_inner_diameter_mm=_positive(
            _number(
                raw.get("transition_inner_diameter_mm"),
                f"{prefix}.transition_inner_diameter_mm",
            ),
            f"{prefix}.transition_inner_diameter_mm",
        ),
        transition_length_mm=_positive(
            _number(
                raw.get("transition_length_mm"),
                f"{prefix}.transition_length_mm",
            ),
            f"{prefix}.transition_length_mm",
        ),
        transition_status=_state(
            raw.get("transition_status"),
            f"{prefix}.transition_status",
        ),
    )


def _parse_chamber_candidate(raw: Mapping[str, Any], prefix: str) -> ChamberCandidateSpec:
    cross_section = _text(raw.get("cross_section"), f"{prefix}.cross_section").lower()
    if cross_section not in {"square", "cylindrical"}:
        raise ValueError(f"{prefix}.cross_section must be square or cylindrical")
    spec = ChamberCandidateSpec(
        name=_text(raw.get("name"), f"{prefix}.name"),
        cross_section=cross_section,
        status=_state(raw.get("status"), f"{prefix}.status"),
        inner_size_x_mm=_positive(
            _number(raw.get("inner_size_x_mm"), f"{prefix}.inner_size_x_mm"),
            f"{prefix}.inner_size_x_mm",
        ),
        inner_size_y_mm=_positive(
            _number(raw.get("inner_size_y_mm"), f"{prefix}.inner_size_y_mm"),
            f"{prefix}.inner_size_y_mm",
        ),
        length_mm=_positive(
            _number(raw.get("length_mm"), f"{prefix}.length_mm"),
            f"{prefix}.length_mm",
        ),
        center_z_mm=_number(raw.get("center_z_mm"), f"{prefix}.center_z_mm"),
        wall_thickness_mm=_positive(
            _number(raw.get("wall_thickness_mm"), f"{prefix}.wall_thickness_mm"),
            f"{prefix}.wall_thickness_mm",
        ),
        wall_thickness_status=_state(
            raw.get("wall_thickness_status"),
            f"{prefix}.wall_thickness_status",
        ),
        material=_text(raw.get("material"), f"{prefix}.material"),
        service_accessibility=_text(
            raw.get("service_accessibility"),
            f"{prefix}.service_accessibility",
        ),
        service_plate_concept=_text(
            raw.get("service_plate_concept"),
            f"{prefix}.service_plate_concept",
        ),
    )
    if spec.cross_section == "cylindrical" and abs(spec.inner_size_x_mm - spec.inner_size_y_mm) > 1.0e-9:
        raise ValueError(f"{prefix} cylindrical candidate requires equal X/Y inner sizes")
    return spec


def _parse_maintenance_access(
    raw: Mapping[str, Any] | None,
) -> MaintenanceAccessSpec | None:
    if raw is None:
        return None
    prefix = "deployment.maintenance_access"
    candidates: list[MaintenanceAccessFlangeSpec] = []
    for idx, item in enumerate(_items(raw.get("candidates"), f"{prefix}.candidates")):
        entry_prefix = f"{prefix}.candidates[{idx}]"
        entry = _mapping(item, entry_prefix)
        candidate = MaintenanceAccessFlangeSpec(
            standard=_text(entry.get("standard"), f"{entry_prefix}.standard"),
            status=_state(entry.get("status"), f"{entry_prefix}.status"),
            disposition=_text(
                entry.get("disposition"),
                f"{entry_prefix}.disposition",
            ),
            chamber_candidate=_text(
                entry.get("chamber_candidate"),
                f"{entry_prefix}.chamber_candidate",
            ),
            center_x_mm=_number(
                entry.get("center_x_mm"),
                f"{entry_prefix}.center_x_mm",
            ),
            center_z_mm=_number(
                entry.get("center_z_mm"),
                f"{entry_prefix}.center_z_mm",
            ),
            flange_outer_diameter_mm=_positive(
                _number(
                    entry.get("flange_outer_diameter_mm"),
                    f"{entry_prefix}.flange_outer_diameter_mm",
                ),
                f"{entry_prefix}.flange_outer_diameter_mm",
            ),
            clear_bore_diameter_mm=_positive(
                _number(
                    entry.get("clear_bore_diameter_mm"),
                    f"{entry_prefix}.clear_bore_diameter_mm",
                ),
                f"{entry_prefix}.clear_bore_diameter_mm",
            ),
            counterbore_diameter_mm=_positive(
                _number(
                    entry.get("counterbore_diameter_mm"),
                    f"{entry_prefix}.counterbore_diameter_mm",
                ),
                f"{entry_prefix}.counterbore_diameter_mm",
            ),
            counterbore_depth_mm=_positive(
                _number(
                    entry.get("counterbore_depth_mm"),
                    f"{entry_prefix}.counterbore_depth_mm",
                ),
                f"{entry_prefix}.counterbore_depth_mm",
            ),
            pipe_outer_diameter_mm=_positive(
                _number(
                    entry.get("pipe_outer_diameter_mm"),
                    f"{entry_prefix}.pipe_outer_diameter_mm",
                ),
                f"{entry_prefix}.pipe_outer_diameter_mm",
            ),
            flange_thickness_mm=_positive(
                _number(
                    entry.get("flange_thickness_mm"),
                    f"{entry_prefix}.flange_thickness_mm",
                ),
                f"{entry_prefix}.flange_thickness_mm",
            ),
            bolt_circle_diameter_mm=_positive(
                _number(
                    entry.get("bolt_circle_diameter_mm"),
                    f"{entry_prefix}.bolt_circle_diameter_mm",
                ),
                f"{entry_prefix}.bolt_circle_diameter_mm",
            ),
            bolt_count=_integer(
                entry.get("bolt_count"),
                f"{entry_prefix}.bolt_count",
            ),
            bolt_hole_diameter_mm=_positive(
                _number(
                    entry.get("bolt_hole_diameter_mm"),
                    f"{entry_prefix}.bolt_hole_diameter_mm",
                ),
                f"{entry_prefix}.bolt_hole_diameter_mm",
            ),
            gasket_outer_diameter_mm=_positive(
                _number(
                    entry.get("gasket_outer_diameter_mm"),
                    f"{entry_prefix}.gasket_outer_diameter_mm",
                ),
                f"{entry_prefix}.gasket_outer_diameter_mm",
            ),
            gasket_inner_diameter_mm=_positive(
                _number(
                    entry.get("gasket_inner_diameter_mm"),
                    f"{entry_prefix}.gasket_inner_diameter_mm",
                ),
                f"{entry_prefix}.gasket_inner_diameter_mm",
            ),
            gasket_thickness_mm=_positive(
                _number(
                    entry.get("gasket_thickness_mm"),
                    f"{entry_prefix}.gasket_thickness_mm",
                ),
                f"{entry_prefix}.gasket_thickness_mm",
            ),
            weld_neck_length_mm=_positive(
                _number(
                    entry.get("weld_neck_length_mm"),
                    f"{entry_prefix}.weld_neck_length_mm",
                ),
                f"{entry_prefix}.weld_neck_length_mm",
            ),
        )
        if candidate.bolt_count <= 0:
            raise ValueError(f"{entry_prefix}.bolt_count must be > 0")
        if not (
            candidate.clear_bore_diameter_mm
            < candidate.counterbore_diameter_mm
            < candidate.flange_outer_diameter_mm
        ):
            raise ValueError(
                f"{entry_prefix} requires clear bore < counterbore < flange OD"
            )
        if candidate.counterbore_depth_mm >= candidate.flange_thickness_mm:
            raise ValueError(
                f"{entry_prefix}.counterbore_depth_mm must be less than flange thickness"
            )
        if not (
            candidate.gasket_inner_diameter_mm
            < candidate.gasket_outer_diameter_mm
            < candidate.flange_outer_diameter_mm
        ):
            raise ValueError(
                f"{entry_prefix} requires gasket ID < gasket OD < flange OD"
            )
        candidates.append(candidate)
    spec = MaintenanceAccessSpec(
        enabled=_boolean(raw.get("enabled"), f"{prefix}.enabled"),
        status=_state(raw.get("status"), f"{prefix}.status"),
        wall=_text(raw.get("wall"), f"{prefix}.wall"),
        selected_candidate=_text(
            raw.get("selected_candidate"),
            f"{prefix}.selected_candidate",
        ),
        supplier=_text(raw.get("supplier"), f"{prefix}.supplier"),
        fixed_flange_part_number=_text(
            raw.get("fixed_flange_part_number"),
            f"{prefix}.fixed_flange_part_number",
        ),
        blank_flange_part_number=_text(
            raw.get("blank_flange_part_number"),
            f"{prefix}.blank_flange_part_number",
        ),
        certified_drawing_reference=_text(
            raw.get("certified_drawing_reference"),
            f"{prefix}.certified_drawing_reference",
        ),
        dimensions_status=_state(
            raw.get("dimensions_status"),
            f"{prefix}.dimensions_status",
        ),
        seal_type=_text(raw.get("seal_type"), f"{prefix}.seal_type"),
        seal_material=_text(raw.get("seal_material"), f"{prefix}.seal_material"),
        elastomer_seal_allowed=_boolean(
            raw.get("elastomer_seal_allowed"),
            f"{prefix}.elastomer_seal_allowed",
        ),
        helium_leak_rate_max_pa_m3_s=_positive(
            _number(
                raw.get("helium_leak_rate_max_pa_m3_s"),
                f"{prefix}.helium_leak_rate_max_pa_m3_s",
            ),
            f"{prefix}.helium_leak_rate_max_pa_m3_s",
        ),
        flange_edge_margin_mm=_positive(
            _number(
                raw.get("flange_edge_margin_mm"),
                f"{prefix}.flange_edge_margin_mm",
            ),
            f"{prefix}.flange_edge_margin_mm",
        ),
        service_port_clearance_mm=_positive(
            _number(
                raw.get("service_port_clearance_mm"),
                f"{prefix}.service_port_clearance_mm",
            ),
            f"{prefix}.service_port_clearance_mm",
        ),
        passage_diametral_clearance_mm=_positive(
            _number(
                raw.get("passage_diametral_clearance_mm"),
                f"{prefix}.passage_diametral_clearance_mm",
            ),
            f"{prefix}.passage_diametral_clearance_mm",
        ),
        complete_extraction_status=_state(
            raw.get("complete_extraction_status"),
            f"{prefix}.complete_extraction_status",
        ),
        candidates=tuple(candidates),
    )
    if spec.wall != "positive_y_top":
        raise ValueError(f"{prefix}.wall must be positive_y_top")
    standards = [candidate.standard for candidate in spec.candidates]
    if len(standards) != len(set(standards)):
        raise ValueError(f"{prefix}.candidates standards must be unique")
    _ = spec.selected
    return spec


def _parse_sector_mounts(value: Any) -> tuple[SectorMountSpec, ...]:
    if value is None:
        return ()
    mounts: list[SectorMountSpec] = []
    for idx, item in enumerate(_items(value, "deployment.sector_mounts")):
        prefix = f"deployment.sector_mounts[{idx}]"
        entry = _mapping(item, prefix)
        sector = _text(entry.get("sector"), f"{prefix}.sector")
        wall = _text(entry.get("wall"), f"{prefix}.wall")
        if sector not in {"left", "right", "up", "down"}:
            raise ValueError(f"{prefix}.sector is unsupported: {sector!r}")
        if wall not in {"negative_x", "positive_x", "positive_y", "negative_y"}:
            raise ValueError(f"{prefix}.wall is unsupported: {wall!r}")
        mounts.append(
            SectorMountSpec(
                sector=sector,
                wall=wall,
                tangent_coordinate_mm=_number(
                    entry.get("tangent_coordinate_mm"),
                    f"{prefix}.tangent_coordinate_mm",
                ),
                wall_standoff_mm=_positive(
                    _number(
                        entry.get("wall_standoff_mm"),
                        f"{prefix}.wall_standoff_mm",
                    ),
                    f"{prefix}.wall_standoff_mm",
                ),
                release_clearance_mm=_positive(
                    _number(
                        entry.get("release_clearance_mm"),
                        f"{prefix}.release_clearance_mm",
                    ),
                    f"{prefix}.release_clearance_mm",
                ),
            )
        )
    sectors = [item.sector for item in mounts]
    if len(sectors) != len(set(sectors)):
        raise ValueError("deployment.sector_mounts sectors must be unique")
    return tuple(mounts)


def _parse_deployment(raw: Mapping[str, Any]) -> DeploymentSpec:
    candidates = tuple(
        _parse_chamber_candidate(
            _mapping(item, f"deployment.chamber_candidates[{idx}]"),
            f"deployment.chamber_candidates[{idx}]",
        )
        for idx, item in enumerate(
            _items(raw.get("chamber_candidates"), "deployment.chamber_candidates")
        )
    )
    envelope_raw = raw.get("available_envelope_mm")
    envelope = (
        None
        if envelope_raw is None
        else _vector(envelope_raw, "deployment.available_envelope_mm", 3)
    )
    ports: list[ServicePortPlacementSpec] = []
    for idx, item in enumerate(_items(raw.get("service_ports"), "deployment.service_ports")):
        entry = _mapping(item, f"deployment.service_ports[{idx}]")
        sector_raw = entry.get("sector")
        ports.append(
            ServicePortPlacementSpec(
                name=_text(entry.get("name"), f"deployment.service_ports[{idx}].name"),
                role=_text(entry.get("role"), f"deployment.service_ports[{idx}].role"),
                sector=(
                    None
                    if sector_raw is None
                    else _text(sector_raw, f"deployment.service_ports[{idx}].sector")
                ),
                center_x_mm=_number(
                    entry.get("center_x_mm"),
                    f"deployment.service_ports[{idx}].center_x_mm",
                ),
                center_z_mm=_number(
                    entry.get("center_z_mm"),
                    f"deployment.service_ports[{idx}].center_z_mm",
                ),
                bore_diameter_mm=_positive(
                    _number(
                        entry.get("bore_diameter_mm"),
                        f"deployment.service_ports[{idx}].bore_diameter_mm",
                    ),
                    f"deployment.service_ports[{idx}].bore_diameter_mm",
                ),
                collar_outer_diameter_mm=_positive(
                    _number(
                        entry.get("collar_outer_diameter_mm"),
                        f"deployment.service_ports[{idx}].collar_outer_diameter_mm",
                    ),
                    f"deployment.service_ports[{idx}].collar_outer_diameter_mm",
                ),
                collar_length_mm=_positive(
                    _number(
                        entry.get("collar_length_mm"),
                        f"deployment.service_ports[{idx}].collar_length_mm",
                    ),
                    f"deployment.service_ports[{idx}].collar_length_mm",
                ),
            )
        )
        if ports[-1].role not in {"rotary", "signal"}:
            raise ValueError(
                "deployment.service_ports role must be rotary or signal; "
                f"removed service role {ports[-1].role!r} is not supported"
            )
    spec = DeploymentSpec(
        name=_text(raw.get("name"), "deployment.name"),
        instrument_name=_text(
            raw.get("instrument_name"),
            "deployment.instrument_name",
        ),
        location=_text(raw.get("location"), "deployment.location"),
        status=_state(raw.get("status"), "deployment.status"),
        external_route_module=_text(
            raw.get("external_route_module"),
            "deployment.external_route_module",
        ),
        selected_chamber_candidate=_text(
            raw.get("selected_chamber_candidate"),
            "deployment.selected_chamber_candidate",
        ),
        chamber_candidates=candidates,
        beam_stay_clear_diameter_mm=_positive(
            _number(
                raw.get("beam_stay_clear_diameter_mm"),
                "deployment.beam_stay_clear_diameter_mm",
            ),
            "deployment.beam_stay_clear_diameter_mm",
        ),
        beam_stay_clear_status=_state(
            raw.get("beam_stay_clear_status"),
            "deployment.beam_stay_clear_status",
        ),
        available_envelope_mm=(
            None if envelope is None else (envelope[0], envelope[1], envelope[2])
        ),
        available_envelope_status=_state(
            raw.get("available_envelope_status"),
            "deployment.available_envelope_status",
        ),
        front_interface=_parse_beam_interface(
            _mapping(raw.get("front_interface"), "deployment.front_interface"),
            "deployment.front_interface",
        ),
        rear_interface=_parse_beam_interface(
            _mapping(raw.get("rear_interface"), "deployment.rear_interface"),
            "deployment.rear_interface",
        ),
        target_feedthrough_standard=_text(
            raw.get("target_feedthrough_standard"),
            "deployment.target_feedthrough_standard",
        ),
        target_feedthrough_status=_state(
            raw.get("target_feedthrough_status"),
            "deployment.target_feedthrough_status",
        ),
        pump_gauge_requirements=tuple(
            _text(item, f"deployment.pump_gauge_requirements[{idx}]")
            for idx, item in enumerate(
                _items(raw.get("pump_gauge_requirements"), "deployment.pump_gauge_requirements")
            )
        ),
        support_alignment_status=_state(
            raw.get("support_alignment_status"),
            "deployment.support_alignment_status",
        ),
        external_service_envelope_status=_state(
            raw.get("external_service_envelope_status"),
            "deployment.external_service_envelope_status",
        ),
        maintenance_access=_parse_maintenance_access(
            None
            if raw.get("maintenance_access") is None
            else _mapping(
                raw.get("maintenance_access"),
                "deployment.maintenance_access",
            )
        ),
        sector_mounts=_parse_sector_mounts(raw.get("sector_mounts")),
        service_ports=tuple(ports),
    )
    _ = spec.chamber
    if spec.maintenance_access is not None and spec.maintenance_access.enabled:
        access_candidate = spec.maintenance_access.selected
        chamber_names = {candidate.name for candidate in spec.chamber_candidates}
        unresolved_chambers = {
            candidate.chamber_candidate
            for candidate in spec.maintenance_access.candidates
            if candidate.chamber_candidate not in chamber_names
        }
        if unresolved_chambers:
            raise ValueError(
                "maintenance-access candidates reference unknown chamber candidates: "
                f"{sorted(unresolved_chambers)}"
            )
        if access_candidate.chamber_candidate != spec.selected_chamber_candidate:
            raise ValueError(
                "selected maintenance-access candidate must reference the selected "
                "chamber candidate"
            )
    return spec


_REMOVED_SCHEMA_V2_FIELDS = {
    "cassette",
    "sector_cartridge",
    "temperature_sensor",
    "temperature_sensor_status",
    "temperature_channels",
    "wires_per_temperature_channel",
    "temperature_harnesses",
    "housekeeping_pin_capacity",
    "housekeeping_interface",
    "housekeeping",
    "anti_rotation_tab_mm",
}


def _removed_field_paths(
    value: Any,
    prefix: str = "",
) -> tuple[str, ...]:
    paths: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if key in _REMOVED_SCHEMA_V2_FIELDS:
                paths.append(path)
            paths.extend(_removed_field_paths(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_removed_field_paths(item, f"{prefix}[{index}]"))
    return tuple(paths)


def parse_compact_one_config(raw: Mapping[str, Any]) -> CompactOnePlatformConfig:
    schema_version = _integer(raw.get("schema_version"), "schema_version")
    if schema_version != 3:
        raise ValueError(
            "CompactOne schema_version must be 3; migrate detector.cassette to "
            "detector.head, sector_cartridge to sector_holder, and remove all "
            "temperature/housekeeping fields"
        )
    removed_paths = _removed_field_paths(raw)
    if removed_paths:
        raise ValueError(
            "CompactOne schema v3 rejects removed fields: "
            + ", ".join(sorted(removed_paths))
        )
    architecture_mode = _text(raw.get("architecture_mode"), "architecture_mode")
    if architecture_mode != "compact_one":
        raise ValueError("architecture_mode must be compact_one for schema v3")
    return CompactOnePlatformConfig(
        schema_version=schema_version,
        architecture_mode=architecture_mode,
        detector=_parse_detector(_mapping(raw.get("detector"), "detector")),
        sector_holder=_parse_sector_holder(
            _mapping(raw.get("sector_holder"), "sector_holder")
        ),
        target=_parse_target(_mapping(raw.get("target"), "target")),
        services=_parse_services(_mapping(raw.get("services"), "services")),
        thermal=_parse_thermal(_mapping(raw.get("thermal"), "thermal")),
        materials=_parse_materials(_items(raw.get("materials"), "materials")),
        deployment=_parse_deployment(_mapping(raw.get("deployment"), "deployment")),
    )


def compact_one_vessel_mapping(platform: CompactOnePlatformConfig) -> dict[str, Any]:
    chamber = platform.deployment.chamber

    def interface_mapping(interface: PurchasedBeamInterfaceSpec) -> dict[str, Any]:
        return {
            "standard": interface.standard,
            "module_outer_diameter_mm": interface.module_outer_diameter_mm,
            "module_inner_diameter_mm": interface.module_inner_diameter_mm,
            "pipe_outer_diameter_mm": interface.transition_outer_diameter_mm,
            "pipe_inner_diameter_mm": interface.transition_inner_diameter_mm,
            "pipe_length_mm": interface.transition_length_mm,
            "module_thickness_mm": interface.module_thickness_mm,
            "seal_face_width_mm": interface.seal_face_width_mm,
            "bolt_circle_diameter_mm": interface.bolt_circle_diameter_mm,
            "bolt_count": interface.bolt_count,
            "flange_bolt_hole_diameter_mm": interface.bolt_hole_diameter_mm,
            "oring_groove_inner_diameter_mm": interface.oring_groove_inner_diameter_mm,
            "oring_groove_outer_diameter_mm": interface.oring_groove_outer_diameter_mm,
            "oring_groove_depth_mm": interface.oring_groove_depth_mm,
            "interface_bolt_diameter_mm": max(1.0, interface.bolt_hole_diameter_mm - 0.4),
            "interface_bolt_length_mm": interface.module_thickness_mm + 18.0,
            "interface_nut_outer_diameter_mm": max(3.0, interface.bolt_hole_diameter_mm + 4.6),
            "interface_nut_thickness_mm": 6.5,
            "interface_washer_outer_diameter_mm": max(4.0, interface.bolt_hole_diameter_mm + 7.6),
            "interface_washer_thickness_mm": 1.5,
        }

    # [EN] The legacy vessel view is generated from the selected deployment candidate so geometry code cannot silently diverge from the schema-v3 source. / [CN] 旧版 vessel 视图由所选部署候选自动生成，避免几何代码与 schema-v3 权威来源静默分叉。
    return {
        "cross_section": chamber.cross_section,
        "inner_size_x_mm": chamber.inner_size_x_mm,
        "inner_size_y_mm": chamber.inner_size_y_mm,
        "wall_thickness_mm": chamber.wall_thickness_mm,
        "length_mm": chamber.length_mm,
        "center_z_mm": chamber.center_z_mm,
        "beam_bore_diameter_mm": min(
            platform.deployment.front_interface.transition_inner_diameter_mm,
            platform.deployment.rear_interface.transition_inner_diameter_mm,
        ),
        "end_modules": {
            "front": interface_mapping(platform.deployment.front_interface),
            "rear": interface_mapping(platform.deployment.rear_interface),
        },
        "contract": {
            "front_standard": platform.deployment.front_interface.standard,
            "rear_standard": platform.deployment.rear_interface.standard,
        },
    }


def compact_one_detector_mapping(platform: CompactOnePlatformConfig) -> dict[str, Any]:
    detector = platform.detector
    head = detector.head
    # [EN] Deprecated scalar fields mirror only active geometry for analysis callers; schema v3 derives the detector-head envelope from the real axial stack. / [CN] 弃用标量只为分析调用方镜像有效体几何；schema v3 由真实轴向堆栈推导探测器头包络。
    return {
        "radius_reference": detector.radius_reference,
        "diameter_mm": detector.active.diameter_mm,
        "length_mm": detector.active.thickness_mm,
        "clamp_outer_diameter_mm": head.mounting_flange_diameter_mm,
        "clamp_width_mm": min(
            detector.active.thickness_mm,
            head.rear_cap_wall_mm,
        ),
        "active_medium_status": "selected",
        "active_medium": detector.active.material,
        "photosensor_status": "selected",
        "photosensor": detector.sipm.model,
    }


def compact_one_inner_frame_mapping(platform: CompactOnePlatformConfig) -> dict[str, Any]:
    holder = platform.sector_holder
    # [EN] These values exist only for legacy-scaffold compatibility; preferred CompactOne geometry consumes the sector-holder specification directly. / [CN] 这些数值仅用于旧脚手架兼容；首选 CompactOne 几何直接读取扇区支架规范。
    return {
        "spine_diameter_mm": 2.0 * holder.carrier_node_radius_mm,
        "arm_cross_width_mm": holder.carrier_web_width_mm,
        "arm_cross_thickness_mm": holder.carrier_plate_thickness_mm,
    }


def compact_one_top_services_mapping(platform: CompactOnePlatformConfig) -> dict[str, Any]:
    services = platform.services
    target = platform.target
    deployment = platform.deployment
    signal_ports = [port for port in deployment.service_ports if port.role == "signal"]
    rotary_ports = [port for port in deployment.service_ports if port.role == "rotary"]
    if len(signal_ports) != 4 or len(rotary_ports) != 1:
        raise ValueError(
            "deployment service layout requires four sector signal ports and one rotary port"
        )
    rotary_port = rotary_ports[0]
    interface = services.signal_interface
    rotary = target.rotary
    holder = target.holder
    foil = target.foil

    # [EN] All bought-out flange dimensions remain tagged by schema-v3 decision metadata; this compatibility mapping only supplies envelope geometry to the old builder. / [CN] 所有采购法兰尺寸仍由 schema-v3 决策元数据标识；此兼容映射只向旧生成器提供包络几何。
    return {
        "status": "interface_envelope",
        "icf70_interface": {
            "standard": interface.standard,
            "module_outer_diameter_mm": interface.module_outer_diameter_mm,
            "module_inner_diameter_mm": interface.module_inner_diameter_mm,
            "pipe_outer_diameter_mm": interface.module_inner_diameter_mm,
            "pipe_inner_diameter_mm": min(
                interface.nominal_clear_bore_mm,
                rotary_port.bore_diameter_mm,
            ),
            "pipe_length_mm": 0.0,
            "module_thickness_mm": interface.module_thickness_mm,
            "seal_face_width_mm": interface.seal_face_width_mm,
            "bolt_circle_diameter_mm": interface.bolt_circle_diameter_mm,
            "bolt_count": interface.bolt_count,
            "flange_bolt_hole_diameter_mm": interface.bolt_hole_diameter_mm,
            "oring_groove_inner_diameter_mm": 0.0,
            "oring_groove_outer_diameter_mm": 0.0,
            "oring_groove_depth_mm": 0.0,
            "interface_bolt_diameter_mm": max(1.0, interface.bolt_hole_diameter_mm - 0.6),
            "interface_bolt_length_mm": interface.module_thickness_mm + 10.0,
            "interface_nut_outer_diameter_mm": interface.bolt_hole_diameter_mm + 3.4,
            "interface_nut_thickness_mm": 5.0,
            "interface_washer_outer_diameter_mm": interface.bolt_hole_diameter_mm + 5.4,
            "interface_washer_thickness_mm": 1.0,
        },
        "rotary": {
            "mount_standard": rotary.mount_standard,
            "pivot_x_mm": rotary.pivot_mm[0],
            "pivot_z_mm": rotary.pivot_mm[2],
            "port_inner_diameter_mm": rotary_port.bore_diameter_mm,
            "port_outer_diameter_mm": rotary_port.collar_outer_diameter_mm,
            "port_collar_length_mm": rotary_port.collar_length_mm,
            "shaft_diameter_mm": rotary.shaft_diameter_mm,
            "work_angle_deg": rotary.work_angle_deg,
            "park_angle_deg": rotary.park_angle_deg,
            "arm_length_mm": rotary.arm_length_mm,
            "arm_width_mm": rotary.arm_width_mm,
            "arm_thickness_mm": rotary.arm_thickness_mm,
            "hub_diameter_mm": rotary.hub_diameter_mm,
            "hub_thickness_mm": rotary.hub_thickness_mm,
            "holder_outer_width_mm": holder.outer_width_mm,
            "holder_outer_height_mm": holder.outer_height_mm,
            "holder_frame_width_mm": holder.frame_width_mm,
            "holder_thickness_mm": holder.thickness_mm,
            "target_diameter_mm": foil.diameter_mm,
            "target_thickness_mm": foil.thickness_mm,
            "beam_stay_clear_diameter_mm": deployment.beam_stay_clear_diameter_mm,
            "supplier_model_status": "unfrozen",
            "supplier_reference_code": "UNRESOLVED_ROTARY_PURCHASED_PART",
            "external_body_diameter_mm": 38.0,
            "external_body_length_mm": 107.5,
            "handwheel_diameter_mm": 70.0,
            "handwheel_thickness_mm": 12.0,
        },
        "electrical": {
            "architecture_status": "provisional",
            "impedance_ohm": services.coax_impedance_ohm,
            "detector_channel_count": services.fast_signal_channels,
            "bias_on_signal_coax": services.bias_architecture == "external_bias_tee_on_signal_coax",
            "active_electronics_in_vacuum": services.active_electronics_in_vacuum,
            "channels_per_signal_port": services.channels_per_signal_feedthrough,
            "signal_ports": [
                {
                    "name": port.name,
                    "sector": port.sector,
                    "center_x_mm": port.center_x_mm,
                    "center_z_mm": port.center_z_mm,
                }
                for port in signal_ports
            ],
            "signal_port_inner_diameter_mm": interface.nominal_clear_bore_mm,
            "signal_port_outer_diameter_mm": signal_ports[0].collar_outer_diameter_mm,
            "signal_port_collar_length_mm": signal_ports[0].collar_length_mm,
            "signal_equipment_envelope_diameter_mm": 50.0,
            "signal_equipment_envelope_length_mm": 55.0,
            "routing": {
                "cable_keepout_diameter_mm": services.routing.cable_keepout_diameter_mm,
                "minimum_static_bend_radius_mm": services.routing.minimum_static_bend_radius_mm,
                "wall_clearance_mm": services.routing.wall_clearance_mm,
                "strain_relief_length_mm": services.routing.strain_relief_length_mm,
                "strain_relief_width_mm": services.routing.strain_relief_width_mm,
                "strain_relief_thickness_mm": services.routing.strain_relief_thickness_mm,
            },
            "grounding": {
                "protective_bond_required": services.grounding.protective_bond_required,
                "coax_shield_bond_at_feedthrough": services.grounding.coax_shield_bond_at_feedthrough,
                "signal_shield_is_only_protective_earth": (
                    services.grounding.signal_shield_is_only_protective_earth
                ),
            },
        },
    }
