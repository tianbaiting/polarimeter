#include "dpolar/config.hpp"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>

namespace dpolar {
namespace {

using IniMap = std::map<std::string, std::string>;

std::string trim(const std::string& input) {
    const auto first = std::find_if_not(input.begin(), input.end(), [](const unsigned char value) {
        return std::isspace(value) != 0;
    });
    const auto last = std::find_if_not(input.rbegin(), input.rend(), [](const unsigned char value) {
        return std::isspace(value) != 0;
    }).base();
    if (first >= last) {
        return {};
    }
    return std::string(first, last);
}

IniMap parseIni(const std::filesystem::path& path) {
    std::ifstream input(path);
    if (!input.is_open()) {
        throw std::runtime_error("Unable to open scenario file: " + path.string());
    }

    IniMap values;
    std::string line;
    std::string current_section;
    while (std::getline(input, line)) {
        const std::string trimmed = trim(line);
        if (trimmed.empty() || trimmed.starts_with('#') || trimmed.starts_with(';')) {
            continue;
        }
        if (trimmed.front() == '[' && trimmed.back() == ']') {
            current_section = trim(trimmed.substr(1, trimmed.size() - 2));
            continue;
        }
        const auto equals_position = trimmed.find('=');
        if (equals_position == std::string::npos) {
            continue;
        }
        const std::string key = trim(trimmed.substr(0, equals_position));
        const std::string value = trim(trimmed.substr(equals_position + 1));
        values[current_section + "." + key] = value;
    }
    return values;
}

std::string requireString(const IniMap& values, const std::string& key) {
    const auto iterator = values.find(key);
    if (iterator == values.end()) {
        throw std::runtime_error("Missing scenario key: " + key);
    }
    return iterator->second;
}

std::string getString(const IniMap& values, const std::string& key, const std::string& fallback) {
    const auto iterator = values.find(key);
    return iterator == values.end() ? fallback : iterator->second;
}

double getDouble(const IniMap& values, const std::string& key, const double fallback) {
    const auto iterator = values.find(key);
    if (iterator == values.end()) {
        return fallback;
    }
    return std::stod(iterator->second);
}

int getInt(const IniMap& values, const std::string& key, const int fallback) {
    const auto iterator = values.find(key);
    if (iterator == values.end()) {
        return fallback;
    }
    return std::stoi(iterator->second);
}

std::vector<double> parseDoubleList(const std::string& raw) {
    std::vector<double> values;
    std::stringstream stream(raw);
    std::string token;
    while (std::getline(stream, token, ',')) {
        const std::string stripped = trim(token);
        if (!stripped.empty()) {
            values.push_back(std::stod(stripped));
        }
    }
    if (values.empty()) {
        values.push_back(std::stod(trim(raw)));
    }
    return values;
}

std::vector<double> getDoubleList(const IniMap& values, const std::string& key, const std::vector<double>& fallback) {
    const auto iterator = values.find(key);
    if (iterator == values.end()) {
        return fallback;
    }
    return parseDoubleList(iterator->second);
}

std::filesystem::path resolvePath(const std::filesystem::path& base, const std::string& raw_path) {
    const std::filesystem::path path(raw_path);
    if (path.is_absolute()) {
        return path;
    }
    return std::filesystem::weakly_canonical(base / path);
}

std::vector<double> broadcast(const std::vector<double>& values, const std::size_t count) {
    if (values.size() == count) {
        return values;
    }
    if (values.size() == 1U) {
        return std::vector<double>(count, values.front());
    }
    throw std::runtime_error("Unable to broadcast detector parameter list to requested size");
}

std::vector<DetectorArm> makeArms(
    const std::vector<double>& theta_deg,
    const double distance_mm,
    const std::vector<double>& width_theta_mm,
    const std::vector<double>& width_phi_mm) {
    const std::vector<double> theta_widths = broadcast(width_theta_mm, theta_deg.size());
    const std::vector<double> phi_widths = broadcast(width_phi_mm, theta_deg.size());

    std::vector<DetectorArm> arms;
    arms.reserve(theta_deg.size());
    for (std::size_t index = 0; index < theta_deg.size(); ++index) {
        // [EN] Broadcast scalar widths into full detector arrays so geometry presets stay concise / [CN] 将标量宽度广播成完整阵列，便于保持几何预设简洁
        arms.push_back(DetectorArm {
            theta_deg[index],
            distance_mm,
            theta_widths[index],
            phi_widths[index],
        });
    }
    return arms;
}

}  // namespace

ScenarioConfig loadScenarioConfig(const std::filesystem::path& scenario_path) {
    const std::filesystem::path absolute_path = std::filesystem::weakly_canonical(scenario_path);
    const IniMap values = parseIni(absolute_path);
    const std::filesystem::path base_dir = absolute_path.parent_path();

    ScenarioConfig scenario;
    scenario.scenario_path = absolute_path;
    scenario.project_root = std::filesystem::weakly_canonical(base_dir / "..");
    scenario.scenario_name = getString(values, "meta.scenario_name", absolute_path.stem().string());

    scenario.beam.deuteron_mass_mev = getDouble(values, "beam.deuteron_mass_mev", scenario.beam.deuteron_mass_mev);
    scenario.beam.proton_mass_mev = getDouble(values, "beam.proton_mass_mev", scenario.beam.proton_mass_mev);
    scenario.beam.kinetic_energy_mev = getDouble(values, "beam.kinetic_energy_mev", scenario.beam.kinetic_energy_mev);

    scenario.target.areal_density_g_per_m2 = getDouble(values, "target.areal_density_g_per_m2", scenario.target.areal_density_g_per_m2);
    scenario.target.molar_mass_g_per_mol = getDouble(values, "target.molar_mass_g_per_mol", scenario.target.molar_mass_g_per_mol);
    scenario.target.avogadro = getDouble(values, "target.avogadro", scenario.target.avogadro);

    scenario.run.beam_current_amp = getDouble(values, "run.beam_current_amp", scenario.run.beam_current_amp);
    scenario.run.electron_charge_c = getDouble(values, "run.electron_charge_c", scenario.run.electron_charge_c);
    scenario.run.duration_s = getDouble(values, "run.duration_s", scenario.run.duration_s);
    scenario.run.duration_s_list = getDoubleList(values, "run.duration_s_list", {scenario.run.duration_s});
    if (scenario.run.duration_s_list.empty()) {
        scenario.run.duration_s_list.push_back(scenario.run.duration_s);
    }
    scenario.run.duration_s = scenario.run.duration_s_list.back();
    scenario.run.single_arm_sector_multiplier = getDouble(values, "run.single_arm_sector_multiplier", scenario.run.single_arm_sector_multiplier);
    scenario.run.lrud_sector_multiplier = getDouble(values, "run.lrud_sector_multiplier", scenario.run.lrud_sector_multiplier);
    scenario.run.coincidence_sector_multiplier = getDouble(values, "run.coincidence_sector_multiplier", scenario.run.coincidence_sector_multiplier);
    scenario.run.integration_steps = getInt(values, "run.integration_steps", scenario.run.integration_steps);

    scenario.scan.polarization_min = getDouble(values, "scan.polarization_min", scenario.scan.polarization_min);
    scenario.scan.polarization_max = getDouble(values, "scan.polarization_max", scenario.scan.polarization_max);
    scenario.scan.polarization_steps = getInt(values, "scan.polarization_steps", scenario.scan.polarization_steps);

    scenario.coverage.theta_bins = getInt(values, "coverage.theta_bins", scenario.coverage.theta_bins);
    scenario.coverage.phi_bins = getInt(values, "coverage.phi_bins", scenario.coverage.phi_bins);

    scenario.data.observables_dir = resolvePath(base_dir, requireString(values, "data.observables_dir"));
    scenario.data.cross_section_file = resolvePath(scenario.data.observables_dir, requireString(values, "data.cross_section_file"));
    scenario.data.tensor_file = resolvePath(scenario.data.observables_dir, requireString(values, "data.tensor_file"));
    scenario.data.energy_range_file = resolvePath(base_dir, requireString(values, "data.energy_range_file"));

    const std::vector<double> custom_proton_theta = getDoubleList(values, "custom_layout.proton_theta_lab_deg", {53.4, 11.2});
    const std::vector<double> custom_proton_theta_width = getDoubleList(values, "custom_layout.proton_width_theta_mm", {40.0, 40.0});
    const std::vector<double> custom_proton_phi_width = getDoubleList(values, "custom_layout.proton_width_phi_mm", {40.0, 40.0});
    const double custom_proton_distance = getDouble(values, "custom_layout.proton_distance_mm", 620.0);
    const std::vector<DetectorArm> proton_arms = makeArms(
        custom_proton_theta,
        custom_proton_distance,
        custom_proton_theta_width,
        custom_proton_phi_width);
    if (proton_arms.size() != scenario.custom_layout.proton_arms.size()) {
        throw std::runtime_error("custom_layout.proton_theta_lab_deg must define exactly two proton arms");
    }
    std::copy(proton_arms.begin(), proton_arms.end(), scenario.custom_layout.proton_arms.begin());
    scenario.custom_layout.deuteron_arm = DetectorArm {
        getDouble(values, "custom_layout.deuteron_theta_lab_deg", 20.9),
        getDouble(values, "custom_layout.deuteron_distance_mm", 400.0),
        getDouble(values, "custom_layout.deuteron_width_theta_mm", 40.0),
        getDouble(values, "custom_layout.deuteron_width_phi_mm", 40.0),
    };

    scenario.sekiguchi_layout.proton_arms = makeArms(
        getDoubleList(values, "sekiguchi_layout.proton_theta_lab_deg", {21.3, 26.1, 30.9, 35.8, 40.8, 45.0, 50.8, 55.9}),
        getDouble(values, "sekiguchi_layout.proton_distance_mm", 560.0),
        getDoubleList(values, "sekiguchi_layout.proton_width_theta_mm", {20.0}),
        getDoubleList(values, "sekiguchi_layout.proton_width_phi_mm", {20.0}));
    scenario.sekiguchi_layout.deuteron_arms = makeArms(
        getDoubleList(values, "sekiguchi_layout.deuteron_theta_lab_deg", {20.1, 22.7, 25.6, 29.3}),
        getDouble(values, "sekiguchi_layout.deuteron_distance_mm", 560.0),
        getDoubleList(values, "sekiguchi_layout.deuteron_width_theta_mm", {24.0, 24.0, 24.0, 50.0}),
        getDoubleList(values, "sekiguchi_layout.deuteron_width_phi_mm", {24.0, 24.0, 24.0, 50.0}));

    scenario.energy_loss.projectile_mass_number = getInt(values, "energy_loss.projectile_mass_number", scenario.energy_loss.projectile_mass_number);
    scenario.energy_loss.energy_min_mev_per_u = getDouble(values, "energy_loss.energy_min_mev_per_u", scenario.energy_loss.energy_min_mev_per_u);
    scenario.energy_loss.energy_max_mev_per_u = getDouble(values, "energy_loss.energy_max_mev_per_u", scenario.energy_loss.energy_max_mev_per_u);
    scenario.energy_loss.energy_step_mev_per_u = getDouble(values, "energy_loss.energy_step_mev_per_u", scenario.energy_loss.energy_step_mev_per_u);
    scenario.energy_loss.first_scintillator_um = getDouble(values, "energy_loss.first_scintillator_um", scenario.energy_loss.first_scintillator_um);
    scenario.energy_loss.second_scintillator_um = getDouble(values, "energy_loss.second_scintillator_um", scenario.energy_loss.second_scintillator_um);

    return scenario;
}

std::filesystem::path defaultOutputRoot(const ScenarioConfig& scenario) {
    return scenario.project_root / "output";
}

}  // namespace dpolar
