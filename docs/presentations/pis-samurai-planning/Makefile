.PHONY: all pdf clean

LATEXMK ?= latexmk
DOCUMENTS := pis-samurai-planning pis-samurai-notes-zh
OUTPUT_DIR := ../../../output/pdf
FIGURES := ../../physics/polarization_production_transport/figures

all: pdf

pdf: $(addprefix $(OUTPUT_DIR)/,$(addsuffix .pdf,$(DOCUMENTS)))

$(OUTPUT_DIR)/%.pdf: %.tex pis-samurai-planning.tex speaker-notes.tex $(FIGURES)/sakamoto2016_p1_fig1.png $(FIGURES)/sakamoto2016_p1_fig2.png
	mkdir -p $(OUTPUT_DIR)
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=build $<
	cp build/$*.pdf $@

clean:
	$(LATEXMK) -c -outdir=build $(addsuffix .tex,$(DOCUMENTS))
