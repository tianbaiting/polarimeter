#pragma once

#include "dpolar/acceptance.hpp"
#include "dpolar/counts.hpp"
#include "dpolar/energy_loss.hpp"
#include "dpolar/inference.hpp"
#include "dpolar/plotting.hpp"

#include <filesystem>

namespace dpolar {

enum class LayoutPreset {
    Custom,
    Sekiguchi
};

enum class RatioMode {
    Deuteron,
    Proton,
    Coincidence
};

class AnalysisSession {
public:
    explicit AnalysisSession(ScenarioConfig scenario);

    [[nodiscard]] const ScenarioConfig& scenario() const noexcept;

    AnalysisArtifacts runTransformValidation(const std::filesystem::path& output_root) const;
    AnalysisArtifacts runLayoutOverlay(LayoutPreset preset, const std::filesystem::path& output_root) const;
    AnalysisArtifacts runEnergyPlot(const std::filesystem::path& output_root) const;
    AnalysisArtifacts runRatioScan(RatioMode mode, const std::filesystem::path& output_root) const;
    AnalysisArtifacts runLrudScan(const std::filesystem::path& output_root) const;
    AnalysisArtifacts runLrudScan(LrudObservable observable, const std::filesystem::path& output_root) const;
    AnalysisArtifacts runCoincidenceScan(const std::filesystem::path& output_root) const;
    AnalysisArtifacts runCoincidenceTotalScan(const std::filesystem::path& output_root) const;
    AnalysisArtifacts runCrossSectionScan(const std::filesystem::path& output_root) const;
    AnalysisArtifacts runEnergyLossScan(const std::filesystem::path& output_root) const;
    AnalysisArtifacts runBatchWorkflow(const std::filesystem::path& output_root) const;

private:
    AnalysisArtifacts runRatioScanSingleDuration(RatioMode mode, const std::filesystem::path& analysis_dir) const;
    AnalysisArtifacts runLrudScanSingleDuration(
        LrudObservable observable,
        const std::filesystem::path& analysis_dir) const;
    AnalysisArtifacts runCoincidenceScanSingleDuration(const std::filesystem::path& analysis_dir) const;
    AnalysisArtifacts runCoincidenceTotalScanSingleDuration(const std::filesystem::path& analysis_dir) const;

    ScenarioConfig scenario_;
    ElasticDpKinematics kinematics_;
    ObservableTableRepository observables_;
    CountRateCalculator counts_;
    EnergyLossModel energy_loss_;
};

}  // namespace dpolar
