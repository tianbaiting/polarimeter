from __future__ import annotations

import pathlib
import sys

import pytest


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from civ.config import config_dependency_paths, load_config
from civ.stateflow import compute_config_hash


CONFIG_DIR = pathlib.Path(__file__).parent.parent / "config"


def test_two_compact_deployment_profiles_load() -> None:
    aftersrc = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml"))
    samurai = load_config(str(CONFIG_DIR / "infrontSamurai_compact.yaml"))

    assert aftersrc.compact_one is not None
    assert samurai.compact_one is not None
    assert aftersrc.compact_one.deployment.name == "CompactOne-afterSRC"
    assert samurai.compact_one.deployment.name == "CompactOne-infrontSamurai"
    assert aftersrc.compact_one.deployment.external_route_module == "afterSRC"
    assert samurai.compact_one.deployment.external_route_module == "infrontofSamuraiMag"
    assert len(aftersrc.channels) * len(aftersrc.sectors) == 12
    assert len(samurai.channels) * len(samurai.sectors) == 12


def test_active_detector_is_separate_from_cassette() -> None:
    cfg = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml"))
    platform = cfg.compact_one
    assert platform is not None

    assert platform.detector.active.diameter_mm == 20.0
    assert platform.detector.active.thickness_mm == 5.5
    assert platform.detector.active.thickness_status == "recommended"
    assert platform.detector.sipm.model == "NDL EQR15 11-6060D-S"
    assert platform.detector.sipm.status == "recommended"
    assert platform.detector.cassette.outer_envelope_mm == (32.0, 32.0, 44.0)
    assert platform.detector.cassette.outer_envelope_mm[2] > platform.detector.active.thickness_mm


def test_square_and_cylindrical_candidates_are_real_choices() -> None:
    aftersrc = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml")).compact_one
    samurai = load_config(str(CONFIG_DIR / "infrontSamurai_compact.yaml")).compact_one
    assert aftersrc is not None
    assert samurai is not None

    assert {item.cross_section for item in aftersrc.deployment.chamber_candidates} == {
        "square",
        "cylindrical",
    }
    assert {item.cross_section for item in samurai.deployment.chamber_candidates} == {
        "square",
        "cylindrical",
    }
    assert aftersrc.deployment.chamber.cross_section == "cylindrical"
    assert samurai.deployment.chamber.cross_section == "square"


def test_inherited_config_dependencies_are_hashed(tmp_path: pathlib.Path) -> None:
    base = tmp_path / "base.yaml"
    child = tmp_path / "child.yaml"
    base.write_text("value: 1\n", encoding="utf-8")
    child.write_text("extends: base.yaml\nchild: true\n", encoding="utf-8")

    assert config_dependency_paths(child) == (base.resolve(), child.resolve())
    first_hash = compute_config_hash(str(child), {})
    base.write_text("value: 2\n", encoding="utf-8")
    second_hash = compute_config_hash(str(child), {})
    assert first_hash != second_hash


def test_unknown_decision_state_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be one of"):
        load_config(
            str(CONFIG_DIR / "afterSRC_compact.yaml"),
            overrides={"detector.active.material_status": "selected"},
        )


def test_purchased_interface_and_project_transition_are_separate() -> None:
    cfg = load_config(str(CONFIG_DIR / "afterSRC_compact.yaml"))
    deployment = cfg.compact_one.deployment
    interface = deployment.front_interface

    assert interface.status == "purchased-part-contract"
    assert interface.certified_drawing_reference == "unresolved"
    assert interface.transition_status == "provisional"
    assert interface.transition_outer_diameter_mm > interface.transition_inner_diameter_mm
    assert (interface.transition_outer_diameter_mm - interface.transition_inner_diameter_mm) / 2.0 > 0.30
