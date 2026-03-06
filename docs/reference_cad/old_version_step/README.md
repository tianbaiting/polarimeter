# old-version SolidWorks -> STEP Reference Pack

This directory stores neutral CAD exports (`.step`) converted from `old-version/*.SLDPRT` and `old-version/*.SLDASM`.

## 1) Export rule (outside this repo)

Use a SolidWorks-capable machine and export each source file as:

- Format: `STEP AP242`
- Units: `mm`
- Scale: `1.0` (no scaling)
- Naming: keep original base name and relative structure

Examples:

- `old-version/chamber_base.SLDPRT` -> `docs/reference_cad/old_version_step/chamber_base.step`
- `old-version/scintilator/base_pmt.SLDPRT` -> `docs/reference_cad/old_version_step/scintilator/base_pmt.step`

## 2) Build/refresh manifest

From repo root:

```bash
python3 scripts/cad_reference/build_old_version_step_manifest.py
```

Output:

- `docs/reference_cad/old_version_step_manifest.json`

## 3) Validate STEP import in FreeCAD runtime

From repo root:

```bash
./scripts/cad_reference/run_old_version_step_import_check.sh \
  --manifest docs/reference_cad/old_version_step_manifest.json \
  --output docs/reference_cad/old_version_step_import_report.json \
  --strict
```

Output:

- `docs/reference_cad/old_version_step_import_report.json`

## 4) Status files

- Human-updated source: `old-version/*.SLDPRT`, `old-version/*.SLDASM`
- Machine-generated status:
  - `docs/reference_cad/old_version_step_manifest.json`
  - `docs/reference_cad/old_version_step_import_report.json`
