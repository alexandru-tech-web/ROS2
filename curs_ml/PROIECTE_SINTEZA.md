# PROIECTE_SINTEZA.md -- proiecte integratoare pe datele tezei

Patru proiecte care leaga mai multe module pe datele mele (`date_sar`). Fiecare are
un livrabil (script rulabil + figura + interpretare scrisa). Implementate in
`curs_ml/proiecte/`; folosesc scikit-learn (modulele predau versiunile de la zero)
si, la capstone, nucleele reale M21/M22.

ONESTITATE: datele sunt SINTETICE, semanate din C1/M. Proiectele demonstreaza
metodologia; cifrele finale cer datele reale de campanie.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/proiecte
$PY p1_predictie_latenta.py
$PY p2_clasificator_link.py
$PY p3_deznodamant_misiune.py
$PY p4_capstone_politica.py
```

## P1 -- Pipeline de predictie a latentei  [GATA]
- Module: M04 + M05 + M06 + M07 + M18. Fisier: `proiecte/p1_predictie_latenta.py`.
- De la date brute la Ridge cu lambda ales prin CV; prezice log10(rtt_ms).
- Rezultat (SINTETIC): bate baza (media) cu ~30% RMSE; interval pe falduri raportat.

## P2 -- Clasificator de link 'usable' calibrat si explicat  [GATA]
- Module: M04 + M08 + M09 + M14. Fisier: `proiecte/p2_clasificator_link.py`.
- Clase dezechilibrate: prag pe recall-ul clasei rare, calibrare izotonica,
  importanta prin permutare. Livrabil: curba PR + clasament de feature-uri.

## P3 -- Predictia deznodamantului misiunii  [GATA]
- Module: M04 + M12 + M13 + M14. Fisier: `proiecte/p3_deznodamant_misiune.py`.
- Random Forest vs un singur arbore pentru mission_complete + importanta de feature.
- Rezultat (SINTETIC): `delivered_frac` e factorul dominant al succesului.

## P4 (capstone) -- Politica adaptiva vs statica  [GATA]
- Module: M17/M19 + M21 + M22. Fisier: `proiecte/p4_capstone_politica.py`.
- Foloseste nucleele REALE: predictorul de link M22 + Q-learning M21. Compara
  politica invatata cu cele statice (mereu DDS / mereu Zenoh) si cu optimul.
- Rezultat (SINTETIC): predictor ~0.99 acuratete; politica invatata atinge ~optimul
  si bate cea mai buna statica (~+30%). Inchide cursul in teza (C3). Figura pentru A2.
- De confirmat cu date HIL + o dinamica temporala reala (vezi nota M21).
