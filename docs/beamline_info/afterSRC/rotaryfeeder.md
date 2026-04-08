# 真空旋转馈通 (Vacuum Rotary Feedthrough) — 选型与集成指南

## 1. 原始参考产品

- **Cosmotec 旋转導入器**: <https://en.cosmotec-co.jp/products/detail/4064>
- **原理**: 波纹管密封 (Bellows seal) 传递外部旋转至真空内部，保持 UHV 完整性。

---

## 2. infrontofSamuraiMag 系统机械约束

从 `config/profiles/side_exit_single_rotary_strict.yaml` 与 `src/ifsm/components.py` 提取的关键参数：

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

> **关键约束**: 馈通必须能穿过 **φ22 mm 的腔壁孔**并安装于 **φ42 mm 外径法兰面**上。轴在真空内沿 Y 轴旋转，偏心距 70 mm，行程 0°→90°（约四分之一圈），带硬限位 (hard stop)。

---

## 3. 适用产品对比

### 3.1 Cosmotec 回転導入器 (波纹管式) ✅ 推荐
- **密封方式**: 波纹管 (Bellows seal)
- **法兰**: ICF34 (外径 ≈70 mm)
- **轴径**: ~φ10–18 mm | **烘烤**: ≤200°C | **寿命**: ~10,000 半圈
- **适用性**: 日本国内供应，法兰尺寸最接近端口外径 φ42 mm，仅 90° 行程完全在寿命范围内
- 🔗 **产品页**: <https://en.cosmotec-co.jp/products/detail/4064>
- 🔗 **全产品线 (Motion Feedthrough)**: <https://en.cosmotec-co.jp/products/list/23>
- 🔗 **MISUMI 购买**: <https://jp.misumi-ec.com/> (搜索 "Cosmotec 回転導入器")

### 3.2 UHV Design — MagiDrive MD40 系列 (磁耦合) ✅ 推荐
- **密封方式**: 磁耦合 (Magnetic coupling) — 完全无动密封，零颗粒
- **法兰**: CF40 / DN40CF (2.75″ OD)
- **轴**: 定制可选 | **扭矩**: 0.45–9 Nm | **烘烤**: ≤250°C
- **适用性**: 超长寿命，可配步进电机或手轮，适合最严格 UHV 场景
- 🔗 **官方产品页 (Solid shaft)**: <https://www.uhvdesign.com/products/rotary-drives/solid-magidrive/md40>
- 🔗 **官方产品页 (Hollow shaft)**: <https://www.uhvdesign.com/products/rotary-drives/hollow-magidrive/md40h>
- 🔗 **Lesker 代理购买**: <https://www.lesker.com/newweb/feedthroughs/magidrive_rotary_feedthroughs.cfm>

### 3.3 Kurt J. Lesker — DPRF 差分抽气旋转平台 ⚠️
- **密封方式**: 差分抽气 (Differentially pumped)
- **法兰**: CF40 | **烘烤**: ≤150°C
- **适用性**: 支持 360° 连续旋转，0.1° 蜗轮刻度，有电机/手动版。需额外中间抽气口，体积较大。
- 🔗 **官方产品页**: <https://www.lesker.com/newweb/feedthroughs/diff_pumped_rotary_platforms.cfm>
- 🔗 **技术文档**: <https://www.lesker.com/newweb/feedthroughs/diff_pumped_rotary_platforms_technicalnotes.cfm>

### 3.4 Ferrotec — Ferrofluidic® 真空旋转馈通 ✅
- **密封方式**: 磁性流体密封 (Ferrofluidic seal)
- **法兰**: CF 系列 (含 CF40) | **轴径**: φ6–50 mm | **烘烤**: ≤150°C (可水冷)
- **适用性**: 极低泄漏 (< 10⁻¹¹ mbar·L/s)，高转速低摩擦，可定制轴径。日本有分公司。
- 🔗 **官方产品一览**: <https://www.ferrotec.com/products/vacuum-feedthroughs/rotary-feedthroughs>
- 🔗 **CF 法兰型号**: <https://www.ferrotec.com/products/vacuum-feedthroughs/rotary-feedthroughs/conflat-flange>
- 🔗 **日本分公司**: <https://www.ferrotec.co.jp/>

### 3.5 Phytron — VSS 真空步进电机 (内置方案) ⚠️
- **密封方式**: 电机直接置于真空中，无需旋转馈通
- **仅需电极引线** | **扭矩**: 0.01–5 Nm | **烘烤**: ≤200°C | **真空**: ≤10⁻¹¹ hPa
- **适用性**: 省空间、高精度 (0.01°)、无回程。但需电极馈通和散热设计。
- 🔗 **官方产品页**: <https://www.phytron.eu/vacuum-stepper-motors-for-vacuum-and-cryo>
- 🔗 **E-MotionSupply 购买**: <https://www.e-motionsupply.com/collections/phytron-vacuum-stepper-motors>

### 推荐优先级

1. **Cosmotec ICF34 波纹管式** → 日本国内采购方便、法兰尺寸匹配、波纹管密封简单可靠，仅 90° 行程完全在寿命范围内。
2. **UHV Design MagiDrive MD40 (CF40)** → 如需更高真空度或更长寿命，磁耦合是最优选择。
3. **Ferrotec 磁性流体式** → 如需高速连续旋转（例如未来换为连续旋转靶），Ferrotec 性能最强。

---

## 4. 与 Target Chamber 的配合方式

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

1. **法兰密封**: 选型产品的安装法兰必须匹配腔体端口的 φ42 mm 外径密封面。对于 ICF34, 使用无氧铜 (OFHC) 垫圈或金属密封环。
2. **轴心对齐**: 馈通轴中心必须与 `pivot_x_mm = 70.0` 精确对齐，通过端口的 `center_x_mm = 70.0` 保证。
3. **轴长匹配**: 总轴长 = 腔壁厚 (12 mm) + 端口凸出 (80 mm) + 额外密封段 ≈ 92.5 mm 外段 + 内部到 pivot 的距离。配置中 `feedthrough_length_mm = 120 mm` 是指从腔壁顶面到外端的总伸出。
4. **角度零点**: 将馈通的零刻度或编码器零点校准到 `work_angle_deg = 0°` (靶在束流上)。90° 位置 (park) 靶完全离开束流路径。
5. **硬限位**: 安装外部硬限位块 (hard_stop_span = 70 mm)，物理防止超出 0°–90° 范围。

---

## 5. 如何将新选型放入 infrontofSamuraiMag CAD 模型

### Step 1: 修改端口尺寸（如选型法兰与现有不同）

编辑 `config/profiles/side_exit_single_rotary_strict.yaml`:

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
cd /home/tian/workspace/dpol/polarimeter/infrontofSamuraiMag
./run_infrontofSamuraiMag.sh
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

