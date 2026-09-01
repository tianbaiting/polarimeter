REPORT := compact_coordinate_sheet_zh

.PHONY: all report clean help

all: report

report:
	mkdir -p build
	latexmk -lualatex -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build $(REPORT).tex

clean:
	test ! -d build || trash-put -- build

help:
	@echo "make          Build PDF"
	@echo "make clean    Move build artifacts to the desktop trash"
