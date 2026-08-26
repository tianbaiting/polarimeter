#include "dpolar/analysis.hpp"
#include "dpolar/config.hpp"
#include "dpolar/identifiability.hpp"
#include "dpolar/inference.hpp"
#include "dpolar/inference_plot.hpp"
#include "dpolar/observables.hpp"
#include "dpolar/tensor.hpp"

#include "TROOT.h"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <numbers>
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

dpolar::ChannelSelection parseChannelSelection(const std::string& selection) {
    if (selection == "ideal") {
        return dpolar::ChannelSelection::IdealOneTheta;
    }
    if (selection == "one-theta") {
        return dpolar::ChannelSelection::ProtonOneTheta;
    }
    if (selection == "proton" || selection == "proton-singles") {
        return dpolar::ChannelSelection::ProtonSingles;
    }
    if (selection == "deuteron" || selection == "deuteron-singles") {
        return dpolar::ChannelSelection::DeuteronSingles;
    }
    if (selection == "deuteron-branches") {
        return dpolar::ChannelSelection::DeuteronBranches;
    }
    if (selection == "coincidence" || selection == "coincidences") {
        return dpolar::ChannelSelection::Coincidences;
    }
    if (selection == "current") {
        return dpolar::ChannelSelection::CurrentProduction;
    }
    throw std::runtime_error("selection must be ideal, one-theta, proton, deuteron, "
                             "deuteron-branches, coincidence, or current");
}

dpolar::NormalizationModel parseNormalizationModel(const std::string& model) {
    if (model == "known") {
        return dpolar::NormalizationModel::Known;
    }
    if (model == "global") {
        return dpolar::NormalizationModel::Global;
    }
    if (model == "per-station") {
        return dpolar::NormalizationModel::PerStation;
    }
    if (model == "per-angle") {
        return dpolar::NormalizationModel::PerAngle;
    }
    throw std::runtime_error("normalization must be known, global, per-station, or per-angle");
}

dpolar::VectorPolarization rotationAxis(const std::string& axis) {
    if (axis == "x") {
        return {1.0, 0.0, 0.0};
    }
    if (axis == "y") {
        return {0.0, 1.0, 0.0};
    }
    if (axis == "z") {
        return {0.0, 0.0, 1.0};
    }
    throw std::runtime_error("rotation axis must be x, y, or z");
}

std::vector<dpolar::PolarimeterChannelResponse> selectedChannels(const dpolar::ScenarioConfig& scenario,
                                                                 const dpolar::ChannelSelection selection) {
    if (selection != dpolar::ChannelSelection::IdealOneTheta) {
        return dpolar::buildScenarioChannels(scenario, selection);
    }
    const dpolar::ObservableTableRepository observables(scenario);
    return dpolar::buildIdealFourArmRing(dpolar::cartesianAnalyzingPowers(observables, 68.6));
}

double smallestNonzero(const std::vector<double>& values, const double threshold) {
    double result = std::numeric_limits<double>::infinity();
    for (const double value : values) {
        if (value > threshold) {
            result = std::min(result, value);
        }
    }
    return std::isfinite(result) ? result : 0.0;
}

void printIdentifiabilitySummary(const dpolar::IdentifiabilityResult& identifiability,
                                 const dpolar::FisherInformation& fisher,
                                 const std::filesystem::path& output_dir) {
    std::cout << std::setprecision(12);
    std::cout << "raw_rank=" << identifiability.svd.rank << '\n';
    std::cout << "effective_rank=" << fisher.effective_rank << '\n';
    std::cout << "condition_number=" << identifiability.svd.condition_number << '\n';
    std::cout << "nullity=" << identifiability.null_directions.size() << '\n';
    std::cout << "singular_values=";
    for (std::size_t index = 0; index < identifiability.svd.singular_values.size(); ++index) {
        std::cout << (index == 0U ? "" : ",") << identifiability.svd.singular_values[index];
    }
    std::cout << '\n';
    std::cout << "output_dir=" << output_dir << '\n';
}

void printPolarizationEstimate(const dpolar::PolarizationEstimate& estimate, const dpolar::ScenarioConfig& scenario) {
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
    std::cout << "Usage: dpol_tool <command> --scenario <path> [--preset "
                 "custom|sekiguchi] [--mode deuteron|proton|coincidence] "
                 "[--observable proton|deuteron|coincidence] [--count <value>] "
                 "[--count2 <value>] [--count-lr <value>] [--count-ud <value>] "
                 "[--case-label <label>] [--output-dir <path>]\n"
              << "Commands: validate-transform, layout, energy, ratio, lrud, "
                 "coincidence, coincidence-total, cross-section, energy-loss, "
                 "infer-pzz, infer-pyy, infer-pzz-plot, infer-pyy-plot, rank, "
                 "fisher, two-station, rotation-scan, nominal-pyy\n";
}

} // namespace

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
        std::string channel_selection = "current";
        std::string normalization = "known";
        std::string rotation_axis = "y";
        double rotation_deg = 20.0;
        double rotation_step_deg = 2.0;
        double rank_relative_tolerance = 1.0e-10;
        double rank_absolute_tolerance = 1.0e-12;
        double pxx_minus_pyy = 0.0;
        double pxy = 0.0;
        double pxz = 0.0;
        double pyz = 0.0;
        double pzz = 0.0;
        double nominal_pyy = 0.8;
        int station_count = 1;
        bool relative_efficiencies = false;
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
            } else if (argument == "--selection") {
                channel_selection = requireValue(index, argc, argv);
            } else if (argument == "--normalization") {
                normalization = requireValue(index, argc, argv);
            } else if (argument == "--profile-normalization") {
                normalization = "global";
            } else if (argument == "--known-normalization" || argument == "--tensor-only") {
                normalization = argument == "--known-normalization" ? "known" : normalization;
            } else if (argument == "--relative-efficiencies") {
                relative_efficiencies = true;
            } else if (argument == "--rotation-axis") {
                rotation_axis = requireValue(index, argc, argv);
            } else if (argument == "--rotation-deg") {
                rotation_deg = requireDoubleValue(index, argc, argv);
            } else if (argument == "--rotation-step-deg") {
                rotation_step_deg = requireDoubleValue(index, argc, argv);
            } else if (argument == "--rank-relative-tol") {
                rank_relative_tolerance = requireDoubleValue(index, argc, argv);
            } else if (argument == "--rank-absolute-tol") {
                rank_absolute_tolerance = requireDoubleValue(index, argc, argv);
            } else if (argument == "--pxx-minus-pyy") {
                pxx_minus_pyy = requireDoubleValue(index, argc, argv);
            } else if (argument == "--pxy") {
                pxy = requireDoubleValue(index, argc, argv);
            } else if (argument == "--pxz") {
                pxz = requireDoubleValue(index, argc, argv);
            } else if (argument == "--pyz") {
                pyz = requireDoubleValue(index, argc, argv);
            } else if (argument == "--pzz") {
                pzz = requireDoubleValue(index, argc, argv);
            } else if (argument == "--nominal-pyy") {
                nominal_pyy = requireDoubleValue(index, argc, argv);
            } else if (argument == "--stations") {
                station_count = std::stoi(requireValue(index, argc, argv));
            } else {
                throw std::runtime_error("Unknown argument: " + argument);
            }
        }

        if (scenario_path == std::filesystem::path("current")) {
            scenario_path = std::filesystem::path(DPOLAR_SOURCE_DIR) / "config" / "current_tensor.ini";
        }
        const dpolar::ScenarioConfig scenario = dpolar::loadScenarioConfig(scenario_path);

        const bool identifiability_command =
            command == "rank" || command == "fisher" || command == "two-station" || command == "rotation-scan" || command == "nominal-pyy";
        if (identifiability_command) {
            if (!(rotation_step_deg > 0.0)) {
                throw std::runtime_error("rotation step must be positive");
            }
            if (station_count != 1 && station_count != 2) {
                throw std::runtime_error("stations must be 1 or 2");
            }
            const dpolar::ChannelSelection selection = parseChannelSelection(channel_selection);
            const std::vector<dpolar::PolarimeterChannelResponse> channels = selectedChannels(scenario, selection);
            dpolar::AnalysisOptions options;
            options.normalization = parseNormalizationModel(normalization);
            options.profile_relative_sector_efficiencies = relative_efficiencies;
            options.threshold.relative = rank_relative_tolerance;
            options.threshold.absolute = rank_absolute_tolerance;
            const dpolar::TensorVector state =
                dpolar::TensorPolarization::fromPhysical(dpolar::PhysicalTensorComponents{pxx_minus_pyy, pxy, pxz, pyz, pzz}).internal();
            if (output_dir.empty()) {
                output_dir = dpolar::defaultOutputRoot(scenario) / scenario.scenario_name / "tensor_identifiability" / command;
            }
            std::filesystem::create_directories(output_dir);

            const dpolar::PolarimeterStation first_station{"station1", channels, dpolar::identityMatrix(5U)};
            const dpolar::SpinRotation relative_rotation =
                dpolar::SpinRotation::axisAngle(rotationAxis(rotation_axis), rotation_deg * std::numbers::pi_v<double> / 180.0);
            const dpolar::PolarimeterStation second_station{"station2", channels, relative_rotation.tensorMap()};

            if (command == "rotation-scan") {
                const std::filesystem::path csv_path = output_dir / "rotation_scan.csv";
                std::ofstream csv(csv_path);
                if (!csv.is_open()) {
                    throw std::runtime_error("Unable to create rotation scan CSV");
                }
                csv << std::setprecision(17);
                csv << "rotation_axis,rotation_deg,raw_rank,effective_rank,smallest_"
                       "singular,smallest_nonzero_singular,condition_number,fisher_"
                       "pseudo_determinant,null_intersection_dimension,principal_"
                       "angles_deg\n";
                for (double angle = 0.0; angle <= 180.0 + 0.5 * rotation_step_deg; angle += rotation_step_deg) {
                    const dpolar::SpinRotation rotation =
                        dpolar::SpinRotation::axisAngle(rotationAxis(rotation_axis), angle * std::numbers::pi_v<double> / 180.0);
                    const dpolar::PolarimeterStation scanned_second{"station2", channels, rotation.tensorMap()};
                    const dpolar::MultiStationAnalysis result = dpolar::analyzeStations({first_station, scanned_second}, state, options);
                    csv << rotation_axis << ',' << angle << ',' << result.identifiability.svd.rank << ',' << result.fisher.effective_rank
                        << ',' << result.identifiability.svd.singular_values.back() << ','
                        << smallestNonzero(result.identifiability.svd.singular_values, result.identifiability.svd.threshold) << ','
                        << result.identifiability.svd.condition_number << ',' << result.fisher.pseudo_determinant << ','
                        << result.null_intersection_dimension << ",\"";
                    for (std::size_t index = 0; index < result.null_space_principal_angles_deg.size(); ++index) {
                        csv << (index == 0U ? "" : ";") << result.null_space_principal_angles_deg[index];
                    }
                    csv << "\"\n";
                }
                std::cout << "output_dir=" << output_dir << '\n';
                std::cout << "rotation_scan_csv=" << csv_path << '\n';
                return 0;
            }

            if (command == "nominal-pyy") {
                std::vector<dpolar::PolarimeterStation> stations{first_station};
                if (station_count == 2) {
                    stations.push_back(second_station);
                }
                const dpolar::NominalPyyResult result = dpolar::analyzeNominalPyy(stations, nominal_pyy, options);
                dpolar::writeNominalPyyJson(
                    output_dir / "summary.json", scenario.scenario_name, nominal_pyy, result, options, stations.size());
                dpolar::writeMatrixCsv(output_dir / "nominal_pyy_jacobian.csv", result.jacobian);
                dpolar::writeMatrixCsv(output_dir / "nominal_pyy_fisher_profiled.csv", result.fisher.profiled);
                std::cout << "effective_rank=" << result.fisher.effective_rank << '\n';
                std::cout << "sigma_PT=" << result.one_sigma[0] << '\n';
                std::cout << "sigma_tilt_x_rad=" << result.one_sigma[1] << '\n';
                std::cout << "sigma_tilt_z_rad=" << result.one_sigma[2] << '\n';
                std::cout << "output_dir=" << output_dir << '\n';
                return 0;
            }

            if (command == "two-station") {
                const dpolar::MultiStationAnalysis result = dpolar::analyzeStations({first_station, second_station}, state, options);
                std::vector<dpolar::PolarimeterChannelResponse> report_channels = channels;
                report_channels.insert(report_channels.end(), channels.begin(), channels.end());
                dpolar::writeIdentifiabilityJson(output_dir / "summary.json",
                                                 scenario.scenario_name,
                                                 "two_station",
                                                 report_channels,
                                                 state,
                                                 result.identifiability,
                                                 result.fisher,
                                                 options,
                                                 {{"rotation_axis", rotation_axis},
                                                  {"rotation_deg", std::to_string(rotation_deg)},
                                                  {"null_intersection_dimension", std::to_string(result.null_intersection_dimension)}});
                dpolar::writeMatrixCsv(output_dir / "response_matrix.csv", result.combined_response);
                dpolar::writeMatrixCsv(output_dir / "fisher_profiled.csv", result.fisher.profiled);
                printIdentifiabilitySummary(result.identifiability, result.fisher, output_dir);
                std::cout << "null_intersection_dimension=" << result.null_intersection_dimension << '\n';
                return 0;
            }

            const dpolar::IdentifiabilityResult identifiability =
                dpolar::analyzeIdentifiability(dpolar::responseMatrix(channels), options.threshold);
            const dpolar::FisherInformation fisher = dpolar::calculateFisherInformation(channels, state, options);
            dpolar::writeIdentifiabilityJson(output_dir / "summary.json",
                                             scenario.scenario_name,
                                             command,
                                             channels,
                                             state,
                                             identifiability,
                                             fisher,
                                             options,
                                             {{"selection", channel_selection},
                                              {"acceptance_model", scenario.geometry_contract.acceptance_model},
                                              {"geometry_source", scenario.geometry_contract.source_config.string()}});
            dpolar::writeMatrixCsv(output_dir / "response_matrix.csv", identifiability.response_matrix);
            dpolar::writeMatrixCsv(output_dir / "fisher_profiled.csv", fisher.profiled);
            printIdentifiabilitySummary(identifiability, fisher, output_dir);
            return 0;
        }
        if (command == "infer-pzz") {
            if (!std::isfinite(count)) {
                throw std::runtime_error("infer-pzz requires --count");
            }

            const dpolar::PzzObservable pzz_observable = parsePzzObservable(observable);
            dpolar::PolarizationInference inference(scenario);
            const bool use_pair_counts = std::isfinite(count2);
            const dpolar::PolarizationEstimate estimate = use_pair_counts ? inference.inferPzzFromCounts(pzz_observable, count, count2)
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
                dpolar::runPzzInferencePlot(inference,
                                            pzz_observable,
                                            count,
                                            std::isfinite(count2) ? std::optional<double>{count2} : std::nullopt,
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
            const dpolar::PolarizationEstimate estimate = inference.inferPyyFromLrudCounts(lrud_observable, count_lr, count_ud);
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
