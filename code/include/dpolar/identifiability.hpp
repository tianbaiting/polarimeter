#pragma once

#include "dpolar/config.hpp"
#include "dpolar/observables.hpp"
#include "dpolar/tensor.hpp"

#include <array>
#include <filesystem>
#include <string>
#include <vector>

namespace dpolar {

struct CartesianAnalyzingPowers {
    double ay{};
    double axz{};
    double axx_minus_ayy{};
    double azz{};
};

struct PolarimeterChannelResponse {
    std::string label;
    std::string angle_group;
    std::string sector;
    double theta_lab_deg{};
    double phi_center_deg{};
    double unpolarized_mean{};
    TensorVector tensor_derivative{};
    VectorPolarization vector_derivative{};
};

enum class ChannelSelection {
    IdealOneTheta,
    ProtonOneTheta,
    ProtonSingles,
    DeuteronSingles,
    DeuteronBranches,
    Coincidences,
    CurrentProduction
};

enum class NormalizationModel { Known, Global, PerStation, PerAngle };

struct RankThreshold {
    double relative{1.0e-10};
    double absolute{1.0e-12};
};

struct SvdResult {
    std::vector<double> singular_values;
    DenseMatrix right_singular_vectors;
    int rank{};
    double threshold{};
    double condition_number{};
};

struct NullDirection {
    TensorVector internal{};
    PhysicalTensorComponents physical;
    double residual_norm{};
};

struct IdentifiabilityResult {
    DenseMatrix response_matrix;
    SvdResult svd;
    std::vector<NullDirection> null_directions;
};

struct NuisanceDefinition {
    std::string name;
    std::string kind;
};

struct FisherInformation {
    DenseMatrix full;
    DenseMatrix polarization_raw;
    DenseMatrix profiled;
    DenseMatrix covariance;
    DenseMatrix correlation;
    DenseMatrix nuisance_jacobian;
    std::vector<NuisanceDefinition> nuisances;
    std::vector<double> effective_singular_values;
    int effective_rank{};
    double threshold{};
    double pseudo_determinant{};
};

struct AnalysisOptions {
    NormalizationModel normalization{NormalizationModel::Known};
    bool profile_relative_sector_efficiencies{false};
    RankThreshold threshold;
};

struct PolarimeterStation {
    std::string label;
    std::vector<PolarimeterChannelResponse> channels;
    DenseMatrix transport{identityMatrix(5)};
};

struct MultiStationAnalysis {
    DenseMatrix combined_response;
    IdentifiabilityResult identifiability;
    FisherInformation fisher;
    std::vector<double> null_space_principal_angles_deg;
    int null_intersection_dimension{};
};

struct NominalPyyResult {
    std::vector<std::string> parameter_names;
    DenseMatrix jacobian;
    FisherInformation fisher;
    std::vector<double> one_sigma;
};

[[nodiscard]] CartesianAnalyzingPowers cartesianAnalyzingPowers(const ObservableTableRepository& observables, double theta_cm_deg);
[[nodiscard]] std::vector<PolarimeterChannelResponse> buildIdealFourArmRing(const CartesianAnalyzingPowers& powers,
                                                                            double unpolarized_count_per_arm = 1.0e5,
                                                                            double theta_lab_deg = 0.0,
                                                                            std::string angle_group = "ideal_theta");
[[nodiscard]] std::vector<PolarimeterChannelResponse> buildScenarioChannels(const ScenarioConfig& scenario, ChannelSelection selection);
[[nodiscard]] DenseMatrix responseMatrix(const std::vector<PolarimeterChannelResponse>& channels);
[[nodiscard]] std::vector<double> expectedMeans(const std::vector<PolarimeterChannelResponse>& channels, const TensorVector& state);
[[nodiscard]] IdentifiabilityResult analyzeIdentifiability(const DenseMatrix& response, const RankThreshold& threshold = {});
[[nodiscard]] FisherInformation calculateFisherInformation(const std::vector<PolarimeterChannelResponse>& channels,
                                                           const TensorVector& state,
                                                           const AnalysisOptions& options = {});
[[nodiscard]] MultiStationAnalysis
analyzeStations(const std::vector<PolarimeterStation>& stations, const TensorVector& reference_state, const AnalysisOptions& options = {});
[[nodiscard]] NominalPyyResult
analyzeNominalPyy(const std::vector<PolarimeterStation>& stations, double magnitude, const AnalysisOptions& options = {});
[[nodiscard]] DenseMatrix nullSpace(const IdentifiabilityResult& result);
[[nodiscard]] int
nullIntersectionDimension(const DenseMatrix& first_response, const DenseMatrix& second_response, const RankThreshold& threshold = {});
[[nodiscard]] std::vector<double>
nullSpacePrincipalAnglesDegrees(const DenseMatrix& first_response, const DenseMatrix& second_response, const RankThreshold& threshold = {});

void writeIdentifiabilityJson(const std::filesystem::path& path,
                              const std::string& scenario_name,
                              const std::string& study_name,
                              const std::vector<PolarimeterChannelResponse>& channels,
                              const TensorVector& state,
                              const IdentifiabilityResult& identifiability,
                              const FisherInformation& fisher,
                              const AnalysisOptions& options,
                              const std::vector<std::pair<std::string, std::string>>& metadata = {});
void writeMatrixCsv(const std::filesystem::path& path, const DenseMatrix& matrix);
void writeNominalPyyJson(const std::filesystem::path& path,
                         const std::string& scenario_name,
                         double magnitude,
                         const NominalPyyResult& result,
                         const AnalysisOptions& options,
                         std::size_t station_count);

}
