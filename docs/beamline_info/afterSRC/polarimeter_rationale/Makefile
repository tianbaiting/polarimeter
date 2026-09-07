.PHONY: all pdf zh en

LATEXMK ?= latexmk
PDF_DIR := ../../../../output/pdf

all: pdf

pdf: zh en

zh: rationale_zh.tex
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=build rationale_zh.tex
	mkdir -p $(PDF_DIR)
	cp build/rationale_zh.pdf $(PDF_DIR)/afterSRC_polarimeter_rationale_zh.pdf

en: rationale_en.tex
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=build rationale_en.tex
	mkdir -p $(PDF_DIR)
	cp build/rationale_en.pdf $(PDF_DIR)/afterSRC_polarimeter_rationale_en.pdf
