from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import FreeCAD as App
import Part


MODULE_ROOT = Path(__file__).resolve().parents[1]
ACCESS_STUDY_CONFIG_DIR = MODULE_ROOT / "studies" / "access_port" / "config"
sys.path.insert(0, str(MODULE_ROOT / "src"))

from civ.assembly import (
    build_sector_holder_document,
    build_transparent_detector_head_document,
)
from civ.access import (
    build_maintenance_access_boundary,
    build_maintenance_access_components,
)
from civ.cassette import build_detector_head, detector_head_compound
from civ.cartridge import build_sector_holder, sector_holder_compound
from civ.chamber import build_chamber
from civ.config import load_config
from civ.detector import detector_stack_metrics
from civ.internal import build_internal_assembly, internal_compound
from civ.layout import build_detector_placements
from civ.services import build_services
from civ.support import build_sector_mount
from civ.thermal import evaluate_thermal_paths
from civ.validation_compact import (
    find_acceptance_obstructions,
    validate_compact_one,
)
from civ.visual import (
    DATUM,
    KEEPOUT,
    OPTIONAL_REFERENCE,
    PHYSICAL,
    PHYSICS_ACCEPTANCE,
    PURCHASED,
    SERVICE_CENTERLINE,
    add_feature,
)


def _intersection_volume_mm3(shape_a: Part.Shape, shape_b: Part.Shape) -> float:
    common = shape_a.common(shape_b)
    return 0.0 if common.isNull() else float(common.Volume)


def _check_by_name(report: dict[str, object], name: str) -> dict[str, object]:
    return next(check for check in report["checks"] if check["name"] == name)


def test_detector_head_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    geometry = build_detector_head(cfg)
    compound = detector_head_compound(geometry)
    required = {
        "ActivePlastic",
        "ReflectorEnvelope",
        "OpticalCoupling",
        "SiPMPackage",
        "SensorPCBCarrier",
        "LightTightSleeve",
        "RearMountingFace",
        "CableExit",
    }
    assert required <= set(geometry.physical)
    assert compound.isValid() and not compound.isNull()
    assert all(
        shape.isValid() and not shape.isNull()
        for shape in geometry.physical.values()
    )
    assert not any(
        token in name.lower()
        for name in (
            *geometry.physical,
            *geometry.interfaces,
            *geometry.keepouts,
            *geometry.datums,
        )
        for token in ("temperature", "housekeeping", "thermalbridge")
    )

    active = geometry.physical["ActivePlastic"]
    coupling = geometry.physical["OpticalCoupling"]
    sipm = geometry.physical["SiPMPackage"]
    carrier = geometry.physical["SensorPCBCarrier"]
    rear_face = geometry.physical["RearMountingFace"]
    assert abs(active.CenterOfMass.x - coupling.CenterOfMass.x) <= 1.0e-9
    assert abs(active.CenterOfMass.y - coupling.CenterOfMass.y) <= 1.0e-9
    assert abs(coupling.CenterOfMass.x - sipm.CenterOfMass.x) <= 1.0e-9
    assert abs(coupling.CenterOfMass.y - sipm.CenterOfMass.y) <= 1.0e-9
    assert coupling.BoundBox.ZMin >= active.BoundBox.ZMax - 1.0e-9
    assert sipm.BoundBox.ZMin >= coupling.BoundBox.ZMax - 1.0e-9
    assert carrier.BoundBox.ZMin >= sipm.BoundBox.ZMax - 1.0e-9
    assert rear_face.distToShape(carrier)[0] <= 1.0e-6

    stack = detector_stack_metrics(cfg)
    assert math.isclose(
        float(stack["calculated_physical_depth_mm"]),
        9.7,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    )
    assert float(stack["calculated_physical_depth_mm"]) <= 18.0
    assert {"CableExit", "ConnectorKeepout"} <= set(stack["excludes"])

    return {
        "status": "pass",
        "physical_components": sorted(geometry.physical),
        "calculated_physical_depth_mm": stack["calculated_physical_depth_mm"],
        "housing_bounding_box_mm": [
            float(compound.BoundBox.XLength),
            float(compound.BoundBox.YLength),
            float(compound.BoundBox.ZLength),
        ],
    }


def test_sector_holder_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    geometry = build_sector_holder(cfg, "left")
    compound = sector_holder_compound(geometry)
    assert compound.isValid() and not compound.isNull()
    assert tuple(item.channel_name for item in geometry.placements) == (
        "deuteron",
        "proton_small",
        "proton_large",
    )
    assert len(geometry.placements) == 3
    assert tuple(
        name
        for name in geometry.holder_physical_names
        if name.endswith("_SectorCarrierPlate")
    ) == ("left_SectorCarrierPlate",)
    assert len(
        [
            name
            for name in geometry.holder_physical_names
            if name.endswith("_DetectorNestCradle")
        ]
    ) == 3
    assert len(
        [
            name
            for name in geometry.holder_physical_names
            if name.endswith("_RemovableClampBridge")
        ]
    ) == 3
    assert not any(
        name.endswith(("StructuralRail", "CartridgeMountPad", "ThermalStrap"))
        for name in geometry.physical
    )
    assert len(
        [
            name
            for name in geometry.purchased_interfaces
            if "M3ClampFastenerEnvelope" in name
        ]
    ) == 6
    assert {
        "left_PrimaryPlaneDatum",
        "left_RoundPinAxisDatum",
        "left_ClockingSlotDatum",
    } <= set(geometry.datums)
    assert "left_SectorRemovalEnvelope" in geometry.keepouts
    assert "left_RearCableLane" in geometry.keepouts
    assert geometry.stationary_physical_names == (
        "left_PermanentWallSupport",
    )
    assert set(geometry.stationary_purchased_interface_names) == {
        "left_RoundLocatingPinEnvelope",
        "left_SlotLocatingPinEnvelope",
    }
    assert geometry.physical["left_SectorInterfaceBlock"].distToShape(
        geometry.physical["left_PermanentWallSupport"]
    )[0] <= 1.0e-6
    assert all(
        shape.isValid() and not shape.isNull()
        for shape in (
            *geometry.physical.values(),
            *geometry.purchased_interfaces.values(),
        )
    )

    obstacles = {
        **geometry.physical,
        **geometry.purchased_interfaces,
    }
    obstructions = find_acceptance_obstructions(
        cfg,
        list(geometry.placements),
        obstacles,
        {
            placement.tag: {f"{placement.tag}_ActivePlastic"}
            for placement in geometry.placements
        },
    )
    assert not obstructions, obstructions

    return {
        "status": "pass",
        "detector_count": len(geometry.placements),
        "holder_component_count": len(geometry.holder_physical_names),
        "purchased_fastener_envelope_count": 6,
        "acceptance_obstructions": obstructions,
    }


def test_internal_and_services_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    internal = build_internal_assembly(cfg)
    services = build_services(cfg, internal)
    chamber = build_chamber(cfg)
    compound = internal_compound(internal)
    assert compound.isValid() and not compound.isNull()
    assert len(internal.placements) == 12
    assert set(internal.sector_holders) == {"left", "right", "up", "down"}
    assert all(len(holder.placements) == 3 for holder in internal.sector_holders.values())
    assert len(services.fast_signal_paths) == 12
    assert len(services.grounding_connections) == 4
    assert all(
        shape.isValid() and not shape.isNull()
        for shape in (
            *internal.physical.values(),
            *internal.purchased_interfaces.values(),
            *services.physical.values(),
            *services.purchased_interfaces.values(),
        )
    )
    assert {port.port.role for port in services.ports.values()} == {
        "rotary",
        "signal",
    }
    names = (
        *internal.physical,
        *internal.purchased_interfaces,
        *internal.keepouts,
        *services.physical,
        *services.purchased_interfaces,
        *services.keepouts,
        *services.centerlines,
    )
    assert not any(
        token in name.lower()
        for name in names
        for token in ("temperature", "housekeeping")
    )
    thermal = evaluate_thermal_paths(cfg, internal)
    assert thermal.status == "pass"
    assert len(thermal.channels) == 12
    assert all(item.connected for item in thermal.channels)
    chamber_body = chamber.physical["ProjectChamberBody"]
    lift_corridor = chamber.keepouts["MaintenanceAccessInternalLiftCorridor"]
    for sector, holder in internal.sector_holders.items():
        block = holder.physical[f"{sector}_SectorInterfaceBlock"]
        support = holder.physical[f"{sector}_PermanentWallSupport"]
        ground = services.physical[f"{sector}_ProtectiveGroundStrap"]
        assert block.distToShape(support)[0] <= 1.0e-6
        assert support.distToShape(chamber_body)[0] <= 1.0e-6
        assert ground.Volume > 100.0
        assert max(
            ground.BoundBox.XLength,
            ground.BoundBox.YLength,
            ground.BoundBox.ZLength,
        ) > 5.0
        assert ground.distToShape(block)[0] <= 1.0e-6
        assert ground.distToShape(support)[0] <= 1.0e-6
        assert ground.distToShape(chamber_body)[0] <= 1.0e-6
        assert _intersection_volume_mm3(support, lift_corridor) <= 1.0e-6
        assert _intersection_volume_mm3(ground, lift_corridor) <= 1.0e-6
        mount_geometry = build_sector_mount(
            cfg,
            sector,
            block.BoundBox.Center.z,
        )
        assert mount_geometry.interface_block.distToShape(block)[0] <= 1.0e-6
        assert mount_geometry.stationary_support.distToShape(support)[0] <= 1.0e-6
        assert set(mount_geometry.stationary_purchased_interfaces) == set(
            holder.stationary_purchased_interface_names
        )

    configured = {
        (placement.channel_name, placement.sector_name): (
            placement.angle_deg,
            placement.radius_mm,
        )
        for placement in build_detector_placements(cfg)
    }
    generated = {
        (placement.channel_name, placement.sector_name): (
            placement.angle_deg,
            placement.radius_mm,
        )
        for placement in internal.placements
    }
    assert generated == configured

    return {
        "status": "pass",
        "detector_count": len(internal.placements),
        "sector_count": len(internal.sector_holders),
        "signal_path_count": len(services.fast_signal_paths),
        "service_roles": sorted({port.port.role for port in services.ports.values()}),
        "thermal_connected_channel_count": len(thermal.channels),
    }


def test_document_roles_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    documents = (
        build_transparent_detector_head_document(cfg),
        build_sector_holder_document(cfg, "left"),
    )
    add_feature(
        documents[-1],
        "VisibilityProbeServiceCenterline",
        Part.makeLine(App.Vector(0.0, 0.0, 0.0), App.Vector(0.0, 0.0, 1.0)),
        role=SERVICE_CENTERLINE,
        group_name="Services",
    )
    expected_groups = {
        "DetectorHead",
        "SectorHolder",
        "Services",
        "Keepouts",
        "Datums",
        "PhysicsAcceptance",
        "OptionalReference",
    }
    observed_roles: set[str] = set()
    for document in documents:
        observed_roles.update(
            str(obj.EngineeringRole)
            for obj in document.Objects
            if hasattr(obj, "EngineeringRole")
        )
        if App.GuiUp:
            for obj in document.Objects:
                if not hasattr(obj, "EngineeringRole"):
                    continue
                role = str(obj.EngineeringRole)
                assert bool(obj.ViewObject.Visibility) == (
                    role in {PHYSICAL, PURCHASED}
                )
    full_document = documents[-1]
    assert expected_groups <= {
        obj.Name
        for obj in full_document.Objects
        if obj.TypeId == "App::DocumentObjectGroup"
    }
    assert {
        PHYSICAL,
        PURCHASED,
        KEEPOUT,
        DATUM,
        SERVICE_CENTERLINE,
        PHYSICS_ACCEPTANCE,
        OPTIONAL_REFERENCE,
    } <= observed_roles
    transparent = documents[0]
    assert transparent.getObject("LightTightSleeve").ViewObject.Transparency >= 80

    return {
        "status": "pass",
        "gui_available": bool(App.GuiUp),
        "observed_roles": sorted(observed_roles),
        "group_count": len(expected_groups),
    }


def test_maintenance_access_runtime() -> dict[str, object]:
    observed: dict[str, object] = {}
    for profile in (
        "afterSRC_access_icf253.yaml",
        "afterSRC_access_icf305.yaml",
        "afterSRC_access_icf356.yaml",
    ):
        cfg = load_config(str(ACCESS_STUDY_CONFIG_DIR / profile))
        access = cfg.compact_one.deployment.maintenance_access
        assert access is not None and access.enabled
        spec = access.selected
        chamber = build_chamber(cfg)
        boundary = build_maintenance_access_boundary(cfg)
        assert boundary is not None
        (
            access_physical,
            access_purchased,
            access_keepouts,
            access_datums,
            access_materials,
        ) = build_maintenance_access_components(cfg)
        assert {
            "MaintenanceAccessProjectWeldNeck",
            "MaintenanceAccessProjectWeldBead",
        } <= set(access_physical) <= set(chamber.physical)
        assert {
            "MaintenanceAccessFixedICFFlange",
            "MaintenanceAccessCopperGasket",
            "MaintenanceAccessBlindFlange",
        } <= set(access_purchased) <= set(chamber.purchased_interfaces)
        assert {
            "MaintenanceAccessOpenPassage",
            "MaintenanceAccessBlindRemovalEnvelope",
        } <= set(access_keepouts) <= set(chamber.keepouts)
        assert "MaintenanceAccessSealPlaneDatum" in access_datums
        assert set(access_materials) == set(access_physical)
        assert all(
            shape.isValid() and not shape.isNull()
            for shape in (
                chamber.physical["MaintenanceAccessProjectWeldNeck"],
                chamber.purchased_interfaces["MaintenanceAccessFixedICFFlange"],
                chamber.purchased_interfaces["MaintenanceAccessCopperGasket"],
                chamber.purchased_interfaces["MaintenanceAccessBlindFlange"],
            )
        )
        fixed = chamber.purchased_interfaces["MaintenanceAccessFixedICFFlange"]
        gasket = chamber.purchased_interfaces["MaintenanceAccessCopperGasket"]
        blank = chamber.purchased_interfaces["MaintenanceAccessBlindFlange"]
        neck = chamber.physical["MaintenanceAccessProjectWeldNeck"]
        weld_bead = chamber.physical["MaintenanceAccessProjectWeldBead"]
        assert math.isclose(
            fixed.BoundBox.XLength,
            spec.flange_outer_diameter_mm,
            rel_tol=0.0,
            abs_tol=1.0e-6,
        )
        assert math.isclose(
            fixed.BoundBox.ZLength,
            spec.flange_outer_diameter_mm,
            rel_tol=0.0,
            abs_tol=1.0e-6,
        )
        assert neck.distToShape(weld_bead)[0] <= 1.0e-6
        assert weld_bead.distToShape(fixed)[0] <= 1.0e-6
        assert fixed.distToShape(gasket)[0] <= 1.0e-6
        assert gasket.distToShape(blank)[0] <= 1.0e-6
        assert chamber.vacuum_control_volume.isValid()
        assert len(chamber.vacuum_control_volume.Solids) == 1
        expected_seal_plane_y_mm = (
            0.5 * chamber.candidate.inner_size_y_mm
            + chamber.candidate.wall_thickness_mm
            + spec.weld_neck_length_mm
            + spec.flange_thickness_mm
            + spec.gasket_thickness_mm
        )
        assert math.isclose(
            chamber.vacuum_control_volume.BoundBox.YMax,
            expected_seal_plane_y_mm,
            rel_tol=0.0,
            abs_tol=1.0e-6,
        )
        observed[spec.standard] = {
            "clear_bore_diameter_mm": spec.clear_bore_diameter_mm,
            "flange_outer_diameter_mm": spec.flange_outer_diameter_mm,
            "chamber_length_mm": chamber.candidate.length_mm,
        }
    return {"status": "pass", "candidates": observed}


def test_categorized_validation_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    report = validate_compact_one(
        cfg,
        build_detector_placements(cfg),
        strict=False,
    )
    assert report["status"] == "pass"
    assert report["summary"]["fail_count"] == 0
    required_passes = {
        "removed_monitoring_subsystem_absent",
        "detector_head_component_stack_present",
        "sipm_behind_and_aligned_with_optical_coupling",
        "physical_detector_head_depth_gate",
        "coherent_three_detector_sector_holders",
        "sector_mount_release_envelope_clear",
        "detector_axial_removal_after_clamp_release_clear",
        "full_active_acceptance_clear",
        "cable_routing_and_connector_keepouts_clear",
        "maintenance_access_all_metal_contract",
        "maintenance_access_flange_within_top_face",
        "maintenance_access_service_ports_clear",
        "maintenance_access_detached_holder_passage_screen",
        "maintenance_access_nominal_metal_seal_topology",
        "holder_to_stationary_support_load_path",
        "stationary_support_to_permanent_chamber_contact",
        "protective_ground_bond_to_permanent_chamber",
        "maintenance_access_closure_load_free",
        "stationary_sector_support_configuration",
        "maintenance_access_has_no_top_wall_sector_mount",
    }
    assert all(
        _check_by_name(report, name)["status"] == "pass"
        for name in required_passes
    )
    metrics = report["engineering_metrics"]
    assert len(metrics["detector_acceptance"]) == 12
    assert len(metrics["coincidence_geometry"]) == 8
    assert metrics["detector_head_stack"]["calculated_physical_depth_mm"] == 9.7
    assert metrics["maintenance_access"]["selected_candidate"]["standard"] == "ICF305"
    comparison = {
        item["standard"]: item
        for item in metrics["maintenance_access"]["candidate_comparison"]
    }
    assert not comparison["ICF253"]["flat_lift_screen_passed"]
    assert not comparison["ICF253"]["edge_on_screen_passed"]
    assert comparison["ICF305"]["flat_lift_screen_passed"]
    assert comparison["ICF356"]["flat_lift_screen_passed"]
    assert _check_by_name(
        report,
        "maintenance_access_complete_extraction_evidence",
    )["status"] == "warning"

    return {
        "status": "pass",
        "pass_count": report["summary"]["pass_count"],
        "warning_count": report["summary"]["warning_count"],
        "fail_count": report["summary"]["fail_count"],
        "required_engineering_checks": sorted(required_passes),
    }


def main() -> int:
    def run_case(name: str, function):
        print(f"RUN {name}", file=sys.stderr, flush=True)
        result = function()
        print(f"PASS {name}", file=sys.stderr, flush=True)
        return result

    print(
        json.dumps(
            {
                "detector_head": run_case(
                    "detector_head",
                    test_detector_head_runtime,
                ),
                "sector_holder": run_case(
                    "sector_holder",
                    test_sector_holder_runtime,
                ),
                "internal_services": run_case(
                    "internal_services",
                    test_internal_and_services_runtime,
                ),
                "categorized_validation": run_case(
                    "categorized_validation",
                    test_categorized_validation_runtime,
                ),
                "maintenance_access": run_case(
                    "maintenance_access",
                    test_maintenance_access_runtime,
                ),
                "document_roles": run_case(
                    "document_roles",
                    test_document_roles_runtime,
                ),
                "freecad_version": ".".join(App.Version()[:3]),
            },
            indent=2,
        )
    )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
