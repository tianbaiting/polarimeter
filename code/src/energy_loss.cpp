#include "dpolar/energy_loss.hpp"

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace dpolar {
namespace {

double interpolateLinear(const std::vector<double>& x_values, const std::vector<double>& y_values, const double x) {
    if (x_values.size() != y_values.size() || x_values.empty()) {
        throw std::runtime_error("Interpolation vectors are inconsistent");
    }
    if (x <= x_values.front()) {
        return y_values.front();
    }
    if (x >= x_values.back()) {
        return y_values.back();
    }
    for (std::size_t index = 1; index < x_values.size(); ++index) {
        if (x <= x_values[index]) {
            const double x0 = x_values[index - 1];
            const double x1 = x_values[index];
            const double y0 = y_values[index - 1];
            const double y1 = y_values[index];
            const double fraction = (x - x0) / (x1 - x0);
            return y0 + fraction * (y1 - y0);
        }
    }
    return y_values.back();
}

}  // namespace

EnergyLossModel::EnergyLossModel(const ScenarioConfig& scenario)
    : config_(scenario.energy_loss) {
    std::ifstream input(scenario.data.energy_range_file);
    if (!input.is_open()) {
        throw std::runtime_error("Unable to open energy-loss range table: " + scenario.data.energy_range_file.string());
    }

    std::string line;
    for (int header_index = 0; header_index < 3; ++header_index) {
        std::getline(input, line);
    }

    while (std::getline(input, line)) {
        std::istringstream row(line);
        std::vector<double> columns;
        double value {};
        while (row >> value) {
            columns.push_back(value);
        }
        if (columns.size() >= 10U) {
            // [EN] Preserve the original macro choice of the improved ATIMA range column to stay numerically compatible / [CN] 保留原宏中改进版 ATIMA 射程列的选择，以保持数值兼容
            energy_mev_per_u_.push_back(columns[0]);
            range_um_.push_back(columns[9]);
        }
    }

    if (energy_mev_per_u_.empty()) {
        throw std::runtime_error("Energy-loss range table produced no usable samples");
    }
}

double EnergyLossModel::energyLossMev(const int mass_number, const double energy_per_u_mev, const double thickness_um) const {
    const double total_energy_mev = energy_per_u_mev * static_cast<double>(mass_number);
    const double initial_range_um = interpolateLinear(energy_mev_per_u_, range_um_, energy_per_u_mev);
    if (initial_range_um <= thickness_um) {
        return total_energy_mev;
    }
    const double residual_range_um = initial_range_um - thickness_um;
    const double residual_energy_per_u_mev = interpolateLinear(range_um_, energy_mev_per_u_, residual_range_um);
    return total_energy_mev - residual_energy_per_u_mev * static_cast<double>(mass_number);
}

std::vector<SamplePoint> EnergyLossModel::firstScintillatorCurve() const {
    std::vector<SamplePoint> samples;
    for (double energy = config_.energy_min_mev_per_u; energy <= config_.energy_max_mev_per_u + 1.0e-9; energy += config_.energy_step_mev_per_u) {
        samples.push_back(SamplePoint {
            energy,
            energyLossMev(config_.projectile_mass_number, energy, config_.first_scintillator_um),
            0.0,
        });
    }
    return samples;
}

std::vector<SamplePoint> EnergyLossModel::secondScintillatorCurve() const {
    std::vector<SamplePoint> samples;
    for (double energy = config_.energy_min_mev_per_u; energy <= config_.energy_max_mev_per_u + 1.0e-9; energy += config_.energy_step_mev_per_u) {
        const double first_loss_mev = energyLossMev(config_.projectile_mass_number, energy, config_.first_scintillator_um);
        const double residual_energy_mev_per_u = energy - first_loss_mev / static_cast<double>(config_.projectile_mass_number);
        samples.push_back(SamplePoint {
            energy,
            energyLossMev(config_.projectile_mass_number, residual_energy_mev_per_u, config_.second_scintillator_um),
            0.0,
        });
    }
    return samples;
}

}  // namespace dpolar
