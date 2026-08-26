#pragma once

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace dpolar {

using TensorVector = std::array<double, 5>;
using VectorPolarization = std::array<double, 3>;
using Matrix3 = std::array<double, 9>;

struct PhysicalTensorComponents {
    double pxx_minus_pyy{};
    double pxy{};
    double pxz{};
    double pyz{};
    double pzz{};
};

class TensorPolarization {
  public:
    TensorPolarization();
    explicit TensorPolarization(Matrix3 matrix);

    [[nodiscard]] static TensorPolarization fromInternal(const TensorVector& coordinates);
    [[nodiscard]] static TensorPolarization fromPhysical(const PhysicalTensorComponents& components);
    [[nodiscard]] static TensorPolarization axial(double magnitude, const VectorPolarization& axis);

    [[nodiscard]] TensorVector internal() const noexcept;
    [[nodiscard]] PhysicalTensorComponents physical() const noexcept;
    [[nodiscard]] const Matrix3& matrix() const noexcept;
    [[nodiscard]] double frobeniusNorm() const noexcept;

  private:
    Matrix3 matrix_{};
};

struct DenseMatrix {
    std::size_t rows{};
    std::size_t cols{};
    std::vector<double> values;

    DenseMatrix() = default;
    DenseMatrix(std::size_t row_count, std::size_t column_count, double initial_value = 0.0);

    double& operator()(std::size_t row, std::size_t column);
    [[nodiscard]] double operator()(std::size_t row, std::size_t column) const;
};

class SpinRotation {
  public:
    SpinRotation();
    explicit SpinRotation(Matrix3 rotation);

    [[nodiscard]] static SpinRotation axisAngle(const VectorPolarization& axis, double angle_rad);
    [[nodiscard]] static SpinRotation eulerZyx(double z_rad, double y_rad, double x_rad);

    [[nodiscard]] TensorPolarization apply(const TensorPolarization& tensor) const;
    [[nodiscard]] VectorPolarization apply(const VectorPolarization& vector) const noexcept;
    [[nodiscard]] DenseMatrix tensorMap() const;
    [[nodiscard]] const Matrix3& matrix() const noexcept;

  private:
    Matrix3 rotation_{};
};

[[nodiscard]] DenseMatrix identityMatrix(std::size_t size);
[[nodiscard]] DenseMatrix transpose(const DenseMatrix& matrix);
[[nodiscard]] DenseMatrix multiply(const DenseMatrix& left, const DenseMatrix& right);
[[nodiscard]] DenseMatrix verticalStack(const DenseMatrix& upper, const DenseMatrix& lower);
[[nodiscard]] TensorVector multiply(const DenseMatrix& matrix, const TensorVector& vector);
[[nodiscard]] std::string tensorBasisDescription();

}
