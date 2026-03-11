#include "dpolar/counts.hpp"

#include <cmath>

namespace dpolar {
namespace {

struct TensorCoefficients {
    double t20 {};
    double t22 {};
};

template <typename Integrand>
double integrateWindow(
    const CmBranchWindow& window,
    const int steps,
    Integrand&& integrand) {
    if (!window.valid()) {
        return 0.0;
    }
    const double delta_theta = (window.end_rad - window.begin_rad) / static_cast<double>(steps);
    double integral = 0.0;
    for (int step = 0; step < steps; ++step) {
        const double theta_rad = window.begin_rad + (static_cast<double>(step) + 0.5) * delta_theta;
        integral += integrand(theta_rad) * delta_theta;
    }
    return integral * window.delta_phi_rad * kMillibarnToSquareMeter;
}

template <typename CoefficientProvider>
double tensorVarianceForWindow(
    const CmBranchWindow& window,
    const int steps,
    const double count_scale,
    const ObservableTableRepository& observables,
    CoefficientProvider&& coefficients) {
    if (!window.valid()) {
        return 0.0;
    }
    const double delta_theta = (window.end_rad - window.begin_rad) / static_cast<double>(steps);
    double variance = 0.0;
    for (int step = 0; step < steps; ++step) {
        const double theta_rad = window.begin_rad + (static_cast<double>(step) + 0.5) * delta_theta;
        const double theta_deg = toDegrees(theta_rad);
        const TensorCoefficients factors = coefficients(theta_deg);
        const double derivative_scale =
            count_scale * observables.differentialCrossSectionMbPerSr(theta_deg) *
            delta_theta * window.delta_phi_rad * kMillibarnToSquareMeter;
        const double derivative_t20 = derivative_scale * factors.t20;
        const double derivative_t22 = derivative_scale * factors.t22;
        variance += derivative_t20 * derivative_t20 * std::pow(observables.tensorT20Error(theta_deg), 2.0);
        variance += derivative_t22 * derivative_t22 * std::pow(observables.tensorT22Error(theta_deg), 2.0);
    }
    return variance;
}

template <typename CoefficientProvider>
double tensorCovarianceForWindows(
    const CmBranchWindow& first_window,
    const CmBranchWindow& second_window,
    const int steps,
    const double count_scale,
    const ObservableTableRepository& observables,
    CoefficientProvider&& coefficients) {
    const double begin = std::max(first_window.begin_rad, second_window.begin_rad);
    const double end = std::min(first_window.end_rad, second_window.end_rad);
    if (end <= begin || first_window.delta_phi_rad <= 0.0 || second_window.delta_phi_rad <= 0.0) {
        return 0.0;
    }

    const double delta_theta = (end - begin) / static_cast<double>(steps);
    double covariance = 0.0;
    for (int step = 0; step < steps; ++step) {
        const double theta_rad = begin + (static_cast<double>(step) + 0.5) * delta_theta;
        const double theta_deg = toDegrees(theta_rad);
        const auto [first_coefficients, second_coefficients] = coefficients(theta_deg);
        const double common_scale =
            count_scale * observables.differentialCrossSectionMbPerSr(theta_deg) *
            delta_theta * kMillibarnToSquareMeter;
        const double first_t20 = common_scale * first_window.delta_phi_rad * first_coefficients.t20;
        const double first_t22 = common_scale * first_window.delta_phi_rad * first_coefficients.t22;
        const double second_t20 = common_scale * second_window.delta_phi_rad * second_coefficients.t20;
        const double second_t22 = common_scale * second_window.delta_phi_rad * second_coefficients.t22;
        covariance += first_t20 * second_t20 * std::pow(observables.tensorT20Error(theta_deg), 2.0);
        covariance += first_t22 * second_t22 * std::pow(observables.tensorT22Error(theta_deg), 2.0);
    }
    return covariance;
}

}  // namespace

CountRateCalculator::CountRateCalculator(const ScenarioConfig& scenario, const ObservableTableRepository& observables)
    : observables_(observables)
    , target_(scenario.target)
    , run_(scenario.run) {
}

double CountRateCalculator::integralForPzz(const CmBranchWindow& window, const double pzz) const {
    return integrateWindow(window, run_.integration_steps, [&](const double theta_rad) {
        const double theta_deg = toDegrees(theta_rad);
        return observables_.differentialCrossSectionMbPerSr(theta_deg) *
               (1.0 + 0.5 * std::sqrt(2.0) * observables_.tensorT20(theta_deg) * pzz);
    });
}

double CountRateCalculator::integralForLr(const CmBranchWindow& window, const double pyy) const {
    return integrateWindow(window, run_.integration_steps, [&](const double theta_rad) {
        const double theta_deg = toDegrees(theta_rad);
        return observables_.differentialCrossSectionMbPerSr(theta_deg) *
               (1.0
                - 0.25 * pyy * 2.0 * std::sqrt(3.0) * observables_.tensorT22(theta_deg)
                - 0.25 * pyy * std::sqrt(2.0) * observables_.tensorT20(theta_deg));
    });
}

double CountRateCalculator::integralForUd(const CmBranchWindow& window, const double pyy) const {
    return integrateWindow(window, run_.integration_steps, [&](const double theta_rad) {
        const double theta_deg = toDegrees(theta_rad);
        return observables_.differentialCrossSectionMbPerSr(theta_deg) *
               (1.0
                + 0.25 * pyy * 2.0 * std::sqrt(3.0) * observables_.tensorT22(theta_deg)
                - 0.25 * pyy * std::sqrt(2.0) * observables_.tensorT20(theta_deg));
    });
}

double CountRateCalculator::countsFromIntegratedCrossSection(const double integrated_cross_section_m2_sr) const {
    // [EN] Convert integrated cross section into expected beam-time counts using the CH2 areal density model / [CN] 使用 CH2 面密度模型把积分截面换算成束流时间内的期望计数
    return target_.areal_density_g_per_m2 / target_.molar_mass_g_per_mol *
           target_.avogadro * 2.0 * integrated_cross_section_m2_sr *
           run_.beam_current_amp / run_.electron_charge_c * run_.duration_s;
}

double CountRateCalculator::beamParticleCount() const noexcept {
    return run_.beam_current_amp / run_.electron_charge_c * run_.duration_s;
}

double CountRateCalculator::countVarianceFromTensorForPzz(const CmBranchWindow& window, const double pzz) const {
    const double coefficient_t20 = 0.5 * std::sqrt(2.0) * pzz;
    const double count_scale = target_.areal_density_g_per_m2 / target_.molar_mass_g_per_mol *
                               target_.avogadro * 2.0 * run_.beam_current_amp / run_.electron_charge_c * run_.duration_s;
    return tensorVarianceForWindow(window, run_.integration_steps, count_scale, observables_, [&](const double) {
        return TensorCoefficients {coefficient_t20, 0.0};
    });
}

double CountRateCalculator::countCovarianceFromTensorForPzz(
    const CmBranchWindow& first_window,
    const CmBranchWindow& second_window,
    const double pzz) const {
    const double coefficient_t20 = 0.5 * std::sqrt(2.0) * pzz;
    const double count_scale = target_.areal_density_g_per_m2 / target_.molar_mass_g_per_mol *
                               target_.avogadro * 2.0 * run_.beam_current_amp / run_.electron_charge_c * run_.duration_s;
    return tensorCovarianceForWindows(
        first_window,
        second_window,
        run_.integration_steps,
        count_scale,
        observables_,
        [&](const double) {
            return std::pair {TensorCoefficients {coefficient_t20, 0.0}, TensorCoefficients {coefficient_t20, 0.0}};
        });
}

double CountRateCalculator::countVarianceFromTensorForLr(const CmBranchWindow& window, const double pyy) const {
    const double count_scale = target_.areal_density_g_per_m2 / target_.molar_mass_g_per_mol *
                               target_.avogadro * 2.0 * run_.beam_current_amp / run_.electron_charge_c * run_.duration_s;
    return tensorVarianceForWindow(window, run_.integration_steps, count_scale, observables_, [&](const double) {
        return TensorCoefficients {-0.25 * std::sqrt(2.0) * pyy, -0.5 * std::sqrt(3.0) * pyy};
    });
}

double CountRateCalculator::countVarianceFromTensorForUd(const CmBranchWindow& window, const double pyy) const {
    const double count_scale = target_.areal_density_g_per_m2 / target_.molar_mass_g_per_mol *
                               target_.avogadro * 2.0 * run_.beam_current_amp / run_.electron_charge_c * run_.duration_s;
    return tensorVarianceForWindow(window, run_.integration_steps, count_scale, observables_, [&](const double) {
        return TensorCoefficients {-0.25 * std::sqrt(2.0) * pyy, 0.5 * std::sqrt(3.0) * pyy};
    });
}

double CountRateCalculator::countCovarianceFromTensorForLrUd(const CmBranchWindow& window, const double pyy) const {
    const double count_scale = target_.areal_density_g_per_m2 / target_.molar_mass_g_per_mol *
                               target_.avogadro * 2.0 * run_.beam_current_amp / run_.electron_charge_c * run_.duration_s;
    return tensorCovarianceForWindows(
        window,
        window,
        run_.integration_steps,
        count_scale,
        observables_,
        [&](const double) {
            return std::pair {
                TensorCoefficients {-0.25 * std::sqrt(2.0) * pyy, -0.5 * std::sqrt(3.0) * pyy},
                TensorCoefficients {-0.25 * std::sqrt(2.0) * pyy, 0.5 * std::sqrt(3.0) * pyy}};
        });
}

const RunConfig& CountRateCalculator::run() const noexcept {
    return run_;
}

}  // namespace dpolar
