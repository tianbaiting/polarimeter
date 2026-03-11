from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable


def _tool_path(binary_name: str) -> str:
    env_name = "DPOLAR_BATCH" if binary_name == "dpol_batch" else "DPOLAR_TOOL"
    if env_name in os.environ:
        return os.environ[env_name]

    package_root = Path(__file__).resolve().parents[2]
    candidates = [
        package_root / "build" / binary_name,
        package_root / binary_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    resolved = shutil.which(binary_name)
    if resolved is None:
        raise FileNotFoundError(f"Unable to locate {binary_name}. Set {env_name} or build code_reco first.")
    return resolved


def _extend_args(arguments: list[str], option: str, value: str | None) -> None:
    if value is not None:
        arguments.extend([option, value])


def run(command: str, scenario_path: str | Path, output_dir: str | Path | None = None) -> subprocess.CompletedProcess[str]:
    scenario = str(Path(scenario_path).expanduser().resolve())
    if command == "full":
        arguments = [_tool_path("dpol_batch"), "--scenario", scenario, "--workflow", "full"]
        _extend_args(arguments, "--output-dir", None if output_dir is None else str(Path(output_dir).expanduser().resolve()))
    else:
        arguments = [_tool_path("dpol_tool"), command, "--scenario", scenario]
        _extend_args(arguments, "--output-dir", None if output_dir is None else str(Path(output_dir).expanduser().resolve()))
    return subprocess.run(arguments, check=True, text=True, capture_output=True)
