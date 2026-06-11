# Protocolul experimental A1 (de urmat pas cu pas, cu bife)

> **TERMEN SSRR 2026: articol complet 19 IUNIE 2026** (notificare 31 aug; final 15 oct) — vezi `workflow_A1.md` pentru sprintul zi-cu-zi.

## Faza 0 — pregătire (o dată)
- [ ] `sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-rmw-zenoh-cpp`
- [ ] `python3 test_bench_core.py` → 11 verificări trec
- [ ] `python3 analyze_campaign.py --selftest` → figurile sintetice apar în `selftest_out/`
- [ ] `python3 run_campaign.py --dry --reps 1` → planul afișat, fără erori
- [ ] `sudo -v` funcționează (tc cere root); notează versiunile: `ros2 doctor --report | head`, `uname -a`

## Faza 1 — repetiția generală (o mașină, prin `lo`, ~40 min)
```bash
python3 run_campaign.py --iface lo --reps 2 --duration 10
python3 analyze_campaign.py results_c1/
```
- [ ] `campaign_summary.csv` are rânduri pentru ambele RMW × toate condițiile
- [ ] sanity: la `ideal`, pierderea ≈ 0 și RTT mic; la `loss_30`, pierderea de transport ≈ **51%** (ecoul compune ambele sensuri: 1−(1−p)²) — e corect, nu un defect
- [ ] notă metodologică: netem pe `lo` afectează TOT traficul local, inclusiv descoperirea RMW și routerul Zenoh — exact middleware-ul sub stres; cifrele de titlu vin însă din Faza 2

## Faza 2 — montajul pe două mașini (cifrele articolului)
- [ ] mașina A (operator/GCS) ↔ mașina B (drone/ecou), aceeași rețea; `ROS_DOMAIN_ID` identic; `ping` între ele OK
- [ ] netem se aplică pe interfața REALĂ a mașinii A: `--iface <eno1/wlp...>` (degradează egress-ul A→B; pentru ambele sensuri, aplică și pe B)
- [ ] Zenoh: routerul pe A; pe B configurează rmw_zenoh să se conecteze la `tcp/IP_A:7447` (vezi README-ul rmw_zenoh — env de conectare) **[de verificat la montaj]**
- [ ] CycloneDDS între subrețele poate cere `CYCLONEDDS_URI` cu peers expliciți **[de verificat: pe aceeași subrețea, multicast-ul implicit ajunge]**
- [ ] stratul transport: `bench_echo_server.py` pe B, clientul pe A; stratul misiune: dronele pe B, GCS+sonda pe A (aceleași launch-uri, noduri pornite separat)

## Faza 3 — campania completă (~3–4 h, lăsată să ruleze)
```bash
python3 run_campaign.py --iface <iface> --reps 5
```
- [ ] nu folosi mașinile în timpul rulării (zgomot de planificare)
- [ ] la final tc e curățat automat (`finally`); verifică: `python3 netem.py show --iface <iface>`

## Faza 4 — analiza și articolul
```bash
python3 analyze_campaign.py results_c1/
cp results_c1/analysis/fig_*.png paper/
cd paper && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```
- [ ] completează [TODO]-urile: setup (Faza 2), cifrele de titlu, verdictul H1–H4
- [ ] arhivează `results_c1/` (zip) — datele brute = anexa reproductibilității

## Integritatea datelor
- [ ] 5 repetiții/condiție; nicio repetiție ștearsă fără motiv notat
- [ ] orice anomalie (router căzut, mașină ocupată) → repetiția se reia și se notează
