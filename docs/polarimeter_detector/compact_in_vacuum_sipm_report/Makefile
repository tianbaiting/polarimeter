PYTHON := micromamba run -n anaroot-env python
LATEXMK := latexmk
REPORT_EN := compact_in_vacuum_sipm_report
REPORT_ZH := compact_in_vacuum_sipm_report_zh

.PHONY: all data check-data test report report-en report-zh verify-pdf verify-pdf-en verify-pdf-zh verify help

all: verify

data:
	$(PYTHON) scripts/generate_report_data.py

check-data:
	$(PYTHON) scripts/generate_report_data.py --check

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

report: report-en report-zh

report-en: data
	mkdir -p build
	$(LATEXMK) -lualatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build $(REPORT_EN).tex

report-zh: data
	mkdir -p build
	$(LATEXMK) -lualatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build $(REPORT_ZH).tex

verify-pdf-en: report-en
	pdfinfo build/$(REPORT_EN).pdf | rg '^(Pages|Page size|File size)'
	pdftotext -layout build/$(REPORT_EN).pdf - | rg -q 'EQR15'
	pdftotext -layout build/$(REPORT_EN).pdf - | rg -q 'afterSRC'
	pdftotext -layout build/$(REPORT_EN).pdf - | rg -q 'CompactInVacuum-afterSRC'
	pdftotext -layout build/$(REPORT_EN).pdf - | rg -q 'CompactInVacuum-preSAMURAI'
	pdftotext -layout build/$(REPORT_EN).pdf - | rg -q 'legacy/fallback'
	pdftotext -layout build/$(REPORT_EN).pdf - | rg -q 'LISE.. thickness scan'
	pdftotext -layout build/$(REPORT_EN).pdf - | rg -q 'RFQ checklist for Shanghai PrMat'
	pdftotext -layout build/$(REPORT_EN).pdf - | rg -q 'Data and calculation verification'
	if pdftotext -layout build/$(REPORT_EN).pdf - | rg -q 'ICF152'; then exit 1; fi
	if pdftotext -layout build/$(REPORT_EN).pdf - | rg -q 'The project contains two distinct polarimeters'; then exit 1; fi

verify-pdf-zh: report-zh
	pdfinfo build/$(REPORT_ZH).pdf | rg '^(Pages|Page size|File size)'
	pdftotext -layout build/$(REPORT_ZH).pdf - | rg -q 'EQR15'
	pdftotext -layout build/$(REPORT_ZH).pdf - | rg -q 'afterSRC'
	pdftotext -layout build/$(REPORT_ZH).pdf - | rg -q 'CompactInVacuum-afterSRC'
	pdftotext -layout build/$(REPORT_ZH).pdf - | rg -q 'CompactInVacuum-preSAMURAI'
	pdftotext -layout build/$(REPORT_ZH).pdf - | rg -q 'legacy/fallback'
	pdftotext -layout build/$(REPORT_ZH).pdf - | rg -q 'LISE.. 厚度扫描'
	pdftotext -layout build/$(REPORT_ZH).pdf - | rg -q '上海谱幂'
	pdftotext -layout build/$(REPORT_ZH).pdf - | rg -q '数据与计算验证'
	if pdftotext -layout build/$(REPORT_ZH).pdf - | rg -q 'ICF152'; then exit 1; fi
	if pdftotext -layout build/$(REPORT_ZH).pdf - | rg -q '本项目包含两台不同用途的极化仪'; then exit 1; fi

verify-pdf: verify-pdf-en verify-pdf-zh

verify: check-data test verify-pdf

help:
	@echo "make data       Regenerate CSV, JSON, and LaTeX numerical fragments"
	@echo "make check-data Verify that generated files match current source inputs"
	@echo "make test       Run numerical unit tests"
	@echo "make report     Compile both English and Chinese reports with LuaLaTeX"
	@echo "make report-en  Compile the English report"
	@echo "make report-zh  Compile the Chinese report"
	@echo "make verify     Run the complete data, test, and bilingual PDF checks"
