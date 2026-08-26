from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPOSITORY_ROOT / "scripts" / "plot_tensor_identifiability.py"
SPEC = importlib.util.spec_from_file_location("plot_tensor_identifiability", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
plotting = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = plotting
SPEC.loader.exec_module(plotting)


def test_figure_registry_contains_ten_unique_publication_outputs() -> None:
    stems = [definition.stem for definition in plotting.FIGURES]
    assert len(stems) == 10
    assert len(set(stems)) == 10
    assert stems[0].startswith("01_")
    assert stems[-1].startswith("10_")


def test_rotation_scan_parser_preserves_rank_singular_and_principal_angles(tmp_path: Path) -> None:
    path = tmp_path / "rotation_scan.csv"
    path.write_text(
        "rotation_axis,rotation_deg,raw_rank,effective_rank,smallest_singular,smallest_nonzero_singular,condition_number,fisher_pseudo_determinant,null_intersection_dimension,principal_angles_deg\n"
        'z,22.5,5,5,1.25,1.25,12.0,3.4e20,0,"45;70"\n',
        encoding="utf-8",
    )
    rows = plotting.load_rotation_scan(path)
    assert rows == [
        {
            "axis": "z",
            "angle_deg": 22.5,
            "raw_rank": 5,
            "effective_rank": 5,
            "smallest_singular": 1.25,
            "smallest_nonzero_singular": 1.25,
            "condition_number": 12.0,
            "fisher_pseudo_determinant": 3.4e20,
            "null_intersection_dimension": 0,
            "principal_angles_deg": [45.0, 70.0],
        }
    ]


def test_normalization_and_identifiability_helpers_handle_null_modes() -> None:
    normalized = plotting.normalized_singular_values({"singular_values": [8.0, 2.0, 0.0]})
    assert np.allclose(normalized, [1.0, 0.25, 0.0])
    assert plotting.parameter_identifiable({"one_sigma": [0.2, None], "parameter_identifiable": [True, False]}, 0)
    assert not plotting.parameter_identifiable({"one_sigma": [0.2, None], "parameter_identifiable": [True, False]}, 1)


def test_covariance_ellipse_uses_one_sigma_principal_axes() -> None:
    covariance = np.diag([4.0, 1.0])
    ellipse = plotting.covariance_ellipse(covariance, (0.0, 0.0), "blue", "case")
    assert np.isclose(ellipse.width, 4.0)
    assert np.isclose(ellipse.height, 2.0)
    plt.close("all")
