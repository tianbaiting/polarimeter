# BigRIPS Overview

This page summarizes the BigRIPS separator parameters that matter for beamline-interface work near SAMURAI.

Scope note:

- This page is about the BigRIPS separator itself and the transport boundary into downstream lines.
- It does not summarize secondary RI-beam yields or isotope-production performance tables.

## System Boundary

- BigRIPS is the two-stage separator from the production target region to `F7`.
- ZeroDegree is the downstream spectrometer section from `F8` to `F11`.
- For SAMURAI experiments, optics are matched further downstream toward `F13` / SAMURAI, but that downstream transport should not be treated as identical to the separator itself.
- In this repository, avoid the shorthand `BigRIPS = F0-F13` unless the downstream delivery line is explicitly intended.

## Core Parameters

| Parameter | Value | Convention / context | Source |
| --- | --- | --- | --- |
| Separator structure | Two-stage separator | First stage produces and separates RI beams; second stage identifies and delivers tagged beams | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html), [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Main magnets | 14 superconducting triplet quadrupoles + 6 dipoles | Dipoles are 30-degree room-temperature dipoles in the official overview | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html), [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Focal planes | `F1` momentum dispersive; `F2`, `F3` achromatic; `F4`, `F5`, `F6` momentum dispersive; `F7` doubly achromatic | Canonical BigRIPS focal-plane layout | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html), [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Horizontal angular acceptance | `80 mrad` | Official full width; equivalent to `±40 mrad` half acceptance | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html), [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Vertical angular acceptance | `100 mrad` | Official full width; equivalent to `±50 mrad` half acceptance | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html), [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Momentum acceptance | `6%` | Official full width; equivalent to `±3%` momentum acceptance | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html), [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Maximum magnetic rigidity | `9 Tm` | Official configuration page value | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| Maximum magnetic rigidity | `9.5 Tm` / `8.8 Tm` | First-stage / second-stage values in the 2012 design-performance paper | [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Total length | `77 m` | Official configuration page reports `F0-F7` path length | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| Total length | `78.2 m` | Total BigRIPS separator length in the 2012 paper | [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Momentum resolving power, first stage | `1290` | Official value for `dX = 1 mm` | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| Momentum resolving power, second stage | `3300` | Official value for `dX = 1 mm` | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| Momentum resolving power, first stage | `1260` | Value quoted in the 2012 paper | [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Momentum resolving power, second stage | `3420` | Value quoted in the 2012 paper | [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Degrader locations | `F1`, `F4`, `F5`, `F6` | Official device/configuration summary | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| High-power beam dump | Inside the gap of `D1` | Used to stop primary heavy-ion beams | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html), [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |

## How to Read the Source Differences

- `80 mrad`, `100 mrad`, and `6%` on the official page are full-width acceptances. The design paper writes the same acceptances as `±40 mrad`, `±50 mrad`, and `±3%`.
- The differences in `9 Tm` versus `9.5/8.8 Tm`, `77 m` versus `78.2 m`, and `1290/3300` versus `1260/3420` are genuine source-era differences, not just notation changes.
- For planning or citation, keep the source label attached to the number instead of collapsing these values into a single unsourced "official" value.

## Practical Boundary for This Repository

- Use this page when a SAMURAI-adjacent note needs facility-level BigRIPS parameters or separator geometry language.
- Use [primary-beam-and-polarized-deuteron.md](primary-beam-and-polarized-deuteron.md) for primary-beam values, especially polarized deuterons.
- Use [slits/acceptance-and-loss.md](slits/acceptance-and-loss.md) for slit-related transmission, acceptance trimming, and beam-quality tradeoffs.

## Source Notes

- RIKEN official configuration page is the authoritative facility web summary for current user-facing separator parameters.
- Kubo et al. 2012 is the canonical design / performance overview and should be cited when stage-by-stage separator values are needed.
