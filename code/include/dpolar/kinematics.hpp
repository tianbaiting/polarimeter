#pragma once

#include "dpolar/config.hpp"
#include "dpolar/types.hpp"

#include <utility>

namespace dpolar {

class ElasticDpKinematics {
public:
    explicit ElasticDpKinematics(const BeamConfig& beam);

    [[nodiscard]] ScatteringSolution scatter(double theta_cm_rad, double phi_cm_rad) const;
    [[nodiscard]] std::pair<double, double> deuteronCmFromLab(double theta_lab_rad) const;
    [[nodiscard]] double protonLabFromDeuteronCm(double theta_cm_rad) const;
    [[nodiscard]] double protonCmFromLab(double theta_lab_rad) const;

    [[nodiscard]] double deuteronMassMev() const noexcept;
    [[nodiscard]] double protonMassMev() const noexcept;
    [[nodiscard]] double deuteronMomentumMevC() const noexcept;

private:
    BeamConfig beam_;
    double total_deuteron_energy_mev_ {};
    double deuteron_momentum_mev_c_ {};
    double beta_ {};
    double gamma_ {};
    double deuteron_cm_energy_mev_ {};
    double deuteron_cm_momentum_mev_c_ {};
    double proton_cm_energy_mev_ {};
};

}  // namespace dpolar
