# RAPORT NOAPTE -- campania HIL C2

Generat NON-interactiv de `c2_analysis/make_raport_noapte.py` la 2026-08-04 00:27:13.
Raport MECANIC: ce s-a generat, din ce date, si ce anomalii verificabile exista.
**Nu contine interpretare stiintifica** -- aceea ramane a ta.

## SURSE (read-only, arhivele sunt sigilate a-w)

| rol | cale |
|---|---|
| HIL 4KB | `/home/ubuntu/DATE_CAMPANIE/C2_HIL_WIFI_20260801` |
| HIL 64KB | `/home/ubuntu/DATE_CAMPANIE/C2_HIL_WIFI64_20260803` |
| SIL 4KB | `/home/ubuntu/DATE_CAMPANIE/C2_SIL_20260718` |
| SIL 64KB | `/home/ubuntu/DATE_CAMPANIE/C2_SIL64_20260719` |
| iesiri | `/home/ubuntu/DATE_CAMPANIE/ANALIZA_C2` |

Directoare-proba excluse explicit din tabele: bern_5_MIX2_INVALID, bern_5_MIXT_INVALID, bern_5_V3_ECOUMORT.

## REZUMAT MECANIC

- celule (conditie x RMW): 22 la 4KB, 6 la 64KB
- repetitii citite: 220 la 4KB, 60 la 64KB
- celule fara niciun supravietuitor (n0 = N): 4 -- 4KB zenoh/bern_30, 4KB zenoh/ge_30_3, 4KB zenoh/ge_30_8, 64KB zenoh/ge_15_8
- anomalii mecanice: 0

Statisticile din tabele sunt CONDITIONATE pe rularile supravietuitoare (n>0);
fractia de esec e raportata separat ca n0=k/N. O celula cu n0=N nu are mediana --
apare ca `-` in tabele si hasurata in figuri.

## HIL Wi-Fi 4KB -- C2_HIL_WIFI_20260801

Campanie HIL Wi-Fi, sarcina utila 4096 B, N=10 repetitii/celula. Statistici CONDITIONATE pe rularile supravietuitoare (n>0); fractia de esec e raportata separat ca n0=k/N.

| conditie | RMW | N | n0 | supr. | livrare% med | min | max | first_seq med |
|---|---|---|---|---|---|---|---|---|
| ideal | cdds | 10 | 0/10 | 10 | 100.0 | 83.3 | 100.0 | 11 |
| bern_5 | cdds | 10 | 0/10 | 10 | 100.0 | 96.1 | 100.0 | 11 |
| ge_5_3 | cdds | 10 | 0/10 | 10 | 100.0 | 99.9 | 100.0 | 11 |
| ge_5_8 | cdds | 10 | 0/10 | 10 | 99.8 | 99.3 | 100.0 | 11 |
| bern_15 | cdds | 10 | 0/10 | 10 | 78.4 | 73.0 | 87.6 | 11 |
| ge_15_3 | cdds | 10 | 0/10 | 10 | 95.0 | 90.6 | 97.6 | 11 |
| ge_15_8 | cdds | 10 | 0/10 | 10 | 95.7 | 90.1 | 99.9 | 11 |
| bern_30 | cdds | 10 | 0/10 | 10 | 19.0 | 9.8 | 21.2 | 12 |
| ge_30_3 | cdds | 10 | 0/10 | 10 | 37.7 | 31.2 | 43.2 | 26 |
| ge_30_8 | cdds | 10 | 0/10 | 10 | 47.9 | 27.1 | 73.1 | 107 |
| lat200_jit50_ge_15_8 | cdds | 10 | 0/10 | 10 | 55.3 | 10.9 | 62.4 | 96 |
| ideal | zenoh | 10 | 0/10 | 10 | 100.0 | 85.7 | 100.0 | 11 |
| bern_5 | zenoh | 10 | 0/10 | 10 | 100.0 | 94.3 | 100.0 | 11 |
| ge_5_3 | zenoh | 10 | 0/10 | 10 | 81.2 | 32.2 | 91.7 | 11 |
| ge_5_8 | zenoh | 10 | 9/10 | 1 | 15.0 | 15.0 | 15.0 | 11 |
| bern_15 | zenoh | 10 | 0/10 | 10 | 48.7 | 27.7 | 61.0 | 11 |
| ge_15_3 | zenoh | 10 | 9/10 | 1 | 3.8 | 3.8 | 3.8 | 11 |
| ge_15_8 | zenoh | 10 | 3/10 | 7 | 8.7 | 1.5 | 12.4 | 651 |
| bern_30 | zenoh | 10 | 10/10 | 0 | - | - | - | - |
| ge_30_3 | zenoh | 10 | 10/10 | 0 | - | - | - | - |
| ge_30_8 | zenoh | 10 | 10/10 | 0 | - | - | - | - |
| lat200_jit50_ge_15_8 | zenoh | 10 | 8/10 | 2 | 1.7 | 1.3 | 2.0 | 112 |

n0=k/N: rulari cu ZERO esantioane livrate. Coloanele livrare si first_seq (mediana, min, max) sunt calculate DOAR pe cele 'supr.' rulari supravietuitoare (n>0).

EXCLUS (director-proba, cyclonedds): bern_5_MIX2_INVALID, bern_5_MIXT_INVALID, bern_5_V3_ECOUMORT

EXCLUS (director-proba, zenoh): bern_5_MIX2_INVALID, bern_5_MIXT_INVALID, bern_5_V3_ECOUMORT

## HIL Wi-Fi 64KB -- C2_HIL_WIFI64_20260803

Sonda HIL 64KB (65536 B), N=10 repetitii/celula. Aceleasi conventii ca la 4KB: mediane pe supravietuitori, esecul separat in n0.

| conditie | RMW | N | n0 | supr. | livrare% med | min | max | first_seq med |
|---|---|---|---|---|---|---|---|---|
| ideal | cdds | 10 | 0/10 | 10 | 100.0 | 41.9 | 100.0 | 11 |
| bern_15 | cdds | 10 | 0/10 | 10 | 0.5 | 0.1 | 1.3 | 365 |
| ge_15_8 | cdds | 10 | 0/10 | 10 | 6.2 | 1.6 | 14.3 | 57 |
| ideal | zenoh | 10 | 0/10 | 10 | 29.5 | 21.7 | 36.7 | 11 |
| bern_15 | zenoh | 10 | 0/10 | 10 | 2.2 | 1.4 | 3.3 | 51 |
| ge_15_8 | zenoh | 10 | 10/10 | 0 | - | - | - | - |

n0=k/N: rulari cu ZERO esantioane livrate. Coloanele livrare si first_seq (mediana, min, max) sunt calculate DOAR pe cele 'supr.' rulari supravietuitoare (n>0).

# SIL vs HIL -- conditii comune

SIL 4KB : /home/ubuntu/DATE_CAMPANIE/C2_SIL_20260718
SIL 64KB: /home/ubuntu/DATE_CAMPANIE/C2_SIL64_20260719
HIL 4KB : /home/ubuntu/DATE_CAMPANIE/C2_HIL_WIFI_20260801
HIL 64KB: /home/ubuntu/DATE_CAMPANIE/C2_HIL_WIFI64_20260803

## 4KB

| conditie | RMW | SIL n0 | SIL livr% med | HIL n0 | HIL livr% med | delta livr% (HIL-SIL) | delta first_seq |
|---|---|---|---|---|---|---|---|
| ideal | cdds | 0/10 | 100.0 | 0/10 | 100.0 | +0.0 | +0 |
| ideal | zenoh | 0/10 | 100.0 | 0/10 | 100.0 | +0.0 | +0 |
| bern_5 | cdds | 0/10 | 100.0 | 0/10 | 100.0 | +0.0 | +0 |
| bern_5 | zenoh | 0/10 | 100.0 | 0/10 | 100.0 | +0.0 | +0 |
| ge_5_3 | cdds | 0/10 | 100.0 | 0/10 | 100.0 | +0.0 | +0 |
| ge_5_3 | zenoh | 0/10 | 93.0 | 0/10 | 81.2 | -11.8 | +0 |
| ge_5_8 | cdds | 0/10 | 100.0 | 0/10 | 99.8 | -0.2 | +0 |
| ge_5_8 | zenoh | 0/10 | 82.1 | 9/10 | 15.0 | -67.1 | +0 |
| bern_15 | cdds | 0/10 | 98.3 | 0/10 | 78.4 | -19.9 | +0 |
| bern_15 | zenoh | 0/10 | 100.0 | 0/10 | 48.7 | -51.3 | +0 |
| ge_15_3 | cdds | 0/10 | 99.6 | 0/10 | 95.0 | -4.6 | +0 |
| ge_15_3 | zenoh | 0/10 | 65.9 | 9/10 | 3.8 | -62.1 | -14 |
| ge_15_8 | cdds | 0/10 | 97.0 | 0/10 | 95.7 | -1.3 | +0 |
| ge_15_8 | zenoh | 0/10 | 20.0 | 3/10 | 8.7 | -11.3 | +640 |
| bern_30 | cdds | 0/10 | 57.5 | 0/10 | 19.0 | -38.5 | -26 |
| bern_30 | zenoh | 0/10 | 46.5 | 10/10 | - | - | - |
| ge_30_3 | cdds | 0/10 | 59.0 | 0/10 | 37.7 | -21.4 | +14 |
| ge_30_3 | zenoh | 2/10 | 25.3 | 10/10 | - | - | - |
| ge_30_8 | cdds | 0/10 | 55.7 | 0/10 | 47.9 | -7.8 | +92 |
| ge_30_8 | zenoh | 5/10 | 8.5 | 10/10 | - | - | - |

Delta pozitiv = HIL livreaza MAI MULT decat SIL. Medianele sunt conditionate pe supravietuitori, deci se citesc IMPREUNA cu n0.

## 64KB

| conditie | RMW | SIL n0 | SIL livr% med | HIL n0 | HIL livr% med | delta livr% (HIL-SIL) | delta first_seq |
|---|---|---|---|---|---|---|---|
| bern_15 | cdds | 0/10 | 35.9 | 0/10 | 0.5 | -35.5 | +354 |
| bern_15 | zenoh | 0/10 | 90.0 | 0/10 | 2.2 | -87.8 | +40 |
| ge_15_8 | cdds | 0/10 | 98.2 | 0/10 | 6.2 | -92.0 | +46 |
| ge_15_8 | zenoh | 2/10 | 6.1 | 10/10 | - | - | - |

Delta pozitiv = HIL livreaza MAI MULT decat SIL. Medianele sunt conditionate pe supravietuitori, deci se citesc IMPREUNA cu n0.

## FIGURI GENERATE

| fisier | octeti |
|---|---|
| fig/fig_hil_heatmap_mirror.png | 199763 |
| fig/fig_hil_heatmap_mirror.pdf | 33414 |
| fig/fig_hil_delivery_vs_B.png | 170341 |
| fig/fig_hil_delivery_vs_B.pdf | 20569 |
| fig/fig_hil_discovery_prefix.png | 68469 |
| fig/fig_hil_discovery_prefix.pdf | 18965 |
| fig/fig_hil_sil_vs_hil_zenoh.png | 111667 |
| fig/fig_hil_sil_vs_hil_zenoh.pdf | 19579 |

## ANOMALII DETECTATE

### HIL 4KB (C2_HIL_WIFI_20260801)

Niciuna. Verificate: mismatch summary-vs-CSV, first_seq<11, n>sent, fisiere lipsa, JSON corupt -- pe fiecare repetitie din fiecare celula.

### HIL 64KB (C2_HIL_WIFI64_20260803)

Niciuna. Verificate: mismatch summary-vs-CSV, first_seq<11, n>sent, fisiere lipsa, JSON corupt -- pe fiecare repetitie din fiecare celula.

## FISIERE .TEX

`tabel_hil_4k.tex` si `tabel_hil_64k.tex` sunt documente complete (article, tabular simplu, fara booktabs) -- se compileaza direct cu pdflatex.
