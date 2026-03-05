# RCNP BLP 设计细节查询

## 1. 文档目标与范围

本文整理 RCNP（大阪大学核物理研究中心）WS 束流线 BLP（Beam Line Polarimeter）相关公开资料中的机械与工艺要点，面向本项目 FreeCAD 建模使用。重点关注：

- BLP 在 WS 束流线中的位置与功能
- 散射室开孔、窗口、密封与真空接口
- 靶梯（target ladder）与线性馈入机构
- 探测器几何与支撑思路
- 与本项目 `infrontofSamuraiMag` 设计参数的映射

本文不替代 RCNP 内部工程图纸；公开资料缺失的尺寸会明确标注为“待定参数”。

## 2. 已确认的核心几何与实验事实

### 2.1 BLP 几何与测量模式

- WS 束流线上使用 BLP1/BLP2 监测束流状态与极化，BLP 在设施布局图中有明确标注 [2][3][4]。
- BLP 水平面几何采用散射-反冲符合计数，典型角度为：
  - 散射角约 `17.0°`
  - 反冲角约 `69.7°` 或 `70.5°`（不同文献/版本略有差异）[2][3][4][5]。
- BLP 使用塑料闪烁体对（L/R/U/D）进行符合测量 [2][3][5]。

### 2.2 分析靶信息（公开文献）

- 曾使用 `CH2` 与 aramid（芳纶）作为分析靶 [2][3][4]。
- 文献中可见如下量级：
  - CH2 面密度：约 `8.4 mg/cm²`
  - aramid 面密度：约 `5.0 mg/cm²`
  - 另有薄膜厚度级别 `4 μm` 的 aramid 描述 [2][3]。

### 2.3 相关窗口与薄膜参数（公开文献）

注意：以下窗口参数中，部分来自 GR/VDC/气体靶系统，不全是“BLP 本体出射窗”直接尺寸，但对材料和薄膜工艺有直接参考价值。

- `Entrance/exit window`: `12.5 μm` aramid 或 carbon-aramid 薄膜 [3][5]。
- VDC cathode：`10 μm` carbon-aramid 薄膜 [3][5]。
- 气体靶 cell 示例：aramid 窗厚 `6 μm`，窗口尺寸约 `58W × 28H mm²` [2]。

## 3. 散射室机械设计要点（可直接映射到 CAD）

### 3.1 室体与主束流通道

- 室体形态：公开资料中可见“箱式/紧凑散射室”工程图与照片 [6]。
- 主束流轴应保留入口/出口通道，且出口可适度放大以降低边缘打束风险（工程上常用的背景抑制策略）。
- 材料优先非磁/弱磁不锈钢（如 304/316L）。

建议建模字段（参数化）：

| 参数 | 建议类型 | 当前值状态 |
|---|---|---|
| chamber 外形尺寸 | mm | 待定（由现场安装空间反推） |
| 壁厚 | mm | 待定 |
| 束流入口孔径 | mm | 参考级别：80–100（需现场确认） |
| 束流出口孔径 | mm | 建议不小于入口 |
| 入口/出口法兰标准 | 枚举 | 待定（CF/ISO 需选型） |

### 3.2 散射粒子窗口

- 窗口开孔应按运动学方向布置（至少覆盖 L/R 对；若包含 U/D 则补充垂直平面窗口）。
- 窗口结构建议采用：
  - 室壁开孔
  - 压环（retaining ring）
  - 薄膜（Kapton/aramid 方案二选一，按真空与散射损失折中）
- 薄膜厚度选型建议在文献可见范围内选点，并通过强度校核后定版。

建议建模字段：

| 参数 | 建议类型 | 当前值状态 |
|---|---|---|
| 窗口中心角度（水平） | deg | 可用：17.0, 69.7/70.5 相关几何派生 |
| 窗口开孔直径/扇角 | mm/deg | 待定 |
| 薄膜材料 | 枚举 | Kapton / aramid（待定） |
| 薄膜厚度 | μm | 参考级别：6, 10, 12.5 |
| 压环外径与厚度 | mm | 待定 |

### 3.3 真空接口

应预留：

- 泵口（涡轮分子泵）
- 真空计口
- 安全泄压/检修口

这些接口在 CAD 中应作为独立零件或标准件占位体，便于后续替换为具体法兰标准。

## 4. 靶梯（Target Ladder）与馈入机构

公开资料支持“多靶位 + 线性馈入”的结构思路 [2][6]。可按五槽位方案建模：

| 槽位 | 功能 | 典型内容 |
|---|---|---|
| 1 | 分析靶 | CH2 / aramid |
| 2 | 标定靶 | C 靶 |
| 3 | 观察屏 | 荧光屏 |
| 4 | 空框 | empty frame |
| 5 | 直通 | no target |

机构要点：

- 垂直导向（双导轨）
- 顶部线性馈入杆
- 波纹管真空隔离段
- 目标定位重复精度指标（工程目标）建议优于 `0.1 mm`（最终需实验团队确认）

## 5. 探测器与支撑结构

### 5.1 本项目约束（来自项目 readme）

本项目要求“探测器外壳为直径 `50 mm` 圆柱，前表面中心位于给定角度与半径”。当前约束为：

| 粒子通道 | 角度（lab） | 半径 |
|---|---:|---:|
| deuteron | 20.9° | 0.40 m |
| proton-1 | 11.2° | 0.62 m |
| proton-2 | 53.4° | 0.62 m |

这三组是本项目布置约束，不是 RCNP 原始 BLP 的一一复刻参数。

### 5.2 支撑建模建议

- 每个探测器至少包含：壳体、前端有效面、支撑杆、锁紧环。
- 支撑杆应从腔体壁面/窗口环引出，并预留长度调节余量。
- 建议为每个探测器对象写入属性：`AngleDeg`, `RadiusMM`, `FrontFaceConstraint`，方便后续自动校核。

## 6. 准直器与背景抑制

- 上游可配置铜准直器，文献中常见 `5 mm` 厚度量级 [7]。
- 准直孔径应与束斑和计数率目标联调；建议在 CAD 中独立建“可替换孔径插片”结构。

## 7. 公式与数据处理（简要）

极化计常见左右不对称定义可写为：

`epsilon = (N_L - N_R) / (N_L + N_R)`

并结合分析力 `A_y` 估算极化分量：

`P ≈ epsilon / A_y`

具体修正项（效率、背景、传输修正）应以对应实验论文分析章节为准 [2][3][5]。

## 8. 对本仓库 CAD 的落地建议

针对 `infrontofSamuraiMag`：

1. 采用“参数化装配”而非单体布尔模型。
2. 腔体、法兰、窗口环、薄膜、靶梯、馈入、探测器支撑全部拆为独立对象。
3. 所有关键尺寸写为脚本参数，禁止硬编码散落。
4. 导出 `FCStd + STEP` 两份，并保留对象命名语义化（便于审阅与二次开发）。

## 9. 当前缺失与待确认参数

以下内容在公开资料中缺乏“可加工级尺寸链”，需后续补充：

- BLP 本体散射室完整二维工程图（含法兰标准、孔系、公差）
- BLP 独立窗口组件（压环螺栓孔、预紧方式、膜片固定细节）
- 探测器支架装配图（调角机构、锁定方式、重复定位指标）
- 靶梯电机与丝杠规格（导程、扭矩、安全行程）

---

## 参考文献

[1] RCNP, Nuclear Science 1A Facilities. https://www.rcnp.osaka-u.ac.jp/Divisions/np1-a/facilities.html (accessed 2026-02-23).

[2] Matsubara, PhD Thesis (2010), RCNP. https://www.rcnp.osaka-u.ac.jp/Divisions/np1-a/thesis/Matsubara_PhD2010.pdf (accessed 2026-02-23).

[3] Nakamura, Master Thesis (2018), RCNP. https://www.rcnp.osaka-u.ac.jp/Divisions/np1-a/thesis/Nakamura_master2018.pdf (accessed 2026-02-23).

[4] Matsubara, Master Thesis (2005), RCNP. https://www.rcnp.osaka-u.ac.jp/Divisions/np1-a/thesis/Matsubara_master2005.pdf (accessed 2026-02-23).

[5] Zenihiro, PhD Thesis (2011), RCNP. https://www.rcnp.osaka-u.ac.jp/Divisions/np1-a/thesis/Zenihiro_PhD2011.pdf (accessed 2026-02-23).

[6] I Ou, PhD Thesis (2017), RCNP (Appendix B drawings). https://www.rcnp.osaka-u.ac.jp/Divisions/np1-a/thesis/IOu_PhD2017.pdf (accessed 2026-02-23).

[7] RCNP WS beam line note (CYC2001). https://epaper.kek.jp/c01/cyc2001/paper/P1-17.pdf (accessed 2026-02-23).

[8] RCNP WS beam line page (BLP sections). https://www.rcnp.osaka-u.ac.jp/Divisions/np1-a/ws/index.html (accessed 2026-02-23).
