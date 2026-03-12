#include "dpolar/analysis.hpp"

#include "TAxis.h"
#include "TBox.h"
#include "TCanvas.h"
#include "TGraphAsymmErrors.h"
#include "TGraph.h"
#include "TGraphErrors.h"
#include "TH2D.h"
#include "TLegend.h"
#include "TLatex.h"
#include "TLine.h"
#include "TPad.h"
#include "TPaveText.h"
#include "TROOT.h"
#include "TStyle.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <memory>
#include <numbers>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace dpolar {
namespace {

struct LrudStatModel {
    double variance_left_right {};
    double variance_up_down {};
    double covariance {};
    double variance_asymmetry {};
};

struct PlotRange {
    double minimum {};
    double maximum {};
};

struct InferenceScanPoint {
    double true_polarization {};
    double observed_first_count {std::numeric_limits<double>::quiet_NaN()};
    double observed_second_count {std::numeric_limits<double>::quiet_NaN()};
    double observed_total_count {std::numeric_limits<double>::quiet_NaN()};
    double observed_ratio_or_asymmetry {std::numeric_limits<double>::quiet_NaN()};
    PolarizationEstimate estimate;
};

struct OverlayAnnotation {
    std::string short_label;
    std::string table_line;
    CoverageParticle particle {CoverageParticle::Deuteron};
    double box_x_min {};
    double box_x_max {};
    double box_y_min {};
    double box_y_max {};
    double theta_lab_min_deg {};
    double theta_lab_max_deg {};
    double theta_cm_min_deg {};
    double theta_cm_max_deg {};
    int fill_color {};
};

struct OverlayLabelPlacement {
    double x {};
    double y {};
    int text_align {22};
};

std::string formatDouble(const double value, const int precision = 6) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(precision) << value;
    return stream.str();
}

std::string formatScientific(const double value, const int precision = 3) {
    std::ostringstream stream;
    stream << std::scientific << std::setprecision(precision) << value;
    return stream.str();
}

std::filesystem::path resolveOutputRoot(const ScenarioConfig& scenario, const std::filesystem::path& output_root) {
    if (!output_root.empty()) {
        return output_root;
    }
    return defaultOutputRoot(scenario);
}

std::vector<double> linspace(const double begin, const double end, const int count) {
    std::vector<double> values;
    values.reserve(static_cast<std::size_t>(count));
    if (count == 1) {
        values.push_back(begin);
        return values;
    }
    const double step = (end - begin) / static_cast<double>(count - 1);
    for (int index = 0; index < count; ++index) {
        values.push_back(begin + static_cast<double>(index) * step);
    }
    return values;
}

void addWindowSummary(
    std::vector<SummaryEntry>& summary,
    const std::string& prefix,
    const CmBranchWindow& window) {
    summary.push_back({prefix + "_begin_deg", formatDouble(toDegrees(window.begin_rad), 4)});
    summary.push_back({prefix + "_end_deg", formatDouble(toDegrees(window.end_rad), 4)});
    summary.push_back({prefix + "_delta_phi_deg", formatDouble(toDegrees(window.delta_phi_rad), 4)});
}

std::vector<double> scanPolarizationValues(const ScanConfig& scan) {
    std::vector<double> values;
    if (scan.polarization_steps <= 0) {
        values.push_back(scan.polarization_min);
        return values;
    }
    const double step = (scan.polarization_max - scan.polarization_min) / static_cast<double>(scan.polarization_steps);
    for (int index = 0; index <= scan.polarization_steps; ++index) {
        values.push_back(scan.polarization_min + static_cast<double>(index) * step);
    }
    return values;
}

double safeRatio(const double numerator, const double denominator) {
    return denominator == 0.0 ? 0.0 : numerator / denominator;
}

double safeSqrt(const double value) {
    return value <= 0.0 ? 0.0 : std::sqrt(value);
}

std::string sanitizeLabel(std::string value) {
    for (char& character : value) {
        if (!std::isalnum(static_cast<unsigned char>(character))) {
            character = '_';
        }
    }
    return value;
}

const char* particleLabel(const CoverageParticle particle) {
    return particle == CoverageParticle::Deuteron ? "deuteron" : "proton";
}

const char* errorSourceLabel(const bool include_tensor) {
    return include_tensor ? "Statistical + T uncertainty" : "Statistical only";
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

std::string ratioAnalysisName(const RatioMode mode) {
    switch (mode) {
        case RatioMode::Deuteron:
            return "ratio_deuteron";
        case RatioMode::Proton:
            return "ratio_proton";
        case RatioMode::Coincidence:
            return "ratio_coincidence";
    }
    throw std::runtime_error("Unsupported ratio mode");
}

std::string lrudAnalysisName(const LrudObservable observable) {
    return observable == LrudObservable::Coincidence ? "lrud_coincidence" : "lrud_scan";
}

double legacyRatioStatSigma(
    const double numerator,
    const double denominator,
    const double beam_particles) {
    if (numerator <= 0.0 || denominator <= 0.0 || beam_particles <= 0.0) {
        return 0.0;
    }
    const double variance =
        numerator / (denominator * denominator) +
        numerator * numerator / std::pow(denominator, 3.0) +
        2.0 * numerator / (beam_particles * denominator * denominator);
    return safeSqrt(variance);
}

UncertaintyBreakdown makeBreakdown(const double value, const double tensor_variance) {
    const double stat_sigma = safeSqrt(std::max(value, 0.0));
    const double tensor_sigma = safeSqrt(tensor_variance);
    return UncertaintyBreakdown {
        value,
        stat_sigma,
        tensor_sigma,
        std::sqrt(stat_sigma * stat_sigma + tensor_sigma * tensor_sigma),
    };
}

LrudStatModel computeLegacyLrudStatModel(
    const double left_right_count,
    const double up_down_count,
    const double beam_particles) {
    if (left_right_count <= 0.0 || up_down_count <= 0.0 || beam_particles <= 0.0) {
        return {};
    }

    const double probability_left_right = left_right_count / beam_particles;
    const double probability_up_down = up_down_count / beam_particles;
    const double sum = left_right_count + up_down_count;
    if (sum <= 0.0) {
        return {};
    }

    const double variance_left_right = beam_particles * (1.0 - probability_left_right) * probability_up_down;
    const double variance_up_down = beam_particles * (1.0 - probability_up_down) * probability_up_down;
    const double covariance = -beam_particles * probability_left_right * probability_up_down;
    const double derivative_left_right = 2.0 * up_down_count / (sum * sum);
    const double derivative_up_down = -2.0 * left_right_count / (sum * sum);
    const double variance_asymmetry =
        derivative_left_right * derivative_left_right * variance_left_right +
        derivative_up_down * derivative_up_down * variance_up_down +
        2.0 * derivative_left_right * derivative_up_down * covariance;

    return LrudStatModel {
        variance_left_right,
        variance_up_down,
        covariance,
        std::max(variance_asymmetry, 0.0),
    };
}

void configureCanvasMargins(TCanvas& canvas) {
    canvas.SetLeftMargin(0.15);
    canvas.SetBottomMargin(0.15);
}

void configureInfoPad(TPad& pad) {
    pad.SetLeftMargin(0.06);
    pad.SetRightMargin(0.03);
    pad.SetTopMargin(0.05);
    pad.SetBottomMargin(0.02);
}

void configurePlotPad(TPad& pad) {
    pad.SetLeftMargin(0.15);
    pad.SetRightMargin(0.05);
    pad.SetTopMargin(0.02);
    pad.SetBottomMargin(0.16);
    pad.SetGrid();
}

PlotRange computePaddedRange(
    const std::vector<double>& values,
    const std::vector<double>& errors,
    const double padding_fraction = 0.08) {
    double minimum = std::numeric_limits<double>::max();
    double maximum = std::numeric_limits<double>::lowest();
    for (std::size_t index = 0; index < values.size(); ++index) {
        const double error = index < errors.size() ? std::abs(errors[index]) : 0.0;
        minimum = std::min(minimum, values[index] - error);
        maximum = std::max(maximum, values[index] + error);
    }

    if (!std::isfinite(minimum) || !std::isfinite(maximum)) {
        return PlotRange {0.0, 1.0};
    }

    if (maximum <= minimum) {
        const double center = 0.5 * (minimum + maximum);
        const double half_width = std::max(std::abs(center) * 0.1, 1.0e-6);
        return PlotRange {center - half_width, center + half_width};
    }

    const double span = maximum - minimum;
    const double padding = span * padding_fraction;
    return PlotRange {minimum - padding, maximum + padding};
}

PlotRange mergePlotRanges(const PlotRange& left, const PlotRange& right) {
    return PlotRange {
        std::min(left.minimum, right.minimum),
        std::max(left.maximum, right.maximum),
    };
}

void styleErrorGraph(TGraphErrors& graph, const int color, const double line_width) {
    graph.SetLineColor(color);
    graph.SetLineWidth(static_cast<Width_t>(line_width));
    graph.SetMarkerColor(color);
    graph.SetMarkerStyle(1);
    graph.SetMarkerSize(0.01);
    graph.SetFillStyle(0);
}

void styleMarkerGraph(TGraph& graph, const int color, const int marker_style, const double marker_size) {
    graph.SetLineColor(color);
    graph.SetLineWidth(0);
    graph.SetMarkerColor(color);
    graph.SetMarkerStyle(marker_style);
    graph.SetMarkerSize(marker_size);
    graph.SetFillStyle(0);
}

void drawInfoBox(
    const std::vector<std::string>& lines,
    const double x1 = 0.18,
    const double y1 = 0.62,
    const double x2 = 0.88,
    const double y2 = 0.89,
    const double text_size = 0.024) {
    TPaveText box(x1, y1, x2, y2, "NDC");
    box.SetFillColor(kWhite);
    box.SetFillStyle(1001);
    box.SetBorderSize(1);
    box.SetTextAlign(12);
    box.SetTextSize(text_size);
    for (const std::string& line : lines) {
        box.AddText(line.c_str());
    }
    box.DrawClone();
}

std::string formatOverlayRangeLine(
    const std::string& short_label,
    const double theta_lab_min_deg,
    const double theta_lab_max_deg,
    const double theta_cm_min_deg,
    const double theta_cm_max_deg) {
    return short_label + ": theta_lab=[" + formatDouble(theta_lab_min_deg, 1) + "," +
           formatDouble(theta_lab_max_deg, 1) + "] deg; theta_cm=[" +
           formatDouble(theta_cm_min_deg, 1) + "," + formatDouble(theta_cm_max_deg, 1) + "] deg";
}

double overlayInfoTextSize(const std::size_t line_count) {
    return std::clamp(0.30 / static_cast<double>(std::max<std::size_t>(line_count + 1U, 1U)), 0.024, 0.034);
}

void drawOverlayInfoSection(
    const std::string& title,
    const std::vector<std::string>& lines,
    const double y1,
    const double y2) {
    TPaveText box(0.02, y1, 0.98, y2, "NDC");
    box.SetFillColor(kWhite);
    box.SetFillStyle(1001);
    box.SetBorderSize(1);
    box.SetTextAlign(12);
    box.SetTextSize(overlayInfoTextSize(lines.size()));
    if (TText* header = box.AddText(title.c_str()); header != nullptr) {
        header->SetTextFont(62);
    }
    for (const std::string& line : lines) {
        box.AddText(line.c_str());
    }
    box.DrawClone();
}

OverlayLabelPlacement computeOverlayLabelPlacement(
    const OverlayAnnotation& annotation,
    const PlotRange& x_range,
    const PlotRange& y_range) {
    const double x_span = x_range.maximum - x_range.minimum;
    const double y_span = y_range.maximum - y_range.minimum;
    const double box_width = std::abs(annotation.box_x_max - annotation.box_x_min);
    const double box_height = std::abs(annotation.box_y_max - annotation.box_y_min);
    OverlayLabelPlacement placement {
        0.5 * (annotation.box_x_min + annotation.box_x_max),
        0.5 * (annotation.box_y_min + annotation.box_y_max),
        22
    };

    if (box_width < 0.04 * x_span || box_height < 0.04 * y_span) {
        placement.x = std::clamp(
            std::max(annotation.box_x_min, annotation.box_x_max) + 0.012 * x_span,
            x_range.minimum + 0.02 * x_span,
            x_range.maximum - 0.02 * x_span);
        placement.y = std::clamp(
            std::max(annotation.box_y_min, annotation.box_y_max) + 0.012 * y_span,
            y_range.minimum + 0.02 * y_span,
            y_range.maximum - 0.02 * y_span);
        placement.text_align = 11;
    }

    return placement;
}

void drawOverlayAnnotations(
    const std::vector<OverlayAnnotation>& annotations,
    const PlotRange& x_range,
    const PlotRange& y_range) {
    TLatex latex;
    latex.SetTextFont(42);
    latex.SetTextSize(0.022);
    latex.SetTextColor(kBlack);

    for (const OverlayAnnotation& annotation : annotations) {
        TBox box(annotation.box_x_min, annotation.box_y_min, annotation.box_x_max, annotation.box_y_max);
        box.SetFillColorAlpha(annotation.fill_color, 0.25);
        box.SetLineColor(annotation.fill_color);
        box.SetLineWidth(2);
        box.DrawClone("same");

        const OverlayLabelPlacement placement = computeOverlayLabelPlacement(annotation, x_range, y_range);
        latex.SetTextAlign(placement.text_align);
        latex.DrawLatex(placement.x, placement.y, annotation.short_label.c_str());
    }
}

void drawOverlayInfoPanel(
    TPad& info_pad,
    const std::vector<OverlayAnnotation>& annotations) {
    std::vector<std::string> proton_lines;
    std::vector<std::string> deuteron_lines;
    proton_lines.reserve(annotations.size());
    deuteron_lines.reserve(annotations.size());
    for (const OverlayAnnotation& annotation : annotations) {
        if (annotation.particle == CoverageParticle::Proton) {
            proton_lines.push_back(annotation.table_line);
        } else {
            deuteron_lines.push_back(annotation.table_line);
        }
    }

    info_pad.cd();
    drawOverlayInfoSection("Proton windows", proton_lines, 0.52, 0.98);
    drawOverlayInfoSection("Deuteron windows", deuteron_lines, 0.02, 0.48);
}

void addOverlayAnnotationSummary(
    std::vector<SummaryEntry>& summary,
    const std::vector<OverlayAnnotation>& annotations) {
    const auto proton_count = static_cast<int>(std::count_if(
        annotations.begin(),
        annotations.end(),
        [](const OverlayAnnotation& annotation) {
            return annotation.particle == CoverageParticle::Proton;
        }));
    const int deuteron_count = static_cast<int>(annotations.size()) - proton_count;
    summary.push_back({"overlay_annotation_count", std::to_string(annotations.size())});
    summary.push_back({"overlay_proton_annotation_count", std::to_string(proton_count)});
    summary.push_back({"overlay_deuteron_annotation_count", std::to_string(deuteron_count)});
    summary.push_back({"overlay_annotation_style", "inline_short_label_plus_side_table"});
}

void addDefinitionSummary(
    std::vector<SummaryEntry>& summary,
    const std::string& prefix,
    const std::vector<std::string>& lines) {
    for (std::size_t index = 0; index < lines.size(); ++index) {
        summary.push_back({prefix + "_" + std::to_string(index + 1), lines[index]});
    }
}

std::string runContextLine(const ScenarioConfig& scenario, const double beam_particles) {
    return "I = " + formatScientific(scenario.run.beam_current_amp, 3) + " A; t = " +
           formatDouble(scenario.run.duration_s, 1) + " s; Nbeam = I/e x t = " +
           formatScientific(beam_particles, 3);
}

std::vector<std::string> ratioDefinitionLines(
    const ScenarioConfig& scenario,
    const RatioMode mode,
    const bool include_tensor,
    const double beam_particles) {
    std::vector<std::string> lines;
    if (mode == RatioMode::Proton) {
        lines.push_back(
            "N1 = 4 x Np(single, #theta_{lab} = " +
            formatDouble(scenario.custom_layout.proton_arms[0].theta_lab_deg, 1) + " deg)");
        lines.push_back(
            "N2 = 4 x Np(single, #theta_{lab} = " +
            formatDouble(scenario.custom_layout.proton_arms[1].theta_lab_deg, 1) + " deg)");
        lines.push_back("R = N1 / N2; no coincidence gate is used");
        lines.push_back("Ni = M x Ntarget x Nbeam x #int d#theta d#phi [d#sigma/d#Omega x (1 + #sqrt{2}/2 T20 pzz)]");
    } else if (mode == RatioMode::Deuteron) {
        lines.push_back(
            "N1 = 4 x Nd(single, #theta_{lab} = " +
            formatDouble(scenario.custom_layout.deuteron_arm.theta_lab_deg, 1) + " deg, forward branch)");
        lines.push_back(
            "N2 = 4 x Nd(single, #theta_{lab} = " +
            formatDouble(scenario.custom_layout.deuteron_arm.theta_lab_deg, 1) + " deg, backward branch)");
        lines.push_back("R = N1 / N2; no coincidence gate is used");
        lines.push_back("Ni = M x Ntarget x Nbeam x #int d#theta d#phi [d#sigma/d#Omega x (1 + #sqrt{2}/2 T20 pzz)]");
    } else {
        lines.push_back(
            "N1 = Np+d(coincidence, proton arm 1 with deuteron forward branch, #theta_{lab}^{p} = " +
            formatDouble(scenario.custom_layout.proton_arms[0].theta_lab_deg, 1) +
            " deg)");
        lines.push_back(
            "N2 = Np+d(coincidence, proton arm 2 with deuteron backward branch, #theta_{lab}^{p} = " +
            formatDouble(scenario.custom_layout.proton_arms[1].theta_lab_deg, 1) +
            " deg)");
        lines.push_back("R = N1 / N2; proton and deuteron coincidence gate is used");
        lines.push_back("Ni = M x Ntarget x Nbeam x #int_{CM overlap} d#theta d#phi [d#sigma/d#Omega x (1 + #sqrt{2}/2 T20 pzz)]");
    }
    lines.push_back("#sigma_{R,stat}^{2} = N1/N2^{2} + N1^{2}/N2^{3} + 2N1/(Nbeam N2^{2})");
    lines.push_back(include_tensor ? "#sigma_{tot}^{2} = #sigma_{stat}^{2} + #sigma_{T}^{2}" : "#sigma = #sigma_{stat} only");
    lines.push_back(runContextLine(scenario, beam_particles));
    return lines;
}

std::vector<std::string> lrudDefinitionLines(
    const ScenarioConfig& scenario,
    const LrudObservable observable,
    const bool include_tensor,
    const double beam_particles) {
    std::vector<std::string> lines;
    if (observable == LrudObservable::Coincidence) {
        lines.push_back(
            "NLR = 2 x Np+d(coincidence LR sector, proton arm 1 with deuteron forward branch, #theta_{lab}^{p} = " +
            formatDouble(scenario.custom_layout.proton_arms[0].theta_lab_deg, 1) + " deg)");
        lines.push_back(
            "NUD = 2 x Np+d(coincidence UD sector, proton arm 1 with deuteron forward branch, #theta_{lab}^{p} = " +
            formatDouble(scenario.custom_layout.proton_arms[0].theta_lab_deg, 1) + " deg)");
        lines.push_back("R_{LRUD} = (NLR - NUD) / (NLR + NUD); proton and deuteron coincidence gate is used");
        lines.push_back("NLR #propto #int_{CM overlap} d#theta d#phi [d#sigma/d#Omega x (1 - #sqrt{3}/2 T22 pyy - #sqrt{2}/4 T20 pyy)]");
        lines.push_back("NUD #propto #int_{CM overlap} d#theta d#phi [d#sigma/d#Omega x (1 + #sqrt{3}/2 T22 pyy - #sqrt{2}/4 T20 pyy)]");
    } else {
        lines.push_back(
            "NLR = 2 x Np(single LR sector, #theta_{lab} = " +
            formatDouble(scenario.custom_layout.proton_arms[0].theta_lab_deg, 1) + " deg)");
        lines.push_back(
            "NUD = 2 x Np(single UD sector, #theta_{lab} = " +
            formatDouble(scenario.custom_layout.proton_arms[0].theta_lab_deg, 1) + " deg)");
        lines.push_back("R_{LRUD} = (NLR - NUD) / (NLR + NUD); no coincidence gate is used");
        lines.push_back("NLR #propto #int d#theta d#phi [d#sigma/d#Omega x (1 - #sqrt{3}/2 T22 pyy - #sqrt{2}/4 T20 pyy)]");
        lines.push_back("NUD #propto #int d#theta d#phi [d#sigma/d#Omega x (1 + #sqrt{3}/2 T22 pyy - #sqrt{2}/4 T20 pyy)]");
    }
    lines.push_back(include_tensor ? "#sigma_{tot}^{2} = #sigma_{stat}^{2} + #sigma_{T}^{2}" : "#sigma = #sigma_{stat} only");
    lines.push_back(runContextLine(scenario, beam_particles));
    return lines;
}

std::vector<std::string> coincidenceDefinitionLines(
    const ScenarioConfig& scenario,
    const bool forward_branch,
    const double beam_particles) {
    const DetectorArm& proton_arm = forward_branch ? scenario.custom_layout.proton_arms[0] : scenario.custom_layout.proton_arms[1];
    std::vector<std::string> lines;
    lines.push_back(
        std::string("Channel: ") + (forward_branch ? "forward" : "backward") +
        " coincidence only");
    lines.push_back(
        "Proton arm: #theta_{lab} = " + formatDouble(proton_arm.theta_lab_deg, 1) +
        " deg; deuteron arm: #theta_{lab} = " +
        formatDouble(scenario.custom_layout.deuteron_arm.theta_lab_deg, 1) + " deg");
    lines.push_back(
        std::string("Branch pairing: proton arm ") + (forward_branch ? "1" : "2") +
        " with deuteron " + (forward_branch ? "forward" : "backward") + " CM branch");
    lines.push_back("Ncoin = Ntarget x Nbeam x #int_{CM overlap} d#theta d#phi [d#sigma/d#Omega x (1 + #sqrt{2}/2 T20 pzz)]");
    lines.push_back(
        std::string("Efficiency = Ncoin / Np(single arm ") + (forward_branch ? "1" : "2") +
        "); channels are not summed");
    lines.push_back(runContextLine(scenario, beam_particles));
    return lines;
}

std::vector<std::string> coincidenceTotalDefinitionLines(
    const ScenarioConfig& scenario,
    const double beam_particles) {
    std::vector<std::string> lines;
    lines.push_back("Channel: total coincidence, forward + backward branches summed");
    lines.push_back(
        "Proton arms: #theta_{lab} = " + formatDouble(scenario.custom_layout.proton_arms[0].theta_lab_deg, 1) +
        " deg and " + formatDouble(scenario.custom_layout.proton_arms[1].theta_lab_deg, 1) + " deg");
    lines.push_back(
        "Deuteron arm: #theta_{lab} = " +
        formatDouble(scenario.custom_layout.deuteron_arm.theta_lab_deg, 1) + " deg");
    lines.push_back(
        "Ntotal = Ncoin(forward overlap) + Ncoin(backward overlap)");
    lines.push_back("Each Ncoin = Ntarget x Nbeam x #int_{CM overlap} d#theta d#phi [d#sigma/d#Omega x (1 + #sqrt{2}/2 T20 pzz)]");
    lines.push_back("Coincidence sector multiplier is applied before summation");
    lines.push_back(runContextLine(scenario, beam_particles));
    return lines;
}

std::vector<double> effectiveDurations(const ScenarioConfig& scenario) {
    return scenario.run.duration_s_list.empty()
               ? std::vector<double> {scenario.run.duration_s}
               : scenario.run.duration_s_list;
}

ScenarioConfig scenarioWithDuration(const ScenarioConfig& scenario, const double duration_s) {
    ScenarioConfig copy = scenario;
    copy.run.duration_s = duration_s;
    copy.run.duration_s_list = {duration_s};
    return copy;
}

std::string durationLabel(const double duration_s) {
    const double hours = duration_s / 3600.0;
    const double minutes = duration_s / 60.0;
    if (std::abs(hours - std::round(hours)) < 1.0e-9) {
        return formatDouble(std::round(hours), 0) + "h";
    }
    if (std::abs(minutes - std::round(minutes)) < 1.0e-9) {
        return formatDouble(std::round(minutes), 0) + "min";
    }
    return formatDouble(duration_s, 0) + "s";
}

std::filesystem::path durationOutputDir(const std::filesystem::path& parent_dir, const double duration_s) {
    return parent_dir / durationLabel(duration_s);
}

void clearParentAnalysisIndexDir(const std::filesystem::path& parent_dir) {
    if (!std::filesystem::exists(parent_dir)) {
        return;
    }

    for (const auto& entry : std::filesystem::directory_iterator(parent_dir)) {
        if (!entry.is_regular_file()) {
            continue;
        }
        std::error_code error;
        std::filesystem::remove(entry.path(), error);
    }
}

AnalysisArtifacts aggregateDurationRuns(
    const std::filesystem::path& parent_dir,
    const std::vector<double>& durations_s,
    const std::vector<AnalysisArtifacts>& runs) {
    std::filesystem::create_directories(parent_dir);
    std::ofstream manifest(parent_dir / "duration_runs.csv");
    manifest << "duration_label,duration_s,summary_csv,summary_json\n";

    AnalysisArtifacts artifacts;
    artifacts.output_dir = parent_dir;
    artifacts.summary.push_back({"duration_count", std::to_string(durations_s.size())});
    for (std::size_t index = 0; index < durations_s.size(); ++index) {
        const std::string label = durationLabel(durations_s[index]);
        manifest
            << label << ','
            << formatDouble(durations_s[index], 1) << ','
            << (runs[index].output_dir / "summary.csv").string() << ','
            << (runs[index].output_dir / "summary.json").string() << '\n';
        artifacts.summary.push_back({"duration_" + std::to_string(index + 1) + "_label", label});
        artifacts.summary.push_back({"duration_" + std::to_string(index + 1) + "_seconds", formatDouble(durations_s[index], 1)});
        artifacts.summary.push_back({"duration_" + std::to_string(index + 1) + "_dir", runs[index].output_dir.string()});
        artifacts.files.push_back(runs[index].output_dir / "summary.csv");
        artifacts.files.push_back(runs[index].output_dir / "summary.json");
    }
    artifacts.files.push_back(parent_dir / "duration_runs.csv");
    return artifacts;
}

void saveCanvasAndTrack(
    AnalysisArtifacts& artifacts,
    TCanvas& canvas,
    const std::filesystem::path& base_path_without_extension) {
    saveCanvas(canvas, base_path_without_extension);
    artifacts.files.push_back(base_path_without_extension.string() + ".png");
    artifacts.files.push_back(base_path_without_extension.string() + ".pdf");
}

void writeCoverageCsv(
    const std::filesystem::path& path,
    const std::vector<AcceptanceCoverage>& coverages) {
    std::ofstream output(path);
    output << "label,particle,accepted_solid_angle_sr,theta_cm_min_deg,theta_cm_max_deg,phi_cm_min_deg,phi_cm_max_deg,accepted_cells,theta_bins,phi_bins\n";
    for (const AcceptanceCoverage& coverage : coverages) {
        output
            << coverage.label << ','
            << particleLabel(coverage.particle) << ','
            << formatDouble(coverage.accepted_solid_angle_sr, 8) << ','
            << formatDouble(toDegrees(coverage.theta_cm_min_rad), 6) << ','
            << formatDouble(toDegrees(coverage.theta_cm_max_rad), 6) << ','
            << formatDouble(toDegrees(coverage.phi_cm_min_rad), 6) << ','
            << formatDouble(toDegrees(coverage.phi_cm_max_rad), 6) << ','
            << coverage.accepted_cells << ','
            << coverage.theta_bins << ','
            << coverage.phi_bins << '\n';
    }
}

void addCoverageSummary(
    std::vector<SummaryEntry>& summary,
    const AcceptanceCoverage& coverage) {
    const std::string prefix = sanitizeLabel(coverage.label);
    summary.push_back({prefix + "_particle", particleLabel(coverage.particle)});
    summary.push_back({prefix + "_accepted_solid_angle_sr", formatDouble(coverage.accepted_solid_angle_sr, 8)});
    summary.push_back({prefix + "_theta_cm_min_deg", formatDouble(toDegrees(coverage.theta_cm_min_rad), 6)});
    summary.push_back({prefix + "_theta_cm_max_deg", formatDouble(toDegrees(coverage.theta_cm_max_rad), 6)});
    summary.push_back({prefix + "_phi_cm_min_deg", formatDouble(toDegrees(coverage.phi_cm_min_rad), 6)});
    summary.push_back({prefix + "_phi_cm_max_deg", formatDouble(toDegrees(coverage.phi_cm_max_rad), 6)});
    summary.push_back({prefix + "_accepted_cells", std::to_string(coverage.accepted_cells)});
}

std::unique_ptr<TH2D> makeCoverageHistogram(
    const AcceptanceCoverage& coverage,
    const std::string& name,
    const std::string& title) {
    auto histogram = std::make_unique<TH2D>(
        name.c_str(),
        title.c_str(),
        coverage.theta_bins,
        toDegrees(coverage.theta_grid_min_rad),
        toDegrees(coverage.theta_grid_max_rad),
        coverage.phi_bins,
        toDegrees(coverage.phi_grid_min_rad),
        toDegrees(coverage.phi_grid_max_rad));
    histogram->SetStats(false);
    histogram->GetXaxis()->SetTitle("#theta_{cm}(deg)");
    histogram->GetYaxis()->SetTitle("#phi_{cm}(deg)");
    histogram->GetZaxis()->SetTitle("accepted");
    for (int theta_index = 0; theta_index < coverage.theta_bins; ++theta_index) {
        for (int phi_index = 0; phi_index < coverage.phi_bins; ++phi_index) {
            const std::size_t flat_index = static_cast<std::size_t>(theta_index * coverage.phi_bins + phi_index);
            histogram->SetBinContent(theta_index + 1, phi_index + 1, coverage.accepted_map[flat_index]);
        }
    }
    return histogram;
}

AcceptanceCoverage combineCoverages(
    const std::string& label,
    const CoverageParticle particle,
    const std::vector<AcceptanceCoverage>& coverages) {
    AcceptanceCoverage combined;
    combined.label = label;
    combined.particle = particle;
    if (coverages.empty()) {
        return combined;
    }

    const AcceptanceCoverage& reference = coverages.front();
    combined.theta_bins = reference.theta_bins;
    combined.phi_bins = reference.phi_bins;
    combined.theta_grid_min_rad = reference.theta_grid_min_rad;
    combined.theta_grid_max_rad = reference.theta_grid_max_rad;
    combined.phi_grid_min_rad = reference.phi_grid_min_rad;
    combined.phi_grid_max_rad = reference.phi_grid_max_rad;
    combined.accepted_map.assign(reference.accepted_map.size(), 0.0);

    const double theta_step_rad =
        (reference.theta_grid_max_rad - reference.theta_grid_min_rad) / static_cast<double>(reference.theta_bins);
    const double phi_step_rad =
        (reference.phi_grid_max_rad - reference.phi_grid_min_rad) / static_cast<double>(reference.phi_bins);

    // [EN] Build the union mask cell-by-cell so the reported solid angle matches the plotted CM acceptance exactly / [CN] 逐网格构造并集掩膜，使输出立体角与绘制的质心系接受区域严格一致
    for (std::size_t index = 0; index < combined.accepted_map.size(); ++index) {
        bool accepted = false;
        for (const AcceptanceCoverage& coverage : coverages) {
            if (coverage.theta_bins != reference.theta_bins || coverage.phi_bins != reference.phi_bins) {
                throw std::runtime_error("Coverage grids are inconsistent and cannot be combined");
            }
            accepted = accepted || coverage.accepted_map[index] > 0.5;
        }
        if (!accepted) {
            continue;
        }

        combined.accepted_map[index] = 1.0;
        combined.accepted_cells += 1;
        const int theta_index = static_cast<int>(index / static_cast<std::size_t>(reference.phi_bins));
        const int phi_index = static_cast<int>(index % static_cast<std::size_t>(reference.phi_bins));
        const double theta_cm_rad = reference.theta_grid_min_rad + (static_cast<double>(theta_index) + 0.5) * theta_step_rad;
        const double phi_cm_rad = reference.phi_grid_min_rad + (static_cast<double>(phi_index) + 0.5) * phi_step_rad;
        combined.accepted_solid_angle_sr += std::sin(theta_cm_rad) * theta_step_rad * phi_step_rad;
        combined.theta_cm_min_rad = std::min(combined.theta_cm_min_rad, theta_cm_rad);
        combined.theta_cm_max_rad = std::max(combined.theta_cm_max_rad, theta_cm_rad);
        combined.phi_cm_min_rad = std::min(combined.phi_cm_min_rad, phi_cm_rad);
        combined.phi_cm_max_rad = std::max(combined.phi_cm_max_rad, phi_cm_rad);
    }

    if (!combined.hasAcceptance()) {
        combined.theta_cm_min_rad = 0.0;
        combined.phi_cm_min_rad = 0.0;
    }

    return combined;
}

void writeRatioScanCsv(const std::filesystem::path& path, const std::vector<RatioScanPoint>& points) {
    std::ofstream output(path);
    output << "polarization,N1,N2,sigma_N1_stat,sigma_N1_tensor,sigma_N1_total,sigma_N2_stat,sigma_N2_tensor,sigma_N2_total,R,sigma_R_stat,sigma_R_tensor,sigma_R_total,covariance_T\n";
    for (const RatioScanPoint& point : points) {
        output
            << formatDouble(point.polarization, 8) << ','
            << formatDouble(point.first_count.value, 8) << ','
            << formatDouble(point.second_count.value, 8) << ','
            << formatDouble(point.first_count.stat_sigma, 8) << ','
            << formatDouble(point.first_count.tensor_sigma, 8) << ','
            << formatDouble(point.first_count.total_sigma, 8) << ','
            << formatDouble(point.second_count.stat_sigma, 8) << ','
            << formatDouble(point.second_count.tensor_sigma, 8) << ','
            << formatDouble(point.second_count.total_sigma, 8) << ','
            << formatDouble(point.ratio.value, 10) << ','
            << formatDouble(point.ratio.stat_sigma, 10) << ','
            << formatDouble(point.ratio.tensor_sigma, 10) << ','
            << formatDouble(point.ratio.total_sigma, 10) << ','
            << formatDouble(point.tensor_covariance, 10) << '\n';
    }
}

void writeLrudScanCsv(const std::filesystem::path& path, const std::vector<LrudScanPoint>& points) {
    std::ofstream output(path);
    output << "polarization,N_LR,N_UD,sigma_N_LR_stat,sigma_N_LR_tensor,sigma_N_LR_total,sigma_N_UD_stat,sigma_N_UD_tensor,sigma_N_UD_total,R_LRUD,sigma_R_stat,sigma_R_tensor,sigma_R_total,covariance_stat,covariance_T\n";
    for (const LrudScanPoint& point : points) {
        output
            << formatDouble(point.polarization, 8) << ','
            << formatDouble(point.left_right_count.value, 8) << ','
            << formatDouble(point.up_down_count.value, 8) << ','
            << formatDouble(point.left_right_count.stat_sigma, 8) << ','
            << formatDouble(point.left_right_count.tensor_sigma, 8) << ','
            << formatDouble(point.left_right_count.total_sigma, 8) << ','
            << formatDouble(point.up_down_count.stat_sigma, 8) << ','
            << formatDouble(point.up_down_count.tensor_sigma, 8) << ','
            << formatDouble(point.up_down_count.total_sigma, 8) << ','
            << formatDouble(point.asymmetry.value, 10) << ','
            << formatDouble(point.asymmetry.stat_sigma, 10) << ','
            << formatDouble(point.asymmetry.tensor_sigma, 10) << ','
            << formatDouble(point.asymmetry.total_sigma, 10) << ','
            << formatDouble(point.stat_covariance, 10) << ','
            << formatDouble(point.tensor_covariance, 10) << '\n';
    }
}

void writeCoincidenceScanCsv(
    const std::filesystem::path& path,
    const std::vector<double>& polarizations,
    const std::vector<double>& coincidence_forward,
    const std::vector<double>& proton_single_forward,
    const std::vector<double>& deuteron_single_forward,
    const std::vector<double>& efficiency_forward,
    const std::vector<double>& coincidence_backward,
    const std::vector<double>& proton_single_backward,
    const std::vector<double>& deuteron_single_backward,
    const std::vector<double>& efficiency_backward) {
    std::ofstream output(path);
    output << "polarization,coincidence_forward,proton_single_forward,deuteron_single_forward,efficiency_forward,coincidence_backward,proton_single_backward,deuteron_single_backward,efficiency_backward\n";
    for (std::size_t index = 0; index < polarizations.size(); ++index) {
        output
            << formatDouble(polarizations[index], 8) << ','
            << formatDouble(coincidence_forward[index], 8) << ','
            << formatDouble(proton_single_forward[index], 8) << ','
            << formatDouble(deuteron_single_forward[index], 8) << ','
            << formatDouble(efficiency_forward[index], 10) << ','
            << formatDouble(coincidence_backward[index], 8) << ','
            << formatDouble(proton_single_backward[index], 8) << ','
            << formatDouble(deuteron_single_backward[index], 8) << ','
            << formatDouble(efficiency_backward[index], 10) << '\n';
    }
}

void writeCoincidenceTotalScanCsv(
    const std::filesystem::path& path,
    const std::vector<double>& polarizations,
    const std::vector<double>& coincidence_forward,
    const std::vector<double>& coincidence_backward,
    const std::vector<double>& coincidence_total) {
    std::ofstream output(path);
    output << "polarization,coincidence_forward,coincidence_backward,coincidence_total\n";
    for (std::size_t index = 0; index < polarizations.size(); ++index) {
        output
            << formatDouble(polarizations[index], 8) << ','
            << formatDouble(coincidence_forward[index], 8) << ','
            << formatDouble(coincidence_backward[index], 8) << ','
            << formatDouble(coincidence_total[index], 8) << '\n';
    }
}

std::vector<InferenceScanPoint> buildPzzInferenceScanPoints(
    const std::vector<RatioScanPoint>& points,
    const PolarizationInference& inference,
    const PzzObservable observable) {
    std::vector<InferenceScanPoint> inference_points;
    inference_points.reserve(points.size());
    for (const RatioScanPoint& point : points) {
        InferenceScanPoint inference_point;
        inference_point.true_polarization = point.polarization;
        inference_point.observed_first_count = point.first_count.value;
        inference_point.observed_second_count = point.second_count.value;
        inference_point.observed_total_count = point.first_count.value + point.second_count.value;
        inference_point.observed_ratio_or_asymmetry = point.ratio.value;
        inference_point.estimate =
            inference.inferPzzFromCounts(observable, point.first_count.value, point.second_count.value);
        inference_points.push_back(inference_point);
    }
    return inference_points;
}

std::vector<InferenceScanPoint> buildPyyInferenceScanPoints(
    const std::vector<LrudScanPoint>& points,
    const PolarizationInference& inference,
    const LrudObservable observable) {
    std::vector<InferenceScanPoint> inference_points;
    inference_points.reserve(points.size());
    for (const LrudScanPoint& point : points) {
        InferenceScanPoint inference_point;
        inference_point.true_polarization = point.polarization;
        inference_point.observed_first_count = point.left_right_count.value;
        inference_point.observed_second_count = point.up_down_count.value;
        inference_point.observed_total_count = point.left_right_count.value + point.up_down_count.value;
        inference_point.observed_ratio_or_asymmetry = point.asymmetry.value;
        inference_point.estimate =
            inference.inferPyyFromLrudCounts(observable, point.left_right_count.value, point.up_down_count.value);
        inference_points.push_back(inference_point);
    }
    return inference_points;
}

void writeInferenceScanCsv(const std::filesystem::path& path, const std::vector<InferenceScanPoint>& points) {
    std::ofstream output(path);
    output << "true_polarization,observed_first_count,observed_second_count,observed_total_count,observed_ratio_or_asymmetry,mle,sigma_mle,ci68_low,ci68_high,ci95_low,ci95_high,at_lower_bound,at_upper_bound\n";
    for (const InferenceScanPoint& point : points) {
        output
            << formatDouble(point.true_polarization, 8) << ','
            << formatDouble(point.observed_first_count, 8) << ','
            << formatDouble(point.observed_second_count, 8) << ','
            << formatDouble(point.observed_total_count, 8) << ','
            << formatDouble(point.observed_ratio_or_asymmetry, 10) << ','
            << formatDouble(point.estimate.estimate, 10) << ','
            << formatDouble(point.estimate.sigma_mle, 10) << ','
            << formatDouble(point.estimate.ci68.low, 10) << ','
            << formatDouble(point.estimate.ci68.high, 10) << ','
            << formatDouble(point.estimate.ci95.low, 10) << ','
            << formatDouble(point.estimate.ci95.high, 10) << ','
            << (point.estimate.at_lower_bound ? "true" : "false") << ','
            << (point.estimate.at_upper_bound ? "true" : "false") << '\n';
    }
}

void addInferenceSummary(
    std::vector<SummaryEntry>& summary,
    const std::vector<InferenceScanPoint>& points,
    const std::string& estimator,
    const std::string& observable_label) {
    summary.push_back({"inference_estimator", estimator});
    summary.push_back({"inference_observable", observable_label});
    summary.push_back({"inference_point_count", std::to_string(points.size())});
    if (!points.empty()) {
        summary.push_back({"inference_estimate_at_min_pol", formatDouble(points.front().estimate.estimate, 8)});
        summary.push_back({"inference_estimate_at_max_pol", formatDouble(points.back().estimate.estimate, 8)});
        summary.push_back({"inference_ci68_width_at_max_pol", formatDouble(points.back().estimate.ci68.high - points.back().estimate.ci68.low, 8)});
        summary.push_back({"inference_ci95_width_at_max_pol", formatDouble(points.back().estimate.ci95.high - points.back().estimate.ci95.low, 8)});
    }
}

void drawInferenceSummaryCanvas(
    const std::vector<InferenceScanPoint>& points,
    const std::string& parameter_axis_label,
    const std::string& observable_label,
    const std::vector<std::string>& definition_lines,
    const std::filesystem::path& base_path) {
    std::vector<double> true_values;
    std::vector<double> mle_values;
    std::vector<double> zero_errors(points.size(), 0.0);
    std::vector<double> lower_errors_68;
    std::vector<double> upper_errors_68;
    std::vector<double> lower_errors_95;
    std::vector<double> upper_errors_95;
    std::vector<double> y_range_values;
    std::vector<double> y_range_errors;
    true_values.reserve(points.size());
    mle_values.reserve(points.size());
    lower_errors_68.reserve(points.size());
    upper_errors_68.reserve(points.size());
    lower_errors_95.reserve(points.size());
    upper_errors_95.reserve(points.size());
    y_range_values.reserve(points.size());
    y_range_errors.reserve(points.size());
    for (const InferenceScanPoint& point : points) {
        true_values.push_back(point.true_polarization);
        mle_values.push_back(point.estimate.estimate);
        lower_errors_68.push_back(point.estimate.estimate - point.estimate.ci68.low);
        upper_errors_68.push_back(point.estimate.ci68.high - point.estimate.estimate);
        lower_errors_95.push_back(point.estimate.estimate - point.estimate.ci95.low);
        upper_errors_95.push_back(point.estimate.ci95.high - point.estimate.estimate);
        y_range_values.push_back(point.estimate.estimate);
        y_range_errors.push_back(std::max(lower_errors_95.back(), upper_errors_95.back()));
    }

    const PlotRange y_range = computePaddedRange(y_range_values, y_range_errors, 0.12);
    const double x_min = true_values.front();
    const double x_max = true_values.back();

    TCanvas canvas(("inference_summary_" + base_path.stem().string()).c_str(), "inference_summary", 960, 820);
    gStyle->SetEndErrorSize(10.0);
    TPad info_pad(("inference_info_" + base_path.stem().string()).c_str(), "", 0.0, 0.73, 1.0, 1.0);
    TPad plot_pad(("inference_plot_" + base_path.stem().string()).c_str(), "", 0.0, 0.0, 1.0, 0.73);
    configureInfoPad(info_pad);
    configurePlotPad(plot_pad);
    info_pad.Draw();
    plot_pad.Draw();
    info_pad.cd();

    std::vector<std::string> info_lines;
    info_lines.push_back("observable = " + observable_label);
    info_lines.push_back("estimator = pair_binomial MLE");
    info_lines.push_back("error bars show 68% and 95% profile-likelihood intervals");
    info_lines.insert(info_lines.end(), definition_lines.begin(), definition_lines.end());
    drawInfoBox(info_lines, 0.02, 0.08, 0.98, 0.92, 0.046);

    plot_pad.cd();
    TGraph reference_line(
        static_cast<int>(true_values.size()),
        true_values.data(),
        true_values.data());
    reference_line.SetTitle((";True " + parameter_axis_label + ";Inferred " + parameter_axis_label).c_str());
    reference_line.SetLineColor(kGray + 2);
    reference_line.SetLineStyle(2);
    reference_line.SetLineWidth(2);
    reference_line.SetMinimum(y_range.minimum);
    reference_line.SetMaximum(y_range.maximum);
    reference_line.Draw("AL");

    TGraphAsymmErrors graph95(
        static_cast<int>(true_values.size()),
        true_values.data(),
        mle_values.data(),
        zero_errors.data(),
        zero_errors.data(),
        lower_errors_95.data(),
        upper_errors_95.data());
    TGraphAsymmErrors graph68(
        static_cast<int>(true_values.size()),
        true_values.data(),
        mle_values.data(),
        zero_errors.data(),
        zero_errors.data(),
        lower_errors_68.data(),
        upper_errors_68.data());
    TGraph markers(
        static_cast<int>(true_values.size()),
        true_values.data(),
        mle_values.data());
    graph95.SetLineColor(kOrange + 7);
    graph95.SetLineWidth(2);
    graph95.SetMarkerSize(0.0);
    graph68.SetLineColor(kGreen + 2);
    graph68.SetLineWidth(4);
    graph68.SetMarkerSize(0.0);
    styleMarkerGraph(markers, kBlue + 1, 20, 1.1);

    graph95.Draw("[] SAME");
    graph68.Draw("[] SAME");
    markers.Draw("P SAME");

    TLine diagonal(x_min, x_min, x_max, x_max);
    diagonal.SetLineColor(kGray + 1);
    diagonal.SetLineStyle(3);
    diagonal.SetLineWidth(2);
    diagonal.Draw("SAME");

    TLegend legend(0.60, 0.16, 0.88, 0.32);
    legend.SetFillStyle(0);
    legend.SetBorderSize(0);
    legend.AddEntry(&markers, "MLE", "p");
    legend.AddEntry(&graph68, "68% interval", "l");
    legend.AddEntry(&graph95, "95% interval", "l");
    legend.AddEntry(&diagonal, "y = x", "l");
    legend.Draw();

    saveCanvas(canvas, base_path);
}

AnalysisArtifacts finalizeArtifacts(AnalysisArtifacts artifacts) {
    writeSummaryFiles(artifacts);
    return artifacts;
}

}  // namespace

AnalysisSession::AnalysisSession(ScenarioConfig scenario)
    : scenario_(std::move(scenario))
    , kinematics_(scenario_.beam)
    , observables_(scenario_)
    , counts_(scenario_, observables_)
    , energy_loss_(scenario_) {
}

const ScenarioConfig& AnalysisSession::scenario() const noexcept {
    return scenario_;
}

AnalysisArtifacts AnalysisSession::runTransformValidation(const std::filesystem::path& output_root) const {
    const std::filesystem::path dir = analysisOutputDir(resolveOutputRoot(scenario_, output_root), scenario_.scenario_name, "transform_validation");
    std::filesystem::create_directories(dir);

    std::ofstream table(dir / "theta_compare.csv");
    table << "theta_cm_deg,deuteron_lab_deg,proton_lab_deg,deuteron_cm_recovered_1_deg,deuteron_cm_recovered_2_deg,proton_cm_recovered_deg\n";

    double max_deuteron_roundtrip_error_deg = 0.0;
    double max_proton_roundtrip_error_deg = 0.0;
    const double proton_validation_begin_deg = observables_.tensorAnglesDegrees().front();
    const double proton_validation_end_deg = observables_.tensorAnglesDegrees().back();
    for (const double theta_cm_rad : linspace(0.0, std::numbers::pi_v<double>, 180)) {
        const ScatteringSolution solution = kinematics_.scatter(theta_cm_rad, 0.0);
        const auto recovered_deuteron = kinematics_.deuteronCmFromLab(solution.deuteron.theta_lab_rad);
        const double recovered_proton_cm = kinematics_.protonCmFromLab(solution.proton.theta_lab_rad);
        const double deuteron_error = std::min(
            std::abs(theta_cm_rad - recovered_deuteron.first),
            std::abs(theta_cm_rad - recovered_deuteron.second));
        const double theta_cm_deg = toDegrees(theta_cm_rad);
        max_deuteron_roundtrip_error_deg = std::max(max_deuteron_roundtrip_error_deg, toDegrees(deuteron_error));
        if (theta_cm_deg >= proton_validation_begin_deg && theta_cm_deg <= proton_validation_end_deg) {
            const double proton_error = std::abs(theta_cm_rad - recovered_proton_cm);
            max_proton_roundtrip_error_deg = std::max(max_proton_roundtrip_error_deg, toDegrees(proton_error));
        }

        table
            << formatDouble(theta_cm_deg, 6) << ','
            << formatDouble(toDegrees(solution.deuteron.theta_lab_rad), 6) << ','
            << formatDouble(toDegrees(solution.proton.theta_lab_rad), 6) << ','
            << formatDouble(toDegrees(recovered_deuteron.first), 6) << ','
            << formatDouble(toDegrees(recovered_deuteron.second), 6) << ','
            << formatDouble(toDegrees(recovered_proton_cm), 6) << '\n';
    }

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    artifacts.files.push_back(dir / "theta_compare.csv");
    artifacts.summary = {
        {"max_deuteron_roundtrip_error_deg", formatDouble(max_deuteron_roundtrip_error_deg, 6)},
        {"max_proton_roundtrip_error_deg", formatDouble(max_proton_roundtrip_error_deg, 6)},
        {"proton_validation_domain_begin_deg", formatDouble(proton_validation_begin_deg, 4)},
        {"proton_validation_domain_end_deg", formatDouble(proton_validation_end_deg, 4)},
    };
    return finalizeArtifacts(std::move(artifacts));
}

AnalysisArtifacts AnalysisSession::runLayoutOverlay(const LayoutPreset preset, const std::filesystem::path& output_root) const {
    const std::string analysis_name = preset == LayoutPreset::Custom ? "layout_custom" : "layout_sekiguchi";
    const std::filesystem::path dir = analysisOutputDir(resolveOutputRoot(scenario_, output_root), scenario_.scenario_name, analysis_name);
    std::filesystem::create_directories(dir);

    const std::vector<double> theta_cm_rad = linspace(0.0, std::numbers::pi_v<double>, 1000);
    std::vector<double> theta_cm_deg;
    std::vector<double> deuteron_theta_lab_deg;
    std::vector<double> proton_theta_lab_deg;
    theta_cm_deg.reserve(theta_cm_rad.size());
    deuteron_theta_lab_deg.reserve(theta_cm_rad.size());
    proton_theta_lab_deg.reserve(theta_cm_rad.size());

    for (const double theta : theta_cm_rad) {
        const ScatteringSolution solution = kinematics_.scatter(theta, 0.0);
        theta_cm_deg.push_back(toDegrees(theta));
        deuteron_theta_lab_deg.push_back(toDegrees(solution.deuteron.theta_lab_rad));
        proton_theta_lab_deg.push_back(toDegrees(solution.proton.theta_lab_rad));
    }

    TCanvas projection_canvas("layout_projection", "layout_projection", 1500, 900);
    TPad plot_pad("layout_projection_plot", "", 0.0, 0.0, 0.68, 1.0);
    TPad info_pad("layout_projection_info", "", 0.68, 0.0, 1.0, 1.0);
    configurePlotPad(plot_pad);
    configureInfoPad(info_pad);
    plot_pad.Draw();
    info_pad.Draw();
    plot_pad.cd();

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    std::vector<AcceptanceCoverage> coverages;
    std::vector<OverlayAnnotation> annotations;
    PlotRange overlay_x_range;
    PlotRange overlay_y_range;

    if (preset == LayoutPreset::Custom) {
        TGraph deuteron_graph(
            static_cast<int>(deuteron_theta_lab_deg.size()),
            deuteron_theta_lab_deg.data(),
            theta_cm_deg.data());
        TGraph proton_graph(
            static_cast<int>(proton_theta_lab_deg.size()),
            proton_theta_lab_deg.data(),
            theta_cm_deg.data());

        proton_graph.SetTitle(";#theta_{lab}(deg);#theta_{cm}(deg)");
        proton_graph.GetXaxis()->SetRangeUser(0.0, 90.0);
        proton_graph.GetYaxis()->SetRangeUser(0.0, 180.0);
        proton_graph.SetLineColor(kBlue + 1);
        deuteron_graph.SetLineColor(kRed + 1);
        proton_graph.Draw("AL");
        deuteron_graph.Draw("L SAME");
        overlay_x_range = PlotRange {0.0, 90.0};
        overlay_y_range = PlotRange {0.0, 180.0};
        annotations.reserve(scenario_.custom_layout.proton_arms.size() + 2U);

        for (std::size_t index = 0; index < scenario_.custom_layout.proton_arms.size(); ++index) {
            const DetectorArm& arm = scenario_.custom_layout.proton_arms[index];
            const CmBranchWindow window = protonWindowFromArm(kinematics_, arm);
            const std::string label = "proton_arm_" + std::to_string(index + 1);
            const double delta_theta_deg = toDegrees(thetaAcceptanceRad(arm.width_theta_mm, arm.distance_mm));
            const double theta_lab_min_deg = arm.theta_lab_deg - delta_theta_deg / 2.0;
            const double theta_lab_max_deg = arm.theta_lab_deg + delta_theta_deg / 2.0;
            const double theta_cm_min_deg = toDegrees(window.begin_rad);
            const double theta_cm_max_deg = toDegrees(window.end_rad);
            annotations.push_back(OverlayAnnotation {
                "P" + std::to_string(index + 1),
                formatOverlayRangeLine("P" + std::to_string(index + 1), theta_lab_min_deg, theta_lab_max_deg, theta_cm_min_deg, theta_cm_max_deg),
                CoverageParticle::Proton,
                theta_lab_min_deg,
                theta_lab_max_deg,
                theta_cm_min_deg,
                theta_cm_max_deg,
                theta_lab_min_deg,
                theta_lab_max_deg,
                theta_cm_min_deg,
                theta_cm_max_deg,
                kCyan + 1
            });
            addWindowSummary(artifacts.summary, label + "_window", window);
            AcceptanceCoverage coverage = computeCoverage(
                kinematics_,
                arm,
                CoverageParticle::Proton,
                window,
                scenario_.coverage);
            coverage.label = label;
            coverages.push_back(std::move(coverage));
        }

        const DetectorArm& arm = scenario_.custom_layout.deuteron_arm;
        const BranchPair windows = deuteronWindowsFromArm(kinematics_, arm);
        const std::vector<std::pair<CmBranchWindow, std::string>> branches = {
            {windows.forward, "D1F"},
            {windows.backward, "D1B"},
        };
        for (std::size_t index = 0; index < branches.size(); ++index) {
            const auto& [window, short_label] = branches[index];
            const double delta_theta_deg = toDegrees(thetaAcceptanceRad(arm.width_theta_mm, arm.distance_mm));
            const double theta_lab_min_deg = arm.theta_lab_deg - delta_theta_deg / 2.0;
            const double theta_lab_max_deg = arm.theta_lab_deg + delta_theta_deg / 2.0;
            const double theta_cm_min_deg = toDegrees(window.begin_rad);
            const double theta_cm_max_deg = toDegrees(window.end_rad);
            const std::string summary_label = index == 0U ? "deuteron_forward" : "deuteron_backward";
            annotations.push_back(OverlayAnnotation {
                short_label,
                formatOverlayRangeLine(short_label, theta_lab_min_deg, theta_lab_max_deg, theta_cm_min_deg, theta_cm_max_deg),
                CoverageParticle::Deuteron,
                theta_lab_min_deg,
                theta_lab_max_deg,
                theta_cm_min_deg,
                theta_cm_max_deg,
                theta_lab_min_deg,
                theta_lab_max_deg,
                theta_cm_min_deg,
                theta_cm_max_deg,
                kPink + 1
            });
            addWindowSummary(artifacts.summary, summary_label + "_window", window);
            AcceptanceCoverage coverage = computeCoverage(
                kinematics_,
                arm,
                CoverageParticle::Deuteron,
                window,
                scenario_.coverage);
            coverage.label = summary_label;
            coverages.push_back(std::move(coverage));
        }

        drawOverlayAnnotations(annotations, overlay_x_range, overlay_y_range);
        TLegend legend(0.66, 0.77, 0.92, 0.92);
        legend.SetFillStyle(1001);
        legend.SetFillColor(kWhite);
        legend.AddEntry(&proton_graph, "proton", "l");
        legend.AddEntry(&deuteron_graph, "deuteron", "l");
        legend.Draw();
        drawOverlayInfoPanel(info_pad, annotations);
        addOverlayAnnotationSummary(artifacts.summary, annotations);

        saveCanvasAndTrack(artifacts, projection_canvas, dir / "Pol_angcover_flipped");

        TCanvas coverage_canvas("layout_custom_coverage", "layout_custom_coverage", 1200, 900);
        coverage_canvas.Divide(2, 2);
        std::vector<std::unique_ptr<TH2D>> histograms;
        histograms.reserve(coverages.size());
        for (std::size_t index = 0; index < coverages.size(); ++index) {
            coverage_canvas.cd(static_cast<int>(index + 1));
            histograms.push_back(makeCoverageHistogram(
                coverages[index],
                "layout_custom_cov_" + std::to_string(index),
                coverages[index].label + " coverage in CM solid angle (" + formatDouble(coverages[index].accepted_solid_angle_sr, 5) + " sr)"));
            histograms.back()->Draw("COLZ");
        }
        saveCanvasAndTrack(artifacts, coverage_canvas, dir / "Pol_angcover_flipped_cm_coverage");
    } else {
        TGraph deuteron_graph(
            static_cast<int>(theta_cm_deg.size()),
            theta_cm_deg.data(),
            deuteron_theta_lab_deg.data());
        TGraph proton_graph(
            static_cast<int>(theta_cm_deg.size()),
            theta_cm_deg.data(),
            proton_theta_lab_deg.data());

        deuteron_graph.SetTitle(";#theta_{cm}(deg);#theta_{lab}(deg)");
        deuteron_graph.GetXaxis()->SetRangeUser(0.0, 180.0);
        deuteron_graph.GetYaxis()->SetRangeUser(0.0, 90.0);
        deuteron_graph.SetLineColor(kRed + 1);
        proton_graph.SetLineColor(kBlue + 1);
        deuteron_graph.Draw("AL");
        proton_graph.Draw("L SAME");
        overlay_x_range = PlotRange {0.0, 180.0};
        overlay_y_range = PlotRange {0.0, 90.0};
        annotations.reserve(scenario_.sekiguchi_layout.proton_arms.size() + 2U * scenario_.sekiguchi_layout.deuteron_arms.size());

        for (std::size_t index = 0; index < scenario_.sekiguchi_layout.deuteron_arms.size(); ++index) {
            const DetectorArm& arm = scenario_.sekiguchi_layout.deuteron_arms[index];
            const BranchPair windows = deuteronWindowsFromArm(kinematics_, arm);
            const std::vector<std::pair<CmBranchWindow, std::string>> branches = {
                {windows.forward, "D" + std::to_string(index + 1) + "F"},
                {windows.backward, "D" + std::to_string(index + 1) + "B"},
            };
            for (std::size_t branch_index = 0; branch_index < branches.size(); ++branch_index) {
                const auto& [window, short_label] = branches[branch_index];
                const double delta_theta_deg = toDegrees(thetaAcceptanceRad(arm.width_theta_mm, arm.distance_mm));
                const double theta_lab_min_deg = arm.theta_lab_deg - delta_theta_deg / 2.0;
                const double theta_lab_max_deg = arm.theta_lab_deg + delta_theta_deg / 2.0;
                const double theta_cm_min_deg = toDegrees(window.begin_rad);
                const double theta_cm_max_deg = toDegrees(window.end_rad);
                const std::string summary_label = "deuteron_arm_" + std::to_string(index + 1) +
                                                  (branch_index == 0U ? "_forward" : "_backward");
                annotations.push_back(OverlayAnnotation {
                    short_label,
                    formatOverlayRangeLine(short_label, theta_lab_min_deg, theta_lab_max_deg, theta_cm_min_deg, theta_cm_max_deg),
                    CoverageParticle::Deuteron,
                    theta_cm_min_deg,
                    theta_cm_max_deg,
                    theta_lab_min_deg,
                    theta_lab_max_deg,
                    theta_lab_min_deg,
                    theta_lab_max_deg,
                    theta_cm_min_deg,
                    theta_cm_max_deg,
                    kPink + 1
                });
                addWindowSummary(artifacts.summary, summary_label + "_window", window);
                AcceptanceCoverage coverage = computeCoverage(
                    kinematics_,
                    arm,
                    CoverageParticle::Deuteron,
                    window,
                    scenario_.coverage);
                coverage.label = summary_label;
                coverages.push_back(std::move(coverage));
            }
        }

        for (std::size_t index = 0; index < scenario_.sekiguchi_layout.proton_arms.size(); ++index) {
            const DetectorArm& arm = scenario_.sekiguchi_layout.proton_arms[index];
            const CmBranchWindow window = protonWindowFromArm(kinematics_, arm);
            const std::string label = "proton_arm_" + std::to_string(index + 1);
            const double delta_theta_deg = toDegrees(thetaAcceptanceRad(arm.width_theta_mm, arm.distance_mm));
            const double theta_lab_min_deg = arm.theta_lab_deg - delta_theta_deg / 2.0;
            const double theta_lab_max_deg = arm.theta_lab_deg + delta_theta_deg / 2.0;
            const double theta_cm_min_deg = toDegrees(window.begin_rad);
            const double theta_cm_max_deg = toDegrees(window.end_rad);
            annotations.push_back(OverlayAnnotation {
                "P" + std::to_string(index + 1),
                formatOverlayRangeLine("P" + std::to_string(index + 1), theta_lab_min_deg, theta_lab_max_deg, theta_cm_min_deg, theta_cm_max_deg),
                CoverageParticle::Proton,
                theta_cm_min_deg,
                theta_cm_max_deg,
                theta_lab_min_deg,
                theta_lab_max_deg,
                theta_lab_min_deg,
                theta_lab_max_deg,
                theta_cm_min_deg,
                theta_cm_max_deg,
                kCyan + 1
            });
            addWindowSummary(artifacts.summary, label + "_window", window);
            AcceptanceCoverage coverage = computeCoverage(
                kinematics_,
                arm,
                CoverageParticle::Proton,
                window,
                scenario_.coverage);
            coverage.label = label;
            coverages.push_back(std::move(coverage));
        }

        drawOverlayAnnotations(annotations, overlay_x_range, overlay_y_range);
        TLegend legend(0.66, 0.77, 0.92, 0.92);
        legend.SetFillStyle(1001);
        legend.SetFillColor(kWhite);
        legend.AddEntry(&proton_graph, "proton", "l");
        legend.AddEntry(&deuteron_graph, "deuteron", "l");
        legend.Draw();
        drawOverlayInfoPanel(info_pad, annotations);
        addOverlayAnnotationSummary(artifacts.summary, annotations);
        artifacts.summary.push_back({"sekiguchi_deuteron_detectors", std::to_string(scenario_.sekiguchi_layout.deuteron_arms.size())});
        artifacts.summary.push_back({"sekiguchi_proton_detectors", std::to_string(scenario_.sekiguchi_layout.proton_arms.size())});
        saveCanvasAndTrack(artifacts, projection_canvas, dir / "ThetaLab_vs_ThetaDc_deg");

        std::vector<AcceptanceCoverage> proton_coverages;
        std::vector<AcceptanceCoverage> deuteron_coverages;
        for (const AcceptanceCoverage& coverage : coverages) {
            if (coverage.particle == CoverageParticle::Proton) {
                proton_coverages.push_back(coverage);
            } else {
                deuteron_coverages.push_back(coverage);
            }
        }
        AcceptanceCoverage proton_union = combineCoverages("proton_union", CoverageParticle::Proton, proton_coverages);
        AcceptanceCoverage deuteron_union = combineCoverages("deuteron_union", CoverageParticle::Deuteron, deuteron_coverages);
        coverages.push_back(proton_union);
        coverages.push_back(deuteron_union);

        TCanvas coverage_canvas("layout_sekiguchi_coverage", "layout_sekiguchi_coverage", 1200, 900);
        coverage_canvas.Divide(1, 2);
        std::vector<std::unique_ptr<TH2D>> histograms;
        histograms.reserve(2);
        coverage_canvas.cd(1);
        histograms.push_back(makeCoverageHistogram(
            proton_union,
            "layout_sekiguchi_proton_union",
            proton_union.label + " coverage in CM solid angle (" + formatDouble(proton_union.accepted_solid_angle_sr, 5) + " sr)"));
        histograms.back()->Draw("COLZ");
        coverage_canvas.cd(2);
        histograms.push_back(makeCoverageHistogram(
            deuteron_union,
            "layout_sekiguchi_deuteron_union",
            deuteron_union.label + " coverage in CM solid angle (" + formatDouble(deuteron_union.accepted_solid_angle_sr, 5) + " sr)"));
        histograms.back()->Draw("COLZ");
        saveCanvasAndTrack(artifacts, coverage_canvas, dir / "ThetaLab_vs_ThetaDc_deg_cm_coverage");
    }

    artifacts.summary.push_back({"coverage_theta_bins", std::to_string(scenario_.coverage.theta_bins)});
    artifacts.summary.push_back({"coverage_phi_bins", std::to_string(scenario_.coverage.phi_bins)});
    for (const AcceptanceCoverage& coverage : coverages) {
        addCoverageSummary(artifacts.summary, coverage);
    }

    const std::filesystem::path coverage_csv = dir / "coverage.csv";
    writeCoverageCsv(coverage_csv, coverages);
    artifacts.files.push_back(coverage_csv);
    return finalizeArtifacts(std::move(artifacts));
}

AnalysisArtifacts AnalysisSession::runEnergyPlot(const std::filesystem::path& output_root) const {
    const std::filesystem::path dir = analysisOutputDir(resolveOutputRoot(scenario_, output_root), scenario_.scenario_name, "energy_plot");
    std::filesystem::create_directories(dir);

    const std::vector<double> theta_cm_rad = linspace(0.0, std::numbers::pi_v<double>, 1000);
    std::vector<double> deuteron_theta_lab_deg;
    std::vector<double> proton_theta_lab_deg;
    std::vector<double> deuteron_energy_per_u_mev;
    std::vector<double> proton_energy_mev;
    deuteron_theta_lab_deg.reserve(theta_cm_rad.size());
    proton_theta_lab_deg.reserve(theta_cm_rad.size());
    deuteron_energy_per_u_mev.reserve(theta_cm_rad.size());
    proton_energy_mev.reserve(theta_cm_rad.size());

    for (const double theta : theta_cm_rad) {
        const ScatteringSolution solution = kinematics_.scatter(theta, 0.0);
        deuteron_theta_lab_deg.push_back(toDegrees(solution.deuteron.theta_lab_rad));
        proton_theta_lab_deg.push_back(toDegrees(solution.proton.theta_lab_rad));
        deuteron_energy_per_u_mev.push_back(solution.deuteron.kinetic_energy_mev / 2.0);
        proton_energy_mev.push_back(solution.proton.kinetic_energy_mev);
    }

    TCanvas canvas("energy_plot", "energy_plot", 900, 700);
    configureCanvasMargins(canvas);
    TGraph deuteron_graph(
        static_cast<int>(deuteron_theta_lab_deg.size()),
        deuteron_theta_lab_deg.data(),
        deuteron_energy_per_u_mev.data());
    TGraph proton_graph(
        static_cast<int>(proton_theta_lab_deg.size()),
        proton_theta_lab_deg.data(),
        proton_energy_mev.data());

    proton_graph.SetTitle(";#theta_{lab}(deg);Energy (MeV/u or MeV)");
    proton_graph.SetLineColor(kBlue + 1);
    deuteron_graph.SetLineColor(kRed + 1);
    proton_graph.GetXaxis()->SetRangeUser(0.0, 90.0);
    proton_graph.GetYaxis()->SetRangeUser(0.0, 370.0);
    proton_graph.Draw("AL");
    deuteron_graph.Draw("L SAME");

    TLegend legend(0.68, 0.74, 0.9, 0.9);
    legend.AddEntry(&deuteron_graph, "deuteron / A", "l");
    legend.AddEntry(&proton_graph, "proton", "l");
    legend.Draw();

    const DetectorArm& arm1 = scenario_.custom_layout.proton_arms[0];
    const DetectorArm& arm2 = scenario_.custom_layout.proton_arms[1];
    const DetectorArm& deuteron_arm = scenario_.custom_layout.deuteron_arm;
    for (const DetectorArm* arm : {&arm1, &arm2}) {
        const double delta_theta_deg = toDegrees(thetaAcceptanceRad(arm->width_theta_mm, arm->distance_mm));
        const double lower_energy = kinematics_.scatter(
            kinematics_.protonCmFromLab(toRadians(arm->theta_lab_deg) + toRadians(delta_theta_deg) / 2.0), 0.0).proton.kinetic_energy_mev;
        const double upper_energy = kinematics_.scatter(
            kinematics_.protonCmFromLab(toRadians(arm->theta_lab_deg) - toRadians(delta_theta_deg) / 2.0), 0.0).proton.kinetic_energy_mev;
        TBox box(
            arm->theta_lab_deg - delta_theta_deg / 2.0,
            std::min(lower_energy, upper_energy),
            arm->theta_lab_deg + delta_theta_deg / 2.0,
            std::max(lower_energy, upper_energy));
        box.SetFillColorAlpha(kCyan + 1, 0.25);
        box.Draw("same");
    }

    const BranchPair deuteron_windows = deuteronWindowsFromArm(kinematics_, deuteron_arm);
    for (const CmBranchWindow& window : {deuteron_windows.forward, deuteron_windows.backward}) {
        const double delta_theta_deg = toDegrees(thetaAcceptanceRad(deuteron_arm.width_theta_mm, deuteron_arm.distance_mm));
        const double lower_energy = kinematics_.scatter(window.begin_rad, 0.0).deuteron.kinetic_energy_mev / 2.0;
        const double upper_energy = kinematics_.scatter(window.end_rad, 0.0).deuteron.kinetic_energy_mev / 2.0;
        TBox box(
            deuteron_arm.theta_lab_deg - delta_theta_deg / 2.0,
            std::min(lower_energy, upper_energy),
            deuteron_arm.theta_lab_deg + delta_theta_deg / 2.0,
            std::max(lower_energy, upper_energy));
        box.SetFillColorAlpha(kPink + 1, 0.25);
        box.Draw("same");
    }

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    artifacts.summary = {
        {"deuteron_energy_min_per_u_mev", formatDouble(*std::min_element(deuteron_energy_per_u_mev.begin(), deuteron_energy_per_u_mev.end()), 4)},
        {"deuteron_energy_max_per_u_mev", formatDouble(*std::max_element(deuteron_energy_per_u_mev.begin(), deuteron_energy_per_u_mev.end()), 4)},
        {"proton_energy_min_mev", formatDouble(*std::min_element(proton_energy_mev.begin(), proton_energy_mev.end()), 4)},
        {"proton_energy_max_mev", formatDouble(*std::max_element(proton_energy_mev.begin(), proton_energy_mev.end()), 4)},
    };
    saveCanvasAndTrack(artifacts, canvas, dir / "Energy_vs_ThetaDc_deg");
    return finalizeArtifacts(std::move(artifacts));
}

AnalysisArtifacts AnalysisSession::runRatioScan(const RatioMode mode, const std::filesystem::path& output_root) const {
    const std::filesystem::path root = resolveOutputRoot(scenario_, output_root);
    const std::vector<double> durations_s = effectiveDurations(scenario_);
    const std::string analysis_name = ratioAnalysisName(mode);
    if (durations_s.size() == 1U) {
        return runRatioScanSingleDuration(mode, analysisOutputDir(root, scenario_.scenario_name, analysis_name));
    }

    const std::filesystem::path parent_dir = analysisOutputDir(root, scenario_.scenario_name, analysis_name);
    clearParentAnalysisIndexDir(parent_dir);
    std::vector<AnalysisArtifacts> runs;
    runs.reserve(durations_s.size());
    for (const double duration_s : durations_s) {
        AnalysisSession child_session(scenarioWithDuration(scenario_, duration_s));
        runs.push_back(child_session.runRatioScanSingleDuration(mode, durationOutputDir(parent_dir, duration_s)));
    }
    return finalizeArtifacts(aggregateDurationRuns(parent_dir, durations_s, runs));
}

AnalysisArtifacts AnalysisSession::runRatioScanSingleDuration(const RatioMode mode, const std::filesystem::path& dir) const {
    std::filesystem::create_directories(dir);

    CmBranchWindow first_window;
    CmBranchWindow second_window;
    PzzObservable observable = PzzObservable::Proton;
    double sector_scale = scenario_.run.single_arm_sector_multiplier;
    std::string first_label;
    std::string second_label;
    if (mode == RatioMode::Deuteron) {
        const BranchPair windows = deuteronWindowsFromArm(kinematics_, scenario_.custom_layout.deuteron_arm);
        first_window = windows.forward;
        second_window = windows.backward;
        observable = PzzObservable::Deuteron;
        first_label = "d single forward branch";
        second_label = "d single backward branch";
    } else if (mode == RatioMode::Coincidence) {
        const BranchPair deuteron_windows = deuteronWindowsFromArm(kinematics_, scenario_.custom_layout.deuteron_arm);
        const CmBranchWindow proton_forward = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[0]);
        const CmBranchWindow proton_backward = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[1]);
        first_window = intersectWindows(proton_forward, deuteron_windows.forward);
        second_window = intersectWindows(proton_backward, deuteron_windows.backward);
        observable = PzzObservable::Coincidence;
        sector_scale = scenario_.run.coincidence_sector_multiplier;
        first_label = "p+d coincidence branch 1";
        second_label = "p+d coincidence branch 2";
    } else {
        first_window = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[0]);
        second_window = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[1]);
        first_label = "p single arm 1";
        second_label = "p single arm 2";
    }

    const std::vector<double> polarization_values = scanPolarizationValues(scenario_.scan);
    const double beam_particles = counts_.beamParticleCount();
    const double sector_scale_squared = sector_scale * sector_scale;
    std::vector<RatioScanPoint> points;
    points.reserve(polarization_values.size());

    for (const double polarization : polarization_values) {
        const double integrated_first = counts_.integralForPzz(first_window, polarization);
        const double integrated_second = counts_.integralForPzz(second_window, polarization);
        const double count_first = counts_.countsFromIntegratedCrossSection(integrated_first) * sector_scale;
        const double count_second = counts_.countsFromIntegratedCrossSection(integrated_second) * sector_scale;
        const double tensor_variance_first =
            counts_.countVarianceFromTensorForPzz(first_window, polarization) * sector_scale_squared;
        const double tensor_variance_second =
            counts_.countVarianceFromTensorForPzz(second_window, polarization) * sector_scale_squared;
        const double tensor_covariance =
            counts_.countCovarianceFromTensorForPzz(first_window, second_window, polarization) * sector_scale_squared;

        const double ratio = safeRatio(count_first, count_second);
        const double derivative_first = count_second == 0.0 ? 0.0 : 1.0 / count_second;
        const double derivative_second = count_second == 0.0 ? 0.0 : -count_first / (count_second * count_second);
        const double ratio_tensor_variance =
            derivative_first * derivative_first * tensor_variance_first +
            derivative_second * derivative_second * tensor_variance_second +
            2.0 * derivative_first * derivative_second * tensor_covariance;

        RatioScanPoint point;
        point.polarization = polarization;
        point.first_count = makeBreakdown(count_first, tensor_variance_first);
        point.second_count = makeBreakdown(count_second, tensor_variance_second);
        point.ratio = UncertaintyBreakdown {
            ratio,
            legacyRatioStatSigma(count_first, count_second, beam_particles),
            safeSqrt(std::max(ratio_tensor_variance, 0.0)),
            0.0,
        };
        point.ratio.total_sigma = std::sqrt(
            point.ratio.stat_sigma * point.ratio.stat_sigma +
            point.ratio.tensor_sigma * point.ratio.tensor_sigma);
        point.tensor_covariance = tensor_covariance;
        points.push_back(point);
    }

    std::vector<double> polarizations;
    std::vector<double> first_values;
    std::vector<double> second_values;
    std::vector<double> ratios;
    std::vector<double> first_stat_errors;
    std::vector<double> first_total_errors;
    std::vector<double> second_stat_errors;
    std::vector<double> second_total_errors;
    std::vector<double> ratio_stat_errors;
    std::vector<double> ratio_total_errors;
    polarizations.reserve(points.size());
    first_values.reserve(points.size());
    second_values.reserve(points.size());
    ratios.reserve(points.size());
    first_stat_errors.reserve(points.size());
    first_total_errors.reserve(points.size());
    second_stat_errors.reserve(points.size());
    second_total_errors.reserve(points.size());
    ratio_stat_errors.reserve(points.size());
    ratio_total_errors.reserve(points.size());
    for (const RatioScanPoint& point : points) {
        polarizations.push_back(point.polarization);
        first_values.push_back(point.first_count.value);
        second_values.push_back(point.second_count.value);
        ratios.push_back(point.ratio.value);
        first_stat_errors.push_back(point.first_count.stat_sigma);
        first_total_errors.push_back(point.first_count.total_sigma);
        second_stat_errors.push_back(point.second_count.stat_sigma);
        second_total_errors.push_back(point.second_count.total_sigma);
        ratio_stat_errors.push_back(point.ratio.stat_sigma);
        ratio_total_errors.push_back(point.ratio.total_sigma);
    }

    auto drawCountsCanvas = [&](const bool include_tensor, const std::filesystem::path& base_path) {
        TCanvas canvas(("ratio_counts_" + base_path.stem().string()).c_str(), "ratio_counts", 960, 820);
        gStyle->SetEndErrorSize(10.0);
        TPad info_pad(("ratio_counts_info_" + base_path.stem().string()).c_str(), "", 0.0, 0.73, 1.0, 1.0);
        TPad plot_pad(("ratio_counts_plot_" + base_path.stem().string()).c_str(), "", 0.0, 0.0, 1.0, 0.73);
        configureInfoPad(info_pad);
        configurePlotPad(plot_pad);
        info_pad.Draw();
        plot_pad.Draw();
        info_pad.cd();
        drawInfoBox(ratioDefinitionLines(scenario_, mode, include_tensor, beam_particles), 0.02, 0.08, 0.98, 0.92, 0.078);

        plot_pad.cd();
        const std::vector<double>& first_errors = include_tensor ? first_total_errors : first_stat_errors;
        const std::vector<double>& second_errors = include_tensor ? second_total_errors : second_stat_errors;
        const PlotRange first_range = computePaddedRange(first_values, first_errors);
        const PlotRange second_range = computePaddedRange(second_values, second_errors);
        const PlotRange plot_range = mergePlotRanges(first_range, second_range);
        TGraph first_markers(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            first_values.data());
        TGraph second_markers(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            second_values.data());
        TGraphErrors first_graph(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            first_values.data(),
            nullptr,
            first_errors.data());
        TGraphErrors second_graph(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            second_values.data(),
            nullptr,
            second_errors.data());
        styleMarkerGraph(first_markers, kRed + 1, 20, 1.0);
        styleMarkerGraph(second_markers, kBlue + 1, 21, 1.0);
        styleErrorGraph(first_graph, kRed + 1, 4.0);
        styleErrorGraph(second_graph, kBlue + 1, 4.0);

        second_markers.SetTitle(";#it{p}_{zz};Counts");
        second_markers.SetMinimum(plot_range.minimum);
        second_markers.SetMaximum(plot_range.maximum);
        second_markers.Draw("AP");
        first_markers.Draw("P SAME");
        second_graph.Draw("P SAME");
        first_graph.Draw("P SAME");

        TLegend legend(0.62, 0.16, 0.88, 0.30);
        legend.SetFillStyle(0);
        legend.SetBorderSize(0);
        legend.SetHeader(errorSourceLabel(include_tensor), "C");
        legend.AddEntry(&first_markers, first_label.c_str(), "p");
        legend.AddEntry(&second_markers, second_label.c_str(), "p");
        legend.Draw();
        saveCanvas(canvas, base_path);
    };

    auto drawSingleCanvas = [&](const bool include_tensor, const std::filesystem::path& base_path) {
        TCanvas canvas(("ratio_single_" + base_path.stem().string()).c_str(), "ratio_single", 960, 820);
        gStyle->SetEndErrorSize(10.0);
        TPad info_pad(("ratio_single_info_" + base_path.stem().string()).c_str(), "", 0.0, 0.73, 1.0, 1.0);
        TPad plot_pad(("ratio_single_plot_" + base_path.stem().string()).c_str(), "", 0.0, 0.0, 1.0, 0.73);
        configureInfoPad(info_pad);
        configurePlotPad(plot_pad);
        info_pad.Draw();
        plot_pad.Draw();
        info_pad.cd();
        drawInfoBox(ratioDefinitionLines(scenario_, mode, include_tensor, beam_particles), 0.02, 0.08, 0.98, 0.92, 0.078);

        plot_pad.cd();
        const std::vector<double>& first_errors = include_tensor ? first_total_errors : first_stat_errors;
        const PlotRange plot_range = computePaddedRange(first_values, first_errors);
        TGraph markers(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            first_values.data());
        TGraphErrors graph(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            first_values.data(),
            nullptr,
            first_errors.data());
        styleMarkerGraph(markers, kRed + 1, 20, 1.0);
        styleErrorGraph(graph, kRed + 1, 4.0);

        markers.SetTitle(";#it{p}_{zz};N_{window1}");
        markers.SetMinimum(plot_range.minimum);
        markers.SetMaximum(plot_range.maximum);
        markers.Draw("AP");
        graph.Draw("P SAME");

        TLegend legend(0.62, 0.20, 0.88, 0.30);
        legend.SetFillStyle(0);
        legend.SetBorderSize(0);
        legend.SetHeader(errorSourceLabel(include_tensor), "C");
        legend.AddEntry(&markers, first_label.c_str(), "p");
        legend.Draw();
        saveCanvas(canvas, base_path);
    };

    auto drawRatioCanvas = [&](const bool include_tensor, const std::filesystem::path& base_path) {
        TCanvas canvas(("ratio_value_" + base_path.stem().string()).c_str(), "ratio_value", 960, 820);
        gStyle->SetEndErrorSize(10.0);
        TPad info_pad(("ratio_value_info_" + base_path.stem().string()).c_str(), "", 0.0, 0.73, 1.0, 1.0);
        TPad plot_pad(("ratio_value_plot_" + base_path.stem().string()).c_str(), "", 0.0, 0.0, 1.0, 0.73);
        configureInfoPad(info_pad);
        configurePlotPad(plot_pad);
        info_pad.Draw();
        plot_pad.Draw();
        info_pad.cd();
        drawInfoBox(ratioDefinitionLines(scenario_, mode, include_tensor, beam_particles), 0.02, 0.08, 0.98, 0.92, 0.078);

        plot_pad.cd();
        const std::vector<double>& errors = include_tensor ? ratio_total_errors : ratio_stat_errors;
        const PlotRange plot_range = computePaddedRange(ratios, errors);
        TGraph markers(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            ratios.data());
        TGraphErrors graph(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            ratios.data(),
            nullptr,
            errors.data());
        styleMarkerGraph(markers, kBlue + 1, 24, 1.3);
        styleErrorGraph(graph, kBlue + 1, 5.0);

        markers.SetTitle(";#it{p}_{zz};N_{1}/N_{2}");
        markers.SetMinimum(plot_range.minimum);
        markers.SetMaximum(plot_range.maximum);
        markers.Draw("AP");
        graph.Draw("P SAME");

        TLegend legend(0.66, 0.20, 0.88, 0.28);
        legend.SetFillStyle(0);
        legend.SetBorderSize(0);
        legend.SetHeader(errorSourceLabel(include_tensor), "C");
        legend.AddEntry(&markers, "ratio", "p");
        legend.Draw();
        saveCanvas(canvas, base_path);
    };

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    addWindowSummary(artifacts.summary, "window_1", first_window);
    addWindowSummary(artifacts.summary, "window_2", second_window);
    artifacts.summary.push_back({"duration_label", durationLabel(scenario_.run.duration_s)});
    artifacts.summary.push_back({"duration_s", formatDouble(scenario_.run.duration_s, 1)});
    artifacts.summary.push_back({"ratio_observable", pzzObservableLabel(observable)});
    artifacts.summary.push_back({"beam_particles", formatDouble(beam_particles, 4)});
    artifacts.summary.push_back({"ratio_sector_multiplier", formatDouble(sector_scale, 1)});
    artifacts.summary.push_back({"ratio_at_min_pol", formatDouble(points.front().ratio.value, 8)});
    artifacts.summary.push_back({"ratio_at_max_pol", formatDouble(points.back().ratio.value, 8)});
    artifacts.summary.push_back({"ratio_stat_sigma_at_max_pol", formatDouble(points.back().ratio.stat_sigma, 8)});
    artifacts.summary.push_back({"ratio_total_sigma_at_max_pol", formatDouble(points.back().ratio.total_sigma, 8)});
    addDefinitionSummary(artifacts.summary, "stat_only_definition", ratioDefinitionLines(scenario_, mode, false, beam_particles));
    addDefinitionSummary(artifacts.summary, "stat_plus_T_definition", ratioDefinitionLines(scenario_, mode, true, beam_particles));

    const std::filesystem::path scan_csv = dir / "scan_points.csv";
    writeRatioScanCsv(scan_csv, points);
    artifacts.files.push_back(scan_csv);

    const std::vector<std::filesystem::path> bases = {
        dir / "N_total4_vs_pzz_stat_only",
        dir / "N_total4_vs_pzz_stat_plus_T",
        dir / "N1vs_pzz_stat_only",
        dir / "N1vs_pzz_stat_plus_T",
        dir / "Ratio_vs_pzz_stat_only",
        dir / "Ratio_vs_pzz_stat_plus_T",
    };
    drawCountsCanvas(false, bases[0]);
    drawCountsCanvas(true, bases[1]);
    drawSingleCanvas(false, bases[2]);
    drawSingleCanvas(true, bases[3]);
    drawRatioCanvas(false, bases[4]);
    drawRatioCanvas(true, bases[5]);
    for (const std::filesystem::path& base : bases) {
        artifacts.files.push_back(base.string() + ".png");
        artifacts.files.push_back(base.string() + ".pdf");
    }

    const PolarizationInference inference(scenario_);
    const std::vector<InferenceScanPoint> inference_points =
        buildPzzInferenceScanPoints(points, inference, observable);
    const std::filesystem::path inference_csv = dir / "inference_scan.csv";
    writeInferenceScanCsv(inference_csv, inference_points);
    artifacts.files.push_back(inference_csv);
    addInferenceSummary(artifacts.summary, inference_points, "pair_binomial", pzzObservableLabel(observable));
    const std::filesystem::path inference_base = dir / "Inferred_pzz_vs_true_pzz";
    drawInferenceSummaryCanvas(
        inference_points,
        "#it{p}_{zz}",
        std::string("pzz_") + pzzObservableLabel(observable),
        ratioDefinitionLines(scenario_, mode, false, beam_particles),
        inference_base);
    artifacts.files.push_back(inference_base.string() + ".png");
    artifacts.files.push_back(inference_base.string() + ".pdf");
    return finalizeArtifacts(std::move(artifacts));
}

AnalysisArtifacts AnalysisSession::runLrudScan(const std::filesystem::path& output_root) const {
    return runLrudScan(LrudObservable::Proton, output_root);
}

AnalysisArtifacts AnalysisSession::runLrudScan(
    const LrudObservable observable,
    const std::filesystem::path& output_root) const {
    const std::filesystem::path root = resolveOutputRoot(scenario_, output_root);
    const std::vector<double> durations_s = effectiveDurations(scenario_);
    const std::string analysis_name = lrudAnalysisName(observable);
    if (durations_s.size() == 1U) {
        return runLrudScanSingleDuration(observable, analysisOutputDir(root, scenario_.scenario_name, analysis_name));
    }

    const std::filesystem::path parent_dir = analysisOutputDir(root, scenario_.scenario_name, analysis_name);
    clearParentAnalysisIndexDir(parent_dir);
    std::vector<AnalysisArtifacts> runs;
    runs.reserve(durations_s.size());
    for (const double duration_s : durations_s) {
        AnalysisSession child_session(scenarioWithDuration(scenario_, duration_s));
        runs.push_back(child_session.runLrudScanSingleDuration(observable, durationOutputDir(parent_dir, duration_s)));
    }
    return finalizeArtifacts(aggregateDurationRuns(parent_dir, durations_s, runs));
}

AnalysisArtifacts AnalysisSession::runLrudScanSingleDuration(
    const LrudObservable observable,
    const std::filesystem::path& dir) const {
    std::filesystem::create_directories(dir);

    const CmBranchWindow proton_window = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[0]);
    const CmBranchWindow window = observable == LrudObservable::Coincidence
                                      ? intersectWindows(
                                            proton_window,
                                            deuteronWindowsFromArm(kinematics_, scenario_.custom_layout.deuteron_arm).forward)
                                      : proton_window;
    const std::vector<double> polarization_values = scanPolarizationValues(scenario_.scan);
    const double beam_particles = counts_.beamParticleCount();
    const double sector_scale = scenario_.run.lrud_sector_multiplier;
    const double sector_scale_squared = sector_scale * sector_scale;
    std::vector<LrudScanPoint> points;
    points.reserve(polarization_values.size());

    for (const double polarization : polarization_values) {
        const double left_right_count = counts_.countsFromIntegratedCrossSection(counts_.integralForLr(window, polarization))
                                        * sector_scale;
        const double up_down_count = counts_.countsFromIntegratedCrossSection(counts_.integralForUd(window, polarization))
                                     * sector_scale;
        const double sum = left_right_count + up_down_count;
        const double asymmetry = sum == 0.0 ? 0.0 : (left_right_count - up_down_count) / sum;

        const LrudStatModel stat_model = computeLegacyLrudStatModel(left_right_count, up_down_count, beam_particles);
        const double tensor_variance_left_right =
            counts_.countVarianceFromTensorForLr(window, polarization) * sector_scale_squared;
        const double tensor_variance_up_down =
            counts_.countVarianceFromTensorForUd(window, polarization) * sector_scale_squared;
        const double tensor_covariance =
            counts_.countCovarianceFromTensorForLrUd(window, polarization) * sector_scale_squared;
        const double derivative_left_right = sum == 0.0 ? 0.0 : 2.0 * up_down_count / (sum * sum);
        const double derivative_up_down = sum == 0.0 ? 0.0 : -2.0 * left_right_count / (sum * sum);
        const double tensor_variance_asymmetry =
            derivative_left_right * derivative_left_right * tensor_variance_left_right +
            derivative_up_down * derivative_up_down * tensor_variance_up_down +
            2.0 * derivative_left_right * derivative_up_down * tensor_covariance;

        LrudScanPoint point;
        point.polarization = polarization;
        point.left_right_count = UncertaintyBreakdown {
            left_right_count,
            safeSqrt(stat_model.variance_left_right),
            safeSqrt(tensor_variance_left_right),
            0.0,
        };
        point.left_right_count.total_sigma = std::sqrt(
            point.left_right_count.stat_sigma * point.left_right_count.stat_sigma +
            point.left_right_count.tensor_sigma * point.left_right_count.tensor_sigma);
        point.up_down_count = UncertaintyBreakdown {
            up_down_count,
            safeSqrt(stat_model.variance_up_down),
            safeSqrt(tensor_variance_up_down),
            0.0,
        };
        point.up_down_count.total_sigma = std::sqrt(
            point.up_down_count.stat_sigma * point.up_down_count.stat_sigma +
            point.up_down_count.tensor_sigma * point.up_down_count.tensor_sigma);
        point.asymmetry = UncertaintyBreakdown {
            asymmetry,
            safeSqrt(stat_model.variance_asymmetry),
            safeSqrt(std::max(tensor_variance_asymmetry, 0.0)),
            0.0,
        };
        point.asymmetry.total_sigma = std::sqrt(
            point.asymmetry.stat_sigma * point.asymmetry.stat_sigma +
            point.asymmetry.tensor_sigma * point.asymmetry.tensor_sigma);
        point.stat_covariance = stat_model.covariance;
        point.tensor_covariance = tensor_covariance;
        points.push_back(point);
    }

    std::vector<double> polarizations;
    std::vector<double> left_right_values;
    std::vector<double> up_down_values;
    std::vector<double> asymmetry_values;
    std::vector<double> left_right_stat_errors;
    std::vector<double> left_right_total_errors;
    std::vector<double> up_down_stat_errors;
    std::vector<double> up_down_total_errors;
    std::vector<double> stat_errors;
    std::vector<double> total_errors;
    polarizations.reserve(points.size());
    left_right_values.reserve(points.size());
    up_down_values.reserve(points.size());
    asymmetry_values.reserve(points.size());
    left_right_stat_errors.reserve(points.size());
    left_right_total_errors.reserve(points.size());
    up_down_stat_errors.reserve(points.size());
    up_down_total_errors.reserve(points.size());
    stat_errors.reserve(points.size());
    total_errors.reserve(points.size());
    for (const LrudScanPoint& point : points) {
        polarizations.push_back(point.polarization);
        left_right_values.push_back(point.left_right_count.value);
        up_down_values.push_back(point.up_down_count.value);
        asymmetry_values.push_back(point.asymmetry.value);
        left_right_stat_errors.push_back(point.left_right_count.stat_sigma);
        left_right_total_errors.push_back(point.left_right_count.total_sigma);
        up_down_stat_errors.push_back(point.up_down_count.stat_sigma);
        up_down_total_errors.push_back(point.up_down_count.total_sigma);
        stat_errors.push_back(point.asymmetry.stat_sigma);
        total_errors.push_back(point.asymmetry.total_sigma);
    }

    auto drawCountCanvas = [&](const bool include_tensor, const std::filesystem::path& base_path) {
        TCanvas canvas(("lrud_counts_" + base_path.stem().string()).c_str(), "lrud_counts", 960, 820);
        gStyle->SetEndErrorSize(10.0);
        TPad info_pad(("lrud_counts_info_" + base_path.stem().string()).c_str(), "", 0.0, 0.73, 1.0, 1.0);
        TPad plot_pad(("lrud_counts_plot_" + base_path.stem().string()).c_str(), "", 0.0, 0.0, 1.0, 0.73);
        configureInfoPad(info_pad);
        configurePlotPad(plot_pad);
        info_pad.Draw();
        plot_pad.Draw();
        info_pad.cd();
        drawInfoBox(lrudDefinitionLines(scenario_, observable, include_tensor, beam_particles), 0.02, 0.08, 0.98, 0.92, 0.078);

        plot_pad.cd();
        const std::vector<double>& left_right_errors = include_tensor ? left_right_total_errors : left_right_stat_errors;
        const std::vector<double>& up_down_errors = include_tensor ? up_down_total_errors : up_down_stat_errors;
        const PlotRange left_right_range = computePaddedRange(left_right_values, left_right_errors);
        const PlotRange up_down_range = computePaddedRange(up_down_values, up_down_errors);
        const PlotRange plot_range = mergePlotRanges(left_right_range, up_down_range);
        TGraph left_right_markers(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            left_right_values.data());
        TGraph up_down_markers(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            up_down_values.data());
        TGraphErrors left_right_graph(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            left_right_values.data(),
            nullptr,
            left_right_errors.data());
        TGraphErrors up_down_graph(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            up_down_values.data(),
            nullptr,
            up_down_errors.data());
        styleMarkerGraph(left_right_markers, kRed + 1, 20, 1.0);
        styleMarkerGraph(up_down_markers, kBlue + 1, 21, 1.0);
        styleErrorGraph(left_right_graph, kRed + 1, 4.0);
        styleErrorGraph(up_down_graph, kBlue + 1, 4.0);

        left_right_markers.SetTitle(";#it{p}_{y'y'};Counts");
        left_right_markers.SetMinimum(plot_range.minimum);
        left_right_markers.SetMaximum(plot_range.maximum);
        left_right_markers.Draw("AP");
        up_down_markers.Draw("P SAME");
        left_right_graph.Draw("P SAME");
        up_down_graph.Draw("P SAME");

        TLegend legend(0.62, 0.16, 0.88, 0.30);
        legend.SetFillStyle(0);
        legend.SetBorderSize(0);
        legend.SetHeader(errorSourceLabel(include_tensor), "C");
        legend.AddEntry(&left_right_markers, "N_{LR}", "p");
        legend.AddEntry(&up_down_markers, "N_{UD}", "p");
        legend.Draw();
        saveCanvas(canvas, base_path);
    };

    auto drawAsymmetryCanvas = [&](const bool include_tensor, const std::filesystem::path& base_path) {
        TCanvas canvas(("lrud_" + base_path.stem().string()).c_str(), "lrud_scan", 960, 820);
        gStyle->SetEndErrorSize(10.0);
        TPad info_pad(("lrud_info_" + base_path.stem().string()).c_str(), "", 0.0, 0.73, 1.0, 1.0);
        TPad plot_pad(("lrud_plot_" + base_path.stem().string()).c_str(), "", 0.0, 0.0, 1.0, 0.73);
        configureInfoPad(info_pad);
        configurePlotPad(plot_pad);
        info_pad.Draw();
        plot_pad.Draw();
        info_pad.cd();
        drawInfoBox(lrudDefinitionLines(scenario_, observable, include_tensor, beam_particles), 0.02, 0.08, 0.98, 0.92, 0.078);

        plot_pad.cd();
        const std::vector<double>& errors = include_tensor ? total_errors : stat_errors;
        const PlotRange plot_range = computePaddedRange(asymmetry_values, errors);
        TGraph markers(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            asymmetry_values.data());
        TGraphErrors graph(
            static_cast<int>(polarizations.size()),
            polarizations.data(),
            asymmetry_values.data(),
            nullptr,
            errors.data());
        styleMarkerGraph(markers, kBlue + 1, 24, 1.4);
        styleErrorGraph(graph, kBlue + 1, 5.0);

        markers.SetTitle(";#it{p}_{y'y'};#it{R}_{LRUD}");
        markers.SetMinimum(plot_range.minimum);
        markers.SetMaximum(plot_range.maximum);
        markers.Draw("AP");
        graph.Draw("P SAME");

        TLegend legend(0.63, 0.20, 0.88, 0.28);
        legend.SetFillStyle(0);
        legend.SetBorderSize(0);
        legend.SetHeader(errorSourceLabel(include_tensor), "C");
        legend.AddEntry(&markers, "R_{LRUD}", "p");
        legend.Draw();
        saveCanvas(canvas, base_path);
    };

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    addWindowSummary(artifacts.summary, "lrud_window", window);
    artifacts.summary.push_back({"duration_label", durationLabel(scenario_.run.duration_s)});
    artifacts.summary.push_back({"duration_s", formatDouble(scenario_.run.duration_s, 1)});
    artifacts.summary.push_back({"lrud_observable", lrudObservableLabel(observable)});
    artifacts.summary.push_back({"beam_particles", formatDouble(beam_particles, 4)});
    artifacts.summary.push_back({"lrud_sector_multiplier", formatDouble(sector_scale, 1)});
    artifacts.summary.push_back({"asymmetry_at_min_pol", formatDouble(points.front().asymmetry.value, 8)});
    artifacts.summary.push_back({"asymmetry_at_max_pol", formatDouble(points.back().asymmetry.value, 8)});
    artifacts.summary.push_back({"asymmetry_stat_sigma_at_max_pol", formatDouble(points.back().asymmetry.stat_sigma, 8)});
    artifacts.summary.push_back({"asymmetry_total_sigma_at_max_pol", formatDouble(points.back().asymmetry.total_sigma, 8)});
    addDefinitionSummary(artifacts.summary, "stat_only_definition", lrudDefinitionLines(scenario_, observable, false, beam_particles));
    addDefinitionSummary(artifacts.summary, "stat_plus_T_definition", lrudDefinitionLines(scenario_, observable, true, beam_particles));

    const std::filesystem::path scan_csv = dir / "scan_points.csv";
    writeLrudScanCsv(scan_csv, points);
    artifacts.files.push_back(scan_csv);

    const std::vector<std::filesystem::path> bases = {
        dir / "N_LR_N_UD_vs_pyy_stat_only",
        dir / "N_LR_N_UD_vs_pyy_stat_plus_T",
        dir / "R_LRUD_vs_pyy_stat_only",
        dir / "R_LRUD_vs_pyy_stat_plus_T",
    };
    drawCountCanvas(false, bases[0]);
    drawCountCanvas(true, bases[1]);
    drawAsymmetryCanvas(false, bases[2]);
    drawAsymmetryCanvas(true, bases[3]);
    for (const std::filesystem::path& base : bases) {
        artifacts.files.push_back(base.string() + ".png");
        artifacts.files.push_back(base.string() + ".pdf");
    }

    const PolarizationInference inference(scenario_);
    const std::vector<InferenceScanPoint> inference_points =
        buildPyyInferenceScanPoints(points, inference, observable);
    const std::filesystem::path inference_csv = dir / "inference_scan.csv";
    writeInferenceScanCsv(inference_csv, inference_points);
    artifacts.files.push_back(inference_csv);
    addInferenceSummary(artifacts.summary, inference_points, "pair_binomial", lrudObservableLabel(observable));
    const std::filesystem::path inference_base = dir / "Inferred_pyy_vs_true_pyy";
    drawInferenceSummaryCanvas(
        inference_points,
        "#it{p}_{y'y'}",
        std::string("pyy_") + lrudObservableLabel(observable),
        lrudDefinitionLines(scenario_, observable, false, beam_particles),
        inference_base);
    artifacts.files.push_back(inference_base.string() + ".png");
    artifacts.files.push_back(inference_base.string() + ".pdf");
    return finalizeArtifacts(std::move(artifacts));
}

AnalysisArtifacts AnalysisSession::runCoincidenceScan(const std::filesystem::path& output_root) const {
    const std::filesystem::path root = resolveOutputRoot(scenario_, output_root);
    const std::vector<double> durations_s = effectiveDurations(scenario_);
    if (durations_s.size() == 1U) {
        return runCoincidenceScanSingleDuration(analysisOutputDir(root, scenario_.scenario_name, "coincidence_scan"));
    }

    const std::filesystem::path parent_dir = analysisOutputDir(root, scenario_.scenario_name, "coincidence_scan");
    clearParentAnalysisIndexDir(parent_dir);
    std::vector<AnalysisArtifacts> runs;
    runs.reserve(durations_s.size());
    for (const double duration_s : durations_s) {
        AnalysisSession child_session(scenarioWithDuration(scenario_, duration_s));
        runs.push_back(child_session.runCoincidenceScanSingleDuration(durationOutputDir(parent_dir, duration_s)));
    }
    return finalizeArtifacts(aggregateDurationRuns(parent_dir, durations_s, runs));
}

AnalysisArtifacts AnalysisSession::runCoincidenceScanSingleDuration(const std::filesystem::path& dir) const {
    std::filesystem::create_directories(dir);

    const CmBranchWindow proton_forward = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[0]);
    const CmBranchWindow proton_backward = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[1]);
    const BranchPair deuteron_windows = deuteronWindowsFromArm(kinematics_, scenario_.custom_layout.deuteron_arm);
    const CmBranchWindow overlap_forward = intersectWindows(proton_forward, deuteron_windows.forward);
    const CmBranchWindow overlap_backward = intersectWindows(proton_backward, deuteron_windows.backward);

    const std::vector<double> polarization_values = scanPolarizationValues(scenario_.scan);
    const double beam_particles = counts_.beamParticleCount();
    std::vector<double> coincidence_forward_counts;
    std::vector<double> coincidence_backward_counts;
    std::vector<double> proton_single_forward_counts;
    std::vector<double> proton_single_backward_counts;
    std::vector<double> deuteron_single_forward_counts;
    std::vector<double> deuteron_single_backward_counts;
    std::vector<double> forward_efficiency;
    std::vector<double> backward_efficiency;
    coincidence_forward_counts.reserve(polarization_values.size());
    coincidence_backward_counts.reserve(polarization_values.size());
    proton_single_forward_counts.reserve(polarization_values.size());
    proton_single_backward_counts.reserve(polarization_values.size());
    deuteron_single_forward_counts.reserve(polarization_values.size());
    deuteron_single_backward_counts.reserve(polarization_values.size());
    forward_efficiency.reserve(polarization_values.size());
    backward_efficiency.reserve(polarization_values.size());

    for (const double polarization : polarization_values) {
        const double forward_coincidence_integral = counts_.integralForPzz(overlap_forward, polarization);
        const double backward_coincidence_integral = counts_.integralForPzz(overlap_backward, polarization);
        const double proton_forward_integral = counts_.integralForPzz(proton_forward, polarization);
        const double proton_backward_integral = counts_.integralForPzz(proton_backward, polarization);
        const double deuteron_forward_integral = counts_.integralForPzz(deuteron_windows.forward, polarization);
        const double deuteron_backward_integral = counts_.integralForPzz(deuteron_windows.backward, polarization);

        const double forward_coincidence_value = counts_.countsFromIntegratedCrossSection(forward_coincidence_integral)
                                                 * scenario_.run.coincidence_sector_multiplier;
        const double backward_coincidence_value = counts_.countsFromIntegratedCrossSection(backward_coincidence_integral)
                                                  * scenario_.run.coincidence_sector_multiplier;
        const double proton_forward_single = counts_.countsFromIntegratedCrossSection(proton_forward_integral)
                                             * scenario_.run.single_arm_sector_multiplier;
        const double proton_backward_single = counts_.countsFromIntegratedCrossSection(proton_backward_integral)
                                              * scenario_.run.single_arm_sector_multiplier;
        const double deuteron_forward_single = counts_.countsFromIntegratedCrossSection(deuteron_forward_integral)
                                               * scenario_.run.single_arm_sector_multiplier;
        const double deuteron_backward_single = counts_.countsFromIntegratedCrossSection(deuteron_backward_integral)
                                                * scenario_.run.single_arm_sector_multiplier;

        coincidence_forward_counts.push_back(forward_coincidence_value);
        coincidence_backward_counts.push_back(backward_coincidence_value);
        proton_single_forward_counts.push_back(proton_forward_single);
        proton_single_backward_counts.push_back(proton_backward_single);
        deuteron_single_forward_counts.push_back(deuteron_forward_single);
        deuteron_single_backward_counts.push_back(deuteron_backward_single);
        forward_efficiency.push_back(safeRatio(forward_coincidence_value, proton_forward_single));
        backward_efficiency.push_back(safeRatio(backward_coincidence_value, proton_backward_single));
    }

    auto drawCountsCanvas = [&](const bool forward_branch, const std::filesystem::path& base_path) {
        TCanvas canvas(("coincidence_counts_" + base_path.stem().string()).c_str(), "coincidence_counts", 900, 700);
        configureCanvasMargins(canvas);
        const std::vector<double>& values = forward_branch ? coincidence_forward_counts : coincidence_backward_counts;
        TGraph graph(
            static_cast<int>(polarization_values.size()),
            polarization_values.data(),
            values.data());
        graph.SetTitle(";#it{p}_{zz};Coincidence counts");
        graph.SetLineColor(forward_branch ? (kBlue + 1) : (kRed + 1));
        graph.SetLineWidth(2);
        graph.Draw("AL");
        drawInfoBox(coincidenceDefinitionLines(scenario_, forward_branch, beam_particles), 0.18, 0.62, 0.88, 0.89, 0.024);
        saveCanvas(canvas, base_path);
    };

    auto drawEfficiencyCanvas = [&](const bool forward_branch, const std::filesystem::path& base_path) {
        TCanvas canvas(("coincidence_eff_" + base_path.stem().string()).c_str(), "coincidence_efficiency", 900, 700);
        configureCanvasMargins(canvas);
        const std::vector<double>& values = forward_branch ? forward_efficiency : backward_efficiency;
        TGraph graph(
            static_cast<int>(polarization_values.size()),
            polarization_values.data(),
            values.data());
        graph.SetTitle(";#it{p}_{zz};Coincidence / proton single");
        graph.SetLineColor(forward_branch ? (kBlue + 1) : (kRed + 1));
        graph.SetLineWidth(2);
        graph.Draw("AL");
        drawInfoBox(coincidenceDefinitionLines(scenario_, forward_branch, beam_particles), 0.18, 0.62, 0.88, 0.89, 0.024);
        saveCanvas(canvas, base_path);
    };

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    addWindowSummary(artifacts.summary, "forward_overlap", overlap_forward);
    addWindowSummary(artifacts.summary, "backward_overlap", overlap_backward);
    artifacts.summary.push_back({"duration_label", durationLabel(scenario_.run.duration_s)});
    artifacts.summary.push_back({"duration_s", formatDouble(scenario_.run.duration_s, 1)});
    artifacts.summary.push_back({"beam_particles", formatDouble(beam_particles, 4)});
    artifacts.summary.push_back({"single_arm_sector_multiplier", formatDouble(scenario_.run.single_arm_sector_multiplier, 1)});
    artifacts.summary.push_back({"coincidence_sector_multiplier", formatDouble(scenario_.run.coincidence_sector_multiplier, 1)});
    artifacts.summary.push_back({"coincidence_forward_at_max_pol", formatDouble(coincidence_forward_counts.back(), 6)});
    artifacts.summary.push_back({"coincidence_backward_at_max_pol", formatDouble(coincidence_backward_counts.back(), 6)});
    artifacts.summary.push_back({"proton_single_forward_at_max_pol", formatDouble(proton_single_forward_counts.back(), 6)});
    artifacts.summary.push_back({"proton_single_backward_at_max_pol", formatDouble(proton_single_backward_counts.back(), 6)});
    artifacts.summary.push_back({"deuteron_single_forward_at_max_pol", formatDouble(deuteron_single_forward_counts.back(), 6)});
    artifacts.summary.push_back({"deuteron_single_backward_at_max_pol", formatDouble(deuteron_single_backward_counts.back(), 6)});
    artifacts.summary.push_back({"coincidence_forward_efficiency_at_max_pol", formatDouble(forward_efficiency.back(), 6)});
    artifacts.summary.push_back({"coincidence_backward_efficiency_at_max_pol", formatDouble(backward_efficiency.back(), 6)});
    addDefinitionSummary(artifacts.summary, "forward_definition", coincidenceDefinitionLines(scenario_, true, beam_particles));
    addDefinitionSummary(artifacts.summary, "backward_definition", coincidenceDefinitionLines(scenario_, false, beam_particles));

    const std::filesystem::path scan_csv = dir / "scan_points.csv";
    writeCoincidenceScanCsv(
        scan_csv,
        polarization_values,
        coincidence_forward_counts,
        proton_single_forward_counts,
        deuteron_single_forward_counts,
        forward_efficiency,
        coincidence_backward_counts,
        proton_single_backward_counts,
        deuteron_single_backward_counts,
        backward_efficiency);
    artifacts.files.push_back(scan_csv);

    const std::vector<std::filesystem::path> bases = {
        dir / "Coincidence_forward_vs_pzz",
        dir / "Coincidence_backward_vs_pzz",
        dir / "Coincidence_efficiency_forward_vs_pzz",
        dir / "Coincidence_efficiency_backward_vs_pzz",
    };
    drawCountsCanvas(true, bases[0]);
    drawCountsCanvas(false, bases[1]);
    drawEfficiencyCanvas(true, bases[2]);
    drawEfficiencyCanvas(false, bases[3]);
    for (const std::filesystem::path& base : bases) {
        artifacts.files.push_back(base.string() + ".png");
        artifacts.files.push_back(base.string() + ".pdf");
    }
    return finalizeArtifacts(std::move(artifacts));
}

AnalysisArtifacts AnalysisSession::runCoincidenceTotalScan(const std::filesystem::path& output_root) const {
    const std::filesystem::path root = resolveOutputRoot(scenario_, output_root);
    const std::vector<double> durations_s = effectiveDurations(scenario_);
    if (durations_s.size() == 1U) {
        return runCoincidenceTotalScanSingleDuration(analysisOutputDir(root, scenario_.scenario_name, "coincidence_total"));
    }

    const std::filesystem::path parent_dir = analysisOutputDir(root, scenario_.scenario_name, "coincidence_total");
    clearParentAnalysisIndexDir(parent_dir);
    std::vector<AnalysisArtifacts> runs;
    runs.reserve(durations_s.size());
    for (const double duration_s : durations_s) {
        AnalysisSession child_session(scenarioWithDuration(scenario_, duration_s));
        runs.push_back(child_session.runCoincidenceTotalScanSingleDuration(durationOutputDir(parent_dir, duration_s)));
    }
    return finalizeArtifacts(aggregateDurationRuns(parent_dir, durations_s, runs));
}

AnalysisArtifacts AnalysisSession::runCoincidenceTotalScanSingleDuration(const std::filesystem::path& dir) const {
    std::filesystem::create_directories(dir);

    const CmBranchWindow proton_forward = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[0]);
    const CmBranchWindow proton_backward = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[1]);
    const BranchPair deuteron_windows = deuteronWindowsFromArm(kinematics_, scenario_.custom_layout.deuteron_arm);
    const CmBranchWindow overlap_forward = intersectWindows(proton_forward, deuteron_windows.forward);
    const CmBranchWindow overlap_backward = intersectWindows(proton_backward, deuteron_windows.backward);

    const std::vector<double> polarization_values = scanPolarizationValues(scenario_.scan);
    const double beam_particles = counts_.beamParticleCount();
    std::vector<double> coincidence_forward_counts;
    std::vector<double> coincidence_backward_counts;
    std::vector<double> coincidence_total_counts;
    coincidence_forward_counts.reserve(polarization_values.size());
    coincidence_backward_counts.reserve(polarization_values.size());
    coincidence_total_counts.reserve(polarization_values.size());

    for (const double polarization : polarization_values) {
        const double forward_coincidence_integral = counts_.integralForPzz(overlap_forward, polarization);
        const double backward_coincidence_integral = counts_.integralForPzz(overlap_backward, polarization);
        const double forward_coincidence_value = counts_.countsFromIntegratedCrossSection(forward_coincidence_integral)
                                                 * scenario_.run.coincidence_sector_multiplier;
        const double backward_coincidence_value = counts_.countsFromIntegratedCrossSection(backward_coincidence_integral)
                                                  * scenario_.run.coincidence_sector_multiplier;
        coincidence_forward_counts.push_back(forward_coincidence_value);
        coincidence_backward_counts.push_back(backward_coincidence_value);
        coincidence_total_counts.push_back(forward_coincidence_value + backward_coincidence_value);
    }

    TCanvas canvas("coincidence_total", "coincidence_total", 960, 820);
    gStyle->SetEndErrorSize(10.0);
    TPad info_pad("coincidence_total_info", "", 0.0, 0.73, 1.0, 1.0);
    TPad plot_pad("coincidence_total_plot", "", 0.0, 0.0, 1.0, 0.73);
    configureInfoPad(info_pad);
    configurePlotPad(plot_pad);
    info_pad.Draw();
    plot_pad.Draw();
    info_pad.cd();
    drawInfoBox(coincidenceTotalDefinitionLines(scenario_, beam_particles), 0.02, 0.08, 0.98, 0.92, 0.078);

    plot_pad.cd();
    const PlotRange plot_range = computePaddedRange(coincidence_total_counts, {});
    TGraph total_markers(
        static_cast<int>(polarization_values.size()),
        polarization_values.data(),
        coincidence_total_counts.data());
    TGraph forward_markers(
        static_cast<int>(polarization_values.size()),
        polarization_values.data(),
        coincidence_forward_counts.data());
    TGraph backward_markers(
        static_cast<int>(polarization_values.size()),
        polarization_values.data(),
        coincidence_backward_counts.data());
    styleMarkerGraph(total_markers, kBlue + 1, 20, 1.2);
    styleMarkerGraph(forward_markers, kGreen + 2, 21, 1.0);
    styleMarkerGraph(backward_markers, kRed + 1, 22, 1.0);

    total_markers.SetTitle(";#it{p}_{zz};Coincidence counts");
    total_markers.SetMinimum(plot_range.minimum);
    total_markers.SetMaximum(plot_range.maximum);
    total_markers.Draw("AP");
    forward_markers.Draw("P SAME");
    backward_markers.Draw("P SAME");

    TLegend legend(0.60, 0.16, 0.88, 0.31);
    legend.SetFillStyle(0);
    legend.SetBorderSize(0);
    legend.AddEntry(&total_markers, "total coincidence", "p");
    legend.AddEntry(&forward_markers, "forward branch", "p");
    legend.AddEntry(&backward_markers, "backward branch", "p");
    legend.Draw();

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    addWindowSummary(artifacts.summary, "forward_overlap", overlap_forward);
    addWindowSummary(artifacts.summary, "backward_overlap", overlap_backward);
    artifacts.summary.push_back({"duration_label", durationLabel(scenario_.run.duration_s)});
    artifacts.summary.push_back({"duration_s", formatDouble(scenario_.run.duration_s, 1)});
    artifacts.summary.push_back({"beam_particles", formatDouble(beam_particles, 4)});
    artifacts.summary.push_back({"coincidence_sector_multiplier", formatDouble(scenario_.run.coincidence_sector_multiplier, 1)});
    artifacts.summary.push_back({"coincidence_forward_at_min_pol", formatDouble(coincidence_forward_counts.front(), 6)});
    artifacts.summary.push_back({"coincidence_backward_at_min_pol", formatDouble(coincidence_backward_counts.front(), 6)});
    artifacts.summary.push_back({"coincidence_total_at_min_pol", formatDouble(coincidence_total_counts.front(), 6)});
    artifacts.summary.push_back({"coincidence_forward_at_max_pol", formatDouble(coincidence_forward_counts.back(), 6)});
    artifacts.summary.push_back({"coincidence_backward_at_max_pol", formatDouble(coincidence_backward_counts.back(), 6)});
    artifacts.summary.push_back({"coincidence_total_at_max_pol", formatDouble(coincidence_total_counts.back(), 6)});
    addDefinitionSummary(artifacts.summary, "coincidence_total_definition", coincidenceTotalDefinitionLines(scenario_, beam_particles));

    const std::filesystem::path scan_csv = dir / "scan_points.csv";
    writeCoincidenceTotalScanCsv(
        scan_csv,
        polarization_values,
        coincidence_forward_counts,
        coincidence_backward_counts,
        coincidence_total_counts);
    artifacts.files.push_back(scan_csv);

    saveCanvasAndTrack(artifacts, canvas, dir / "Coincidence_total_vs_pzz");
    return finalizeArtifacts(std::move(artifacts));
}

AnalysisArtifacts AnalysisSession::runCrossSectionScan(const std::filesystem::path& output_root) const {
    const std::filesystem::path dir = analysisOutputDir(resolveOutputRoot(scenario_, output_root), scenario_.scenario_name, "cross_section_scan");
    std::filesystem::create_directories(dir);

    TCanvas canvas("cross_section_scan", "cross_section_scan", 900, 1000);
    canvas.Divide(1, 3);

    canvas.cd(1);
    TGraph cross_section_graph(
        static_cast<int>(observables_.crossSectionAnglesDegrees().size()),
        observables_.crossSectionAnglesDegrees().data(),
        observables_.crossSectionValues().data());
    cross_section_graph.SetTitle("Differential cross section;#theta_{cm}(deg);d#sigma/d#Omega (mb/sr)");
    cross_section_graph.SetLineColor(kRed + 1);
    cross_section_graph.Draw("AL");
    gPad->SetLogy(true);

    canvas.cd(2);
    TGraph t20_graph(
        static_cast<int>(observables_.tensorAnglesDegrees().size()),
        observables_.tensorAnglesDegrees().data(),
        observables_.tensorT20Values().data());
    t20_graph.SetTitle("T20;#theta_{cm}(deg);T20");
    t20_graph.SetLineColor(kGreen + 2);
    t20_graph.Draw("AL");

    canvas.cd(3);
    TGraph t22_graph(
        static_cast<int>(observables_.tensorT22AnglesDegrees().size()),
        observables_.tensorT22AnglesDegrees().data(),
        observables_.tensorT22Values().data());
    t22_graph.SetTitle("T22;#theta_{cm}(deg);T22");
    t22_graph.SetLineColor(kBlue + 1);
    t22_graph.Draw("AL");

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    artifacts.summary = {
        {"cross_section_points", std::to_string(observables_.crossSectionAnglesDegrees().size())},
        {"tensor_t20_points", std::to_string(observables_.tensorAnglesDegrees().size())},
        {"tensor_t22_points", std::to_string(observables_.tensorT22AnglesDegrees().size())},
    };
    saveCanvasAndTrack(artifacts, canvas, dir / "CrossSection_T20_T22");
    return finalizeArtifacts(std::move(artifacts));
}

AnalysisArtifacts AnalysisSession::runEnergyLossScan(const std::filesystem::path& output_root) const {
    const std::filesystem::path dir = analysisOutputDir(resolveOutputRoot(scenario_, output_root), scenario_.scenario_name, "energy_loss_scan");
    std::filesystem::create_directories(dir);

    const std::vector<SamplePoint> first_curve = energy_loss_.firstScintillatorCurve();
    const std::vector<SamplePoint> second_curve = energy_loss_.secondScintillatorCurve();

    std::vector<double> x_values;
    std::vector<double> first_values;
    std::vector<double> second_values;
    x_values.reserve(first_curve.size());
    first_values.reserve(first_curve.size());
    second_values.reserve(second_curve.size());
    for (const SamplePoint& sample : first_curve) {
        x_values.push_back(sample.x);
        first_values.push_back(sample.y);
    }
    for (const SamplePoint& sample : second_curve) {
        second_values.push_back(sample.y);
    }

    TCanvas canvas("energy_loss", "energy_loss", 900, 700);
    configureCanvasMargins(canvas);
    TGraph first_graph(static_cast<int>(x_values.size()), x_values.data(), first_values.data());
    TGraph second_graph(static_cast<int>(x_values.size()), x_values.data(), second_values.data());
    first_graph.SetTitle(";Incident energy (MeV/u);#DeltaE (MeV)");
    first_graph.SetLineColor(kRed + 1);
    second_graph.SetLineColor(kBlue + 1);
    first_graph.Draw("AL");
    second_graph.Draw("L SAME");
    TLegend legend(0.68, 0.74, 0.9, 0.9);
    legend.AddEntry(&first_graph, "1st scintillator", "l");
    legend.AddEntry(&second_graph, "2nd scintillator", "l");
    legend.Draw();

    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    artifacts.summary = {
        {"energy_loss_first_at_max_energy_mev", formatDouble(first_values.back(), 6)},
        {"energy_loss_second_at_max_energy_mev", formatDouble(second_values.back(), 6)},
    };
    saveCanvasAndTrack(artifacts, canvas, dir / "eloss");
    return finalizeArtifacts(std::move(artifacts));
}

AnalysisArtifacts AnalysisSession::runBatchWorkflow(const std::filesystem::path& output_root) const {
    const std::filesystem::path root = resolveOutputRoot(scenario_, output_root);
    const std::vector<AnalysisArtifacts> runs = {
        runTransformValidation(root),
        runLayoutOverlay(LayoutPreset::Custom, root),
        runLayoutOverlay(LayoutPreset::Sekiguchi, root),
        runEnergyPlot(root),
        runRatioScan(RatioMode::Deuteron, root),
        runRatioScan(RatioMode::Proton, root),
        runRatioScan(RatioMode::Coincidence, root),
        runLrudScan(LrudObservable::Proton, root),
        runLrudScan(LrudObservable::Coincidence, root),
        runCoincidenceScan(root),
        runCoincidenceTotalScan(root),
        runCrossSectionScan(root),
        runEnergyLossScan(root),
    };

    const std::filesystem::path dir = analysisOutputDir(root, scenario_.scenario_name, "batch_full");
    std::filesystem::create_directories(dir);

    std::ofstream manifest(dir / "artifacts.csv");
    manifest << "analysis,summary_csv,summary_json\n";
    AnalysisArtifacts artifacts;
    artifacts.output_dir = dir;
    for (const AnalysisArtifacts& run : runs) {
        const std::string analysis_name = run.output_dir.filename().string();
        manifest
            << analysis_name << ','
            << (run.output_dir / "summary.csv").string() << ','
            << (run.output_dir / "summary.json").string() << '\n';
        artifacts.summary.push_back({analysis_name, run.output_dir.string()});
        artifacts.files.push_back(run.output_dir / "summary.csv");
        artifacts.files.push_back(run.output_dir / "summary.json");
    }
    artifacts.files.push_back(dir / "artifacts.csv");
    return finalizeArtifacts(std::move(artifacts));
}

}  // namespace dpolar
