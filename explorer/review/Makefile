# Scoring review for the Data Center Explorer. Reads the precomputed results in ../data, so
# rerun after `glen-charts precompute results` and scripts/build-national.py.

report.pdf: build/report.md build/correlations.png
	pandoc build/report.md --resource-path=.:build --pdf-engine=xelatex -o $@

build/report.md: report.md build/values.json render.py
	python3 render.py

build/values.json build/correlations.png: analysis.py ../config/app.json $(wildcard ../data/results/*/*/facility-*.json)
	python3 analysis.py

clean:
	rm -rf build report.pdf

.PHONY: clean
