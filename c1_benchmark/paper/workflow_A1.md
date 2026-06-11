# SPRINT A1 → SSRR 2026 (Incheon, 2–4 nov)

**Termen articol complet (8 pagini): VINERI 19 IUNIE 2026 — peste 8 zile.**
Notificare: 31 aug. Varianta finală (camera-ready): 15 oct. Recenzie pe
articolul complet; SSRR cere motivare de teren (utilizatori finali expliciți
— la noi: echipele de intervenție SAR, formulat deja în Introducere).

## Decizia strategică (asumată în articol)
Submitem pe 18–19 iunie cu **campania pe o mașină (lo)** + secțiunea
*Threats to Validity* scrisă onest („single-host loopback; physical-link
two-machine validation planned for the final version"). Fereastra până la
**15 octombrie** permite întărirea camera-ready cu datele pe două mașini
(+ eventual FastDDS, al treilea RMW). Riscul e gestionat, nu ascuns.

## Calendarul zi-cu-zi
| Zi | Data | Livrabil |
|---|---|---|
| J1 | joi 11 | GO; `apt install` RMW-uri; `test_bench_core` + `--selftest` + `--dry` trec |
| J2 | vin 12 | **repetiția generală**: `run_campaign.py --iface lo --reps 2 --duration 10` → primele figuri REALE; sanity (ideal≈0 pierdere; loss_30→~51% pe ecou); trimite `campaign_summary.csv` |
| J3 | sâm 13 | **CAMPANIA**: `--iface lo --reps 5` (~3–4 h, mașina liberă); arhivează `results_c1/` |
| J4 | dum 14 | `analyze_campaign.py` → figurile finale în `paper/`; verdictele H1–H4 pe cifre |
| J5 | lun 15 | Secțiunile IV–V (Rezultate) scrise pe cifre; Setup completat (versiuni, mașină) |
| J6 | mar 16 | Discussion + abstract cu cifra de titlu; autorii arXiv completați în bib |
| J7 | mie 17 | Citire integrală; limita 8 pag; pdflatex curat; checklist double-blind/format IEEE de pe site |
| J8 | joi 18 | **SUBMISIE** (nu lăsa pe 19!) |

## Plan B (dacă 18–19 nu se prinde)
arXiv preprint imediat (prioritate de idee) → următoarele ținte: IEEE IRC /
ICARSC 2027 / revistă (Sensors, IEEE Access); SSRR 2027. Datele și
infrastructura rămân valabile integral.

## După submisie (iul–oct)
Montajul pe două mașini (protocol Faza 2) → date fizice pentru camera-ready;
opțional FastDDS; A2 (teleoperarea) intră la rând cu datele deja măsurate.
