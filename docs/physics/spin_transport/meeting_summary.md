# SRC-to-SAMURAI deuteron spin transport: meeting summary

## What happens to the density matrix in a magnetic field?

For deterministic transport, the spin-1 density matrix changes as

\[
\rho_f=U\rho_iU^\dagger.
\]

Its trace, eigenvalues, positivity, and purity \(\mathrm{Tr}\rho^2\) are unchanged. Vector polarization rotates as a vector; tensor polarization rotates as \(P'=RPR^T\).

## Does magnetic bending reduce polarization?

Not by itself. A common spin rotation changes the polarization-axis direction but not the density-matrix eigenvalues or intrinsic tensor magnitude. Effective depolarization occurs when the beam ensemble samples different spin rotations, when spin-dependent particles are lost, or when other nonunitary interactions matter.

The central distinction is:

\[
\boxed{\text{coherent tensor rotation}\ne\text{polarization loss}}.
\]

## What happens to pyy?

For an ideal horizontal bend produced by a vertical magnetic field, orbit and spin rotations are about \(y\). An axial tensor already oriented along \(y\) is invariant:

\[
p_{yy}'=p_{yy},\quad p_{xx}'=p_{zz}'=-p_{yy}/2,
\]

with no generated off-diagonal tensor components.

This is not guaranteed for the real lattice. Vertical bends, radial or longitudinal fields, steerers, solenoids, fringe fields, nonplanar transport, and coupling can rotate a vertical state.

## What happens to pzz?

An initially longitudinal tensor does not generally remain longitudinal after the beam bends. In the transported beam frame, for a horizontal relative rotation \(\delta\),

\[
p_{zz}'=p_T\left(\cos^2\delta-\frac12\sin^2\delta\right),
\]

\[
p_{xx}'=p_T\left(\sin^2\delta-\frac12\cos^2\delta\right),
\quad p_{yy}'=-p_T/2,
\]

\[
p_{xz}'=\frac32p_T\sin\delta\cos\delta.
\]

The tensor magnitude is preserved; its principal axis is no longer parallel to the local beam.

## What tensor components are generated from an initial pzz state?

An ideal horizontal bend generates \(p_{xx}\), modifies \(p_{zz}\), keeps \(p_{yy}=-p_T/2\), and generates \(p_{xz}\). It does not generate \(p_{xy}\) or \(p_{yz}\) in this ideal planar case.

For the explicitly illustrative case \(p_T=0.8\) and a +30 degree orbit bend:

- \(\delta=-5.15870\) degrees;
- \(p_{xx}=-0.39030\);
- \(p_{yy}=-0.40000\);
- \(p_{zz}=0.79030\);
- \(p_{xz}=-0.10746\).

This 30 degree bend is not asserted for the SRC-to-SAMURAI line.

## How much does the spin rotate for a given beam bend at 190 MeV/u?

Using 2022 CODATA values:

- \(m_dc^2=1875.612945\) MeV;
- \(G_d=-0.14298727\);
- \(\gamma=1.20260044\) at 380 MeV total kinetic energy;
- \(G_d\gamma=-0.17195655\).

For a simple transverse magnetic dipole,

\[
\delta=G_d\gamma\theta_{\rm orbit}.
\]

| Orbit bend | Spin relative to new beam |
| ---: | ---: |
| 1 degree | -0.17196 degree |
| 3 degrees | -0.51587 degree |
| 5 degrees | -0.85978 degree |
| 10 degrees | -1.71957 degrees |
| 20 degrees | -3.43913 degrees |
| 30 degrees | -5.15870 degrees |

## What can the afterSRC polarimeter measure?

It measures d-p scattering counts, not the density matrix directly. With known analyzing powers, calibrated efficiencies, several polar angles, and an assumed state model, it can estimate tensor magnitude and selected tensor-axis components at the upstream station. It provides \(\rho_{\rm afterSRC}\) only through measured projections and model assumptions.

## What can the pre-SAMURAI polarimeter measure?

It measures the same kinds of projections in the local downstream beam frame. In a transported longitudinal mode, the generated \(p_{xz}\) produces a first-harmonic left-right signal through \(A_{xz}\). The downstream station can therefore be sensitive to tensor-axis rotation, not only to a change in tensor magnitude.

## Can comparing the two determine the spin-transfer angle?

Yes for a constrained planar axial model, in principle. Fit tensor magnitude, orientation angle, and normalization at both stations using multiple angular channels. The angle difference tests the spin-transfer prediction.

No for a completely general density matrix or arbitrary 3D spin transfer using only one four-sector detector ring. A general tensor has five independent components, vector polarization adds three, and detector/beam nuisances add more. General transport requires multiple non-collinear source modes, multiple analyzing-power channels, calibrated efficiencies, and beam tracking.

The ideal two-channel Fisher demonstration gives roughly \(\sigma(p_T)=0.0063\) and \(\sigma(\delta)=0.195\) degree for an unpolarized normalization of \(10^5\) counts per forward sector, with fixed analyzing powers and no background/systematic uncertainty. This is a sensitivity demonstration, not a final forecast.

## What information about the actual RIKEN magnet lattice is still needed?

- Exact primary-deuteron reference trajectory from afterSRC to pre-SAMURAI.
- Ordered magnet names and types.
- Signed bend axes and bend angles or calibrated field integrals/3D field maps.
- Actual currents and optics settings for the polarized-deuteron tune.
- Energy at every element.
- Quadrupole, steerer, solenoid, and fringe-field information.
- Momentum spread, emittance, and measured phase space at both stations.

The public and repository material confirms the PIS/Wien-filter and AVF-RRC-SRC chain, but does not contain a complete sourceable SRC-to-pre-SAMURAI lattice. The 30 degree SAMURAI spectrometer configuration is downstream of the target and must not be used as the upstream transport bend.

## How stable must beam position and angle be?

The current point-detector model includes the two compact proton channels, tabulated cross sections/analyzing powers, geometry, and a fit that incorrectly assumes a centered beam. Representative biases are:

- pzz mode, +1 mm horizontal offset: \(\Delta p_T=-0.0037\), \(\Delta\delta=+0.39\) degree;
- pzz mode, +1 mrad horizontal angle: \(\Delta p_T=-0.00042\), \(\Delta\delta=-0.061\) degree;
- pyy mode, +1 mm vertical offset: \(\Delta p_T=-0.00115\), apparent vertical-axis tilt \(-1.02\) degrees;
- pyy mode, +1 mrad vertical angle: \(\Delta p_T=-0.00019\), apparent tilt \(-0.058\) degree.

These values show which nuisance directions are dangerous. They are not final alignment tolerances because finite detector acceptance, tracking resolution, backgrounds, and simultaneous nuisance fitting are not yet included. Beam position and direction should be measured event-by-event or spill-by-spill and included in the polarization likelihood.

## Immediate experimental conclusion

For an ideal horizontal bend, vertical axial pyy is robust because its tensor axis is the precession axis. Longitudinal pzz is different: the spin does not follow the momentum exactly, so the downstream local-frame state contains pxx and pxz in addition to pzz. The A_xz analyzing power makes this rotation measurable through left-right counts. Comparing afterSRC and pre-SAMURAI is therefore a direct monitor of spin transport, provided the actual lattice, beam trajectory, analyzing powers, and detector response are constrained.
