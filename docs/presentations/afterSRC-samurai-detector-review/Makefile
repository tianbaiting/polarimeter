.PHONY: all pdf clean

LATEXMK ?= latexmk
DOCUMENTS := afterSRC-samurai-detector-review

all: pdf

pdf: $(addsuffix .pdf,$(DOCUMENTS))

.PHONY: $(addsuffix .pdf,$(DOCUMENTS))
$(addsuffix .pdf,$(DOCUMENTS)): %.pdf: %.tex
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=build $<
	cp build/$@ $@

clean:
	$(LATEXMK) -c -outdir=build $(addsuffix .tex,$(DOCUMENTS))
