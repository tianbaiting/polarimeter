# afterSRC Worklog

Purpose: detailed execution timeline for stateful runs and geometry iteration decisions.

Entry Template:
- Timestamp UTC:
- Timestamp Local:
- Intent:
- Command(s):
- Key Parameters/Overrides:
- Validation Result:
- State Snapshot:
- Artifacts:
- Next Action:

## Entries

- Timestamp UTC: 2026-03-27T00:54:37Z
- Timestamp Local: 2026-03-27 09:54:37 JST
- Intent: Validate the first `afterSRC` stateful build with front/rear `ICF114`, top `ICF70`, and no side pump/gauge/spare ports.
- Command(s): `./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
- Key Parameters/Overrides: new `afterSRC` target/config registered in `codex_targets.yaml`; beamline bore reduced to `63.0 mm`; front/rear welded stubs initially set to `pipe_od=63.5 mm`, `pipe_id=63.0 mm`, `pipe_len=80.0 mm`; top rotary interface set to direct `ICF70`.
- Validation Result: fail.
- State Snapshot: run_id=`20260327T005437Z-9`, run.status=`fail`, validation.status=`fail`.
- Artifacts: report `sha256=dbba60bf...`; failing check `chamber.vacuum_boundary_complete` with `solids=3, shells=3`.
- Next Action: inspect the vacuum-boundary fuse and identify which chamber/end-module interfaces remain disconnected.

- Timestamp UTC: 2026-03-27T00:56:13Z
- Timestamp Local: 2026-03-27 09:56:13 JST
- Intent: Revalidate after changing end-module pipe geometry to seat slightly into the chamber wall as well as the flange bore.
- Command(s): `./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
- Key Parameters/Overrides: shared end-module builder updated so welded stubs overlap the chamber wall by a finite seat distance instead of only face-touching; `ICF114` stub OD still `63.5 mm`.
- Validation Result: fail.
- State Snapshot: run_id=`20260327T005613Z-9`, run.status=`fail`, validation.status=`fail`.
- Artifacts: report `sha256=dbba60bf...`; `vacuum_boundary_complete` still fails because each `ICF114` stub remains a separate solid inside the flange bore.
- Next Action: eliminate the remaining clearance by matching the welded-stub OD to the `ICF114` flange bore.

- Timestamp UTC: 2026-03-27T00:57:42Z
- Timestamp Local: 2026-03-27 09:57:42 JST
- Intent: Revalidate after matching the `ICF114` welded-stub OD to the flange bore.
- Command(s): `./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
- Key Parameters/Overrides: front/rear `ICF114` `pipe_outer_diameter_mm` increased from `63.5` to `63.6` so the welded pipe shares the flange bore and fuses into a single solid with the chamber vacuum envelope.
- Validation Result: pass.
- State Snapshot: run_id=`20260327T005742Z-9`, run.status=`pass`, validation.status=`pass`.
- Artifacts: report `sha256=d2e61348...`; all chamber/plates/detector/target/stand checks pass.
- Next Action: run force-rebuild to export FCStd/STEP artifacts for the validated `afterSRC` geometry.

- Timestamp UTC: 2026-03-27T00:58:42Z
- Timestamp Local: 2026-03-27 09:58:42 JST
- Intent: Export FCStd/STEP artifacts for the strict-pass `afterSRC` chamber variant.
- Command(s): `./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --force-rebuild`
- Key Parameters/Overrides: finalized geometry uses front/rear `ICF114` welded beamline stubs, top `ICF70` rotary flange, `main_pump/gauge_safety/spare` disabled, and a vendor-reference envelope aligned to model `ICF70MRMF50`.
- Validation Result: pass.
- State Snapshot: run_id=`20260327T005842Z-9`, run.status=`pass`, validation.status=`pass`.
- Artifacts: FCStd `sha256=cceae38d...`, STEP `sha256=6abdf878...`, report `sha256=d2e61348...`.
- Next Action: run `infrontofSamuraiMag` regression validation and hand off the new `afterSRC` module.

- Timestamp UTC: 2026-04-24T00:44:16Z
- Timestamp Local: 2026-04-24 09:44:16 JST
- Module/Scope: Sub-2 Task 13 — strict-validate regression + force-rebuild after detector-clamp weldment redesign
- Command(s): `IFSM_SKIP_FCSTD_ROUNDTRIP=1 ./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --force-rebuild`
- Key Parameters/Overrides: `draw_fasteners_as_solids=true`; 330 viewprovider-bearing objects. Env-var `IFSM_SKIP_FCSTD_ROUNDTRIP=1` required because offscreen Qt + ~300+ Part::Feature VPs deadlocks during GUI init (FreeCAD #22870 class; our symptom was futex_wait_queue in 64/65 threads with frozen CPU). With the env var set, `ensure_fcstd_gui_session`, `_prepare_fcstd_gui_state`, and the `_verify_fcstd_roundtrip` reopen are all bypassed; FCStd is written without `GuiDocument.xml` (FreeCAD #23376 behavior) but opens fine in GUI with default visibility; archive-structure check replaces the reopen check.
- Validation Result: pass.
- State Snapshot: run_id=`20260424T004036Z-1670861`, run.status=`pass`, validation.status=`pass`, strict=`true`, git_head=`90a1e35`.
- Artifacts: FCStd `sha256=90768383...` (828 KB, no GuiDocument.xml), STEP `sha256=ddd25406...` (4.5 MB, 96142 entities), report `sha256=23dd465d...`.
- Next Action: proceed to Sub-2 Task 14 visual review (before/after screenshots) and Task 15 parts manifest + DoD sign-off.

- Timestamp UTC: 2026-04-24T09:51:10Z
- Timestamp Local: 2026-04-24 18:51:10 JST
- Module/Scope: Sub-2 Task 15 — emit `parts_manifest` in validation report and regenerate artifacts
- Command(s): `IFSM_SKIP_FCSTD_ROUNDTRIP=1 ./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --force-rebuild`
- Key Parameters/Overrides: added `build_clamp_parts_manifest(cfg, placements)` in `validation.py`; thread sizes derived via shared `_bolt_diameter_to_thread` helper (6 mm → M6, 9 mm clearance hole → M8). `report_to_dict` / `write_report_json` now forward the manifest; CLI builds it from the validated placements. Same env-var guard (`IFSM_SKIP_FCSTD_ROUNDTRIP=1`) still required for the 330-VP offscreen-Qt path.
- Validation Result: pass.
- State Snapshot: run_id=`20260424T094228Z-1761888`, run.status=`pass`, validation.status=`pass`, strict=`true`, git_head=`90a1e35`.
- Artifacts: FCStd `sha256=b2eb26b0...` (828 KB), STEP `sha256=5ae88a05...` (4.5 MB, 96142 entities), report `sha256=21fd18aa...` (now carries `parts_manifest` with 12 × 7 line items).
- Next Action: Sub-2 DoD sign-off doc at `docs/superpowers/specs/2026-04-17-sub2-dod-signoff.md`; await user approval for commit/cleanup of Phase 0 spike script.

- Timestamp UTC: 2026-07-26T17:07:33Z
- Timestamp Local: 2026-07-27 02:07:33 JST
- Intent: Regress the preserved external afterSRC route after CompactOne development and diagnose the incomplete v1.33 clamp migration.
- Command(s): `./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation --force-rebuild`
- Key Parameters/Overrides: first diagnostic run used the then-current v1.33 clamp schema directly; no geometry overrides.
- Validation Result: error before validation (`DetectorClampConfig.outer_diameter_mm` missing), proving the v1.33 schema had replaced fields still required by the validated external assembly.
- State Snapshot: the diagnostic error state was superseded by the successful rerun below; no generated CAD artifact was accepted from the failed run.
- Next Action: isolate the unfinished v1.33 prototype from the active external fixture contract and rerun strict validation.

- Timestamp UTC: 2026-07-26T17:07:33Z
- Timestamp Local: 2026-07-27 02:07:33 JST
- Intent: Strictly revalidate afterSRC with the last validated external fixture explicitly preserved alongside the unfinished v1.33 prototype.
- Command(s): `./afterSRC/run_afterSRC.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation --force-rebuild`
- Key Parameters/Overrides: `geometry.detector.active_fixture=external_reference_v1_31`; reference geometry parameters restored under the isolated `external_reference_fixture` namespace; v1.33 prototype schema retained unchanged.
- Validation Result: pass.
- State Snapshot: run_id=`20260726T170350Z-3938883`, run.status=`pass`, validation.status=`pass`, strict=`true`.
- Artifacts: validation report refreshed; validate-only intentionally did not replace FCStd/STEP.
- Next Action: execute the full final external-route regression and retain v1.33 as inactive until its assembly integration is complete.
