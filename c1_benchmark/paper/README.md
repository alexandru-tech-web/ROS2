# paper/ -- schelet articol A1 (C1: benchmark middleware ROS 2)

Schelet ONEST al articolului A1, pe rezultatele reale C1. Toate cifrele sunt PROVIZORII
(SIL / loopback, N=10) -- de inlocuit cu HIL inainte de orice submisie.

## Continut
- `main.tex`        -- scheletul (article local; comuta pe IEEEtran pe Overleaf)
- `references.bib`  -- SEED de bibliografie (TODO: referinte reale; CLAUDE.md: nu inventa citari)
- `figs/`           -- aici copiezi/generezi figurile (.pdf) inainte de compilare

## Build
LOCAL (IEEEtran lipseste, vezi CLAUDE.md sec 4):
```
cd c1_benchmark/paper
pdflatex main && bibtex main && pdflatex main && pdflatex main
```
Foloseste `\documentclass{article}` + `\bibliographystyle{plain}`.
OVERLEAF / TeX Live complet: comuta pe `\documentclass[conference]{IEEEtran}`.

## Figuri (de copiat in figs/ inainte de build)
- `fig_transport.pdf`    <- `analyze_campaign.py <results_c1/>`
- `selector_regret.pdf`  <- `reproduce_selector.py selector_dataset.csv`
- optional: `box/cdf/variability` (analysis/), PDIA `figA/B/C` (Analiza_ML_18.06.2026/)

## Status (DRAFT)
- Ipotezele H1-H4 sunt derivate ONEST din rezultatele SIL (vezi sectiunea Rezultate din main.tex):
  - H1: CycloneDDS = coada de latenta mai mica si mai predictibila (SIL).
  - H2 (negativ): selectorul de control NU bate always-CycloneDDS sub LOCO.
  - H3: sub obiectiv constient de pierdere, politica optima e DEPENDENTA DE DEADLINE.
  - H4 (de testat): la stratul de misiune, alegerea rmw afecteaza timpul de misiune (date in curs).
- TODO inainte de submisie: proza finala per sectiune; lucrari conexe + citari REALE;
  figurile in `figs/`; inlocuirea tuturor cifrelor SIL cu date HIL (N mai mare, doua masini).
