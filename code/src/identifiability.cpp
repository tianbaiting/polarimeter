#include "dpolar/identifiability.hpp"

#include "dpolar/acceptance.hpp"
#include "dpolar/counts.hpp"
#include "dpolar/kinematics.hpp"
#include "dpolar/types.hpp"

#include "TDecompSVD.h"
#include "TMatrixD.h"
#include "TMatrixDSym.h"
#include "TMatrixDSymEigen.h"
#include "TVectorD.h"

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <limits>
#include <map>
#include <numbers>
#include <numeric>
#include <set>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace dpolar {
namespace {

struct SymmetricEigenResult {
    std::vector<double> values;
    DenseMatrix vectors;
};

struct HarmonicIntegrals {
    double constant{};
    double cos_phi{};
    double sin_phi{};
    double cos_two_phi{};
    double sin_two_phi{};
};

TMatrixDSym toRootSymmetric(const DenseMatrix& matrix) {
    if (matrix.rows != matrix.cols) {
        throw std::invalid_argument("Symmetric matrix must be square");
    }
    TMatrixDSym result(static_cast<int>(matrix.rows));
    for (std::size_t row = 0; row < matrix.rows; ++row) {
        for (std::size_t column = 0; column < matrix.cols; ++column) {
            result(static_cast<int>(row), static_cast<int>(column)) = matrix(row, column);
        }
    }
    return result;
}

SymmetricEigenResult symmetricEigen(const DenseMatrix& matrix) {
    if (matrix.rows == 0U) {
        return SymmetricEigenResult{{}, DenseMatrix(0U, 0U)};
    }
    TMatrixDSymEigen decomposition(toRootSymmetric(matrix));
    const TVectorD eigenvalues = decomposition.GetEigenValues();
    const TMatrixD eigenvectors = decomposition.GetEigenVectors();
    std::vector<std::size_t> order(matrix.rows);
    std::iota(order.begin(), order.end(), 0U);
    std::sort(order.begin(), order.end(), [&](const std::size_t left, const std::size_t right) {
        return eigenvalues[static_cast<int>(left)] > eigenvalues[static_cast<int>(right)];
    });
    SymmetricEigenResult result;
    result.values.resize(matrix.rows);
    result.vectors = DenseMatrix(matrix.rows, matrix.rows);
    for (std::size_t output_column = 0; output_column < matrix.rows; ++output_column) {
        const std::size_t source_column = order[output_column];
        result.values[output_column] = eigenvalues[static_cast<int>(source_column)];
        for (std::size_t row = 0; row < matrix.rows; ++row) {
            result.vectors(row, output_column) = eigenvectors(static_cast<int>(row), static_cast<int>(source_column));
        }
    }
    return result;
}

DenseMatrix pseudoInverseSymmetric(const DenseMatrix& matrix, const RankThreshold& threshold) {
    if (matrix.rows == 0U) {
        return DenseMatrix(0U, 0U);
    }
    const SymmetricEigenResult eigen = symmetricEigen(matrix);
    const double maximum = std::max(0.0, eigen.values.front());
    const double cutoff = std::max(threshold.absolute, threshold.relative * maximum);
    DenseMatrix result(matrix.rows, matrix.cols);
    for (std::size_t mode = 0; mode < matrix.rows; ++mode) {
        if (!(eigen.values[mode] > cutoff)) {
            continue;
        }
        const double inverse = 1.0 / eigen.values[mode];
        for (std::size_t row = 0; row < matrix.rows; ++row) {
            for (std::size_t column = 0; column < matrix.cols; ++column) {
                result(row, column) += inverse * eigen.vectors(row, mode) * eigen.vectors(column, mode);
            }
        }
    }
    return result;
}

double dotRow(const DenseMatrix& matrix, const std::size_t row, const TensorVector& vector) {
    double result = 0.0;
    for (std::size_t column = 0; column < 5U; ++column) {
        result += matrix(row, column) * vector[column];
    }
    return result;
}

double vectorNorm(const std::vector<double>& values) {
    double squared = 0.0;
    for (const double value : values) {
        squared += value * value;
    }
    return std::sqrt(squared);
}

HarmonicIntegrals harmonicIntegrals(const double center_rad, const double width_rad) {
    const double half_width = 0.5 * width_rad;
    return HarmonicIntegrals{
        width_rad,
        2.0 * std::cos(center_rad) * std::sin(half_width),
        2.0 * std::sin(center_rad) * std::sin(half_width),
        std::cos(2.0 * center_rad) * std::sin(width_rad),
        std::sin(2.0 * center_rad) * std::sin(width_rad),
    };
}

PolarimeterChannelResponse integrateWindowResponse(const ScenarioConfig& scenario,
                                                   const ObservableTableRepository& observables,
                                                   const CountRateCalculator& counts,
                                                   const CmBranchWindow& window,
                                                   const DetectorArm& arm,
                                                   const std::string& label,
                                                   const std::string& angle_group,
                                                   const std::string& sector,
                                                   const double phi_center_deg) {
    PolarimeterChannelResponse result;
    result.label = label;
    result.angle_group = angle_group;
    result.sector = sector;
    result.theta_lab_deg = arm.theta_lab_deg;
    result.phi_center_deg = phi_center_deg;
    if (!window.valid()) {
        return result;
    }

    const HarmonicIntegrals harmonics = harmonicIntegrals(toRadians(phi_center_deg), window.delta_phi_rad);
    const int steps = scenario.run.integration_steps;
    const double delta_theta = window.width_rad() / static_cast<double>(steps);
    double baseline_integral = 0.0;
    std::array<double, 5> tensor_integrals{};
    std::array<double, 3> vector_integrals{};
    for (int step = 0; step < steps; ++step) {
        const double theta_rad = window.begin_rad + (static_cast<double>(step) + 0.5) * delta_theta;
        const double theta_deg = toDegrees(theta_rad);
        const double sigma = observables.differentialCrossSectionMbPerSr(theta_deg);
        const CartesianAnalyzingPowers powers = cartesianAnalyzingPowers(observables, theta_deg);
        baseline_integral += sigma * harmonics.constant * delta_theta;
        for (std::size_t basis_index = 0; basis_index < 5U; ++basis_index) {
            TensorVector basis{};
            basis[basis_index] = 1.0;
            const PhysicalTensorComponents physical = TensorPolarization::fromInternal(basis).physical();
            const double response = (2.0 / 3.0) * powers.axz * (physical.pxz * harmonics.cos_phi - physical.pyz * harmonics.sin_phi) +
                                    (1.0 / 6.0) * powers.axx_minus_ayy *
                                        (physical.pxx_minus_pyy * harmonics.cos_two_phi - 2.0 * physical.pxy * harmonics.sin_two_phi) +
                                    0.5 * physical.pzz * powers.azz * harmonics.constant;
            tensor_integrals[basis_index] += sigma * response * delta_theta;
        }
        vector_integrals[0] += sigma * 1.5 * powers.ay * harmonics.sin_phi * delta_theta;
        vector_integrals[1] += sigma * 1.5 * powers.ay * harmonics.cos_phi * delta_theta;
    }

    result.unpolarized_mean = counts.countsFromIntegratedCrossSection(baseline_integral * kMillibarnToSquareMeter);
    for (std::size_t index = 0; index < 5U; ++index) {
        result.tensor_derivative[index] = counts.countsFromIntegratedCrossSection(tensor_integrals[index] * kMillibarnToSquareMeter);
    }
    for (std::size_t index = 0; index < 3U; ++index) {
        result.vector_derivative[index] = counts.countsFromIntegratedCrossSection(vector_integrals[index] * kMillibarnToSquareMeter);
    }
    return result;
}

PolarimeterChannelResponse
addResponses(const PolarimeterChannelResponse& first, const PolarimeterChannelResponse& second, const std::string& label) {
    PolarimeterChannelResponse result = first;
    result.label = label;
    result.unpolarized_mean += second.unpolarized_mean;
    for (std::size_t index = 0; index < 5U; ++index) {
        result.tensor_derivative[index] += second.tensor_derivative[index];
    }
    for (std::size_t index = 0; index < 3U; ++index) {
        result.vector_derivative[index] += second.vector_derivative[index];
    }
    return result;
}

std::array<std::pair<std::string, double>, 4> sectors() {
    return {{{"L", 0.0}, {"U", 90.0}, {"R", 180.0}, {"D", 270.0}}};
}

std::vector<NuisanceDefinition> nuisanceDefinitions(const std::vector<PolarimeterChannelResponse>& channels,
                                                    const AnalysisOptions& options) {
    std::vector<NuisanceDefinition> definitions;
    if (options.normalization == NormalizationModel::Global) {
        definitions.push_back(NuisanceDefinition{"log_luminosity", "global_normalization"});
    } else if (options.normalization == NormalizationModel::PerStation) {
        std::set<std::string> stations;
        for (const PolarimeterChannelResponse& channel : channels) {
            const std::size_t separator = channel.angle_group.find(':');
            stations.insert(separator == std::string::npos ? "station1" : channel.angle_group.substr(0U, separator));
        }
        for (const std::string& station : stations) {
            definitions.push_back(NuisanceDefinition{"log_norm_" + station, "per_station_normalization"});
        }
    } else if (options.normalization == NormalizationModel::PerAngle) {
        std::set<std::string> groups;
        for (const PolarimeterChannelResponse& channel : channels) {
            groups.insert(channel.angle_group);
        }
        for (const std::string& group : groups) {
            definitions.push_back(NuisanceDefinition{"log_norm_" + group, "per_angle_normalization"});
        }
    }
    if (options.profile_relative_sector_efficiencies) {
        for (const auto& [sector, phi] : sectors()) {
            static_cast<void>(phi);
            definitions.push_back(NuisanceDefinition{"log_efficiency_" + sector, "relative_sector_efficiency"});
        }
    }
    return definitions;
}

DenseMatrix nuisanceJacobian(const std::vector<PolarimeterChannelResponse>& channels,
                             const std::vector<double>& means,
                             const std::vector<NuisanceDefinition>& definitions) {
    DenseMatrix result(channels.size(), definitions.size());
    for (std::size_t row = 0; row < channels.size(); ++row) {
        for (std::size_t column = 0; column < definitions.size(); ++column) {
            const NuisanceDefinition& definition = definitions[column];
            if (definition.kind == "global_normalization") {
                result(row, column) = means[row];
            } else if (definition.kind == "per_station_normalization") {
                const std::size_t separator = channels[row].angle_group.find(':');
                const std::string station =
                    separator == std::string::npos ? "station1" : channels[row].angle_group.substr(0U, separator);
                if (definition.name == "log_norm_" + station) {
                    result(row, column) = means[row];
                }
            } else if (definition.kind == "per_angle_normalization" && definition.name == "log_norm_" + channels[row].angle_group) {
                result(row, column) = means[row];
            } else if (definition.kind == "relative_sector_efficiency" && definition.name == "log_efficiency_" + channels[row].sector) {
                result(row, column) = means[row];
            }
        }
    }
    return result;
}

FisherInformation fisherFromJacobian(const std::vector<PolarimeterChannelResponse>& channels,
                                     const std::vector<double>& means,
                                     const DenseMatrix& polarization_jacobian,
                                     const AnalysisOptions& options) {
    FisherInformation result;
    result.nuisances = nuisanceDefinitions(channels, options);
    result.nuisance_jacobian = nuisanceJacobian(channels, means, result.nuisances);
    const std::size_t q_count = polarization_jacobian.cols;
    const std::size_t nuisance_count = result.nuisances.size();
    const std::size_t total_count = q_count + nuisance_count;
    result.full = DenseMatrix(total_count, total_count);
    for (std::size_t channel = 0; channel < channels.size(); ++channel) {
        if (!(means[channel] > 0.0) || !std::isfinite(means[channel])) {
            throw std::runtime_error("Poisson means must be finite and positive");
        }
        std::vector<double> derivative(total_count);
        for (std::size_t parameter = 0; parameter < q_count; ++parameter) {
            derivative[parameter] = polarization_jacobian(channel, parameter);
        }
        for (std::size_t parameter = 0; parameter < nuisance_count; ++parameter) {
            derivative[q_count + parameter] = result.nuisance_jacobian(channel, parameter);
        }
        for (std::size_t row = 0; row < total_count; ++row) {
            for (std::size_t column = 0; column < total_count; ++column) {
                result.full(row, column) += derivative[row] * derivative[column] / means[channel];
            }
        }
    }

    result.polarization_raw = DenseMatrix(q_count, q_count);
    for (std::size_t row = 0; row < q_count; ++row) {
        for (std::size_t column = 0; column < q_count; ++column) {
            result.polarization_raw(row, column) = result.full(row, column);
        }
    }
    result.profiled = result.polarization_raw;
    if (nuisance_count > 0U) {
        DenseMatrix qn(q_count, nuisance_count);
        DenseMatrix nn(nuisance_count, nuisance_count);
        for (std::size_t row = 0; row < q_count; ++row) {
            for (std::size_t column = 0; column < nuisance_count; ++column) {
                qn(row, column) = result.full(row, q_count + column);
            }
        }
        for (std::size_t row = 0; row < nuisance_count; ++row) {
            for (std::size_t column = 0; column < nuisance_count; ++column) {
                nn(row, column) = result.full(q_count + row, q_count + column);
            }
        }
        const DenseMatrix correction = multiply(multiply(qn, pseudoInverseSymmetric(nn, options.threshold)), transpose(qn));
        for (std::size_t row = 0; row < q_count; ++row) {
            for (std::size_t column = 0; column < q_count; ++column) {
                result.profiled(row, column) -= correction(row, column);
                if (std::abs(result.profiled(row, column)) < 1.0e-12) {
                    result.profiled(row, column) = 0.0;
                }
            }
        }
    }

    const SymmetricEigenResult profiled_eigen = symmetricEigen(result.profiled);
    const SymmetricEigenResult raw_eigen = symmetricEigen(result.polarization_raw);
    const double largest_information = profiled_eigen.values.empty() ? 0.0 : std::max(0.0, profiled_eigen.values.front());
    const double reference_information = raw_eigen.values.empty()
                                             ? largest_information
                                             : std::max(largest_information, std::max(0.0, raw_eigen.values.front()));
    const double information_cutoff =
        std::max(options.threshold.absolute * options.threshold.absolute, options.threshold.relative * reference_information);
    result.threshold = std::sqrt(information_cutoff);
    result.effective_singular_values.reserve(profiled_eigen.values.size());
    result.pseudo_determinant = 1.0;
    for (const double eigenvalue : profiled_eigen.values) {
        const double singular = std::sqrt(std::max(0.0, eigenvalue));
        result.effective_singular_values.push_back(singular);
        if (eigenvalue > information_cutoff) {
            ++result.effective_rank;
            result.pseudo_determinant *= eigenvalue;
        }
    }
    if (result.effective_rank == 0) {
        result.pseudo_determinant = 0.0;
    }
    RankThreshold covariance_threshold;
    covariance_threshold.absolute = information_cutoff;
    covariance_threshold.relative = 0.0;
    result.covariance = pseudoInverseSymmetric(result.profiled, covariance_threshold);
    result.correlation = DenseMatrix(q_count, q_count);
    for (std::size_t row = 0; row < q_count; ++row) {
        for (std::size_t column = 0; column < q_count; ++column) {
            const double denominator =
                std::sqrt(std::max(0.0, result.covariance(row, row)) * std::max(0.0, result.covariance(column, column)));
            if (denominator > 0.0) {
                result.correlation(row, column) = result.covariance(row, column) / denominator;
            }
        }
    }
    for (std::size_t parameter = 0; parameter < q_count; ++parameter) {
        double null_projection = 0.0;
        for (std::size_t mode = 0; mode < profiled_eigen.values.size(); ++mode) {
            if (profiled_eigen.values[mode] <= information_cutoff) {
                null_projection += profiled_eigen.vectors(parameter, mode) * profiled_eigen.vectors(parameter, mode);
            }
        }
        if (null_projection > 1.0e-10) {
            for (std::size_t other = 0; other < q_count; ++other) {
                result.correlation(parameter, other) = 0.0;
                result.correlation(other, parameter) = 0.0;
            }
        }
    }
    return result;
}

std::string escapeJson(const std::string& value) {
    std::string result;
    for (const char character : value) {
        if (character == '"' || character == '\\') {
            result.push_back('\\');
        }
        if (character == '\n') {
            result += "\\n";
        } else {
            result.push_back(character);
        }
    }
    return result;
}

void writeJsonMatrix(std::ostream& output, const DenseMatrix& matrix) {
    output << '[';
    for (std::size_t row = 0; row < matrix.rows; ++row) {
        if (row > 0U) {
            output << ',';
        }
        output << '[';
        for (std::size_t column = 0; column < matrix.cols; ++column) {
            if (column > 0U) {
                output << ',';
            }
            output << matrix(row, column);
        }
        output << ']';
    }
    output << ']';
}

template <typename Range> void writeJsonArray(std::ostream& output, const Range& values) {
    output << '[';
    bool first = true;
    for (const auto& value : values) {
        if (!first) {
            output << ',';
        }
        first = false;
        output << value;
    }
    output << ']';
}

}

CartesianAnalyzingPowers cartesianAnalyzingPowers(const ObservableTableRepository& observables, const double theta_cm_deg) {
    return CartesianAnalyzingPowers{
        2.0 * observables.vectorIT11(theta_cm_deg) / std::sqrt(3.0),
        -std::sqrt(3.0) * observables.tensorT21(theta_cm_deg),
        2.0 * std::sqrt(3.0) * observables.tensorT22(theta_cm_deg),
        std::numbers::sqrt2_v<double> * observables.tensorT20(theta_cm_deg),
    };
}

std::vector<PolarimeterChannelResponse> buildIdealFourArmRing(const CartesianAnalyzingPowers& powers,
                                                              const double unpolarized_count_per_arm,
                                                              const double theta_lab_deg,
                                                              std::string angle_group) {
    std::vector<PolarimeterChannelResponse> channels;
    for (const auto& [sector, phi_deg] : sectors()) {
        PolarimeterChannelResponse channel;
        channel.label = angle_group + ":" + sector;
        channel.angle_group = angle_group;
        channel.sector = sector;
        channel.theta_lab_deg = theta_lab_deg;
        channel.phi_center_deg = phi_deg;
        channel.unpolarized_mean = unpolarized_count_per_arm;
        const double phi = toRadians(phi_deg);
        for (std::size_t basis_index = 0; basis_index < 5U; ++basis_index) {
            TensorVector basis{};
            basis[basis_index] = 1.0;
            const PhysicalTensorComponents physical = TensorPolarization::fromInternal(basis).physical();
            channel.tensor_derivative[basis_index] =
                unpolarized_count_per_arm *
                ((2.0 / 3.0) * (physical.pxz * std::cos(phi) - physical.pyz * std::sin(phi)) * powers.axz +
                 (1.0 / 6.0) * (physical.pxx_minus_pyy * std::cos(2.0 * phi) - 2.0 * physical.pxy * std::sin(2.0 * phi)) *
                     powers.axx_minus_ayy +
                 0.5 * physical.pzz * powers.azz);
        }
        channel.vector_derivative = VectorPolarization{
            unpolarized_count_per_arm * 1.5 * std::sin(phi) * powers.ay,
            unpolarized_count_per_arm * 1.5 * std::cos(phi) * powers.ay,
            0.0,
        };
        channels.push_back(std::move(channel));
    }
    return channels;
}

std::vector<PolarimeterChannelResponse> buildScenarioChannels(const ScenarioConfig& scenario, const ChannelSelection selection) {
    const ElasticDpKinematics kinematics(scenario.beam);
    const ObservableTableRepository observables(scenario);
    const CountRateCalculator counts(scenario, observables);
    std::vector<PolarimeterChannelResponse> channels;

    auto append_proton_arm = [&](const std::size_t arm_index, const CmBranchWindow& window, const std::string& group) {
        const DetectorArm& arm = scenario.custom_layout.proton_arms.at(arm_index);
        for (const auto& [sector, phi_deg] : sectors()) {
            channels.push_back(
                integrateWindowResponse(scenario, observables, counts, window, arm, group + ":" + sector, group, sector, phi_deg));
        }
    };

    const CmBranchWindow proton_forward = protonWindowFromArm(kinematics, scenario.custom_layout.proton_arms[0]);
    const CmBranchWindow proton_backward = protonWindowFromArm(kinematics, scenario.custom_layout.proton_arms[1]);
    const BranchPair deuteron = deuteronWindowsFromArm(kinematics, scenario.custom_layout.deuteron_arm);

    if (selection == ChannelSelection::ProtonOneTheta) {
        append_proton_arm(0U, proton_forward, "proton_forward");
        return channels;
    }
    if (selection == ChannelSelection::ProtonSingles || selection == ChannelSelection::CurrentProduction) {
        append_proton_arm(0U, proton_forward, "proton_forward");
        append_proton_arm(1U, proton_backward, "proton_backward");
        return channels;
    }
    if (selection == ChannelSelection::DeuteronSingles) {
        for (const auto& [sector, phi_deg] : sectors()) {
            const PolarimeterChannelResponse forward = integrateWindowResponse(scenario,
                                                                               observables,
                                                                               counts,
                                                                               deuteron.forward,
                                                                               scenario.custom_layout.deuteron_arm,
                                                                               "deuteron_forward:" + sector,
                                                                               "deuteron_combined",
                                                                               sector,
                                                                               phi_deg);
            const PolarimeterChannelResponse backward = integrateWindowResponse(scenario,
                                                                                observables,
                                                                                counts,
                                                                                deuteron.backward,
                                                                                scenario.custom_layout.deuteron_arm,
                                                                                "deuteron_backward:" + sector,
                                                                                "deuteron_combined",
                                                                                sector,
                                                                                phi_deg);
            channels.push_back(addResponses(forward, backward, "deuteron_combined:" + sector));
        }
        return channels;
    }
    if (selection == ChannelSelection::DeuteronBranches) {
        for (const auto& [sector, phi_deg] : sectors()) {
            channels.push_back(integrateWindowResponse(scenario,
                                                       observables,
                                                       counts,
                                                       deuteron.forward,
                                                       scenario.custom_layout.deuteron_arm,
                                                       "deuteron_forward:" + sector,
                                                       "deuteron_forward",
                                                       sector,
                                                       phi_deg));
            channels.push_back(integrateWindowResponse(scenario,
                                                       observables,
                                                       counts,
                                                       deuteron.backward,
                                                       scenario.custom_layout.deuteron_arm,
                                                       "deuteron_backward:" + sector,
                                                       "deuteron_backward",
                                                       sector,
                                                       phi_deg));
        }
        return channels;
    }
    if (selection == ChannelSelection::Coincidences) {
        const CmBranchWindow forward_overlap = intersectWindows(proton_forward, deuteron.forward);
        const CmBranchWindow backward_overlap = intersectWindows(proton_backward, deuteron.backward);
        append_proton_arm(0U, forward_overlap, "coincidence_forward");
        append_proton_arm(1U, backward_overlap, "coincidence_backward");
        return channels;
    }
    throw std::invalid_argument("Ideal channel selection requires explicit analyzing powers");
}

DenseMatrix responseMatrix(const std::vector<PolarimeterChannelResponse>& channels) {
    DenseMatrix result(channels.size(), 5U);
    for (std::size_t row = 0; row < channels.size(); ++row) {
        for (std::size_t column = 0; column < 5U; ++column) {
            result(row, column) = channels[row].tensor_derivative[column];
        }
    }
    return result;
}

std::vector<double> expectedMeans(const std::vector<PolarimeterChannelResponse>& channels, const TensorVector& state) {
    std::vector<double> result(channels.size());
    const DenseMatrix response = responseMatrix(channels);
    for (std::size_t row = 0; row < channels.size(); ++row) {
        result[row] = channels[row].unpolarized_mean + dotRow(response, row, state);
    }
    return result;
}

IdentifiabilityResult analyzeIdentifiability(const DenseMatrix& response, const RankThreshold& threshold) {
    IdentifiabilityResult result;
    result.response_matrix = response;
    const std::size_t decomposition_rows = std::max(response.rows, response.cols);
    TMatrixD root_response(static_cast<int>(decomposition_rows), static_cast<int>(response.cols));
    for (std::size_t row = 0; row < response.rows; ++row) {
        for (std::size_t column = 0; column < response.cols; ++column) {
            root_response(static_cast<int>(row), static_cast<int>(column)) = response(row, column);
        }
    }
    TDecompSVD decomposition(root_response);
    if (!decomposition.Decompose()) {
        throw std::runtime_error("Response-matrix SVD failed");
    }
    const TVectorD singular_values = decomposition.GetSig();
    const TMatrixD right_vectors = decomposition.GetV();
    result.svd.right_singular_vectors = DenseMatrix(response.cols, response.cols);
    for (std::size_t row = 0; row < response.cols; ++row) {
        for (std::size_t column = 0; column < response.cols; ++column) {
            result.svd.right_singular_vectors(row, column) = right_vectors(static_cast<int>(row), static_cast<int>(column));
        }
    }
    const double largest = singular_values.GetNrows() > 0 ? singular_values[0] : 0.0;
    result.svd.threshold = std::max(threshold.absolute, threshold.relative * largest);
    for (std::size_t index = 0; index < response.cols; ++index) {
        const double singular = singular_values[static_cast<int>(index)];
        result.svd.singular_values.push_back(singular);
        if (singular > result.svd.threshold) {
            ++result.svd.rank;
        }
    }
    if (result.svd.rank > 0) {
        const double smallest = result.svd.singular_values[static_cast<std::size_t>(result.svd.rank - 1)];
        result.svd.condition_number = smallest > 0.0 ? largest / smallest : std::numeric_limits<double>::infinity();
    } else {
        result.svd.condition_number = std::numeric_limits<double>::infinity();
    }
    for (std::size_t mode = static_cast<std::size_t>(result.svd.rank); mode < 5U; ++mode) {
        NullDirection direction;
        std::vector<double> residual(response.rows);
        for (std::size_t component = 0; component < 5U; ++component) {
            direction.internal[component] = result.svd.right_singular_vectors(component, mode);
        }
        direction.physical = TensorPolarization::fromInternal(direction.internal).physical();
        for (std::size_t row = 0; row < response.rows; ++row) {
            residual[row] = dotRow(response, row, direction.internal);
        }
        direction.residual_norm = vectorNorm(residual);
        result.null_directions.push_back(direction);
    }
    return result;
}

FisherInformation calculateFisherInformation(const std::vector<PolarimeterChannelResponse>& channels,
                                             const TensorVector& state,
                                             const AnalysisOptions& options) {
    return fisherFromJacobian(channels, expectedMeans(channels, state), responseMatrix(channels), options);
}

MultiStationAnalysis
analyzeStations(const std::vector<PolarimeterStation>& stations, const TensorVector& reference_state, const AnalysisOptions& options) {
    if (stations.empty()) {
        throw std::invalid_argument("At least one polarimeter station is required");
    }
    MultiStationAnalysis result;
    std::vector<PolarimeterChannelResponse> transported_channels;
    std::vector<DenseMatrix> station_responses;
    for (const PolarimeterStation& station : stations) {
        DenseMatrix local = responseMatrix(station.channels);
        DenseMatrix transported = multiply(local, station.transport);
        station_responses.push_back(transported);
        for (std::size_t row = 0; row < station.channels.size(); ++row) {
            PolarimeterChannelResponse channel = station.channels[row];
            channel.label = station.label + ":" + channel.label;
            channel.angle_group = station.label + ":" + channel.angle_group;
            for (std::size_t column = 0; column < 5U; ++column) {
                channel.tensor_derivative[column] = transported(row, column);
            }
            transported_channels.push_back(std::move(channel));
        }
    }
    result.combined_response = station_responses.front();
    for (std::size_t station = 1U; station < station_responses.size(); ++station) {
        result.combined_response = verticalStack(result.combined_response, station_responses[station]);
    }
    result.identifiability = analyzeIdentifiability(result.combined_response, options.threshold);
    result.fisher = calculateFisherInformation(transported_channels, reference_state, options);
    if (station_responses.size() >= 2U) {
        result.null_intersection_dimension = nullIntersectionDimension(station_responses[0], station_responses[1], options.threshold);
        result.null_space_principal_angles_deg =
            nullSpacePrincipalAnglesDegrees(station_responses[0], station_responses[1], options.threshold);
    } else {
        result.null_intersection_dimension = 5 - result.identifiability.svd.rank;
    }
    return result;
}

NominalPyyResult
analyzeNominalPyy(const std::vector<PolarimeterStation>& stations, const double magnitude, const AnalysisOptions& options) {
    NominalPyyResult result;
    result.parameter_names = {"P_T", "tilt_toward_x_rad", "tilt_toward_z_rad"};
    const TensorVector magnitude_direction = TensorPolarization::axial(1.0, VectorPolarization{0.0, 1.0, 0.0}).internal();
    const TensorVector reference = TensorPolarization::axial(magnitude, VectorPolarization{0.0, 1.0, 0.0}).internal();
    TensorVector tilt_x{};
    TensorVector tilt_z{};
    tilt_x[1] = 1.5 * std::numbers::sqrt2_v<double> * magnitude;
    tilt_z[3] = 1.5 * std::numbers::sqrt2_v<double> * magnitude;
    std::vector<PolarimeterChannelResponse> transported_channels;
    std::vector<double> means;
    std::vector<std::array<double, 3>> rows;
    for (const PolarimeterStation& station : stations) {
        const DenseMatrix local_response = responseMatrix(station.channels);
        const DenseMatrix transported_response = multiply(local_response, station.transport);
        const TensorVector local_reference = multiply(station.transport, reference);
        const TensorVector station_magnitude = multiply(station.transport, magnitude_direction);
        const TensorVector station_tilt_x = multiply(station.transport, tilt_x);
        const TensorVector station_tilt_z = multiply(station.transport, tilt_z);
        for (std::size_t channel_index = 0; channel_index < station.channels.size(); ++channel_index) {
            PolarimeterChannelResponse channel = station.channels[channel_index];
            channel.label = station.label + ":" + channel.label;
            channel.angle_group = station.label + ":" + channel.angle_group;
            transported_channels.push_back(std::move(channel));
            double mean = station.channels[channel_index].unpolarized_mean;
            for (std::size_t component = 0; component < 5U; ++component) {
                mean += local_response(channel_index, component) * local_reference[component];
            }
            means.push_back(mean);
            std::array<double, 3> row{};
            for (std::size_t component = 0; component < 5U; ++component) {
                row[0] += local_response(channel_index, component) * station_magnitude[component];
                row[1] += local_response(channel_index, component) * station_tilt_x[component];
                row[2] += local_response(channel_index, component) * station_tilt_z[component];
            }
            rows.push_back(row);
        }
    }
    result.jacobian = DenseMatrix(rows.size(), 3U);
    for (std::size_t row = 0; row < rows.size(); ++row) {
        for (std::size_t column = 0; column < 3U; ++column) {
            result.jacobian(row, column) = rows[row][column];
        }
    }
    result.fisher = fisherFromJacobian(transported_channels, means, result.jacobian, options);
    result.one_sigma.resize(3U, std::numeric_limits<double>::infinity());
    const SymmetricEigenResult information_eigen = symmetricEigen(result.fisher.profiled);
    const double information_cutoff = result.fisher.threshold * result.fisher.threshold;
    for (std::size_t parameter = 0; parameter < 3U; ++parameter) {
        double null_projection = 0.0;
        for (std::size_t mode = 0; mode < information_eigen.values.size(); ++mode) {
            if (information_eigen.values[mode] <= information_cutoff) {
                null_projection += information_eigen.vectors(parameter, mode) * information_eigen.vectors(parameter, mode);
            }
        }
        if (null_projection < 1.0e-10 && result.fisher.covariance(parameter, parameter) > 0.0) {
            result.one_sigma[parameter] = std::sqrt(result.fisher.covariance(parameter, parameter));
        } else {
            for (std::size_t other = 0; other < 3U; ++other) {
                result.fisher.correlation(parameter, other) = 0.0;
                result.fisher.correlation(other, parameter) = 0.0;
            }
        }
    }
    return result;
}

DenseMatrix nullSpace(const IdentifiabilityResult& result) {
    const std::size_t nullity = 5U - static_cast<std::size_t>(result.svd.rank);
    DenseMatrix output(5U, nullity);
    for (std::size_t column = 0; column < nullity; ++column) {
        for (std::size_t row = 0; row < 5U; ++row) {
            output(row, column) = result.svd.right_singular_vectors(row, static_cast<std::size_t>(result.svd.rank) + column);
        }
    }
    return output;
}

int nullIntersectionDimension(const DenseMatrix& first_response, const DenseMatrix& second_response, const RankThreshold& threshold) {
    return 5 - analyzeIdentifiability(verticalStack(first_response, second_response), threshold).svd.rank;
}

std::vector<double>
nullSpacePrincipalAnglesDegrees(const DenseMatrix& first_response, const DenseMatrix& second_response, const RankThreshold& threshold) {
    const DenseMatrix first_null = nullSpace(analyzeIdentifiability(first_response, threshold));
    const DenseMatrix second_null = nullSpace(analyzeIdentifiability(second_response, threshold));
    if (first_null.cols == 0U || second_null.cols == 0U) {
        return {};
    }
    const DenseMatrix overlap = multiply(transpose(first_null), second_null);
    const DenseMatrix gram = multiply(transpose(overlap), overlap);
    const SymmetricEigenResult eigen = symmetricEigen(gram);
    const std::size_t count = std::min(first_null.cols, second_null.cols);
    std::vector<double> angles;
    angles.reserve(count);
    for (std::size_t index = 0; index < count; ++index) {
        const double cosine = std::sqrt(std::clamp(eigen.values[index], 0.0, 1.0));
        angles.push_back(std::acos(cosine) * 180.0 / std::numbers::pi_v<double>);
    }
    return angles;
}

void writeIdentifiabilityJson(const std::filesystem::path& path,
                              const std::string& scenario_name,
                              const std::string& study_name,
                              const std::vector<PolarimeterChannelResponse>& channels,
                              const TensorVector& state,
                              const IdentifiabilityResult& identifiability,
                              const FisherInformation& fisher,
                              const AnalysisOptions& options,
                              const std::vector<std::pair<std::string, std::string>>& metadata) {
    std::filesystem::create_directories(path.parent_path());
    std::ofstream output(path);
    if (!output.is_open()) {
        throw std::runtime_error("Unable to create identifiability JSON: " + path.string());
    }
    output << std::setprecision(17);
    output << "{\n";
    output << "  \"schema_version\": 1,\n";
    output << "  \"scenario\": \"" << escapeJson(scenario_name) << "\",\n";
    output << "  \"study\": \"" << escapeJson(study_name) << "\",\n";
    output << "  \"tensor_basis\": \"" << escapeJson(tensorBasisDescription()) << "\",\n";
    output << "  \"reporting_basis\": "
              "[\"pxx_minus_pyy\",\"pxy\",\"pxz\",\"pyz\",\"pzz\"],\n";
    output << "  \"state_internal\": ";
    writeJsonArray(output, state);
    output << ",\n";
    output << "  \"rank_threshold\": {\"relative\": " << options.threshold.relative << ", \"absolute\": " << options.threshold.absolute
           << ", \"applied\": " << identifiability.svd.threshold << "},\n";
    output << "  \"normalization_model\": \""
           << (options.normalization == NormalizationModel::Known
                   ? "known"
                   : options.normalization == NormalizationModel::Global
                         ? "global"
                         : options.normalization == NormalizationModel::PerStation ? "per_station" : "per_angle")
           << "\",\n";
    output << "  \"profile_relative_sector_efficiencies\": " << (options.profile_relative_sector_efficiencies ? "true" : "false") << ",\n";
    output << "  \"channels\": [\n";
    for (std::size_t index = 0; index < channels.size(); ++index) {
        const PolarimeterChannelResponse& channel = channels[index];
        output << "    {\"label\":\"" << escapeJson(channel.label) << "\",\"angle_group\":\"" << escapeJson(channel.angle_group)
               << "\",\"sector\":\"" << escapeJson(channel.sector) << "\",\"theta_lab_deg\":" << channel.theta_lab_deg
               << ",\"phi_center_deg\":" << channel.phi_center_deg << ",\"unpolarized_mean\":" << channel.unpolarized_mean << '}';
        output << (index + 1U == channels.size() ? "\n" : ",\n");
    }
    output << "  ],\n";
    output << "  \"response_matrix\": ";
    writeJsonMatrix(output, identifiability.response_matrix);
    output << ",\n";
    output << "  \"raw_rank\": " << identifiability.svd.rank << ",\n";
    output << "  \"singular_values\": ";
    writeJsonArray(output, identifiability.svd.singular_values);
    output << ",\n";
    output << "  \"condition_number\": " << identifiability.svd.condition_number << ",\n";
    output << "  \"right_singular_vectors\": ";
    writeJsonMatrix(output, identifiability.svd.right_singular_vectors);
    output << ",\n";
    output << "  \"null_directions\": [";
    for (std::size_t index = 0; index < identifiability.null_directions.size(); ++index) {
        const NullDirection& direction = identifiability.null_directions[index];
        if (index > 0U) {
            output << ',';
        }
        output << "{\"internal\":";
        writeJsonArray(output, direction.internal);
        output << ",\"physical\":[" << direction.physical.pxx_minus_pyy << ',' << direction.physical.pxy << ',' << direction.physical.pxz
               << ',' << direction.physical.pyz << ',' << direction.physical.pzz << "],\"residual_norm\":" << direction.residual_norm
               << '}';
    }
    output << "],\n";
    output << "  \"nuisances\": [";
    for (std::size_t index = 0; index < fisher.nuisances.size(); ++index) {
        if (index > 0U) {
            output << ',';
        }
        output << "{\"name\":\"" << escapeJson(fisher.nuisances[index].name) << "\",\"kind\":\"" << escapeJson(fisher.nuisances[index].kind)
               << "\"}";
    }
    output << "],\n";
    output << "  \"fisher_full\": ";
    writeJsonMatrix(output, fisher.full);
    output << ",\n  \"fisher_polarization_raw\": ";
    writeJsonMatrix(output, fisher.polarization_raw);
    output << ",\n  \"fisher_profiled\": ";
    writeJsonMatrix(output, fisher.profiled);
    output << ",\n  \"covariance_pseudoinverse\": ";
    writeJsonMatrix(output, fisher.covariance);
    output << ",\n  \"correlation\": ";
    writeJsonMatrix(output, fisher.correlation);
    output << ",\n  \"effective_singular_values\": ";
    writeJsonArray(output, fisher.effective_singular_values);
    output << ",\n  \"profiled_uncertainty_eigenvalues\": [";
    for (std::size_t index = 0; index < fisher.effective_singular_values.size(); ++index) {
        if (index > 0U) {
            output << ',';
        }
        const double singular = fisher.effective_singular_values[index];
        if (singular > fisher.threshold) {
            output << 1.0 / (singular * singular);
        } else {
            output << "null";
        }
    }
    output << ']';
    output << ",\n  \"pseudoinverse_one_sigma\": [";
    for (std::size_t index = 0; index < fisher.covariance.rows; ++index) {
        if (index > 0U) {
            output << ',';
        }
        output << std::sqrt(std::max(0.0, fisher.covariance(index, index)));
    }
    output << ']';
    output << ",\n  \"effective_rank\": " << fisher.effective_rank;
    output << ",\n  \"effective_singular_threshold\": " << fisher.threshold;
    output << ",\n  \"fisher_pseudo_determinant\": " << fisher.pseudo_determinant;
    output << ",\n  \"metadata\": {";
    for (std::size_t index = 0; index < metadata.size(); ++index) {
        if (index > 0U) {
            output << ',';
        }
        output << '\"' << escapeJson(metadata[index].first) << "\":\"" << escapeJson(metadata[index].second) << '\"';
    }
    output << "}\n}\n";
}

void writeMatrixCsv(const std::filesystem::path& path, const DenseMatrix& matrix) {
    std::filesystem::create_directories(path.parent_path());
    std::ofstream output(path);
    if (!output.is_open()) {
        throw std::runtime_error("Unable to create matrix CSV: " + path.string());
    }
    output << std::setprecision(17);
    output << "row";
    for (std::size_t column = 0; column < matrix.cols; ++column) {
        output << ",c" << column;
    }
    output << '\n';
    for (std::size_t row = 0; row < matrix.rows; ++row) {
        output << row;
        for (std::size_t column = 0; column < matrix.cols; ++column) {
            output << ',' << matrix(row, column);
        }
        output << '\n';
    }
}

void writeNominalPyyJson(const std::filesystem::path& path,
                         const std::string& scenario_name,
                         const double magnitude,
                         const NominalPyyResult& result,
                         const AnalysisOptions& options,
                         const std::size_t station_count) {
    std::filesystem::create_directories(path.parent_path());
    std::ofstream output(path);
    if (!output.is_open()) {
        throw std::runtime_error("Unable to create nominal-pyy JSON: " + path.string());
    }
    output << std::setprecision(17);
    output << "{\n  \"schema_version\":1,\n  \"scenario\":\"" << escapeJson(scenario_name)
           << "\",\n  \"study\":\"nominal_pyy\",\n  \"station_count\":" << station_count << ",\n  \"magnitude\":" << magnitude
           << ",\n  \"parameter_names\":[";
    for (std::size_t index = 0; index < result.parameter_names.size(); ++index) {
        if (index > 0U) {
            output << ',';
        }
        output << '\"' << escapeJson(result.parameter_names[index]) << '\"';
    }
    output << "],\n  \"jacobian\":";
    writeJsonMatrix(output, result.jacobian);
    output << ",\n  \"fisher_profiled\":";
    writeJsonMatrix(output, result.fisher.profiled);
    output << ",\n  \"covariance_pseudoinverse\":";
    writeJsonMatrix(output, result.fisher.covariance);
    output << ",\n  \"correlation\":";
    writeJsonMatrix(output, result.fisher.correlation);
    output << ",\n  \"effective_singular_values\":";
    writeJsonArray(output, result.fisher.effective_singular_values);
    output << ",\n  \"effective_rank\":" << result.fisher.effective_rank << ",\n  \"one_sigma\":";
    output << '[';
    for (std::size_t index = 0; index < result.one_sigma.size(); ++index) {
        if (index > 0U) {
            output << ',';
        }
        if (std::isfinite(result.one_sigma[index])) {
            output << result.one_sigma[index];
        } else {
            output << "null";
        }
    }
    output << "],\n  \"parameter_identifiable\":[";
    for (std::size_t index = 0; index < result.one_sigma.size(); ++index) {
        if (index > 0U) {
            output << ',';
        }
        output << (std::isfinite(result.one_sigma[index]) ? "true" : "false");
    }
    output << ']';
    output << ",\n  \"normalization_model\":\""
           << (options.normalization == NormalizationModel::Known
                   ? "known"
                   : options.normalization == NormalizationModel::Global
                         ? "global"
                         : options.normalization == NormalizationModel::PerStation ? "per_station" : "per_angle")
           << "\",\n  \"nuisances\":[";
    for (std::size_t index = 0; index < result.fisher.nuisances.size(); ++index) {
        if (index > 0U) {
            output << ',';
        }
        output << "{\"name\":\"" << escapeJson(result.fisher.nuisances[index].name) << "\",\"kind\":\""
               << escapeJson(result.fisher.nuisances[index].kind) << "\"}";
    }
    output << ']';
    output << ",\n  \"rank_threshold\":{\"relative\":" << options.threshold.relative << ",\"absolute\":" << options.threshold.absolute
           << "}\n}\n";
}

}
