# Registrul CENTRAL al ipotezelor -- rehab_exo_description

Fiecare cifra din pachet apartine exact uneia dintre clasele de mai jos. Fisierele
tematice (`urdf/IPOTEZE_LIMITE.md`, `urdf/MASE_NEVERIFICATE.md`,
`urdf/SPEC_DERIVATE.md`) raman sursa detaliata; aici e indexul, ca sa se poata
raspunde dintr-o privire la intrebarea "de unde vine cifra asta".

| clasa | ce inseamna | are voie in concluzii? |
|---|---|---|
| **DOCUMENTAT** | e in PDF, cu pagina | da |
| **DERIVAT** | calculat din documentat, cu formula scrisa | da, cu formula alaturi |
| **IPOTEZA** | alegere motivata, nu in document | doar declarat ca atare |
| **NEVERIFICAT** | placeholder, necesar simularii | NU |
| **ALES PRIN MASURARE** | fixat dupa un experiment in simulare | doar despre SIMULARE, nu despre dispozitiv |

## Registrul

| # | cifra | valoare | clasa | unde | de cand |
|---|---|---|---|---|---|
| 1 | cursele articulare TOTALE | sold 90, genunchi 140, glezna 70 grade | DOCUMENTAT | [PDF Tabel 3.1, p.10-11] | 19 aug |
| 2 | impartirea min/max a curselor | 0..90, 0..140, -35..+35 | IPOTEZA | `urdf/IPOTEZE_LIMITE.md` | 19 aug |
| 3 | minimul soldului in SEZUT | 25 grade | IPOTEZA | inelul de oprire, reper 208 [PDF p.7]; cifra din literatura LLR-Ro | 19 aug |
| 4 | efort si viteza nominale | sold 176.7 Nm / 1.5786 rad/s etc. | DERIVAT | `scripts/spec_derivate.py` din motor+reductor+raport | 20 aug |
| 5 | turatia de bobinaj TBM | A 2900 / B 2450 rpm | DOCUMENTAT | [PDF anexa, TBM(S) 60 Performance Data, pp. ~37-38] | 20 aug |
| 6 | mase si inertii | toate | **NEVERIFICAT** | `urdf/MASE_NEVERIFICATE.md`; GAP 1 | 19 aug |
| 7 | amortizare si frecare articulara | 2.0 / 1.0 (revolute) | **NEVERIFICAT** | argumente xacro `amort_*`, `frec_*`; acelasi GAP 1 | 22 aug |
| 8 | POSTURA_INITIALA, sold | 35.22 grade | DERIVAT | fractia 0.3913 din cursa veche, re-derivata; vezi README | 19 aug |
| 9 | toti senzorii | cuplu, forta 6D, unghi, rigla | **NEVERIFICAT** (sintetic) | `scripts/senzori_core.py`, model declarat | 20 aug |
| 10 | offset de montaj al senzorului de glezna | +-0.012 rad | IPOTEZA | `senzori_core.OFFSET_MONTAJ_GLEZNA`; deliberat, ca senzorul sa nu fie o copie a lui `/joint_states` | 21 aug |
| 11 | `position_proportional_gain` | 1.0 | **ALES PRIN MASURARE** | `config/controllers.yaml`; 15.0 producea oscilatie, 1.0 nu | 22 aug |
| 12 | inaltimea de aparitie | 1.2 m | **ALES PRIN MASURARE** | la 0, talpile intra in podea si contactul falsifica urmarirea | 21 aug |
| 13 | marja pragului ELECTRIC | 5 grade sub opritor | IPOTEZA | `supervizor_core.MARJA_IMPLICITA_RAD`; proximitatile reale nemasurate | 22 aug |
| 14 | banda de armare (histerezis) | 2 grade | IPOTEZA | `supervizor_core.BANDA_ARMARE_RAD` | 22 aug |
| 15 | praguri terapeutice de cuplu/viteza | vezi fisier | IPOTEZA | `config/safety_limits.yaml`; de stabilit cu personal clinic | anterior |
| 16 | praguri de raportare in monitor | urmarire 0.10 rad, saturatie 0.98 din limita, plafon de viteza 0.5 rad/s | **ALES PRIN MASURARE** | `scripts/monitor_core.py`; praguri de DEMONSTRATIE, nu cerinte clinice | 21-22 aug |

## Ce ar transforma ipotezele in masuratori

O singura vizita fizica inchide majoritatea: **6** si **7** cer cantarirea si
identificarea segmentelor; **13** cere vazut unde sunt montate proximitatile;
**2**, **3** cer masurat opritoarele si inelul de oprire (reper 208); **9** cere
fisele senzorilor montati. Pana atunci, niciun rezultat DINAMIC din acest pachet nu
are valoare in afara simularii.

Clasa **ALES PRIN MASURARE** merita citita cu grija: cifrele sunt reale si
reproductibile, dar spun ceva despre *aceasta simulare*, nu despre dispozitiv.
Castigul de 1.0 (**11**), de exemplu, e corect fiindca `gz_ros2_control` comanda
articulatiile CINEMATIC; pe hardware real, cu comanda in efort, nu inseamna nimic.
