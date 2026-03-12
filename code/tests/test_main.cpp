#include "dpolar/acceptance.hpp"
#include "dpolar/analysis.hpp"
#include "dpolar/config.hpp"
#include "dpolar/counts.hpp"
#include "dpolar/kinematics.hpp"
#include "dpolar/observables.hpp"

#include "TROOT.h"

#include <chrono>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <numbers>
#include <string>
#include <stdexcept>

namespace {

bool approx(const double left, const double right, const double tolerance) {
    return std::abs(left - right) <= tolerance;
}

void require(const bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

std::string findSummaryValue(
    const std::vector<dpolar::SummaryEntry>& summary,
    const std::string& key) {
    for (const dpolar::SummaryEntry& entry : summary) {
        if (entry.key == key) {
            return entry.value;
        }
    }
    throw std::runtime_error("Missing summary key: " + key);
}

}  // namespace

int main() {
    try {
        gROOT->SetBatch(kTRUE);

        const std::filesystem::path scenario_path = std::filesystem::path(DPOLAR_SOURCE_DIR) / "config" / "default.ini";
        const dpolar::ScenarioConfig scenario = dpolar::loadScenarioConfig(scenario_path);
        const dpolar::ElasticDpKinematics kinematics(scenario.beam);
        const dpolar::ObservableTableRepository observables(scenario);
        const dpolar::CountRateCalculator counts(scenario, observables);
        const dpolar::AnalysisSession analysis(scenario);

        const double theta_cm_rad = dpolar::toRadians(68.6);
        const dpolar::ScatteringSolution solution = kinematics.scatter(theta_cm_rad, 0.0);
        const auto recovered = kinematics.deuteronCmFromLab(solution.deuteron.theta_lab_rad);
        require(
            approx(theta_cm_rad, recovered.first, 1.0e-10) || approx(theta_cm_rad, recovered.second, 1.0e-10),
            "deuteron CM roundtrip failed");

        const double proton_lab_rad = kinematics.protonLabFromDeuteronCm(theta_cm_rad);
        const double proton_cm_rad = kinematics.protonCmFromLab(proton_lab_rad);
        require(
            approx(proton_cm_rad, theta_cm_rad, 1.0e-10),
            "proton CM roundtrip failed");

        const dpolar::BranchPair deuteron_windows = dpolar::deuteronWindowsFromArm(kinematics, scenario.custom_layout.deuteron_arm);
        const dpolar::CmBranchWindow proton_forward = dpolar::protonWindowFromArm(kinematics, scenario.custom_layout.proton_arms[0]);
        const dpolar::CmBranchWindow proton_backward = dpolar::protonWindowFromArm(kinematics, scenario.custom_layout.proton_arms[1]);
        const dpolar::CmBranchWindow overlap_forward = dpolar::intersectWindows(proton_forward, deuteron_windows.forward);
        const dpolar::CmBranchWindow overlap_backward = dpolar::intersectWindows(proton_backward, deuteron_windows.backward);

        const dpolar::AcceptanceCoverage proton_coverage = dpolar::computeCoverage(
            kinematics,
            scenario.custom_layout.proton_arms[0],
            dpolar::CoverageParticle::Proton,
            proton_forward,
            scenario.coverage);
        require(proton_coverage.accepted_solid_angle_sr > 0.0, "proton coverage solid angle must be positive");

        const dpolar::AcceptanceCoverage deuteron_coverage = dpolar::computeCoverage(
            kinematics,
            scenario.custom_layout.deuteron_arm,
            dpolar::CoverageParticle::Deuteron,
            deuteron_windows.forward,
            scenario.coverage);
        require(deuteron_coverage.accepted_solid_angle_sr > 0.0, "deuteron coverage solid angle must be positive");

        const double pzz = 0.5;
        const double coincidence_counts = counts.countsFromIntegratedCrossSection(counts.integralForPzz(overlap_forward, pzz) + counts.integralForPzz(overlap_backward, pzz));
        const double proton_single_counts = counts.countsFromIntegratedCrossSection(counts.integralForPzz(proton_forward, pzz) + counts.integralForPzz(proton_backward, pzz))
                                            * scenario.run.single_arm_sector_multiplier;
        const double deuteron_single_counts = counts.countsFromIntegratedCrossSection(counts.integralForPzz(deuteron_windows.forward, pzz) + counts.integralForPzz(deuteron_windows.backward, pzz))
                                              * scenario.run.single_arm_sector_multiplier;
        require(coincidence_counts <= proton_single_counts + 1.0e-9, "coincidence counts exceed proton singles");
        require(coincidence_counts <= deuteron_single_counts + 1.0e-9, "coincidence counts exceed deuteron singles");

        const dpolar::CmBranchWindow zero_overlap {};
        require(counts.integralForPzz(zero_overlap, pzz) == 0.0, "zero-overlap window must integrate to zero");
        require(
            approx(counts.countVarianceFromTensorForPzz(proton_forward, 0.0), 0.0, 1.0e-12),
            "pzz tensor variance must vanish at zero polarization");
        require(
            approx(counts.countVarianceFromTensorForLr(proton_forward, 0.0), 0.0, 1.0e-12),
            "LR tensor variance must vanish at zero polarization");
        require(
            approx(counts.countVarianceFromTensorForUd(proton_forward, 0.0), 0.0, 1.0e-12),
            "UD tensor variance must vanish at zero polarization");

        const std::filesystem::path overlay_root =
            std::filesystem::temp_directory_path() /
            ("dpolar_overlay_tests_" + std::to_string(static_cast<long long>(
                                         std::chrono::steady_clock::now().time_since_epoch().count())));
        std::filesystem::remove_all(overlay_root);

        const dpolar::AnalysisArtifacts custom_artifacts =
            analysis.runLayoutOverlay(dpolar::LayoutPreset::Custom, overlay_root);
        require(
            std::filesystem::exists(custom_artifacts.output_dir / "Pol_angcover_flipped.pdf"),
            "custom layout pdf was not generated");
        require(
            std::filesystem::exists(custom_artifacts.output_dir / "Pol_angcover_flipped.png"),
            "custom layout png was not generated");
        require(
            std::filesystem::exists(custom_artifacts.output_dir / "coverage.csv"),
            "custom layout coverage csv was not generated");
        require(
            std::filesystem::exists(custom_artifacts.output_dir / "summary.json"),
            "custom layout summary json was not generated");
        require(
            findSummaryValue(custom_artifacts.summary, "overlay_annotation_count") == "4",
            "custom overlay annotation count mismatch");
        require(
            findSummaryValue(custom_artifacts.summary, "overlay_proton_annotation_count") == "2",
            "custom proton annotation count mismatch");
        require(
            findSummaryValue(custom_artifacts.summary, "overlay_deuteron_annotation_count") == "2",
            "custom deuteron annotation count mismatch");
        require(
            findSummaryValue(custom_artifacts.summary, "overlay_annotation_style") == "inline_short_label_plus_side_table",
            "custom overlay annotation style mismatch");

        const dpolar::AnalysisArtifacts sekiguchi_artifacts =
            analysis.runLayoutOverlay(dpolar::LayoutPreset::Sekiguchi, overlay_root);
        require(
            std::filesystem::exists(sekiguchi_artifacts.output_dir / "ThetaLab_vs_ThetaDc_deg.pdf"),
            "sekiguchi layout pdf was not generated");
        require(
            std::filesystem::exists(sekiguchi_artifacts.output_dir / "ThetaLab_vs_ThetaDc_deg.png"),
            "sekiguchi layout png was not generated");
        require(
            std::filesystem::exists(sekiguchi_artifacts.output_dir / "coverage.csv"),
            "sekiguchi layout coverage csv was not generated");
        require(
            std::filesystem::exists(sekiguchi_artifacts.output_dir / "summary.json"),
            "sekiguchi layout summary json was not generated");
        require(
            findSummaryValue(sekiguchi_artifacts.summary, "overlay_annotation_count") == "16",
            "sekiguchi overlay annotation count mismatch");
        require(
            findSummaryValue(sekiguchi_artifacts.summary, "overlay_proton_annotation_count") == "8",
            "sekiguchi proton annotation count mismatch");
        require(
            findSummaryValue(sekiguchi_artifacts.summary, "overlay_deuteron_annotation_count") == "8",
            "sekiguchi deuteron annotation count mismatch");
        require(
            findSummaryValue(sekiguchi_artifacts.summary, "overlay_annotation_style") == "inline_short_label_plus_side_table",
            "sekiguchi overlay annotation style mismatch");

        dpolar::ScenarioConfig coincidence_total_scenario = scenario;
        coincidence_total_scenario.run.duration_s_list = {coincidence_total_scenario.run.duration_s};
        const dpolar::AnalysisSession coincidence_total_analysis(coincidence_total_scenario);
        const dpolar::AnalysisArtifacts coincidence_total_artifacts =
            coincidence_total_analysis.runCoincidenceTotalScan(overlay_root);
        require(
            std::filesystem::exists(coincidence_total_artifacts.output_dir / "Coincidence_total_vs_pzz.pdf"),
            "coincidence total pdf was not generated");
        require(
            std::filesystem::exists(coincidence_total_artifacts.output_dir / "Coincidence_total_vs_pzz.png"),
            "coincidence total png was not generated");
        require(
            std::filesystem::exists(coincidence_total_artifacts.output_dir / "scan_points.csv"),
            "coincidence total scan csv was not generated");
        require(
            std::filesystem::exists(coincidence_total_artifacts.output_dir / "summary.json"),
            "coincidence total summary json was not generated");
        const double coincidence_total_at_max_pol =
            std::stod(findSummaryValue(coincidence_total_artifacts.summary, "coincidence_total_at_max_pol"));
        const double coincidence_forward_at_max_pol =
            std::stod(findSummaryValue(coincidence_total_artifacts.summary, "coincidence_forward_at_max_pol"));
        const double coincidence_backward_at_max_pol =
            std::stod(findSummaryValue(coincidence_total_artifacts.summary, "coincidence_backward_at_max_pol"));
        require(
            approx(
                coincidence_total_at_max_pol,
                coincidence_forward_at_max_pol + coincidence_backward_at_max_pol,
                1.0e-6),
            "coincidence total count must equal forward plus backward coincidence counts");
        std::filesystem::remove_all(overlay_root);

        std::cout << "All dpolar tests passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
