#include "dpolar/acceptance.hpp"

#include <algorithm>
#include <cmath>
#include <numbers>

namespace dpolar {
namespace {

double canonicalLabPhiCenter(const CoverageParticle particle) {
    return particle == CoverageParticle::Deuteron
               ? std::numbers::pi_v<double> / 2.0
               : 3.0 * std::numbers::pi_v<double> / 2.0;
}

double wrapToZeroToTwoPi(double angle_rad) {
    const double full_turn = 2.0 * std::numbers::pi_v<double>;
    while (angle_rad < 0.0) {
        angle_rad += full_turn;
    }
    while (angle_rad >= full_turn) {
        angle_rad -= full_turn;
    }
    return angle_rad;
}

double wrappedAngleDifference(double left_rad, double right_rad) {
    const double full_turn = 2.0 * std::numbers::pi_v<double>;
    double difference = wrapToZeroToTwoPi(left_rad) - wrapToZeroToTwoPi(right_rad);
    while (difference <= -std::numbers::pi_v<double>) {
        difference += full_turn;
    }
    while (difference > std::numbers::pi_v<double>) {
        difference -= full_turn;
    }
    return difference;
}

}  // namespace

double thetaAcceptanceRad(const double width_mm, const double distance_mm) {
    return width_mm / distance_mm;
}

double phiAcceptanceRad(const double width_mm, const double distance_mm, const double theta_lab_deg) {
    const double sine = std::sin(toRadians(theta_lab_deg));
    const double safe_sine = std::abs(sine) < 1.0e-9 ? 1.0e-9 : sine;
    return width_mm / distance_mm / safe_sine;
}

CmBranchWindow normalizeWindow(const double begin_rad, const double end_rad, const double delta_phi_rad) {
    return CmBranchWindow {
        std::min(begin_rad, end_rad),
        std::max(begin_rad, end_rad),
        delta_phi_rad,
    };
}

BranchPair deuteronWindowsFromArm(const ElasticDpKinematics& kinematics, const DetectorArm& arm) {
    const double delta_theta = thetaAcceptanceRad(arm.width_theta_mm, arm.distance_mm);
    const double delta_phi = phiAcceptanceRad(arm.width_phi_mm, arm.distance_mm, arm.theta_lab_deg);
    const auto lower_edge = kinematics.deuteronCmFromLab(toRadians(arm.theta_lab_deg) - delta_theta / 2.0);
    const auto upper_edge = kinematics.deuteronCmFromLab(toRadians(arm.theta_lab_deg) + delta_theta / 2.0);

    return BranchPair {
        normalizeWindow(lower_edge.first, upper_edge.first, delta_phi),
        normalizeWindow(lower_edge.second, upper_edge.second, delta_phi),
    };
}

CmBranchWindow protonWindowFromArm(const ElasticDpKinematics& kinematics, const DetectorArm& arm) {
    const double delta_theta = thetaAcceptanceRad(arm.width_theta_mm, arm.distance_mm);
    const double delta_phi = phiAcceptanceRad(arm.width_phi_mm, arm.distance_mm, arm.theta_lab_deg);
    const double begin = kinematics.protonCmFromLab(toRadians(arm.theta_lab_deg) + delta_theta / 2.0);
    const double end = kinematics.protonCmFromLab(toRadians(arm.theta_lab_deg) - delta_theta / 2.0);
    return normalizeWindow(begin, end, delta_phi);
}

CmBranchWindow intersectWindows(const CmBranchWindow& left, const CmBranchWindow& right) {
    const double begin = std::max(left.begin_rad, right.begin_rad);
    const double end = std::min(left.end_rad, right.end_rad);
    const double delta_phi = std::min(left.delta_phi_rad, right.delta_phi_rad);
    if (end <= begin || delta_phi <= 0.0) {
        return CmBranchWindow {};
    }
    // [EN] Coincidence gating must satisfy both detector openings, so the shared azimuth is the narrower one / [CN] 重合门必须同时满足两臂开口，因此共享方位角取更窄的一侧
    return CmBranchWindow {begin, end, delta_phi};
}

AcceptanceCoverage computeCoverage(
    const ElasticDpKinematics& kinematics,
    const DetectorArm& arm,
    const CoverageParticle particle,
    const CmBranchWindow& cm_window,
    const CoverageConfig& config) {
    AcceptanceCoverage coverage;
    coverage.particle = particle;
    coverage.theta_bins = config.theta_bins;
    coverage.phi_bins = config.phi_bins;
    coverage.lab_phi_center_rad = canonicalLabPhiCenter(particle);
    coverage.accepted_map.assign(static_cast<std::size_t>(config.theta_bins * config.phi_bins), 0.0);

    if (!cm_window.valid()) {
        coverage.theta_cm_min_rad = 0.0;
        coverage.phi_cm_min_rad = 0.0;
        return coverage;
    }

    const double theta_lab_center_rad = toRadians(arm.theta_lab_deg);
    const double theta_half_width_rad = thetaAcceptanceRad(arm.width_theta_mm, arm.distance_mm) / 2.0;
    const double phi_half_width_rad = phiAcceptanceRad(arm.width_phi_mm, arm.distance_mm, arm.theta_lab_deg) / 2.0;
    const double theta_step_rad = (coverage.theta_grid_max_rad - coverage.theta_grid_min_rad) / static_cast<double>(config.theta_bins);
    const double phi_step_rad = (coverage.phi_grid_max_rad - coverage.phi_grid_min_rad) / static_cast<double>(config.phi_bins);

    for (int theta_index = 0; theta_index < config.theta_bins; ++theta_index) {
        const double theta_cm_rad = coverage.theta_grid_min_rad + (static_cast<double>(theta_index) + 0.5) * theta_step_rad;
        if (theta_cm_rad < cm_window.begin_rad || theta_cm_rad > cm_window.end_rad) {
            continue;
        }
        for (int phi_index = 0; phi_index < config.phi_bins; ++phi_index) {
            const double phi_cm_rad = coverage.phi_grid_min_rad + (static_cast<double>(phi_index) + 0.5) * phi_step_rad;
            const ScatteringSolution solution = kinematics.scatter(theta_cm_rad, phi_cm_rad);
            const ScatterPoint& point = particle == CoverageParticle::Deuteron ? solution.deuteron : solution.proton;
            const bool theta_match = std::abs(point.theta_lab_rad - theta_lab_center_rad) <= theta_half_width_rad;
            const bool phi_match = std::abs(wrappedAngleDifference(point.phi_lab_rad, coverage.lab_phi_center_rad)) <= phi_half_width_rad;
            if (!theta_match || !phi_match) {
                continue;
            }

            const std::size_t flat_index = static_cast<std::size_t>(theta_index * config.phi_bins + phi_index);
            coverage.accepted_map[flat_index] = 1.0;
            coverage.accepted_solid_angle_sr += std::sin(theta_cm_rad) * theta_step_rad * phi_step_rad;
            coverage.accepted_cells += 1;
            coverage.theta_cm_min_rad = std::min(coverage.theta_cm_min_rad, theta_cm_rad);
            coverage.theta_cm_max_rad = std::max(coverage.theta_cm_max_rad, theta_cm_rad);
            coverage.phi_cm_min_rad = std::min(coverage.phi_cm_min_rad, phi_cm_rad);
            coverage.phi_cm_max_rad = std::max(coverage.phi_cm_max_rad, phi_cm_rad);
        }
    }

    if (!coverage.hasAcceptance()) {
        coverage.theta_cm_min_rad = 0.0;
        coverage.phi_cm_min_rad = 0.0;
    }

    return coverage;
}

}  // namespace dpolar
