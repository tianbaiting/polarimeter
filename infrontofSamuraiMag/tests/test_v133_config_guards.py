"""v1.33: ClampConfig __post_init__ guards (spec §5.3)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ifsm.config import ConfigError, load_target


def _mutate_clamp(tmp_path: Path, **overrides):
    src = Path("infrontofSamuraiMag/config/default_infront.yaml")
    dst = tmp_path / "target.yaml"
    raw = yaml.safe_load(src.read_text())
    raw["geometry"]["detector"]["clamp"].update(overrides)
    dst.write_text(yaml.safe_dump(raw))
    return dst


def test_guard_plate_thickness_too_thin_for_csk(tmp_path: Path) -> None:
    # M4 csk needs plate_t >= 4.0 * 0.6 = 2.4 mm
    target = _mutate_clamp(tmp_path, plate_thickness_mm=2.0, clamp_bolt_diameter_mm=4.0)
    with pytest.raises(ConfigError, match="plate_thickness_mm"):
        load_target(target)


def test_guard_plate_thickness_passes_when_sufficient(tmp_path: Path) -> None:
    target = _mutate_clamp(tmp_path, plate_thickness_mm=10.0, clamp_bolt_diameter_mm=4.0)
    load_target(target)  # must not raise


def test_guard_csk_head_overruns_plate_width(tmp_path: Path) -> None:
    # 4.0 * 2.0 = 8.0 csk head; pitch 56 + 8 = 64 > 60 plate_width
    target = _mutate_clamp(
        tmp_path, plate_width_mm=60.0, clamp_bolt_pitch_w_mm=56.0,
        clamp_bolt_diameter_mm=4.0, countersink_head_factor=2.0,
    )
    with pytest.raises(ConfigError, match="countersink head"):
        load_target(target)


def test_guard_csk_head_fits_within_plate_width(tmp_path: Path) -> None:
    target = _mutate_clamp(
        tmp_path, plate_width_mm=60.0, clamp_bolt_pitch_w_mm=44.0,
        clamp_bolt_diameter_mm=4.0, countersink_head_factor=2.0,
    )
    load_target(target)


def test_guard_cradle_clearance_too_tight(tmp_path: Path) -> None:
    target = _mutate_clamp(tmp_path, cradle_clearance_mm=0.01)
    with pytest.raises(ConfigError, match="cradle_clearance_mm"):
        load_target(target)


def test_guard_cradle_clearance_too_loose(tmp_path: Path) -> None:
    target = _mutate_clamp(tmp_path, cradle_clearance_mm=1.0)
    with pytest.raises(ConfigError, match="cradle_clearance_mm"):
        load_target(target)


def test_guard_cradle_clearance_within_band(tmp_path: Path) -> None:
    target = _mutate_clamp(tmp_path, cradle_clearance_mm=0.1)
    load_target(target)


def test_guard_combined_bolt_length_exceeds_iso_lengths(tmp_path: Path) -> None:
    # combined: H/V plate_t (assume 8) + 2 * plate_t + 5; force it past 40 with thick plate
    # plate_t = 20 -> 8 + 40 + 5 = 53 > 40
    target = _mutate_clamp(tmp_path, plate_thickness_mm=20.0)
    with pytest.raises(ConfigError, match="ISO standard length"):
        load_target(target)


def test_guard_split_mode_bolt_length_within_iso_lengths(tmp_path: Path) -> None:
    # split: 2 * plate_t + 5 = 25 -> exact ISO length 25, passes
    target = _mutate_clamp(tmp_path, plate_thickness_mm=10.0, mount_mode="split")
    load_target(target)


def test_incomplete_v133_fixture_cannot_be_activated(tmp_path: Path) -> None:
    src = Path("infrontofSamuraiMag/config/default_infront.yaml")
    dst = tmp_path / "target.yaml"
    raw = yaml.safe_load(src.read_text())
    raw["geometry"]["detector"]["active_fixture"] = "v1_33_twin_plate"
    dst.write_text(yaml.safe_dump(raw))

    with pytest.raises(ConfigError, match="assembly and strict-validation coverage"):
        load_target(dst)
