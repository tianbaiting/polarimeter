#pragma once

#include "dpolar/acceptance.hpp"
#include "dpolar/config.hpp"
#include "dpolar/counts.hpp"
#include "dpolar/observables.hpp"

#include <limits>
#include <optional>
#include <string>
#include <vector>

namespace dpolar {

enum class PzzObservable {
    Proton,
    Deuteron,
    Coincidence
};

enum class LrudObservable {
    Proton,
    Coincidence
};

struct PolarizationInterval {
    double low {};
    double high {};
};

struct PolarizationEstimate {
    double estimate {};
    double sigma_mle {};
    PolarizationInterval ci68;
    PolarizationInterval ci95;
    bool at_lower_bound {};
    bool at_upper_bound {};
    double loglikelihood_max {};
};

struct PolarizationProfilePoint {
    double polarization {};
    double minus_two_delta_loglikelihood {};
    double expected_first_count {std::numeric_limits<double>::quiet_NaN()};
    double expected_second_count {std::numeric_limits<double>::quiet_NaN()};
    double expected_total_count {std::numeric_limits<double>::quiet_NaN()};
    double expected_ratio_or_asymmetry {std::numeric_limits<double>::quiet_NaN()};
};

struct PolarizationProfile {
    PolarizationEstimate estimate;
    std::vector<PolarizationProfilePoint> points;
    std::string estimator;
    std::string observable_label;
};

class PolarizationInference {
public:
    explicit PolarizationInference(ScenarioConfig scenario);

    [[nodiscard]] const ScenarioConfig& scenario() const noexcept;

    [[nodiscard]] PolarizationEstimate inferPzzFromCounts(
        PzzObservable observable,
        double first_count,
        double second_count) const;
    [[nodiscard]] PolarizationEstimate inferPzzFromTotalCount(
        PzzObservable observable,
        double total_count) const;
    [[nodiscard]] PolarizationEstimate inferPyyFromLrudCounts(
        double left_right_count,
        double up_down_count) const;
    [[nodiscard]] PolarizationEstimate inferPyyFromLrudCounts(
        LrudObservable observable,
        double left_right_count,
        double up_down_count) const;
    [[nodiscard]] PolarizationProfile buildPzzProfile(
        PzzObservable observable,
        double count,
        const std::optional<double>& count2 = std::nullopt) const;
    [[nodiscard]] PolarizationProfile buildPyyProfile(
        double left_right_count,
        double up_down_count) const;
    [[nodiscard]] PolarizationProfile buildPyyProfile(
        LrudObservable observable,
        double left_right_count,
        double up_down_count) const;

private:
    struct LinearResponse {
        double intercept {};
        double slope {};
    };

    struct PairedResponse {
        LinearResponse first;
        LinearResponse second;
    };

    [[nodiscard]] LinearResponse pzzResponseForWindow(const CmBranchWindow& window, double sector_scale) const;
    [[nodiscard]] LinearResponse pyyLrResponse(LrudObservable observable) const;
    [[nodiscard]] LinearResponse pyyUdResponse(LrudObservable observable) const;
    [[nodiscard]] PairedResponse pzzPairResponse(PzzObservable observable) const;

    ScenarioConfig scenario_;
    ElasticDpKinematics kinematics_;
    ObservableTableRepository observables_;
    CountRateCalculator counts_;
};

}  // namespace dpolar
