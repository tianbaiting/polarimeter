.PHONY: all pdf clean

LATEXMK ?= latexmk
DOCUMENTS := pis-samurai-planning pis-samurai-notes-zh
FIGURES := ../../physics/polarization_production_transport/figures

all: pdf

pdf: $(addsuffix .pdf,$(DOCUMENTS))

$(addsuffix .pdf,$(DOCUMENTS)): %.pdf: %.tex pis-samurai-planning.tex speaker-notes.tex Makefile $(FIGURES)/sakamoto2016_p1_fig1.png figures/deuterium-hyperfine-states.png
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=build $<
	cp build/$@ $@

clean:
	$(LATEXMK) -c -outdir=build $(addsuffix .tex,$(DOCUMENTS))
