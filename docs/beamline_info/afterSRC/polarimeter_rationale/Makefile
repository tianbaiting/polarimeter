.PHONY: all pdf

LATEXMK ?= latexmk
PDF_DIR := ../../../../output/pdf

all: pdf

pdf: rationale_zh.tex
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=build rationale_zh.tex
	mkdir -p $(PDF_DIR)
	cp build/rationale_zh.pdf $(PDF_DIR)/afterSRC_polarimeter_rationale_zh.pdf
