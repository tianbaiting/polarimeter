.PHONY: all pdf clean

LATEXMK ?= latexmk
DOCUMENTS := Concise_Full_Density_Matrix_Identifiability Concise_Tensor_Only_Polarimetry Identifiability_of_Deuteron_Tensor_Polarization

all: pdf

pdf: $(addsuffix .pdf,$(DOCUMENTS))

.PHONY: $(addsuffix .pdf,$(DOCUMENTS))
$(addsuffix .pdf,$(DOCUMENTS)): %.pdf: %.tex
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=build $<
	cp build/$@ $@

clean:
	$(LATEXMK) -c -outdir=build $(addsuffix .tex,$(DOCUMENTS))
