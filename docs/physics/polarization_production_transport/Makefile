.PHONY: all zh en screenshots verify

all: zh en

zh:
	latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build polarization_production_transport_zh.tex
	cp build/polarization_production_transport_zh.pdf polarization_production_transport_zh.pdf

en:
	latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build polarization_production_transport_en.tex
	cp build/polarization_production_transport_en.pdf polarization_production_transport_en.pdf

screenshots:
	python3 capture_sources.py

verify:
	python3 capture_sources.py --verify-only

.PHONY: pdf timeline-en clean
all: timeline-en
pdf: all

timeline-en:
	latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build riken_pis_status_timeline_en.tex
	cp build/riken_pis_status_timeline_en.pdf riken_pis_status_timeline_en.pdf

clean:
	latexmk -c -outdir=build *.tex
