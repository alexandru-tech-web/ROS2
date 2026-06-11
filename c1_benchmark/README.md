# C1 Benchmark — pachetul de cercetare al articolului A1

**Benchmarking `rmw_zenoh` vs CycloneDDS sub degradare de rețea SAR-realistă (tc netem), pe două straturi: transport (RTT/pierdere pe ecou, sarcini utile 64 B / 4 KiB / 64 KiB) și misiune SAR completă (timp de finalizare, acoperire, comanda omului). Lacuna atacată: studiile existente (incl. Liang et al. 2023) măsoară doar în condiții ideale.**

![Teste](https://img.shields.io/badge/verific%C4%83ri-11%20+%20autotest%20figuri-green)

| Fișier | Rol |
|---|---|
| `bench_core.py` | nucleul PUR: condițiile, statisticile RTT, comenzile tc, planul, extractorul de misiune (11 teste) |
| `bench_echo_server.py` / `bench_client.py` | microbenchmarkul de transport (RTT pe ecou = corect între ceasuri nesincronizate) |
| `netem.py` | aplică/curăță/arată condiția REALĂ pe interfață (`--dry` pentru plan) |
| `run_campaign.py` | orchestratorul: RMW × condiție × repetiții × straturi; routerul Zenoh gestionat; tc curățat la final |
| `analyze_campaign.py` | agregare → `campaign_summary.csv` + **figurile articolului** (transport / misiune / CDF); `--selftest` validează tot fluxul pe date sintetice, fără ROS |
| `paper/main.tex` + `references.bib` | scheletul IEEE pre-completat (ipoteze H1–H4, tabelul condițiilor, figurile legate) |
| `paper/experimental_protocol.md` | protocolul de laborator pas-cu-pas, cu bife |

## Fluxul cercetării

```bash
python3 test_bench_core.py                      # 1. verificările
python3 analyze_campaign.py --selftest          # 2. analiza validată end-to-end
python3 run_campaign.py --dry                   # 3. planul (120 rulări la reps=5)
python3 run_campaign.py --iface lo --reps 2     # 4. repetiția generală (o mașină)
python3 run_campaign.py --iface <eth> --reps 5  # 5. CAMPANIA (două mașini)
python3 analyze_campaign.py results_c1/         # 6. tabel + figurile articolului
```

## Notele metodologice (intră în articol)
- **Misiunea rulează cu `scenario:=none.yaml`** — injectorul simulat publică stare curată, iar singura degradare e cea FIZICĂ (tc). Diferențele măsurate aparțin exclusiv middleware-ului.
- **Ecoul compune pierderea pe ambele sensuri**: la p=30% configurat, pierderea de transport măsurată ≈ 1−(1−p)² = 51% — raportată ca atare.
- Fără sincronizare de ceas între mașini: RTT, nu one-way.

## Onestitate
Nucleul (11 teste), planul `--dry` și întreg lanțul de analiză (autotest cu figuri) au **rulat aici**. Nodurile ROS și campania reală cer mașina ta (RMW-urile instalate, sudo pentru tc) — protocolul acoperă fiecare pas, inclusiv punctele de verificat la montajul pe două mașini.
