#pragma once

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct dpolar_scattering_solution_t {
    double deuteron_theta_lab_rad;
    double deuteron_phi_lab_rad;
    double deuteron_kinetic_energy_mev;
    double proton_theta_lab_rad;
    double proton_phi_lab_rad;
    double proton_kinetic_energy_mev;
} dpolar_scattering_solution_t;

int dpolar_scatter(
    const char* scenario_path,
    double theta_cm_rad,
    double phi_cm_rad,
    dpolar_scattering_solution_t* output,
    char* error_buffer,
    size_t error_buffer_size);

int dpolar_deuteron_cm_from_lab(
    const char* scenario_path,
    double theta_lab_rad,
    double* forward_cm_rad,
    double* backward_cm_rad,
    char* error_buffer,
    size_t error_buffer_size);

int dpolar_proton_cm_from_lab(
    const char* scenario_path,
    double theta_lab_rad,
    double* proton_cm_rad,
    char* error_buffer,
    size_t error_buffer_size);

int dpolar_proton_lab_from_deuteron_cm(
    const char* scenario_path,
    double theta_cm_rad,
    double* proton_lab_rad,
    char* error_buffer,
    size_t error_buffer_size);

#ifdef __cplusplus
}
#endif
