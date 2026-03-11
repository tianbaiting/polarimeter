#pragma once

#include "dpolar/types.hpp"

#include <array>
#include <filesystem>
#include <string>
#include <vector>

namespace dpolar {

struct BeamConfig {
    double deuteron_mass_mev {1875.612};
    double proton_mass_mev {938.0};
    double kinetic_energy_mev {380.0};
};

struct TargetConfig {
    double areal_density_g_per_m2 {10000.0};
    double molar_mass_g_per_mol {14.0};
    double avogadro {6.02214076e23};
};

struct RunConfig {
    double beam_current_amp {1.6e-12};
    double electron_charge_c {1.602176634e-19};
    double duration_s {180.0 * 60.0};
    std::vector<double> duration_s_list {180.0 * 60.0};
    double single_arm_sector_multiplier {4.0};
    double lrud_sector_multiplier {2.0};
    double coincidence_sector_multiplier {1.0};
    int integration_steps {400};
};

struct ScanConfig {
    double polarization_min {0.0};
    double polarization_max {1.0};
    int polarization_steps {10};
};

struct CoverageConfig {
    int theta_bins {360};
    int phi_bins {360};
};

struct DataConfig {
    std::filesystem::path observables_dir;
    std::filesystem::path cross_section_file;
    std::filesystem::path tensor_file;
    std::filesystem::path energy_range_file;
};

struct CustomLayoutConfig {
    std::array<DetectorArm, 2> proton_arms {};
    DetectorArm deuteron_arm {};
};

struct SekiguchiLayoutConfig {
    std::vector<DetectorArm> proton_arms;
    std::vector<DetectorArm> deuteron_arms;
};

struct EnergyLossConfig {
    int projectile_mass_number {1};
    double energy_min_mev_per_u {0.0};
    double energy_max_mev_per_u {200.0};
    double energy_step_mev_per_u {1.0};
    double first_scintillator_um {20000.0};
    double second_scintillator_um {20000.0};
};

struct ScenarioConfig {
    std::string scenario_name {"default"};
    std::filesystem::path scenario_path;
    std::filesystem::path project_root;
    BeamConfig beam;
    TargetConfig target;
    RunConfig run;
    ScanConfig scan;
    CoverageConfig coverage;
    DataConfig data;
    CustomLayoutConfig custom_layout;
    SekiguchiLayoutConfig sekiguchi_layout;
    EnergyLossConfig energy_loss;
};

ScenarioConfig loadScenarioConfig(const std::filesystem::path& scenario_path);
std::filesystem::path defaultOutputRoot(const ScenarioConfig& scenario);

}  // namespace dpolar
