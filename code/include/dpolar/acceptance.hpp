#pragma once

#include "dpolar/kinematics.hpp"
#include "dpolar/types.hpp"

namespace dpolar {

[[nodiscard]] double thetaAcceptanceRad(double width_mm, double distance_mm);
[[nodiscard]] double phiAcceptanceRad(double width_mm, double distance_mm, double theta_lab_deg);
[[nodiscard]] CmBranchWindow normalizeWindow(double begin_rad, double end_rad, double delta_phi_rad);
[[nodiscard]] BranchPair deuteronWindowsFromArm(const ElasticDpKinematics& kinematics, const DetectorArm& arm);
[[nodiscard]] CmBranchWindow protonWindowFromArm(const ElasticDpKinematics& kinematics, const DetectorArm& arm);
[[nodiscard]] CmBranchWindow intersectWindows(const CmBranchWindow& left, const CmBranchWindow& right);
[[nodiscard]] AcceptanceCoverage computeCoverage(
    const ElasticDpKinematics& kinematics,
    const DetectorArm& arm,
    CoverageParticle particle,
    const CmBranchWindow& cm_window,
    const CoverageConfig& config);

}  // namespace dpolar
