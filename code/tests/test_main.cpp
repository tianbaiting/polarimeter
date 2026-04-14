#include "dpolar/acceptance.hpp"
#include "dpolar/analysis.hpp"
#include "dpolar/config.hpp"
#include "dpolar/counts.hpp"
#include "dpolar/inference.hpp"
#include "dpolar/inference_plot.hpp"
#include "dpolar/kinematics.hpp"
#include "dpolar/observables.hpp"

#include "TROOT.h"

#include <chrono>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <numbers>
#include <optional>
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
        const dpolar::PolarizationInference inference(scenario);
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

        const double proton_pair_first =
            counts.countsFromIntegratedCrossSection(counts.integralForPzz(proton_forward, pzz))
            * scenario.run.single_arm_sector_multiplier;
        const double proton_pair_second =
            counts.countsFromIntegratedCrossSection(counts.integralForPzz(proton_backward, pzz))
            * scenario.run.single_arm_sector_multiplier;
        const dpolar::PolarizationEstimate proton_pair_estimate =
            inference.inferPzzFromCounts(dpolar::PzzObservable::Proton, proton_pair_first, proton_pair_second);
        require(approx(proton_pair_estimate.estimate, pzz, 1.0e-5), "pair pzz inference must recover the input polarization");
        require(
            proton_pair_estimate.ci68.low <= pzz && proton_pair_estimate.ci68.high >= pzz,
            "pair pzz 68% interval must contain the true polarization");
        require(
            proton_pair_estimate.ci95.low <= proton_pair_estimate.ci68.low &&
                proton_pair_estimate.ci95.high >= proton_pair_estimate.ci68.high,
            "pair pzz 95% interval must bracket the 68% interval");

        const dpolar::PolarizationEstimate proton_total_estimate =
            inference.inferPzzFromTotalCount(dpolar::PzzObservable::Proton, proton_single_counts);
        require(
            approx(proton_total_estimate.estimate, pzz, 1.0e-5),
            "absolute pzz inference must recover the input polarization");

        const double coincidence_pair_first =
            counts.countsFromIntegratedCrossSection(counts.integralForPzz(overlap_forward, pzz))
            * scenario.run.coincidence_sector_multiplier;
        const double coincidence_pair_second =
            counts.countsFromIntegratedCrossSection(counts.integralForPzz(overlap_backward, pzz))
            * scenario.run.coincidence_sector_multiplier;
        const dpolar::PolarizationEstimate coincidence_pair_estimate =
            inference.inferPzzFromCounts(dpolar::PzzObservable::Coincidence, coincidence_pair_first, coincidence_pair_second);
        require(
            approx(coincidence_pair_estimate.estimate, pzz, 1.0e-5),
            "coincidence pair pzz inference must recover the input polarization");
        require(
            coincidence_pair_estimate.ci68.low <= pzz && coincidence_pair_estimate.ci68.high >= pzz,
            "coincidence pair pzz 68% interval must contain the true polarization");

        const double pyy = 0.6;
        const double left_right_count =
            counts.countsFromIntegratedCrossSection(counts.integralForLr(proton_forward, pyy))
            * scenario.run.lrud_sector_multiplier;
        const double up_down_count =
            counts.countsFromIntegratedCrossSection(counts.integralForUd(proton_forward, pyy))
            * scenario.run.lrud_sector_multiplier;
        const dpolar::PolarizationEstimate pyy_estimate =
            inference.inferPyyFromLrudCounts(left_right_count, up_down_count);
        require(approx(pyy_estimate.estimate, pyy, 1.0e-5), "pyy inference must recover the LR/UD input polarization");
        require(
            pyy_estimate.ci68.low <= pyy && pyy_estimate.ci68.high >= pyy,
            "pyy 68% interval must contain the true polarization");

        const double coincidence_left_right_count =
            counts.countsFromIntegratedCrossSection(counts.integralForLr(overlap_forward, pyy))
            * scenario.run.lrud_sector_multiplier;
        const double coincidence_up_down_count =
            counts.countsFromIntegratedCrossSection(counts.integralForUd(overlap_forward, pyy))
            * scenario.run.lrud_sector_multiplier;
        const dpolar::PolarizationEstimate coincidence_pyy_estimate =
            inference.inferPyyFromLrudCounts(
                dpolar::LrudObservable::Coincidence,
                coincidence_left_right_count,
                coincidence_up_down_count);
        require(
            approx(coincidence_pyy_estimate.estimate, pyy, 1.0e-5),
            "coincidence-gated pyy inference must recover the input polarization");
        require(
            coincidence_pyy_estimate.ci68.low <= pyy && coincidence_pyy_estimate.ci68.high >= pyy,
            "coincidence-gated pyy 68% interval must contain the true polarization");

        const dpolar::PolarizationEstimate zero_count_estimate =
            inference.inferPzzFromTotalCount(dpolar::PzzObservable::Coincidence, 0.0);
        const double coincidence_at_scan_min =
            counts.countsFromIntegratedCrossSection(
                counts.integralForPzz(overlap_forward, scenario.scan.polarization_min) +
                counts.integralForPzz(overlap_backward, scenario.scan.polarization_min))
            * scenario.run.coincidence_sector_multiplier;
        const double coincidence_at_scan_max =
            counts.countsFromIntegratedCrossSection(
                counts.integralForPzz(overlap_forward, scenario.scan.polarization_max) +
                counts.integralForPzz(overlap_backward, scenario.scan.polarization_max))
            * scenario.run.coincidence_sector_multiplier;
        const bool expect_upper_boundary = coincidence_at_scan_max < coincidence_at_scan_min;
        require(
            expect_upper_boundary ? zero_count_estimate.at_upper_bound : zero_count_estimate.at_lower_bound,
            "zero-count pzz inference must clamp to the scan boundary with the lower expected coincidence count");

        bool zero_lrud_failed = false;
        try {
            static_cast<void>(inference.inferPyyFromLrudCounts(0.0, 0.0));
        } catch (const std::exception&) {
            zero_lrud_failed = true;
        }
        require(zero_lrud_failed, "zero-total LR/UD inference must report a failure");

        const std::filesystem::path overlay_root =
            std::filesystem::temp_directory_path() /
            ("dpolar_overlay_tests_" + std::to_string(static_cast<long long>(
                                         std::chrono::steady_clock::now().time_since_epoch().count())));
        std::filesystem::remove_all(overlay_root);

        const dpolar::AnalysisArtifacts pzz_plot_artifacts =
            dpolar::runPzzInferencePlot(
                inference,
                dpolar::PzzObservable::Proton,
                proton_pair_first,
                std::optional<double> {proton_pair_second},
                "proton_pair_case",
                overlay_root);
        require(
            std::filesystem::exists(pzz_plot_artifacts.output_dir / "Profile_likelihood_vs_pzz.pdf"),
            "pzz likelihood pdf was not generated");
        require(
            std::filesystem::exists(pzz_plot_artifacts.output_dir / "Profile_likelihood_vs_pzz.png"),
            "pzz likelihood png was not generated");
        require(
            std::filesystem::exists(pzz_plot_artifacts.output_dir / "likelihood_scan.csv"),
            "pzz likelihood scan csv was not generated");
        require(
            std::filesystem::exists(pzz_plot_artifacts.output_dir / "summary.json"),
            "pzz likelihood summary json was not generated");
        require(
            approx(std::stod(findSummaryValue(pzz_plot_artifacts.summary, "estimate")), pzz, 1.0e-5),
            "pzz likelihood summary must report the injected polarization");
        require(
            findSummaryValue(pzz_plot_artifacts.summary, "likelihood_point_count") == "401",
            "pzz likelihood scan must use the expected point count");

        const dpolar::AnalysisArtifacts pyy_plot_artifacts =
            dpolar::runPyyInferencePlot(
                inference,
                dpolar::LrudObservable::Proton,
                left_right_count,
                up_down_count,
                "lrud_case",
                overlay_root);
        require(
            std::filesystem::exists(pyy_plot_artifacts.output_dir / "Profile_likelihood_vs_pyy.pdf"),
            "pyy likelihood pdf was not generated");
        require(
            std::filesystem::exists(pyy_plot_artifacts.output_dir / "Profile_likelihood_vs_pyy.png"),
            "pyy likelihood png was not generated");
        require(
            std::filesystem::exists(pyy_plot_artifacts.output_dir / "likelihood_scan.csv"),
            "pyy likelihood scan csv was not generated");
        require(
            std::filesystem::exists(pyy_plot_artifacts.output_dir / "summary.json"),
            "pyy likelihood summary json was not generated");
        require(
            approx(std::stod(findSummaryValue(pyy_plot_artifacts.summary, "estimate")), pyy, 1.0e-5),
            "pyy likelihood summary must report the injected polarization");

        const dpolar::AnalysisArtifacts coincidence_pzz_plot_artifacts =
            dpolar::runPzzInferencePlot(
                inference,
                dpolar::PzzObservable::Coincidence,
                coincidence_pair_first,
                std::optional<double> {coincidence_pair_second},
                "coincidence_pair_case",
                overlay_root);
        require(
            std::filesystem::exists(coincidence_pzz_plot_artifacts.output_dir / "Profile_likelihood_vs_pzz.pdf"),
            "coincidence pair pzz likelihood pdf was not generated");
        require(
            approx(std::stod(findSummaryValue(coincidence_pzz_plot_artifacts.summary, "estimate")), pzz, 1.0e-5),
            "coincidence pair pzz likelihood summary must report the injected polarization");

        const dpolar::AnalysisArtifacts coincidence_pyy_plot_artifacts =
            dpolar::runPyyInferencePlot(
                inference,
                dpolar::LrudObservable::Coincidence,
                coincidence_left_right_count,
                coincidence_up_down_count,
                "lrud_coincidence_case",
                overlay_root);
        require(
            std::filesystem::exists(coincidence_pyy_plot_artifacts.output_dir / "Profile_likelihood_vs_pyy.pdf"),
            "coincidence-gated pyy likelihood pdf was not generated");
        require(
            approx(std::stod(findSummaryValue(coincidence_pyy_plot_artifacts.summary, "estimate")), pyy, 1.0e-5),
            "coincidence-gated pyy likelihood summary must report the injected polarization");

        const dpolar::AnalysisArtifacts zero_count_plot_artifacts =
            dpolar::runPzzInferencePlot(
                inference,
                dpolar::PzzObservable::Coincidence,
                0.0,
                std::nullopt,
                "coincidence_zero_case",
                overlay_root);
        require(
            std::filesystem::exists(zero_count_plot_artifacts.output_dir / "Profile_likelihood_vs_pzz.pdf"),
            "zero-count coincidence likelihood pdf was not generated");

        bool zero_lrud_plot_failed = false;
        try {
            static_cast<void>(
                dpolar::runPyyInferencePlot(
                    inference,
                    dpolar::LrudObservable::Proton,
                    0.0,
                    0.0,
                    "lrud_zero_case",
                    overlay_root));
        } catch (const std::exception&) {
            zero_lrud_plot_failed = true;
        }
        require(zero_lrud_plot_failed, "zero-total LR/UD likelihood plot must report a failure");

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

        dpolar::ScenarioConfig single_duration_scenario = scenario;
        single_duration_scenario.run.duration_s_list = {single_duration_scenario.run.duration_s};
        const dpolar::AnalysisSession single_duration_analysis(single_duration_scenario);
        const dpolar::AnalysisArtifacts coincidence_scan_artifacts =
            single_duration_analysis.runCoincidenceScan(overlay_root);
        require(
            std::filesystem::exists(coincidence_scan_artifacts.output_dir / "Coincidence_efficiency_forward_vs_pzz.pdf"),
            "coincidence forward efficiency pdf was not generated");
        require(
            std::filesystem::exists(coincidence_scan_artifacts.output_dir / "Coincidence_efficiency_backward_vs_pzz.pdf"),
            "coincidence backward efficiency pdf was not generated");
        require(
            std::filesystem::exists(coincidence_scan_artifacts.output_dir / "summary.json"),
            "coincidence scan summary json was not generated");
        const double max_pzz = scenario.scan.polarization_max;
        const double expected_forward_efficiency_one_sector =
            counts.countsFromIntegratedCrossSection(counts.integralForPzz(overlap_forward, max_pzz)) /
            counts.countsFromIntegratedCrossSection(counts.integralForPzz(proton_forward, max_pzz));
        const double expected_backward_efficiency_one_sector =
            counts.countsFromIntegratedCrossSection(counts.integralForPzz(overlap_backward, max_pzz)) /
            counts.countsFromIntegratedCrossSection(counts.integralForPzz(proton_backward, max_pzz));
        require(
            approx(
                std::stod(findSummaryValue(
                    coincidence_scan_artifacts.summary,
                    "coincidence_forward_efficiency_one_sector_at_max_pol")),
                expected_forward_efficiency_one_sector,
                1.0e-6),
            "forward coincidence efficiency must be normalized to one proton sector");
        require(
            approx(
                std::stod(findSummaryValue(
                    coincidence_scan_artifacts.summary,
                    "coincidence_backward_efficiency_one_sector_at_max_pol")),
                expected_backward_efficiency_one_sector,
                1.0e-6),
            "backward coincidence efficiency must be normalized to one proton sector");

        const dpolar::AnalysisArtifacts ratio_proton_artifacts =
            single_duration_analysis.runRatioScan(dpolar::RatioMode::Proton, overlay_root);
        require(
            std::filesystem::exists(ratio_proton_artifacts.output_dir / "Inferred_pzz_vs_true_pzz.pdf"),
            "proton ratio inference summary pdf was not generated");
        require(
            std::filesystem::exists(ratio_proton_artifacts.output_dir / "inference_scan.csv"),
            "proton ratio inference csv was not generated");
        require(
            findSummaryValue(ratio_proton_artifacts.summary, "inference_point_count") == "11",
            "proton ratio inference point count mismatch");

        const dpolar::AnalysisArtifacts ratio_coincidence_artifacts =
            single_duration_analysis.runRatioScan(dpolar::RatioMode::Coincidence, overlay_root);
        require(
            std::filesystem::exists(ratio_coincidence_artifacts.output_dir / "Ratio_vs_pzz_stat_only.pdf"),
            "coincidence ratio pdf was not generated");
        require(
            std::filesystem::exists(ratio_coincidence_artifacts.output_dir / "Inferred_pzz_vs_true_pzz.pdf"),
            "coincidence ratio inference summary pdf was not generated");
        require(
            findSummaryValue(ratio_coincidence_artifacts.summary, "ratio_observable") == "coincidence",
            "coincidence ratio observable summary mismatch");

        const dpolar::AnalysisArtifacts lrud_proton_artifacts =
            single_duration_analysis.runLrudScan(dpolar::LrudObservable::Proton, overlay_root);
        require(
            std::filesystem::exists(lrud_proton_artifacts.output_dir / "N_LR_N_UD_vs_pyy_stat_only.pdf"),
            "proton LRUD count pdf was not generated");
        require(
            std::filesystem::exists(lrud_proton_artifacts.output_dir / "Inferred_pyy_vs_true_pyy.pdf"),
            "proton LRUD inference summary pdf was not generated");
        require(
            findSummaryValue(lrud_proton_artifacts.summary, "lrud_observable") == "proton",
            "proton LRUD observable summary mismatch");

        const dpolar::AnalysisArtifacts lrud_coincidence_artifacts =
            single_duration_analysis.runLrudScan(dpolar::LrudObservable::Coincidence, overlay_root);
        require(
            std::filesystem::exists(lrud_coincidence_artifacts.output_dir / "N_LR_N_UD_vs_pyy_stat_only.pdf"),
            "coincidence-gated LRUD count pdf was not generated");
        require(
            std::filesystem::exists(lrud_coincidence_artifacts.output_dir / "Inferred_pyy_vs_true_pyy.pdf"),
            "coincidence-gated LRUD inference summary pdf was not generated");
        require(
            findSummaryValue(lrud_coincidence_artifacts.summary, "lrud_observable") == "coincidence",
            "coincidence-gated LRUD observable summary mismatch");
        std::filesystem::remove_all(overlay_root);

        std::cout << "All dpolar tests passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
