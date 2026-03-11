#include "dpolar/plotting.hpp"

#include "TCanvas.h"

#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

namespace dpolar {
namespace {

std::string escapeJson(const std::string& value) {
    std::ostringstream escaped;
    for (const char character : value) {
        switch (character) {
        case '\\':
            escaped << "\\\\";
            break;
        case '"':
            escaped << "\\\"";
            break;
        case '\n':
            escaped << "\\n";
            break;
        default:
            escaped << character;
            break;
        }
    }
    return escaped.str();
}

}  // namespace

void saveCanvas(TCanvas& canvas, const std::filesystem::path& base_path_without_extension) {
    std::filesystem::create_directories(base_path_without_extension.parent_path());
    canvas.SaveAs((base_path_without_extension.string() + ".png").c_str());
    canvas.SaveAs((base_path_without_extension.string() + ".pdf").c_str());
}

void writeSummaryFiles(const AnalysisArtifacts& artifacts) {
    std::filesystem::create_directories(artifacts.output_dir);

    std::ofstream csv(artifacts.output_dir / "summary.csv");
    csv << "key,value\n";
    for (const SummaryEntry& entry : artifacts.summary) {
        csv << entry.key << ',' << entry.value << '\n';
    }

    std::ofstream json(artifacts.output_dir / "summary.json");
    json << "{\n";
    for (std::size_t index = 0; index < artifacts.summary.size(); ++index) {
        const SummaryEntry& entry = artifacts.summary[index];
        json << "  \"" << escapeJson(entry.key) << "\": \"" << escapeJson(entry.value) << '"';
        if (index + 1U != artifacts.summary.size()) {
            json << ',';
        }
        json << '\n';
    }
    json << "}\n";
}

std::filesystem::path analysisOutputDir(
    const std::filesystem::path& root_output,
    const std::string& scenario_name,
    const std::string& analysis_name) {
    return root_output / scenario_name / analysis_name;
}

}  // namespace dpolar
