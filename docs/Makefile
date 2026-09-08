.PHONY: all reading guides verify

LATEXMK ?= latexmk

all:
	$(MAKE) reading
	$(MAKE) guides
	$(MAKE) verify

reading:
	python3 ../scripts/build_docs.py --build

guides:
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=build/navigation index_zh.tex
	$(LATEXMK) -xelatex -interaction=nonstopmode -halt-on-error -outdir=build/navigation index_en.tex
	cp build/navigation/index_zh.pdf index_zh.pdf
	cp build/navigation/index_en.pdf index_en.pdf

verify:
	python3 ../scripts/build_docs.py --check
