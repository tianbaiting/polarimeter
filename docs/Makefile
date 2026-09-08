.PHONY: all reading guides verify clean

LATEXMK ?= latexmk

all:
	$(MAKE) reading
	$(MAKE) guides
	$(MAKE) verify

reading:
	python3 ../scripts/build_docs.py --build

guides:
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=index/build index_zh.tex
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=index/build index_en.tex
	cp index/build/index_zh.pdf index_zh.pdf
	cp index/build/index_en.pdf index_en.pdf

verify:
	python3 ../scripts/build_docs.py --check

clean:
	$(LATEXMK) -c -outdir=index/build index_zh.tex index_en.tex
