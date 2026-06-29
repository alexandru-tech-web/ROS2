# M06 -- Regularizare

Indispensabil la N mic: Ridge (penalizare L2, forma inchisa) micsoreaza neted
coeficientii, iar Lasso (penalizare L1, coordinate descent) ii aduce la EXACT zero
si face selectie de feature. Nucleul implementeaza ambele de la zero.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (derivare Ridge + soft-threshold + exemplu numeric).
- `regularizare_core.py` -- nucleu pur numpy + `_selftest()` (Ridge vs OLS, sparsitate Lasso).
- `regularizare_sklearn.py` -- validare incrucisata (Ridge exact; Lasso pe suport).
- `demo_sil.py` -- trasee de coeficienti vs lambda pe latenta (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m06_regularizare
$PY regularizare_core.py
$PY regularizare_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
