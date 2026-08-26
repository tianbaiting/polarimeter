#include "dpolar/config.hpp"
#include "dpolar/identifiability.hpp"
#include "dpolar/observables.hpp"
#include "dpolar/tensor.hpp"
#include "dpolar/types.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <limits>
#include <numbers>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void require(const bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

bool approx(const double left, const double right, const double tolerance = 1.0e-10) {
    return std::abs(left - right) <= tolerance * std::max({1.0, std::abs(left), std::abs(right)});
}

double
channelMean(const std::vector<dpolar::PolarimeterChannelResponse>& channels, const std::string& sector, const dpolar::TensorVector& state) {
    for (const dpolar::PolarimeterChannelResponse& channel : channels) {
        if (channel.sector != sector) {
            continue;
        }
        double mean = channel.unpolarized_mean;
        for (std::size_t index = 0; index < 5U; ++index) {
            mean += channel.tensor_derivative[index] * state[index];
        }
        return mean;
    }
    throw std::runtime_error("Requested sector is absent");
}

}

int main() {
    try {
        const dpolar::PhysicalTensorComponents physical{0.37, -0.08, 0.11, -0.04, 0.23};
        const dpolar::TensorPolarization tensor = dpolar::TensorPolarization::fromPhysical(physical);
        const dpolar::TensorVector tensor_coordinates = tensor.internal();
        const dpolar::TensorPolarization round_trip = dpolar::TensorPolarization::fromInternal(tensor_coordinates);
        require(approx(round_trip.physical().pxx_minus_pyy, physical.pxx_minus_pyy), "diagonal reporting round trip failed");
        require(approx(round_trip.physical().pxy, physical.pxy), "pxy reporting round trip failed");
        require(approx(round_trip.physical().pxz, physical.pxz), "pxz reporting round trip failed");
        require(approx(round_trip.physical().pyz, physical.pyz), "pyz reporting round trip failed");
        require(approx(round_trip.physical().pzz, physical.pzz), "pzz reporting round trip failed");
        require(
            approx(tensor.frobeniusNorm(),
                   std::sqrt(std::inner_product(tensor_coordinates.begin(), tensor_coordinates.end(), tensor_coordinates.begin(), 0.0))),
            "orthonormal tensor basis must preserve the Frobenius norm");

        const dpolar::SpinRotation identity;
        require(identity.apply(tensor).matrix() == tensor.matrix(), "identity rotation must be exact");
        for (const dpolar::VectorPolarization axis : {dpolar::VectorPolarization{1.0, 0.0, 0.0},
                                                      dpolar::VectorPolarization{0.0, 1.0, 0.0},
                                                      dpolar::VectorPolarization{0.0, 0.0, 1.0},
                                                      dpolar::VectorPolarization{0.3, -0.4, 0.7}}) {
            const dpolar::TensorPolarization rotated = dpolar::SpinRotation::axisAngle(axis, 0.43).apply(tensor);
            require(approx(rotated.frobeniusNorm(), tensor.frobeniusNorm()), "SO(3) rotation must preserve tensor norm");
        }
        require(approx(dpolar::SpinRotation::eulerZyx(0.31, -0.27, 0.18).apply(tensor).frobeniusNorm(), tensor.frobeniusNorm()),
                "generic Euler rotation must preserve tensor norm");
        const dpolar::SpinRotation first_rotation = dpolar::SpinRotation::axisAngle({1.0, 0.0, 0.0}, 0.21);
        const dpolar::SpinRotation second_rotation = dpolar::SpinRotation::axisAngle({0.0, 0.0, 1.0}, -0.34);
        const dpolar::TensorVector sequential = second_rotation.apply(first_rotation.apply(tensor)).internal();
        const dpolar::TensorVector mapped =
            dpolar::multiply(dpolar::multiply(second_rotation.tensorMap(), first_rotation.tensorMap()), tensor.internal());
        for (std::size_t index = 0; index < 5U; ++index) {
            require(approx(sequential[index], mapped[index]), "rank-2 transport map composition failed");
        }

        const dpolar::CartesianAnalyzingPowers ideal_powers{0.2, 0.31, -0.84, 0.27};
        const std::vector<dpolar::PolarimeterChannelResponse> ideal = dpolar::buildIdealFourArmRing(ideal_powers, 1.0e5);
        const dpolar::DenseMatrix ideal_response = dpolar::responseMatrix(ideal);
        for (std::size_t row = 0; row < ideal_response.rows; ++row) {
            require(std::abs(ideal_response(row, 1U)) < 1.0e-10, "ideal cardinal ring must have an exact pxy null column");
        }
        const dpolar::IdentifiabilityResult ideal_rank = dpolar::analyzeIdentifiability(ideal_response);
        require(ideal_rank.svd.rank == 4, "known-normalization ideal ring must have tensor rank four");
        require(ideal_rank.null_directions.size() == 1U, "ideal ring must expose one structural null direction");
        require(std::abs(ideal_rank.null_directions.front().physical.pxy) > 0.7, "ideal null direction must be pxy");

        const dpolar::TensorVector pxz_state = dpolar::TensorPolarization::fromPhysical({0.0, 0.0, 0.1, 0.0, 0.0}).internal();
        const dpolar::TensorVector pyz_state = dpolar::TensorPolarization::fromPhysical({0.0, 0.0, 0.0, 0.1, 0.0}).internal();
        const dpolar::TensorVector diagonal_state = dpolar::TensorPolarization::fromPhysical({0.1, 0.0, 0.0, 0.0, 0.0}).internal();
        require(channelMean(ideal, "L", pxz_state) > channelMean(ideal, "R", pxz_state),
                "L-R must respond positively to pxz for positive Axz");
        require(channelMean(ideal, "U", pyz_state) < channelMean(ideal, "D", pyz_state), "U-D must carry the repository negative pyz sign");
        const double lr_diagonal = channelMean(ideal, "L", diagonal_state) + channelMean(ideal, "R", diagonal_state);
        const double ud_diagonal = channelMean(ideal, "U", diagonal_state) + channelMean(ideal, "D", diagonal_state);
        require(lr_diagonal < ud_diagonal,
                "LR-vs-UD must respond to diagonal anisotropy with the "
                "analyzing-power sign");

        dpolar::AnalysisOptions known;
        known.normalization = dpolar::NormalizationModel::Known;
        dpolar::AnalysisOptions global;
        global.normalization = dpolar::NormalizationModel::Global;
        const dpolar::TensorVector unpolarized{};
        require(dpolar::calculateFisherInformation(ideal, unpolarized, known).effective_rank == 4,
                "known normalization must retain the ideal pzz common mode");
        require(dpolar::calculateFisherInformation(ideal, unpolarized, global).effective_rank == 3,
                "global normalization profiling must remove the one-angle pzz "
                "common mode");
        dpolar::AnalysisOptions free_sector_efficiencies = known;
        free_sector_efficiencies.profile_relative_sector_efficiencies = true;
        require(dpolar::calculateFisherInformation(ideal, unpolarized, free_sector_efficiencies).effective_rank == 0,
                "four unconstrained sector efficiencies must absorb all four ideal-ring counts");
        free_sector_efficiencies.normalization = dpolar::NormalizationModel::Global;
        require(dpolar::calculateFisherInformation(ideal, unpolarized, free_sector_efficiencies).effective_rank == 0,
                "adding a redundant global scale must not increase profiled information");

        std::vector<dpolar::PolarimeterChannelResponse> two_angles = ideal;
        std::vector<dpolar::PolarimeterChannelResponse> second_angle =
            dpolar::buildIdealFourArmRing({0.15, -0.22, 0.45, -0.41}, 0.7e5, 0.0, "ideal_theta_2");
        two_angles.insert(two_angles.end(), second_angle.begin(), second_angle.end());
        require(dpolar::calculateFisherInformation(two_angles, unpolarized, global).effective_rank == 4,
                "two angles with distinct Azz must separate pzz from global "
                "normalization");

        const dpolar::PolarimeterStation station1{"station1", ideal, dpolar::identityMatrix(5U)};
        const dpolar::PolarimeterStation station2_identity{"station2", ideal, dpolar::identityMatrix(5U)};
        const dpolar::MultiStationAnalysis duplicated = dpolar::analyzeStations({station1, station2_identity}, unpolarized, known);
        require(duplicated.identifiability.svd.rank == ideal_rank.svd.rank,
                "duplicating an aligned station must not increase structural rank");
        require(duplicated.null_intersection_dimension == 1,
                "aligned station null-space intersection must retain the pxy "
                "direction");
        require(duplicated.null_space_principal_angles_deg.size() == 1U &&
                    std::abs(duplicated.null_space_principal_angles_deg.front()) < 1.0e-5,
                "aligned station null spaces must have zero principal angle");
        const dpolar::FisherInformation one_station_fisher = dpolar::calculateFisherInformation(ideal, unpolarized, known);
        require(approx(duplicated.fisher.profiled(0U, 0U), 2.0 * one_station_fisher.profiled(0U, 0U)),
                "an identical second station must double Fisher information in "
                "observed modes");

        const dpolar::PolarimeterStation station2_rotated{
            "station2", ideal, dpolar::SpinRotation::axisAngle({0.0, 0.0, 1.0}, std::numbers::pi_v<double> / 8.0).tensorMap()};
        const dpolar::MultiStationAnalysis complementary = dpolar::analyzeStations({station1, station2_rotated}, unpolarized, known);
        require(complementary.identifiability.svd.rank == 5, "a complementary z rotation must lift the pxy null direction");
        require(complementary.null_intersection_dimension == 0, "transported null spaces must have zero-dimensional intersection");
        require(complementary.null_intersection_dimension ==
                    dpolar::nullIntersectionDimension(dpolar::responseMatrix(ideal),
                                                      dpolar::multiply(dpolar::responseMatrix(ideal), station2_rotated.transport)),
                "combined nullity must equal the transported null-space "
                "intersection dimension");

        const dpolar::NominalPyyResult nominal_one = dpolar::analyzeNominalPyy({station1}, 0.8, global);
        require(nominal_one.fisher.effective_rank == 2,
                "one ideal station must observe pyy magnitude and only one "
                "first-order tilt");
        require(!std::isfinite(nominal_one.one_sigma[1]), "tilt toward x must be first-order invisible because it generates pxy");
        require(std::isfinite(nominal_one.one_sigma[2]), "tilt toward z must be visible through pyz");
        const dpolar::NominalPyyResult nominal_two = dpolar::analyzeNominalPyy({station1, station2_rotated}, 0.8, global);
        require(nominal_two.fisher.effective_rank == 3, "transport-complementary station must recover both local pyy tilts");

        const dpolar::ScenarioConfig current =
            dpolar::loadScenarioConfig(std::filesystem::path(DPOLAR_SOURCE_DIR) / "config" / "current_tensor.ini");
        require(approx(current.custom_layout.proton_arms[0].theta_lab_deg, 53.4), "current forward proton angle changed unexpectedly");
        require(approx(current.custom_layout.proton_arms[1].theta_lab_deg, 11.2), "current backward proton angle changed unexpectedly");
        require(approx(current.detector_model.active_diameter_mm, 20.0), "current active diameter must match the planned compact detector");
        const std::vector<dpolar::PolarimeterChannelResponse> current_one =
            dpolar::buildScenarioChannels(current, dpolar::ChannelSelection::ProtonOneTheta);
        const std::vector<dpolar::PolarimeterChannelResponse> current_multi =
            dpolar::buildScenarioChannels(current, dpolar::ChannelSelection::CurrentProduction);
        const std::vector<dpolar::PolarimeterChannelResponse> deuteron_branches =
            dpolar::buildScenarioChannels(current, dpolar::ChannelSelection::DeuteronBranches);
        require(current_one.size() == 4U && current_multi.size() == 8U, "current proton channel cardinality mismatch");
        require(deuteron_branches.size() == 8U, "energy-resolved deuteron branch cardinality mismatch");
        require(dpolar::analyzeIdentifiability(dpolar::responseMatrix(current_one)).svd.rank == 4,
                "current one-angle raw response must retain four tensor modes");
        require(dpolar::calculateFisherInformation(current_one, unpolarized, global).effective_rank == 3,
                "current one-angle profiled response must lose pzz to normalization");
        require(dpolar::calculateFisherInformation(current_multi, unpolarized, global).effective_rank == 4,
                "current two-angle response must recover pzz against global "
                "normalization");
        require(dpolar::calculateFisherInformation(deuteron_branches, unpolarized, global).effective_rank == 4,
                "energy-resolved deuteron branches must recover pzz against global normalization");
        for (const dpolar::RankThreshold threshold : {dpolar::RankThreshold{1.0e-8, 1.0e-10}, dpolar::RankThreshold{1.0e-12, 1.0e-14}}) {
            require(dpolar::analyzeIdentifiability(dpolar::responseMatrix(current_multi), threshold).svd.rank == 4,
                    "realistic structural rank must be stable under reasonable "
                    "threshold variation");
        }

        const dpolar::ObservableTableRepository observables(current);
        const dpolar::CartesianAnalyzingPowers converted = dpolar::cartesianAnalyzingPowers(observables, 68.6);
        require(approx(converted.azz, std::sqrt(2.0) * observables.tensorT20(68.6)),
                "Azz conversion must reproduce the scalar pzz convention");
        require(approx(converted.axx_minus_ayy, 2.0 * std::sqrt(3.0) * observables.tensorT22(68.6)),
                "diagonal analyzing-power conversion must reproduce the scalar pyy "
                "convention");

        std::cout << "All tensor identifiability tests passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
