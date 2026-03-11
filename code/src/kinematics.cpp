#include "dpolar/kinematics.hpp"

#include "TLorentzVector.h"
#include "TVector3.h"

#include <cmath>
#include <numbers>

namespace dpolar {

ElasticDpKinematics::ElasticDpKinematics(const BeamConfig& beam)
    : beam_(beam) {
    total_deuteron_energy_mev_ = beam_.deuteron_mass_mev + beam_.kinetic_energy_mev;
    deuteron_momentum_mev_c_ = std::sqrt(
        total_deuteron_energy_mev_ * total_deuteron_energy_mev_ -
        beam_.deuteron_mass_mev * beam_.deuteron_mass_mev);
    beta_ = deuteron_momentum_mev_c_ / (total_deuteron_energy_mev_ + beam_.proton_mass_mev);
    gamma_ = 1.0 / std::sqrt(1.0 - beta_ * beta_);
    deuteron_cm_energy_mev_ = gamma_ * total_deuteron_energy_mev_ - gamma_ * beta_ * deuteron_momentum_mev_c_;
    deuteron_cm_momentum_mev_c_ = -gamma_ * beta_ * total_deuteron_energy_mev_ + gamma_ * deuteron_momentum_mev_c_;
    proton_cm_energy_mev_ = gamma_ * beam_.proton_mass_mev;
}

ScatteringSolution ElasticDpKinematics::scatter(const double theta_cm_rad, const double phi_cm_rad) const {
    TLorentzVector proton_lab_before;
    proton_lab_before.SetPxPyPzE(0.0, 0.0, 0.0, beam_.proton_mass_mev);

    TLorentzVector deuteron_lab_before;
    deuteron_lab_before.SetPxPyPzE(0.0, 0.0, deuteron_momentum_mev_c_, total_deuteron_energy_mev_);

    TLorentzVector total_lab = proton_lab_before + deuteron_lab_before;
    const TVector3 boost_vector = total_lab.BoostVector();

    TLorentzVector proton_cm = proton_lab_before;
    TLorentzVector deuteron_cm = deuteron_lab_before;
    proton_cm.Boost(-boost_vector);
    deuteron_cm.Boost(-boost_vector);

    // [EN] Rotate the elastic two-body final state in the CM frame before boosting back to the lab / [CN] 在质心系中先旋转两体末态，再整体洛伦兹变换回实验室系
    proton_cm.SetTheta(std::numbers::pi_v<double> - theta_cm_rad);
    proton_cm.SetPhi(std::numbers::pi_v<double> + phi_cm_rad);
    deuteron_cm.SetTheta(theta_cm_rad);
    deuteron_cm.SetPhi(phi_cm_rad);

    proton_cm.Boost(boost_vector);
    deuteron_cm.Boost(boost_vector);

    return ScatteringSolution {
        ScatterPoint {
            deuteron_cm.Theta(),
            deuteron_cm.Phi(),
            deuteron_cm.E() - beam_.deuteron_mass_mev,
        },
        ScatterPoint {
            proton_cm.Theta(),
            proton_cm.Phi(),
            proton_cm.E() - beam_.proton_mass_mev,
        },
    };
}

std::pair<double, double> ElasticDpKinematics::deuteronCmFromLab(const double theta_lab_rad) const {
    const double tangent = std::tan(theta_lab_rad);
    const double gamma_tangent = gamma_ * tangent;
    const double square_root = std::sqrt(1.0 + gamma_ * gamma_ * tangent * tangent);
    const double arcsine = std::asin(
        (tangent * gamma_ * beta_ * deuteron_cm_energy_mev_) /
        (deuteron_cm_momentum_mev_c_ * square_root));
    const double first = std::atan(gamma_tangent) + arcsine;
    const double second = std::atan(gamma_tangent) + std::numbers::pi_v<double> - arcsine;
    return {first, second};
}

double ElasticDpKinematics::protonLabFromDeuteronCm(const double theta_cm_rad) const {
    const double sine = std::sin(theta_cm_rad);
    const double cosine = std::cos(theta_cm_rad);
    const double numerator = deuteron_cm_momentum_mev_c_ * sine;
    const double denominator = gamma_ * beta_ * proton_cm_energy_mev_ - gamma_ * deuteron_cm_momentum_mev_c_ * cosine;
    return std::atan(numerator / denominator);
}

double ElasticDpKinematics::protonCmFromLab(const double theta_lab_rad) const {
    const double tangent = std::tan(theta_lab_rad);
    const double gamma_tangent = gamma_ * tangent;
    const double square_root = std::sqrt(1.0 + gamma_ * gamma_ * tangent * tangent);
    const double arcsine = std::asin(
        (tangent * gamma_ * beta_ * proton_cm_energy_mev_) /
        (deuteron_cm_momentum_mev_c_ * square_root));
    return std::numbers::pi_v<double> - (std::atan(gamma_tangent) + arcsine);
}

double ElasticDpKinematics::deuteronMassMev() const noexcept {
    return beam_.deuteron_mass_mev;
}

double ElasticDpKinematics::protonMassMev() const noexcept {
    return beam_.proton_mass_mev;
}

double ElasticDpKinematics::deuteronMomentumMevC() const noexcept {
    return deuteron_momentum_mev_c_;
}

}  // namespace dpolar
