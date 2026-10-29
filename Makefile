LATEX ?= xelatex

.PHONY: article clean

article:
	mkdir -p build
	$(LATEX) -interaction=nonstopmode -halt-on-error -output-directory=build article.tex
	$(LATEX) -interaction=nonstopmode -halt-on-error -output-directory=build article.tex

clean:
	rm -rf build
