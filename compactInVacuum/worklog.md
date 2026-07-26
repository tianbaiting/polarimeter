# compactInVacuum Worklog

Purpose: module-level command/result timeline for the compact in-vacuum polarimeter pipeline.

Entry Template:
- Timestamp UTC:
- Timestamp Local:
- Module/Scope:
- Command(s):
- Key Parameters/Overrides:
- Validation Result:
- Artifacts/State:
- Next Action:

## Entries

- Timestamp UTC: 2026-04-12T11:45:40Z
- Timestamp Local: 2026-04-12 20:45:40 JST
- Module/Scope: compactInVacuum (full stateful build/export)
- Command(s): `./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml`
- Key Parameters/Overrides: default target `compactInVacuum/target.yaml`; strict validation enabled; no overrides
- Validation Result: pass
- Artifacts/State: `state.json.run.status=pass`, `validation.status=pass`, `compactInVacuum.FCStd`, `compactInVacuum.step`, and `compactInVacuum.validation_report.json` regenerated
- Next Action: provide artifact paths to the user and collect follow-up geometry changes if needed.

- Timestamp UTC: 2026-04-13T02:16:32Z
- Timestamp Local: 2026-04-13 11:16:32 JST
- Module/Scope: compactInVacuum (strict validate-only after square vessel + modular ICF114 refactor)
- Command(s): `./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
- Key Parameters/Overrides: default target updated to `vessel.cross_section=square`; front/rear end modules switched to explicit `ICF114` welded pipe-stub flange blocks; new strict checks include `vessel_cross_section_contract`, `end_module_standard`, `end_module_type_semantics`, `welded_pipe_stub_to_standard_flange`, and `vacuum_boundary_complete`.
- Validation Result: pass
- Artifacts/State: `state.json.run.status=pass`, `validation.status=pass`; refreshed report confirms `front=ICF114`, `rear=ICF114`, square `440 x 440 mm` inner section, and a single closed vacuum boundary solid.
- Next Action: run full rebuild to export FCStd/STEP from the new square-chamber geometry.

- Timestamp UTC: 2026-04-13T02:17:04Z
- Timestamp Local: 2026-04-13 11:17:04 JST
- Module/Scope: compactInVacuum (full rebuild/export after square vessel + modular ICF114 refactor)
- Command(s): `./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml --force-rebuild`
- Key Parameters/Overrides: same square-body + `ICF114/ICF114` contract as the preceding strict validate-only run; assembly now exports `VesselBody`, `FrontEndModule_ICF114`, and `RearEndModule_ICF114` as separate document features.
- Validation Result: pass
- Artifacts/State: `state.json.run.status=pass`, `validation.status=pass`, `compactInVacuum.FCStd`, `compactInVacuum.step`, and `compactInVacuum.validation_report.json` regenerated from the new geometry.
- Next Action: hand off the rebuilt square-chamber artifacts and keep the `example_jis_vf100.yaml` profile available for downstream flange swaps.

- Timestamp UTC: 2026-07-26T10:19:57Z
- Timestamp Local: 2026-07-26 19:19:57 JST
- Module/Scope: compactInVacuum (strict physics-contract validate-only)
- Command(s): `./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
- Key Parameters/Overrides: active-center radius semantics; 12 typed channels; 8 opposite-azimuth elastic D-P pairs; provisional 380 MeV deuteron plus CH2 inputs; active medium and photosensor remain undecided.
- Validation Result: pass.
- Artifacts/State: `state.json.run.status=pass`; validation report and `compactInVacuum.channel_manifest.json` generated; physics partitions confirm pzz `4+4` pairs and pyy `2+2` pairs.
- Next Action: force rebuild FCStd/STEP with the corrected active-center solid placement and validate actual axial extents.

- Timestamp UTC: 2026-07-26T10:21:14Z
- Timestamp Local: 2026-07-26 19:21:14 JST
- Module/Scope: compactInVacuum (full physics-contract rebuild/export)
- Command(s): `./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml --force-rebuild`
- Key Parameters/Overrides: same compact physics contract; detector solids centered at configured 140/190/205 mm radii; 25 x 50 mm cylindrical geometry remains a replaceable placeholder.
- Validation Result: pass.
- Artifacts/State: FCStd, STEP, validation report, state, and channel manifest regenerated; all 12 actual detector solids pass center-radius and 50 mm axial-length checks.
- Next Action: use the compact manifest and `code/config/compact_in_vacuum.ini` as the shared CAD/analysis interface; replace placeholder detector response after material and photosensor selection.

- Timestamp UTC: 2026-07-26T14:38:11Z
- Timestamp Local: 2026-07-26 23:38:11 JST
- Module/Scope: compactInVacuum (strict service-interface validate-only)
- Command(s): `./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`
- Key Parameters/Overrides: front/rear ICF114; top ICF70 rotary interface; four sector-grouped ICF70 4-channel signal/bias interfaces; one ICF70 32-pin housekeeping interface; 12 cable routes; 25 mm provisional cable bend radius; no overrides.
- Validation Result: pass.
- Artifacts/State: strict report passed with one closed vacuum-boundary solid, 12 used + 4 spare coax channels, 24 used + 8 spare housekeeping pins, zero support/service overlap with the provisional 20 mm beam stay-clear, and zero support/drive overlap with the elastic-particle LOS envelopes.
- Next Action: add resolved configuration and stable engineering metrics to the report, then force-refresh validation.

- Timestamp UTC: 2026-07-26T14:40:00Z
- Timestamp Local: 2026-07-26 23:40:00 JST
- Module/Scope: compactInVacuum (cached recheck followed by forced metric refresh)
- Command(s): `./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation`; `./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml --validate-only --strict-validation --force-rebuild`
- Key Parameters/Overrides: unchanged service configuration; the first command exercised the hash-skip path, and the second intentionally refreshed code-derived validation metrics.
- Validation Result: skipped with prior pass, then pass after forced refresh.
- Artifacts/State: validation JSON now embeds the full resolved configuration, FreeCAD/Python versions, vacuum-boundary volume/bounds, all detector centers/bounds, port coordinates, target work/park centers, and service capacities.
- Next Action: run a complete forced FCStd/STEP export.

- Timestamp UTC: 2026-07-26T14:40:51Z
- Timestamp Local: 2026-07-26 23:40:51 JST
- Module/Scope: compactInVacuum (full service-integrated CAD rebuild/export)
- Command(s): `./compactInVacuum/run_compactInVacuum.sh --pipeline-index codex_targets.yaml --force-rebuild`
- Key Parameters/Overrides: same strict service contract; central beam-axis spine removed and replaced by detector-back-face supports to the first service wall; supplier equipment remains explicitly tagged as interface envelopes.
- Validation Result: pass.
- Artifacts/State: FCStd, STEP, validation report, state, and schema-v2 channel/service manifest regenerated; FCStd contains 67 non-null objects (27 physical, 6 supplier-interface envelopes, 17 keep-outs, 17 interface envelopes); STEP contains 13,939 transfer entities.
- Next Action: close supplier RFQs for the rotary unit, four-channel coax assemblies, 32-pin housekeeping feedthrough, and vacuum cable; replace the 20 mm beam stay-clear and 25 mm cable bend-radius assumptions with signed interface data.

- Timestamp UTC: 2026-07-26T15:38:41Z
- Timestamp Local: 2026-07-27 00:38:41 JST
- Module/Scope: CompactOne Phase A architecture and requirement audit
- Command(s): repository/commit/worklog inspection; source/config/report audit; `git switch -c compact-one-architecture-v1`; `git diff --check`
- Key Parameters/Overrides: no CAD or configuration changes; external `afterSRC/` and `infrontofSamuraiMag/` routes classified as preserved parallel routes; current CompactInVacuum geometry audited at commit `679849a`.
- Validation Result: architecture audit complete; confirmed strict flag is currently ignored, 0.30 mm radial-wall beam stubs pass, detector active/housing geometry is conflated, square-only validator contradicts cylindrical builder, and target/LOS/service/thermal abstractions are incomplete.
- Artifacts/State: added CompactOne audit, CompactOne requirement baseline, module README, and corrected root project matrix; no runtime state or generated CAD changed.
- Next Action: implement common configuration domains and two deployment profiles before replacing preferred geometry.

- Timestamp UTC: 2026-07-26T15:52:58Z
- Timestamp Local: 2026-07-27 00:52:58 JST
- Module/Scope: CompactOne Phase B schema-v2 configuration and deployment separation
- Command(s): `micromamba run -n anaroot-env python -m pytest -q compactInVacuum/tests/test_platform_config.py compactInVacuum/tests/test_geometry.py`; Python compile checks
- Key Parameters/Overrides: common active plastic `20 x 5.5 mm` with 5/5.5/6 mm candidates; EQR15 recommended baseline; separate 32 x 32 x 44 mm cassette; four 3-channel cartridges; 12 x 50-ohm services; afterSRC cylindrical candidate selected; SAMURAI square candidate selected; both profiles retain square and cylindrical candidates.
- Validation Result: pass, 20 tests; both deployment profiles and the legacy scaffold load; inherited common YAML participates in the state hash.
- Artifacts/State: added schema-v2 parser, common detector config, two deployment configs/aliases, migration note, and purchased-interface/project-transition metadata.
- Next Action: implement and independently validate the detector cassette geometry.

- Timestamp UTC: 2026-07-26T15:59:35Z
- Timestamp Local: 2026-07-27 00:59:35 JST
- Module/Scope: CompactOne Phase C golden detector cassette
- Command(s): `./compactInVacuum/run_freecad_tests.sh`; `micromamba run -n anaroot-env python -m pytest -q compactInVacuum/tests/test_platform_config.py compactInVacuum/tests/test_geometry.py`
- Key Parameters/Overrides: 20 mm diameter x 5.5 mm active plastic; 32 x 32 x 44 mm cassette body; explicit coupling, reflector, EQR15 envelope, copper carrier/spreader/bridge, shell, stop, key, strain relief, connector keep-out, temperature sensor, and datums.
- Validation Result: pass; 12 valid physical shapes, active volume 1727.875959 mm3, zero shell overlap with active/entrance path, and zero-distance contacts through the declared thermal chain.
- Artifacts/State: independent cassette builder/document builder and FreeCAD runtime regression entry added; no deployment assembly switched yet.
- Next Action: place D/P-small/P-large cassettes on one removable golden sector and validate shared structure/services/thermal semantics.
