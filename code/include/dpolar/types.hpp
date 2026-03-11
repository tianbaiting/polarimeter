#pragma once

#include <cmath>
#include <cstddef>
#include <numbers>
#include <string>
#include <vector>

namespace dpolar {

constexpr double kDegreesToRadians = std::numbers::pi_v<double> / 180.0;
constexpr double kRadiansToDegrees = 180.0 / std::numbers::pi_v<double>;
constexpr double kMillibarnToSquareMeter = 1.0e-31;

inline double toRadians(const double degrees) noexcept {
    return degrees * kDegreesToRadians;
}

inline double toDegrees(const double radians) noexcept {
    return radians * kRadiansToDegrees;
}

struct DetectorArm {
    double theta_lab_deg {};
    double distance_mm {};
    double width_theta_mm {};
    double width_phi_mm {};
};

struct ScatterPoint {
    double theta_lab_rad {};
    double phi_lab_rad {};
    double kinetic_energy_mev {};
};

struct ScatteringSolution {
    ScatterPoint deuteron;
    ScatterPoint proton;
};

struct CmBranchWindow {
    double begin_rad {};
    double end_rad {};
    double delta_phi_rad {};

    [[nodiscard]] bool valid() const noexcept {
        return end_rad > begin_rad && delta_phi_rad > 0.0;
    }

    [[nodiscard]] double width_rad() const noexcept {
        return valid() ? (end_rad - begin_rad) : 0.0;
    }
};

struct BranchPair {
    CmBranchWindow forward;
    CmBranchWindow backward;
};

enum class CoverageParticle {
    Deuteron,
    Proton
};

struct AcceptanceCoverage {
    std::string label;
    CoverageParticle particle {CoverageParticle::Deuteron};
    int theta_bins {};
    int phi_bins {};
    double theta_grid_min_rad {};
    double theta_grid_max_rad {std::numbers::pi_v<double>};
    double phi_grid_min_rad {};
    double phi_grid_max_rad {2.0 * std::numbers::pi_v<double>};
    double lab_phi_center_rad {};
    double accepted_solid_angle_sr {};
    double theta_cm_min_rad {std::numbers::pi_v<double>};
    double theta_cm_max_rad {};
    double phi_cm_min_rad {2.0 * std::numbers::pi_v<double>};
    double phi_cm_max_rad {};
    int accepted_cells {};
    std::vector<double> accepted_map;

    [[nodiscard]] bool hasAcceptance() const noexcept {
        return accepted_cells > 0;
    }
};

struct SamplePoint {
    double x {};
    double y {};
    double error {};
};

struct UncertaintyBreakdown {
    double value {};
    double stat_sigma {};
    double tensor_sigma {};
    double total_sigma {};
};

struct RatioScanPoint {
    double polarization {};
    UncertaintyBreakdown first_count;
    UncertaintyBreakdown second_count;
    UncertaintyBreakdown ratio;
    double tensor_covariance {};
};

struct LrudScanPoint {
    double polarization {};
    UncertaintyBreakdown left_right_count;
    UncertaintyBreakdown up_down_count;
    UncertaintyBreakdown asymmetry;
    double stat_covariance {};
    double tensor_covariance {};
};

struct CoincidenceResult {
    CmBranchWindow forward_overlap;
    CmBranchWindow backward_overlap;
    double coincidence_counts {};
    double proton_single_counts {};
    double deuteron_single_counts {};
};

struct SummaryEntry {
    std::string key;
    std::string value;
};

}  // namespace dpolar
