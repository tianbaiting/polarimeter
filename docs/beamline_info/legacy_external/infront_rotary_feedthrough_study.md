# 真空旋转馈通历史研究（legacy external）

> 状态：2026-09-01 归档标记。本文保留的是旧 `infrontofSamuraiMag`
> 外置探测器路线的候选件筛选笔记，不是当前 CompactInVacuum-afterSRC
> 的选型或采购依据。文中几何数值属历史配置，产品名称不能代替签字图纸。
> 当前 compact 旋转馈通仍是按部署关闭的工程研究包络。

## 1. 原始参考产品

- **Cosmotec 旋转導入器**: <https://en.cosmotec-co.jp/products/detail/4064>
- **原理**: 波纹管密封 (Bellows seal) 传递外部旋转至真空内部，保持 UHV 完整性。

---

## 2. legacy infrontofSamuraiMag 外置系统的历史机械约束

从 `external_version/infrontofSamuraiMag/config/profiles/side_exit_single_rotary_strict.yaml`
与 `external_version/infrontofSamuraiMag/src/ifsm/components.py` 提取的历史参数：

| 项目 | 值 | 来源 |
|------|------|------|
| 腔体顶壁端口 (port) | **side: top**, center_x = 70 mm | `ports.rotary_feedthrough` |
| 端口内径 / 外径 | **φ22 mm / φ42 mm** | 同上 |
| 端口凸出长度 | 80 mm | `length_mm` |
| 转轴直径 | **φ18 mm** | `feedthrough_shaft_diameter_mm` |
| 馈通总长度 | 120 mm | `feedthrough_length_mm` |
| 旋转轴心 (pivot) | x = 70 mm, y = 0, z = 0 | `pivot_x_mm` |
| 旋转轴方向 | **Y 轴** (顶部进入，在 xz 平面内摆臂) | `components.py:1426` |
| 摇臂长度 | 70 mm | `arm_length_mm` |
| 工作角 / 停车角 | 0° / 90° | `work_angle_deg / park_angle_deg` |
| 枢纽直径 | φ32 mm | `hub_diameter_mm` |
| 腔体内半高度 (half_y) | 92.5 mm (`size_y_mm / 2`) | `chamber.core` |

> **历史约束，仅适用于 external reference：** 馈通当时按φ22 mm 腔壁孔、
> φ42 mm 端口包络、x=70 mm 偏心轴和 0°→90° 行程建模。这些值不得传播到
> 当前 compact 设计。

---

## 3. 适用产品对比

### 3.1 Cosmotec 回転導入器（波纹管式，历史候选）
- **密封方式**: 波纹管 (Bellows seal)
- **法兰**: 旧笔记标为 ICF34；“外径约 70 mm”是名义系列混用，已作废。
  必须以所选型号的最新签字图纸确认法兰外径、孔径和刀口。
- **轴径**: ~φ10–18 mm | **烘烤**: ≤200°C | **寿命**: ~10,000 半圈
- **历史判断**: 当时因日本国内供应和 90° 行程而列入候选；法兰匹配和寿命未由签字图纸/寿命数据关闭。
- 🔗 **产品页**: <https://en.cosmotec-co.jp/products/detail/4064>
- 🔗 **全产品线 (Motion Feedthrough)**: <https://en.cosmotec-co.jp/products/list/23>
- 🔗 **MISUMI 购买**: <https://jp.misumi-ec.com/> (搜索 "Cosmotec 回転導入器")

### 3.2 UHV Design — MagiDrive MD40 系列（磁耦合，历史候选）
- **密封方式**: 磁耦合 (Magnetic coupling) — 完全无动密封，零颗粒
- **法兰**: CF40 / DN40CF (2.75″ OD)
- **轴**: 定制可选 | **扭矩**: 0.45–9 Nm | **烘烤**: ≤250°C
- **适用性**: 超长寿命，可配步进电机或手轮，适合最严格 UHV 场景
- 🔗 **官方产品页 (Solid shaft)**: <https://www.uhvdesign.com/products/rotary-drives/solid-magidrive/md40>
- 🔗 **官方产品页 (Hollow shaft)**: <https://www.uhvdesign.com/products/rotary-drives/hollow-magidrive/md40h>
- 🔗 **Lesker 代理购买**: <https://www.lesker.com/newweb/feedthroughs/magidrive_rotary_feedthroughs.cfm>

### 3.3 Kurt J. Lesker — DPRF 差分抽气旋转平台（历史特殊工况候选）
- **密封方式**: 差分抽气 (Differentially pumped)
- **法兰**: CF40 | **烘烤**: ≤150°C
- **适用性**: 支持 360° 连续旋转，0.1° 蜗轮刻度，有电机/手动版。需额外中间抽气口，体积较大。
- 🔗 **官方产品页**: <https://www.lesker.com/newweb/feedthroughs/diff_pumped_rotary_platforms.cfm>
- 🔗 **技术文档**: <https://www.lesker.com/newweb/feedthroughs/diff_pumped_rotary_platforms_technicalnotes.cfm>

### 3.4 Ferrotec — Ferrofluidic® 真空旋转馈通（历史候选）
- **密封方式**: 磁性流体密封 (Ferrofluidic seal)
- **法兰**: CF 系列 (含 CF40) | **轴径**: φ6–50 mm | **烘烤**: ≤150°C (可水冷)
- **适用性**: 极低泄漏 (< 10⁻¹¹ mbar·L/s)，高转速低摩擦，可定制轴径。日本有分公司。
- 🔗 **官方产品一览**: <https://www.ferrotec.com/products/vacuum-feedthroughs/rotary-feedthroughs>
- 🔗 **CF 法兰型号**: <https://www.ferrotec.com/products/vacuum-feedthroughs/rotary-feedthroughs/conflat-flange>
- 🔗 **日本分公司**: <https://www.ferrotec.co.jp/>

### 3.5 Phytron — VSS 真空步进电机（历史内置候选）
- **密封方式**: 电机直接置于真空中，无需旋转馈通
- **仅需电极引线** | **扭矩**: 0.01–5 Nm | **烘烤**: ≤200°C | **真空**: ≤10⁻¹¹ hPa
- **适用性**: 省空间、高精度 (0.01°)、无回程。但需电极馈通和散热设计。
- 🔗 **官方产品页**: <https://www.phytron.eu/vacuum-stepper-motors-for-vacuum-and-cryo>
- 🔗 **E-MotionSupply 购买**: <https://www.e-motionsupply.com/collections/phytron-vacuum-stepper-motors>

### 历史候选清单（无当前推荐顺序）

Cosmotec 波纹管式、UHV Design MagiDrive MD40 和 Ferrotec 磁性流体式仅保留为
历史筛选入口。重新选型时应从站点真空指标、轴径/轴长、载荷、扭矩、回差、寿命、
烘烤、漏率、维护包络和签字图纸重新建立比较矩阵。

---

## 4. 与 legacy external Target Chamber 的历史配合方式

### 4.1 物理安装

```
        [电机/手轮]
             │
    ═════════╪═════════  ← Motor Mount (120×90×16 mm)
             │
         Hard Stops
             │
        Index Disk
             │
    ─────────┼─────────  ← 腔壁顶面 (y = +92.5 mm)
      法兰密封面 (φ42 mm外径)
             │  ← 轴穿过 φ22 mm 孔洞
             │
         枢纽 Hub (φ32 mm)
             │
         摇臂 Arm (70 mm)
             │
         靶架 Holder (58×58 mm)
             │
      ──── 靶材 Target ──── ← z=0 (束流中心, work_angle=0°)
```

### 4.2 配合要点

1. **法兰密封（历史模型）**: φ42 mm 只是旧端口包络，不是标准法兰合同。
   不得把 ICF34 名称、φ42 mm 包络和 ICF70 尺寸混用；采购件必须整套使用对应刀口和 OFHC 铜垫片。
2. **轴心对齐**: 馈通轴中心必须与 `pivot_x_mm = 70.0` 精确对齐，通过端口的 `center_x_mm = 70.0` 保证。
3. **轴长匹配**: 总轴长 = 腔壁厚 (12 mm) + 端口凸出 (80 mm) + 额外密封段 ≈ 92.5 mm 外段 + 内部到 pivot 的距离。配置中 `feedthrough_length_mm = 120 mm` 是指从腔壁顶面到外端的总伸出。
4. **角度零点**: 将馈通的零刻度或编码器零点校准到 `work_angle_deg = 0°` (靶在束流上)。90° 位置 (park) 靶完全离开束流路径。
5. **硬限位**: 安装外部硬限位块 (hard_stop_span = 70 mm)，物理防止超出 0°–90° 范围。

---

## 5. 如何将候选件放入 legacy external CAD 模型

### Step 1: 修改端口尺寸（如选型法兰与现有不同）

编辑 `external_version/infrontofSamuraiMag/config/profiles/side_exit_single_rotary_strict.yaml`:

```yaml
ports:
  rotary_feedthrough:
    side: top
    center_x_mm: 70.0       # 保持与 pivot_x_mm 对齐
    center_y_mm: 0.0
    center_z_mm: 0.0
    inner_diameter_mm: 22.0  # ← 根据新选型轴径 + 间隙调整
    outer_diameter_mm: 42.0  # ← 根据新选型法兰外径调整
    length_mm: 80.0          # ← 端口管凸出高度
```

### Step 2: 修改旋转靶机构尺寸

```yaml
target:
  mode: single_rotary
  rotary:
    pivot_x_mm: 70.0
    feedthrough_shaft_diameter_mm: 18.0  # ← 新选型实际轴径
    feedthrough_length_mm: 120.0         # ← 新选型实际伸出长
    handwheel_diameter_mm: 110.0         # ← 手轮/皮带轮外径
    motor_mount_width_mm: 120.0          # ← 电机支架宽
    motor_mount_height_mm: 90.0          # ← 电机支架高
    motor_mount_thickness_mm: 16.0       # ← 电机支架厚
    hub_diameter_mm: 32.0                # ← 内部枢纽直径
    # arm / hard_stop / index 参数保持不变即可
```

### Step 3: 重新生成并验证

```bash
cd /home/tian/workspace/dpol/polarimeter
./external_version/infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml
```

系统将自动：
- 根据新尺寸生成 shaft、hub、arm、motor mount 等实体
- 在 `work_angle_deg` 和 `park_angle_deg` 下检测碰撞
- 切削 LOS 锥形通道确认靶臂不遮挡探测器视线
- 输出 `.FCStd` 和 `.step` 文件及 `validation_report.json`



## 中国产品 



中国科学院沈阳科学仪器股份有限公司 

电动磁力转轴

https://www.sky.ac.cn/productMechanies/178.html

手动磁力转轴. 
