#pragma once

#include "dpolar/inference.hpp"
#include "dpolar/plotting.hpp"

#include <filesystem>
#include <optional>
#include <string>

namespace dpolar {

AnalysisArtifacts runPzzInferencePlot(
    const PolarizationInference& inference,
    PzzObservable observable,
    double count,
    const std::optional<double>& count2,
    const std::string& case_label,
    const std::filesystem::path& output_root);

AnalysisArtifacts runPyyInferencePlot(
    const PolarizationInference& inference,
    LrudObservable observable,
    double count_lr,
    double count_ud,
    const std::string& case_label,
    const std::filesystem::path& output_root);

}  // namespace dpolar
