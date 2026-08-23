#!/usr/bin/env python3
"""Generate quantitative SRC-to-SAMURAI spin-transport study artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, FancyArrowPatch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.spin_transport.bmt import DEUTERON_ANOMALY, DEUTERON_BMT_G, DEUTERON_MASS_MEV, gamma_from_kinetic_energy
from analysis.spin_transport.ensemble import gaussian_phase_average
from analysis.spin_transport.polarimeter_response import (
    DetectorGeometry,
    PolarimeterChannel,
    analyzing_powers_from_table,
    differential_cross_section,
    fisher_resolution_multi_channel,
    fit_axial_multi_channel,
    four_sector_yields,
    multi_channel_yields,
    proton_cm_from_lab,
    proton_cm_slope,
    sector_observables,
)
from analysis.spin_transport.rotations import rotation_matrix
from analysis.spin_transport.scans import horizontal_bend_scan, phase_spread_scan, sector_angle_scan
from analysis.spin_transport.spin1_density import axial_density_matrix, axial_tensor, diagnose, rotate_density, tensor_components


TABLE = ROOT / "code/data/observables/CompletSetOFT/T.txt"
CROSS_SECTION_TABLE = ROOT / "code/data/observables/DSigamaOverDOmega.txt"


def style() -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 150,
            "savefig.dpi": 220,
            "savefig.bbox": "tight",
        }
    )


def save(fig: plt.Figure, output: Path, name: str) -> None:
    fig.savefig(output / f"{name}.pdf")
    fig.savefig(output / f"{name}.png")
    plt.close(fig)


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str, label: str) -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14, linewidth=2.2, color=color))
    ax.text(end[0], end[1], label, color=color, ha="left", va="bottom")


def figure_beamline(output: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 2.8))
    labels = ["PIS / Wien filter", "AVF-RRC-SRC", "afterSRC\npolarimeter", "transport lattice\n(settings required)", "pre-SAMURAI\npolarimeter", "SAMURAI target"]
    x = np.arange(len(labels))
    for index, label in enumerate(labels):
        ax.text(index, 0.0, label, ha="center", va="center", bbox={"boxstyle": "round,pad=0.45", "fc": "#eef4f8", "ec": "#386a8c"})
        if index + 1 < len(labels):
            arrow(ax, (index + 0.28, 0.0), (index + 0.72, 0.0), "#444444", "")
    ax.text(2.5, -0.65, r"$\rho_2=U_{\rm transport}\rho_1U_{\rm transport}^\dagger$ (coherent ideal)", ha="center", color="#8b1e3f")
    ax.set_xlim(-0.65, len(labels) - 0.35)
    ax.set_ylim(-1.05, 0.65)
    ax.axis("off")
    save(fig, output, "01_beamline_concept")


def figure_orbit_spin(output: Path, gamma: float) -> None:
    theta = np.radians(30.0)
    delta = DEUTERON_ANOMALY * gamma * theta
    psi = theta + delta
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    arrow(ax, (0, 0), (2.8, 0), "#333333", "initial momentum / tensor axis")
    arrow(ax, (0, 0), (2.8 * np.cos(theta), 2.8 * np.sin(theta)), "#1261a0", r"new momentum: $\theta$")
    arrow(ax, (0, 0), (2.5 * np.cos(psi), 2.5 * np.sin(psi)), "#b21f45", r"spin/tensor axis: $\psi$")
    ax.add_patch(Arc((0, 0), 1.6, 1.6, theta1=0, theta2=np.degrees(theta), color="#1261a0"))
    ax.add_patch(Arc((0, 0), 2.0, 2.0, theta1=np.degrees(psi), theta2=np.degrees(theta), color="#b21f45"))
    ax.text(0.85, 0.18, r"$\theta_{\rm orbit}$", color="#1261a0")
    ax.text(0.98, 0.54, rf"$\delta=G\gamma\theta={np.degrees(delta):.2f}^\circ$", color="#b21f45")
    ax.set_aspect("equal")
    ax.set_xlim(-0.2, 3.3)
    ax.set_ylim(-0.3, 2.0)
    ax.axis("off")
    save(fig, output, "02_orbit_vs_spin")


def figure_frames(output: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    arrow(ax, (0, 0), (2.7, 0), "#444444", r"$z_0$ initial beam")
    theta = np.radians(24.0)
    arrow(ax, (0, 0), (2.7 * np.cos(theta), 2.7 * np.sin(theta)), "#1261a0", r"$z_b$ local beam")
    arrow(ax, (0, 0), (0, 2.0), "#2f7f4f", r"$y_{\rm lab}=y_0=y_b$")
    ax.text(1.6, 1.35, "Polarimeter angles are formed\nin the local beam frame", color="#1261a0", ha="center")
    ax.set_xlim(-0.4, 3.2)
    ax.set_ylim(-0.4, 2.5)
    ax.set_aspect("equal")
    ax.axis("off")
    save(fig, output, "03_coordinate_frames")


def tensor_orientation_figure(output: Path, mode: str, transported: bool, delta_deg: float = -5.16) -> None:
    fig, ax = plt.subplots(figsize=(7.0, 4.5))
    theta = np.radians(30.0) if transported else 0.0
    beam_label = "" if mode == "pzz" and not transported else "local beam"
    arrow(ax, (0, 0), (3.0 * np.cos(theta), 3.0 * np.sin(theta)), "#1261a0", beam_label)
    if mode == "pyy":
        arrow(ax, (0, 0), (0.0, 2.3), "#b21f45", r"tensor axis $y$")
        note = "Invariant for an ideal horizontal bend" if transported else "Vertical axial tensor"
    else:
        tensor_angle = theta + (np.radians(delta_deg) if transported else 0.0)
        if transported:
            arrow(ax, (0, 0), (2.5 * np.cos(tensor_angle), 2.5 * np.sin(tensor_angle)), "#b21f45", "tensor principal axis")
        else:
            ax.add_patch(FancyArrowPatch((0, 0.08), (2.45, 0.08), arrowstyle="-|>", mutation_scale=14, linewidth=2.2, color="#b21f45"))
            ax.text(2.42, 0.23, "tensor principal axis", color="#b21f45", ha="right")
            ax.text(2.92, -0.20, "beam direction", color="#1261a0", ha="right")
        note = rf"Relative axis angle $\delta={delta_deg:.2f}^\circ$" if transported else "Longitudinal axial tensor"
    ax.text(1.4, -0.45, note, ha="center")
    ax.set_xlim(-0.6, 3.4)
    ax.set_ylim(-0.75, 2.7)
    ax.set_aspect("equal")
    ax.axis("off")
    prefix = "transported" if transported else "initial"
    save(fig, output, f"0{4 if mode == 'pyy' and not transported else 5 if mode == 'pyy' else 6 if not transported else 7}_{prefix}_{mode}")


def figure_tensor_and_density(output: Path, gamma: float) -> None:
    bends = np.linspace(0.0, 30.0, 301)
    scan = horizontal_bend_scan(0.8, bends)
    fig, ax = plt.subplots(figsize=(7.5, 4.7))
    for key, label in (("pzz", r"$p_{zz}$"), ("pxx", r"$p_{xx}$"), ("pxz", r"$p_{xz}$")):
        ax.plot(bends, scan[key], label=label, linewidth=2)
    ax.plot(bends, scan["pyy"], label=r"$p_{yy}$", linestyle="--")
    ax.set(xlabel="Signed orbital bend (deg)", ylabel="Tensor component in local beam frame")
    ax.legend(ncol=2)
    save(fig, output, "08_tensor_components_vs_bend")

    elements: list[np.ndarray] = []
    rho0 = axial_density_matrix(0.8, np.array([0.0, 0.0, 1.0]))
    for bend in bends:
        delta = DEUTERON_ANOMALY * gamma * np.radians(bend)
        elements.append(rotate_density(rho0, np.array([0.0, 1.0, 0.0]), delta))
    matrices = np.asarray(elements)
    fig, ax = plt.subplots(figsize=(7.5, 4.7))
    ax.plot(bends, matrices[:, 0, 0].real, label=r"$\rho_{+1,+1}$")
    ax.plot(bends, matrices[:, 1, 1].real, label=r"$\rho_{0,0}$")
    ax.plot(bends, matrices[:, 2, 2].real, label=r"$\rho_{-1,-1}$", linestyle="--")
    ax.plot(bends, matrices[:, 0, 1].real, label=r"Re $\rho_{+1,0}$")
    ax.plot(bends, matrices[:, 0, 2].real, label=r"Re $\rho_{+1,-1}$")
    ax.set(xlabel="Signed orbital bend (deg)", ylabel="Density-matrix element")
    ax.legend(ncol=2)
    save(fig, output, "09_density_matrix_vs_bend")


def figure_sector_response(output: Path, analyzing, channels: list[PolarimeterChannel]) -> tuple[float, float, float]:
    deltas = np.linspace(-12.0, 12.0, 241)
    scan = sector_angle_scan(0.8, deltas, analyzing)
    fig, axes = plt.subplots(2, 1, figsize=(7.5, 7.4), sharex=True)
    for key in ("L", "R", "U", "D"):
        axes[0].plot(deltas, scan[key], label=key)
    axes[0].set_ylabel("Expected counts / sector")
    axes[0].legend(ncol=4)
    for key in ("L-R", "U-D", "LR-UD"):
        axes[1].plot(deltas, scan[key], label=key)
    axes[1].set(xlabel=r"Relative tensor-axis angle $\delta$ (deg)", ylabel="Normalized observable")
    axes[1].legend(ncol=3)
    save(fig, output, "10_four_sector_yields_vs_spin_angle")

    counts = np.logspace(3, 7, 80)
    sigma_p, sigma_delta = [], []
    conditions = []
    for count in counts:
        first, second, condition = fisher_resolution_multi_channel(0.8, np.radians(-5.1587), channels, count)
        sigma_p.append(first)
        sigma_delta.append(np.degrees(second))
        conditions.append(condition)
    fig, ax1 = plt.subplots(figsize=(7.5, 4.8))
    ax2 = ax1.twinx()
    first_line = ax1.loglog(counts, sigma_p, color="#1261a0", label=r"$\sigma(p_T)$")
    second_line = ax2.loglog(counts, sigma_delta, color="#b21f45", label=r"$\sigma(\delta)$")
    ax1.set(xlabel="Unpolarized normalization per sector", ylabel=r"$\sigma(p_T)$", ylim=(1.0e-4, 1.0))
    ax2.set(ylabel=r"$\sigma(\delta)$ (deg)", ylim=(1.0e-3, 100.0))
    ax1.legend(first_line + second_line, [item.get_label() for item in first_line + second_line], loc="upper right")
    save(fig, output, "11_tensor_axis_sensitivity")
    return float(sigma_p[-1]), float(sigma_delta[-1]), float(conditions[-1])


def figure_ensemble(output: Path) -> None:
    sigma = np.linspace(0.0, 35.0, 176)
    scan = phase_spread_scan(0.8, sigma, mean_delta_rad=np.radians(-5.1587))
    rho0 = axial_density_matrix(0.8, np.array([0.0, 0.0, 1.0]))
    purities = [diagnose(gaussian_phase_average(rho0, np.array([0.0, 1.0, 0.0]), np.radians(-5.1587), np.radians(value))).purity for value in sigma]
    fig, axes = plt.subplots(2, 1, figsize=(7.5, 7.0), sharex=True)
    axes[0].plot(sigma, scan["pzz"], label=r"$p_{zz}$")
    axes[0].plot(sigma, scan["pxz"], label=r"$p_{xz}$")
    axes[0].plot(sigma, scan["pyy"], label=r"$p_{yy}$")
    axes[0].set_ylabel("Ensemble tensor component")
    axes[0].legend()
    axes[1].plot(sigma, purities, color="#6f4a8e")
    axes[1].set(xlabel=r"RMS spin-phase spread $\sigma_\delta$ (deg)", ylabel=r"Purity $\mathrm{Tr}\,\bar\rho^2$")
    save(fig, output, "12_coherent_rotation_vs_depolarization")


def steering_scan(output: Path, channels: list[PolarimeterChannel]) -> dict[str, object]:
    p_value = 0.8
    delta_value = -5.1587
    pzz_axis = np.array([np.sin(np.radians(delta_value)), 0.0, np.cos(np.radians(delta_value))])
    pyy_axis = np.array([0.0, 1.0, 0.0])
    offsets = np.array([-5.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 5.0])
    angles = np.array([-5.0, -2.0, -1.0, -0.5, -0.1, 0.0, 0.1, 0.5, 1.0, 2.0, 5.0])

    rows: list[dict[str, float | str]] = []
    curves: dict[str, list[float]] = {"pzz_x_dp": [], "pzz_x_dd": [], "pyy_y_dp": [], "pyy_y_dd": []}
    for mode, true_axis, fit_base, fit_rotation in (
        ("pzz", pzz_axis, np.array([0.0, 0.0, 1.0]), np.array([0.0, 1.0, 0.0])),
        ("pyy", pyy_axis, np.array([0.0, 1.0, 0.0]), np.array([1.0, 0.0, 0.0])),
    ):
        for parameter, values in (("x_mm", offsets), ("y_mm", offsets), ("alpha_x_mrad", angles), ("alpha_y_mrad", angles)):
            for value in values:
                position = (value, 0.0) if parameter == "x_mm" else (0.0, value) if parameter == "y_mm" else (0.0, 0.0)
                beam_angle = (value, 0.0) if parameter == "alpha_x_mrad" else (0.0, value) if parameter == "alpha_y_mrad" else (0.0, 0.0)
                observed = multi_channel_yields(axial_tensor(p_value, true_axis), channels, 100_000.0, position, beam_angle)
                bounds = (-12.0, 2.0) if mode == "pzz" else (-8.0, 8.0)
                fit = fit_axial_multi_channel(observed, channels, fit_base, fit_rotation, (0.5, 1.0), bounds)
                delta_bias = fit["delta_deg"] - delta_value if mode == "pzz" else fit["delta_deg"]
                rows.append({"mode": mode, "parameter": parameter, "value": float(value), "delta_pT": fit["p_tensor"] - p_value, "delta_delta_deg": delta_bias})
                if mode == "pzz" and parameter == "x_mm":
                    curves["pzz_x_dp"].append(fit["p_tensor"] - p_value)
                    curves["pzz_x_dd"].append(delta_bias)
                if mode == "pyy" and parameter == "y_mm":
                    curves["pyy_y_dp"].append(fit["p_tensor"] - p_value)
                    curves["pyy_y_dd"].append(delta_bias)

    with (output.parent / "beam_steering_bias.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    fig, axes = plt.subplots(2, 1, figsize=(7.5, 7.0), sharex=True)
    axes[0].plot(offsets, curves["pzz_x_dp"], marker="o", label=r"$p_{zz}$ mode, $x_b$")
    axes[0].plot(offsets, curves["pyy_y_dp"], marker="s", label=r"$p_{yy}$ mode, $y_b$")
    axes[0].set_ylabel(r"Fit bias $\Delta p_T$")
    axes[0].legend()
    axes[1].plot(offsets, curves["pzz_x_dd"], marker="o", label=r"$p_{zz}$ mode, $x_b$")
    axes[1].plot(offsets, curves["pyy_y_dd"], marker="s", label=r"$p_{yy}$ mode, $y_b$")
    axes[1].set(xlabel="Beam offset (mm)", ylabel=r"Fit bias $\Delta\delta$ (deg)")
    axes[1].legend()
    save(fig, output, "13_beam_offset_fake_spin_rotation")
    return {"rows": rows}


def figure_two_stations(output: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.2, 3.4))
    ax.text(0.12, 0.5, "afterSRC\nmeasure $\\rho_1$", ha="center", va="center", bbox={"boxstyle": "round", "fc": "#e8f2f8", "ec": "#1261a0"})
    ax.text(0.50, 0.5, "lattice model\n$M_{\\rm spin}$", ha="center", va="center", bbox={"boxstyle": "round", "fc": "#f7f1e3", "ec": "#9c6b1b"})
    ax.text(0.88, 0.5, "pre-SAMURAI\nmeasure $\\rho_2$", ha="center", va="center", bbox={"boxstyle": "round", "fc": "#e9f6ed", "ec": "#2f7f4f"})
    arrow(ax, (0.23, 0.5), (0.40, 0.5), "#444444", "")
    arrow(ax, (0.61, 0.5), (0.78, 0.5), "#444444", "")
    ax.text(0.50, 0.14, "Fit rotation and magnitude jointly; compare prediction with station 2", ha="center", color="#8b1e3f")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    save(fig, output, "14_two_polarimeter_spin_transfer")


def write_tables(output_root: Path, gamma: float, analyzing, sensitivity: tuple[float, float, float], steering: dict[str, object]) -> None:
    bends = [1, 3, 5, 10, 20, 30]
    with (output_root / "bend_table.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["orbit_bend_deg", "spin_lab_deg", "relative_spin_deg"])
        for bend in bends:
            writer.writerow([bend, (1.0 + DEUTERON_ANOMALY * gamma) * bend, DEUTERON_ANOMALY * gamma * bend])

    delta = DEUTERON_ANOMALY * gamma * np.radians(30.0)
    pyy_tensor = axial_tensor(0.8, np.array([0.0, 1.0, 0.0]))
    pzz_tensor = axial_tensor(0.8, np.array([np.sin(delta), 0.0, np.cos(delta)]))
    summary = {
        "constants": {"deuteron_mass_mev": DEUTERON_MASS_MEV, "bmt_g": DEUTERON_BMT_G, "G": DEUTERON_ANOMALY, "gamma_380MeV": gamma, "G_gamma": DEUTERON_ANOMALY * gamma},
        "illustrative_30deg": {"relative_spin_deg": float(np.degrees(delta)), "pyy_tensor": pyy_tensor.tolist(), "pzz_tensor": pzz_tensor.tolist()},
        "analyzing_powers_at_68p6deg_cm": analyzing.__dict__,
        "fisher_at_1e7_normalization": {"sigma_pT": sensitivity[0], "sigma_delta_deg": sensitivity[1], "condition_number": sensitivity[2]},
        "steering_scan_rows": len(steering["rows"]),
        "lattice_status": "No sourced complete SRC-to-preSAMURAI magnet sequence or settings were found; real transport remains an input requirement.",
    }
    (output_root / "study_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/spin_transport/figures")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    style()
    gamma = gamma_from_kinetic_energy(380.0)
    analyzing = analyzing_powers_from_table(68.6, TABLE)
    forward_lab = np.radians(53.4)
    backward_lab = np.radians(11.2)
    forward_cm = np.degrees(proton_cm_from_lab(forward_lab))
    backward_cm = np.degrees(proton_cm_from_lab(backward_lab))
    backward_scale = differential_cross_section(backward_cm, CROSS_SECTION_TABLE) / differential_cross_section(forward_cm, CROSS_SECTION_TABLE) * (205.0 / 190.0) ** 2
    channels = [
        PolarimeterChannel("forward", analyzing_powers_from_table(forward_cm, TABLE), DetectorGeometry(theta_lab_deg=53.4, radius_mm=205.0), 1.0, forward_cm, proton_cm_slope(forward_lab), TABLE, CROSS_SECTION_TABLE),
        PolarimeterChannel("backward", analyzing_powers_from_table(backward_cm, TABLE), DetectorGeometry(theta_lab_deg=11.2, radius_mm=190.0), backward_scale, backward_cm, proton_cm_slope(backward_lab), TABLE, CROSS_SECTION_TABLE),
    ]
    figure_beamline(output)
    figure_orbit_spin(output, gamma)
    figure_frames(output)
    tensor_orientation_figure(output, "pyy", False)
    tensor_orientation_figure(output, "pyy", True)
    tensor_orientation_figure(output, "pzz", False)
    tensor_orientation_figure(output, "pzz", True)
    figure_tensor_and_density(output, gamma)
    sensitivity = figure_sector_response(output, analyzing, channels)
    figure_ensemble(output)
    steering = steering_scan(output, channels)
    figure_two_stations(output)
    write_tables(output.parent, gamma, analyzing, sensitivity, steering)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
