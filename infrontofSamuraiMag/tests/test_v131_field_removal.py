"""v1.33: legacy v1.31 ClampConfig fields must trigger a clear ConfigError.

The v1.31 dataclass carried 24 clamp fields plus a separate adapter_block
sub-section. v1.33 removes both. Profiles still carrying any legacy field
should fail loudly with a message that names the offending field, so a
human catches stale YAML during migration.
"""
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

LEGACY_CLAMP_FIELDS = [
    "outer_diameter_mm",
    "inner_diameter_mm",
    "width_mm",
    "split_gap_mm",
    "shoulder_height_mm",
    "end_stop_length_mm",
    "clamp_ear_length_mm",
    "clamp_ear_thickness_mm",
    "anti_rotation_key_width_mm",
    "support_overlap_mm",
    "mount_base_u_mm",
    "mount_base_thickness_mm",
    "mount_bolt_hole_diameter_mm",
    "fillet_radius_mm",
    "bolt_head_type",
]


def _baseline_target(tmp_path: Path) -> Path:
    """Copy default_infront.yaml into tmp_path so we can mutate without polluting repo."""
    src = Path("infrontofSamuraiMag/config/default_infront.yaml")
    dst = tmp_path / "target.yaml"
    dst.write_text(src.read_text())
    return dst


@pytest.mark.parametrize("field", LEGACY_CLAMP_FIELDS)
def test_legacy_clamp_field_rejected(tmp_path: Path, field: str) -> None:
    target = _baseline_target(tmp_path)
    raw = yaml.safe_load(target.read_text())
    raw["geometry"]["detector"]["clamp"][field] = 1.0
    target.write_text(yaml.safe_dump(raw))

    with pytest.raises(ConfigError) as excinfo:
        load_target(target)

    assert field in str(excinfo.value), f"error message must name the offending field {field!r}"


def test_legacy_adapter_block_subsection_rejected(tmp_path: Path) -> None:
    target = _baseline_target(tmp_path)
    raw = yaml.safe_load(target.read_text())
    raw["geometry"]["detector"]["adapter_block"] = {"length_mm": 30.0, "width_mm": 30.0}
    target.write_text(yaml.safe_dump(raw))

    with pytest.raises(ConfigError) as excinfo:
        load_target(target)

    assert "adapter_block" in str(excinfo.value)
