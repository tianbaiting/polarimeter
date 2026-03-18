# BigRIPS Slits: Acceptance, Transmission Loss, and Beam-Quality Tradeoffs

This page explains what BigRIPS slits remove from the beam and why slit settings affect transmission, separator cleanliness, and downstream background.

Scope note:

- This page is about slit action and acceptance trimming.
- It does not document primary-beam energy/current specifications; for those, use [../primary-beam-and-polarized-deuteron.md](../primary-beam-and-polarized-deuteron.md).

## What Slits Remove

In practical beam-tuning language, BigRIPS slit settings remove three overlapping classes of beam components:

1. Large-angle particles outside the accepted transverse phase-space envelope.
2. Momentum-tail particles outside the accepted `Bρ` window.
3. Spatial halo that would otherwise increase downstream background or hit beam-line hardware.

The exact optical meaning depends on the focal plane and slit orientation, but the underlying physics is standard separator phase-space control.

## Acceptance Conventions

Two source conventions appear in BigRIPS documentation. They are compatible and should not be mixed without explanation.

| Quantity | Full-width convention | Half-width convention | Sources |
| --- | --- | --- | --- |
| Horizontal angular acceptance | `80 mrad` | `±40 mrad` | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html), [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Vertical angular acceptance | `100 mrad` | `±50 mrad` | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html), [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |
| Momentum acceptance | `6%` | `±3%` | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html), [Kubo et al. 2012](https://doi.org/10.1093/ptep/pts064) |

## Where the Official Device List Places Slits

The official configuration page lists slits at multiple focal planes rather than treating them as a single generic device.

| Focal plane | Official slit listing | Reading note | Source |
| --- | --- | --- | --- |
| `F1` | `Slit(H)` | First-stage momentum-dispersive plane | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| `F2` | `Slit(V), Slit(H)` | Achromatic focus with beam-line devices | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| `F4` | `Slit(H)` | Second-stage momentum-dispersive plane | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| `F5` | `Slit(H)` | Second-stage momentum-dispersive plane | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| `F6` | `Slit(H)` | Second-stage momentum-dispersive plane | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| `F7` | `Slit(V), Slit(H)` | Doubly achromatic BigRIPS exit focus | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| `F8`, `F11`, `F12` | `Slit(V)` | Downstream line / spectrometer section, not the BigRIPS separator core | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |
| `F9`, `F10` | `Slit(H)` | Downstream line / spectrometer section | [RIKEN BigRIPS configuration page](https://www.nishina.riken.jp/RIBF/BigRIPS/config.html) |

## Optical Interpretation

- At momentum-dispersive planes, horizontal slits are the natural place to trim momentum tails because the position depends strongly on momentum deviation.
- Slits also suppress large-angle particles and halo by limiting the accepted transverse envelope.
- Tightening slit settings improves separator cleanliness and often improves particle-identification conditions downstream, but it reduces transmission.
- The penalty is therefore intentional beam loss in exchange for better beam quality and lower background.

## Why This Matters Near SAMURAI

- Downstream intensity at SAMURAI is not just a source/intensity question; it is also shaped by how aggressively BigRIPS acceptance is trimmed.
- When discussing beam loss with the BigRIPS team, distinguish clearly between source/accelerator limits and separator/slit limits.

## Source Notes

- The earlier repository note on this topic was too loose about acceptance conventions and used non-canonical links.
- This page keeps the same beam-physics idea, but now ties every acceptance number to a primary source and makes the focal-plane device locations explicit.
