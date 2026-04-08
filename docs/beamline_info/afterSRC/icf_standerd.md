# ICF / CF Flange Standard Reference (UHV Optimized)

> **File name:** `icf_standard.md`  
> **Scope:** Quick engineering reference for ICF/CF (ConFlat) vacuum flanges in beamline and detector chamber design.  
> **Target:** High Vacuum (HV) to Ultra-High Vacuum (UHV) systems.

---

## 1. Naming & Identification (The "ICF114" Focus)

In Japanese industrial contexts (e.g., ULVAC, Cosmo), naming often uses the **Flange Outer Diameter (OD)**.

| Global DN Name | **Japan ICF Name** | Inch OD Name | Compatible Gasket |
| :--- | :--- | :--- | :--- |
| DN16CF | **ICF34** | 1.33" | DN16 |
| DN35/40CF | **ICF70** | 2.75" | DN40 |
| **DN63CF** | **ICF114** | **4.50"** | **DN63** |
| DN100CF | **ICF152** | 6.00" | DN100 |
| DN160CF | **ICF203** | 8.00" | DN160 |

---

## 2. Dimensional Data: ICF114 / DN63CF
This is the workhorse size for beamline diagnostic ports and pump interfaces.

| Parameter | Metric Value (mm) | Imperial Value (in) |
| :--- | :--- | :--- |
| **Flange OD** | 113.5 mm | 4.47 in (~4.5") |
| **Nominal ID (Bore)** | 63.6 mm | 2.50 in |
| **Bolt Circle (k)** | 92.2 mm | 3.63 in |
| **Flange Thickness (h)** | 17.5 mm | 0.69 in |
| **Number of Holes** | 8 | 8 |
| **Hole Diameter (d)** | 8.4 mm (Clearance) | 0.33 in |
| **Bolt Thread** | **M8 × 1.25** | 5/16-24 UNF |
| **Gasket OD / ID** | 82.4 / 63.6 mm | 3.24 / 2.50 in |

---

## 3. Engineering Checklists for Physics Experiments

### 3.1 Material & Magnetism (Critical)
* **Default:** 304L or 316L Stainless Steel.
* **Low Mu ($\mu_r$) Requirement:** For chambers near magnets or sensitive spectrometers, specify **316LN** or **316L(ESR)**. Standard 304/316 can become magnetic after machining/welding; 316LN stays stable ($\mu_r < 1.01$).
* **Hardness:** Flange must be harder than the copper gasket (typically HB > 150) to ensure the knife-edge does not deform.

### 3.2 Sealing Principle
CF flanges use a "Knife-Edge" to plastically deform an OFHC copper gasket. 
* **Leak-detection groove:** Ensure the flange has a small radial groove on the bolt-hole circle to allow helium to reach the gasket during leak testing.



---

## 4. Assembly: Bolt Torque Guide
Over-tightening can damage knife-edges; under-tightening causes leaks after bakeout.

| Size | Bolt Size | Torque (N·m) | Torque (ft-lb) |
| :--- | :--- | :--- | :--- |
| DN16 (ICF34) | M4 | 4 N·m | 3 ft-lb |
| DN40 (ICF70) | M6 | 12 - 15 N·m | 9 - 11 ft-lb |
| **DN63 (ICF114)** | **M8** | **18 - 22 N·m** | **13 - 16 ft-lb** |
| DN100 (ICF152) | M8 | 22 - 25 N·m | 16 - 18 ft-lb |

> **Crucial:** Always use **Silver-Plated Bolts** or **Anti-seize (MoS2)** for UHV bakeout systems to prevent bolt "cold-welding" (seizing).

---

## 5. Welding Guidelines (Chamber Port Planning)

### 5.1 The "Internal Weld" Rule
To avoid **Virtual Leaks** (trapped gas pockets):
1.  **Primary Seal:** Full penetration TIG weld on the **Vacuum Side** (internal).
2.  **Secondary Support:** Tack weld or discontinuous weld on the **Atmospheric Side** (external) only if structural support is needed.
3.  **Purge Gas:** Use High-Purity Argon (99.999%) during welding to prevent oxidation ("sugaring").

### 5.2 Recommended Port Prep
```text
[ Flange: ICF114 Bored ]
          ||
          || (Internal TIG Weld)
[ Pipe: OD 63.5mm / V2.5" ]
          ||
[ Chamber Wall: 316L/LN ]

## references

https://www.lesker.com/newweb/flanges/flanges_technicalnotes_conflat_1.cfm

https://www.yako-sangyo.co.jp/en/pages/101/

https://www-eng.lbl.gov/~shuman/XENON/OBSOLETE_ARCHIVE/LLNL%20documents/LANL_ASME_CF.pdf