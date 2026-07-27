#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml


ELECTRON_CHARGE_C = 1.602176634e-19
REPORT_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = REPORT_DIR.parents[2]
DEFAULT_ASSUMPTIONS = REPORT_DIR / "data" / "report_assumptions.yaml"
DEFAULT_OUTPUT_DIR = REPORT_DIR / "generated"


@dataclass(frozen=True)
class SipmResult:
    seed_photoelectrons: float
    fired_cells: float
    nonlinearity_percent: float
    charge_nc: float


@dataclass(frozen=True)
class ChamberMetrics:
    material_volume_l: float
    mass_kg: float
    outer_size_x_mm: float
    outer_size_y_mm: float


@dataclass(frozen=True)
class EnergyLossInterval:
    incident_range_mev: tuple[float, float]
    deposit_range_mev: tuple[float, float]
    maximum_particle_range_mm: float
    all_stopped: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and verify numerical inputs used by the CompactInVacuum SiPM report.",
    )
    parser.add_argument("--assumptions", type=Path, default=DEFAULT_ASSUMPTIONS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that committed generated files match the current inputs without rewriting them.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}")
    return data


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected an object in {path}")
    return data


def load_energy_model(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("dpol_report_energy_model", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load energy model from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sipm_response(
    energy_mev: float,
    light_yield_photons_per_mev: float,
    optical_efficiency: float,
    pde_fraction: float,
    microcells: int,
    gain: float,
) -> SipmResult:
    if energy_mev < 0.0 or light_yield_photons_per_mev <= 0.0:
        raise ValueError("Energy must be non-negative and light yield must be positive")
    if not 0.0 < optical_efficiency <= 1.0 or not 0.0 < pde_fraction <= 1.0:
        raise ValueError("Optical efficiency and PDE must be in (0, 1]")
    if microcells <= 0 or gain <= 0.0:
        raise ValueError("Microcell count and gain must be positive")

    seed = energy_mev * light_yield_photons_per_mev * optical_efficiency * pde_fraction
    if seed == 0.0:
        return SipmResult(0.0, 0.0, 0.0, 0.0)

    # [EN] The short-pulse occupancy model counts unique fired cells before any recovery / [CN] 短脉冲占有模型统计恢复发生前被触发的独立微单元
    fired = float(microcells) * (1.0 - math.exp(-seed / float(microcells)))
    nonlinearity = 100.0 * (1.0 - fired / seed)
    charge_nc = fired * gain * ELECTRON_CHARGE_C * 1.0e9
    return SipmResult(seed, fired, nonlinearity, charge_nc)


def ten_percent_energy_mev(
    light_yield_photons_per_mev: float,
    optical_efficiency: float,
    pde_fraction: float,
    microcells: int,
) -> float:
    lower = 0.0
    upper = 10.0
    for _ in range(120):
        occupancy = 0.5 * (lower + upper)
        response_ratio = (1.0 - math.exp(-occupancy)) / occupancy if occupancy > 0.0 else 1.0
        if response_ratio > 0.9:
            lower = occupancy
        else:
            upper = occupancy
    occupancy = 0.5 * (lower + upper)
    return (
        occupancy
        * float(microcells)
        / (light_yield_photons_per_mev * optical_efficiency * pde_fraction)
    )


def chamber_metrics(
    inner_x_mm: float,
    inner_y_mm: float,
    body_length_mm: float,
    wall_thickness_mm: float,
    density_g_per_cm3: float,
) -> ChamberMetrics:
    outer_x = inner_x_mm + 2.0 * wall_thickness_mm
    outer_y = inner_y_mm + 2.0 * wall_thickness_mm
    inner_length = body_length_mm - 2.0 * wall_thickness_mm
    if min(inner_x_mm, inner_y_mm, inner_length, wall_thickness_mm) <= 0.0:
        raise ValueError("Chamber dimensions must define a positive closed shell")

    # [EN] This screening mass treats the vessel as a closed rectangular shell before subtracting ports / [CN] 此筛选质量把腔体视为封闭矩形壳体，尚未扣除各端口
    material_volume_mm3 = (
        outer_x * outer_y * body_length_mm - inner_x_mm * inner_y_mm * inner_length
    )
    material_volume_l = material_volume_mm3 / 1.0e6
    mass_kg = material_volume_mm3 / 1000.0 * density_g_per_cm3 / 1000.0
    return ChamberMetrics(material_volume_l, mass_kg, outer_x, outer_y)


def active_center_acceptance(center_deg: float, radius_mm: float, diameter_mm: float) -> tuple[float, float]:
    half_angle_deg = math.degrees(math.atan2(0.5 * diameter_mm, radius_mm))
    return center_deg - half_angle_deg, center_deg + half_angle_deg


def intersect_ranges(first: tuple[float, float], second: tuple[float, float]) -> tuple[float, float]:
    overlap = max(first[0], second[0]), min(first[1], second[1])
    if overlap[0] >= overlap[1]:
        raise RuntimeError(f"Ranges do not overlap: {first} and {second}")
    return overlap


def finite_interval(values: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    selected = np.asarray(values)[mask & np.isfinite(values)]
    if selected.size == 0:
        raise RuntimeError("No finite values in requested interval")
    return float(np.min(selected)), float(np.max(selected))


def accepted_interval(
    lab_grid_deg: np.ndarray,
    cm_values_deg: np.ndarray,
    lab_bounds_deg: tuple[float, float],
) -> tuple[float, float]:
    mask = (lab_grid_deg >= lab_bounds_deg[0]) & (lab_grid_deg <= lab_bounds_deg[1])
    return finite_interval(cm_values_deg, mask)


def lab_interval_for_cm_overlap(
    lab_grid_deg: np.ndarray,
    cm_values_deg: np.ndarray,
    lab_bounds_deg: tuple[float, float],
    cm_overlap_deg: tuple[float, float],
) -> tuple[float, float]:
    mask = (
        (lab_grid_deg >= lab_bounds_deg[0])
        & (lab_grid_deg <= lab_bounds_deg[1])
        & (cm_values_deg >= cm_overlap_deg[0])
        & (cm_values_deg <= cm_overlap_deg[1])
    )
    return finite_interval(lab_grid_deg, mask)


def compute_dp_loss_interval(
    kinematics_model: Any,
    range_model: Any,
    lab_range_deg: tuple[float, float],
    branch: str,
    particle: str,
    beam_kinetic_mev: float,
    thickness_um: float,
    range_model_key: str,
    points: int = 4097,
) -> EnergyLossInterval:
    lab_deg = np.linspace(lab_range_deg[0], lab_range_deg[1], points)
    lab_rad = np.deg2rad(lab_deg)
    context = kinematics_model.make_dp_context(beam_kinetic_mev)
    phi = np.zeros_like(lab_rad)

    if particle == "deuteron":
        branch1, branch2 = kinematics_model.deuteron_cm_from_lab(lab_rad, context)
        theta_cm = branch1 if branch == "branch1" else branch2
        deuteron, _ = kinematics_model.scatter_elastic(
            theta_cm,
            phi,
            kinematics_model.PROTON_MASS_MEV,
            beam_kinetic_mev,
        )
        mass_number = 2
        kinetic_per_u = (
            deuteron.energy - kinematics_model.DEUTERON_MASS_MEV
        ) / float(mass_number)
        table_path = kinematics_model.SCRIPT_DIR / "2H_C8H8_range_MeV_um.txt"
    elif particle == "proton":
        theta_cm = kinematics_model.proton_cm_from_lab(lab_rad, context)
        _, proton = kinematics_model.scatter_elastic(
            theta_cm,
            phi,
            kinematics_model.PROTON_MASS_MEV,
            beam_kinetic_mev,
        )
        mass_number = 1
        kinetic_per_u = proton.energy - kinematics_model.PROTON_MASS_MEV
        table_path = kinematics_model.SCRIPT_DIR / "H_c8h8_range.txt"
    else:
        raise ValueError(f"Unsupported d-p final-state particle: {particle}")

    range_table = range_model.load_range_table(table_path, range_model_key)
    initial_range_um = range_model.particle_range_um(kinetic_per_u, range_table)
    loss = range_model.energy_loss_mev(
        mass_number,
        kinetic_per_u,
        thickness_um,
        range_table,
    )
    incident = kinetic_per_u * float(mass_number)
    finite = loss[np.isfinite(loss)]
    finite_incident = incident[np.isfinite(incident)]
    finite_range = initial_range_um[np.isfinite(initial_range_um)]
    return EnergyLossInterval(
        incident_range_mev=(float(np.min(finite_incident)), float(np.max(finite_incident))),
        deposit_range_mev=(float(np.min(finite)), float(np.max(finite))),
        maximum_particle_range_mm=float(np.max(finite_range)) / 1000.0,
        all_stopped=bool(np.all(finite_range <= thickness_um)),
    )


def compute_dc_loss_interval(
    kinematics_model: Any,
    range_model: Any,
    lab_range_deg: tuple[float, float],
    particle: str,
    beam_kinetic_mev: float,
    thickness_um: float,
    range_model_key: str,
    points: int = 200001,
) -> EnergyLossInterval:
    theta_cm = np.linspace(np.deg2rad(0.01), math.pi, points)
    deuteron, carbon = kinematics_model.scatter_elastic(
        theta_cm,
        np.zeros_like(theta_cm),
        kinematics_model.CARBON_MASS_MEV,
        beam_kinetic_mev,
    )
    if particle == "deuteron":
        lab_deg = np.degrees(np.arctan2(deuteron.px, deuteron.pz))
        mass_number = 2
        kinetic_per_u = (
            deuteron.energy - kinematics_model.DEUTERON_MASS_MEV
        ) / float(mass_number)
        table_path = kinematics_model.SCRIPT_DIR / "2H_C8H8_range_MeV_um.txt"
    elif particle == "carbon":
        lab_deg = -np.degrees(np.arctan2(carbon.px, carbon.pz))
        mass_number = 12
        kinetic_per_u = (
            carbon.energy - kinematics_model.CARBON_MASS_MEV
        ) / float(mass_number)
        table_path = kinematics_model.SCRIPT_DIR / "12C_C8H8_range_MeV_um.txt"
    else:
        raise ValueError(f"Unsupported d-C final-state particle: {particle}")

    range_table = range_model.load_range_table(table_path, range_model_key)
    initial_range_um = range_model.particle_range_um(kinetic_per_u, range_table)
    loss = range_model.energy_loss_mev(
        mass_number,
        kinetic_per_u,
        thickness_um,
        range_table,
    )
    incident = kinetic_per_u * float(mass_number)
    mask = (
        (lab_deg >= lab_range_deg[0])
        & (lab_deg <= lab_range_deg[1])
        & np.isfinite(loss)
    )
    selected_loss = np.asarray(loss)[mask]
    selected_incident = np.asarray(incident)[mask]
    selected_range = np.asarray(initial_range_um)[mask]
    if selected_loss.size == 0:
        raise RuntimeError("No d-C samples fall inside the detector acceptance")
    return EnergyLossInterval(
        incident_range_mev=(
            float(np.min(selected_incident)),
            float(np.max(selected_incident)),
        ),
        deposit_range_mev=(
            float(np.min(selected_loss)),
            float(np.max(selected_loss)),
        ),
        maximum_particle_range_mm=float(np.max(selected_range)) / 1000.0,
        all_stopped=bool(np.all(selected_range <= thickness_um)),
    )


def format_float(value: float, digits: int) -> str:
    return f"{value:.{digits}f}"


def tex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in text)


def csv_text(header: list[str], rows: list[list[Any]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def make_outputs(assumptions_path: Path) -> tuple[dict[str, str], list[str]]:
    assumptions = load_yaml(assumptions_path)
    source_paths = {
        key: REPOSITORY_ROOT / relative_path
        for key, relative_path in assumptions["source_files"].items()
    }
    compact_config = load_yaml(source_paths["compact_config"])
    compact_target = load_yaml(source_paths["compact_target"])
    manifest = load_json(source_paths["channel_manifest"])
    validation = load_json(source_paths["validation_report"])
    energy_model = load_energy_model(source_paths["energy_model"])
    range_model = load_energy_model(source_paths["lise_range_model"])
    checks: list[str] = []
    failures: list[str] = []

    def record(name: str, passed: bool, detail: str) -> None:
        status = "PASS" if passed else "FAIL"
        checks.append(f"{status} | {name} | {detail}")
        if not passed:
            failures.append(name)

    record(
        "CAD strict validation",
        validation.get("status") == "pass",
        f"validation status={validation.get('status')}",
    )
    record(
        "Target strict mode",
        bool(compact_target.get("validation", {}).get("strict")),
        f"target.validation.strict={compact_target.get('validation', {}).get('strict')}",
    )

    channels_cfg = {entry["name"]: entry for entry in compact_config["channels"]}
    channels_manifest: dict[str, dict[str, Any]] = {}
    for entry in manifest["channels"]:
        channels_manifest.setdefault(entry["base_channel"], entry)

    angle_tolerance = float(assumptions["verification_tolerances"]["geometry_angle_deg"])
    radius_tolerance = float(assumptions["verification_tolerances"]["geometry_radius_mm"])
    for name, cfg_entry in channels_cfg.items():
        manifest_entry = channels_manifest[name]
        angle_delta = abs(float(cfg_entry["angle_deg"]) - float(manifest_entry["angle_deg"]))
        radius_delta = abs(
            float(cfg_entry["radius_mm"]) - float(manifest_entry["active_center_radius_mm"])
        )
        record(
            f"{name} geometry source agreement",
            angle_delta <= angle_tolerance and radius_delta <= radius_tolerance,
            f"delta_angle={angle_delta:.6g} deg, delta_radius={radius_delta:.6g} mm",
        )

    detector = compact_config["detector"]
    physics = compact_config["physics"]
    vessel = compact_config["vessel"]
    calculation = assumptions["calculation"]
    active_diameter_mm = float(detector["diameter_mm"])
    active_length_mm = float(detector["length_mm"])
    beam_kinetic_mev = float(physics["beam"]["kinetic_energy_mev"])
    candidate_thickness_mm = float(calculation["scintillator_candidate_thickness_mm"])
    thickness_um = candidate_thickness_mm * 1000.0
    primary_range_model = str(calculation["lise_primary_range_model"])
    envelope_range_models = [
        str(value) for value in calculation["lise_range_envelope_models"]
    ]
    supported_range_models = set(range_model.available_model_keys())
    requested_range_models = {primary_range_model, *envelope_range_models}
    unsupported_range_models = sorted(requested_range_models - supported_range_models)
    if unsupported_range_models:
        raise ValueError(
            "Unsupported LISE++ range models in report assumptions: "
            + ", ".join(unsupported_range_models),
        )

    channel_acceptance: dict[str, tuple[float, float]] = {}
    for name, channel in channels_cfg.items():
        channel_acceptance[name] = active_center_acceptance(
            float(channel["angle_deg"]),
            float(channel["radius_mm"]),
            active_diameter_mm,
        )

    # [EN] Intersect the deuteron and proton CM acceptances so energy ranges represent true D-P coincidence / [CN] 对氘核臂和质子臂的质心系接受度取交集，使能损范围对应真实 D-P 符合
    lab_grid_deg = np.linspace(0.01, 89.0, 400001)
    lab_grid_rad = np.deg2rad(lab_grid_deg)
    context = energy_model.make_dp_context(beam_kinetic_mev)
    d_branch1_cm, d_branch2_cm = energy_model.deuteron_cm_from_lab(lab_grid_rad, context)
    proton_cm = energy_model.proton_cm_from_lab(lab_grid_rad, context)
    d_branch1_cm = np.degrees(d_branch1_cm)
    d_branch2_cm = np.degrees(d_branch2_cm)
    proton_cm = np.degrees(proton_cm)

    d_bounds = channel_acceptance["deuteron"]
    p_small_bounds = channel_acceptance["proton_small"]
    p_large_bounds = channel_acceptance["proton_large"]
    forward_cm = intersect_ranges(
        accepted_interval(lab_grid_deg, d_branch1_cm, d_bounds),
        accepted_interval(lab_grid_deg, proton_cm, p_large_bounds),
    )
    backward_cm = intersect_ranges(
        accepted_interval(lab_grid_deg, d_branch2_cm, d_bounds),
        accepted_interval(lab_grid_deg, proton_cm, p_small_bounds),
    )

    forward_d_lab = lab_interval_for_cm_overlap(
        lab_grid_deg,
        d_branch1_cm,
        d_bounds,
        forward_cm,
    )
    forward_p_lab = lab_interval_for_cm_overlap(
        lab_grid_deg,
        proton_cm,
        p_large_bounds,
        forward_cm,
    )
    backward_d_lab = lab_interval_for_cm_overlap(
        lab_grid_deg,
        d_branch2_cm,
        d_bounds,
        backward_cm,
    )
    backward_p_lab = lab_interval_for_cm_overlap(
        lab_grid_deg,
        proton_cm,
        p_small_bounds,
        backward_cm,
    )

    dp_event_definitions = [
        {
            "key": "forward_dp_deuteron",
            "reaction": "d-p forward",
            "particle": "deuteron",
            "station": "D",
            "lab_range_deg": forward_d_lab,
            "branch": "branch1",
            "significance": "Clean timing and charge signal",
        },
        {
            "key": "forward_dp_proton",
            "reaction": "d-p forward",
            "particle": "proton",
            "station": "P-large",
            "lab_range_deg": forward_p_lab,
            "branch": "proton",
            "significance": "Normal proton coincidence branch",
        },
        {
            "key": "backward_dp_deuteron",
            "reaction": "d-p backward",
            "particle": "deuteron",
            "station": "D",
            "lab_range_deg": backward_d_lab,
            "branch": "branch2",
            "significance": "Maximum normal d-p light-load case",
        },
        {
            "key": "backward_dp_proton",
            "reaction": "d-p backward",
            "particle": "proton",
            "station": "P-small",
            "lab_range_deg": backward_p_lab,
            "branch": "proton",
            "significance": "Lowest normal signal; trigger/noise case",
        },
    ]

    energy_rows: list[dict[str, Any]] = []
    for definition in dp_event_definitions:
        interval = compute_dp_loss_interval(
            energy_model,
            range_model,
            definition["lab_range_deg"],
            definition["branch"],
            definition["particle"],
            beam_kinetic_mev,
            thickness_um,
            primary_range_model,
        )
        energy_rows.append(
            {
                **definition,
                "incident_range_mev": interval.incident_range_mev,
                "deposit_range_mev": interval.deposit_range_mev,
                "maximum_particle_range_mm": interval.maximum_particle_range_mm,
                "all_stopped": interval.all_stopped,
                "status": f"derived; {primary_range_model}",
            },
        )

    dc_event_definitions = [
        {
            "key": "dc_deuteron",
            "reaction": "d-C elastic",
            "particle": "deuteron",
            "station": "D",
            "lab_range_deg": d_bounds,
            "significance": "Coincidence geometry remains essential",
            "status": "derived",
        },
        {
            "key": "dc_carbon_small",
            "reaction": "d-C elastic",
            "particle": "carbon",
            "station": "P-small",
            "lab_range_deg": p_small_bounds,
            "significance": "Conservative high-load background",
            "status": "derived, unquenched",
        },
        {
            "key": "dc_carbon_large",
            "reaction": "d-C elastic",
            "particle": "carbon",
            "station": "P-large",
            "lab_range_deg": p_large_bounds,
            "significance": "High-load background",
            "status": "derived, unquenched",
        },
    ]
    for definition in dc_event_definitions:
        interval = compute_dc_loss_interval(
            energy_model,
            range_model,
            definition["lab_range_deg"],
            definition["particle"],
            beam_kinetic_mev,
            thickness_um,
            primary_range_model,
        )
        energy_rows.append(
            {
                **definition,
                "incident_range_mev": interval.incident_range_mev,
                "deposit_range_mev": interval.deposit_range_mev,
                "maximum_particle_range_mm": interval.maximum_particle_range_mm,
                "all_stopped": interval.all_stopped,
                "status": f"{definition['status']}; {primary_range_model}",
            },
        )

    thickness_scan_rows: list[dict[str, Any]] = []
    thickness_summary_rows: list[dict[str, Any]] = []
    for scan_thickness_mm in [float(value) for value in calculation["thickness_scan_mm"]]:
        primary_results: dict[str, EnergyLossInterval] = {}
        all_models_stopped = True
        all_protons_stopped = True
        maximum_model_range_mm = 0.0
        for definition in dp_event_definitions:
            for model_key in envelope_range_models:
                interval = compute_dp_loss_interval(
                    energy_model,
                    range_model,
                    definition["lab_range_deg"],
                    definition["branch"],
                    definition["particle"],
                    beam_kinetic_mev,
                    scan_thickness_mm * 1000.0,
                    model_key,
                )
                thickness_scan_rows.append(
                    {
                        "thickness_mm": scan_thickness_mm,
                        "key": definition["key"],
                        "reaction": definition["reaction"],
                        "particle": definition["particle"],
                        "station": definition["station"],
                        "range_model": model_key,
                        "incident_range_mev": interval.incident_range_mev,
                        "deposit_range_mev": interval.deposit_range_mev,
                        "maximum_particle_range_mm": interval.maximum_particle_range_mm,
                        "all_stopped": interval.all_stopped,
                    },
                )
                all_models_stopped = all_models_stopped and interval.all_stopped
                if definition["particle"] == "proton":
                    all_protons_stopped = all_protons_stopped and interval.all_stopped
                maximum_model_range_mm = max(
                    maximum_model_range_mm,
                    interval.maximum_particle_range_mm,
                )
                if model_key == primary_range_model:
                    primary_results[definition["key"]] = interval

        thickness_summary_rows.append(
            {
                "thickness_mm": scan_thickness_mm,
                "primary_results": {
                    key: value.__dict__ for key, value in primary_results.items()
                },
                "all_models_stopped": all_models_stopped,
                "all_protons_stopped": all_protons_stopped,
                "maximum_model_range_mm": maximum_model_range_mm,
            },
        )

    candidate_summary = next(
        row
        for row in thickness_summary_rows
        if abs(row["thickness_mm"] - candidate_thickness_mm) <= 1.0e-12
    )
    legacy_thickness_mm = float(calculation["legacy_reference_thickness_mm"])
    legacy_summary = next(
        row
        for row in thickness_summary_rows
        if abs(row["thickness_mm"] - legacy_thickness_mm) <= 1.0e-12
    )
    candidate_primary_results = candidate_summary["primary_results"]
    legacy_primary_results = legacy_summary["primary_results"]
    candidate_minimum_deposit_mev = min(
        result["deposit_range_mev"][0]
        for result in candidate_primary_results.values()
    )
    candidate_maximum_deposit_mev = max(
        result["deposit_range_mev"][1]
        for result in candidate_primary_results.values()
    )
    legacy_maximum_deposit_mev = max(
        result["deposit_range_mev"][1]
        for result in legacy_primary_results.values()
    )
    worst_case_normal_range_mm = max(
        row["maximum_model_range_mm"] for row in thickness_summary_rows
    )
    maximum_deposit_reduction_percent = 100.0 * (
        1.0 - candidate_maximum_deposit_mev / legacy_maximum_deposit_mev
    )

    normal_dp_computed = max(
        row["deposit_range_mev"][1] for row in energy_rows if row["reaction"].startswith("d-p")
    )
    carbon_computed = max(
        row["deposit_range_mev"][1] for row in energy_rows if row["particle"] == "carbon"
    )
    energy_tolerance = float(assumptions["verification_tolerances"]["energy_range_mev"])
    reference = assumptions["report_reference_values"]
    record(
        "Candidate thickness agrees with the detailed energy table",
        abs(normal_dp_computed - candidate_maximum_deposit_mev) <= energy_tolerance,
        f"computed={normal_dp_computed:.4f} MeV",
    )
    record(
        "Carbon energy upper bound",
        abs(carbon_computed - float(reference["carbon_upper_deposit_mev"])) <= energy_tolerance,
        f"computed={carbon_computed:.4f} MeV, reference={reference['carbon_upper_deposit_mev']} MeV",
    )
    record(
        "Candidate minimum normal d-p deposit",
        candidate_minimum_deposit_mev
        >= float(calculation["minimum_candidate_deposit_mev"]),
        (
            f"minimum={candidate_minimum_deposit_mev:.4f} MeV, "
            f"threshold={float(calculation['minimum_candidate_deposit_mev']):.4f} MeV"
        ),
    )
    record(
        "Candidate is treated as a delta-E counter rather than a stopping calorimeter",
        not bool(candidate_summary["all_models_stopped"]),
        (
            f"thickness={candidate_thickness_mm:.1f} mm, "
            f"maximum accepted-particle range={worst_case_normal_range_mm:.2f} mm"
        ),
    )
    record(
        "Candidate reduces the maximum normal deposit relative to 10 mm",
        candidate_maximum_deposit_mev < legacy_maximum_deposit_mev,
        (
            f"candidate={candidate_maximum_deposit_mev:.4f} MeV, "
            f"legacy={legacy_maximum_deposit_mev:.4f} MeV"
        ),
    )
    record(
        "Legacy 10 mm maximum normal deposit",
        abs(
            legacy_maximum_deposit_mev
            - float(calculation["legacy_10mm_normal_dp_upper_deposit_mev"])
        )
        <= energy_tolerance,
        (
            f"computed={legacy_maximum_deposit_mev:.4f} MeV, "
            f"reference={float(calculation['legacy_10mm_normal_dp_upper_deposit_mev']):.4f} MeV"
        ),
    )

    light_yield = float(calculation["scintillation_yield_photons_per_mev_ee"])
    normal_energy = candidate_maximum_deposit_mev
    carbon_energy = float(calculation["conservative_carbon_upper_deposit_mev"])
    efficiencies = [float(value) for value in calculation["optical_collection_efficiencies"]]
    saturation_results: list[dict[str, Any]] = []
    for device in assumptions["sipm_devices"]:
        results_by_efficiency: dict[str, SipmResult] = {}
        for efficiency in efficiencies:
            key = f"{int(round(efficiency * 100.0))}pct"
            results_by_efficiency[key] = sipm_response(
                normal_energy,
                light_yield,
                efficiency,
                float(device["pde_fraction"]),
                int(device["microcells"]),
                float(device["gain"]),
            )
        carbon_result = sipm_response(
            carbon_energy,
            light_yield,
            float(calculation["saturation_curve_efficiency"]),
            float(device["pde_fraction"]),
            int(device["microcells"]),
            float(device["gain"]),
        )
        limit = ten_percent_energy_mev(
            light_yield,
            float(calculation["saturation_curve_efficiency"]),
            float(device["pde_fraction"]),
            int(device["microcells"]),
        )
        saturation_results.append(
            {
                "device": device,
                "normal": results_by_efficiency,
                "carbon": carbon_result,
                "ten_percent_limit_mev": limit,
            }
        )

    eqr15 = next(item for item in saturation_results if item["device"]["key"] == "eqr15")
    eqr15_legacy_5pct = sipm_response(
        legacy_maximum_deposit_mev,
        light_yield,
        float(calculation["saturation_curve_efficiency"]),
        float(eqr15["device"]["pde_fraction"]),
        int(eqr15["device"]["microcells"]),
        float(eqr15["device"]["gain"]),
    )
    saturation_tolerance = float(assumptions["verification_tolerances"]["saturation_percent"])
    record(
        "EQR15 candidate-thickness nonlinearity at 5 percent collection",
        eqr15["normal"]["5pct"].nonlinearity_percent
        <= float(calculation["maximum_candidate_eqr15_nonlinearity_percent"])
        + saturation_tolerance,
        (
            f"computed={eqr15['normal']['5pct'].nonlinearity_percent:.4f}%, "
            f"limit={float(calculation['maximum_candidate_eqr15_nonlinearity_percent']):.4f}%"
        ),
    )
    record(
        "EQR15 conservative carbon nonlinearity",
        abs(
            eqr15["carbon"].nonlinearity_percent
            - float(reference["eqr15_carbon_nonlinearity_5pct"])
        )
        <= saturation_tolerance,
        f"computed={eqr15['carbon'].nonlinearity_percent:.4f}%",
    )

    chamber = chamber_metrics(
        float(vessel["inner_size_x_mm"]),
        float(vessel["inner_size_y_mm"]),
        float(vessel["length_mm"]),
        float(vessel["wall_thickness_mm"]),
        float(calculation["stainless_density_g_per_cm3"]),
    )
    pipe_outer = float(vessel["end_modules"]["front"]["pipe_outer_diameter_mm"])
    pipe_inner = float(vessel["end_modules"]["front"]["pipe_inner_diameter_mm"])
    radial_wall = 0.5 * (pipe_outer - pipe_inner)
    beam_bore = float(vessel["beam_bore_diameter_mm"])
    icf = assumptions["icf_screening"]
    icf114_deficit = beam_bore - float(icf["icf114_reference_clear_bore_mm"])
    compact_front_standard = str(vessel["end_modules"]["front"]["standard"])
    compact_rear_standard = str(vessel["end_modules"]["rear"]["standard"])
    interface_classes = assumptions["interface_classification"]
    after_src_interface = interface_classes["compact_afterSRC"]["beam_interfaces"]
    pre_samurai_interface = interface_classes["compact_preSAMURAI"]["beam_interfaces"]
    legacy_after_src_interface = interface_classes["legacy_afterSRC_external"]
    architecture = assumptions["project_architecture"]
    baseline_names = {
        str(item["name"]): str(item["status"])
        for item in architecture["baseline_instruments"]
    }
    legacy_names = {
        str(item["name"]): str(item["status"])
        for item in architecture["legacy_instruments"]
    }
    record(
        "Current beam pipe radial wall arithmetic",
        abs(radial_wall - 0.3) < 1.0e-12,
        f"radial_wall={radial_wall:.3f} mm",
    )
    record(
        "Two CompactInVacuum baseline instruments are declared",
        baseline_names
        == {
            "CompactInVacuum-afterSRC": "baseline",
            "CompactInVacuum-preSAMURAI": "baseline",
        },
        ", ".join(f"{name}={status}" for name, status in baseline_names.items()),
    )
    record(
        "External afterSRC design is legacy/fallback/reference",
        legacy_names.get("legacy afterSRC external-detector design")
        == "legacy/fallback/reference"
        and legacy_after_src_interface["beam_interfaces"]["class"] == "B",
        (
            f"status={legacy_names.get('legacy afterSRC external-detector design')}, "
            f"interface_class={legacy_after_src_interface['beam_interfaces']['class']}"
        ),
    )
    record(
        "Compact deployment beam interfaces remain independently unresolved",
        after_src_interface["class"] == "D"
        and pre_samurai_interface["class"] == "D",
        (
            f"afterSRC={after_src_interface['class']}/{after_src_interface['status']}; "
            f"preSAMURAI={pre_samurai_interface['class']}/{pre_samurai_interface['status']}"
        ),
    )
    record(
        "Legacy numerical CAD interface is labelled as a reference assumption",
        compact_front_standard == str(icf["reference_cad_front_interface"])
        and compact_rear_standard == str(icf["reference_cad_rear_interface"]),
        (
            f"reference CAD front={compact_front_standard}, rear={compact_rear_standard}; "
            "not a compact deployment contract"
        ),
    )
    record(
        "ICF114 purchased-part bore conflict is explicitly detected",
        icf114_deficit > 0.0,
        (
            f"CAD stay-clear exceeds reference purchased-part clear bore by "
            f"{icf114_deficit:.3f} mm in the legacy numerical reference geometry; "
            "no compact deployment interface is inferred"
        ),
    )
    record(
        "ICF-class assembly helium-leak target",
        float(icf["assembly_helium_leak_rate_max_pa_m3_s"]) <= 1.3e-10,
        (
            "acceptance<="
            f"{float(icf['assembly_helium_leak_rate_max_pa_m3_s']):.3e} Pa m^3/s"
        ),
    )

    charge_window_s = float(calculation["effective_charge_window_ns"]) * 1.0e-9
    average_current_a = eqr15["normal"]["5pct"].charge_nc * 1.0e-9 / charge_window_s
    voltage_scale_v = average_current_a * float(calculation["termination_ohm"])
    compact_scale = float(calculation["compact_v2_geometric_scale"])

    source_hashes = {
        key: {
            "path": str(path.relative_to(REPOSITORY_ROOT)),
            "sha256": sha256_file(path),
        }
        for key, path in source_paths.items()
    }
    source_hashes["report_assumptions"] = {
        "path": str(assumptions_path.relative_to(REPOSITORY_ROOT)),
        "sha256": sha256_file(assumptions_path),
    }
    # [EN] Bind generated artifacts to the newest commit that changed an authoritative input, so a later generated-files-only commit does not invalidate its own provenance. / [CN] 将生成物绑定到最近一次修改权威输入的提交，避免随后仅提交生成文件时让来源记录自我失效。
    provenance_source_paths = [
        str(path.relative_to(REPOSITORY_ROOT))
        for path in source_paths.values()
    ]
    provenance_source_paths.append(str(assumptions_path.relative_to(REPOSITORY_ROOT)))
    git_commit = subprocess.run(
        [
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "log",
            "-1",
            "--format=%H",
            "--",
            *provenance_source_paths,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    provenance = {
        "schema_version": 2,
        "git_commit": git_commit,
        "source_hashes": source_hashes,
        "calculation_environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "pyyaml": yaml.__version__,
        },
        "source_validation_status": validation.get("status"),
        "source_detector_decision_state": {
            "active_medium_status": detector["active_medium_status"],
            "active_medium": detector["active_medium"],
            "photosensor_status": detector["photosensor_status"],
            "photosensor": detector["photosensor"],
        },
        "report_recommendation_state": {
            "active_medium": "fast blue plastic scintillator",
            "photosensor": "NDL EQR15 11-6060D-S",
            "candidate_active_thickness_mm": candidate_thickness_mm,
            "status": "proposed prototype baseline; not yet promoted into the CAD configuration",
        },
    }

    derived = {
        "schema_version": 2,
        "git_commit": git_commit,
        "geometry": {
            "beam_energy_mev": beam_kinetic_mev,
            "active_diameter_mm": active_diameter_mm,
            "active_length_mm": active_length_mm,
            "channel_acceptance_lab_deg": {
                key: list(value) for key, value in channel_acceptance.items()
            },
            "coincidence_cm_overlap_deg": {
                "forward": list(forward_cm),
                "backward": list(backward_cm),
            },
            "compact_v2_scaled_radii_mm": {
                key: float(value["radius_mm"]) * compact_scale
                for key, value in channels_cfg.items()
            },
            "compact_v2_active_diameter_mm": active_diameter_mm * compact_scale,
        },
        "energy_deposition": energy_rows,
        "thickness_study": {
            "primary_range_model": primary_range_model,
            "range_model_envelope": envelope_range_models,
            "candidate_thickness_mm": candidate_thickness_mm,
            "legacy_reference_thickness_mm": legacy_thickness_mm,
            "candidate_minimum_deposit_mev": candidate_minimum_deposit_mev,
            "candidate_maximum_deposit_mev": candidate_maximum_deposit_mev,
            "legacy_maximum_deposit_mev": legacy_maximum_deposit_mev,
            "maximum_deposit_reduction_percent": maximum_deposit_reduction_percent,
            "worst_case_normal_particle_range_mm": worst_case_normal_range_mm,
            "candidate_all_protons_stopped": candidate_summary["all_protons_stopped"],
            "candidate_all_particles_stopped": candidate_summary["all_models_stopped"],
            "rows": thickness_summary_rows,
        },
        "sipm": [
            {
                "key": item["device"]["key"],
                "name": item["device"]["name"],
                "normal": {
                    key: result.__dict__ for key, result in item["normal"].items()
                },
                "carbon_5pct": item["carbon"].__dict__,
                "ten_percent_limit_mev": item["ten_percent_limit_mev"],
            }
            for item in saturation_results
        ],
        "electronics": {
            "eqr15_normal_charge_nc": eqr15["normal"]["5pct"].charge_nc,
            "eqr15_legacy_10mm_charge_nc": eqr15_legacy_5pct.charge_nc,
            "eqr15_legacy_10mm_nonlinearity_percent": (
                eqr15_legacy_5pct.nonlinearity_percent
            ),
            "effective_charge_window_ns": float(calculation["effective_charge_window_ns"]),
            "average_current_a": average_current_a,
            "termination_ohm": float(calculation["termination_ohm"]),
            "voltage_scale_v": voltage_scale_v,
            "recommended_low_gain_range_nc": float(
                calculation["minimum_low_gain_charge_range_nc"]
            ),
        },
        "chamber": {
            "outer_size_x_mm": chamber.outer_size_x_mm,
            "outer_size_y_mm": chamber.outer_size_y_mm,
            "length_mm": float(vessel["length_mm"]),
            "closed_shell_material_volume_l": chamber.material_volume_l,
            "screening_mass_kg": chamber.mass_kg,
            "beam_bore_mm": beam_bore,
            "pipe_outer_mm": pipe_outer,
            "pipe_inner_mm": pipe_inner,
            "pipe_radial_wall_mm": radial_wall,
            "icf114_reference_clear_bore_mm": float(
                icf["icf114_reference_clear_bore_mm"]
            ),
            "icf114_stay_clear_deficit_mm": icf114_deficit,
            "assembly_helium_leak_rate_max_pa_m3_s": float(
                icf["assembly_helium_leak_rate_max_pa_m3_s"]
            ),
        },
        "project_architecture": architecture,
        "interface_classification": interface_classes,
        "instrument_interfaces": {
            "legacy_after_src_external": {
                "front": str(icf["legacy_after_src_front_interface"]),
                "rear": str(icf["legacy_after_src_rear_interface"]),
                "rotary_feedthrough": str(icf["legacy_after_src_rotary_interface"]),
                "extra_side_vacuum_ports": False,
                "classification": "B",
            },
            "legacy_numerical_reference_cad": {
                "front": compact_front_standard,
                "rear": compact_rear_standard,
                "adapters_and_bellows_allowed": bool(
                    icf["adapters_and_bellows_allowed"]
                ),
                "classification": "C",
            },
            "compact_after_src": {
                "front": "TBD",
                "rear": "TBD",
                "classification": str(after_src_interface["class"]),
            },
            "compact_pre_samurai": {
                "front": "TBD",
                "rear": "TBD",
                "classification": str(pre_samurai_interface["class"]),
            },
            "vacuum_boundary": {
                "primary_seal": str(icf["primary_seal"]),
                "assembly_helium_leak_rate_max_pa_m3_s": float(
                    icf["assembly_helium_leak_rate_max_pa_m3_s"]
                ),
            },
        },
    }

    energy_csv_rows = [
        [
            row["key"],
            row["reaction"],
            row["particle"],
            row["station"],
            f"{row['lab_range_deg'][0]:.6f}",
            f"{row['lab_range_deg'][1]:.6f}",
            f"{row['deposit_range_mev'][0]:.6f}",
            f"{row['deposit_range_mev'][1]:.6f}",
            row["status"],
        ]
        for row in energy_rows
    ]
    thickness_scan_csv_rows = [
        [
            f"{row['thickness_mm']:.3f}",
            row["key"],
            row["reaction"],
            row["particle"],
            row["station"],
            row["range_model"],
            f"{row['incident_range_mev'][0]:.6f}",
            f"{row['incident_range_mev'][1]:.6f}",
            f"{row['deposit_range_mev'][0]:.6f}",
            f"{row['deposit_range_mev'][1]:.6f}",
            f"{row['maximum_particle_range_mm']:.6f}",
            str(row["all_stopped"]).lower(),
        ]
        for row in thickness_scan_rows
    ]
    thickness_summary_csv_rows = []
    for row in thickness_summary_rows:
        primary_results = row["primary_results"]
        thickness_summary_csv_rows.append(
            [
                f"{row['thickness_mm']:.3f}",
                f"{primary_results['forward_dp_deuteron']['deposit_range_mev'][0]:.6f}",
                f"{primary_results['forward_dp_deuteron']['deposit_range_mev'][1]:.6f}",
                f"{primary_results['forward_dp_proton']['deposit_range_mev'][0]:.6f}",
                f"{primary_results['forward_dp_proton']['deposit_range_mev'][1]:.6f}",
                f"{primary_results['backward_dp_deuteron']['deposit_range_mev'][0]:.6f}",
                f"{primary_results['backward_dp_deuteron']['deposit_range_mev'][1]:.6f}",
                f"{primary_results['backward_dp_proton']['deposit_range_mev'][0]:.6f}",
                f"{primary_results['backward_dp_proton']['deposit_range_mev'][1]:.6f}",
                str(row["all_models_stopped"]).lower(),
                str(row["all_protons_stopped"]).lower(),
                f"{row['maximum_model_range_mm']:.6f}",
            ],
        )
    sipm_csv_rows = []
    for item in saturation_results:
        sipm_csv_rows.append(
            [
                item["device"]["key"],
                item["device"]["name"],
                item["device"]["microcells"],
                item["device"]["pde_fraction"],
                item["device"]["gain"],
                f"{item['normal']['2pct'].nonlinearity_percent:.6f}",
                f"{item['normal']['5pct'].nonlinearity_percent:.6f}",
                f"{item['normal']['5pct'].charge_nc:.6f}",
                f"{item['carbon'].nonlinearity_percent:.6f}",
                f"{item['ten_percent_limit_mev']:.6f}",
            ]
        )

    curve_points = int(calculation["saturation_curve_points"])
    curve_energy = np.linspace(
        0.05,
        float(calculation["saturation_curve_energy_max_mev"]),
        curve_points,
    )
    curve_header = ["energy_mev"] + [
        f"{device['key']}_nonlinearity_pct" for device in assumptions["sipm_devices"]
    ]
    curve_rows: list[list[str]] = []
    for energy in curve_energy:
        row = [f"{energy:.6f}"]
        for device in assumptions["sipm_devices"]:
            result = sipm_response(
                float(energy),
                light_yield,
                float(calculation["saturation_curve_efficiency"]),
                float(device["pde_fraction"]),
                int(device["microcells"]),
                float(device["gain"]),
            )
            row.append(f"{result.nonlinearity_percent:.6f}")
        curve_rows.append(row)

    macros = "\n".join(
        [
            "% Generated by scripts/generate_report_data.py; do not edit.",
            rf"\newcommand{{\ReportGitCommit}}{{\detokenize{{{git_commit}}}}}",
            rf"\newcommand{{\BeamEnergyMeV}}{{{beam_kinetic_mev:.1f}}}",
            rf"\newcommand{{\ActiveDiameterMm}}{{{active_diameter_mm:.1f}}}",
            rf"\newcommand{{\ActiveLengthMm}}{{{active_length_mm:.1f}}}",
            rf"\newcommand{{\ActiveThicknessMm}}{{{candidate_thickness_mm:.1f}}}",
            rf"\newcommand{{\LegacyThicknessMm}}{{{float(calculation['legacy_reference_thickness_mm']):.1f}}}",
            rf"\newcommand{{\CandidateMinimumDepositMeV}}{{{candidate_minimum_deposit_mev:.2f}}}",
            rf"\newcommand{{\CandidateMaximumDepositMeV}}{{{candidate_maximum_deposit_mev:.2f}}}",
            rf"\newcommand{{\LegacyMaximumDepositMeV}}{{{legacy_maximum_deposit_mev:.2f}}}",
            rf"\newcommand{{\MaximumDepositReductionPercent}}{{{maximum_deposit_reduction_percent:.0f}}}",
            rf"\newcommand{{\WorstCaseNormalRangeMm}}{{{worst_case_normal_range_mm:.2f}}}",
            rf"\newcommand{{\LisePrimaryRangeModel}}{{{tex_escape(range_model.RANGE_MODELS_BY_KEY[primary_range_model].label)}}}",
            rf"\newcommand{{\ForwardCmLow}}{{{forward_cm[0]:.2f}}}",
            rf"\newcommand{{\ForwardCmHigh}}{{{forward_cm[1]:.2f}}}",
            rf"\newcommand{{\BackwardCmLow}}{{{backward_cm[0]:.2f}}}",
            rf"\newcommand{{\BackwardCmHigh}}{{{backward_cm[1]:.2f}}}",
            rf"\newcommand{{\EqrNormalNonlinearityTwo}}{{{eqr15['normal']['2pct'].nonlinearity_percent:.2f}}}",
            rf"\newcommand{{\EqrNormalNonlinearityFive}}{{{eqr15['normal']['5pct'].nonlinearity_percent:.2f}}}",
            rf"\newcommand{{\EqrNormalCharge}}{{{eqr15['normal']['5pct'].charge_nc:.3f}}}",
            rf"\newcommand{{\EqrLegacyNormalNonlinearityFive}}{{{eqr15_legacy_5pct.nonlinearity_percent:.2f}}}",
            rf"\newcommand{{\EqrLegacyNormalCharge}}{{{eqr15_legacy_5pct.charge_nc:.3f}}}",
            rf"\newcommand{{\EqrCarbonNonlinearity}}{{{eqr15['carbon'].nonlinearity_percent:.2f}}}",
            rf"\newcommand{{\FrontEndAverageCurrentMilliAmp}}{{{average_current_a * 1.0e3:.1f}}}",
            rf"\newcommand{{\FrontEndVoltageScale}}{{{voltage_scale_v:.2f}}}",
            rf"\newcommand{{\LowGainRangeNc}}{{{float(calculation['minimum_low_gain_charge_range_nc']):.1f}}}",
            rf"\newcommand{{\ChamberMaterialVolumeL}}{{{chamber.material_volume_l:.2f}}}",
            rf"\newcommand{{\ChamberScreeningMassKg}}{{{chamber.mass_kg:.1f}}}",
            rf"\newcommand{{\PipeRadialWallMm}}{{{radial_wall:.2f}}}",
            rf"\newcommand{{\IcfOneOneFourDeficitMm}}{{{icf114_deficit:.1f}}}",
            rf"\newcommand{{\IcfAssemblyLeakMantissa}}{{{float(icf['assembly_helium_leak_rate_max_pa_m3_s']) * 1.0e10:.1f}}}",
            rf"\newcommand{{\CompactScaledDeuteronRadius}}{{{channels_cfg['deuteron']['radius_mm'] * compact_scale:.0f}}}",
            rf"\newcommand{{\CompactScaledProtonSmallRadius}}{{{channels_cfg['proton_small']['radius_mm'] * compact_scale:.0f}}}",
            rf"\newcommand{{\CompactScaledProtonLargeRadius}}{{{channels_cfg['proton_large']['radius_mm'] * compact_scale:.0f}}}",
            rf"\newcommand{{\CompactScaledActiveDiameter}}{{{active_diameter_mm * compact_scale:.0f}}}",
            rf"\newcommand{{\SourceValidationStatus}}{{{tex_escape(str(validation.get('status')).upper())}}}",
            "",
        ]
    )

    geometry_tex_lines = [
        "% Generated data rows; table rules and headings are owned by the report source.",
    ]
    station_names = {
        "deuteron": "D",
        "proton_small": "P-small",
        "proton_large": "P-large",
    }
    for name in ("deuteron", "proton_small", "proton_large"):
        channel = channels_cfg[name]
        bounds = channel_acceptance[name]
        geometry_tex_lines.append(
            f"{station_names[name]} & {tex_escape(str(channel['particle']).capitalize())} & "
            f"{float(channel['angle_deg']):.1f} & {float(channel['radius_mm']):.1f} & "
            f"{bounds[0]:.2f}--{bounds[1]:.2f} \\\\"
        )
    geometry_tex_lines.extend([r"\bottomrule", ""])

    particle_labels_zh = {
        "deuteron": "氘核",
        "proton": "质子",
        "carbon": "碳核",
    }
    geometry_tex_lines_zh = [
        "% [EN] Generated Chinese data rows; table rules and headings are owned by the report source. / [CN] 自动生成的中文数据行；表格线与表头由报告源文件控制。",
    ]
    for name in ("deuteron", "proton_small", "proton_large"):
        channel = channels_cfg[name]
        bounds = channel_acceptance[name]
        geometry_tex_lines_zh.append(
            f"{station_names[name]} & {particle_labels_zh[str(channel['particle'])]} & "
            f"{float(channel['angle_deg']):.1f} & {float(channel['radius_mm']):.1f} & "
            f"{bounds[0]:.2f}--{bounds[1]:.2f} \\\\"
        )
    geometry_tex_lines_zh.extend([r"\bottomrule", ""])

    energy_tex_lines = [
        "% Generated data rows; table rules and headings are owned by the report source.",
    ]
    for row in energy_rows:
        energy_tex_lines.append(
            f"{tex_escape(row['reaction'])}, {tex_escape(row['particle'])} & "
            f"{tex_escape(row['station'])} & "
            f"{row['lab_range_deg'][0]:.2f}--{row['lab_range_deg'][1]:.2f} & "
            f"{row['deposit_range_mev'][0]:.2f}--{row['deposit_range_mev'][1]:.2f} & "
            f"{tex_escape(row['status'])} \\\\"
        )
    energy_tex_lines.extend([r"\bottomrule", ""])

    reaction_labels_zh = {
        "d-p forward": "d--p 前向支",
        "d-p backward": "d--p 后向支",
        "d-C elastic": "d--C 弹性散射",
    }
    energy_tex_lines_zh = [
        "% [EN] Generated Chinese data rows; table rules and headings are owned by the report source. / [CN] 自动生成的中文数据行；表格线与表头由报告源文件控制。",
    ]
    for row in energy_rows:
        status_zh = "计算值；未施加 Birks 淬灭" if "unquenched" in row["status"] else "计算值"
        energy_tex_lines_zh.append(
            f"{reaction_labels_zh[row['reaction']]}，{particle_labels_zh[row['particle']]} & "
            f"{tex_escape(row['station'])} & "
            f"{row['lab_range_deg'][0]:.2f}--{row['lab_range_deg'][1]:.2f} & "
            f"{row['deposit_range_mev'][0]:.2f}--{row['deposit_range_mev'][1]:.2f} & "
            f"{status_zh} \\\\"
        )
    energy_tex_lines_zh.extend([r"\bottomrule", ""])

    thickness_tex_lines = [
        "% Generated data rows; table rules and headings are owned by the report source.",
    ]
    thickness_tex_lines_zh = [
        "% [EN] Generated Chinese data rows; table rules and headings are owned by the report source. / [CN] 自动生成的中文数据行；表格线与表头由报告源文件控制。",
    ]
    for row in thickness_summary_rows:
        primary_results = row["primary_results"]
        if abs(row["thickness_mm"] - candidate_thickness_mm) <= 1.0e-12:
            role_label = "candidate"
            role_label_zh = "候选"
        elif abs(row["thickness_mm"] - legacy_thickness_mm) <= 1.0e-12:
            role_label = "legacy"
            role_label_zh = "旧方案"
        else:
            role_label = "scan"
            role_label_zh = "扫描"
        row_values = (
            f"{row['thickness_mm']:.0f} & "
            f"{primary_results['forward_dp_deuteron']['deposit_range_mev'][0]:.2f}--"
            f"{primary_results['forward_dp_deuteron']['deposit_range_mev'][1]:.2f} & "
            f"{primary_results['forward_dp_proton']['deposit_range_mev'][0]:.2f}--"
            f"{primary_results['forward_dp_proton']['deposit_range_mev'][1]:.2f} & "
            f"{primary_results['backward_dp_deuteron']['deposit_range_mev'][0]:.2f}--"
            f"{primary_results['backward_dp_deuteron']['deposit_range_mev'][1]:.2f} & "
            f"{primary_results['backward_dp_proton']['deposit_range_mev'][0]:.2f}--"
            f"{primary_results['backward_dp_proton']['deposit_range_mev'][1]:.2f}"
        )
        thickness_tex_lines.append(f"{row_values} & {role_label} \\\\")
        thickness_tex_lines_zh.append(f"{row_values} & {role_label_zh} \\\\")
    thickness_tex_lines.extend([r"\bottomrule", ""])
    thickness_tex_lines_zh.extend([r"\bottomrule", ""])

    device_tex_lines = [
        "% Generated data rows; table rules and headings are owned by the report source.",
    ]
    for device in assumptions["sipm_devices"]:
        device_tex_lines.append(
            f"{tex_escape(device['name'])} & "
            f"{device['active_area_mm'][0]:.2f}$\\times${device['active_area_mm'][1]:.2f} & "
            f"{float(device['pitch_um']):.0f} & {int(device['microcells']):,} & "
            f"{100.0 * float(device['pde_fraction']):.1f}\\% & {tex_escape(device['role'])} \\\\"
        )
    device_tex_lines.extend([r"\bottomrule", ""])

    device_role_labels_zh = {
        "Recommended baseline": "推荐基准",
        "Higher-gain backup": "高增益备选",
        "Imported reference": "进口参考",
        "Comparison only": "仅用于比较",
    }
    device_tex_lines_zh = [
        "% [EN] Generated Chinese data rows; table rules and headings are owned by the report source. / [CN] 自动生成的中文数据行；表格线与表头由报告源文件控制。",
    ]
    for device in assumptions["sipm_devices"]:
        device_tex_lines_zh.append(
            f"{tex_escape(device['name'])} & "
            f"{device['active_area_mm'][0]:.2f}$\\times${device['active_area_mm'][1]:.2f} & "
            f"{float(device['pitch_um']):.0f} & {int(device['microcells']):,} & "
            f"{100.0 * float(device['pde_fraction']):.1f}\\% & "
            f"{device_role_labels_zh[device['role']]} \\\\"
        )
    device_tex_lines_zh.extend([r"\bottomrule", ""])

    saturation_tex_lines = [
        "% Generated data rows; table rules and headings are owned by the report source.",
    ]
    for item in saturation_results:
        saturation_tex_lines.append(
            f"{tex_escape(item['device']['name'])} & "
            f"{item['normal']['2pct'].nonlinearity_percent:.1f}\\% & "
            f"{item['normal']['5pct'].nonlinearity_percent:.1f}\\% & "
            f"{item['normal']['5pct'].charge_nc:.3f} & "
            f"{item['carbon'].nonlinearity_percent:.1f}\\% & "
            f"{item['ten_percent_limit_mev']:.1f} \\\\"
        )
    saturation_tex_lines.extend([r"\bottomrule", ""])

    provenance_tex_lines = [
        "% Generated data rows; table rules and headings are owned by the report source.",
    ]
    for key, item in source_hashes.items():
        provenance_tex_lines.append(
            f"{tex_escape(key.replace('_', ' '))} & "
            rf"\path{{{item['path']}}} & "
            rf"\texttt{{{item['sha256'][:12]}\ldots}} \\"
        )
    provenance_tex_lines.extend([r"\bottomrule", ""])

    provenance_role_labels_zh = {
        "compact_architecture_baseline": "紧凑型架构基线",
        "compact_platform_common": "公共探测器平台配置",
        "compact_after_src_profile": "afterSRC 紧凑型部署配置",
        "compact_pre_samurai_profile": "pre-SAMURAI 紧凑型部署配置",
        "compact_config": "紧凑型配置",
        "compact_target": "靶系统配置",
        "channel_manifest": "通道清单",
        "validation_report": "验证报告",
        "analysis_scenario": "分析场景",
        "energy_model": "能损模型",
        "lise_range_model": "LISE 射程模型",
        "mechanical_baseline": "机械需求基线",
        "report_source_en": "英文报告源文件",
        "report_source_zh": "中文报告源文件",
        "report_generator": "报告数据生成器",
        "report_makefile": "报告构建工作流",
        "report_assumptions": "报告假设",
    }
    provenance_tex_lines_zh = [
        "% [EN] Generated Chinese data rows; table rules and headings are owned by the report source. / [CN] 自动生成的中文数据行；表格线与表头由报告源文件控制。",
    ]
    for key, item in source_hashes.items():
        provenance_tex_lines_zh.append(
            f"{provenance_role_labels_zh[key]} & "
            rf"\path{{{item['path']}}} & "
            rf"\texttt{{{item['sha256'][:12]}\ldots}} \\"
        )
    provenance_tex_lines_zh.extend([r"\bottomrule", ""])

    summary_lines = [
        "CompactInVacuum common-platform report numerical verification",
        f"OVERALL: {'FAIL' if failures else 'PASS'}",
        f"Git commit: {git_commit}",
        f"Source validation status: {validation.get('status')}",
        (
            "CAD detector decision state: "
            f"active_medium={detector['active_medium']} ({detector['active_medium_status']}), "
            f"photosensor={detector['photosensor']} ({detector['photosensor_status']})"
        ),
        "Report detector proposal: fast blue plastic scintillator + NDL EQR15 11-6060D-S",
        (
            "Thickness study: "
            f"primary={primary_range_model}, "
            f"candidate={candidate_thickness_mm:.1f} mm, "
            f"candidate deposit={candidate_minimum_deposit_mev:.4f}-"
            f"{candidate_maximum_deposit_mev:.4f} MeV, "
            f"legacy maximum={legacy_maximum_deposit_mev:.4f} MeV"
        ),
        (
            "Project baseline: CompactInVacuum-afterSRC + "
            "CompactInVacuum-preSAMURAI; legacy afterSRC external=reference/fallback"
        ),
        (
            "Compact beam interfaces: afterSRC=D/TBD; preSAMURAI=D/TBD; "
            f"legacy numerical reference CAD={compact_front_standard}/{compact_rear_standard}"
        ),
        "",
        "Checks:",
        *checks,
        "",
        "Reproduction command:",
        "micromamba run -n anaroot-env python scripts/generate_report_data.py --check",
        "",
    ]

    outputs = {
        "provenance.json": json_text(provenance),
        "derived_results.json": json_text(derived),
        "energy_deposition.csv": csv_text(
            [
                "key",
                "reaction",
                "particle",
                "station",
                "lab_angle_min_deg",
                "lab_angle_max_deg",
                "deposit_min_mev",
                "deposit_max_mev",
                "status",
            ],
            energy_csv_rows,
        ),
        "thickness_scan.csv": csv_text(
            [
                "thickness_mm",
                "key",
                "reaction",
                "particle",
                "station",
                "range_model",
                "incident_min_mev",
                "incident_max_mev",
                "deposit_min_mev",
                "deposit_max_mev",
                "maximum_particle_range_mm",
                "all_stopped",
            ],
            thickness_scan_csv_rows,
        ),
        "thickness_summary.csv": csv_text(
            [
                "thickness_mm",
                "forward_d_deposit_min_mev",
                "forward_d_deposit_max_mev",
                "forward_p_deposit_min_mev",
                "forward_p_deposit_max_mev",
                "backward_d_deposit_min_mev",
                "backward_d_deposit_max_mev",
                "backward_p_deposit_min_mev",
                "backward_p_deposit_max_mev",
                "all_models_stopped",
                "all_protons_stopped",
                "maximum_model_range_mm",
            ],
            thickness_summary_csv_rows,
        ),
        "sipm_saturation.csv": csv_text(
            [
                "key",
                "device",
                "microcells",
                "pde_fraction",
                "gain",
                "normal_nonlinearity_2pct",
                "normal_nonlinearity_5pct",
                "normal_charge_5pct_nc",
                "carbon_nonlinearity_5pct",
                "ten_percent_limit_5pct_mev",
            ],
            sipm_csv_rows,
        ),
        "sipm_curve.csv": csv_text(curve_header, curve_rows),
        "macros.tex": macros,
        "geometry_table.tex": "\n".join(geometry_tex_lines),
        "geometry_table_zh.tex": "\n".join(geometry_tex_lines_zh),
        "energy_table.tex": "\n".join(energy_tex_lines),
        "energy_table_zh.tex": "\n".join(energy_tex_lines_zh),
        "thickness_table.tex": "\n".join(thickness_tex_lines),
        "thickness_table_zh.tex": "\n".join(thickness_tex_lines_zh),
        "sipm_device_table.tex": "\n".join(device_tex_lines),
        "sipm_device_table_zh.tex": "\n".join(device_tex_lines_zh),
        "saturation_table.tex": "\n".join(saturation_tex_lines),
        "provenance_table.tex": "\n".join(provenance_tex_lines),
        "provenance_table_zh.tex": "\n".join(provenance_tex_lines_zh),
        "verification_summary.txt": "\n".join(summary_lines),
    }
    return outputs, failures


def write_or_check(outputs: dict[str, str], output_dir: Path, check_only: bool) -> list[str]:
    stale: list[str] = []
    if check_only:
        for name, expected in outputs.items():
            path = output_dir / name
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                stale.append(name)
        return stale

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    return stale


def main() -> int:
    args = parse_args()
    assumptions_path = args.assumptions.resolve()
    output_dir = args.output_dir.resolve()
    outputs, numerical_failures = make_outputs(assumptions_path)
    stale = write_or_check(outputs, output_dir, args.check)

    if args.check:
        if stale:
            print("Generated report data are stale or missing:")
            for name in stale:
                print(f"  {name}")
        else:
            print("Generated report data match current inputs.")
    else:
        print(f"Wrote {len(outputs)} generated report files to {output_dir}")

    if numerical_failures:
        print("Numerical verification failures:")
        for name in numerical_failures:
            print(f"  {name}")
    return 1 if stale or numerical_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
