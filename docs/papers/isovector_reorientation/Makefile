.PHONY: all pdf clean

LATEXMK ?= latexmk
DOCUMENTS := TheDetailedPartOfPol polarization 测量量

all: pdf

pdf: $(addsuffix .pdf,$(DOCUMENTS))

.PHONY: $(addsuffix .pdf,$(DOCUMENTS))
$(addsuffix .pdf,$(DOCUMENTS)): %.pdf: %.tex
	$(LATEXMK) -pdflatex -interaction=nonstopmode -halt-on-error -outdir=build $<
	cp build/$@ $@

clean:
	$(LATEXMK) -c -outdir=build $(addsuffix .tex,$(DOCUMENTS))
