from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ifsm.stateflow import (
    SUPPORTED_TARGET_SCHEMA_VERSION,
    load_pipeline_index,
    load_target_manifest,
    read_state_json,
    should_skip_build,
    target_sha256,
    write_state_json_atomic,
)

import pytest

pytestmark = pytest.mark.pure_python


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_target_hash_is_stable_for_key_order(tmp_path: Path) -> None:
    target_a = _write(
        tmp_path / "target_a.yaml",
        """
schema_version: 1
module: infrontofSamuraiMag
build:
  config: config/default_infront.yaml
  mode: build
  doc_name: infrontofSamuraiMag
  overrides: []
validation:
  strict: true
  angle_tolerance_deg: 0.05
  radius_tolerance_mm: 0.2
output:
  output_dir: .
  basename: infrontofSamuraiMag
  formats: [fcstd, step]
artifacts:
  report_json: report.json
intent:
  description: demo
""",
    )

    target_b = _write(
        tmp_path / "target_b.yaml",
        """
module: infrontofSamuraiMag
schema_version: 1
intent:
  description: demo
artifacts:
  report_json: report.json
output:
  formats: [fcstd, step]
  basename: infrontofSamuraiMag
  output_dir: .
validation:
  radius_tolerance_mm: 0.2
  angle_tolerance_deg: 0.05
  strict: true
build:
  overrides: []
  doc_name: infrontofSamuraiMag
  mode: build
  config: config/default_infront.yaml
""",
    )

    normalized_a = load_target_manifest(target_a, expected_module="infrontofSamuraiMag")
    normalized_b = load_target_manifest(target_b, expected_module="infrontofSamuraiMag")

    assert target_sha256(normalized_a) == target_sha256(normalized_b)


def test_load_pipeline_index_resolves_paths(tmp_path: Path) -> None:
    index = _write(
        tmp_path / "codex_targets.yaml",
        """
schema_version: 1
active_modules:
  - name: infrontofSamuraiMag
    target: infrontofSamuraiMag/target.yaml
    state: infrontofSamuraiMag/state.json
  - name: afterSRC
    target: afterSRC/target.yaml
    state: afterSRC/state.json
""",
    )

    entry = load_pipeline_index(index, module_name="infrontofSamuraiMag")

    assert entry["name"] == "infrontofSamuraiMag"
    assert Path(entry["target"]) == (tmp_path / "infrontofSamuraiMag" / "target.yaml").resolve()
    assert Path(entry["state"]) == (tmp_path / "infrontofSamuraiMag" / "state.json").resolve()


def test_load_pipeline_index_resolves_afterSRC_module_paths(tmp_path: Path) -> None:
    index = _write(
        tmp_path / "codex_targets.yaml",
        """
schema_version: 1
active_modules:
  - name: infrontofSamuraiMag
    target: infrontofSamuraiMag/target.yaml
    state: infrontofSamuraiMag/state.json
  - name: afterSRC
    target: afterSRC/target.yaml
    state: afterSRC/state.json
""",
    )

    entry = load_pipeline_index(index, module_name="afterSRC")

    assert entry["name"] == "afterSRC"
    assert Path(entry["target"]) == (tmp_path / "afterSRC" / "target.yaml").resolve()
    assert Path(entry["state"]) == (tmp_path / "afterSRC" / "state.json").resolve()


def test_should_skip_build_only_when_hash_status_and_artifacts_match(tmp_path: Path) -> None:
    artifact = tmp_path / "model.step"
    artifact.write_text("step", encoding="utf-8")

    state = {
        "schema_version": SUPPORTED_TARGET_SCHEMA_VERSION,
        "target": {"sha256": "abc123"},
        "run": {"status": "pass"},
        "artifacts": {
            "step": {
                "path": str(artifact),
                "exists": True,
            }
        },
    }

    assert should_skip_build(state, target_hash="abc123", force_rebuild=False)
    assert not should_skip_build(state, target_hash="other", force_rebuild=False)
    assert not should_skip_build(state, target_hash="abc123", force_rebuild=True)

    artifact.unlink()
    assert not should_skip_build(state, target_hash="abc123", force_rebuild=False)


def test_write_state_json_atomic_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    payload = {
        "schema_version": SUPPORTED_TARGET_SCHEMA_VERSION,
        "module": "infrontofSamuraiMag",
        "run": {"status": "pass"},
        "artifacts": {},
    }

    write_state_json_atomic(path, payload)
    loaded = read_state_json(path)

    assert loaded == payload
    assert json.loads(path.read_text(encoding="utf-8"))["run"]["status"] == "pass"
