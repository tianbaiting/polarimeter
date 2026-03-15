#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCRIPT_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPT_DIR.parents[1]
DEFAULT_OUTPUT_DIR = CODE_DIR / "output" / "energy_lise" / "dp_dc_kinematics"

DEUTERON_MASS_MEV = 1875.612
PROTON_MASS_MEV = 938.0
CARBON_MASS_MEV = 12.011 * 931.5
DEFAULT_BEAM_KINETIC_MEV = 380.0
DEFAULT_THICKNESS_UM = 10000.0
DEFAULT_POINTS = 300
RANGE_COLUMN_INDEX = 1


@dataclass(frozen=True)
class RangeTable:
    energy_mev_per_u: np.ndarray
    range_um: np.ndarray


@dataclass(frozen=True)
class DetectorWindow:
    center_deg: float
    distance_mm: float
    width_theta_mm: float
    color: str

    @property
    def half_acceptance_deg(self) -> float:
        return np.degrees(self.width_theta_mm / self.distance_mm) / 2.0


@dataclass(frozen=True)
class DpAnalyticContext:
    beta_cm: float
    gamma_cm: float
    deuteron_cm_energy_mev: float
    deuteron_cm_momentum_mev_c: float
    proton_cm_energy_mev: float


@dataclass(frozen=True)
class CurveBundle:
    columns: dict[str, np.ndarray]


@dataclass
class LorentzVector:
    px: np.ndarray
    py: np.ndarray
    pz: np.ndarray
    energy: np.ndarray

    def copy(self) -> "LorentzVector":
        return LorentzVector(
            np.array(self.px, copy=True),
            np.array(self.py, copy=True),
            np.array(self.pz, copy=True),
            np.array(self.energy, copy=True),
        )

    def boost(self, beta_x: np.ndarray, beta_y: np.ndarray, beta_z: np.ndarray) -> None:
        beta_squared = beta_x * beta_x + beta_y * beta_y + beta_z * beta_z
        gamma = 1.0 / np.sqrt(1.0 - beta_squared)
        beta_dot_p = beta_x * self.px + beta_y * self.py + beta_z * self.pz
        gamma_factor = np.divide(
            gamma - 1.0,
            beta_squared,
            out=np.zeros_like(beta_squared),
            where=beta_squared > 0.0,
        )

        px_new = self.px + gamma_factor * beta_dot_p * beta_x + gamma * beta_x * self.energy
        py_new = self.py + gamma_factor * beta_dot_p * beta_y + gamma * beta_y * self.energy
        pz_new = self.pz + gamma_factor * beta_dot_p * beta_z + gamma * beta_z * self.energy
        energy_new = gamma * (self.energy + beta_dot_p)

        self.px = px_new
        self.py = py_new
        self.pz = pz_new
        self.energy = energy_new

    def set_theta_phi(self, theta_rad: np.ndarray, phi_rad: np.ndarray) -> None:
        momentum = np.sqrt(np.maximum(self.px * self.px + self.py * self.py + self.pz * self.pz, 0.0))
        self.px = momentum * np.sin(theta_rad) * np.cos(phi_rad)
        self.py = momentum * np.sin(theta_rad) * np.sin(phi_rad)
        self.pz = momentum * np.cos(theta_rad)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate corrected dp/dC kinematic-relation and 10 mm C8H8 energy-loss plots.",
    )
    parser.add_argument("--beam-kinetic-mev", type=float, default=DEFAULT_BEAM_KINETIC_MEV)
    parser.add_argument("--thickness-um", type=float, default=DEFAULT_THICKNESS_UM)
    parser.add_argument("--points", type=int, default=DEFAULT_POINTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-overlay", action="store_true")
    return parser.parse_args()


def detector_windows() -> list[DetectorWindow]:
    return [
        DetectorWindow(center_deg=20.87, distance_mm=500.0, width_theta_mm=50.0, color="yellow"),
        DetectorWindow(center_deg=55.9, distance_mm=600.0, width_theta_mm=40.0, color="cyan"),
        DetectorWindow(center_deg=11.3, distance_mm=600.0, width_theta_mm=40.0, color="magenta"),
    ]


def load_range_table(path: Path) -> RangeTable:
    data = np.loadtxt(path, skiprows=3)
    # [EN] Keep the notebook's first range column so the standalone script stays numerically comparable to the original study / [CN] 保留 notebook 使用的第一列射程数据，使独立脚本与原始研究的数值风格保持一致
    return RangeTable(energy_mev_per_u=data[:, 0], range_um=data[:, RANGE_COLUMN_INDEX])


def make_dp_context(beam_kinetic_mev: float) -> DpAnalyticContext:
    total_deuteron_energy_mev = DEUTERON_MASS_MEV + beam_kinetic_mev
    deuteron_momentum_mev_c = np.sqrt(total_deuteron_energy_mev * total_deuteron_energy_mev - DEUTERON_MASS_MEV * DEUTERON_MASS_MEV)
    beta_cm = deuteron_momentum_mev_c / (total_deuteron_energy_mev + PROTON_MASS_MEV)
    gamma_cm = 1.0 / np.sqrt(1.0 - beta_cm * beta_cm)
    deuteron_cm_energy_mev = gamma_cm * total_deuteron_energy_mev - gamma_cm * beta_cm * deuteron_momentum_mev_c
    deuteron_cm_momentum_mev_c = -gamma_cm * beta_cm * total_deuteron_energy_mev + gamma_cm * deuteron_momentum_mev_c
    proton_cm_energy_mev = gamma_cm * PROTON_MASS_MEV
    return DpAnalyticContext(
        beta_cm=beta_cm,
        gamma_cm=gamma_cm,
        deuteron_cm_energy_mev=deuteron_cm_energy_mev,
        deuteron_cm_momentum_mev_c=deuteron_cm_momentum_mev_c,
        proton_cm_energy_mev=proton_cm_energy_mev,
    )


def nan_arcsin(argument: np.ndarray) -> np.ndarray:
    valid = np.abs(argument) <= 1.0
    clipped = np.clip(argument, -1.0, 1.0)
    return np.where(valid, np.arcsin(clipped), np.nan)


def deuteron_cm_from_lab(theta_lab_rad: np.ndarray, context: DpAnalyticContext) -> tuple[np.ndarray, np.ndarray]:
    tangent = np.tan(theta_lab_rad)
    gamma_tangent = context.gamma_cm * tangent
    square_root = np.sqrt(1.0 + context.gamma_cm * context.gamma_cm * tangent * tangent)
    arcsine = nan_arcsin(
        (tangent * context.gamma_cm * context.beta_cm * context.deuteron_cm_energy_mev)
        / (context.deuteron_cm_momentum_mev_c * square_root),
    )
    theta_first = np.arctan(gamma_tangent) + arcsine
    theta_second = np.arctan(gamma_tangent) + np.pi - arcsine
    return theta_first, theta_second


def proton_cm_from_lab(theta_lab_rad: np.ndarray, context: DpAnalyticContext) -> np.ndarray:
    tangent = np.tan(theta_lab_rad)
    gamma_tangent = context.gamma_cm * tangent
    square_root = np.sqrt(1.0 + context.gamma_cm * context.gamma_cm * tangent * tangent)
    arcsine = nan_arcsin(
        (tangent * context.gamma_cm * context.beta_cm * context.proton_cm_energy_mev)
        / (context.deuteron_cm_momentum_mev_c * square_root),
    )
    return np.pi - (np.arctan(gamma_tangent) + arcsine)


def scatter_elastic(
    theta_cm_rad: np.ndarray,
    phi_cm_rad: np.ndarray,
    target_mass_mev: float,
    beam_kinetic_mev: float,
) -> tuple[LorentzVector, LorentzVector]:
    theta_cm = np.asarray(theta_cm_rad, dtype=float)
    phi_cm = np.asarray(phi_cm_rad, dtype=float)

    total_beam_energy_mev = DEUTERON_MASS_MEV + beam_kinetic_mev
    deuteron_momentum_mev_c = np.sqrt(total_beam_energy_mev * total_beam_energy_mev - DEUTERON_MASS_MEV * DEUTERON_MASS_MEV)

    beam_lab = LorentzVector(
        px=np.zeros_like(theta_cm),
        py=np.zeros_like(theta_cm),
        pz=np.full_like(theta_cm, deuteron_momentum_mev_c),
        energy=np.full_like(theta_cm, total_beam_energy_mev),
    )
    target_lab = LorentzVector(
        px=np.zeros_like(theta_cm),
        py=np.zeros_like(theta_cm),
        pz=np.zeros_like(theta_cm),
        energy=np.full_like(theta_cm, target_mass_mev),
    )

    total_lab_pz = beam_lab.pz + target_lab.pz
    total_lab_energy = beam_lab.energy + target_lab.energy
    beta_z = total_lab_pz / total_lab_energy
    beta_x = np.zeros_like(beta_z)
    beta_y = np.zeros_like(beta_z)

    beam_cm = beam_lab.copy()
    target_cm = target_lab.copy()
    beam_cm.boost(-beta_x, -beta_y, -beta_z)
    target_cm.boost(-beta_x, -beta_y, -beta_z)

    # [EN] Rotate the elastic final state in the CM frame, then boost back to lab to preserve the notebook's two-body construction / [CN] 先在质心系旋转弹性末态，再变换回实验室系，以保持 notebook 的两体散射构造
    beam_cm.set_theta_phi(theta_cm, phi_cm)
    target_cm.set_theta_phi(np.pi - theta_cm, np.pi + phi_cm)

    beam_cm.boost(beta_x, beta_y, beta_z)
    target_cm.boost(beta_x, beta_y, beta_z)
    return beam_cm, target_cm


def energy_loss_mev(
    mass_number: int,
    kinetic_energy_per_u_mev: np.ndarray,
    thickness_um: float,
    table: RangeTable,
) -> np.ndarray:
    kinetic_energy_per_u = np.asarray(kinetic_energy_per_u_mev, dtype=float)
    total_kinetic_energy_mev = kinetic_energy_per_u * float(mass_number)
    initial_range_um = np.interp(kinetic_energy_per_u, table.energy_mev_per_u, table.range_um)
    residual_range_um = np.maximum(initial_range_um - thickness_um, 0.0)
    residual_energy_per_u_mev = np.interp(residual_range_um, table.range_um, table.energy_mev_per_u)
    return np.where(
        initial_range_um > thickness_um,
        total_kinetic_energy_mev - residual_energy_per_u_mev * float(mass_number),
        total_kinetic_energy_mev,
    )


def build_theta_relation_curves(points: int, beam_kinetic_mev: float) -> CurveBundle:
    dp_context = make_dp_context(beam_kinetic_mev)

    theta_lab_deg = np.linspace(0.1, 89.0, points)
    theta_lab_rad = np.deg2rad(theta_lab_deg)
    theta_deuteron_cm_1 = np.degrees(deuteron_cm_from_lab(theta_lab_rad, dp_context)[0])
    theta_deuteron_cm_2 = np.degrees(deuteron_cm_from_lab(theta_lab_rad, dp_context)[1])
    theta_proton_cm = np.degrees(proton_cm_from_lab(theta_lab_rad, dp_context))

    theta_dc_cm_rad = np.linspace(np.deg2rad(0.1), np.pi, points)
    deuteron_dc_lab, carbon_dc_lab = scatter_elastic(theta_dc_cm_rad, np.zeros_like(theta_dc_cm_rad), CARBON_MASS_MEV, beam_kinetic_mev)
    deuteron_dc_lab_deg = np.degrees(np.arctan2(deuteron_dc_lab.px, deuteron_dc_lab.pz))
    carbon_dc_lab_deg = -np.degrees(np.arctan2(carbon_dc_lab.px, carbon_dc_lab.pz))

    return CurveBundle(
        columns={
            "dp_deuteron_lab_deg": theta_lab_deg,
            "dp_deuteron_cm_branch1_deg": theta_deuteron_cm_1,
            "dp_deuteron_cm_branch2_deg": theta_deuteron_cm_2,
            "dp_proton_lab_deg": theta_lab_deg,
            "dp_proton_cm_deg": theta_proton_cm,
            "dc_deuteron_lab_deg": deuteron_dc_lab_deg,
            "dc_deuteron_cm_deg": np.degrees(theta_dc_cm_rad),
            "dc_carbon_lab_deg": carbon_dc_lab_deg,
            "dc_carbon_cm_deg": np.degrees(theta_dc_cm_rad),
        },
    )


def build_energy_loss_curves(points: int, beam_kinetic_mev: float, thickness_um: float) -> CurveBundle:
    proton_table = load_range_table(SCRIPT_DIR / "H_c8h8_range.txt")
    deuteron_table = load_range_table(SCRIPT_DIR / "2H_C8H8_range_MeV_um.txt")
    carbon_table = load_range_table(SCRIPT_DIR / "12C_C8H8_range_MeV_um.txt")

    dp_context = make_dp_context(beam_kinetic_mev)
    theta_lab_deg = np.linspace(0.1, 89.0, points)
    theta_lab_rad = np.deg2rad(theta_lab_deg)
    theta_deuteron_cm_1_rad, theta_deuteron_cm_2_rad = deuteron_cm_from_lab(theta_lab_rad, dp_context)
    theta_proton_cm_rad = proton_cm_from_lab(theta_lab_rad, dp_context)

    deuteron_dp_branch1, _ = scatter_elastic(theta_deuteron_cm_1_rad, np.zeros_like(theta_deuteron_cm_1_rad), PROTON_MASS_MEV, beam_kinetic_mev)
    deuteron_dp_branch2, _ = scatter_elastic(theta_deuteron_cm_2_rad, np.zeros_like(theta_deuteron_cm_2_rad), PROTON_MASS_MEV, beam_kinetic_mev)
    _, proton_dp = scatter_elastic(theta_proton_cm_rad, np.zeros_like(theta_proton_cm_rad), PROTON_MASS_MEV, beam_kinetic_mev)

    theta_dc_cm_rad = np.linspace(np.deg2rad(0.1), np.pi, points)
    deuteron_dc, carbon_dc = scatter_elastic(theta_dc_cm_rad, np.zeros_like(theta_dc_cm_rad), CARBON_MASS_MEV, beam_kinetic_mev)

    deuteron_branch1_loss_mev = energy_loss_mev(
        mass_number=2,
        kinetic_energy_per_u_mev=(deuteron_dp_branch1.energy - DEUTERON_MASS_MEV) / 2.0,
        thickness_um=thickness_um,
        table=deuteron_table,
    )
    deuteron_branch2_loss_mev = energy_loss_mev(
        mass_number=2,
        kinetic_energy_per_u_mev=(deuteron_dp_branch2.energy - DEUTERON_MASS_MEV) / 2.0,
        thickness_um=thickness_um,
        table=deuteron_table,
    )
    proton_loss_mev = energy_loss_mev(
        mass_number=1,
        kinetic_energy_per_u_mev=proton_dp.energy - PROTON_MASS_MEV,
        thickness_um=thickness_um,
        table=proton_table,
    )
    deuteron_dc_loss_mev = energy_loss_mev(
        mass_number=2,
        kinetic_energy_per_u_mev=(deuteron_dc.energy - DEUTERON_MASS_MEV) / 2.0,
        thickness_um=thickness_um,
        table=deuteron_table,
    )
    carbon_dc_loss_mev = energy_loss_mev(
        mass_number=12,
        kinetic_energy_per_u_mev=(carbon_dc.energy - CARBON_MASS_MEV) / 12.0,
        thickness_um=thickness_um,
        table=carbon_table,
    )

    return CurveBundle(
        columns={
            "dp_deuteron_lab_deg": theta_lab_deg,
            "dp_deuteron_loss_branch1_mev": deuteron_branch1_loss_mev,
            "dp_deuteron_loss_branch2_mev": deuteron_branch2_loss_mev,
            "dp_proton_lab_deg": theta_lab_deg,
            "dp_proton_loss_mev": proton_loss_mev,
            "dc_deuteron_lab_deg": np.degrees(np.arctan2(deuteron_dc.px, deuteron_dc.pz)),
            "dc_deuteron_loss_mev": deuteron_dc_loss_mev,
            "dc_carbon_lab_deg": -np.degrees(np.arctan2(carbon_dc.px, carbon_dc.pz)),
            "dc_carbon_loss_mev": carbon_dc_loss_mev,
        },
    )


def add_detector_overlay(axis: plt.Axes) -> None:
    for window in detector_windows():
        axis.axvspan(
            window.center_deg - window.half_acceptance_deg,
            window.center_deg + window.half_acceptance_deg,
            color=window.color,
            alpha=0.3,
        )


def write_csv(path: Path, columns: dict[str, np.ndarray]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    column_names = list(columns.keys())
    arrays = [np.asarray(columns[name]).reshape(-1) for name in column_names]
    row_count = len(arrays[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(column_names)
        for row_index in range(row_count):
            row: list[str] = []
            for array in arrays:
                value = float(array[row_index])
                row.append(f"{value:.10f}" if np.isfinite(value) else "nan")
            writer.writerow(row)


def save_theta_plot(path: Path, curves: CurveBundle, include_overlay: bool) -> None:
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.plot(curves.columns["dp_deuteron_lab_deg"], curves.columns["dp_deuteron_cm_branch1_deg"], label="Theta D cm, dp scatter", color="green")
    axis.plot(curves.columns["dp_deuteron_lab_deg"], curves.columns["dp_deuteron_cm_branch2_deg"], color="green", linestyle="--")
    axis.plot(curves.columns["dp_proton_lab_deg"], curves.columns["dp_proton_cm_deg"], label="Theta p cm, dp scatter", color="red")
    axis.plot(curves.columns["dc_deuteron_lab_deg"], curves.columns["dc_deuteron_cm_deg"], label="Deuteron labtheta, DC scatter", color="orange")
    axis.plot(curves.columns["dc_carbon_lab_deg"], curves.columns["dc_carbon_cm_deg"], label="Carbon labtheta, DC scatter", color="blue")
    if include_overlay:
        add_detector_overlay(axis)
    axis.set_xlim(0.0, 180.0)
    axis.set_ylim(0.0, 180.0)
    axis.set_xlabel("Theta Lab (degrees)")
    axis.set_ylabel("Theta CM (degrees)")
    axis.set_title("Theta CM vs Theta Lab")
    axis.grid(True, alpha=0.4)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=200)
    plt.close(figure)


def save_energy_loss_plot(path: Path, curves: CurveBundle, include_overlay: bool, thickness_um: float) -> None:
    thickness_mm = thickness_um / 1000.0
    thickness_label = f"{thickness_mm:.1f}mm"
    figure, axis = plt.subplots(figsize=(10, 6))
    axis.plot(curves.columns["dp_deuteron_lab_deg"], curves.columns["dp_deuteron_loss_branch1_mev"], label=f"Deuteron dE ({thickness_label} C8H8, dp_scattering)", color="green")
    axis.plot(curves.columns["dp_deuteron_lab_deg"], curves.columns["dp_deuteron_loss_branch2_mev"], label=f"Deuteron dE branch 2 ({thickness_label} C8H8, dp_scattering)", color="green", linestyle="--")
    axis.plot(curves.columns["dp_proton_lab_deg"], curves.columns["dp_proton_loss_mev"], label=f"Proton dE ({thickness_label} C8H8, dp_scattering)", color="blue")
    axis.plot(curves.columns["dc_deuteron_lab_deg"], curves.columns["dc_deuteron_loss_mev"], label=f"Deuteron dE ({thickness_label} C8H8, dC_scattering)", color="purple")
    axis.plot(curves.columns["dc_carbon_lab_deg"], curves.columns["dc_carbon_loss_mev"], label=f"Carbon dE ({thickness_label} C8H8, dC_scattering)", color="red")
    if include_overlay:
        add_detector_overlay(axis)
    axis.set_xlim(0.0, 180.0)
    axis.set_xlabel("Lab Angle θ_lab (deg)")
    axis.set_ylabel("Loss dE (MeV)")
    axis.set_title(f"Energy Loss vs Lab Angle ({thickness_label} C8H8)")
    axis.grid(True, alpha=0.4)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=200)
    plt.close(figure)


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    theta_curves = build_theta_relation_curves(points=args.points, beam_kinetic_mev=args.beam_kinetic_mev)
    energy_curves = build_energy_loss_curves(
        points=args.points,
        beam_kinetic_mev=args.beam_kinetic_mev,
        thickness_um=args.thickness_um,
    )

    theta_csv_path = output_dir / "theta_relations.csv"
    theta_png_path = output_dir / "theta_relations.png"
    energy_csv_path = output_dir / "energy_loss_10mm_c8h8.csv"
    energy_png_path = output_dir / "energy_loss_10mm_c8h8.png"

    write_csv(theta_csv_path, theta_curves.columns)
    write_csv(energy_csv_path, energy_curves.columns)
    save_theta_plot(theta_png_path, theta_curves, include_overlay=not args.no_overlay)
    save_energy_loss_plot(energy_png_path, energy_curves, include_overlay=not args.no_overlay, thickness_um=args.thickness_um)

    print(f"Wrote {theta_png_path}")
    print(f"Wrote {theta_csv_path}")
    print(f"Wrote {energy_png_path}")
    print(f"Wrote {energy_csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
