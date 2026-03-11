from __future__ import annotations

import ctypes
import os
import shutil
from dataclasses import dataclass
from pathlib import Path


class _ScatteringSolution(ctypes.Structure):
    _fields_ = [
        ("deuteron_theta_lab_rad", ctypes.c_double),
        ("deuteron_phi_lab_rad", ctypes.c_double),
        ("deuteron_kinetic_energy_mev", ctypes.c_double),
        ("proton_theta_lab_rad", ctypes.c_double),
        ("proton_phi_lab_rad", ctypes.c_double),
        ("proton_kinetic_energy_mev", ctypes.c_double),
    ]


@dataclass(slots=True)
class ScatterResult:
    deuteron_theta_lab_rad: float
    deuteron_phi_lab_rad: float
    deuteron_kinetic_energy_mev: float
    proton_theta_lab_rad: float
    proton_phi_lab_rad: float
    proton_kinetic_energy_mev: float


def _library_path() -> str:
    if "DPOLAR_CAPI_LIB" in os.environ:
        return os.environ["DPOLAR_CAPI_LIB"]

    package_root = Path(__file__).resolve().parents[2]
    candidates = [
        package_root / "build" / "libdpolar_capi.so",
        package_root / "build" / "code_reco" / "libdpolar_capi.so",
        package_root / "libdpolar_capi.so",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    resolved = shutil.which("libdpolar_capi.so")
    if resolved is not None:
        return resolved
    raise FileNotFoundError("Unable to locate libdpolar_capi.so. Set DPOLAR_CAPI_LIB or build code_reco first.")


_LIBRARY = ctypes.CDLL(_library_path())

_LIBRARY.dpolar_scatter.argtypes = [
    ctypes.c_char_p,
    ctypes.c_double,
    ctypes.c_double,
    ctypes.POINTER(_ScatteringSolution),
    ctypes.c_char_p,
    ctypes.c_size_t,
]
_LIBRARY.dpolar_scatter.restype = ctypes.c_int

_LIBRARY.dpolar_deuteron_cm_from_lab.argtypes = [
    ctypes.c_char_p,
    ctypes.c_double,
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.c_char_p,
    ctypes.c_size_t,
]
_LIBRARY.dpolar_deuteron_cm_from_lab.restype = ctypes.c_int

_LIBRARY.dpolar_proton_cm_from_lab.argtypes = [
    ctypes.c_char_p,
    ctypes.c_double,
    ctypes.POINTER(ctypes.c_double),
    ctypes.c_char_p,
    ctypes.c_size_t,
]
_LIBRARY.dpolar_proton_cm_from_lab.restype = ctypes.c_int

_LIBRARY.dpolar_proton_lab_from_deuteron_cm.argtypes = [
    ctypes.c_char_p,
    ctypes.c_double,
    ctypes.POINTER(ctypes.c_double),
    ctypes.c_char_p,
    ctypes.c_size_t,
]
_LIBRARY.dpolar_proton_lab_from_deuteron_cm.restype = ctypes.c_int


def _scenario_path(path: str | Path) -> bytes:
    return str(Path(path).expanduser().resolve()).encode("utf-8")


def _call_status(status: int, error_buffer: ctypes.Array[ctypes.c_char]) -> None:
    if status != 0:
        raise RuntimeError(error_buffer.value.decode("utf-8"))


def scatter(theta_cm_rad: float, phi_cm_rad: float, scenario: str | Path) -> ScatterResult:
    output = _ScatteringSolution()
    error = ctypes.create_string_buffer(1024)
    status = _LIBRARY.dpolar_scatter(_scenario_path(scenario), theta_cm_rad, phi_cm_rad, ctypes.byref(output), error, len(error))
    _call_status(status, error)
    return ScatterResult(
        deuteron_theta_lab_rad=output.deuteron_theta_lab_rad,
        deuteron_phi_lab_rad=output.deuteron_phi_lab_rad,
        deuteron_kinetic_energy_mev=output.deuteron_kinetic_energy_mev,
        proton_theta_lab_rad=output.proton_theta_lab_rad,
        proton_phi_lab_rad=output.proton_phi_lab_rad,
        proton_kinetic_energy_mev=output.proton_kinetic_energy_mev,
    )


def deuteron_cm_from_lab(theta_lab_rad: float, scenario: str | Path) -> tuple[float, float]:
    first = ctypes.c_double()
    second = ctypes.c_double()
    error = ctypes.create_string_buffer(1024)
    status = _LIBRARY.dpolar_deuteron_cm_from_lab(
        _scenario_path(scenario),
        theta_lab_rad,
        ctypes.byref(first),
        ctypes.byref(second),
        error,
        len(error),
    )
    _call_status(status, error)
    return first.value, second.value


def proton_cm_from_lab(theta_lab_rad: float, scenario: str | Path) -> float:
    output = ctypes.c_double()
    error = ctypes.create_string_buffer(1024)
    status = _LIBRARY.dpolar_proton_cm_from_lab(
        _scenario_path(scenario),
        theta_lab_rad,
        ctypes.byref(output),
        error,
        len(error),
    )
    _call_status(status, error)
    return output.value


def proton_lab_from_deuteron_cm(theta_cm_rad: float, scenario: str | Path) -> float:
    output = ctypes.c_double()
    error = ctypes.create_string_buffer(1024)
    status = _LIBRARY.dpolar_proton_lab_from_deuteron_cm(
        _scenario_path(scenario),
        theta_cm_rad,
        ctypes.byref(output),
        error,
        len(error),
    )
    _call_status(status, error)
    return output.value
