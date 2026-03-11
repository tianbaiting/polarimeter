from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ScenarioHandle:
    path: Path
    parser: configparser.ConfigParser


def load(path: str | Path) -> ScenarioHandle:
    scenario_path = Path(path).expanduser().resolve()
    parser = configparser.ConfigParser()
    parser.read(scenario_path, encoding="utf-8")
    return ScenarioHandle(path=scenario_path, parser=parser)
