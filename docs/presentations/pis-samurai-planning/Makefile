.PHONY: all pdf plots clean

LATEXMK ?= latexmk
DOCUMENTS := pis-samurai-planning pis-samurai-notes-zh
FIGURES := ../../physics/polarization_production_transport/figures
PRECISION_OUTPUTS := pyy_confidence_10s.pdf pyy_confidence_60s.pdf pyy_confidence_x10_10s.pdf pyy_confidence_x10_60s.pdf pyy_confidence_x100_10s.pdf pyy_confidence_x100_60s.pdf build/pyy-confidence/precision-values.tex
PRECISION_INPUTS := ../../../code/config/current_tensor.ini ../../../code/build/dpol_tool ../../../code/data/observables/DSigamaOverDOmega.txt ../../../code/data/observables/CompletSetOFT/T.txt

all: pdf

pdf: $(addsuffix .pdf,$(DOCUMENTS))

plots: $(PRECISION_OUTPUTS)

$(PRECISION_OUTPUTS) &: plot_pyy_confidence.py $(PRECISION_INPUTS)
	micromamba run -n anaroot-env python plot_pyy_confidence.py

$(addsuffix .pdf,$(DOCUMENTS)): %.pdf: %.tex pis-samurai-planning.tex speaker-notes.tex Makefile $(FIGURES)/sakamoto2016_p1_fig1.png figures/deuterium-hyperfine-states.png $(PRECISION_OUTPUTS)
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=build $<
	cp build/$@ $@

clean:
	$(LATEXMK) -c -outdir=build $(addsuffix .tex,$(DOCUMENTS))
