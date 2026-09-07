.PHONY: all screenshots verify

all:
	latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build polarization_production_transport_zh.tex
	cp build/polarization_production_transport_zh.pdf polarization_production_transport_zh.pdf

screenshots:
	python3 capture_sources.py

verify:
	python3 capture_sources.py --verify-only
