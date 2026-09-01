from __future__ import annotations

from dataclasses import dataclass

from .config import CIVConfig


@dataclass(frozen=True)
class ConfigRule:
    category: str
    name: str
    passed: bool
    strict_only: bool
    detail: str


def _rule(
    category: str,
    name: str,
    passed: bool,
    detail: str,
    strict_only: bool = False,
) -> ConfigRule:
    return ConfigRule(
        category=category,
        name=name,
        passed=passed,
        strict_only=strict_only,
        detail=detail,
    )


def evaluate_config_rules(cfg: CIVConfig) -> tuple[ConfigRule, ...]:
    if cfg.compact_one is None:
        raise ValueError("CompactOne config rules require schema version 3")
    platform = cfg.compact_one
    detector = platform.detector
    head = detector.head
    deployment = platform.deployment
    services = platform.services
    thermal = platform.thermal
    rules: list[ConfigRule] = []

    rules.append(
        _rule(
            "physics",
            "compact_platform_contract",
            platform.schema_version == 3
            and platform.architecture_mode == "compact_one"
            and len(cfg.channels) * len(cfg.sectors) == 12,
            (
                f"schema={platform.schema_version}, mode={platform.architecture_mode}, "
                f"placements={len(cfg.channels) * len(cfg.sectors)}"
            ),
        )
    )
    rules.append(
        _rule(
            "detector",
            "detector_head_axial_stack_complete",
            detector.active.thickness_mm > 0.0
            and detector.optics.coupling_thickness_mm > 0.0
            and detector.sipm.package_envelope_mm[2] > 0.0
            and head.carrier_envelope_mm[2] > 0.0
            and head.rear_cap_wall_mm > 0.0,
            (
                f"active={detector.active.diameter_mm:.3f}x"
                f"{detector.active.thickness_mm:.3f} mm, "
                f"coupling={detector.optics.coupling_thickness_mm:.3f} mm, "
                f"sipm={detector.sipm.package_envelope_mm[2]:.3f} mm, "
                f"carrier={head.carrier_envelope_mm[2]:.3f} mm, "
                f"rear_cap={head.rear_cap_wall_mm:.3f} mm"
            ),
        )
    )
    holder = platform.sector_holder
    rules.append(
        _rule(
            "sector_holder",
            "coherent_three_nest_sector_holder_contract",
            holder.architecture == "single_fabricated_three_nest_sector_carrier"
            and holder.detector_mounts
            == ("deuteron", "proton_small", "proton_large")
            and "plane_pin_slot" in holder.chamber_interface
            and "radially_outward" in holder.sector_removal_direction,
            (
                f"architecture={holder.architecture}, "
                f"mounts={holder.detector_mounts}, "
                f"interface={holder.chamber_interface}, "
                f"removal={holder.sector_removal_direction}"
            ),
        )
    )
    rules.append(
        _rule(
            "detector",
            "detector_head_compact_depth",
            detector.physical_depth_mm <= head.maximum_physical_depth_mm
            and head.maximum_physical_depth_mm <= 18.0,
            (
                f"calculated_physical_depth_mm={detector.physical_depth_mm:.3f}, "
                f"gate_mm={head.maximum_physical_depth_mm:.3f}; "
                "cable and connector keepouts excluded"
            ),
        )
    )
    rules.append(
        _rule(
            "detector",
            "prototype_thickness_candidate",
            detector.active.thickness_mm
            in detector.active.thickness_candidates_mm
            and detector.active.thickness_status
            in {"provisional", "recommended"},
            (
                f"selected={detector.active.thickness_mm}, "
                f"candidates={detector.active.thickness_candidates_mm}, "
                f"status={detector.active.thickness_status}"
            ),
        )
    )
    rules.append(
        _rule(
            "detector",
            "supplier_and_optics_decisions_resolved",
            detector.sipm.status in {"frozen", "purchased-part-contract"}
            and detector.optics.reflector_status != "placeholder"
            and head.carrier_status != "placeholder",
            (
                f"sipm={detector.sipm.status}, "
                f"reflector={detector.optics.reflector_status}, "
                f"carrier={head.carrier_status}"
            ),
            strict_only=True,
        )
    )

    signal_capacity = (
        services.signal_feedthrough_count
        * services.channels_per_signal_feedthrough
    )
    rules.append(
        _rule(
            "services",
            "fast_signal_channel_capacity",
            services.fast_signal_channels == 12
            and signal_capacity >= services.fast_signal_channels,
            (
                f"required={services.fast_signal_channels}, "
                f"capacity={signal_capacity}"
            ),
        )
    )
    rules.append(
        _rule(
            "services",
            "passive_in_vacuum_electronics",
            services.coax_impedance_ohm == 50.0
            and services.bias_architecture
            == "external_bias_tee_on_signal_coax"
            and not services.active_electronics_in_vacuum,
            (
                f"impedance={services.coax_impedance_ohm}, "
                f"bias={services.bias_architecture}, "
                f"active_in_vacuum={services.active_electronics_in_vacuum}"
            ),
        )
    )
    rules.append(
        _rule(
            "services",
            "protective_grounding_contract",
            services.grounding.protective_bond_required
            and services.grounding.coax_shield_bond_at_feedthrough
            and not services.grounding.signal_shield_is_only_protective_earth,
            (
                f"reference={services.grounding.reference}, "
                f"protective_bond={services.grounding.protective_bond_required}"
            ),
        )
    )

    aperture_mm = min(
        deployment.front_interface.nominal_clear_bore_mm,
        deployment.rear_interface.nominal_clear_bore_mm,
        deployment.front_interface.transition_inner_diameter_mm,
        deployment.rear_interface.transition_inner_diameter_mm,
    )
    rules.append(
        _rule(
            "beamline",
            "certified_interface_aperture_compatible",
            deployment.beam_stay_clear_diameter_mm <= aperture_mm,
            (
                f"stay_clear={deployment.beam_stay_clear_diameter_mm:.3f}, "
                f"minimum_interface_bore={aperture_mm:.3f}"
            ),
        )
    )
    for side, interface in (
        ("front", deployment.front_interface),
        ("rear", deployment.rear_interface),
    ):
        radial_wall_mm = 0.5 * (
            interface.transition_outer_diameter_mm
            - interface.transition_inner_diameter_mm
        )
        rules.append(
            _rule(
                "mechanical",
                f"{side}_transition_minimum_sanity_wall",
                radial_wall_mm >= 1.0,
                f"radial_wall_mm={radial_wall_mm:.3f}, screening_minimum_mm=1.000",
                strict_only=True,
            )
        )
        rules.append(
            _rule(
                "vacuum",
                f"{side}_purchased_interface_contract_resolved",
                interface.dimensions_status
                in {"frozen", "purchased-part-contract"}
                and interface.supplier != "unresolved"
                and interface.part_number != "unresolved"
                and interface.certified_drawing_reference != "unresolved",
                (
                    f"dimensions={interface.dimensions_status}, "
                    f"supplier={interface.supplier}, part={interface.part_number}, "
                    f"drawing={interface.certified_drawing_reference}"
                ),
                strict_only=True,
            )
        )
    for role, interface in (("signal", services.signal_interface),):
        rules.append(
            _rule(
                "vacuum",
                f"{role}_feedthrough_contract_resolved",
                interface.dimensions_status
                in {"frozen", "purchased-part-contract"}
                and interface.supplier != "unresolved"
                and interface.part_number != "unresolved"
                and interface.certified_drawing_reference != "unresolved",
                (
                    f"dimensions={interface.dimensions_status}, "
                    f"supplier={interface.supplier}, part={interface.part_number}, "
                    f"drawing={interface.certified_drawing_reference}"
                ),
                strict_only=True,
            )
        )

    rules.append(
        _rule(
            "target",
            "target_mechanism_complete",
            platform.target.mode == "single_rotary"
            and platform.target.rotary.work_angle_deg
            != platform.target.rotary.park_angle_deg
            and platform.target.rotary.hard_stop_angles_deg
            == (
                platform.target.rotary.work_angle_deg,
                platform.target.rotary.park_angle_deg,
            )
            and platform.target.holder.removable,
            (
                f"mode={platform.target.mode}, "
                f"work={platform.target.rotary.work_angle_deg}, "
                f"park={platform.target.rotary.park_angle_deg}, "
                f"stops={platform.target.rotary.hard_stop_angles_deg}"
            ),
        )
    )
    rules.append(
        _rule(
            "thermal",
            "thermal_path_declared",
            not thermal.floating_allowed
            and len(thermal.path) >= 5
            and len(thermal.required_connections) >= 4,
            (
                f"floating_allowed={thermal.floating_allowed}, "
                f"path_nodes={len(thermal.path)}, "
                f"required_connections={len(thermal.required_connections)}"
            ),
        )
    )
    unresolved_materials = tuple(
        material.name
        for material in platform.materials
        if material.vacuum_compatibility_status == "placeholder"
    )
    rules.append(
        _rule(
            "vacuum",
            "vacuum_material_compatibility_resolved",
            not unresolved_materials,
            f"placeholder_materials={unresolved_materials}",
            strict_only=True,
        )
    )
    rules.append(
        _rule(
            "mechanical",
            "chamber_candidate_supported",
            deployment.chamber.cross_section in {"square", "cylindrical"},
            (
                f"candidate={deployment.chamber.name}, "
                f"cross_section={deployment.chamber.cross_section}"
            ),
        )
    )
    rules.append(
        _rule(
            "mechanical",
            "fabrication_wall_requires_structural_gate",
            deployment.chamber.wall_thickness_status == "frozen",
            (
                f"wall={deployment.chamber.wall_thickness_mm:.3f} mm, "
                f"status={deployment.chamber.wall_thickness_status}; "
                "fabrication requires pressure-vessel analysis"
            ),
            strict_only=True,
        )
    )
    rules.append(
        _rule(
            "mechanical",
            "deployment_envelopes_resolved",
            deployment.available_envelope_status != "placeholder"
            and deployment.external_service_envelope_status != "placeholder"
            and deployment.support_alignment_status != "placeholder",
            (
                f"available={deployment.available_envelope_status}, "
                f"external_service={deployment.external_service_envelope_status}, "
                f"support_alignment={deployment.support_alignment_status}"
            ),
            strict_only=True,
        )
    )
    access = deployment.maintenance_access
    if access is not None and access.enabled:
        selected_access = access.selected
        rules.append(
            _rule(
                "vacuum",
                "maintenance_access_all_metal_contract",
                access.wall == "positive_y_top"
                and access.seal_type == "conflat_knife_edge_metal_gasket"
                and access.seal_material == "oxygen_free_copper"
                and not access.elastomer_seal_allowed
                and access.helium_leak_rate_max_pa_m3_s <= 1.0e-10,
                (
                    f"standard={selected_access.standard}, wall={access.wall}, "
                    f"seal={access.seal_type}/{access.seal_material}, "
                    f"elastomer_allowed={access.elastomer_seal_allowed}, "
                    "helium_leak_rate_max_pa_m3_s="
                    f"{access.helium_leak_rate_max_pa_m3_s:.3e}"
                ),
            )
        )
        rules.append(
            _rule(
                "vacuum",
                "maintenance_access_purchased_interface_resolved",
                access.dimensions_status in {"frozen", "purchased-part-contract"}
                and access.supplier != "unresolved"
                and access.fixed_flange_part_number != "unresolved"
                and access.blank_flange_part_number != "unresolved"
                and access.certified_drawing_reference != "unresolved",
                (
                    f"dimensions={access.dimensions_status}, supplier={access.supplier}, "
                    f"fixed={access.fixed_flange_part_number}, "
                    f"blank={access.blank_flange_part_number}, "
                    f"drawing={access.certified_drawing_reference}"
                ),
                strict_only=True,
            )
        )
        rules.append(
            _rule(
                "mechanical",
                "maintenance_access_complete_extraction_evidence",
                access.complete_extraction_status == "frozen",
                (
                    f"status={access.complete_extraction_status}; radial release, "
                    "in-chamber reorientation, and top lift require one continuous "
                    "validated motion"
                ),
                strict_only=True,
            )
        )
    sector_mounts = tuple(deployment.sector_mount(sector) for sector in cfg.sectors)
    mount_tangent_limit_mm = {
        "negative_x": 0.5 * deployment.chamber.inner_size_y_mm
        - 0.5 * holder.interface_block_mm[1],
        "positive_x": 0.5 * deployment.chamber.inner_size_y_mm
        - 0.5 * holder.interface_block_mm[1],
        "positive_y": 0.5 * deployment.chamber.inner_size_x_mm
        - 0.5 * holder.interface_block_mm[1],
        "negative_y": 0.5 * deployment.chamber.inner_size_x_mm
        - 0.5 * holder.interface_block_mm[1],
    }
    rules.append(
        _rule(
            "mechanical",
            "stationary_sector_support_configuration",
            all(
                mount.wall_standoff_mm > 0.0
                and mount.release_clearance_mm
                >= holder.locating_slot_length_mm
                and abs(mount.tangent_coordinate_mm)
                <= mount_tangent_limit_mm[mount.wall]
                for mount in sector_mounts
            ),
            ", ".join(
                f"{mount.sector}:{mount.wall}@{mount.tangent_coordinate_mm:.1f} mm/"
                f"standoff={mount.wall_standoff_mm:.1f} mm/"
                f"release={mount.release_clearance_mm:.1f} mm"
                for mount in sector_mounts
            ),
        )
    )
    if access is not None and access.enabled:
        rules.append(
            _rule(
                "mechanical",
                "maintenance_access_has_no_top_wall_sector_mount",
                all(mount.wall != "positive_y" for mount in sector_mounts),
                f"mount_walls={tuple(mount.wall for mount in sector_mounts)}",
            )
        )
    return tuple(rules)


def rule_status(rule: ConfigRule, strict: bool) -> str:
    if rule.passed:
        return "pass"
    if rule.strict_only and not strict:
        return "warning"
    return "fail"
