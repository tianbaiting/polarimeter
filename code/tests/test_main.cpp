#include "dpolar/acceptance.hpp"
#include "dpolar/config.hpp"
#include "dpolar/counts.hpp"
#include "dpolar/kinematics.hpp"
#include "dpolar/observables.hpp"

#include "TROOT.h"

#include <cmath>
#include <filesystem>
#include <iostream>
#include <numbers>
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

}  // namespace

int main() {
    try {
        gROOT->SetBatch(kTRUE);

        const std::filesystem::path scenario_path = std::filesystem::path(DPOLAR_SOURCE_DIR) / "config" / "default.ini";
        const dpolar::ScenarioConfig scenario = dpolar::loadScenarioConfig(scenario_path);
        const dpolar::ElasticDpKinematics kinematics(scenario.beam);
        const dpolar::ObservableTableRepository observables(scenario);
        const dpolar::CountRateCalculator counts(scenario, observables);

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

        std::cout << "All dpolar tests passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
