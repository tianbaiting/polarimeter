#pragma once

#include "dpolar/config.hpp"
#include "dpolar/types.hpp"

#include <vector>

namespace dpolar {

class EnergyLossModel {
public:
    explicit EnergyLossModel(const ScenarioConfig& scenario);

    [[nodiscard]] double energyLossMev(int mass_number, double energy_per_u_mev, double thickness_um) const;
    [[nodiscard]] std::vector<SamplePoint> firstScintillatorCurve() const;
    [[nodiscard]] std::vector<SamplePoint> secondScintillatorCurve() const;

private:
    EnergyLossConfig config_;
    std::vector<double> energy_mev_per_u_;
    std::vector<double> range_um_;
};

}  // namespace dpolar
