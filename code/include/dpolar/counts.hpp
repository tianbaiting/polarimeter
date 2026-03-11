#pragma once

#include "dpolar/config.hpp"
#include "dpolar/observables.hpp"
#include "dpolar/types.hpp"

namespace dpolar {

class CountRateCalculator {
public:
    CountRateCalculator(const ScenarioConfig& scenario, const ObservableTableRepository& observables);

    [[nodiscard]] double integralForPzz(const CmBranchWindow& window, double pzz) const;
    [[nodiscard]] double integralForLr(const CmBranchWindow& window, double pyy) const;
    [[nodiscard]] double integralForUd(const CmBranchWindow& window, double pyy) const;
    [[nodiscard]] double countsFromIntegratedCrossSection(double integrated_cross_section_m2_sr) const;
    [[nodiscard]] double beamParticleCount() const noexcept;
    [[nodiscard]] double countVarianceFromTensorForPzz(const CmBranchWindow& window, double pzz) const;
    [[nodiscard]] double countCovarianceFromTensorForPzz(
        const CmBranchWindow& first_window,
        const CmBranchWindow& second_window,
        double pzz) const;
    [[nodiscard]] double countVarianceFromTensorForLr(const CmBranchWindow& window, double pyy) const;
    [[nodiscard]] double countVarianceFromTensorForUd(const CmBranchWindow& window, double pyy) const;
    [[nodiscard]] double countCovarianceFromTensorForLrUd(const CmBranchWindow& window, double pyy) const;

    [[nodiscard]] const RunConfig& run() const noexcept;

private:
    const ObservableTableRepository& observables_;
    TargetConfig target_;
    RunConfig run_;
};

}  // namespace dpolar
