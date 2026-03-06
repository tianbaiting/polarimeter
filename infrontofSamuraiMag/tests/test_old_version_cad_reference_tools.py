from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.pure_python

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_SCRIPT = REPO_ROOT / "scripts" / "cad_reference" / "build_old_version_step_manifest.py"


def test_manifest_generation_lists_all_old_version_solidworks_files(tmp_path: Path) -> None:
    output_path = tmp_path / "manifest.json"
    step_root = tmp_path / "step_pack"
    step_root.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            sys.executable,
            str(MANIFEST_SCRIPT),
            "--repo-root",
            str(REPO_ROOT),
            "--source-root",
            "old-version",
            "--step-root",
            str(step_root.relative_to(REPO_ROOT)) if step_root.is_relative_to(REPO_ROOT) else str(step_root),
            "--output",
            str(output_path),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    entries = payload["entries"]
    assert payload["summary"]["solidworks_files"] == 13
    assert len(entries) == 13
    assert payload["summary"]["step_present"] == 0
    assert payload["summary"]["step_missing"] == 13
    assert any(item["subsystem"] == "plates" for item in entries)
    assert any(item["subsystem"] == "detector" for item in entries)


def test_manifest_generation_fail_on_missing_step_returns_nonzero(tmp_path: Path) -> None:
    output_path = tmp_path / "manifest.json"
    step_root = tmp_path / "empty_step_pack"
    step_root.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            sys.executable,
            str(MANIFEST_SCRIPT),
            "--repo-root",
            str(REPO_ROOT),
            "--source-root",
            "old-version",
            "--step-root",
            str(step_root.relative_to(REPO_ROOT)) if step_root.is_relative_to(REPO_ROOT) else str(step_root),
            "--output",
            str(output_path),
            "--fail-on-missing-step",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
