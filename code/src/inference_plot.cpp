#include "dpolar/inference_plot.hpp"

#include "TBox.h"
#include "TCanvas.h"
#include "TGraph.h"
#include "TLegend.h"
#include "TLine.h"
#include "TPaveText.h"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace dpolar {
namespace {

constexpr double kDeltaChiSquare68 = 1.0;
constexpr double kDeltaChiSquare95 = 3.841458820694124;

std::string formatDouble(const double value, const int precision) {
    std::ostringstream output;
    output << std::fixed << std::setprecision(precision) << value;
    return output.str();
}

std::string formatBool(const bool value) {
    return value ? "true" : "false";
}

std::string sanitizeLabel(std::string value) {
    for (char& character : value) {
        if (!std::isalnum(static_cast<unsigned char>(character)) && character != '_' && character != '-') {
            character = '_';
        }
    }
    return value;
}

std::filesystem::path resolveOutputRoot(
    const ScenarioConfig& scenario,
    const std::filesystem::path& output_root) {
    return output_root.empty() ? defaultOutputRoot(scenario) : output_root;
}

bool isNearlyInteger(const double value) {
    return std::abs(value - std::round(value)) <= 1.0e-9;
}

const char* pzzObservableLabel(const PzzObservable observable) {
    switch (observable) {
        case PzzObservable::Proton:
            return "proton";
        case PzzObservable::Deuteron:
            return "deuteron";
        case PzzObservable::Coincidence:
            return "coincidence";
    }
    throw std::runtime_error("Unsupported pzz observable");
}

const char* lrudObservableLabel(const LrudObservable observable) {
    switch (observable) {
        case LrudObservable::Proton:
            return "proton";
        case LrudObservable::Coincidence:
            return "coincidence";
    }
    throw std::runtime_error("Unsupported LRUD observable");
}

std::string defaultPzzCaseLabel(
    const PzzObservable observable,
    const double count,
    const std::optional<double>& count2) {
    const std::string prefix = pzzObservableLabel(observable);
    if (count2.has_value()) {
        return sanitizeLabel(
            prefix + "_pair_n1_" + std::to_string(static_cast<long long>(std::llround(count))) +
            "_n2_" + std::to_string(static_cast<long long>(std::llround(*count2))));
    }
    return sanitizeLabel(
        prefix + "_total_n_" + std::to_string(static_cast<long long>(std::llround(count))));
}

std::string defaultPyyCaseLabel(const LrudObservable observable, const double count_lr, const double count_ud) {
    return sanitizeLabel(
        std::string("lrud_") + lrudObservableLabel(observable) +
        "_nlr_" + std::to_string(static_cast<long long>(std::llround(count_lr))) +
        "_nud_" + std::to_string(static_cast<long long>(std::llround(count_ud))));
}

void writeProfileCsv(
    const std::filesystem::path& path,
    const PolarizationProfile& profile) {
    std::ofstream output(path);
    output << "polarization,minus_two_delta_loglikelihood,expected_first_count,expected_second_count,expected_total_count,expected_ratio_or_asymmetry\n";
    for (const PolarizationProfilePoint& point : profile.points) {
        output
            << formatDouble(point.polarization, 10) << ','
            << formatDouble(point.minus_two_delta_loglikelihood, 10) << ','
            << formatDouble(point.expected_first_count, 10) << ','
            << formatDouble(point.expected_second_count, 10) << ','
            << formatDouble(point.expected_total_count, 10) << ','
            << formatDouble(point.expected_ratio_or_asymmetry, 10) << '\n';
    }
}

double maxFiniteDeltaNll(const PolarizationProfile& profile) {
    double maximum = 0.0;
    for (const PolarizationProfilePoint& point : profile.points) {
        if (std::isfinite(point.minus_two_delta_loglikelihood)) {
            maximum = std::max(maximum, point.minus_two_delta_loglikelihood);
        }
    }
    return maximum;
}

void addEstimateSummary(
    std::vector<SummaryEntry>& summary,
    const PolarizationProfile& profile) {
    summary.push_back({"estimate", formatDouble(profile.estimate.estimate, 10)});
    summary.push_back({"sigma_mle", formatDouble(profile.estimate.sigma_mle, 10)});
    summary.push_back({"ci68_low", formatDouble(profile.estimate.ci68.low, 10)});
    summary.push_back({"ci68_high", formatDouble(profile.estimate.ci68.high, 10)});
    summary.push_back({"ci95_low", formatDouble(profile.estimate.ci95.low, 10)});
    summary.push_back({"ci95_high", formatDouble(profile.estimate.ci95.high, 10)});
    summary.push_back({"at_lower_bound", formatBool(profile.estimate.at_lower_bound)});
    summary.push_back({"at_upper_bound", formatBool(profile.estimate.at_upper_bound)});
    summary.push_back({"loglikelihood_max", formatDouble(profile.estimate.loglikelihood_max, 10)});
    summary.push_back({"likelihood_point_count", std::to_string(profile.points.size())});
}

void drawProfilePlot(
    const PolarizationProfile& profile,
    const std::string& parameter_label,
    const std::vector<std::string>& info_lines,
    const std::filesystem::path& base_path) {
    std::vector<double> x_values;
    std::vector<double> y_values;
    x_values.reserve(profile.points.size());
    y_values.reserve(profile.points.size());
    for (const PolarizationProfilePoint& point : profile.points) {
        x_values.push_back(point.polarization);
        y_values.push_back(point.minus_two_delta_loglikelihood);
    }

    const double x_min = x_values.front();
    const double x_max = x_values.back();
    const double y_max = std::max(4.5, maxFiniteDeltaNll(profile) * 1.08);

    TCanvas canvas(("profile_" + base_path.stem().string()).c_str(), "profile_likelihood", 960, 760);
    canvas.SetLeftMargin(0.14);
    canvas.SetRightMargin(0.06);
    canvas.SetBottomMargin(0.14);
    canvas.SetTopMargin(0.08);

    TGraph curve(
        static_cast<int>(x_values.size()),
        x_values.data(),
        y_values.data());
    curve.SetTitle((";" + parameter_label + ";-2#Delta logL").c_str());
    curve.SetLineColor(kBlue + 1);
    curve.SetLineWidth(3);
    curve.SetMinimum(0.0);
    curve.SetMaximum(y_max);
    curve.Draw("AL");

    TBox band95(profile.estimate.ci95.low, 0.0, profile.estimate.ci95.high, y_max);
    band95.SetFillColor(kOrange - 9);
    band95.SetLineColor(kOrange - 9);
    band95.Draw("SAME");

    TBox band68(profile.estimate.ci68.low, 0.0, profile.estimate.ci68.high, y_max);
    band68.SetFillColor(kGreen - 9);
    band68.SetLineColor(kGreen - 9);
    band68.Draw("SAME");

    curve.Draw("L SAME");

    TLine mle_line(profile.estimate.estimate, 0.0, profile.estimate.estimate, y_max);
    mle_line.SetLineColor(kBlack);
    mle_line.SetLineWidth(3);
    mle_line.Draw("SAME");

    TLine line68(x_min, kDeltaChiSquare68, x_max, kDeltaChiSquare68);
    line68.SetLineColor(kGray + 2);
    line68.SetLineStyle(2);
    line68.Draw("SAME");

    TLine line95(x_min, kDeltaChiSquare95, x_max, kDeltaChiSquare95);
    line95.SetLineColor(kGray + 2);
    line95.SetLineStyle(2);
    line95.Draw("SAME");

    TLegend legend(0.58, 0.70, 0.90, 0.88);
    legend.SetFillStyle(0);
    legend.SetBorderSize(0);
    legend.AddEntry(&curve, "profile likelihood", "l");
    legend.AddEntry(&mle_line, "MLE", "l");
    legend.AddEntry(&band68, "68% interval", "f");
    legend.AddEntry(&band95, "95% interval", "f");
    legend.Draw();

    TPaveText info_box(0.16, 0.70, 0.50, 0.90, "NDC");
    info_box.SetFillStyle(0);
    info_box.SetBorderSize(0);
    info_box.SetTextAlign(12);
    info_box.SetTextSize(0.030);
    for (const std::string& line : info_lines) {
        info_box.AddText(line.c_str());
    }
    info_box.Draw();

    saveCanvas(canvas, base_path);
}

AnalysisArtifacts finalizeArtifacts(AnalysisArtifacts artifacts) {
    writeSummaryFiles(artifacts);
    artifacts.files.push_back(artifacts.output_dir / "summary.csv");
    artifacts.files.push_back(artifacts.output_dir / "summary.json");
    return artifacts;
}

}  // namespace

AnalysisArtifacts runPzzInferencePlot(
    const PolarizationInference& inference,
    const PzzObservable observable,
    const double count,
    const std::optional<double>& count2,
    const std::string& case_label,
    const std::filesystem::path& output_root) {
    const PolarizationProfile profile = inference.buildPzzProfile(observable, count, count2);
    const std::string label = case_label.empty() ? defaultPzzCaseLabel(observable, count, count2) : sanitizeLabel(case_label);
    const std::filesystem::path dir =
        analysisOutputDir(resolveOutputRoot(inference.scenario(), output_root), inference.scenario().scenario_name, "infer_pzz_plot") / label;
    std::filesystem::create_directories(dir);

    const std::filesystem::path scan_csv = dir / "likelihood_scan.csv";
    writeProfileCsv(scan_csv, profile);

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    artifacts.files.push_back(scan_csv);
    artifacts.summary.push_back({"parameter", "pzz"});
    artifacts.summary.push_back({"observable", profile.observable_label});
    artifacts.summary.push_back({"estimator", profile.estimator});
    artifacts.summary.push_back({"case_label", label});
    artifacts.summary.push_back({"input_counts_integer", formatBool(isNearlyInteger(count) && (!count2.has_value() || isNearlyInteger(*count2)))});
    artifacts.summary.push_back({"count", formatDouble(count, 10)});
    if (count2.has_value()) {
        artifacts.summary.push_back({"count2", formatDouble(*count2, 10)});
    }
    addEstimateSummary(artifacts.summary, profile);

    const std::vector<std::string> info_lines = {
        "observable = " + profile.observable_label,
        "estimator = " + profile.estimator,
        "count = " + formatDouble(count, 4),
        count2.has_value() ? "count2 = " + formatDouble(*count2, 4) : "count2 = n/a",
        "MLE = " + formatDouble(profile.estimate.estimate, 6),
        "68% = [" + formatDouble(profile.estimate.ci68.low, 6) + ", " + formatDouble(profile.estimate.ci68.high, 6) + "]",
        "95% = [" + formatDouble(profile.estimate.ci95.low, 6) + ", " + formatDouble(profile.estimate.ci95.high, 6) + "]",
    };
    const std::filesystem::path base_path = dir / "Profile_likelihood_vs_pzz";
    drawProfilePlot(profile, "#it{p}_{zz}", info_lines, base_path);
    artifacts.files.push_back(base_path.string() + ".png");
    artifacts.files.push_back(base_path.string() + ".pdf");
    return finalizeArtifacts(std::move(artifacts));
}

AnalysisArtifacts runPyyInferencePlot(
    const PolarizationInference& inference,
    const LrudObservable observable,
    const double count_lr,
    const double count_ud,
    const std::string& case_label,
    const std::filesystem::path& output_root) {
    const PolarizationProfile profile = inference.buildPyyProfile(observable, count_lr, count_ud);
    const std::string label =
        case_label.empty() ? defaultPyyCaseLabel(observable, count_lr, count_ud) : sanitizeLabel(case_label);
    const std::filesystem::path dir =
        analysisOutputDir(resolveOutputRoot(inference.scenario(), output_root), inference.scenario().scenario_name, "infer_pyy_plot") / label;
    std::filesystem::create_directories(dir);

    const std::filesystem::path scan_csv = dir / "likelihood_scan.csv";
    writeProfileCsv(scan_csv, profile);

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    artifacts.files.push_back(scan_csv);
    artifacts.summary.push_back({"parameter", "pyy"});
    artifacts.summary.push_back({"observable", profile.observable_label});
    artifacts.summary.push_back({"estimator", profile.estimator});
    artifacts.summary.push_back({"case_label", label});
    artifacts.summary.push_back({"input_counts_integer", formatBool(isNearlyInteger(count_lr) && isNearlyInteger(count_ud))});
    artifacts.summary.push_back({"count_lr", formatDouble(count_lr, 10)});
    artifacts.summary.push_back({"count_ud", formatDouble(count_ud, 10)});
    addEstimateSummary(artifacts.summary, profile);

    const std::vector<std::string> info_lines = {
        "observable = " + std::string(lrudObservableLabel(observable)),
        "estimator = " + profile.estimator,
        "count_lr = " + formatDouble(count_lr, 4),
        "count_ud = " + formatDouble(count_ud, 4),
        "MLE = " + formatDouble(profile.estimate.estimate, 6),
        "68% = [" + formatDouble(profile.estimate.ci68.low, 6) + ", " + formatDouble(profile.estimate.ci68.high, 6) + "]",
        "95% = [" + formatDouble(profile.estimate.ci95.low, 6) + ", " + formatDouble(profile.estimate.ci95.high, 6) + "]",
    };
    const std::filesystem::path base_path = dir / "Profile_likelihood_vs_pyy";
    drawProfilePlot(profile, "#it{p}_{y'y'}", info_lines, base_path);
    artifacts.files.push_back(base_path.string() + ".png");
    artifacts.files.push_back(base_path.string() + ".pdf");
    return finalizeArtifacts(std::move(artifacts));
}

}  // namespace dpolar
