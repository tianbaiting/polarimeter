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

void printUsage() {
    std::cout
        << "Usage: dpol_tool <command> --scenario <path> [--preset custom|sekiguchi] [--mode deuteron|proton] [--output-dir <path>]\n"
        << "Commands: validate-transform, layout, energy, ratio, lrud, coincidence, coincidence-total, cross-section, energy-loss\n";
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        gROOT->SetBatch(kTRUE);

        if (argc < 2) {
            printUsage();
            return 1;
        }

        const std::string command = argv[1];
        std::filesystem::path scenario_path = std::filesystem::path(DPOLAR_SOURCE_DIR) / "config" / "default.ini";
        std::filesystem::path output_dir;
        std::string preset = "custom";
        std::string mode = "proton";

        for (int index = 2; index < argc; ++index) {
            const std::string argument = argv[index];
            if (argument == "--scenario") {
                scenario_path = requireValue(index, argc, argv);
            } else if (argument == "--output-dir") {
                output_dir = requireValue(index, argc, argv);
            } else if (argument == "--preset") {
                preset = requireValue(index, argc, argv);
            } else if (argument == "--mode") {
                mode = requireValue(index, argc, argv);
            } else {
                throw std::runtime_error("Unknown argument: " + argument);
            }
        }

        dpolar::AnalysisSession session(dpolar::loadScenarioConfig(scenario_path));
        dpolar::AnalysisArtifacts artifacts;
        if (command == "validate-transform") {
            artifacts = session.runTransformValidation(output_dir);
        } else if (command == "layout") {
            const dpolar::LayoutPreset layout_preset =
                preset == "sekiguchi" ? dpolar::LayoutPreset::Sekiguchi : dpolar::LayoutPreset::Custom;
            artifacts = session.runLayoutOverlay(layout_preset, output_dir);
        } else if (command == "energy") {
            artifacts = session.runEnergyPlot(output_dir);
        } else if (command == "ratio") {
            const dpolar::RatioMode ratio_mode =
                mode == "deuteron" ? dpolar::RatioMode::Deuteron : dpolar::RatioMode::Proton;
            artifacts = session.runRatioScan(ratio_mode, output_dir);
        } else if (command == "lrud") {
            artifacts = session.runLrudScan(output_dir);
        } else if (command == "coincidence") {
            artifacts = session.runCoincidenceScan(output_dir);
        } else if (command == "coincidence-total") {
            artifacts = session.runCoincidenceTotalScan(output_dir);
        } else if (command == "cross-section") {
            artifacts = session.runCrossSectionScan(output_dir);
        } else if (command == "energy-loss") {
            artifacts = session.runEnergyLossScan(output_dir);
        } else {
            printUsage();
            throw std::runtime_error("Unknown command: " + command);
        }

        std::cout << "Output directory: " << artifacts.output_dir << '\n';
        for (const dpolar::SummaryEntry& entry : artifacts.summary) {
            std::cout << entry.key << '=' << entry.value << '\n';
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
