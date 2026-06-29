# M19 -- Serii temporale

Anticiparea traiectoriei cu modele autoregresive: AR(p) ca regresie liniara pe
lag-uri, fereastra glisanta de feature-uri, potrivire prin cele mai mici patrate,
split TEMPORAL fara look-ahead, prognoza un-pas / multi-pas si comparatie onesta
cu persistenta (random walk). Nucleul implementeaza lag-urile, fit_ar, forecast_ar,
temporal_split si baza de persistenta.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`,
functia `make_latency_series`).

## Fisiere
- `teorie.md` -- predare completa (AR(p) + derivare lstsq + exemplu numeric phi de mana).
- `serii_temporale_core.py` -- nucleu pur numpy + `_selftest()` (forme lag, recuperare phi, split, AR vs persistenta).
- `serii_temporale_sklearn.py` -- validare incrucisata (fit_ar == LinearRegression pe lag-uri; TimeSeriesSplit fara look-ahead).
- `demo_sil.py` -- prognoza RTT pe seria de latenta (figura `fig_prognoza_rtt.png`).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m19_serii_temporale
$PY serii_temporale_core.py
$PY serii_temporale_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
