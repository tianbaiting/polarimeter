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
from civ.config import load_config
from civ.detector import build_active_acceptance_cone
from civ.layout import build_detector_placements


def _distance_mm(shape_a: Part.Shape, shape_b: Part.Shape) -> float:
    return float(shape_a.distToShape(shape_b)[0])


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
    }


def main() -> int:
    print(
        json.dumps(
            {
                "cassette": test_cassette_runtime(),
                "sector": test_sector_runtime(),
            },
            indent=2,
        )
    )
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
