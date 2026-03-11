#pragma once

#include "dpolar/config.hpp"

#include <memory>
#include <vector>

class TGraph;
class TSpline3;

namespace dpolar {

class ObservableTableRepository {
public:
    explicit ObservableTableRepository(const ScenarioConfig& scenario);
    ~ObservableTableRepository();

    [[nodiscard]] double differentialCrossSectionMbPerSr(double theta_cm_deg) const;
    [[nodiscard]] double tensorT20(double theta_cm_deg) const;
    [[nodiscard]] double tensorT22(double theta_cm_deg) const;
    [[nodiscard]] double tensorT20Error(double theta_cm_deg) const;
    [[nodiscard]] double tensorT22Error(double theta_cm_deg) const;

    [[nodiscard]] const std::vector<double>& crossSectionAnglesDegrees() const noexcept;
    [[nodiscard]] const std::vector<double>& tensorAnglesDegrees() const noexcept;
    [[nodiscard]] const std::vector<double>& tensorT22AnglesDegrees() const noexcept;
    [[nodiscard]] const std::vector<double>& crossSectionValues() const noexcept;
    [[nodiscard]] const std::vector<double>& tensorT20Values() const noexcept;
    [[nodiscard]] const std::vector<double>& tensorT20Errors() const noexcept;
    [[nodiscard]] const std::vector<double>& tensorT22Values() const noexcept;
    [[nodiscard]] const std::vector<double>& tensorT22Errors() const noexcept;

private:
    std::vector<double> cross_section_angles_deg_;
    std::vector<double> cross_section_values_mb_per_sr_;
    std::vector<double> tensor_angles_deg_;
    std::vector<double> tensor_t22_angles_deg_;
    std::vector<double> tensor_t20_values_;
    std::vector<double> tensor_t20_errors_;
    std::vector<double> tensor_t22_values_;
    std::vector<double> tensor_t22_errors_;

    std::unique_ptr<TGraph> cross_section_graph_;
    std::unique_ptr<TGraph> tensor_t20_graph_;
    std::unique_ptr<TGraph> tensor_t22_graph_;
    std::unique_ptr<TGraph> tensor_t20_error_graph_;
    std::unique_ptr<TGraph> tensor_t22_error_graph_;
    std::unique_ptr<TSpline3> cross_section_spline_;
    std::unique_ptr<TSpline3> tensor_t20_spline_;
    std::unique_ptr<TSpline3> tensor_t22_spline_;
    std::unique_ptr<TSpline3> tensor_t20_error_spline_;
    std::unique_ptr<TSpline3> tensor_t22_error_spline_;
};

}  // namespace dpolar
