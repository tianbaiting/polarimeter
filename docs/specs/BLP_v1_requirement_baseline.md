# BLP Mechanical Requirement Baseline v1

## 1. Purpose
本文件是当前机械设计需求的唯一基线，用于跨终端一致协作与上下文连续性。

## 2. Frozen Decisions
- target chamber 不使用圆锥过渡。
- 探测器全部位于 chamber 外部；chamber 不提供探测器信号穿腔接口。
- 三板拓扑：H+V+V，且三块板均偏离束流中心轴。
- 探测器系统：12 个位点（3 通道 × 上下左右）。
- 探测器夹具：两半抱箍，轴向分型；固定角度过渡块；全固定（无调节）。
- 防转/防滑：机械限位肩 + 端面止挡。
- 板件防遮挡：按 LOS 视线包络开孔，规则扇形环带（大扇形减小扇形），margin=5 mm。
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
- LOS 无遮挡（v1 概念几何范围：plates / plate_ties / ports / stand；豁免：chamber_shell / end_modules / target_hardware / detector_packages）
- 无实体干涉（至少覆盖 detector package 对全装配的碰撞矩阵）
- 真空边界完整

## 6. Required Artifacts
- FCStd
- STEP
- JSON 验收报告（按子系统汇总：chamber / plates / detector / target / stand）

## 7. Change Control
- 本文件为 v1 基线，修改必须追加版本记录，不覆盖历史决策。

## 8. Version History
- 2026-03-05 v1.1:
  - 明确 LOS 验收的 v1 概念几何范围与豁免集合（见第 5 节）。
  - 明确“无实体干涉”至少覆盖 detector package 对全装配碰撞矩阵。
- 2026-03-05 v1.2:
  - 新增 `LOS_v1_scope` / `LOS_v2_scope` 显式定义。
  - 冻结本轮交付口径为 `LOS_v1_scope`，并明确 v2 为后续全路径物理无遮挡口径。
