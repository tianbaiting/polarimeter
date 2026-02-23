# 极化探测器归档（当前默认摆放 + 保留 Sekiguchi 对照）

本目录用于整理 D_Polarization 中与极化探测器相关的内容：摆放计算、摆放后观测量、能量沉积。

## 默认摆放参数（相对靶点）
- Proton detector P1: `theta_lab = 53.4°`，距靶点 `620 mm`
- Proton detector P2: `theta_lab = 11.2°`，距靶点 `620 mm`
- Deuteron detector D: `theta_lab = 20.9°`，距靶点 `400 mm`

## 默认宽度参数
- `width_p1 = 40 mm`
- `width_p2 = 40 mm`
- `width_D = 40 mm`
- `width_p1_phi = 40 mm`
- `width_p2_phi = 40 mm`
- `width_D_phi = 40 mm`

## 当前默认参数下的探测器指标

### 1) 实验室系角覆盖
- `theta_p1_lab`: `51.551749° ~ 55.248251°`
- `theta_p2_lab`: `9.351749° ~ 13.048251°`
- `theta_D_lab`: `18.035211° ~ 23.764789°`
- `delta_phi1`: `4.604411°`
- `delta_phi2`: `19.031144°`

### 2) 对应质心系角覆盖
- 由 P1 覆盖映射到 `theta_D_cm`: `65.087742° ~ 72.281818°`
- 由 P2 覆盖映射到 `theta_D_cm`: `151.716673° ~ 159.698834°`
- D 探测器分支1对应 `theta_D_cm`: `79.874051° ~ 58.362800°`
- D 探测器分支2对应 `theta_D_cm`: `151.286642° ~ 160.623027°`

### 3) 摆放后观测量指标（示例点）
- `N_total4(theta1)/N_total4(theta2)`:
  - `pzz=0.0`: `0.361216`
  - `pzz=0.5`: `0.433111`
  - `pzz=1.0`: `0.528821`
- `R_LRUD=(N_LR-N_UD)/(N_LR+N_UD)`:
  - `pyy=0.0`: `0.000000`
  - `pyy=0.5`: `0.147493`
  - `pyy=1.0`: `0.302725`

## 指标是怎么计算的
- 运动学反解（实验室系/质心系）：`placement_and_geometry/src/function.cpp`
  - `func_theta_P_cm(...)`
  - `func_theta_D_c(...)`
  - `P_lab(...)`
- 摆放后观测量（计数与比值）：`post_placement_observables/src/ratio_2c_proton.cpp`
  - 截面积分：`int_cross_section0(...)`
  - 计数：`N0_count_1detector(...)`
- 左右/上下不对称：`post_placement_observables/src/R_LRUD.cpp`
  - `int_cross_section_LR(...)`
  - `int_cross_section_UD(...)`
  - `R_LRUD=(N_LR-N_UD)/(N_LR+N_UD)`
- 截面与极化输入数据来源：`source_data/DataOfCrosssectionAndPol/`
  - `DSigamaOverDOmega.txt`
  - `CompletSetOFT/T.txt`

## 各种粒子沉积能量是怎么计算的
- 主要在：`energy_deposition/energy_lise/energy_loss.py`
- 核心方法：
  - 从 LISE range / dE/dx 表建立插值（`interp1d`）
  - 用 `eloss(A, E0_A, dx, gER, gRE)` 计算给定厚度后的沉积能量
- 计算内容包括：
  - 质子沉积能（10 mm / 20 mm C8H8）
  - 氘核沉积能（dp 散射两分支）
  - DC 散射分支下 C 与 D 的沉积能
- ROOT 版能量-角度关系图在：`energy_deposition/root_analysis/plot_energyPeru_thetalab.cpp`

## 图放在哪里
- 摆放与角覆盖图：`placement_and_geometry/outputs/`
  - `Pol_angcover.png/.pdf`
  - `Pol_angcover_flipped.png/.pdf`
  - `ThetaLab_vs_ThetaDc_deg.png/.pdf`
- 摆放后观测量图：`post_placement_observables/outputs_cache/`
  - `N1vs_pzz.png/.pdf`
  - `N_total4_vs_pzz.png`
  - `Ratio_vs_pzz.png/.pdf`
  - `R_LRUD_vs_pyy.png/.pdf`
- 能量相关图：
  - `energy_deposition/root_analysis/Energy_vs_ThetaDc_deg.png/.pdf`
  - `energy_deposition/energy_lise/eloss.png`

## 说明
- 上述 `53.4° / 11.2° / 20.9°` 是当前默认摆放参数。
- Sekiguchi 参数与相关结果文件已保留在归档中，作为历史/对照参考（按你的要求不删除）。
- 上面列出的指标值是按当前源码公式复算整理；若直接运行 C++（TSpline3）或 notebook 插值，数值会有轻微差异。
