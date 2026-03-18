# BigRIPS Primary Beams and Polarized Deuteron Beam

This page collects primary-beam parameters relevant to BigRIPS-based experiments, with emphasis on polarized deuteron beams.

Scope note:

- This page is limited to primary beams and the polarized deuteron acceleration chain.
- It intentionally does not summarize secondary RI-beam intensities, isotope-production yields, or separator tuning files for downstream fragments.

## Current Official Primary-Beam Entries Relevant to Deuterons

The current RIKEN accelerator technical tables are the best source for proposal-planning values.

| Beam | Energy | Current | Context | Source |
| --- | --- | --- | --- | --- |
| `d` | `250 MeV/u` | `1000 pnA` maximum achieved so far; `200 pnA` expected | SRC table; AVF injection | [RIKEN accelerator technical information](https://www.nishina.riken.jp/RIBF/accelerator/tecinfo.html) |
| `d(pol.)` | `250 MeV/u` | `120 pnA` maximum achieved so far; `30 pnA` expected | SRC table; AVF injection; official note says source development is necessary | [RIKEN accelerator technical information](https://www.nishina.riken.jp/RIBF/accelerator/tecinfo.html) |
| `d(pol.)` | `135 MeV/u` | `30 pnA` | RRC table; AVF injection; PIS ion source | [RIKEN accelerator technical information](https://www.nishina.riken.jp/RIBF/accelerator/tecinfo.html) |

Additional planning note:

- The same technical-information page explicitly states that proposal planning should use the `expected` currents from the table rather than the maximum instantaneous values.
- The same page also gives a tentative BigRIPS-based primary-beam plan: `FY2025` includes `^{238}U`, `^{124}Xe`, `^{78}Kr`, `^{70}Zn`, and `light ions`; `FY2026` is listed as `to be decided`.

## Historical / Design-Era Statements

These entries are useful context, but they should not be substituted for the current operating tables above.

| Statement | Value | Interpretation | Source |
| --- | --- | --- | --- |
| Goal primary-beam intensity | `1 pμA` | Historical RIBF goal value, limited by radiation shielding around the primary-beam dump | [RIKEN accelerator overview](https://www.nishina.riken.jp/ribf/accelerator/overview.html) |
| Polarized deuteron capability statement | `880 MeV polarized deuteron beam will also be available` | Historical overview wording; keep it as a design-era statement instead of reading it as the current operating table | [RIKEN accelerator overview](https://www.nishina.riken.jp/ribf/accelerator/overview.html) |

## Polarized Deuteron Beam: Source, Spin Control, and Beam-Quality Indicators

The 2016 Cyclotrons conference paper is the most compact primary source for the polarized-deuteron chain used at RIBF.

| Parameter | Value | Context | Source |
| --- | --- | --- | --- |
| Polarized ion source type | Atomic-beam-type PIS with an ECR ionizer | RIKEN polarized ion source used for tensor- and vector-polarized deuterons | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Spin-state flexibility | Any deuteron spin state represented by vector and tensor polarizations | Enabled by the two-stage spin selector in the PIS | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Ion-source beam intensity | `< 100 μA` | Output from the ECR ionizer | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Typical polarization level | `~80%` of the theoretical value | Paper describes this as the typical polarization of the deuteron beam | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Spin-orientation control | Wien filter downstream of the ionizer and before AVF injection | Used to tilt and rotate the spin without changing beam direction | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Demonstrated accelerated energies | `190 MeV/u`, `250 MeV/u`, `300 MeV/u` | Explicitly reported as achieved polarized deuteron beam energies | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Required turn purity | `> 99%` | Required by the polarized-deuteron experiments discussed in the paper | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Observed turn-mixing rate | `0.07%` | Example measurement for the extracted beam time structure | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Stable operating window | `2-3 days` | Single-turn operation remained stable during the measurements | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Reported turn purity in operation | `much more than 99%` | Final summary wording of the Cyclotrons paper | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Beam-bunch length at the target position | `~0.58 ns` | Estimated after subtracting monitor resolution | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |

For more detailed PIS history, recovery status, and post-2024 public reports, see [../pis/polarized-ion-source-status.en.md](../pis/polarized-ion-source-status.en.md).

## Acceleration Chain Used for the Polarized Deuteron Program

For the light-ion polarized-deuteron program described in the Cyclotrons paper, the chain is:

`PIS -> Wien filter -> AVF -> RRC -> SRC -> beam-line polarimeters / experiment`

Relevant accelerator-side parameters reported in the same source include:

| Accelerator | Example deuteron energies in the chain | Notes | Source |
| --- | --- | --- | --- |
| AVF | `4.0`, `4.9`, `5.5 MeV/u` | Injection-stage deuteron energies for the 190 / 250 / 300 MeV/u campaigns | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| RRC | `70.4`, `89.9`, `102.5 MeV/u` | Intermediate-stage deuteron energies | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| SRC | `187.5`, `252.3`, `298.5 MeV/u` | Final extracted energies corresponding to the nominal 190 / 250 / 300 MeV/u runs | [Sakamoto et al. 2016](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |

## Practical Reading Rule

- Use the RIKEN accelerator technical-information page for current planning values.
- Use the Cyclotrons2016 paper for polarized-deuteron source, polarization, and beam-quality indicators.
- Keep the `880 MeV polarized deuteron` statement only as historical facility context unless a newer official page reaffirms it.
