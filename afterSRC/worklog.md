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
