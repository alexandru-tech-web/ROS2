# M03 -- Cadrul invatarii supervizate

Harta mentala a tot ce urmeaza: ERM (minimizarea riscului empiric), risc empiric
vs real, functii de pierdere (patratica, 0-1, hinge, logistica) si descompunerea
bias-varianta derivata complet si verificata Monte Carlo. Nucleul implementeaza
pierderile + un model polinomial + descompunerea bias-varianta.

Procesul de demonstratie e SINTETIC (controlat, f(x)+zgomot), nu masuratori reale.

## Fisiere
- `teorie.md` -- predare completa (derivarea bias-varianta + exemplu numeric de pierderi).
- `invatare_supervizata_core.py` -- nucleu pur numpy + `_selftest()` (egalitatea bias-varianta).
- `invatare_supervizata_sklearn.py` -- validare incrucisata (loss-uri / curbe sklearn).
- `demo_sil.py` -- bias-varianta vs complexitate + surogate vs 0-1 (figuri).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m03_invatare_supervizata
$PY invatare_supervizata_core.py
$PY invatare_supervizata_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
