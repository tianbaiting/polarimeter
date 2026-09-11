from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def prepare_scenario(source: Path, destination: Path) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    with source.open() as stream:
        config.read_file(stream)
    # [EN] Resolve inherited paths before writing a scratch scenario elsewhere. / [CN] 在其他目录写临时配置前先解析原配置的相对路径。
    for section, key in (
        ("data", "observables_dir"),
        ("data", "energy_range_file"),
        ("geometry_contract", "source_config"),
    ):
        config[section][key] = str((source.parent / config[section][key]).resolve())
    config["meta"]["scenario_name"] = "pis_pyy_confidence"
    config["run"]["duration_s"] = "10.0"
    config["run"]["duration_s_list"] = "10.0, 60.0"
    # [EN] Keep the physical fit domain while displaying only positive true polarization. / [CN] 保留完整物理拟合域，图中仅扫描非负真实极化。
    config["scan"]["polarization_min"] = "-2.0"
    config["scan"]["polarization_max"] = "1.0"
    config["scan"]["polarization_steps"] = "300"
    with destination.open("w") as stream:
        config.write(stream)
    return config


def read_and_validate(csv_path: Path) -> np.ndarray:
    rows = np.genfromtxt(csv_path, delimiter=",", names=True, dtype=None, encoding="utf-8")
    rows = rows[(rows["true_polarization"] >= 0.0) & (rows["true_polarization"] <= 1.0)]
    if len(rows) != 101:
        raise RuntimeError(f"Expected 101 displayed truth points in {csv_path}")
    np.testing.assert_allclose(rows["mle"], rows["true_polarization"], atol=3e-6, rtol=0)
    assert np.all(rows["ci95_low"] <= rows["ci68_low"])
    assert np.all(rows["ci68_low"] <= rows["mle"] + 1e-7)
    assert np.all(rows["ci68_high"] >= rows["mle"] - 1e-7)
    assert np.all(rows["ci95_high"] >= rows["ci68_high"])
    assert np.all(rows["ci95_low"] >= -2.0)
    assert np.all(rows["ci95_high"] <= 1.0)
    # [EN] Independently check the likelihood-ratio thresholds at free endpoints. / [CN] 独立检查未触及物理边界的端点是否满足似然比阈值。
    first0, second0 = rows[0]["observed_first_count"], rows[0]["observed_second_count"]
    first_slope = rows[-1]["observed_first_count"] - first0
    second_slope = rows[-1]["observed_second_count"] - second0
    for index in (0, 50, 80, 100):
        row = rows[index]
        count_lr, count_ud = row["observed_first_count"], row["observed_second_count"]
        q_true = count_lr / (count_lr + count_ud)
        for label, threshold in (("ci68", 1.0), ("ci95", 3.841458820694124)):
            for end in ("low", "high"):
                value = row[f"{label}_{end}"]
                if value <= -2.0 + 1e-7 or value >= 1.0 - 1e-7:
                    continue
                lr = first0 + first_slope * value
                ud = second0 + second_slope * value
                q = lr / (lr + ud)
                ratio = 2 * (count_lr * np.log(q_true / q) + count_ud * np.log((1-q_true) / (1-q)))
                if abs(ratio - threshold) > 2e-5:
                    raise RuntimeError(f"Incorrect {label} threshold at truth={row['true_polarization']}")
    return rows


def draw(rows: np.ndarray, duration: int, output: Path, preview: Path, config: configparser.ConfigParser) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 14,
                         "axes.labelsize": 17, "axes.titlesize": 20, "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(12.8, 4.5))
    truth = rows["true_polarization"]
    ax.fill_between(truth, rows["ci95_low"], rows["ci95_high"], color="#B9DCE3", label="95% nominal CI")
    ax.fill_between(truth, rows["ci68_low"], rows["ci68_high"], color="#258F9C", alpha=0.90, label="68.3% nominal CI")
    ax.plot(truth, rows["mle"], color="#16324D", linewidth=1.8, linestyle="--", label="Asimov best fit = truth")
    ax.axhline(1.0, color="#78858D", linewidth=0.8)
    ax.set(xlim=(0, 1), ylim=(-0.38, 1.07), xlabel=r"True $p_{yy}$", ylabel=r"Inferred $p_{yy}$ interval")
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_yticks(np.arange(-0.2, 1.01, 0.2))
    ax.grid(alpha=0.18)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=12)
    ax.set_title(f"{duration} s exposure", loc="left", fontweight="bold", color="#16324D", pad=12)
    target = config.getfloat("target", "areal_density_g_per_m2") / 10.0
    rate = config.getfloat("run", "beam_current_amp") / config.getfloat("run", "electron_charge_c")
    energy = config.getfloat("beam", "kinetic_energy_mev") / 2.0
    context = rf"{energy:g} MeV/u,   {rate/1e7:.3f} $\times 10^7$ d/s,   CH$_2$: {target:g} mg/cm$^2$ (provisional)"
    fig.text(0.09, 0.975, context, va="top", fontsize=11, color="#586974")
    fig.text(0.09, 0.017, "Expected counts (Asimov), statistical only. Physical fit range: −2 ≤ pyy ≤ 1.", fontsize=10, color="#586974")
    fig.subplots_adjust(left=0.09, right=0.985, top=0.79, bottom=0.19)
    fig.savefig(output, metadata={"Title": f"Expected pyy confidence intervals, {duration} s", "Creator": "DPOLAR current_tensor profile likelihood"})
    fig.savefig(preview, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot current-design Asimov pyy intervals at 10 and 60 seconds.")
    parser.add_argument("--scenario", type=Path, default=ROOT / "code/config/current_tensor.ini")
    parser.add_argument("--tool", type=Path, default=ROOT / "code/build/dpol_tool")
    parser.add_argument("--output-dir", type=Path, default=HERE)
    parser.add_argument("--work-dir", type=Path, default=HERE / "build/pyy-confidence")
    args = parser.parse_args()
    source, binary = args.scenario.resolve(), args.tool.resolve()
    output, work = args.output_dir.resolve(), args.work_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    config_path = work / "scenario.ini"
    config = prepare_scenario(source, config_path)
    command = [str(binary), "lrud", "--scenario", str(config_path), "--observable", "coincidence", "--output-dir", str(work / "raw")]
    with (work / "dpol.log").open("w") as log:
        subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    tables = {}
    for duration in (10, 60):
        duration_label = "1min" if duration == 60 else f"{duration}s"
        csv_path = work / "raw/pis_pyy_confidence/lrud_coincidence" / duration_label / "inference_scan.csv"
        tables[duration] = read_and_validate(csv_path)
        draw(tables[duration], duration, output / f"pyy_confidence_{duration}s.pdf", work / f"pyy_confidence_{duration}s.png", config)
    np.testing.assert_allclose(tables[60]["observed_total_count"], 6 * tables[10]["observed_total_count"], rtol=1e-9)
    assert np.all(tables[60]["ci95_low"] >= tables[10]["ci95_low"] - 1e-8)
    assert np.all(tables[60]["ci95_high"] <= tables[10]["ci95_high"] + 1e-8)
    summary = {"source_config": str(source), "config_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "command": command, "observable": "coincidence", "method": "Asimov conditional-binomial profile likelihood",
               "confidence_levels": [0.682689492137, 0.95], "delta_minus_two_logL": [1.0, 3.841458820694124],
               "fit_range": [-2.0, 1.0], "displayed_truth_range": [0.0, 1.0],
               "assumptions": ["Fixed analyzing powers and relative LR/UD response", "Unit detector efficiency and live time",
                               "No background or target energy-loss correction", "Existing 20x20 mm acceptance approximation"], "examples": {}}
    tex = ["% [EN] Values from the C++ Asimov inference scan. / [CN] 数值来自 C++ 典型数据推断扫描。"]
    for duration, tag in ((10, "Ten"), (60, "Sixty")):
        selected = {}
        for index in (0, 50, 80, 100):
            row = tables[duration][index]
            selected[str(row["true_polarization"])] = {name: float(row[name]) for name in ("mle", "observed_total_count", "ci68_low", "ci68_high", "ci95_low", "ci95_high")}
        summary["examples"][str(duration)] = selected
        for index, suffix in ((80, "AtEight"), (100, "AtOne")):
            row = tables[duration][index]
            for key, label in (("observed_total_count", "Count"), ("ci68_low", "LowA"), ("ci68_high", "HighA"), ("ci95_low", "LowB"), ("ci95_high", "HighB")):
                value = f"{row[key]:.1f}" if label == "Count" else f"{row[key]:.3f}"
                tex.append(r"\newcommand{\Pyy" + tag + suffix + label + "}{" + value + "}")
    (work / "precision-values.tex").write_text("\n".join(tex) + "\n")
    (work / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["examples"], indent=2))


if __name__ == "__main__":
    main()
