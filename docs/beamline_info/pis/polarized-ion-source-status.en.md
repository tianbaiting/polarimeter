# Polarized Ion Source (PIS)

This page summarizes public-source information on the polarized deuteron source used for spin-dependent beam work at RIKEN RIBF. Quantitative statements are linked to primary or near-primary sources. If a desired quantity was not found in public sources, that absence is stated explicitly instead of being estimated.

## Scope and notation

- The sources below describe the RIKEN polarized ion source used for polarized deuteron beams, not a generic survey of polarized ion sources.
- Public documents use both `(p_y, p_yy)` and `(P_Z, P_ZZ)` for vector and tensor polarization. This page preserves the notation used by each source.

## 1. Verified system role and architecture

| Item | Verified statement | Source |
|---|---|---|
| Beamline role | The AVF cyclotron can use an external `ECR` ion source or a `Polarized ion Source`. | [RIKEN AVF facility page](https://www.nishina.riken.jp/facility/AVF_e.html) |
| Source type | The RIKEN PIS is an `atomic-beam-type` polarized ion source equipped with an `ECR ionizer`. | [Cyclotrons 2016 proceeding](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Polarized-beam production chain | The source uses a dissociator, sextupole magnets, RF-transition units, and an ECR ionizer to produce polarized deuterons from `D2` gas prepared from heavy water. | [Cyclotrons 2016 proceeding](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf), [SAST 1993 proceeding](https://www.pasj.jp/web_publish/sast1993/26DL3.pdf) |
| Spin-state flexibility | The source is equipped so that vector- and tensor-polarized spin states can be prepared. | [Cyclotrons 2016 proceeding](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Spin-direction control | Spin orientation is controlled downstream of the ion source by a `Wien filter` / spin rotator, allowing the polarization axis to be directed without changing the beam trajectory. | [Cyclotrons 2016 proceeding](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf), [SAST 1993 proceeding](https://www.pasj.jp/web_publish/sast1993/26DL3.pdf) |

## 2. Publicly traceable status timeline

| Date | Publicly traceable status | Source |
|---|---|---|
| 1992 | The source was assembled in May 1992; first acceleration tests were performed with the AVF cyclotron in June and the ring cyclotron in October 1992. | [SAST 1993 proceeding](https://www.pasj.jp/web_publish/sast1993/26DL3.pdf) |
| 1993 | RIKEN reported that the polarized ion source had been improved and was ready for experimental use. | [RIKEN APR Vol. 27](https://www.nishina.riken.jp/researcher/APR/Document/ProgressReport_vol_27.pdf) |
| 2015 | A later RIKEN conference poster states that the PIS was renewed after a long break since the polarized-deuteron experiment in `2015`. | [INPC 2025 poster](https://indico.ibs.re.kr/event/701/contributions/6590/contribution.pdf) |
| 2023 | RIKEN APR58 states that a `water leakage incident in 2023` raised concerns about source degradation after a prolonged operational interval. | [APR58 measurement report](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/36.pdf) |
| 2024-09 | The recovery test described in APR58 was conducted in `September 2024` using a `7 MeV/nucleon` polarized deuteron beam downstream of the AVF cyclotron. | [APR58 measurement report](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/36.pdf) |
| 2025 | The same APR58 report concludes that the `PIS is successfully recovered` and that the result supports its `full restoration`. | [APR58 measurement report](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/36.pdf) |
| 2025 | The Three-Body Nuclear Force Laboratory summary states that in `FY2024` a polarized deuteron beam source was prepared and acceleration tests confirmed `60–80%` beam polarization. | [APR58 laboratory activity summary](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/370.pdf) |

## 3. Polarization and intensity snapshots

The numbers below are kept as dated snapshots. They should not be merged into one timeless “specification”, because they come from different stages of source development and beam tuning.

| Era / context | Beam or source quantity | Publicly reported number | Source |
|---|---|---|---|
| 1993 development status | Source performance | `140 μA` with `50–60%` polarization of the ideal value | [SAST 1993 proceeding](https://www.pasj.jp/web_publish/sast1993/26DL3.pdf) |
| 1993 early ionizer | Best early ionizer performance | `20 μA` with `60%` polarization of the ideal value | [RIKEN APR Vol. 27](https://www.nishina.riken.jp/researcher/APR/Document/ProgressReport_vol_27.pdf) |
| 1993 improved ionizer | Routine improved performance | `140 μA` with `65%` polarization of the ideal value | [RIKEN APR Vol. 27](https://www.nishina.riken.jp/researcher/APR/Document/ProgressReport_vol_27.pdf) |
| 1993 pump dependence | Polarization without Ti sublimation pump | reduced to `50%` of the ideal value | [RIKEN APR Vol. 27](https://www.nishina.riken.jp/researcher/APR/Document/ProgressReport_vol_27.pdf) |
| 2016 operating summary | Ion beam intensity from the ECR ionizer | `< 100 μA` | [Cyclotrons 2016 proceeding](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| 2016 operating summary | Typical deuteron polarization | typically `80%` of the theoretical value | [Cyclotrons 2016 proceeding](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| 2024-09 beam test | Preliminary beam polarization range shown in FB23 material | `50–80% (preliminary)` | [FB23 slide deck](https://indico.ihep.ac.cn/event/21083/contributions/165969/attachments/82329/103939/2409beijing_yuko.pdf) |
| 2024-09 APR58 mode #1 | Measured mode `(p_y, p_yy)` for target theoretical state `(1/3, -1)` | `p_y = 0.222 ± 0.011`, `p_yy = -0.741 ± 0.039` | [APR58 measurement report](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/36.pdf) |
| 2024-09 APR58 mode #2 | Measured mode `(p_y, p_yy)` for target theoretical state `(-2/3, 0)` | `p_y = -0.556 ± 0.013`, `p_yy = 0.021 ± 0.048` | [APR58 measurement report](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/36.pdf) |
| 2024-09 APR58 mode #3 | Measured mode `(p_y, p_yy)` for target theoretical state `(1/3, 1)` | `p_y = 0.260 ± 0.014`, `p_yy = 0.565 ± 0.052` | [APR58 measurement report](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/36.pdf) |
| 2024-09 APR58 interpretation | Recovery-test quality | modes `#1` and `#2` were `70–80%` of the theoretical maxima; mode `#3` was still suboptimal | [APR58 measurement report](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/36.pdf) |
| 2025 INPC poster | Representative recovery-test amplitudes highlighted in conference material | `p_y = -0.556 ± 0.013`, `p_yy = -0.741 ± 0.039`, typical beam intensity `10 nA` at `7 MeV/nucleon` | [INPC 2025 poster](https://indico.ibs.re.kr/event/701/contributions/6590/contribution.pdf) |

## 4. Stability and time behavior

| Aspect | Publicly reported behavior | Source |
|---|---|---|
| Early nozzle problem | Before mitigation, nozzle deposits could reduce beam intensity to about `50%` within a few hours and could plug the orifice after a few days. | [SAST 1993 proceeding](https://www.pasj.jp/web_publish/sast1993/26DL3.pdf) |
| Optimized 1993 operation | With `37 K` nozzle temperature, `N2`-layer conditioning, and low reflected RF power, `no reduction of intensity` was observed for `at least one week`. | [SAST 1993 proceeding](https://www.pasj.jp/web_publish/sast1993/26DL3.pdf) |
| 1993 long-term source study | After nozzle and ionizer modifications, the APR report again states that `no reduction of intensity is observed for at least one week`. | [RIKEN APR Vol. 27](https://www.nishina.riken.jp/researcher/APR/Document/ProgressReport_vol_27.pdf) |
| Pumping sensitivity | The APR report explicitly states that polarization falls from `65%` to `50%` of the ideal value without the Ti sublimation pump. | [RIKEN APR Vol. 27](https://www.nishina.riken.jp/researcher/APR/Document/ProgressReport_vol_27.pdf) |
| Recovery-test cadence | In the September 2024 recovery measurement, the four PIS spin modes were switched cyclically every `5 s`. | [APR58 measurement report](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/36.pdf) |

## 5. Requirement-style numbers relevant to planned d-p spin-correlation work

The numbers in this section are not “intrinsic source specifications”. They are planning or accelerator constraints tied to the intended few-body experiment.

| Requirement / constraint | Publicly reported number or statement | Source |
|---|---|---|
| Cyclotron extraction purity | Polarized deuteron experiments at `100–300 MeV/nucleon` required turn purity `more than 99%` to avoid polarization-amplitude loss from mixed turn numbers. | [Cyclotrons 2016 proceeding](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf) |
| Planned d-p spin-correlation measurement energy | The first planned measurement is the spin-correlation coefficient for `d-p elastic scattering at 100 MeV/nucleon`. | [APR58 laboratory activity summary](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/370.pdf) |
| Planning assumption for uncertainty estimates | A 2025 Tohoku thesis uses `beam polarization (PZ and PZZ) = 70%` and `target polarization = 10%` in the uncertainty estimate table. | [Saito thesis record](https://tohoku.repo.nii.ac.jp/records/2003966) |
| Planning interpretation of recent beam quality | The same thesis states that in the September 2024 machine study, both vector and tensor polarization were obtained at `80%` of the theoretical maximum. | [Saito thesis record](https://tohoku.repo.nii.ac.jp/records/2003966) |
| Beam-side status in FY2024 | The Three-Body Laboratory summary states that the beam acceleration tests confirmed `60–80%` beam polarization. | [APR58 laboratory activity summary](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/370.pdf) |
| Target-side limitation | The same summary states that target depolarization below `10^8 counts/s` was negligible, but the achieved target polarization was only `3%`, so further target development was required. This is a target issue, not a PIS issue. | [APR58 laboratory activity summary](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/370.pdf) |

## 6. Public evidence gaps

- No recent public source located here provides a post-recovery uptime statistic such as weekly availability or mean time between failures.
- No recent public source located here gives a directly measured post-2024 long-term polarization drift in units such as percent per hour or percent per day.
- No public beamline document located here states a single mandatory minimum polarization requirement for SAMURAI use in general; the clearest requirement-like number found was the `70%` planning assumption in the 2025 thesis for the d-p spin-correlation experiment.

## 7. Source list

- [RIKEN AVF facility page](https://www.nishina.riken.jp/facility/AVF_e.html)
- [SAST 1993 proceeding: Development of the RIKEN Atomic Beam Type Polarized Ion Source](https://www.pasj.jp/web_publish/sast1993/26DL3.pdf)
- [RIKEN Accelerator Progress Report Vol. 27 (1993): Development of the RIKEN Polarized Ion Source](https://www.nishina.riken.jp/researcher/APR/Document/ProgressReport_vol_27.pdf)
- [Cyclotrons 2016 proceeding: Acceleration of Polarized Deuteron Beams with RIBF Cyclotrons](https://accelconf.web.cern.ch/cyclotrons2016/papers/tub04.pdf)
- [APR58 measurement report (2025): Measurement of deuteron beam polarization at RIKEN RIBF](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/36.pdf)
- [APR58 laboratory activity summary (2025): Three-Body Nuclear Force Laboratory](https://www.nishina.riken.jp/researcher/APR/APR058/pdf/370.pdf)
- [INPC 2025 poster: Measurement of the polarization of the deuteron beam at RIKEN RIBF](https://indico.ibs.re.kr/event/701/contributions/6590/contribution.pdf)
- [FB23 slide deck (2024): Ready for the Spin Correlation Coefficients Measurement](https://indico.ihep.ac.cn/event/21083/contributions/165969/attachments/82329/103939/2409beijing_yuko.pdf)
- [Saito thesis record (2025): Developments Toward the Measurement of Spin Correlation Coefficients for d-p Elastic Scattering](https://tohoku.repo.nii.ac.jp/records/2003966)
