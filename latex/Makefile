# Makefile for RTLDI ATLAS LaTeX refinement
# Run from the latex/ directory after `python -m src.generate_atlas_latex` (from project root)

LATEX = lualatex
# LATEX = pdflatex   # fallback; may need extra packages for full Unicode

all: main.pdf

main.pdf: main.tex
	$(LATEX) -interaction=nonstopmode main.tex
	$(LATEX) -interaction=nonstopmode main.tex   # for TOC, references, longtable pages

clean:
	rm -f *.aux *.log *.out *.toc *.lof *.lot

.PHONY: all clean
