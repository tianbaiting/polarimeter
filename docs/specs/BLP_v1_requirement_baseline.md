# BLP Mechanical Requirement Baseline v1

## 1. Purpose
本文件是当前机械设计需求的唯一基线，用于跨终端一致协作与上下文连续性。

## 2. Frozen Decisions
- target chamber 不使用圆锥过渡。
- 探测器全部位于 chamber 外部；chamber 不提供探测器信号穿腔接口。
- 三板拓扑：H+V+V，且三块板均偏离束流中心轴。
- 探测器系统：12 个位点（3 通道 × 上下左右）。
- 探测器夹具：两半抱箍，轴向分型；固定角度过渡块；全固定（无调节）。
- 探测器夹具与板连接采用“沿板法向正交投影落板 + 4 孔矩形螺栓固定”，不使用杆件支撑。
- 探测器夹具安装拓扑冻结为“底座 + 双立板 + 顶部桥接件 + 过渡块”，底座必须与夹具形成连续承载路径。
- 板件支撑语义冻结为“无 plate-tie 拉杆”：探测器夹具底座直接固定到板件，不引入板-底座间附加拉杆件。
- 防转/防滑：机械限位肩 + 端面止挡。
- 板件防遮挡：按 LOS 视线包络开孔，规则扇形环带（大扇形减小扇形），margin=5 mm。
- 三板全实体外置于 chamber 外部，板件与 chamber 不允许实体重叠；必要时通过挖孔/让位确保装配无干涉。
- 板位策略采用半自动：支持 `offset_mode=auto/manual`，自动模式按“最小外置 + safety gap”求板法向偏置，板内平移保留人工控制。
- V1/V2 板净间距约束：净间距 >= 2 × 探测器外径（按 clamp 外径口径）。
- 靶切换：3 位线性靶梯（空靶 -> 实验靶 -> 荧光靶）。
- 靶框：统一可拆框架，双螺钉压板锁定。
- 驱动：电机在真空外，纯机械旋转馈通；机械止挡 + 计步校准；外部手轮应急。
- 真空接口：前后 JIS 可更换模块，默认上游 VG150 / 下游 VF150。
- chamber 端口：主泵口 + 真空计/安全口 + 机械旋转馈通口 + 备用口（固定 4 口）。
- 主泵口在右侧；真空计/安全口在对侧。
- chamber 安装：放置于水平主板，4 点支撑脚。
- 整机支架：地脚螺栓 + 长孔找正；调平螺钉 + 垫片；维护方向以上方与左右侧为主。

## 3. Coordinate and Geometry Basis
- 束线主轴：Z 轴。
- chamber 核心体：长方体（独立三轴尺寸）。
- chamber 前后统一接口面：平面密封，圆形螺栓阵列接口。
- 三板姿态语义（冻结）：
  - `plate.h`: `orientation=horizontal`, `mount_plane=xz`
  - `plate.v1`: `orientation=vertical`, `mount_plane=yz`
  - `plate.v2`: `orientation=vertical`, `mount_plane=yz`
- 扇区到板件映射（冻结）：
  - `left/right -> plate.h`
  - `up -> plate.v1`
  - `down -> plate.v2`

## 4. Parameterization Rules
- 命名：分组点号命名（如 `chamber.core.size_z_mm`）。
- 单位：长度 mm，角度 deg。
- 参数分组：
  - beamline
  - chamber.core
  - chamber.end_modules
  - ports
  - plate.h / plate.v1 / plate.v2
  - detector.clamp
  - detector.adapter_block
  - target.ladder
  - target.holder
  - stand
  - clearance
- 布局：`layout.channels[]` 显式通道表。
- 初值策略：可按旧图估算，但每个估算值需标注 confidence（high/medium/low）。

## 5. Validation Gate
LOS scope definition (frozen contract):
- LOS_v1_scope=概念几何遮挡检查（plate/port/stand 级遮挡）
- LOS_v2_scope=全路径物理无遮挡（源面 -> 腔体内有效通道 -> 探测器有效面）
- 当前冻结口径（本轮关账） = LOS_v1_scope

通过条件必须同时满足：
- 角度/半径命中
- LOS 无遮挡（v1 概念几何范围：plates / ports / stand；豁免：chamber_shell / end_modules / target_hardware / detector_packages）
- 无实体干涉（至少覆盖 detector package 对主装配碰撞矩阵）
- 真空边界完整

## 6. Required Artifacts
- FCStd
- STEP
- JSON 验收报告（按子系统汇总：chamber / plates / detector / target / stand）

## 7. Change Control
- 本文件为 v1 基线，修改必须追加版本记录，不覆盖历史决策。

## 8. Version History
- 2026-03-06 v1.9:
  - 冻结 `legacy_center_preview_locked` 阶段基线：三板按当前对齐坐标与尺寸固定，用于后续小步调参。
  - 预览阶段 `target.validation.strict=false`，保留报告输出但不阻断迭代节奏。
- 2026-03-06 v1.8:
  - 新增一次性“旧版板位预览模式”约束：允许将三板按 old-version 尺寸/坐标复刻用于视觉迭代。
  - 预览模式下允许关闭板件开孔与切让位（`disable_plate_cuts=true`），并跳过重叠类校验（`skip_overlap_checks=true`）。
  - 该模式仅用于几何比对与迭代，不作为最终关账口径。
- 2026-03-06 v1.7:
  - 冻结“无 plate-tie 拉杆”约束：夹具底座直接固定到板件。
  - LOS_v1 概念遮挡范围更新为 `plates / ports / stand`（不再含 `plate_ties`）。
- 2026-03-06 v1.6:
  - 冻结夹具安装拓扑：`base + uprights + top bridge + adapter block`，禁止“独立浮置底座”。
  - 新增 detector 子系统验收项：结构连续性、扇区落板映射、桥接长度上限。
  - 冻结板位“半自动”策略：`offset_mode=auto/manual` 与 `clearance.plate_auto_gap_mm`。
- 2026-03-06 v1.5:
  - 冻结三板法向语义：`H ⟂ Y (xz)`，`V1/V2 ⟂ X (yz)`。
  - 冻结板件分配：`left/right->h`，`up->v1`，`down->v2`。
  - 冻结探测器安装语义：沿板法向正交投影落板，4 孔矩形螺栓固定，禁用杆件支撑。
  - 冻结板件外置语义：三板全实体位于 chamber 外部。
  - 无实体干涉口径补充：v1 概念阶段 detector-package 碰撞矩阵豁免 `plate_ties`。
- 2026-03-06 v1.4:
  - 新增板件与 chamber 零重叠约束，要求通过板件挖孔实现。
  - 新增 V1/V2 净间距下限：`>= 2 * detector.clamp.outer_diameter_mm`。
- 2026-03-06 v1.3:
  - 冻结三板姿态坐标语义：`H=xy`，`V1/V2=yz`。
  - 冻结扇区到板件映射：`up/down->h`，`left->v1`，`right->v2`。
- 2026-03-05 v1.1:
  - 明确 LOS 验收的 v1 概念几何范围与豁免集合（见第 5 节）。
  - 明确“无实体干涉”至少覆盖 detector package 对全装配碰撞矩阵。
- 2026-03-05 v1.2:
  - 新增 `LOS_v1_scope` / `LOS_v2_scope` 显式定义。
  - 冻结本轮交付口径为 `LOS_v1_scope`，并明确 v2 为后续全路径物理无遮挡口径。
