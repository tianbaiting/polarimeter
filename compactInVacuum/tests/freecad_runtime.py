from __future__ import annotations

import json
import math
from pathlib import Path
import sys

import FreeCAD as App
import Part


MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "src"))

from civ.cassette import build_detector_cassette, cassette_compound
from civ.cartridge import build_sector_cartridge, cartridge_compound
from civ.chamber import build_chamber
from civ.config import load_config
from civ.detector import build_active_acceptance_cone
from civ.internal import build_internal_assembly, internal_compound
from civ.layout import build_detector_placements
from civ.services import build_services
from civ.thermal import evaluate_thermal_paths
from civ.validation_compact import (
    find_acceptance_obstructions,
    find_pair_collisions,
    find_target_motion_collisions,
    validate_compact_one,
)


def _distance_mm(shape_a: Part.Shape, shape_b: Part.Shape) -> float:
    return float(shape_a.distToShape(shape_b)[0])


def _bounding_boxes_overlap(shape_a: Part.Shape, shape_b: Part.Shape) -> bool:
    a = shape_a.BoundBox
    b = shape_b.BoundBox
    return not (
        a.XMax < b.XMin
        or b.XMax < a.XMin
        or a.YMax < b.YMin
        or b.YMax < a.YMin
        or a.ZMax < b.ZMin
        or b.ZMax < a.ZMin
    )


def test_cassette_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    geometry = build_detector_cassette(cfg)
    compound = cassette_compound(geometry)
    active = cfg.compact_one.detector.active
    expected_active_volume_mm3 = (
        math.pi
        * (0.5 * active.diameter_mm) ** 2
        * active.thickness_mm
    )
    active_shape = geometry.physical["ActivePlastic"]
    shell = geometry.physical["LightTightShell"]
    entrance_probe = Part.makeCylinder(
        0.5 * active.diameter_mm,
        30.0,
        App.Vector(0.0, 0.0, -0.5 * active.thickness_mm - 30.0),
    )

    assert compound.isValid()
    assert all(not shape.isNull() and shape.isValid() for shape in geometry.physical.values())
    assert len(geometry.physical) == 12
    assert math.isclose(
        active_shape.Volume,
        expected_active_volume_mm3,
        rel_tol=0.0,
        abs_tol=1.0e-6,
    )
    assert shell.common(active_shape).Volume <= 1.0e-9
    assert shell.common(entrance_probe).Volume <= 1.0e-9

    thermal_pairs = (
        ("SiPM", "SensorCarrier"),
        ("SensorCarrier", "ThermalSpreader"),
        ("ThermalSpreader", "CassetteThermalBridge"),
        ("CassetteThermalBridge", "LightTightShell"),
        ("LightTightShell", "CassetteMountingInterface"),
    )
    cassette_shapes = {**geometry.physical, **geometry.interfaces}
    thermal_distances = {
        f"{name_a}->{name_b}": _distance_mm(
            cassette_shapes[name_a],
            cassette_shapes[name_b],
        )
        for name_a, name_b in thermal_pairs
    }
    assert all(distance <= 1.0e-6 for distance in thermal_distances.values())

    placements = build_detector_placements(cfg)
    placed = build_detector_cassette(cfg, placements[0])
    placed_active = placed.physical["ActivePlastic"]
    center = placed_active.CenterOfMass
    expected = placements[0].direction * placements[0].radius_mm
    assert (center - expected).Length <= 1.0e-6

    return {
        "status": "pass",
        "freecad_version": ".".join(App.Version()[:3]),
        "physical_component_count": len(geometry.physical),
        "interface_count": len(geometry.interfaces),
        "keepout_count": len(geometry.keepouts),
        "solid_count": len(compound.Solids),
        "bounding_box_mm": [
            float(compound.BoundBox.XLength),
            float(compound.BoundBox.YLength),
            float(compound.BoundBox.ZLength),
        ],
        "active_volume_mm3": float(active_shape.Volume),
        "thermal_contact_distances_mm": thermal_distances,
    }


def test_sector_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    geometry = build_sector_cartridge(cfg, "left")
    compound = cartridge_compound(geometry)
    assert tuple(item.channel_name for item in geometry.placements) == (
        "deuteron",
        "proton_small",
        "proton_large",
    )
    assert compound.isValid()
    assert all(not shape.isNull() and shape.isValid() for shape in geometry.physical.values())

    cassette_shapes: dict[str, Part.Shape] = {}
    for placement in geometry.placements:
        prefix = f"{placement.tag}_"
        cassette_shapes[placement.tag] = Part.makeCompound(
            [
                shape
                for name, shape in geometry.physical.items()
                if name.startswith(prefix)
                and not name.endswith(("CartridgeMountPad", "StructuralRail", "ThermalStrap"))
            ]
        )
    overlap_mm3: dict[str, float] = {}
    tags = tuple(cassette_shapes)
    for index, tag_a in enumerate(tags):
        for tag_b in tags[index + 1 :]:
            key = f"{tag_a}<->{tag_b}"
            overlap_mm3[key] = float(
                cassette_shapes[tag_a].common(cassette_shapes[tag_b]).Volume
            )
    assert all(volume <= 1.0e-6 for volume in overlap_mm3.values())

    los_obstructions: list[dict[str, object]] = []
    for placement in geometry.placements:
        cone = build_active_acceptance_cone(cfg, placement)
        own_active = f"{placement.tag}_ActivePlastic"
        for component, shape in geometry.physical.items():
            if component == own_active:
                continue
            intersection_mm3 = float(cone.common(shape).Volume)
            if intersection_mm3 > 1.0e-6:
                los_obstructions.append(
                    {
                        "channel": placement.channel_name,
                        "component": component,
                        "intersection_volume_mm3": intersection_mm3,
                    }
                )
    assert not los_obstructions, los_obstructions

    all_shapes = {**geometry.physical, **geometry.interfaces}
    thermal_distances = {
        f"{name_a}->{name_b}": _distance_mm(all_shapes[name_a], all_shapes[name_b])
        for name_a, name_b in geometry.thermal_connections
    }
    assert all(distance <= 1.0e-6 for distance in thermal_distances.values()), thermal_distances
    cable_routes = tuple(
        name for name in geometry.keepouts if name.endswith("SectorCableRoute")
    )
    assert len(cable_routes) == 3
    cable_collisions: list[dict[str, object]] = []
    for route_name in cable_routes:
        route = geometry.keepouts[route_name]
        for component, shape in geometry.physical.items():
            if not _bounding_boxes_overlap(route, shape):
                continue
            intersection_mm3 = float(route.common(shape).Volume)
            if intersection_mm3 > 1.0e-6:
                cable_collisions.append(
                    {
                        "route": route_name,
                        "component": component,
                        "intersection_volume_mm3": intersection_mm3,
                    }
                )
    assert not cable_collisions, cable_collisions
    assert "left_CartridgeRemovalEnvelope" in geometry.keepouts

    return {
        "status": "pass",
        "sector": geometry.sector,
        "detector_count": len(geometry.placements),
        "physical_component_count": len(geometry.physical),
        "solid_count": len(compound.Solids),
        "bounding_box_mm": [
            float(compound.BoundBox.XLength),
            float(compound.BoundBox.YLength),
            float(compound.BoundBox.ZLength),
        ],
        "cassette_overlap_mm3": overlap_mm3,
        "acceptance_cone_obstructions": los_obstructions,
        "thermal_contact_distances_mm": thermal_distances,
        "cable_route_count": len(cable_routes),
        "cable_physical_collisions": cable_collisions,
    }


def test_internal_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    geometry = build_internal_assembly(cfg)
    compound = internal_compound(geometry)
    assert compound.isValid()
    assert len(geometry.placements) == 12
    assert set(geometry.cartridges) == {"left", "right", "up", "down"}
    assert len(geometry.target.motion_samples) == 19
    assert geometry.target.work.target_center.Length <= 1.0e-9
    assert (
        geometry.target.park.target_center - App.Vector(70.0, 0.0, 70.0)
    ).Length <= 1.0e-9

    cartridge_compounds = {
        sector: Part.makeCompound(list(cartridge.physical.values()))
        for sector, cartridge in geometry.cartridges.items()
    }
    intersector_overlap_mm3: dict[str, float] = {}
    sectors = tuple(cartridge_compounds)
    for index, sector_a in enumerate(sectors):
        for sector_b in sectors[index + 1 :]:
            key = f"{sector_a}<->{sector_b}"
            intersector_overlap_mm3[key] = float(
                cartridge_compounds[sector_a]
                .common(cartridge_compounds[sector_b])
                .Volume
            )
    assert all(volume <= 1.0e-6 for volume in intersector_overlap_mm3.values())

    target_motion_collisions: list[dict[str, object]] = []
    cartridge_physical = {
        name: shape
        for cartridge in geometry.cartridges.values()
        for name, shape in cartridge.physical.items()
    }
    for pose in geometry.target.motion_samples:
        for moving_name, moving_shape in pose.physical.items():
            motion_obstacles = {
                **cartridge_physical,
                **{
                    name: shape
                    for cartridge in geometry.cartridges.values()
                    for name, shape in cartridge.keepouts.items()
                    if name.endswith(("SectorCableRoute", "ConnectorKeepout"))
                },
            }
            for obstacle_name, obstacle_shape in motion_obstacles.items():
                if not _bounding_boxes_overlap(moving_shape, obstacle_shape):
                    continue
                intersection_mm3 = float(moving_shape.common(obstacle_shape).Volume)
                if intersection_mm3 > 1.0e-6:
                    target_motion_collisions.append(
                        {
                            "angle_deg": pose.angle_deg,
                            "moving_component": moving_name,
                            "obstacle": obstacle_name,
                            "intersection_volume_mm3": intersection_mm3,
                        }
                    )
    assert not target_motion_collisions, target_motion_collisions

    los_obstructions: list[dict[str, object]] = []
    for placement in geometry.placements:
        cone = build_active_acceptance_cone(cfg, placement)
        excluded = {
            f"{placement.tag}_ActivePlastic",
            "TargetWork_TargetFoil",
        }
        los_obstacles = {
            **geometry.physical,
            **{
                name: shape
                for cartridge in geometry.cartridges.values()
                for name, shape in cartridge.keepouts.items()
                if name.endswith(("SectorCableRoute", "ConnectorKeepout"))
            },
        }
        for component, shape in los_obstacles.items():
            if component in excluded or not _bounding_boxes_overlap(cone, shape):
                continue
            intersection_mm3 = float(cone.common(shape).Volume)
            if intersection_mm3 > 1.0e-6:
                los_obstructions.append(
                    {
                        "channel": placement.channel_name,
                        "sector": placement.sector_name,
                        "component": component,
                        "intersection_volume_mm3": intersection_mm3,
                    }
                )
    assert not los_obstructions, los_obstructions

    beam_radius_mm = 0.5 * cfg.compact_one.deployment.beam_stay_clear_diameter_mm
    beam_z_min_mm = cfg.vessel.center_z_mm - 0.5 * cfg.vessel.length_mm
    beam = Part.makeCylinder(
        beam_radius_mm,
        cfg.vessel.length_mm,
        App.Vector(0.0, 0.0, beam_z_min_mm),
    )
    target_support_beam_collisions: list[dict[str, object]] = []
    for pose in geometry.target.motion_samples:
        for name, shape in pose.physical.items():
            if name == "TargetFoil" or not _bounding_boxes_overlap(beam, shape):
                continue
            intersection_mm3 = float(beam.common(shape).Volume)
            if intersection_mm3 > 1.0e-6:
                target_support_beam_collisions.append(
                    {
                        "angle_deg": pose.angle_deg,
                        "component": name,
                        "intersection_volume_mm3": intersection_mm3,
                    }
                )
    assert not target_support_beam_collisions, target_support_beam_collisions

    return {
        "status": "pass",
        "detector_count": len(geometry.placements),
        "sector_count": len(geometry.cartridges),
        "physical_component_count": len(geometry.physical),
        "solid_count": len(compound.Solids),
        "motion_sample_count": len(geometry.target.motion_samples),
        "target_work_center_mm": list(geometry.target.work.target_center),
        "target_park_center_mm": list(geometry.target.park.target_center),
        "intersector_overlap_mm3": intersector_overlap_mm3,
        "target_motion_collisions": target_motion_collisions,
        "acceptance_cone_obstructions": los_obstructions,
        "target_support_beam_collisions": target_support_beam_collisions,
    }


def test_services_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    internal = build_internal_assembly(cfg)
    services = build_services(cfg, internal)
    assert len(services.fast_signal_paths) == 12
    assert len(services.temperature_harnesses) == 4
    assert len(services.grounding_connections) == 4
    assert all(
        not shape.isNull() and shape.isValid()
        for shape in (
            *services.physical.values(),
            *services.purchased_interfaces.values(),
            *services.keepouts.values(),
            *services.centerlines.values(),
        )
    )
    signal_capacity = (
        cfg.compact_one.services.signal_feedthrough_count
        * cfg.compact_one.services.channels_per_signal_feedthrough
    )
    housekeeping_required = (
        cfg.compact_one.services.temperature_channels
        * cfg.compact_one.services.wires_per_temperature_channel
    )
    assert signal_capacity >= cfg.compact_one.services.fast_signal_channels
    assert cfg.compact_one.services.housekeeping_pin_capacity >= housekeeping_required

    route_los_obstructions: list[dict[str, object]] = []
    route_physical_collisions: list[dict[str, object]] = []
    route_names = (
        *services.fast_signal_paths,
        *services.temperature_harnesses,
    )
    service_obstacles = {
        **internal.physical,
        **services.physical,
    }
    for route_name in route_names:
        route = services.keepouts[route_name]
        for component, shape in service_obstacles.items():
            if not _bounding_boxes_overlap(route, shape):
                continue
            intersection_mm3 = float(route.common(shape).Volume)
            if intersection_mm3 > 1.0e-6:
                route_physical_collisions.append(
                    {
                        "service": route_name,
                        "component": component,
                        "intersection_volume_mm3": intersection_mm3,
                    }
                )
    assert not route_physical_collisions, route_physical_collisions

    for placement in internal.placements:
        cone = build_active_acceptance_cone(cfg, placement)
        for route_name in route_names:
            route = services.keepouts[route_name]
            if not _bounding_boxes_overlap(cone, route):
                continue
            intersection_mm3 = float(cone.common(route).Volume)
            if intersection_mm3 > 1.0e-6:
                route_los_obstructions.append(
                    {
                        "channel": placement.tag,
                        "service": route_name,
                        "intersection_volume_mm3": intersection_mm3,
                    }
                )
    assert not route_los_obstructions, route_los_obstructions

    thermal = evaluate_thermal_paths(cfg, internal)
    assert thermal.status == "pass"
    assert len(thermal.channels) == 12
    assert all(item.connected for item in thermal.channels)

    return {
        "status": "pass",
        "port_count": len(services.ports),
        "fast_signal_path_count": len(services.fast_signal_paths),
        "signal_capacity": signal_capacity,
        "temperature_harness_count": len(services.temperature_harnesses),
        "housekeeping_required_pins": housekeeping_required,
        "housekeeping_capacity_pins": cfg.compact_one.services.housekeeping_pin_capacity,
        "grounding_connection_count": len(services.grounding_connections),
        "route_physical_collisions": route_physical_collisions,
        "route_acceptance_obstructions": route_los_obstructions,
        "thermal_connected_channel_count": sum(
            item.connected for item in thermal.channels
        ),
        "maximum_thermal_gap_mm": max(
            item.maximum_contact_gap_mm for item in thermal.channels
        ),
    }


def test_failure_regressions_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    internal = build_internal_assembly(cfg)
    placement = internal.placements[0]
    blocker_start = placement.direction * 60.0
    blocker = Part.makeCylinder(
        5.0,
        12.0,
        blocker_start,
        placement.direction,
    )
    blocked_los = find_acceptance_obstructions(
        cfg,
        [placement],
        {"DeliberateBlockingSupport": blocker},
    )
    assert blocked_los
    assert blocked_los[0]["obstructing_component"] == "DeliberateBlockingSupport"

    collision_blocker = Part.makeSphere(
        8.0,
        internal.target.park.target_center,
    )
    target_collisions = find_target_motion_collisions(
        internal.target,
        {"DeliberateParkCollision": collision_blocker},
    )
    assert target_collisions
    assert any(
        item["obstructing_component"] == "DeliberateParkCollision"
        for item in target_collisions
    )

    overlap_shape = Part.makeBox(10.0, 10.0, 10.0)
    cassette_overlap = find_pair_collisions(
        {
            "CassetteA": overlap_shape,
            "CassetteB": overlap_shape.copy(),
        }
    )
    assert cassette_overlap
    assert cassette_overlap[0]["intersection_volume_mm3"] > 0.0

    aftersrc_chamber = build_chamber(cfg)
    samurai_cfg = load_config(
        str(MODULE_ROOT / "config" / "infrontSamurai_compact.yaml")
    )
    samurai_chamber = build_chamber(samurai_cfg)
    assert aftersrc_chamber.candidate.cross_section == "cylindrical"
    assert samurai_chamber.candidate.cross_section == "square"
    assert aftersrc_chamber.vacuum_control_volume.isValid()
    assert samurai_chamber.vacuum_control_volume.isValid()

    return {
        "status": "pass",
        "blocked_los_failure_count": len(blocked_los),
        "target_motion_failure_count": len(target_collisions),
        "cassette_overlap_failure_count": len(cassette_overlap),
        "cylindrical_chamber_accepted": True,
        "square_chamber_accepted": True,
    }


def test_categorized_validation_runtime() -> dict[str, object]:
    cfg = load_config(str(MODULE_ROOT / "config" / "afterSRC_compact.yaml"))
    report = validate_compact_one(
        cfg,
        build_detector_placements(cfg),
        strict=False,
    )
    assert report["status"] == "pass"
    assert report["validation_mode"] == "prototype_non_strict"
    assert report["summary"]["fail_count"] == 0
    assert report["summary"]["warning_count"] > 0
    assert set(report["categories"]) == {
        "physics",
        "beamline",
        "detector",
        "sector_cartridge",
        "target",
        "LOS",
        "services",
        "vacuum",
        "mechanical",
        "thermal",
    }
    metrics = report["engineering_metrics"]
    assert len(metrics["detector_acceptance"]) == 12
    assert len(metrics["coincidence_geometry"]) == 8
    assert len(metrics["material_path_inventory"]) == 12
    assert {
        item["cross_section"] for item in metrics["chamber_candidates"]
    } == {"square", "cylindrical"}

    return {
        "status": "pass",
        "prototype_status": report["status"],
        "warning_count": report["summary"]["warning_count"],
        "category_count": len(report["categories"]),
        "detector_acceptance_count": len(metrics["detector_acceptance"]),
        "coincidence_geometry_count": len(metrics["coincidence_geometry"]),
        "material_inventory_count": len(metrics["material_path_inventory"]),
    }


def main() -> int:
    print(
        json.dumps(
            {
                "cassette": test_cassette_runtime(),
                "sector": test_sector_runtime(),
                "internal": test_internal_runtime(),
                "services": test_services_runtime(),
                "failure_regressions": test_failure_regressions_runtime(),
                "categorized_validation": test_categorized_validation_runtime(),
            },
            indent=2,
        )
    )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
