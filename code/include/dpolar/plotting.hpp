#pragma once

#include "dpolar/types.hpp"

#include <filesystem>
#include <vector>

class TCanvas;

namespace dpolar {

struct AnalysisArtifacts {
    std::filesystem::path output_dir;
    std::vector<std::filesystem::path> files;
    std::vector<SummaryEntry> summary;
};

void saveCanvas(TCanvas& canvas, const std::filesystem::path& base_path_without_extension);
void writeSummaryFiles(const AnalysisArtifacts& artifacts);
std::filesystem::path analysisOutputDir(
    const std::filesystem::path& root_output,
    const std::string& scenario_name,
    const std::string& analysis_name);

}  // namespace dpolar
