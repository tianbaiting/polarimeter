from __future__ import annotations

import importlib.util

import pytest


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def pytest_sessionstart(session: pytest.Session) -> None:
    missing: list[str] = []
    if not _has_module("yaml"):
        missing.append("PyYAML (module: yaml)")
    if missing:
        joined = ", ".join(missing)
        raise pytest.UsageError(f"Missing required test dependencies: {joined}")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _has_module("FreeCAD"):
        return
    skip_freecad = pytest.mark.skip(reason="FreeCAD runtime dependency is missing for freecad_runtime tests")
    for item in items:
        if "freecad_runtime" in item.keywords:
            item.add_marker(skip_freecad)
