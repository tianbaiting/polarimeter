#!/usr/bin/env python3
"""Generate publication figures for tensor-polarization identifiability / 生成张量极化可识别性的发表级图件。"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch
import numpy as np


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TOOL = REPOSITORY_ROOT / "code" / "build-tensor" / "dpol_tool"
DEFAULT_SCENARIO = REPOSITORY_ROOT / "code" / "config" / "current_tensor.ini"
PHYSICAL_LABELS = [
    r"$p_{xx}-p_{yy}$",
    r"$p_{xy}$",
    r"$p_{xz}$",
    r"$p_{yz}$",
    r"$p_{zz}$",
]
NOMINAL_LABELS = [r"$P_T$", r"tilt $x$ (rad)", r"tilt $z$ (rad)"]
AXIS_COLORS = {"x": "#0072B2", "y": "#D55E00", "z": "#009E73"}


@dataclass(frozen=True)
class StudyInputs:
    one_known: dict[str, Any]
    one_global: dict[str, Any]
    one_theta_known: dict[str, Any]
    one_theta_global: dict[str, Any]
    two_station: dict[str, Any]
    nominal_one: dict[str, Any]
    nominal_two: dict[str, Any]
    rotation_scans: dict[str, list[dict[str, Any]]]
    data_root: Path


@dataclass(frozen=True)
class FigureDefinition:
    stem: str
    caption: str


FIGURES = (
    FigureDefinition(
        "01_one_station_singular_spectrum",
        "One planned two-angle proton-singles station has one exact structural tensor null mode; singular values are normalized to the leading response mode.",
    ),
    FigureDefinition(
        "02_one_station_null_directions",
        "Physical Cartesian content of the one-station null basis. The ideal cardinal L/R/U/D geometry is insensitive to pxy.",
    ),
    FigureDefinition(
        "03_one_theta_vs_multi_theta",
        "A second polar-angle group changes the analyzing-power dependence and restores one polarization mode after global-normalization profiling.",
    ),
    FigureDefinition(
        "04_normalization_profile_comparison",
        "At one polar angle, profiling an unknown global normalization removes the common tensor mode that is available with known absolute normalization.",
    ),
    FigureDefinition(
        "05_one_vs_two_station_singular_spectrum",
        "A second station with a generic 22.5 degree z-axis spin rotation lifts the cardinal-ring pxy null direction; this is not a RIBF beamline prediction.",
    ),
    FigureDefinition(
        "06_effective_rank_rotation_scan",
        "Effective polarization rank versus a generic relative spin rotation. Rank gain depends on whether transport rotates a station null direction into an observable direction.",
    ),
    FigureDefinition(
        "07_smallest_singular_rotation_scan",
        "Smallest response singular value versus generic relative spin rotation. These sweeps are mathematical sensitivity studies, not RIBF transport predictions.",
    ),
    FigureDefinition(
        "08_current_fisher_and_correlation",
        "Profiled Fisher information and pseudoinverse correlation for the planned two-angle proton-singles response with global normalization treated as a nuisance.",
    ),
    FigureDefinition(
        "09_nominal_pyy_fisher_ellipses",
        "Local one-sigma covariance projections around nominal pure pyy. A generic transport-complementary second station recovers the first-order tilt direction missing at one station.",
    ),
    FigureDefinition(
        "10_null_space_intersection_schematic",
        "The combined null space is the intersection of transported station null spaces. An aligned duplicate improves counts but not rank; a complementary rotation can reduce the intersection.",
    ),
)


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 10.5,
            "axes.labelsize": 11,
            "axes.titlesize": 12,
            "legend.fontsize": 9.5,
            "xtick.labelsize": 9.5,
            "ytick.labelsize": 9.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.7,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "savefig.bbox": "tight",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def run_cli(
    tool: Path,
    scenario: Path,
    command: str,
    output_dir: Path,
    options: Iterable[str],
    reuse_data: bool,
    expected_file: str = "summary.json",
) -> Path:
    expected = output_dir / expected_file
    if reuse_data and expected.exists():
        return expected
    output_dir.mkdir(parents=True, exist_ok=True)
    arguments = [
        str(tool),
        command,
        "--scenario",
        str(scenario),
        "--output-dir",
        str(output_dir),
        *options,
    ]
    result = subprocess.run(arguments, cwd=REPOSITORY_ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"dpol_tool failed for {command} ({output_dir.name})\n"
            f"command: {' '.join(arguments)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if not expected.exists():
        raise RuntimeError(f"dpol_tool did not create expected output: {expected}")
    return expected


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def load_rotation_scan(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as stream:
        for raw in csv.DictReader(stream):
            principal = [float(value) for value in raw["principal_angles_deg"].split(";") if value]
            rows.append(
                {
                    "axis": raw["rotation_axis"],
                    "angle_deg": float(raw["rotation_deg"]),
                    "raw_rank": int(raw["raw_rank"]),
                    "effective_rank": int(raw["effective_rank"]),
                    "smallest_singular": float(raw.get("smallest_singular", raw["smallest_nonzero_singular"])),
                    "smallest_nonzero_singular": float(raw["smallest_nonzero_singular"]),
                    "condition_number": float(raw["condition_number"]),
                    "fisher_pseudo_determinant": float(raw["fisher_pseudo_determinant"]),
                    "null_intersection_dimension": int(raw["null_intersection_dimension"]),
                    "principal_angles_deg": principal,
                }
            )
    if not rows:
        raise ValueError(f"Rotation scan is empty: {path}")
    return rows


def generate_inputs(tool: Path, scenario: Path, data_root: Path, reuse_data: bool) -> StudyInputs:
    common = ["--selection", "current"]
    one_known = load_json(
        run_cli(tool, scenario, "rank", data_root / "one_known", [*common, "--normalization", "known"], reuse_data)
    )
    one_global = load_json(
        run_cli(tool, scenario, "fisher", data_root / "one_global", [*common, "--normalization", "global"], reuse_data)
    )
    one_theta_known = load_json(
        run_cli(
            tool,
            scenario,
            "rank",
            data_root / "one_theta_known",
            ["--selection", "one-theta", "--normalization", "known"],
            reuse_data,
        )
    )
    one_theta_global = load_json(
        run_cli(
            tool,
            scenario,
            "fisher",
            data_root / "one_theta_global",
            ["--selection", "one-theta", "--normalization", "global"],
            reuse_data,
        )
    )
    complementary = [*common, "--normalization", "global", "--rotation-axis", "z", "--rotation-deg", "22.5"]
    two_station = load_json(
        run_cli(tool, scenario, "two-station", data_root / "two_station_z22p5", complementary, reuse_data)
    )
    nominal_one = load_json(
        run_cli(
            tool,
            scenario,
            "nominal-pyy",
            data_root / "nominal_pyy_one",
            [*common, "--normalization", "global", "--stations", "1", "--nominal-pyy", "0.8"],
            reuse_data,
        )
    )
    nominal_two = load_json(
        run_cli(
            tool,
            scenario,
            "nominal-pyy",
            data_root / "nominal_pyy_two_z22p5",
            [*complementary, "--stations", "2", "--nominal-pyy", "0.8"],
            reuse_data,
        )
    )
    rotation_scans: dict[str, list[dict[str, Any]]] = {}
    for axis in "xyz":
        scan_path = run_cli(
            tool,
            scenario,
            "rotation-scan",
            data_root / f"rotation_scan_{axis}",
            [
                *common,
                "--normalization",
                "global",
                "--rotation-axis",
                axis,
                "--rotation-step-deg",
                "2",
            ],
            reuse_data,
            expected_file="rotation_scan.csv",
        )
        rotation_scans[axis] = load_rotation_scan(scan_path)
    return StudyInputs(
        one_known=one_known,
        one_global=one_global,
        one_theta_known=one_theta_known,
        one_theta_global=one_theta_global,
        two_station=two_station,
        nominal_one=nominal_one,
        nominal_two=nominal_two,
        rotation_scans=rotation_scans,
        data_root=data_root,
    )


def save_figure(fig: plt.Figure, output_dir: Path, definition: FigureDefinition) -> list[Path]:
    fig.text(0.5, 0.005, definition.caption, ha="center", va="bottom", fontsize=8.5, wrap=True)
    fig.subplots_adjust(bottom=0.17)
    paths = [output_dir / f"{definition.stem}.png", output_dir / f"{definition.stem}.pdf"]
    for path in paths:
        fig.savefig(path)
    plt.close(fig)
    return paths


def normalized_singular_values(summary: dict[str, Any], key: str = "singular_values") -> np.ndarray:
    values = np.asarray(summary[key], dtype=float)
    maximum = float(np.max(values)) if values.size else 0.0
    return values / maximum if maximum > 0.0 else values


def positive_plot_values(values: np.ndarray, floor: float = 1.0e-14) -> np.ndarray:
    output = np.asarray(values, dtype=float).copy()
    output[~np.isfinite(output)] = np.nan
    output[output <= 0.0] = floor
    return output


def figure_one_station_spectrum(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    definition = FIGURES[0]
    singular = normalized_singular_values(inputs.one_known)
    modes = np.arange(1, len(singular) + 1)
    threshold = float(inputs.one_known["rank_threshold"]["applied"]) / float(inputs.one_known["singular_values"][0])
    fig, ax = plt.subplots(figsize=(7.2, 4.7))
    ax.semilogy(modes, positive_plot_values(singular), "o-", color="#0072B2", linewidth=2.2, markersize=7)
    ax.axhline(max(threshold, 1.0e-14), color="#CC79A7", linestyle="--", label="rank threshold")
    ax.set(
        xlabel="Tensor response mode index",
        ylabel=r"Normalized singular value $\sigma_i/\sigma_1$",
        xticks=modes,
        ylim=(5.0e-15, 2.0),
        title="Planned proton-singles one-station tensor response",
    )
    ax.text(0.97, 0.93, f"raw rank = {inputs.one_known['raw_rank']} / 5", transform=ax.transAxes, ha="right", va="top")
    ax.legend(loc="lower left")
    return save_figure(fig, output_dir, definition)


def figure_null_directions(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    definition = FIGURES[1]
    nulls = inputs.one_known["null_directions"]
    if not nulls:
        raise ValueError("One-station report contains no tensor null directions")
    matrix = np.asarray([item["physical"] for item in nulls], dtype=float)
    row_scale = np.max(np.abs(matrix), axis=1, keepdims=True)
    matrix = np.divide(matrix, row_scale, out=np.zeros_like(matrix), where=row_scale > 0.0)
    fig, ax = plt.subplots(figsize=(8.0, 2.6 + 0.55 * len(nulls)))
    image = ax.imshow(matrix, cmap="RdBu_r", vmin=-1.0, vmax=1.0, aspect="auto")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            ax.text(column, row, f"{matrix[row, column]:+.3f}", ha="center", va="center", color="white" if abs(matrix[row, column]) > 0.55 else "black")
    ax.set_xticks(np.arange(5), PHYSICAL_LABELS)
    ax.set_yticks(np.arange(len(nulls)), [f"null {index + 1}" for index in range(len(nulls))])
    ax.set_xlabel("Physical Cartesian tensor component")
    ax.set_ylabel("Right-null basis vector")
    ax.set_title("Physical interpretation of one-station tensor null space")
    colorbar = fig.colorbar(image, ax=ax, pad=0.02)
    colorbar.set_label("Component / largest absolute component")
    return save_figure(fig, output_dir, definition)


def figure_theta_comparison(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    definition = FIGURES[2]
    cases = [inputs.one_theta_global, inputs.one_global]
    labels = ["one polar angle", "two proton angles"]
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.5), gridspec_kw={"width_ratios": [0.9, 1.35]})
    raw = [case["raw_rank"] for case in cases]
    effective = [case["effective_rank"] for case in cases]
    x = np.arange(2)
    axes[0].bar(x - 0.18, raw, width=0.36, color="#999999", label="raw response")
    axes[0].bar(x + 0.18, effective, width=0.36, color="#0072B2", label="profiled Fisher")
    axes[0].set(xticks=x, xticklabels=labels, ylabel="Numerical rank", ylim=(0, 5.5), title="Rank after normalization profiling")
    axes[0].legend(loc="lower right")
    for case, label, color, marker in zip(cases, labels, ("#D55E00", "#009E73"), ("s", "o"), strict=True):
        singular = normalized_singular_values(case, "effective_singular_values")
        axes[1].semilogy(np.arange(1, 6), positive_plot_values(singular), marker=marker, linewidth=2, color=color, label=label)
    axes[1].set(
        xlabel="Profiled Fisher mode index",
        ylabel=r"Normalized information singular value",
        xticks=np.arange(1, 6),
        ylim=(5.0e-15, 2.0),
        title="Profiled information spectrum",
    )
    axes[1].legend()
    return save_figure(fig, output_dir, definition)


def figure_normalization_comparison(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    definition = FIGURES[3]
    cases = [inputs.one_theta_known, inputs.one_theta_global]
    labels = ["known absolute normalization", "profiled global normalization"]
    colors = ["#0072B2", "#D55E00"]
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    for case, label, color in zip(cases, labels, colors, strict=True):
        singular = normalized_singular_values(case, "effective_singular_values")
        ax.semilogy(np.arange(1, 6), positive_plot_values(singular), "o-", linewidth=2.1, markersize=6, label=f"{label} (rank {case['effective_rank']})", color=color)
    ax.set(
        xlabel="Profiled Fisher mode index",
        ylabel="Normalized information singular value",
        xticks=np.arange(1, 6),
        ylim=(5.0e-15, 2.0),
        title="Single-angle normalization degeneracy",
    )
    ax.legend(loc="lower left")
    return save_figure(fig, output_dir, definition)


def figure_station_comparison(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    definition = FIGURES[4]
    one = np.asarray(inputs.one_global["singular_values"], dtype=float)
    two = np.asarray(inputs.two_station["singular_values"], dtype=float)
    scale = max(float(one[0]), float(two[0]))
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    ax.semilogy(np.arange(1, 6), positive_plot_values(one / scale), "o-", linewidth=2.1, color="#0072B2", label=f"one station (rank {inputs.one_global['raw_rank']})")
    ax.semilogy(np.arange(1, 6), positive_plot_values(two / scale), "s-", linewidth=2.1, color="#009E73", label=rf"two stations, generic $R_z(22.5^\circ)$ (rank {inputs.two_station['raw_rank']})")
    ax.set(
        xlabel="Combined-response mode index",
        ylabel="Singular value / largest compared singular value",
        xticks=np.arange(1, 6),
        ylim=(5.0e-15, 2.0),
        title="Structural information from one versus two stations",
    )
    ax.legend(loc="lower left")
    ax.text(0.98, 0.93, "generic sensitivity case\nnot a RIBF transfer prediction", transform=ax.transAxes, ha="right", va="top", fontsize=9)
    return save_figure(fig, output_dir, definition)


def figure_rotation_rank(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    definition = FIGURES[5]
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    for axis, rows in inputs.rotation_scans.items():
        angle = [row["angle_deg"] for row in rows]
        rank = [row["effective_rank"] for row in rows]
        ax.step(angle, rank, where="mid", linewidth=2.1, color=AXIS_COLORS[axis], label=rf"generic $R_{axis}(\alpha)$")
    ax.set(
        xlabel=r"Relative tensor spin rotation $\alpha$ (deg)",
        ylabel="Effective polarization rank",
        xlim=(0, 180),
        ylim=(-0.1, 5.4),
        yticks=np.arange(0, 6),
        title="When does a second station add identifiable dimensions?",
    )
    ax.legend(ncol=3, loc="lower center")
    ax.text(0.98, 0.08, "generic sensitivity sweep; not a RIBF prediction", transform=ax.transAxes, ha="right", fontsize=8.8)
    return save_figure(fig, output_dir, definition)


def figure_rotation_smallest_singular(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    definition = FIGURES[6]
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    global_scale = max(row["smallest_singular"] for rows in inputs.rotation_scans.values() for row in rows)
    for axis, rows in inputs.rotation_scans.items():
        angle = np.asarray([row["angle_deg"] for row in rows])
        values = np.asarray([row["smallest_singular"] for row in rows]) / global_scale
        ax.semilogy(angle, positive_plot_values(values), linewidth=2.1, color=AXIS_COLORS[axis], label=rf"generic $R_{axis}(\alpha)$")
    ax.set(
        xlabel=r"Relative tensor spin rotation $\alpha$ (deg)",
        ylabel="Smallest singular value / scan maximum",
        xlim=(0, 180),
        title="Conditioning of complementary two-station response",
    )
    ax.legend(ncol=3)
    ax.text(0.98, 0.08, "generic sensitivity sweep; not a RIBF prediction", transform=ax.transAxes, ha="right", fontsize=8.8)
    return save_figure(fig, output_dir, definition)


def symmetric_log_scale(matrix: np.ndarray) -> np.ndarray:
    diagonal = np.sqrt(np.maximum(np.diag(matrix), 0.0))
    denominator = np.outer(diagonal, diagonal)
    normalized = np.divide(matrix, denominator, out=np.zeros_like(matrix), where=denominator > 0.0)
    return np.sign(normalized) * np.log10(1.0 + 9.0 * np.abs(normalized))


def annotated_heatmap(ax: plt.Axes, matrix: np.ndarray, labels: list[str], title: str, colorbar_label: str) -> Any:
    image = ax.imshow(matrix, cmap="RdBu_r", vmin=-1.0, vmax=1.0)
    ax.set_xticks(np.arange(len(labels)), labels, rotation=38, ha="right")
    ax.set_yticks(np.arange(len(labels)), labels)
    ax.set_title(title)
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            ax.text(column, row, f"{matrix[row, column]:+.2f}", ha="center", va="center", fontsize=8, color="white" if abs(matrix[row, column]) > 0.55 else "black")
    return image, colorbar_label


def figure_fisher_correlation(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    definition = FIGURES[7]
    fisher = np.asarray(inputs.one_global["fisher_profiled"], dtype=float)
    correlation = np.asarray(inputs.one_global["correlation"], dtype=float)
    fisher_display = symmetric_log_scale(fisher)
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.9))
    fisher_image, fisher_label = annotated_heatmap(
        axes[0], fisher_display, PHYSICAL_LABELS, "Profiled Fisher information", "signed log-normalized Fisher"
    )
    correlation_image, correlation_label = annotated_heatmap(
        axes[1], correlation, PHYSICAL_LABELS, "Pseudoinverse correlation", "correlation coefficient"
    )
    first_bar = fig.colorbar(fisher_image, ax=axes[0], fraction=0.046, pad=0.04)
    first_bar.set_label(fisher_label)
    second_bar = fig.colorbar(correlation_image, ax=axes[1], fraction=0.046, pad=0.04)
    second_bar.set_label(correlation_label)
    fig.subplots_adjust(wspace=0.48)
    fig.suptitle("Planned two-angle proton singles: global normalization profiled", y=0.99)
    return save_figure(fig, output_dir, definition)


def covariance_ellipse(covariance: np.ndarray, center: tuple[float, float], color: str, label: str) -> Ellipse:
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = np.maximum(eigenvalues[order], 0.0)
    eigenvectors = eigenvectors[:, order]
    angle = math.degrees(math.atan2(eigenvectors[1, 0], eigenvectors[0, 0]))
    return Ellipse(
        center,
        width=2.0 * math.sqrt(eigenvalues[0]),
        height=2.0 * math.sqrt(eigenvalues[1]),
        angle=angle,
        facecolor=color,
        edgecolor=color,
        alpha=0.22,
        linewidth=2.0,
        label=label,
    )


def parameter_identifiable(summary: dict[str, Any], index: int) -> bool:
    if "parameter_identifiable" in summary:
        return bool(summary["parameter_identifiable"][index])
    raw_value = summary["one_sigma"][index]
    return raw_value is not None and math.isfinite(float(raw_value)) and float(raw_value) > 0.0


def figure_nominal_pyy(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    definition = FIGURES[8]
    pairs = [(0, 1), (0, 2), (1, 2)]
    covariance_one = np.asarray(inputs.nominal_one["covariance_pseudoinverse"], dtype=float)
    covariance_two = np.asarray(inputs.nominal_two["covariance_pseudoinverse"], dtype=float)
    fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.3))
    for ax, (first, second) in zip(axes, pairs, strict=True):
        plotted = False
        if parameter_identifiable(inputs.nominal_one, first) and parameter_identifiable(inputs.nominal_one, second):
            block = covariance_one[np.ix_([first, second], [first, second])]
            ax.add_patch(covariance_ellipse(block, (0.0, 0.0), "#0072B2", "one station"))
            plotted = True
        else:
            ax.text(0.04, 0.93, "one station:\nstructurally unidentifiable", transform=ax.transAxes, ha="left", va="top", color="#0072B2", fontsize=8.5)
        if parameter_identifiable(inputs.nominal_two, first) and parameter_identifiable(inputs.nominal_two, second):
            block = covariance_two[np.ix_([first, second], [first, second])]
            ax.add_patch(covariance_ellipse(block, (0.0, 0.0), "#009E73", "two stations"))
            plotted = True
        if plotted:
            ax.relim()
            ax.autoscale_view()
            x_limit = max(abs(value) for value in ax.get_xlim()) * 1.25
            y_limit = max(abs(value) for value in ax.get_ylim()) * 1.25
            ax.set_xlim(-x_limit, x_limit)
            ax.set_ylim(-y_limit, y_limit)
        else:
            ax.set_xlim(-1.0, 1.0)
            ax.set_ylim(-1.0, 1.0)
        ax.axhline(0.0, color="#555555", linewidth=0.7)
        ax.axvline(0.0, color="#555555", linewidth=0.7)
        ax.set_xlabel(rf"$\Delta$ {NOMINAL_LABELS[first]}")
        ax.set_ylabel(rf"$\Delta$ {NOMINAL_LABELS[second]}")
        ax.set_title(f"{NOMINAL_LABELS[first]} vs {NOMINAL_LABELS[second]}")
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, loc="best")
    fig.suptitle(r"Local covariance around nominal vertical $p_{yy}=0.8$", y=1.0)
    return save_figure(fig, output_dir, definition)


def add_arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str = "#444444") -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13, linewidth=1.8, color=color))


def figure_null_intersection(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    definition = FIGURES[9]
    null_label = PHYSICAL_LABELS[int(np.argmax(np.abs(np.asarray(inputs.one_known["null_directions"][0]["physical"]))))]
    combined_rank = inputs.two_station["raw_rank"]
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.5))
    for ax in axes:
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.0)
        ax.axis("off")
    axes[0].plot([0.14, 0.86], [0.30, 0.70], color="#0072B2", linewidth=8, solid_capstyle="round", label=r"$\mathcal{N}_1$")
    axes[0].plot([0.14, 0.86], [0.30, 0.70], color="#D55E00", linewidth=3, linestyle="--", label=r"$\mathcal{N}_2$")
    axes[0].text(0.50, 0.80, "aligned null spaces", ha="center", fontsize=11)
    axes[0].text(0.50, 0.16, "same structural rank\nmore Fisher information", ha="center", color="#555555")
    axes[0].set_title("Identity/aligned transport")
    axes[0].legend(loc="lower right")
    axes[1].plot([0.13, 0.87], [0.28, 0.72], color="#0072B2", linewidth=7, solid_capstyle="round", label=r"$\mathcal{N}_1$")
    axes[1].plot([0.18, 0.82], [0.78, 0.22], color="#009E73", linewidth=7, solid_capstyle="round", label=r"$\mathcal{N}_2$")
    axes[1].scatter([0.5], [0.5], s=90, color="#CC79A7", zorder=5, label="intersection")
    add_arrow(axes[1], (0.72, 0.88), (0.64, 0.70), "#009E73")
    axes[1].text(0.74, 0.91, r"generic $T^{(2)}(R)$", ha="center", color="#009E73")
    axes[1].text(0.50, 0.12, f"intersection nullity = {5 - combined_rank}\ncombined raw rank = {combined_rank}", ha="center", color="#555555")
    axes[1].set_title("Transport-complementary station")
    axes[1].legend(loc="upper left")
    fig.suptitle(rf"$\ker J_{{\rm combined}}=\ker(J_1T_1)\cap\ker(J_2T_2)$; one-station null dominated by {null_label}", y=0.99)
    fig.text(0.5, 0.075, "Generic rotation illustration only; an actual beamline conclusion requires a measured or calculated spin-transfer map.", ha="center", color="#7A3E00", fontsize=9)
    return save_figure(fig, output_dir, definition)


def render_all(inputs: StudyInputs, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    configure_style()
    renderers = (
        figure_one_station_spectrum,
        figure_null_directions,
        figure_theta_comparison,
        figure_normalization_comparison,
        figure_station_comparison,
        figure_rotation_rank,
        figure_rotation_smallest_singular,
        figure_fisher_correlation,
        figure_nominal_pyy,
        figure_null_intersection,
    )
    generated: list[Path] = []
    for renderer in renderers:
        generated.extend(renderer(inputs, output_dir))
    return generated


def write_manifest(output_dir: Path, inputs: StudyInputs, generated: list[Path], tool: Path, scenario: Path) -> Path:
    manifest = {
        "schema_version": 1,
        "scenario": "current_tensor",
        "scenario_path": str(scenario),
        "dpol_tool": str(tool),
        "data_root": str(inputs.data_root),
        "rotation_study_label": "generic sensitivity study; not a RIBF beamline prediction",
        "figures": [
            {
                "stem": definition.stem,
                "caption": definition.caption,
                "png": str(output_dir / f"{definition.stem}.png"),
                "pdf": str(output_dir / f"{definition.stem}.pdf"),
            }
            for definition in FIGURES
        ],
        "generated_files": [str(path) for path in generated],
    }
    path = output_dir / "figure_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for the ten PDF and PNG figures")
    parser.add_argument("--tool", type=Path, default=DEFAULT_TOOL, help="Path to the tensor-enabled dpol_tool executable")
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO, help="Path to the current_tensor INI scenario")
    parser.add_argument("--data-dir", type=Path, help="Directory for CLI JSON/CSV inputs; defaults to OUTPUT_DIR/data")
    parser.add_argument("--reuse-data", action="store_true", help="Reuse existing CLI outputs when present")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    output_dir = arguments.output_dir.expanduser().resolve()
    data_root = (arguments.data_dir or output_dir / "data").expanduser().resolve()
    tool = arguments.tool.expanduser().resolve()
    scenario = arguments.scenario.expanduser().resolve()
    if not tool.is_file():
        raise FileNotFoundError(f"Tensor-enabled dpol_tool was not found: {tool}")
    if not scenario.is_file():
        raise FileNotFoundError(f"current_tensor scenario was not found: {scenario}")
    inputs = generate_inputs(tool, scenario, data_root, arguments.reuse_data)
    generated = render_all(inputs, output_dir)
    manifest = write_manifest(output_dir, inputs, generated, tool, scenario)
    print(f"Generated {len(FIGURES)} figures as PDF+PNG in {output_dir}")
    print(f"Figure manifest: {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
