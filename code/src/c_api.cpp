#include "dpolar/c_api.h"

#include "dpolar/config.hpp"
#include "dpolar/kinematics.hpp"

#include <cstring>
#include <exception>
#include <string>

namespace {

void setError(char* buffer, const size_t size, const std::string& message) {
    if (buffer == nullptr || size == 0U) {
        return;
    }
    std::strncpy(buffer, message.c_str(), size - 1U);
    buffer[size - 1U] = '\0';
}

}  // namespace

int dpolar_scatter(
    const char* scenario_path,
    const double theta_cm_rad,
    const double phi_cm_rad,
    dpolar_scattering_solution_t* output,
    char* error_buffer,
    const size_t error_buffer_size) {
    try {
        if (scenario_path == nullptr || output == nullptr) {
            throw std::runtime_error("scenario_path and output must be non-null");
        }
        const dpolar::ScenarioConfig scenario = dpolar::loadScenarioConfig(scenario_path);
        const dpolar::ElasticDpKinematics kinematics(scenario.beam);
        const dpolar::ScatteringSolution solution = kinematics.scatter(theta_cm_rad, phi_cm_rad);
        output->deuteron_theta_lab_rad = solution.deuteron.theta_lab_rad;
        output->deuteron_phi_lab_rad = solution.deuteron.phi_lab_rad;
        output->deuteron_kinetic_energy_mev = solution.deuteron.kinetic_energy_mev;
        output->proton_theta_lab_rad = solution.proton.theta_lab_rad;
        output->proton_phi_lab_rad = solution.proton.phi_lab_rad;
        output->proton_kinetic_energy_mev = solution.proton.kinetic_energy_mev;
        setError(error_buffer, error_buffer_size, "");
        return 0;
    } catch (const std::exception& error) {
        setError(error_buffer, error_buffer_size, error.what());
        return 1;
    }
}

int dpolar_deuteron_cm_from_lab(
    const char* scenario_path,
    const double theta_lab_rad,
    double* forward_cm_rad,
    double* backward_cm_rad,
    char* error_buffer,
    const size_t error_buffer_size) {
    try {
        if (scenario_path == nullptr || forward_cm_rad == nullptr || backward_cm_rad == nullptr) {
            throw std::runtime_error("scenario_path and output pointers must be non-null");
        }
        const dpolar::ScenarioConfig scenario = dpolar::loadScenarioConfig(scenario_path);
        const dpolar::ElasticDpKinematics kinematics(scenario.beam);
        const auto values = kinematics.deuteronCmFromLab(theta_lab_rad);
        *forward_cm_rad = values.first;
        *backward_cm_rad = values.second;
        setError(error_buffer, error_buffer_size, "");
        return 0;
    } catch (const std::exception& error) {
        setError(error_buffer, error_buffer_size, error.what());
        return 1;
    }
}

int dpolar_proton_cm_from_lab(
    const char* scenario_path,
    const double theta_lab_rad,
    double* proton_cm_rad,
    char* error_buffer,
    const size_t error_buffer_size) {
    try {
        if (scenario_path == nullptr || proton_cm_rad == nullptr) {
            throw std::runtime_error("scenario_path and output pointer must be non-null");
        }
        const dpolar::ScenarioConfig scenario = dpolar::loadScenarioConfig(scenario_path);
        const dpolar::ElasticDpKinematics kinematics(scenario.beam);
        *proton_cm_rad = kinematics.protonCmFromLab(theta_lab_rad);
        setError(error_buffer, error_buffer_size, "");
        return 0;
    } catch (const std::exception& error) {
        setError(error_buffer, error_buffer_size, error.what());
        return 1;
    }
}

int dpolar_proton_lab_from_deuteron_cm(
    const char* scenario_path,
    const double theta_cm_rad,
    double* proton_lab_rad,
    char* error_buffer,
    const size_t error_buffer_size) {
    try {
        if (scenario_path == nullptr || proton_lab_rad == nullptr) {
            throw std::runtime_error("scenario_path and output pointer must be non-null");
        }
        const dpolar::ScenarioConfig scenario = dpolar::loadScenarioConfig(scenario_path);
        const dpolar::ElasticDpKinematics kinematics(scenario.beam);
        *proton_lab_rad = kinematics.protonLabFromDeuteronCm(theta_cm_rad);
        setError(error_buffer, error_buffer_size, "");
        return 0;
    } catch (const std::exception& error) {
        setError(error_buffer, error_buffer_size, error.what());
        return 1;
    }
}
