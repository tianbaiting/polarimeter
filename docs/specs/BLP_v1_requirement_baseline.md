# BLP Mechanical Requirement Baseline v1

## 1. Purpose
本文件是当前机械设计需求的唯一基线，用于跨终端一致协作与上下文连续性。

## 2. Frozen Decisions
- target chamber 不使用圆锥过渡。
- 探测器全部位于 chamber 外部；chamber 不提供探测器信号穿腔接口。
- 三板拓扑：H+V+V，且三块板均偏离束流中心轴。
- 探测器系统：12 个位点（3 通道 × 上下左右）。
- 探测器夹具：两半抱箍，轴向分型；固定角度过渡块；全固定（无调节）；抱箍锁紧螺钉必须布置在探测体圆柱外侧两侧，不允许任何锁紧螺钉轴线穿过探测器圆柱包络或抱箍内孔中心带。
- 探测器夹具与板连接采用“探测器 + 抱箍 + 过渡块 + 桥接件 + 底座”共享同一局部刚体坐标系后整体旋转落板；板上 4 孔矩形由该刚体总成方向带出确定打孔位置”，不使用杆件支撑。
- 探测器夹具安装拓扑冻结为“底座 + 双立板 + 顶部桥接件 + 过渡块”，其中整套夹具相对探测体圆柱保持刚性参考关系，底座必须与夹具形成连续承载路径。
- 探测器夹具下部承载语义冻结为“仅支撑侧半抱箍带下侧平鞍座”，该平鞍座必须与过渡块直接贴合形成连续实体承载路径；非承载半抱箍仅负责压紧，不得长出下部承载实体；`detector.adapter_block.radial_standoff_mm` 字段保留但严格口径固定为 `0.0`。
- 探测器夹具承载件语义进一步冻结为“支撑侧半抱箍 + 过渡块 + 双立板 + 顶桥”为一体承力件；与板件连接的四孔底座板保持独立螺接件，不再把承载侧主路径拆成多个彼此贴合的分体件。
- 板件支撑语义冻结为“无 plate-tie 拉杆”：探测器夹具底座直接固定到板件，不引入板-底座间附加拉杆件。
- 当前照片式支撑方案不使用整体大底板；stand 只保留独立支撑脚、调平螺钉与垫片，不再保留覆盖三板下方的 monolithic stand base plate。
- 防转/防滑：机械限位肩 + 端面止挡。
- 板件防遮挡：按“有效靶心 -> 探测器有效面”的真实 LOS 管道做布尔让位；只切除与该 LOS 管道真实相交的板体材料，不允许用探测器到板面的正交投影去连成连续槽口；margin=5 mm。
- 三板全实体外置于 chamber 外部，板件与 chamber 不允许实体重叠；必要时通过挖孔/让位确保装配无干涉。
- 板件切除语义冻结为“只为 chamber 真实让位和 LOS/target 工作空间开口”；底座、支撑脚以及板与底座之间的结构区域不得驱动板体切除。
- 当 `H` 板贴近 `-y` 侧 chamber 时，如与 `down` 三个探测器包络或其“靶心 -> 探测器前表面圆”真实圆锥 LOS 相交，必须在 `H` 板上生成局部长方形让位孔；该矩形让位窗必须覆盖圆锥与板厚带的真实相交投影，禁止退化成仅按板中面圆截面估算的过小开口，也禁止把无关区域连成连续槽。
- 板位策略采用半自动：支持 `offset_mode=auto/manual`，自动模式按“最小外置 + safety gap”求板法向偏置，板内平移保留人工控制。
- 照片式板位冻结：`H` 板位于 `-y` 侧；`V1/V2` 保持 `+x/-x` 对称，并采用“首个 strict-pass 内收值 + 5 mm 制造裕量”的手工偏置。
- V1/V2 板净间距约束：净间距 >= 2 × 探测器外径（按 clamp 外径口径）。
- chamber 核心体采用细长长方体：当前 strict side-exit 基线 `chamber.core.size_x_mm=185.0`、`chamber.core.size_y_mm=185.0`、`chamber.core.size_z_mm=1200.0`、`chamber.core.center_z_mm=400.0`，即有效前后端面落在 `z=[-200.0,+1000.0] mm`，保持工作靶心左侧空间不再继续增加，同时把右侧后端沿束线方向再拉长约 `300 mm`；垂直 z 的横向尺度继续保持收紧，使 12 条通道优先从 `±x / ±y` 四个侧面出腔，而不是先撞 `+z` 面。
- chamber 侧向探测通道的开孔语义冻结为“有效靶点中心 -> 探测器前表面圆”的圆锥包络切腔；禁止再用固定直径圆柱近似整条 side-exit 通道。
- 靶机构：单靶旋转式，不再使用 3 位线性靶梯。
- 靶框：单靶可拆框架，双螺钉压板锁定。
- 驱动：电机在真空外，纯机械旋转馈通；机械止挡 + 计步校准；外部手轮应急；工作位使靶心落在束流中心，停靠位使整套 holder 偏心摆离 z 轴束流包络。
- 真空接口采用模块化合同冻结：`infrontofSamuraiMag` 保持前后 JIS 可更换模块，默认上游 `VF100` / 下游 `VG80`，接口装配语义为 `[ chamber ] -> welded round pipe stub -> [ flange ] <-> [ mating flange / equipment ]`；当前默认上游 stub 长 `100 mm`、下游 stub 长 `20 mm`；`VG` 侧在对外接口面带 O-ring groove，`VF` 侧不带 groove。
- `afterSRC` 真空接口合同冻结为：前后束流端面均为 `ICF114`，保留与 chamber 焊接的一段圆管 stub 用于和上下游束线接续；顶置靶旋转馈通安装面为 `ICF70` 直连法兰。
- chamber 端口按模块化合同冻结：`infrontofSamuraiMag` 保持主泵口 + 真空计/安全口 + 机械旋转馈通口 + 备用口（固定 4 口）；`afterSRC` 仅保留顶置 `rotary_feedthrough`，不再保留 `main_pump / gauge_safety / spare` 侧口；允许端口在所属壁面内做偏心布置以服务新 target rotary 机构。
- 主泵口在右侧；真空计/安全口在对侧。
- chamber 安装：放置于水平主板，改为 chamber 自支撑四柱 + `H` 板独立四柱，共 `8` 个支撑脚。
- 八支撑脚投影布局冻结为“两组独立四柱网格”：target chamber 自带 `4` 根支撑柱，位于 `x=±60 mm` 且 `z` 分别距离前后端面 `50 mm`；按当前基线即 `z=-150 mm` 和 `z=+950 mm`。`H` 板再由另外 `4` 根独立支撑柱承托，当前 strict 基线冻结为 `x=-24±200 mm`、`z=400 mm / 840 mm`，用于把 chamber 与 `H` 板的承载路径拆开并降低大板变形风险。
- 支撑高度语义冻结：stand 的落地基准必须由支撑柱给出，不允许 `V1/V2` 板先接地；当前基线要求支撑脚底面低于两块 `V` 板的最低 `y` 边界。
- 整机支架：地脚螺栓 + 长孔找正；调平螺钉 + 垫片；维护方向以上方与左右侧为主。

## 3. Coordinate and Geometry Basis
- 束线主轴：Z 轴。
- 单靶工作位有效靶心：原点 `(0, 0, 0)`。
- chamber 核心体：长方体（独立三轴尺寸）。
- chamber 前后统一接口面：平面密封，圆形螺栓阵列接口。
- 通道首出腔面（冻结）：
  - `left -> -x`
  - `right -> +x`
  - `up -> +y`
  - `down -> -y`
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
  - target.mode
  - target.rotary
  - target.single_holder
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
- 2026-04-08 v1.31:
  - 探测器夹具承载侧从“下半抱箍与过渡块/立板/桥接件直接接触的分体路径”收紧为“下半抱箍 + 过渡块 + 双立板 + 顶桥”的单件承力体。
  - 板侧 4 孔底座板继续独立保留为螺接安装件，形成“单件承载上体 + 独立底座板”的加工/装配语义。
- 2026-04-08 v1.30:
  - 探测器夹具下部承载路径从“抱箍附近过渡块”收紧为“仅支撑侧半抱箍下侧平鞍座 -> 过渡块 -> 双立板/桥接件 -> 底座”的连续实体路径。
  - `detector.adapter_block.radial_standoff_mm` 保留字段但严格口径固定为 `0.0`，禁止再在抱箍与下方支撑之间保留可见缝隙。
- 2026-04-08 v1.29:
  - 探测器夹具语义从“bridge-to-detector rigid pose”收紧为“detector + clamp + adapter + bridge + base 共享同一局部刚体坐标系并整体旋转落板”，禁止再按板法向对夹具子件做二次相对求姿。
  - 抱箍锁紧螺钉冻结为“圆柱外侧两侧切向夹紧”语义；螺钉轴线不得穿过探测器包络或抱箍内孔中心带。
- 2026-03-27 v1.28:
  - 将真空接口与端口规则改为按模块冻结：`infrontofSamuraiMag` 继续使用 `front=VF100 / rear=VG80 + fixed 4 ports`。
  - 新增 `afterSRC` 合同：`front=ICF114 / rear=ICF114`、顶置 `ICF70` 旋转馈通直连、禁用 `main_pump / gauge_safety / spare` 侧口。
  - `afterSRC` 束流通径按 `ICF114/DN63CF` 兼容口径收紧，不再沿用 `80 mm` 基线。
- 2026-03-27 v1.27:
  - 按最新装配意见，`H` 板独立四柱在 `x` 方向再略向外展开；当前冻结为 `x=-24.0±200.0 mm`，`z=400.0/840.0 mm`。
- 2026-03-27 v1.26:
  - chamber 四柱的前后端面内缩量从 `100 mm` 改为 `50 mm`，当前冻结为 `z=-150.0/+950.0 mm`，继续保持 `x=±60.0 mm`。
  - stand 支撑高度进一步加长，冻结语义为“支撑脚先落地，`V1/V2` 板不得先碰地”；当前 runtime 校验要求支撑脚底低于两块竖板的最低 `y` 边界。
- 2026-03-27 v1.25:
  - 右侧后端沿束线方向再加长约 `300 mm`，strict side-exit chamber 更新为 `size_z_mm=1200.0`、`center_z_mm=400.0`，对应前后端面 `z=[-200.0,+1000.0] mm`。
  - stand 从原先“chamber/H 共用四脚”切换为“chamber 自支撑四脚 + H 板独立四脚”共八脚布局；chamber 四脚冻结在 `x=±60.0 mm, z=-100.0/+900.0 mm`，`H` 板四脚冻结在 `x=-24.0±160.0 mm, z=400.0/840.0 mm`。
- 2026-03-26 v1.24:
  - `H` 板局部长方形让位窗的 LOS 口径收紧为“真实靶点 -> 探测器前表面圆”圆锥与板厚带的相交包络，禁止再用板中面圆截面近似，以免残留材料挡住圆锥通道。
  - 应最新装配观察，将前方那对 chamber-side 支撑脚从 `z=-200.0 mm` 回调到 `z=-150.0 mm`；`H` 板支撑排继续保持 `z=620.0 mm, x=-24.0±160.0 mm`。
- 2026-03-26 v1.23:
  - 应最新装配观察，将前方那对 chamber-side 支撑脚继续朝上游方向移动 `100 mm`，当前冻结为 chamber row `z=-200.0 mm, x=±50.0 mm`；`H` 板支撑排继续保持 `z=620.0 mm, x=-24.0±160.0 mm`。
- 2026-03-26 v1.22:
  - 四支撑脚从“远角底座投影”改为“两排居中支撑”：2 根落在 target chamber footprint 内、2 根落在 `H` 板 footprint 内，减少 `H` 板跨距与变形风险。
  - 当前 strict 基线冻结为 chamber row `z=250.0 mm, x=±50.0 mm`，H row `z=620.0 mm, x=-24.0±160.0 mm`。
- 2026-03-26 v1.21:
  - 按最新视觉要求，strict side-exit chamber 的左侧端面进一步缩到 `z=-200.0 mm`，右侧端面保持 `z=+700.0 mm`，因此核心体更新为 `size_z_mm=900.0`、`center_z_mm=250.0`。
  - 为保持固定四端口既落在缩短后的壳体侧壁范围内、又不遮挡左右通道 LOS，`main_pump / gauge_safety / spare` 的 `center_z_mm` 调整为 `-120 / -140 / -160 mm`。
- 2026-03-26 v1.20:
  - 为保留靶子右侧现有空间、缩短左侧过大空腔，strict side-exit chamber 的 z 向核心体改为不对称布置：`size_z_mm=1300.0`、`center_z_mm=50.0`，对应前后端面 `z=[-600.0,+700.0] mm`。
  - 前端 `VF100` 法兰与 chamber 之间的焊接圆管显著加长到 `100 mm`；后端 `VG80` 焊接圆管继续保持 `20 mm` 不变。
- 2026-03-26 v1.19:
  - chamber 前后真空接口装配语义切换为“腔体短管焊接到 JIS flange，再由 JIS flange 与外部 mating flange / equipment 螺栓连接”；默认 stub 长度冻结为上游 `10 mm`、下游 `20 mm`。
  - 当前 strict side-exit chamber 横向尺寸进一步收紧，冻结为 `chamber.core.size_x_mm=185.0`、`chamber.core.size_y_mm=185.0`，并保持工作靶心在 `(0,0,0)`。
- 2026-03-26 v1.18:
  - 当前 strict side-exit chamber 基线沿束线方向在 `1300.0 mm` 基础上再加长 `100 mm`，冻结为 `chamber.core.size_z_mm=1400.0`。
- 2026-03-26 v1.17:
  - chamber side-exit detector openings 从固定直径 LOS 圆柱切腔改为“有效靶点中心 -> 探测器前表面圆”圆锥包络切腔；rear end module 同步按该圆锥贯通开口。
- 2026-03-26 v1.16:
  - 默认真空接口从“上游 `VG150` / 下游 `VF80`”切换为“上游 `VF100` / 下游 `VG80`”，继续保持 `VG` 带 groove、`VF` 不带 groove 的类型语义。
  - 当前 strict side-exit chamber 基线沿束线方向再加长 100 mm，冻结为 `chamber.core.size_z_mm=1300.0`。
- 2026-03-23 v1.15:
  - 删除当前照片式支撑方案中的 monolithic stand base plate，冻结为“四支脚 + 调平螺钉 + 垫片”支撑。
  - `H` 板内收贴近 chamber 后，若与下方三路探测器包络或其真实 LOS 相交，改用局部长方形让位孔处理，不得切掉底座之间的整片区域。
- 2026-03-23 v1.14:
  - 板件开口口径从“板面投影连续槽”切换为“靶心到探测器的真实 LOS 管道布尔让位”，禁止再按 detector-to-plate projection 连接不同底座之间的空区。
- 2026-03-23 v1.13:
  - `H` 板从 `+y` 翻到 `-y` 服务侧，三块板按“首个 strict-pass 内收值 + 5 mm 制造裕量”重新冻结为更贴近 chamber 的照片式布局。
  - 板体切除语义冻结为“只为 chamber 真实让位和 LOS/target 工作空间开口”，禁止底座/支撑区域驱动大面积切板。
- 2026-03-19 v1.10:
  - 探测器安装语义更新为“bridge-to-detector rigid pose + fixture-driven drilling”；板上 4 孔矩形由总成方向带出，不再以板局部轴作为唯一孔位朝向基准。
  - 保留 `base + uprights + top bridge + adapter block` 连续承载路径，但允许立板长度随目标板法向落板位置变化。
- 2026-03-22 v1.11:
  - chamber 核心体冻结为“沿 z 拉长、横向收窄”的细长长方体；12 条通道首出腔面冻结为 `left/right/up/down -> -x/+x/+y/-y`。
  - 靶机构冻结为“单靶 + 顶置 Y 轴旋转 + 偏心摆出停靠”，删除当前活动设计中的 `3-position linear ladder` 冻结语义。
  - `ports` 参数允许在所属壁面内偏心定位，以支持 `rotary_feedthrough` 服务偏心单靶转轴。
- 2026-03-23 v1.12:
  - 三块板的探测器通道开口冻结为连续圆角槽口，不再使用会留下角落残片的扇形环带布尔切法。
  - `+z` 端下游接口冻结为 `VF80`，上游接口继续保持 `VG150`；`VG/VF` 的 groove 语义按类型区分而不是按前后位置写死。
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
