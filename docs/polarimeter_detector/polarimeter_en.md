![1753452129490](./.polarimeter/1753452129490.png)

![1753452429094](./.polarimeter/1753452429094.png)

![1753452442226](./.polarimeter/1753452442226.png)

This waveform is not ideal, with many ripples. I suspect it may be a matching issue, or possibly the sampling rate is a bit low.

![1753963907599](./.polarimeter/1753963907599.png)

<!-- (The position of the polarimeter is not yet determined. Otsu intends to let us place it in the front.

Who should we contact?

Which area’s magnetic field? Is magnetic shielding needed?) -->

I do think it is indeed an impedance matching issue.

The following images are for 50 $\Omega$ 
![1754201471343](./.polarimeter/1754201471343.png)

The following images are for 1M $\Omega$

![1754201509818](./.polarimeter/1754201509818.png)

![alt text](assets/polarimeter/5e92409e4199b404d43dd7d3e700360.jpg)

Company’s test video

![1754201626480](./.polarimeter/1754201626480.png)

It can be seen that the oscilloscope used during the company’s test probably had a 1MΩ input impedance. The fall time is on the order of 40 microseconds. This parameter is also not ideal.

![1754204211169](./.polarimeter/1754204211169.png)

![alt text](assets/polarimeter/c4b3c19b5ea35a9e9f86ae1277d31b9.jpg)

Suspected to be a base readout issue. When the amplitude is reduced, these small signals have strong reflections. This may occur in the voltage divider circuit or the filter circuit, where strong reflections are present.

## Summary & Report

### Scintillator Luminescence Process

The luminescence process of a scintillator mainly includes the following stages:

1. **Energy Deposition**: High-energy particles (such as muons in cosmic rays) enter the scintillator material, rapidly depositing energy through ionization and excitation, on the timescale of picoseconds or femtoseconds.
2. **Excited State Formation**: Excited atoms or molecules form excited states (such as singlet and triplet states), which is the prerequisite for luminescence.
3. **Energy Transfer**: The excited states transfer energy to the luminescent center molecules via non-radiative processes (such as dipole-dipole interactions), occurring on the nanosecond scale.
4. **Radiative Transition**: The luminescent center molecules transition from the excited state back to the ground state, releasing photons (scintillation light). This process has a characteristic decay time, usually on the nanosecond scale.

### Analysis of Waveform "Ripples"

From a physical perspective, ripples at the top of the waveform are generally not caused by the scintillator itself, for the following reasons:

- **Exponential Decay Characteristic**: The scintillator luminescence process can be described by an exponential function (e.g., $I(t) = I_0 e^{-t/\tau}$). The pulse falling edge should be a smooth curve, without obvious ripples.
- **Instantaneous Energy Deposition**: The energy deposition by high-energy particles is extremely fast, and subsequent processes are continuous and smooth, not causing multiple peaks or fluctuations at the pulse top.
- **Oscillation Due to Impedance Mismatch**: In high-speed electronics, ripples or oscillations on the waveform are usually caused by impedance mismatch. When a signal encounters impedance mismatch on a transmission line, reflection occurs. The reflected signal superimposes with the original signal, causing oscillations in the waveform. The frequency and amplitude depend on the degree of mismatch and the transmission line length.

### Electromagnetic Principle of Impedance Matching

#### Transmission Line Model & Telegraph Equations

A transmission line can be regarded as a distributed parameter circuit composed of inductance $L$ and capacitance $C$ per unit length. According to Kirchhoff's laws, the voltage $V(x, t)$ and current $I(x, t)$ on the transmission line satisfy:

$$
\frac{\partial V(x, t)}{\partial x} = -L \frac{\partial I(x, t)}{\partial t}
$$

$$
\frac{\partial I(x, t)}{\partial x} = -C \frac{\partial V(x, t)}{\partial t}
$$

Combining these gives the wave equation, indicating that signals propagate as waves.

#### Signal Reflection & Reflection Coefficient

When a signal passes from a transmission line with characteristic impedance $Z_0$ to a load impedance $Z_L$, the reflection coefficient $\Gamma$ is:

$$
\Gamma = \frac{Z_L - Z_0}{Z_L + Z_0}
$$

- **Ideal Matching ($Z_L = Z_0$):** $\Gamma = 0$, no reflection, smooth waveform.
- **Open Circuit ($Z_L \to \infty$):** $\Gamma \approx 1$, full reflection, likely to cause trailing and distortion (as seen in the 1M$\Omega$ waveform).
- **Short Circuit ($Z_L \to 0$):** $\Gamma = -1$, full reflection with inverted signal.

Waveform ripples are usually caused by impedance mismatch, where reflected signals superimpose with the main signal, causing oscillations.

#### Derivation of Signal Reflection Coefficient

Let the transmission line have characteristic impedance $Z_0$ and the load impedance be $Z_L$. When the voltage wave reaches the end and $Z_L \neq Z_0$, part of the energy is reflected.

The relationship between incident and reflected waves is:

- Incident wave: $V^+$, $I^+ = \frac{V^+}{Z_0}$
- Reflected wave: $V^-$, $I^- = -\frac{V^-}{Z_0}$

Total voltage: $V_{\text{total}} = V^+ + V^-$  
Total current: $I_{\text{total}} = \frac{V^+}{Z_0} - \frac{V^-}{Z_0}$

According to Ohm's law, at the load: $V_{\text{total}} = Z_L I_{\text{total}}$. Substitute and rearrange to get:

$$
\frac{V^-}{V^+} = \frac{Z_L - Z_0}{Z_L + Z_0}
$$

Therefore, the reflection coefficient $\Gamma$ is:

$$
\Gamma = \frac{V^-}{V^+} = \frac{Z_L - Z_0}{Z_L + Z_0}
$$

---

#### Reflection from PMT Output to Cable

In practical applications, the PMT output can be regarded as a signal source with source impedance $Z_{\text{source}}$, and the cable as a transmission line with characteristic impedance $Z_0$.

When the PMT outputs a pulse signal to the cable, if $Z_{\text{source}} \neq Z_0$, signal reflection occurs. The reflection coefficient is defined as:

$$
\Gamma_{\text{source}} = \frac{Z_{\text{source}} - Z_0}{Z_{\text{source}} + Z_0}
$$

- **Ideal Matching**: $Z_{\text{source}} = Z_0$, $\Gamma_{\text{source}} = 0$, signal fully enters the cable, no reflection.
- **Impedance Mismatch**: $Z_{\text{source}} \neq Z_0$, $\Gamma_{\text{source}} \neq 0$, part of the signal is reflected back to the PMT, causing waveform distortion.

Impedance matching issues may occur not only between the transmission line and the load or PMT, but also within the filter circuit.
当 PMT 输出脉冲信号到电缆时，如果 $Z_{\text{source}} \neq Z_0$，会发生信号反射。此时，反射系数的定义为：

$$
\Gamma_{\text{source}} = \frac{Z_{\text{source}} - Z_0}{Z_{\text{source}} + Z_0}
$$

- **理想匹配**：$Z_{\text{source}} = Z_0$，$\Gamma_{\text{source}} = 0$，信号完全进入电缆，无反射。
- **阻抗不匹配**：$Z_{\text{source}} \neq Z_0$，$\Gamma_{\text{source}} \neq 0$，部分信号被反射回 PMT，导致波形畸变。

此处阻抗匹配的问题不仅可能发生在传输线和负载或者pmt之间，也发生在滤波电路之中。


