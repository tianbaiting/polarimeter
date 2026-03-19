# infrontofSamuraiMag v1 实施计划（按基线冻结语义）

## 0. 约束与入口
- 只走状态化入口：`./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml`
- 严格流水线：Spec(`target.yaml`) -> Generator -> Validator -> Artifacts -> `state.json`
- 不手改 `state.json` / `state.lock`
- 需求冲突处理：先改 `docs/specs/BLP_v1_requirement_baseline.md`，再改代码

## 1. P0 阶段（必须先全通过）
### 1.1 三板拓扑与装配
- H/V/V 姿态固定：`h=horizontal/xz`，`v1,v2=vertical/yz`
- 扇区映射固定：`left/right->h`，`up->v1`，`down->v2`
- 三板均偏离束流轴
- 三板全实体外置于 chamber 外
- 三板均包含承重语义：主板+连接耳+螺栓孔+加劲肋
- 探测器安装采用“桥接件相对探测体圆柱刚性固定 + 4孔矩形由总成方向带出确定打孔位置”
- 禁止使用杆件支撑

验收：
- `plate_pose_valid_hvv=pass`
- `all_plates_offset_from_beam_axis=pass`
- `load_path_complete=pass`
- `detector_mount_bridge_pose_fixed_relative_to_detector_body=pass`
- `detector_mount_hole_pattern_derived_from_fixture_direction=pass`
- `detector_mount_bolt_pattern_4hole_rectangular=pass`

### 1.2 LOS/干涉硬验证
- 板件开孔采用规则扇形环带（大扇形减小扇形）
- `margin=5mm` 生效
- LOS 检查分两层：命中本板开孔 + 对其余潜在遮挡体逐体检查
- 探测器无干涉使用实体相交体积判定（非中心距）

验收：
- `los_unobstructed_margin_5mm=pass`
- `los_all_occluders_clear=pass`
- `no_detector_interference=pass`

## 2. P1 阶段（结构语义补齐）
### 2.1 前后可替换接口模块
- 前 VG150 / 后 VF150
- 平面密封面
- 圆周螺栓阵列
- O-ring 槽

验收：
- `end_module_standard=pass`
- `end_module_interface_complete=pass`

### 2.2 靶梯驱动语义
- 3 位线性靶梯（空靶/实验靶/荧光靶）
- 电机安装结构
- 机械止挡
- 计步/索引校准结构
- 外部手轮应急保留

验收：
- `linear_3_position_ladder=pass`
- `drive_semantics_complete=pass`
- `external_rotary_feedthrough_drive=pass`

### 2.3 真空边界与端口语义
- 固定 4 口：主泵口/真空计安全口/机械旋转馈通/备用口
- 主泵口右侧、真空计安全口对侧
- 不允许探测器信号穿腔端口（由端口定义推导，不允许硬编码恒真）

验收：
- `fixed_4_ports=pass`
- `vacuum_boundary_complete=pass`
- `no_detector_signal_feedthrough_port=pass`

## 3. P2 阶段（一致性与测试）
### 3.1 文档与配置一致
- `README.md` 参数树与 `config/default_infront.yaml` 同步
- 命令示例与 stateful 流程一致

### 3.2 测试覆盖
- 配置约束测试：板姿态、端口语义、驱动参数
- 几何验证测试：LOS 全遮挡、无干涉、装配关系（在 FreeCAD 可用时执行）

## 4. 每次迭代固定回归
1. `infrontofSamuraiMag/.venv-pytest/bin/python -m pytest -q infrontofSamuraiMag/tests`
2. `./infrontofSamuraiMag/run_infrontofSamuraiMag.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
3. 需要重建产物时再执行：`--force-rebuild`

完成判据：
- `infrontofSamuraiMag.validation_report.json` 总状态 `status=pass`
- 产物包含 `FCStd`、`STEP`、JSON 验收报告（chamber/plates/detector/target/stand）

## 5. 迭代记录
- 2026-03-05 Iteration-01:
  - 探测器夹具补充抱箍耳板、贯穿螺栓位、防转键几何与参数约束。
  - 靶框补充双螺钉压板实体（每个 holder 2 螺钉）。
  - 验证补充 `clamp_fastening_and_key_features` 与 `removable_holder_dual_screw_clamp` 几何语义检查。
- 2026-03-05 Iteration-02:
  - chamber 前后接口补充紧固件硬件层：螺栓、垫圈、螺母实体。
  - 配置新增 `interface_bolt_* / interface_nut_* / interface_washer_*` 参数与约束。
  - 验证补充 `end_module_fastener_hardware`，按前后法兰螺栓阵列计数验收。
- 2026-03-05 Iteration-03:
  - 三板到底座承重连接件细化为“连接柱+上下压板+贯穿螺栓”实体。
  - stand 新增 `plate_tie_*` 参数与约束。
  - 验证补充 `plate_to_stand_tie_hardware` 与 `plate_tie_parameterized`。
- 2026-03-05 Iteration-04:
  - P1-1: 增加探测器包络对全装配（chamber/end modules/ports/plates/ties/target/stand）碰撞矩阵检查，补齐“无实体干涉”覆盖面。
  - P1-2: LOS 遮挡验证范围从隐式实现改为显式语义（代码与基线一致），并在报告中给出遮挡体范围说明。
  - P1-3: 真空边界从“参数关系”升级到“几何闭合/连通性”联合检查。
  - P2-1: 补环境复现说明（pytest/PyYAML 依赖与专属虚拟环境）。
- 2026-03-05 Iteration-05:
  - LOS 口径冻结：基线增加 `LOS_v1_scope` / `LOS_v2_scope` 显式定义，并标注本轮冻结口径为 `LOS_v1_scope`。
  - v1 关账：按 stateful 严格流水线完成 validate-only 与导出，`state.json.status=pass`，并归档 `state.json` 与 `validation_report.json`。
  - v2 开始：新增 `geometry.clearance.los_scope` 与 `geometry.chamber.los_channels.*` 参数；v2 下 LOS 路径改为 `source_plane -> chamber_effective_channels -> detector_active_face`，并将 `chamber/end_modules/target/stand` 纳入遮挡判定。
  - 测试分层：新增 `pure_python` / `freecad_runtime` marker，提供 `run_tests_layered.sh` 与 `scripts/precheck_test_env.py` 做依赖预检查与分层执行。
- 2026-03-06 Iteration-06:
  - 冻结并实施板姿态语义统一：`h=horizontal/xy`，`v1/v2=vertical/yz`。
  - 冻结并实施扇区映射：`up/down->h`，`left->v1`，`right->v2`。
  - 配置解析/建模/验证统一支持 `mount_plane=yz`，并补板件最小包络验收门（配置驱动，不自动扩板）。
- 2026-03-06 Iteration-07:
  - 板件与 chamber 干涉改为“全板总成布尔挖孔”，默认余量 `5 mm`。
  - 新增 `vv_min_gap_factor` 与 `plate_chamber_cutout_margin_mm`，冻结 V1/V2 净间距门为 `>=2*detector.clamp.outer_diameter_mm`。
  - 验证补充 `vv_clear_gap_vs_detector_outer_diameter` 与 `no_plate_chamber_overlap_after_cutout`，并将“探测器在板上”升级为桥接体与目标板实体交叠检查。
- 2026-03-06 Iteration-08:
  - 冻结三板新法向语义：`H⊥Y (xz)`，`V⊥X (yz)`；冻结映射：`left/right->h`，`up->v1`，`down->v2`。
  - 探测器安装改为“沿板法向正交投影落板 + 4孔矩形螺栓固定”，移除杆件支撑。
  - 三板统一外置于 chamber 外部，并保持板-腔体零重叠验收门。
