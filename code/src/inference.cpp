#include "dpolar/inference.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <utility>

namespace dpolar {
namespace {

constexpr int kSearchSteps = 2048;
constexpr int kSearchLevels = 6;
constexpr int kBisectionIterations = 80;
constexpr int kProfilePointCount = 401;

struct ProfileExpectedValues {
    double first_count {std::numeric_limits<double>::quiet_NaN()};
    double second_count {std::numeric_limits<double>::quiet_NaN()};
    double total_count {std::numeric_limits<double>::quiet_NaN()};
    double ratio_or_asymmetry {std::numeric_limits<double>::quiet_NaN()};
};

void requireNonNegativeCount(const char* label, const double value) {
    if (!std::isfinite(value) || value < 0.0) {
        throw std::runtime_error(std::string(label) + " must be a finite non-negative count");
    }
}

double poissonLogLikelihood(const double observed_count, const double expected_count) {
    if (!(expected_count > 0.0) || !std::isfinite(expected_count)) {
        return -std::numeric_limits<double>::infinity();
    }
    if (observed_count == 0.0) {
        return -expected_count;
    }
    return observed_count * std::log(expected_count) - expected_count;
}

double binomialLogLikelihood(
    const double observed_successes,
    const double observed_total,
    const double success_probability) {
    if (!(observed_total > 0.0)) {
        throw std::runtime_error("Binomial inference requires a strictly positive total count");
    }
    if (!(success_probability > 0.0) || !(success_probability < 1.0) || !std::isfinite(success_probability)) {
        return -std::numeric_limits<double>::infinity();
    }
    const double observed_failures = observed_total - observed_successes;
    if (observed_failures < 0.0) {
        throw std::runtime_error("Successful counts cannot exceed the total count");
    }
    // [EN] Use the conditional binomial likelihood so paired-arm inference depends on the count split rather than absolute normalization / [CN] 使用条件二项似然，使双臂反推只依赖计数分配而非绝对归一化
    return observed_successes * std::log(success_probability) +
           observed_failures * std::log1p(-success_probability);
}

double maximizeLogLikelihood(
    const double lower_bound,
    const double upper_bound,
    const auto& log_likelihood) {
    if (!(upper_bound > lower_bound)) {
        return lower_bound;
    }

    double left = lower_bound;
    double right = upper_bound;
    double best_parameter = lower_bound;
    double best_value = log_likelihood(lower_bound);

    for (int level = 0; level < kSearchLevels; ++level) {
        const double step = (right - left) / static_cast<double>(kSearchSteps);
        for (int index = 0; index <= kSearchSteps; ++index) {
            const double parameter = left + static_cast<double>(index) * step;
            const double value = log_likelihood(parameter);
            if (value > best_value) {
                best_value = value;
                best_parameter = parameter;
            }
        }

        const double window = std::max(step * 2.0, (upper_bound - lower_bound) * 1.0e-8);
        left = std::max(lower_bound, best_parameter - window);
        right = std::min(upper_bound, best_parameter + window);
    }

    return best_parameter;
}

double solveThresholdIncreasing(
    const double lower_bound,
    const double upper_bound,
    const double target_value,
    const auto& function) {
    double left = lower_bound;
    double right = upper_bound;
    for (int iteration = 0; iteration < kBisectionIterations; ++iteration) {
        const double middle = 0.5 * (left + right);
        if (function(middle) >= target_value) {
            right = middle;
        } else {
            left = middle;
        }
    }
    return 0.5 * (left + right);
}

double solveThresholdDecreasing(
    const double lower_bound,
    const double upper_bound,
    const double target_value,
    const auto& function) {
    double left = lower_bound;
    double right = upper_bound;
    for (int iteration = 0; iteration < kBisectionIterations; ++iteration) {
        const double middle = 0.5 * (left + right);
        if (function(middle) >= target_value) {
            left = middle;
        } else {
            right = middle;
        }
    }
    return 0.5 * (left + right);
}

PolarizationInterval makeProfileInterval(
    const double lower_bound,
    const double upper_bound,
    const double estimate,
    const double loglikelihood_max,
    const double delta_chi_square,
    const auto& log_likelihood) {
    const double target_value = loglikelihood_max - 0.5 * delta_chi_square;
    const double left_value = log_likelihood(lower_bound);
    const double right_value = log_likelihood(upper_bound);

    double interval_low = lower_bound;
    if (estimate > lower_bound && left_value < target_value) {
        interval_low = solveThresholdIncreasing(lower_bound, estimate, target_value, log_likelihood);
    }

    double interval_high = upper_bound;
    if (estimate < upper_bound && right_value < target_value) {
        interval_high = solveThresholdDecreasing(estimate, upper_bound, target_value, log_likelihood);
    }

    return PolarizationInterval {interval_low, interval_high};
}

double estimateSigmaFromCurvature(
    const double lower_bound,
    const double upper_bound,
    const double estimate,
    const double loglikelihood_max,
    const PolarizationInterval& ci68,
    const auto& log_likelihood) {
    const double local_span = std::min(estimate - lower_bound, upper_bound - estimate);
    if (local_span > 0.0) {
        const double step = std::max(local_span * 1.0e-3, (upper_bound - lower_bound) * 1.0e-7);
        if (estimate - step >= lower_bound && estimate + step <= upper_bound) {
            const double curvature =
                (log_likelihood(estimate + step) - 2.0 * loglikelihood_max + log_likelihood(estimate - step)) /
                (step * step);
            if (curvature < 0.0 && std::isfinite(curvature)) {
                return std::sqrt(-1.0 / curvature);
            }
        }
    }

    const double left_sigma = estimate - ci68.low;
    const double right_sigma = ci68.high - estimate;
    return 0.5 * (left_sigma + right_sigma);
}

PolarizationEstimate inferFromLogLikelihood(
    const double lower_bound,
    const double upper_bound,
    const auto& log_likelihood,
    const double initial_estimate) {
    const double clamped_initial = std::clamp(initial_estimate, lower_bound, upper_bound);
    const double estimate = maximizeLogLikelihood(lower_bound, upper_bound, log_likelihood);
    const double loglikelihood_max = log_likelihood(estimate);
    if (!std::isfinite(loglikelihood_max)) {
        throw std::runtime_error("Likelihood is not finite anywhere inside the configured polarization scan range");
    }
    const PolarizationInterval ci68 = makeProfileInterval(
        lower_bound,
        upper_bound,
        estimate,
        loglikelihood_max,
        1.0,
        log_likelihood);
    const PolarizationInterval ci95 = makeProfileInterval(
        lower_bound,
        upper_bound,
        estimate,
        loglikelihood_max,
        3.841458820694124,
        log_likelihood);
    const double boundary_tolerance = std::max((upper_bound - lower_bound) * 1.0e-6, 1.0e-9);

    PolarizationEstimate result;
    result.estimate = std::isfinite(estimate) ? estimate : clamped_initial;
    result.sigma_mle = estimateSigmaFromCurvature(
        lower_bound,
        upper_bound,
        result.estimate,
        loglikelihood_max,
        ci68,
        log_likelihood);
    result.ci68 = ci68;
    result.ci95 = ci95;
    result.at_lower_bound = std::abs(result.estimate - lower_bound) <= boundary_tolerance;
    result.at_upper_bound = std::abs(result.estimate - upper_bound) <= boundary_tolerance;
    result.loglikelihood_max = loglikelihood_max;
    return result;
}

double invertLinearCount(
    const double observed_count,
    const double intercept,
    const double slope,
    const double fallback_value) {
    if (std::abs(slope) <= 1.0e-12) {
        return fallback_value;
    }
    return (observed_count - intercept) / slope;
}

double invertPairProbability(
    const double observed_first,
    const double observed_second,
    const auto& first,
    const auto& second,
    const double fallback_value) {
    const double observed_total = observed_first + observed_second;
    if (!(observed_total > 0.0)) {
        return fallback_value;
    }
    const double observed_probability = observed_first / observed_total;
    const double intercept_sum = first.intercept + second.intercept;
    const double slope_sum = first.slope + second.slope;
    const double denominator = first.slope - observed_probability * slope_sum;
    if (std::abs(denominator) <= 1.0e-12) {
        return fallback_value;
    }
    return (observed_probability * intercept_sum - first.intercept) / denominator;
}

double responseValue(const auto& response, const double polarization) {
    return response.intercept + response.slope * polarization;
}

double safeRatio(const double numerator, const double denominator) {
    return denominator == 0.0 ? std::numeric_limits<double>::quiet_NaN() : numerator / denominator;
}

double safeAsymmetry(const double first, const double second) {
    const double sum = first + second;
    return sum == 0.0 ? std::numeric_limits<double>::quiet_NaN() : (first - second) / sum;
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

PolarizationProfile buildProfile(
    const double lower_bound,
    const double upper_bound,
    const double initial_estimate,
    std::string estimator,
    std::string observable_label,
    const auto& log_likelihood,
    const auto& expected_values) {
    PolarizationProfile profile;
    profile.estimate = inferFromLogLikelihood(lower_bound, upper_bound, log_likelihood, initial_estimate);
    profile.estimator = std::move(estimator);
    profile.observable_label = std::move(observable_label);

    const int point_count = upper_bound > lower_bound ? kProfilePointCount : 1;
    profile.points.reserve(static_cast<std::size_t>(point_count));
    for (int index = 0; index < point_count; ++index) {
        const double fraction = point_count == 1
                                    ? 0.0
                                    : static_cast<double>(index) / static_cast<double>(point_count - 1);
        const double polarization = lower_bound + (upper_bound - lower_bound) * fraction;
        const double log_likelihood_value = log_likelihood(polarization);
        const ProfileExpectedValues expected = expected_values(polarization);

        PolarizationProfilePoint point;
        point.polarization = polarization;
        point.minus_two_delta_loglikelihood =
            std::isfinite(log_likelihood_value)
                ? std::max(0.0, -2.0 * (log_likelihood_value - profile.estimate.loglikelihood_max))
                : std::numeric_limits<double>::infinity();
        point.expected_first_count = expected.first_count;
        point.expected_second_count = expected.second_count;
        point.expected_total_count = expected.total_count;
        point.expected_ratio_or_asymmetry = expected.ratio_or_asymmetry;
        profile.points.push_back(point);
    }

    return profile;
}

}  // namespace

PolarizationInference::PolarizationInference(ScenarioConfig scenario)
    : scenario_(std::move(scenario))
    , kinematics_(scenario_.beam)
    , observables_(scenario_)
    , counts_(scenario_, observables_) {
}

const ScenarioConfig& PolarizationInference::scenario() const noexcept {
    return scenario_;
}

PolarizationInference::LinearResponse PolarizationInference::pzzResponseForWindow(
    const CmBranchWindow& window,
    const double sector_scale) const {
    const double count_at_zero =
        counts_.countsFromIntegratedCrossSection(counts_.integralForPzz(window, 0.0)) * sector_scale;
    const double count_at_one =
        counts_.countsFromIntegratedCrossSection(counts_.integralForPzz(window, 1.0)) * sector_scale;
    return LinearResponse {
        count_at_zero,
        count_at_one - count_at_zero,
    };
}

PolarizationInference::LinearResponse PolarizationInference::pyyLrResponse(const LrudObservable observable) const {
    const CmBranchWindow proton_window = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[0]);
    const CmBranchWindow window = observable == LrudObservable::Coincidence
                                      ? intersectWindows(
                                            proton_window,
                                            deuteronWindowsFromArm(kinematics_, scenario_.custom_layout.deuteron_arm).forward)
                                      : proton_window;
    const double sector_scale = scenario_.run.lrud_sector_multiplier;
    const double count_at_zero =
        counts_.countsFromIntegratedCrossSection(counts_.integralForLr(window, 0.0)) * sector_scale;
    const double count_at_one =
        counts_.countsFromIntegratedCrossSection(counts_.integralForLr(window, 1.0)) * sector_scale;
    return LinearResponse {
        count_at_zero,
        count_at_one - count_at_zero,
    };
}

PolarizationInference::LinearResponse PolarizationInference::pyyUdResponse(const LrudObservable observable) const {
    const CmBranchWindow proton_window = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[0]);
    const CmBranchWindow window = observable == LrudObservable::Coincidence
                                      ? intersectWindows(
                                            proton_window,
                                            deuteronWindowsFromArm(kinematics_, scenario_.custom_layout.deuteron_arm).forward)
                                      : proton_window;
    const double sector_scale = scenario_.run.lrud_sector_multiplier;
    const double count_at_zero =
        counts_.countsFromIntegratedCrossSection(counts_.integralForUd(window, 0.0)) * sector_scale;
    const double count_at_one =
        counts_.countsFromIntegratedCrossSection(counts_.integralForUd(window, 1.0)) * sector_scale;
    return LinearResponse {
        count_at_zero,
        count_at_one - count_at_zero,
    };
}

PolarizationInference::PairedResponse PolarizationInference::pzzPairResponse(const PzzObservable observable) const {
    if (observable == PzzObservable::Proton) {
        return PairedResponse {
            pzzResponseForWindow(
                protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[0]),
                scenario_.run.single_arm_sector_multiplier),
            pzzResponseForWindow(
                protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[1]),
                scenario_.run.single_arm_sector_multiplier),
        };
    }

    if (observable == PzzObservable::Deuteron) {
        const BranchPair windows = deuteronWindowsFromArm(kinematics_, scenario_.custom_layout.deuteron_arm);
        return PairedResponse {
            pzzResponseForWindow(windows.forward, scenario_.run.single_arm_sector_multiplier),
            pzzResponseForWindow(windows.backward, scenario_.run.single_arm_sector_multiplier),
        };
    }

    const BranchPair deuteron_windows = deuteronWindowsFromArm(kinematics_, scenario_.custom_layout.deuteron_arm);
    const CmBranchWindow proton_forward = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[0]);
    const CmBranchWindow proton_backward = protonWindowFromArm(kinematics_, scenario_.custom_layout.proton_arms[1]);
    return PairedResponse {
        pzzResponseForWindow(
            intersectWindows(proton_forward, deuteron_windows.forward),
            scenario_.run.coincidence_sector_multiplier),
        pzzResponseForWindow(
            intersectWindows(proton_backward, deuteron_windows.backward),
            scenario_.run.coincidence_sector_multiplier),
    };
}

PolarizationEstimate PolarizationInference::inferPzzFromCounts(
    const PzzObservable observable,
    const double first_count,
    const double second_count) const {
    requireNonNegativeCount("first_count", first_count);
    requireNonNegativeCount("second_count", second_count);

    const PairedResponse response = pzzPairResponse(observable);
    const double lower_bound = scenario_.scan.polarization_min;
    const double upper_bound = scenario_.scan.polarization_max;
    const double initial_estimate = invertPairProbability(
        first_count,
        second_count,
        response.first,
        response.second,
        0.5 * (lower_bound + upper_bound));

    const double total_count = first_count + second_count;
    if (!(total_count > 0.0)) {
        throw std::runtime_error("Paired pzz inference requires first_count + second_count > 0");
    }

    const auto log_likelihood = [&](const double polarization) {
        const double expected_first = responseValue(response.first, polarization);
        const double expected_second = responseValue(response.second, polarization);
        const double expected_total = expected_first + expected_second;
        if (!(expected_first > 0.0) || !(expected_second > 0.0) || !(expected_total > 0.0)) {
            return -std::numeric_limits<double>::infinity();
        }
        return binomialLogLikelihood(first_count, total_count, expected_first / expected_total);
    };

    return inferFromLogLikelihood(lower_bound, upper_bound, log_likelihood, initial_estimate);
}

PolarizationEstimate PolarizationInference::inferPzzFromTotalCount(
    const PzzObservable observable,
    const double total_count) const {
    requireNonNegativeCount("total_count", total_count);

    const PairedResponse response = pzzPairResponse(observable);
    const LinearResponse total_response {
        response.first.intercept + response.second.intercept,
        response.first.slope + response.second.slope,
    };
    const double lower_bound = scenario_.scan.polarization_min;
    const double upper_bound = scenario_.scan.polarization_max;
    const double initial_estimate = invertLinearCount(
        total_count,
        total_response.intercept,
        total_response.slope,
        0.5 * (lower_bound + upper_bound));

    const auto log_likelihood = [&](const double polarization) {
        return poissonLogLikelihood(total_count, responseValue(total_response, polarization));
    };

    return inferFromLogLikelihood(lower_bound, upper_bound, log_likelihood, initial_estimate);
}

PolarizationEstimate PolarizationInference::inferPyyFromLrudCounts(
    const double left_right_count,
    const double up_down_count) const {
    return inferPyyFromLrudCounts(LrudObservable::Proton, left_right_count, up_down_count);
}

PolarizationEstimate PolarizationInference::inferPyyFromLrudCounts(
    const LrudObservable observable,
    const double left_right_count,
    const double up_down_count) const {
    requireNonNegativeCount("left_right_count", left_right_count);
    requireNonNegativeCount("up_down_count", up_down_count);

    const LinearResponse left_right_response = pyyLrResponse(observable);
    const LinearResponse up_down_response = pyyUdResponse(observable);
    const double total_count = left_right_count + up_down_count;
    if (!(total_count > 0.0)) {
        throw std::runtime_error("LR/UD inference requires left_right_count + up_down_count > 0");
    }

    const double lower_bound = scenario_.scan.polarization_min;
    const double upper_bound = scenario_.scan.polarization_max;
    const double initial_estimate = invertPairProbability(
        left_right_count,
        up_down_count,
        left_right_response,
        up_down_response,
        0.5 * (lower_bound + upper_bound));

    const auto log_likelihood = [&](const double polarization) {
        const double expected_left_right = responseValue(left_right_response, polarization);
        const double expected_up_down = responseValue(up_down_response, polarization);
        const double expected_total = expected_left_right + expected_up_down;
        if (!(expected_left_right > 0.0) || !(expected_up_down > 0.0) || !(expected_total > 0.0)) {
            return -std::numeric_limits<double>::infinity();
        }
        return binomialLogLikelihood(left_right_count, total_count, expected_left_right / expected_total);
    };

    return inferFromLogLikelihood(lower_bound, upper_bound, log_likelihood, initial_estimate);
}

PolarizationProfile PolarizationInference::buildPzzProfile(
    const PzzObservable observable,
    const double count,
    const std::optional<double>& count2) const {
    requireNonNegativeCount("count", count);
    const PairedResponse response = pzzPairResponse(observable);
    const double lower_bound = scenario_.scan.polarization_min;
    const double upper_bound = scenario_.scan.polarization_max;
    const std::string observable_label = pzzObservableLabel(observable);

    if (count2.has_value()) {
        requireNonNegativeCount("count2", *count2);
        const double total_count = count + *count2;
        if (!(total_count > 0.0)) {
            throw std::runtime_error("Paired pzz inference requires count + count2 > 0");
        }

        const double initial_estimate = invertPairProbability(
            count,
            *count2,
            response.first,
            response.second,
            0.5 * (lower_bound + upper_bound));
        const auto log_likelihood = [&](const double polarization) {
            const double expected_first = responseValue(response.first, polarization);
            const double expected_second = responseValue(response.second, polarization);
            const double expected_total = expected_first + expected_second;
            if (!(expected_first > 0.0) || !(expected_second > 0.0) || !(expected_total > 0.0)) {
                return -std::numeric_limits<double>::infinity();
            }
            return binomialLogLikelihood(count, total_count, expected_first / expected_total);
        };
        const auto expected_values = [&](const double polarization) {
            const double expected_first = responseValue(response.first, polarization);
            const double expected_second = responseValue(response.second, polarization);
            return ProfileExpectedValues {
                expected_first,
                expected_second,
                expected_first + expected_second,
                safeRatio(expected_first, expected_second),
            };
        };
        return buildProfile(
            lower_bound,
            upper_bound,
            initial_estimate,
            "pair_binomial",
            observable_label,
            log_likelihood,
            expected_values);
    }

    const LinearResponse total_response {
        response.first.intercept + response.second.intercept,
        response.first.slope + response.second.slope,
    };
    const double initial_estimate = invertLinearCount(
        count,
        total_response.intercept,
        total_response.slope,
        0.5 * (lower_bound + upper_bound));
    const auto log_likelihood = [&](const double polarization) {
        return poissonLogLikelihood(count, responseValue(total_response, polarization));
    };
    const auto expected_values = [&](const double polarization) {
        const double expected_first = responseValue(response.first, polarization);
        const double expected_second = responseValue(response.second, polarization);
        return ProfileExpectedValues {
            expected_first,
            expected_second,
            expected_first + expected_second,
            safeRatio(expected_first, expected_second),
        };
    };
    return buildProfile(
        lower_bound,
        upper_bound,
        initial_estimate,
        "absolute_poisson",
        observable_label,
        log_likelihood,
        expected_values);
}

PolarizationProfile PolarizationInference::buildPyyProfile(
    const double left_right_count,
    const double up_down_count) const {
    return buildPyyProfile(LrudObservable::Proton, left_right_count, up_down_count);
}

PolarizationProfile PolarizationInference::buildPyyProfile(
    const LrudObservable observable,
    const double left_right_count,
    const double up_down_count) const {
    requireNonNegativeCount("left_right_count", left_right_count);
    requireNonNegativeCount("up_down_count", up_down_count);

    const LinearResponse left_right_response = pyyLrResponse(observable);
    const LinearResponse up_down_response = pyyUdResponse(observable);
    const double total_count = left_right_count + up_down_count;
    if (!(total_count > 0.0)) {
        throw std::runtime_error("LR/UD inference requires left_right_count + up_down_count > 0");
    }

    const double lower_bound = scenario_.scan.polarization_min;
    const double upper_bound = scenario_.scan.polarization_max;
    const double initial_estimate = invertPairProbability(
        left_right_count,
        up_down_count,
        left_right_response,
        up_down_response,
        0.5 * (lower_bound + upper_bound));
    const auto log_likelihood = [&](const double polarization) {
        const double expected_left_right = responseValue(left_right_response, polarization);
        const double expected_up_down = responseValue(up_down_response, polarization);
        const double expected_total = expected_left_right + expected_up_down;
        if (!(expected_left_right > 0.0) || !(expected_up_down > 0.0) || !(expected_total > 0.0)) {
            return -std::numeric_limits<double>::infinity();
        }
        return binomialLogLikelihood(left_right_count, total_count, expected_left_right / expected_total);
    };
    const auto expected_values = [&](const double polarization) {
        const double expected_left_right = responseValue(left_right_response, polarization);
        const double expected_up_down = responseValue(up_down_response, polarization);
        return ProfileExpectedValues {
            expected_left_right,
            expected_up_down,
            expected_left_right + expected_up_down,
            safeAsymmetry(expected_left_right, expected_up_down),
        };
    };
    return buildProfile(
        lower_bound,
        upper_bound,
        initial_estimate,
        "pair_binomial",
        std::string("lrud_") + lrudObservableLabel(observable),
        log_likelihood,
        expected_values);
}

}  // namespace dpolar
