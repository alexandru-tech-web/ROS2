# M09 -- Metrici, dezechilibru si calibrare

Cum evaluezi corect un clasificator cu clase DEZECHILIBRATE (clasa 'usable' din
datele de link e minoritara ~30%): de ce acuratetea minte, precizie/recall/F1 pe
clasa rara, AUC-ROC (prin ranguri si trapez), curba precizie-recall si precizia
medie, alegerea pragului (max F1 sau recall-tinta) si calibrarea probabilitatilor
(curba de fiabilitate, ECE, scalare Platt). Nucleul implementeaza totul de la zero.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (derivare AUC = P(poz>neg), PR vs ROC, calibrare; exemple numerice).
- `metrici_calibrare_core.py` -- nucleu pur numpy + `_selftest()` (AUC perfect=1/aleator~0.5, prag pe recall, calibrare Platt).
- `metrici_calibrare_sklearn.py` -- validare incrucisata (roc_auc / AP / precizie-recall vs sklearn).
- `demo_sil.py` -- metrici la dezechilibru + curba PR si diagrama de calibrare pe link (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m09_metrici_dezechilibru
$PY metrici_calibrare_core.py
$PY metrici_calibrare_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
