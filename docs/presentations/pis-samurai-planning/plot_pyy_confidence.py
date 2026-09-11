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


def prepare_scenario(source: Path, destination: Path, count_scale: int) -> configparser.ConfigParser:
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
    # [EN] A normalization-only change multiplies expected counts without changing the response shape. / [CN] 仅改变归一化以放大期望计数，不改变响应形状。
    config["run"]["beam_current_amp"] = str(config.getfloat("run", "beam_current_amp") * count_scale)
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


def draw(rows: np.ndarray, duration: int, output: Path, preview: Path, config: configparser.ConfigParser, count_scale: int) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12,
                         "axes.labelsize": 16, "axes.titlesize": 17, "pdf.fonttype": 42})
    fig, ax = plt.subplots(figsize=(6.8, 4.25))
    truth = rows["true_polarization"]
    ax.fill_between(truth, rows["ci95_low"], rows["ci95_high"], color="#B9DCE3", label="95% nominal CI")
    ax.fill_between(truth, rows["ci68_low"], rows["ci68_high"], color="#258F9C", alpha=0.90, label="68.3% nominal CI")
    ax.plot(truth, rows["mle"], color="#16324D", linewidth=1.8, linestyle="--", label="Best fit (Asimov)")
    ax.axhline(1.0, color="#78858D", linewidth=0.8)
    ax.set(xlim=(0, 1), ylim=(-0.38, 1.07), xlabel=r"True $p_{yy}$", ylabel=r"Inferred $p_{yy}$ interval")
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_yticks(np.arange(-0.2, 1.01, 0.2))
    ax.grid(alpha=0.18)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    ax.set_title(f"{duration} s exposure", loc="left", fontweight="bold", color="#16324D", pad=12)
    exponent = 7 + int(np.log10(count_scale))
    context = rf"Counts $\times {count_scale}$,  $I_{{\rm pol}} \simeq 10^{{{exponent}}}$ d/s"
    fig.text(0.145, 0.975, context, va="top", fontsize=11, color="#586974")
    transmission = "Reference intensity" if count_scale == 1 else f"Downstream ATT/slit transmission: 1/{count_scale}"
    fig.text(0.145, 0.925, transmission, va="top", fontsize=10, color="#586974")
    fig.text(0.145, 0.018, "Asimov, statistics only. Fit domain: −2 ≤ pyy ≤ 1.", fontsize=9, color="#586974")
    fig.subplots_adjust(left=0.145, right=0.98, top=0.76, bottom=0.20)
    fig.savefig(output, metadata={"Title": f"Expected pyy confidence intervals, {duration} s, counts x{count_scale}", "Creator": "DPOLAR current_tensor profile likelihood"})
    fig.savefig(preview, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot Asimov pyy intervals at 10 and 60 seconds with count scales 1, 10, and 100.")
    parser.add_argument("--scenario", type=Path, default=ROOT / "code/config/current_tensor.ini")
    parser.add_argument("--tool", type=Path, default=ROOT / "code/build/dpol_tool")
    parser.add_argument("--output-dir", type=Path, default=HERE)
    parser.add_argument("--work-dir", type=Path, default=HERE / "build/pyy-confidence")
    args = parser.parse_args()
    source, binary = args.scenario.resolve(), args.tool.resolve()
    output, work = args.output_dir.resolve(), args.work_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    all_tables = {}
    commands = []
    tex = ["% [EN] Values from the C++ Asimov inference scan. / [CN] 数值来自 C++ 典型数据推断扫描。"]
    summary = {"source_config": str(source), "config_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "observable": "coincidence", "method": "Asimov conditional-binomial profile likelihood",
               "confidence_levels": [0.682689492137, 0.95], "delta_minus_two_logL": [1.0, 3.841458820694124],
               "fit_range": [-2.0, 1.0], "displayed_truth_range": [0.0, 1.0],
               "count_scales": [1, 10, 100], "durations_s": [10, 60],
               "assumptions": ["Only count normalization changes", "Fixed analyzing powers and relative LR/UD response",
                               "Unit detector efficiency and live time", "No background or target energy-loss correction",
                               "Existing 20x20 mm acceptance approximation",
                               "Higher polarimeter intensity assumes attenuation downstream of polarimeter and upstream of F3"],
               "examples": {}}
    for count_scale, macro_prefix in ((1, ""), (10, "GainTen"), (100, "GainHundred")):
        case_work = work / f"x{count_scale}"
        case_work.mkdir(parents=True, exist_ok=True)
        config_path = case_work / "scenario.ini"
        config = prepare_scenario(source, config_path, count_scale)
        command = [str(binary), "lrud", "--scenario", str(config_path), "--observable", "coincidence", "--output-dir", str(case_work / "raw")]
        commands.append(command)
        with (case_work / "dpol.log").open("w") as log:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        tables = {}
        for duration in (10, 60):
            duration_label = "1min" if duration == 60 else f"{duration}s"
            csv_path = case_work / "raw/pis_pyy_confidence/lrud_coincidence" / duration_label / "inference_scan.csv"
            tables[duration] = read_and_validate(csv_path)
            suffix = "" if count_scale == 1 else f"_x{count_scale}"
            basename = f"pyy_confidence{suffix}_{duration}s"
            draw(tables[duration], duration, output / f"{basename}.pdf", work / f"{basename}.png", config, count_scale)
            if count_scale > 1:
                for column in ("observed_first_count", "observed_second_count", "observed_total_count"):
                    np.testing.assert_allclose(tables[duration][column], count_scale * all_tables[1][duration][column], rtol=1e-9)
                assert np.all(tables[duration]["ci95_low"] >= all_tables[1][duration]["ci95_low"] - 1e-8)
                assert np.all(tables[duration]["ci95_high"] <= all_tables[1][duration]["ci95_high"] + 1e-8)
        np.testing.assert_allclose(tables[60]["observed_total_count"], 6 * tables[10]["observed_total_count"], rtol=1e-9)
        assert np.all(tables[60]["ci95_low"] >= tables[10]["ci95_low"] - 1e-8)
        assert np.all(tables[60]["ci95_high"] <= tables[10]["ci95_high"] + 1e-8)
        all_tables[count_scale] = tables
        summary["examples"][str(count_scale)] = {}
        for duration, tag in ((10, "Ten"), (60, "Sixty")):
            selected = {}
            for index in (0, 50, 80, 100):
                row = tables[duration][index]
                selected[str(row["true_polarization"])] = {name: float(row[name]) for name in ("mle", "observed_total_count", "ci68_low", "ci68_high", "ci95_low", "ci95_high")}
            summary["examples"][str(count_scale)][str(duration)] = selected
            for index, suffix in ((80, "AtEight"), (100, "AtOne")):
                row = tables[duration][index]
                for key, label in (("observed_total_count", "Count"), ("ci68_low", "LowA"), ("ci68_high", "HighA"), ("ci95_low", "LowB"), ("ci95_high", "HighB")):
                    value = f"{row[key]:.1f}" if label == "Count" else f"{row[key]:.3f}"
                    tex.append(r"\newcommand{\Pyy" + macro_prefix + tag + suffix + label + "}{" + value + "}")
    summary["commands"] = commands
    (work / "precision-values.tex").write_text("\n".join(tex) + "\n")
    (work / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({scale: {duration: points["1.0"] for duration, points in examples.items()}
                      for scale, examples in summary["examples"].items()}, indent=2))


if __name__ == "__main__":
    main()
