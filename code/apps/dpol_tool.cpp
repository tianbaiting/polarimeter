#include "dpolar/analysis.hpp"
#include "dpolar/config.hpp"
#include "dpolar/inference.hpp"
#include "dpolar/inference_plot.hpp"

#include "TROOT.h"

#include <cmath>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
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

double requireDoubleValue(int& index, const int argc, char* argv[]) {
    return std::stod(requireValue(index, argc, argv));
}

bool isNearlyInteger(const double value) {
    return std::abs(value - std::round(value)) <= 1.0e-9;
}

const char* pzzObservableLabel(const dpolar::PzzObservable observable) {
    switch (observable) {
        case dpolar::PzzObservable::Proton:
            return "proton";
        case dpolar::PzzObservable::Deuteron:
            return "deuteron";
        case dpolar::PzzObservable::Coincidence:
            return "coincidence";
    }
    throw std::runtime_error("Unsupported pzz observable");
}

dpolar::PzzObservable parsePzzObservable(const std::string& observable) {
    if (observable == "proton") {
        return dpolar::PzzObservable::Proton;
    }
    if (observable == "deuteron") {
        return dpolar::PzzObservable::Deuteron;
    }
    if (observable == "coincidence") {
        return dpolar::PzzObservable::Coincidence;
    }
    throw std::runtime_error("pzz observable must be proton, deuteron, or coincidence");
}

const char* lrudObservableLabel(const dpolar::LrudObservable observable) {
    switch (observable) {
        case dpolar::LrudObservable::Proton:
            return "proton";
        case dpolar::LrudObservable::Coincidence:
            return "coincidence";
    }
    throw std::runtime_error("Unsupported LRUD observable");
}

dpolar::LrudObservable parseLrudObservable(const std::string& observable) {
    if (observable == "proton") {
        return dpolar::LrudObservable::Proton;
    }
    if (observable == "coincidence") {
        return dpolar::LrudObservable::Coincidence;
    }
    throw std::runtime_error("LRUD observable must be proton or coincidence");
}

dpolar::RatioMode parseRatioMode(const std::string& mode) {
    if (mode == "proton") {
        return dpolar::RatioMode::Proton;
    }
    if (mode == "deuteron") {
        return dpolar::RatioMode::Deuteron;
    }
    if (mode == "coincidence") {
        return dpolar::RatioMode::Coincidence;
    }
    throw std::runtime_error("ratio mode must be proton, deuteron, or coincidence");
}

void printPolarizationEstimate(
    const dpolar::PolarizationEstimate& estimate,
    const dpolar::ScenarioConfig& scenario) {
    std::cout << std::fixed << std::setprecision(10);
    std::cout << "scan_lower_bound=" << scenario.scan.polarization_min << '\n';
    std::cout << "scan_upper_bound=" << scenario.scan.polarization_max << '\n';
    std::cout << "estimate=" << estimate.estimate << '\n';
    std::cout << "sigma_mle=" << estimate.sigma_mle << '\n';
    std::cout << "ci68_low=" << estimate.ci68.low << '\n';
    std::cout << "ci68_high=" << estimate.ci68.high << '\n';
    std::cout << "ci95_low=" << estimate.ci95.low << '\n';
    std::cout << "ci95_high=" << estimate.ci95.high << '\n';
    std::cout << std::boolalpha;
    std::cout << "at_lower_bound=" << estimate.at_lower_bound << '\n';
    std::cout << "at_upper_bound=" << estimate.at_upper_bound << '\n';
    std::cout << std::noboolalpha;
    std::cout << "loglikelihood_max=" << estimate.loglikelihood_max << '\n';
}

void printUsage() {
    std::cout
        << "Usage: dpol_tool <command> --scenario <path> [--preset custom|sekiguchi] [--mode deuteron|proton|coincidence] [--observable proton|deuteron|coincidence] [--count <value>] [--count2 <value>] [--count-lr <value>] [--count-ud <value>] [--case-label <label>] [--output-dir <path>]\n"
        << "Commands: validate-transform, layout, energy, ratio, lrud, coincidence, coincidence-total, cross-section, energy-loss, infer-pzz, infer-pyy, infer-pzz-plot, infer-pyy-plot\n";
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
        std::string observable = "proton";
        std::string case_label;
        double count = std::numeric_limits<double>::quiet_NaN();
        double count2 = std::numeric_limits<double>::quiet_NaN();
        double count_lr = std::numeric_limits<double>::quiet_NaN();
        double count_ud = std::numeric_limits<double>::quiet_NaN();

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
            } else if (argument == "--observable") {
                observable = requireValue(index, argc, argv);
            } else if (argument == "--count") {
                count = requireDoubleValue(index, argc, argv);
            } else if (argument == "--count2") {
                count2 = requireDoubleValue(index, argc, argv);
            } else if (argument == "--count-lr") {
                count_lr = requireDoubleValue(index, argc, argv);
            } else if (argument == "--count-ud") {
                count_ud = requireDoubleValue(index, argc, argv);
            } else if (argument == "--case-label") {
                case_label = requireValue(index, argc, argv);
            } else {
                throw std::runtime_error("Unknown argument: " + argument);
            }
        }

        const dpolar::ScenarioConfig scenario = dpolar::loadScenarioConfig(scenario_path);
        if (command == "infer-pzz") {
            if (!std::isfinite(count)) {
                throw std::runtime_error("infer-pzz requires --count");
            }

            const dpolar::PzzObservable pzz_observable = parsePzzObservable(observable);
            dpolar::PolarizationInference inference(scenario);
            const bool use_pair_counts = std::isfinite(count2);
            const dpolar::PolarizationEstimate estimate = use_pair_counts
                                                             ? inference.inferPzzFromCounts(pzz_observable, count, count2)
                                                             : inference.inferPzzFromTotalCount(pzz_observable, count);
            std::cout << "parameter=pzz\n";
            std::cout << "observable=" << pzzObservableLabel(pzz_observable) << '\n';
            std::cout << "estimator=" << (use_pair_counts ? "pair_binomial" : "absolute_poisson") << '\n';
            std::cout << std::boolalpha;
            std::cout << "input_counts_integer=" << (isNearlyInteger(count) && (!use_pair_counts || isNearlyInteger(count2))) << '\n';
            std::cout << std::noboolalpha;
            std::cout << "count=" << count << '\n';
            if (use_pair_counts) {
                std::cout << "count2=" << count2 << '\n';
            }
            printPolarizationEstimate(estimate, scenario);
            return 0;
        }

        if (command == "infer-pzz-plot") {
            if (!std::isfinite(count)) {
                throw std::runtime_error("infer-pzz-plot requires --count");
            }

            const dpolar::PzzObservable pzz_observable = parsePzzObservable(observable);
            dpolar::PolarizationInference inference(scenario);
            const dpolar::AnalysisArtifacts artifacts =
                dpolar::runPzzInferencePlot(
                    inference,
                    pzz_observable,
                    count,
                    std::isfinite(count2) ? std::optional<double> {count2} : std::nullopt,
                    case_label,
                    output_dir);
            std::cout << "Output directory: " << artifacts.output_dir << '\n';
            for (const dpolar::SummaryEntry& entry : artifacts.summary) {
                std::cout << entry.key << '=' << entry.value << '\n';
            }
            return 0;
        }

        if (command == "infer-pyy") {
            if (!std::isfinite(count_lr) || !std::isfinite(count_ud)) {
                throw std::runtime_error("infer-pyy requires --count-lr and --count-ud");
            }

            const dpolar::LrudObservable lrud_observable = parseLrudObservable(observable);
            dpolar::PolarizationInference inference(scenario);
            const dpolar::PolarizationEstimate estimate =
                inference.inferPyyFromLrudCounts(lrud_observable, count_lr, count_ud);
            std::cout << "parameter=pyy\n";
            std::cout << "observable=" << lrudObservableLabel(lrud_observable) << '\n';
            std::cout << "estimator=pair_binomial\n";
            std::cout << std::boolalpha;
            std::cout << "input_counts_integer=" << (isNearlyInteger(count_lr) && isNearlyInteger(count_ud)) << '\n';
            std::cout << std::noboolalpha;
            std::cout << "count_lr=" << count_lr << '\n';
            std::cout << "count_ud=" << count_ud << '\n';
            printPolarizationEstimate(estimate, scenario);
            return 0;
        }

        if (command == "infer-pyy-plot") {
            if (!std::isfinite(count_lr) || !std::isfinite(count_ud)) {
                throw std::runtime_error("infer-pyy-plot requires --count-lr and --count-ud");
            }

            const dpolar::LrudObservable lrud_observable = parseLrudObservable(observable);
            dpolar::PolarizationInference inference(scenario);
            const dpolar::AnalysisArtifacts artifacts =
                dpolar::runPyyInferencePlot(inference, lrud_observable, count_lr, count_ud, case_label, output_dir);
            std::cout << "Output directory: " << artifacts.output_dir << '\n';
            for (const dpolar::SummaryEntry& entry : artifacts.summary) {
                std::cout << entry.key << '=' << entry.value << '\n';
            }
            return 0;
        }

        dpolar::AnalysisSession session(scenario);
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
            const dpolar::RatioMode ratio_mode = parseRatioMode(mode);
            artifacts = session.runRatioScan(ratio_mode, output_dir);
        } else if (command == "lrud") {
            artifacts = session.runLrudScan(parseLrudObservable(observable), output_dir);
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
