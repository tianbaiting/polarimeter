#include "dpolar/observables.hpp"

#include "TGraph.h"
#include "TSpline.h"

#include <algorithm>
#include <fstream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace dpolar {
namespace {

double clampAngle(const std::vector<double>& values, const double angle_deg) {
    if (values.empty()) {
        throw std::runtime_error("Observable table is empty");
    }
    if (angle_deg < values.front()) {
        return values.front();
    }
    if (angle_deg > values.back()) {
        return values.back();
    }
    return angle_deg;
}

}  // namespace

ObservableTableRepository::ObservableTableRepository(const ScenarioConfig& scenario) {
    {
        std::ifstream input(scenario.data.cross_section_file);
        if (!input.is_open()) {
            throw std::runtime_error("Unable to open cross-section table: " + scenario.data.cross_section_file.string());
        }

        std::string line;
        while (std::getline(input, line)) {
            std::istringstream row(line);
            double angle_deg {};
            double value_mb_per_sr {};
            if (row >> angle_deg >> value_mb_per_sr) {
                cross_section_angles_deg_.push_back(angle_deg);
                cross_section_values_mb_per_sr_.push_back(value_mb_per_sr);
            }
        }
    }

    {
        std::ifstream input(scenario.data.tensor_file);
        if (!input.is_open()) {
            throw std::runtime_error("Unable to open tensor table: " + scenario.data.tensor_file.string());
        }

        std::string line;
        std::getline(input, line);
        while (std::getline(input, line)) {
            std::istringstream row(line);
            std::vector<std::string> tokens;
            std::string token;
            while (row >> token) {
                tokens.push_back(token);
            }
            if (tokens.size() < 9U) {
                continue;
            }

            const double angle_deg = std::stod(tokens[0]);
            if (tokens[3] != "null" && tokens[4] != "null") {
                tensor_angles_deg_.push_back(angle_deg);
                tensor_t20_values_.push_back(std::stod(tokens[3]));
                tensor_t20_errors_.push_back(std::stod(tokens[4]));
            }
            if (tokens[7] != "null" && tokens[8] != "null") {
                tensor_t22_angles_deg_.push_back(angle_deg);
                tensor_t22_values_.push_back(std::stod(tokens[7]));
                tensor_t22_errors_.push_back(std::stod(tokens[8]));
            }
        }
    }

    if (cross_section_angles_deg_.empty() || tensor_angles_deg_.empty() || tensor_t22_values_.empty()) {
        throw std::runtime_error("Observable tables did not produce enough spline points");
    }

    cross_section_graph_ = std::make_unique<TGraph>(
        static_cast<int>(cross_section_angles_deg_.size()),
        cross_section_angles_deg_.data(),
        cross_section_values_mb_per_sr_.data());
    tensor_t20_graph_ = std::make_unique<TGraph>(
        static_cast<int>(tensor_angles_deg_.size()),
        tensor_angles_deg_.data(),
        tensor_t20_values_.data());
    tensor_t22_graph_ = std::make_unique<TGraph>(
        static_cast<int>(tensor_t22_angles_deg_.size()),
        tensor_t22_angles_deg_.data(),
        tensor_t22_values_.data());
    tensor_t20_error_graph_ = std::make_unique<TGraph>(
        static_cast<int>(tensor_angles_deg_.size()),
        tensor_angles_deg_.data(),
        tensor_t20_errors_.data());
    tensor_t22_error_graph_ = std::make_unique<TGraph>(
        static_cast<int>(tensor_t22_angles_deg_.size()),
        tensor_t22_angles_deg_.data(),
        tensor_t22_errors_.data());

    cross_section_spline_ = std::make_unique<TSpline3>("cross_section_spline", cross_section_graph_.get());
    tensor_t20_spline_ = std::make_unique<TSpline3>("tensor_t20_spline", tensor_t20_graph_.get());
    tensor_t22_spline_ = std::make_unique<TSpline3>("tensor_t22_spline", tensor_t22_graph_.get());
    tensor_t20_error_spline_ = std::make_unique<TSpline3>("tensor_t20_error_spline", tensor_t20_error_graph_.get());
    tensor_t22_error_spline_ = std::make_unique<TSpline3>("tensor_t22_error_spline", tensor_t22_error_graph_.get());
}

ObservableTableRepository::~ObservableTableRepository() = default;

double ObservableTableRepository::differentialCrossSectionMbPerSr(const double theta_cm_deg) const {
    return cross_section_spline_->Eval(clampAngle(cross_section_angles_deg_, theta_cm_deg));
}

double ObservableTableRepository::tensorT20(const double theta_cm_deg) const {
    return tensor_t20_spline_->Eval(clampAngle(tensor_angles_deg_, theta_cm_deg));
}

double ObservableTableRepository::tensorT22(const double theta_cm_deg) const {
    return tensor_t22_spline_->Eval(clampAngle(tensor_t22_angles_deg_, theta_cm_deg));
}

double ObservableTableRepository::tensorT20Error(const double theta_cm_deg) const {
    return std::max(0.0, tensor_t20_error_spline_->Eval(clampAngle(tensor_angles_deg_, theta_cm_deg)));
}

double ObservableTableRepository::tensorT22Error(const double theta_cm_deg) const {
    return std::max(0.0, tensor_t22_error_spline_->Eval(clampAngle(tensor_t22_angles_deg_, theta_cm_deg)));
}

const std::vector<double>& ObservableTableRepository::crossSectionAnglesDegrees() const noexcept {
    return cross_section_angles_deg_;
}

const std::vector<double>& ObservableTableRepository::tensorAnglesDegrees() const noexcept {
    return tensor_angles_deg_;
}

const std::vector<double>& ObservableTableRepository::tensorT22AnglesDegrees() const noexcept {
    return tensor_t22_angles_deg_;
}

const std::vector<double>& ObservableTableRepository::crossSectionValues() const noexcept {
    return cross_section_values_mb_per_sr_;
}

const std::vector<double>& ObservableTableRepository::tensorT20Values() const noexcept {
    return tensor_t20_values_;
}

const std::vector<double>& ObservableTableRepository::tensorT20Errors() const noexcept {
    return tensor_t20_errors_;
}

const std::vector<double>& ObservableTableRepository::tensorT22Values() const noexcept {
    return tensor_t22_values_;
}

const std::vector<double>& ObservableTableRepository::tensorT22Errors() const noexcept {
    return tensor_t22_errors_;
}

}  // namespace dpolar
