#include "dpolar/config.hpp"
#include "dpolar/kinematics.hpp"
#include "dpolar/observables.hpp"
#include "dpolar/types.hpp"

#include "TAxis.h"
#include "TCanvas.h"
#include "TGraph.h"
#include "TLegend.h"
#include "TROOT.h"
#include "TStyle.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numbers>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

struct CurvePoint {
    double angle_deg {};
    double value_mb_per_sr {};
};

struct BranchCurves {
    std::vector<CurvePoint> first;
    std::vector<CurvePoint> second;
    std::vector<CurvePoint> total;
};

double finiteDifference(
    const dpolar::ElasticDpKinematics& kinematics,
    const double theta_cm_rad,
    const bool deuteron_branch) {
    const double support_margin_rad = dpolar::toRadians(1.0e-4);
    const double lower = std::max(support_margin_rad, theta_cm_rad - support_margin_rad);
    const double upper = std::min(std::numbers::pi_v<double> - support_margin_rad, theta_cm_rad + support_margin_rad);
    if (upper <= lower) {
        return std::numeric_limits<double>::quiet_NaN();
    }

    const dpolar::ScatteringSolution lower_solution = kinematics.scatter(lower, 0.0);
    const dpolar::ScatteringSolution upper_solution = kinematics.scatter(upper, 0.0);
    const double lower_theta_lab = deuteron_branch ? lower_solution.deuteron.theta_lab_rad : lower_solution.proton.theta_lab_rad;
    const double upper_theta_lab = deuteron_branch ? upper_solution.deuteron.theta_lab_rad : upper_solution.proton.theta_lab_rad;
    return (upper_theta_lab - lower_theta_lab) / (upper - lower);
}

double labCrossSectionFromCm(
    const dpolar::ObservableTableRepository& observables,
    const dpolar::ElasticDpKinematics& kinematics,
    const double theta_cm_rad,
    const bool deuteron_branch) {
    const dpolar::ScatteringSolution solution = kinematics.scatter(theta_cm_rad, 0.0);
    const double theta_lab_rad = deuteron_branch ? solution.deuteron.theta_lab_rad : solution.proton.theta_lab_rad;
    const double derivative = finiteDifference(kinematics, theta_cm_rad, deuteron_branch);
    if (!std::isfinite(theta_lab_rad) || !std::isfinite(derivative)) {
        return std::numeric_limits<double>::quiet_NaN();
    }

    const double sine_lab = std::sin(theta_lab_rad);
    const double sine_cm = std::sin(theta_cm_rad);
    const double safe_sine_lab = std::abs(sine_lab) < 1.0e-12 ? 1.0e-12 : sine_lab;
    const double safe_derivative = std::abs(derivative) < 1.0e-12 ? std::copysign(1.0e-12, derivative) : derivative;
    const double jacobian = sine_cm / (safe_sine_lab * std::abs(safe_derivative));
    return observables.differentialCrossSectionMbPerSr(dpolar::toDegrees(theta_cm_rad)) * jacobian;
}

std::vector<CurvePoint> makeCmCurve(
    const dpolar::ObservableTableRepository& observables,
    const int samples) {
    const std::vector<double>& cm_angles = observables.crossSectionAnglesDegrees();
    if (cm_angles.empty()) {
        throw std::runtime_error("Cross-section table is empty");
    }

    const double min_angle_deg = cm_angles.front();
    const double max_angle_deg = cm_angles.back();
    std::vector<CurvePoint> curve;
    curve.reserve(static_cast<std::size_t>(samples));
    for (int index = 0; index < samples; ++index) {
        const double fraction = samples == 1 ? 0.0 : static_cast<double>(index) / static_cast<double>(samples - 1);
        const double angle_deg = min_angle_deg + fraction * (max_angle_deg - min_angle_deg);
        curve.push_back(CurvePoint {
            angle_deg,
            observables.differentialCrossSectionMbPerSr(angle_deg),
        });
    }
    return curve;
}

std::vector<CurvePoint> makeProtonLabCurve(
    const dpolar::ObservableTableRepository& observables,
    const dpolar::ElasticDpKinematics& kinematics,
    const int samples) {
    const std::vector<double>& cm_angles = observables.crossSectionAnglesDegrees();
    if (cm_angles.empty()) {
        throw std::runtime_error("Cross-section table is empty");
    }

    const double min_cm_rad = dpolar::toRadians(cm_angles.front());
    const double max_cm_rad = dpolar::toRadians(cm_angles.back());
    std::vector<CurvePoint> curve;
    curve.reserve(static_cast<std::size_t>(samples));
    for (int index = 0; index < samples; ++index) {
        const double fraction = samples == 1 ? 0.0 : static_cast<double>(index) / static_cast<double>(samples - 1);
        const double theta_cm_rad = min_cm_rad + fraction * (max_cm_rad - min_cm_rad);
        const dpolar::ScatteringSolution solution = kinematics.scatter(theta_cm_rad, 0.0);
        curve.push_back(CurvePoint {
            dpolar::toDegrees(solution.proton.theta_lab_rad),
            labCrossSectionFromCm(observables, kinematics, theta_cm_rad, false),
        });
    }
    std::sort(curve.begin(), curve.end(), [](const CurvePoint& left, const CurvePoint& right) {
        return left.angle_deg < right.angle_deg;
    });
    return curve;
}

BranchCurves makeDeuteronLabCurves(
    const dpolar::ObservableTableRepository& observables,
    const dpolar::ElasticDpKinematics& kinematics,
    const int samples) {
    const std::vector<double>& cm_angles = observables.crossSectionAnglesDegrees();
    if (cm_angles.empty()) {
        throw std::runtime_error("Cross-section table is empty");
    }

    const double min_cm_rad = dpolar::toRadians(cm_angles.front());
    const double max_cm_rad = dpolar::toRadians(cm_angles.back());
    std::vector<CurvePoint> full_curve;
    full_curve.reserve(static_cast<std::size_t>(samples));
    for (int index = 0; index < samples; ++index) {
        const double fraction = samples == 1 ? 0.0 : static_cast<double>(index) / static_cast<double>(samples - 1);
        const double theta_cm_rad = min_cm_rad + fraction * (max_cm_rad - min_cm_rad);
        const dpolar::ScatteringSolution solution = kinematics.scatter(theta_cm_rad, 0.0);
        full_curve.push_back(CurvePoint {
            dpolar::toDegrees(solution.deuteron.theta_lab_rad),
            labCrossSectionFromCm(observables, kinematics, theta_cm_rad, true),
        });
    }

    const auto turning_point = std::max_element(
        full_curve.begin(),
        full_curve.end(),
        [](const CurvePoint& left, const CurvePoint& right) {
            return left.angle_deg < right.angle_deg;
        });
    const std::size_t turning_index = static_cast<std::size_t>(std::distance(full_curve.begin(), turning_point));

    BranchCurves curves;
    curves.first.assign(full_curve.begin(), full_curve.begin() + static_cast<long>(turning_index + 1U));
    curves.second.assign(full_curve.begin() + static_cast<long>(turning_index), full_curve.end());
    std::reverse(curves.second.begin(), curves.second.end());

    TGraph first_graph(static_cast<int>(curves.first.size()));
    for (std::size_t index = 0; index < curves.first.size(); ++index) {
        first_graph.SetPoint(
            static_cast<int>(index),
            curves.first[index].angle_deg,
            curves.first[index].value_mb_per_sr);
    }

    TGraph second_graph(static_cast<int>(curves.second.size()));
    for (std::size_t index = 0; index < curves.second.size(); ++index) {
        second_graph.SetPoint(
            static_cast<int>(index),
            curves.second[index].angle_deg,
            curves.second[index].value_mb_per_sr);
    }

    const double min_total_angle_deg = std::min(curves.first.front().angle_deg, curves.second.front().angle_deg);
    const double max_total_angle_deg = std::max(curves.first.back().angle_deg, curves.second.back().angle_deg);
    curves.total.reserve(static_cast<std::size_t>(samples));
    for (int index = 0; index < samples; ++index) {
        const double fraction = samples == 1 ? 0.0 : static_cast<double>(index) / static_cast<double>(samples - 1);
        const double angle_deg = min_total_angle_deg + fraction * (max_total_angle_deg - min_total_angle_deg);
        const double first_value =
            angle_deg >= curves.first.front().angle_deg && angle_deg <= curves.first.back().angle_deg
                ? first_graph.Eval(angle_deg)
                : 0.0;
        const double second_value =
            angle_deg >= curves.second.front().angle_deg && angle_deg <= curves.second.back().angle_deg
                ? second_graph.Eval(angle_deg)
                : 0.0;
        curves.total.push_back(CurvePoint {angle_deg, first_value + second_value});
    }
    return curves;
}

TGraph makeGraph(const std::vector<CurvePoint>& points) {
    TGraph graph(static_cast<int>(points.size()));
    for (std::size_t index = 0; index < points.size(); ++index) {
        graph.SetPoint(static_cast<int>(index), points[index].angle_deg, points[index].value_mb_per_sr);
    }
    return graph;
}

void styleGraph(TGraph& graph, const int color, const int style, const int width) {
    graph.SetLineColor(color);
    graph.SetMarkerColor(color);
    graph.SetLineStyle(style);
    graph.SetLineWidth(width);
}

std::filesystem::path resolveOutputPath(const std::filesystem::path& project_root, const int argc, char* argv[]) {
    if (argc >= 3) {
        return std::filesystem::absolute(argv[2]);
    }
    const std::filesystem::path repository_root = project_root.filename() == "code"
                                                      ? project_root.parent_path()
                                                      : project_root;
    return repository_root / "docs" / "code" / "polarimeter_stastic" / "img" / "dp_cross_section_frames.pdf";
}

std::filesystem::path resolveScenarioPath(const std::filesystem::path& project_root, const int argc, char* argv[]) {
    if (argc >= 2) {
        return std::filesystem::absolute(argv[1]);
    }
    return project_root / "code" / "config" / "default.ini";
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        gROOT->SetBatch(kTRUE);
        gStyle->SetOptStat(0);

        const std::filesystem::path default_project_root = std::filesystem::weakly_canonical(
            std::filesystem::path(argv[0]).parent_path() / ".." / "..");
        const std::filesystem::path scenario_path = resolveScenarioPath(default_project_root, argc, argv);
        const dpolar::ScenarioConfig scenario = dpolar::loadScenarioConfig(scenario_path);
        const std::filesystem::path output_path = resolveOutputPath(scenario.project_root, argc, argv);
        std::filesystem::create_directories(output_path.parent_path());

        const dpolar::ObservableTableRepository observables(scenario);
        const dpolar::ElasticDpKinematics kinematics(scenario.beam);

        const int samples = 1600;
        const std::vector<CurvePoint> cm_curve = makeCmCurve(observables, samples);
        const std::vector<CurvePoint> cm_points = [&observables]() {
            std::vector<CurvePoint> points;
            const std::vector<double>& angles = observables.crossSectionAnglesDegrees();
            const std::vector<double>& values = observables.crossSectionValues();
            points.reserve(angles.size());
            for (std::size_t index = 0; index < angles.size(); ++index) {
                points.push_back(CurvePoint {angles[index], values[index]});
            }
            return points;
        }();
        const std::vector<CurvePoint> proton_lab_curve = makeProtonLabCurve(observables, kinematics, samples);
        const BranchCurves deuteron_lab_curves = makeDeuteronLabCurves(observables, kinematics, samples);

        TCanvas canvas("dp_cross_sections", "dp_cross_sections", 1400, 620);
        canvas.Divide(2, 1);

        TGraph cm_graph = makeGraph(cm_curve);
        TGraph cm_marker_graph = makeGraph(cm_points);
        styleGraph(cm_graph, kBlue + 1, 1, 3);
        cm_marker_graph.SetMarkerStyle(20);
        cm_marker_graph.SetMarkerSize(0.75);
        cm_marker_graph.SetMarkerColor(kBlack);

        canvas.cd(1);
        gPad->SetLeftMargin(0.14);
        gPad->SetBottomMargin(0.12);
        gPad->SetLogy();
        cm_graph.SetTitle("Center-of-mass differential cross section");
        cm_graph.GetXaxis()->SetTitle("#theta_{c.m.} (deg)");
        cm_graph.GetYaxis()->SetTitle("d#sigma/d#Omega_{c.m.} (mb/sr)");
        cm_graph.GetXaxis()->SetTitleSize(0.048);
        cm_graph.GetYaxis()->SetTitleSize(0.048);
        cm_graph.GetXaxis()->SetLabelSize(0.042);
        cm_graph.GetYaxis()->SetLabelSize(0.042);
        cm_graph.Draw("AL");
        cm_marker_graph.Draw("P SAME");
        TLegend cm_legend(0.48, 0.72, 0.88, 0.88);
        cm_legend.SetBorderSize(0);
        cm_legend.SetFillStyle(0);
        cm_legend.AddEntry(&cm_graph, "Spline used by dpolar", "l");
        cm_legend.AddEntry(&cm_marker_graph, "Digitized table points", "p");
        cm_legend.Draw();

        TGraph proton_graph = makeGraph(proton_lab_curve);
        TGraph deuteron_total_graph = makeGraph(deuteron_lab_curves.total);
        TGraph deuteron_first_graph = makeGraph(deuteron_lab_curves.first);
        TGraph deuteron_second_graph = makeGraph(deuteron_lab_curves.second);
        styleGraph(proton_graph, kBlue + 1, 1, 3);
        styleGraph(deuteron_total_graph, kRed + 1, 1, 3);
        styleGraph(deuteron_first_graph, kRed + 1, 2, 2);
        styleGraph(deuteron_second_graph, kRed + 2, 3, 2);

        canvas.cd(2);
        gPad->SetLeftMargin(0.14);
        gPad->SetBottomMargin(0.12);
        gPad->SetLogy();
        proton_graph.SetTitle("Laboratory differential cross section");
        proton_graph.GetXaxis()->SetTitle("#theta_{lab} (deg)");
        proton_graph.GetYaxis()->SetTitle("d#sigma/d#Omega_{lab} (mb/sr)");
        proton_graph.GetXaxis()->SetTitleSize(0.048);
        proton_graph.GetYaxis()->SetTitleSize(0.048);
        proton_graph.GetXaxis()->SetLabelSize(0.042);
        proton_graph.GetYaxis()->SetLabelSize(0.042);
        proton_graph.Draw("AL");
        deuteron_total_graph.Draw("L SAME");
        deuteron_first_graph.Draw("L SAME");
        deuteron_second_graph.Draw("L SAME");
        TLegend lab_legend(0.44, 0.64, 0.88, 0.88);
        lab_legend.SetBorderSize(0);
        lab_legend.SetFillStyle(0);
        lab_legend.AddEntry(&proton_graph, "Proton, total", "l");
        lab_legend.AddEntry(&deuteron_total_graph, "Deuteron, total", "l");
        lab_legend.AddEntry(&deuteron_first_graph, "Deuteron branch 1", "l");
        lab_legend.AddEntry(&deuteron_second_graph, "Deuteron branch 2", "l");
        lab_legend.Draw();

        canvas.SaveAs(output_path.string().c_str());

        std::cout << std::fixed << std::setprecision(6)
                  << "scenario=" << scenario.scenario_path << '\n'
                  << "output=" << output_path << '\n'
                  << "cm_angle_range_deg=[" << observables.crossSectionAnglesDegrees().front() << ", "
                  << observables.crossSectionAnglesDegrees().back() << "]" << '\n'
                  << "proton_lab_range_deg=[" << proton_lab_curve.front().angle_deg << ", "
                  << proton_lab_curve.back().angle_deg << "]" << '\n'
                  << "deuteron_lab_range_deg=[" << deuteron_lab_curves.total.front().angle_deg << ", "
                  << deuteron_lab_curves.total.back().angle_deg << "]" << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "dpol_plot_cross_sections failed: " << error.what() << '\n';
        return 1;
    }
}
