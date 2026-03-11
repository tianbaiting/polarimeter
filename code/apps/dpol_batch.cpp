#include "dpolar/analysis.hpp"
#include "dpolar/config.hpp"

#include "TROOT.h"

#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

std::string requireValue(int& index, const int argc, char* argv[]) {
    if (index + 1 >= argc) {
        throw std::runtime_error(std::string("Missing value for argument: ") + argv[index]);
    }
    ++index;
    return argv[index];
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        gROOT->SetBatch(kTRUE);

        std::filesystem::path scenario_path = std::filesystem::path(DPOLAR_SOURCE_DIR) / "config" / "default.ini";
        std::filesystem::path output_dir;
        std::string workflow = "full";

        for (int index = 1; index < argc; ++index) {
            const std::string argument = argv[index];
            if (argument == "--scenario") {
                scenario_path = requireValue(index, argc, argv);
            } else if (argument == "--output-dir") {
                output_dir = requireValue(index, argc, argv);
            } else if (argument == "--workflow") {
                workflow = requireValue(index, argc, argv);
            } else {
                throw std::runtime_error("Unknown argument: " + argument);
            }
        }

        if (workflow != "full") {
            throw std::runtime_error("Only the 'full' workflow is implemented");
        }

        dpolar::AnalysisSession session(dpolar::loadScenarioConfig(scenario_path));
        const dpolar::AnalysisArtifacts artifacts = session.runBatchWorkflow(output_dir);
        std::cout << "Batch output directory: " << artifacts.output_dir << '\n';
        for (const dpolar::SummaryEntry& entry : artifacts.summary) {
            std::cout << entry.key << '=' << entry.value << '\n';
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
