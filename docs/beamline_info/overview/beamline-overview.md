# Beamline Overview

## Beamline Chain

PIS (polarized ion source)
-> Injector / AVF / RILAC
-> Cyclotron chain (RRC -> fRC / IRC / SRC as required)
-> BigRIPS separator (target region to F7)
-> ZeroDegree / downstream matching section (F8 and beyond, experiment-dependent)
-> SAMURAI beamline / target
-> SAMURAI spectrometer + detectors

![Beamline map around BigRIPS and SAMURAI](../samurai/beam-pipe/figures/beamline-chain-samurai-location-map.png)

## Polarization Budget

The working decomposition used in this folder is

`P(SAMURAI) = P(source) x transport effects x beamline effects x systematics`

The documents under `beamline_info/` mainly constrain the `beamline effects` and the mechanical interfaces near SAMURAI.

## Reading Guide

- Use [contacts-and-interfaces.md](contacts-and-interfaces.md) when you need to know who owns which beamline question.
- Use [../pis/polarized-ion-source-status.en.md](../pis/polarized-ion-source-status.en.md) for sourced notes on the RIKEN polarized ion source, including status, polarization numbers, and evidence gaps.
- Use [../bigrips/overview.md](../bigrips/overview.md) for separator boundaries, optics structure, and core BigRIPS parameters.
- Use [../bigrips/primary-beam-and-polarized-deuteron.md](../bigrips/primary-beam-and-polarized-deuteron.md) for current primary-beam values and polarized-deuteron-beam metrics.
- Use [../bigrips/slits/acceptance-and-loss.md](../bigrips/slits/acceptance-and-loss.md) for the BigRIPS slit and transmission background.
- Use [../samurai/beam-pipe/overview.md](../samurai/beam-pipe/overview.md) and [../samurai/beam-pipe/jis-flange-reference.md](../samurai/beam-pipe/jis-flange-reference.md) for the upstream pipe chain and flange standards.
- Use [../samurai/upstream-detector/questionnaire.en.md](../samurai/upstream-detector/questionnaire.en.md) when preparing external questions about the upstream detector installation boundary.

## Boundary Note

Within this folder, `BigRIPS` refers to the separator core and should not be used as a blanket synonym for the entire downstream `F0-F13` transport chain unless that broader scope is stated explicitly.
