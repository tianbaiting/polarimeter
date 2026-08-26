#include "dpolar/tensor.hpp"

#include <algorithm>
#include <cmath>
#include <numbers>
#include <stdexcept>
#include <utility>

namespace dpolar {
namespace {

constexpr std::size_t index3(const std::size_t row, const std::size_t column) noexcept {
    return 3U * row + column;
}

Matrix3 multiply3(const Matrix3& left, const Matrix3& right) noexcept {
    Matrix3 result{};
    for (std::size_t row = 0; row < 3U; ++row) {
        for (std::size_t column = 0; column < 3U; ++column) {
            for (std::size_t inner = 0; inner < 3U; ++inner) {
                result[index3(row, column)] += left[index3(row, inner)] * right[index3(inner, column)];
            }
        }
    }
    return result;
}

Matrix3 transpose3(const Matrix3& matrix) noexcept {
    Matrix3 result{};
    for (std::size_t row = 0; row < 3U; ++row) {
        for (std::size_t column = 0; column < 3U; ++column) {
            result[index3(row, column)] = matrix[index3(column, row)];
        }
    }
    return result;
}

Matrix3 axisRotation(const std::size_t axis, const double angle) noexcept {
    const double cosine = std::cos(angle);
    const double sine = std::sin(angle);
    if (axis == 0U) {
        return Matrix3{1.0, 0.0, 0.0, 0.0, cosine, -sine, 0.0, sine, cosine};
    }
    if (axis == 1U) {
        return Matrix3{cosine, 0.0, sine, 0.0, 1.0, 0.0, -sine, 0.0, cosine};
    }
    return Matrix3{cosine, -sine, 0.0, sine, cosine, 0.0, 0.0, 0.0, 1.0};
}

}

TensorPolarization::TensorPolarization() = default;

TensorPolarization::TensorPolarization(Matrix3 matrix) : matrix_(std::move(matrix)) {
    const double scale = std::max(1.0, frobeniusNorm());
    if (std::abs(matrix_[1] - matrix_[3]) > 1.0e-12 * scale || std::abs(matrix_[2] - matrix_[6]) > 1.0e-12 * scale ||
        std::abs(matrix_[5] - matrix_[7]) > 1.0e-12 * scale) {
        throw std::invalid_argument("Tensor polarization must be symmetric");
    }
    if (std::abs(matrix_[0] + matrix_[4] + matrix_[8]) > 1.0e-12 * scale) {
        throw std::invalid_argument("Tensor polarization must be traceless");
    }
}

TensorPolarization TensorPolarization::fromInternal(const TensorVector& coordinates) {
    constexpr double inverse_root_two = 1.0 / std::numbers::sqrt2_v<double>;
    const double inverse_root_six = 1.0 / std::sqrt(6.0);
    return TensorPolarization(Matrix3{
        coordinates[0] * inverse_root_two - coordinates[4] * inverse_root_six,
        coordinates[1] * inverse_root_two,
        coordinates[2] * inverse_root_two,
        coordinates[1] * inverse_root_two,
        -coordinates[0] * inverse_root_two - coordinates[4] * inverse_root_six,
        coordinates[3] * inverse_root_two,
        coordinates[2] * inverse_root_two,
        coordinates[3] * inverse_root_two,
        2.0 * coordinates[4] * inverse_root_six,
    });
}

TensorPolarization TensorPolarization::fromPhysical(const PhysicalTensorComponents& components) {
    const double pxx = 0.5 * (-components.pzz + components.pxx_minus_pyy);
    const double pyy = 0.5 * (-components.pzz - components.pxx_minus_pyy);
    return TensorPolarization(Matrix3{
        pxx,
        components.pxy,
        components.pxz,
        components.pxy,
        pyy,
        components.pyz,
        components.pxz,
        components.pyz,
        components.pzz,
    });
}

TensorPolarization TensorPolarization::axial(const double magnitude, const VectorPolarization& axis) {
    const double norm = std::sqrt(axis[0] * axis[0] + axis[1] * axis[1] + axis[2] * axis[2]);
    if (!(norm > 0.0)) {
        throw std::invalid_argument("Tensor symmetry axis must be nonzero");
    }
    VectorPolarization unit{axis[0] / norm, axis[1] / norm, axis[2] / norm};
    Matrix3 matrix{};
    for (std::size_t row = 0; row < 3U; ++row) {
        for (std::size_t column = 0; column < 3U; ++column) {
            matrix[index3(row, column)] = 1.5 * magnitude * unit[row] * unit[column];
            if (row == column) {
                matrix[index3(row, column)] -= 0.5 * magnitude;
            }
        }
    }
    return TensorPolarization(matrix);
}

TensorVector TensorPolarization::internal() const noexcept {
    constexpr double inverse_root_two = 1.0 / std::numbers::sqrt2_v<double>;
    return TensorVector{
        (matrix_[0] - matrix_[4]) * inverse_root_two,
        std::numbers::sqrt2_v<double> * matrix_[1],
        std::numbers::sqrt2_v<double> * matrix_[2],
        std::numbers::sqrt2_v<double> * matrix_[5],
        std::sqrt(1.5) * matrix_[8],
    };
}

PhysicalTensorComponents TensorPolarization::physical() const noexcept {
    return PhysicalTensorComponents{
        matrix_[0] - matrix_[4],
        matrix_[1],
        matrix_[2],
        matrix_[5],
        matrix_[8],
    };
}

const Matrix3& TensorPolarization::matrix() const noexcept {
    return matrix_;
}

double TensorPolarization::frobeniusNorm() const noexcept {
    double norm_squared = 0.0;
    for (const double value : matrix_) {
        norm_squared += value * value;
    }
    return std::sqrt(norm_squared);
}

DenseMatrix::DenseMatrix(const std::size_t row_count, const std::size_t column_count, const double initial_value)
    : rows(row_count), cols(column_count), values(row_count * column_count, initial_value) {}

double& DenseMatrix::operator()(const std::size_t row, const std::size_t column) {
    return values.at(row * cols + column);
}

double DenseMatrix::operator()(const std::size_t row, const std::size_t column) const {
    return values.at(row * cols + column);
}

SpinRotation::SpinRotation() : rotation_{1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0} {}

SpinRotation::SpinRotation(Matrix3 rotation) : rotation_(std::move(rotation)) {
    const Matrix3 product = multiply3(rotation_, transpose3(rotation_));
    for (std::size_t index = 0; index < 9U; ++index) {
        const double expected = index % 4U == 0U ? 1.0 : 0.0;
        if (std::abs(product[index] - expected) > 1.0e-10) {
            throw std::invalid_argument("Spin rotation must be orthogonal");
        }
    }
    const double determinant = rotation_[0] * (rotation_[4] * rotation_[8] - rotation_[5] * rotation_[7]) -
                               rotation_[1] * (rotation_[3] * rotation_[8] - rotation_[5] * rotation_[6]) +
                               rotation_[2] * (rotation_[3] * rotation_[7] - rotation_[4] * rotation_[6]);
    if (std::abs(determinant - 1.0) > 1.0e-10) {
        throw std::invalid_argument("Spin rotation must have determinant +1");
    }
}

SpinRotation SpinRotation::axisAngle(const VectorPolarization& axis, const double angle_rad) {
    if (angle_rad == 0.0) {
        return SpinRotation();
    }
    const double norm = std::sqrt(axis[0] * axis[0] + axis[1] * axis[1] + axis[2] * axis[2]);
    if (!(norm > 0.0)) {
        throw std::invalid_argument("Spin rotation axis must be nonzero");
    }
    const double x = axis[0] / norm;
    const double y = axis[1] / norm;
    const double z = axis[2] / norm;
    const double cosine = std::cos(angle_rad);
    const double sine = std::sin(angle_rad);
    const double complement = 1.0 - cosine;
    return SpinRotation(Matrix3{
        cosine + x * x * complement,
        x * y * complement - z * sine,
        x * z * complement + y * sine,
        y * x * complement + z * sine,
        cosine + y * y * complement,
        y * z * complement - x * sine,
        z * x * complement - y * sine,
        z * y * complement + x * sine,
        cosine + z * z * complement,
    });
}

SpinRotation SpinRotation::eulerZyx(const double z_rad, const double y_rad, const double x_rad) {
    return SpinRotation(multiply3(axisRotation(2U, z_rad), multiply3(axisRotation(1U, y_rad), axisRotation(0U, x_rad))));
}

TensorPolarization SpinRotation::apply(const TensorPolarization& tensor) const {
    return TensorPolarization(multiply3(multiply3(rotation_, tensor.matrix()), transpose3(rotation_)));
}

VectorPolarization SpinRotation::apply(const VectorPolarization& vector) const noexcept {
    VectorPolarization result{};
    for (std::size_t row = 0; row < 3U; ++row) {
        for (std::size_t column = 0; column < 3U; ++column) {
            result[row] += rotation_[index3(row, column)] * vector[column];
        }
    }
    return result;
}

DenseMatrix SpinRotation::tensorMap() const {
    DenseMatrix map(5U, 5U);
    for (std::size_t column = 0; column < 5U; ++column) {
        TensorVector basis{};
        basis[column] = 1.0;
        const TensorVector transformed = apply(TensorPolarization::fromInternal(basis)).internal();
        for (std::size_t row = 0; row < 5U; ++row) {
            map(row, column) = transformed[row];
        }
    }
    return map;
}

const Matrix3& SpinRotation::matrix() const noexcept {
    return rotation_;
}

DenseMatrix identityMatrix(const std::size_t size) {
    DenseMatrix result(size, size);
    for (std::size_t index = 0; index < size; ++index) {
        result(index, index) = 1.0;
    }
    return result;
}

DenseMatrix transpose(const DenseMatrix& matrix) {
    DenseMatrix result(matrix.cols, matrix.rows);
    for (std::size_t row = 0; row < matrix.rows; ++row) {
        for (std::size_t column = 0; column < matrix.cols; ++column) {
            result(column, row) = matrix(row, column);
        }
    }
    return result;
}

DenseMatrix multiply(const DenseMatrix& left, const DenseMatrix& right) {
    if (left.cols != right.rows) {
        throw std::invalid_argument("Matrix dimensions are incompatible for multiplication");
    }
    DenseMatrix result(left.rows, right.cols);
    for (std::size_t row = 0; row < left.rows; ++row) {
        for (std::size_t inner = 0; inner < left.cols; ++inner) {
            const double scale = left(row, inner);
            for (std::size_t column = 0; column < right.cols; ++column) {
                result(row, column) += scale * right(inner, column);
            }
        }
    }
    return result;
}

DenseMatrix verticalStack(const DenseMatrix& upper, const DenseMatrix& lower) {
    if (upper.cols != lower.cols) {
        throw std::invalid_argument("Stacked matrices must have the same column count");
    }
    DenseMatrix result(upper.rows + lower.rows, upper.cols);
    for (std::size_t row = 0; row < upper.rows; ++row) {
        for (std::size_t column = 0; column < upper.cols; ++column) {
            result(row, column) = upper(row, column);
        }
    }
    for (std::size_t row = 0; row < lower.rows; ++row) {
        for (std::size_t column = 0; column < lower.cols; ++column) {
            result(upper.rows + row, column) = lower(row, column);
        }
    }
    return result;
}

TensorVector multiply(const DenseMatrix& matrix, const TensorVector& vector) {
    if (matrix.rows != 5U || matrix.cols != 5U) {
        throw std::invalid_argument("Tensor map must be 5 by 5");
    }
    TensorVector result{};
    for (std::size_t row = 0; row < 5U; ++row) {
        for (std::size_t column = 0; column < 5U; ++column) {
            result[row] += matrix(row, column) * vector[column];
        }
    }
    return result;
}

std::string tensorBasisDescription() {
    return "orthonormal Frobenius basis: (xx-yy)/sqrt(2), sqrt(2)xy, sqrt(2)xz, "
           "sqrt(2)yz, sqrt(3/2)zz";
}

}
