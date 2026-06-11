# c1_benchmark — Articolul A1 (SSRR 2026)

**Întrebarea de cercetare:** rmw_zenoh vs CycloneDDS sub degradare de rețea SAR-realistă (tc netem) — lacuna atacată: benchmarkurile existente (Liang et al. 2023) măsoară **doar în condiții ideale**.

## Structura pachetului

```
c1_benchmark/
├── bench_core.py          # nucleul PUR: condiții, statistici RTT, planul (11 teste)
├── bench_client.py        # clientul de transport (RTT pe ecou)
├── bench_echo_server.py   # serverul de ecou
├── netem.py               # aplică/curăță/arată condiția tc netem
├── run_campaign.py        # orchestratorul: RMW × condiție × repetiții
├── analyze_campaign.py    # agregare → campaign_summary.csv + figuri
├── test_bench_core.py     # 11/11 verificări
├── paper/
│   ├── main.tex           # scheletul IEEE cu ipoteze H1–H4
│   ├── references.bib
│   ├── figs/              # figurile generate (fig_transport/mission/cdf.png)
│   └── experimental_protocol.md
└── results_c1/            # NU în git — merg în ~/c1_archive/
```

## Fluxul complet

```bash
# 1. verificări
python3 test_bench_core.py                       # 11/11

# 2. repetiția generală (~40 min)
cd ~/ros2_ws/src/c1_benchmark
./preflight.sh                                   # VERDICT: GO obligatoriu
python3 run_campaign.py --iface lo --reps 2 --out ~/c1_results

# 3. campania completă (~3–4 h, peste noapte)
python3 run_campaign.py --iface lo --reps 5 --out ~/c1_results_full

# 4. analiza
python3 analyze_campaign.py ~/c1_results_full
# → ~/c1_results_full/analysis/campaign_summary.csv
# → ~/c1_results_full/analysis/fig_transport.png
# → ~/c1_results_full/analysis/fig_mission.png
# → ~/c1_results_full/analysis/fig_cdf.png

# 5. articolul
cp ~/c1_results_full/analysis/*.png paper/figs/
cd paper && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

## Cele 6 condiții de rețea

| Condiție | Descriere | tc netem |
|---|---|---|
| `ideal` | fără degradare | — |
| `loss_5` | 5% pierdere pachete | `loss 5%` |
| `loss_15` | 15% pierdere pachete | `loss 15%` |
| `loss_30` | 30% pierdere pachete | `loss 30%` |
| `lat200_jit50` | 200 ms ± 50 ms jitter | `delay 200ms 50ms` |
| `lat200_l15` | 200 ms + 15% pierdere | `delay 200ms loss 15%` |

## Rezultatele campaniei (sumar)

| Condiție | p95 DDS [ms] | p95 Zenoh [ms] | loss DDS | loss Zenoh |
|---|---|---|---|---|
| ideal | 1.5 | 1.7 | 0% | 0% |
| loss_5 | 146 | 25 | 0% | 1% |
| loss_15 | 1060 | 758 | 1.1% | 25.3% |
| loss_30 | 2590 | 3748 | 42% | 37% |
| lat200_jit50 | 913 | 481 | 4.2% | 2.7% |
| **lat200_l15** | **2540** | **2463** | **45.6%** | **14.9%** |

**Fraza de titlu:** La coadă egală (~2.5 s), DDS pierde 45.6% vs Zenoh 14.9% — de 3× mai fiabil în condiția SAR-realistă (latență + pierdere simultane).

## Calendar submisie

| Zi | Sarcina |
|---|---|
| J 12.06 | Secțiunile Results + Discussion (din `c1_results_section.tex`) în `main.tex` |
| V 13.06 | Introduction + Related Work + Method |
| D 14.06 | Limitations + Conclusion + abstract; prima compilare |
| L 15.06 | Tăiere la 8 pagini IEEE |
| M 16.06 | Citire integrală + verificarea fiecărei cifre |
| Mi 17.06 | Buffer coautori/conducător |
| **J 18.06** | **SUBMISIE SSRR 2026** |

## Notă metodologică
Misiunea rulează cu `scenario:=none.yaml` — singura degradare e cea fizică (tc). Motorul de misiune și logica de autonomie absorb o parte din zgomot, de aceea **ambele straturi** (transport + misiune) sunt necesare — raportând doar microbenchmarkul supraevaluezi diferența practică.
