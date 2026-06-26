# HIL transport -- cheatsheet de rulare (M1 PC + M2 RPi)

Comenzile exacte pentru comparatia AUTORITARA CycloneDDS vs Zenoh pe doua masini fizice, strat
transport. Detalii: HIL_RUNBOOK.md. Nota de validitate: NOTA_METODOLOGICA_C1.md. Pana cand rulezi
asta, toate cifrele din repo sunt SIL (loopback).

Decizii fixate:
- netem SIMETRIC (aceeasi regula pe egress pe AMBELE masini) -> round-trip ~ 1-(1-p)^2, RTT ~ 2x
  one-way, coerent cu SIL. M1: run_campaign aplica pe M1; M2: hil_netem.py aplica aceeasi regula.
- Zenoh: P2P, FARA router (rmw_zenohd crapa sub pierdere).
- Conditii HIL = 8 (memoryless + latenta): ideal, loss_5, loss_15, loss_20, loss_25, loss_30,
  lat200_jit50, lat200_l15. *_burst / gilbert_* sunt EXCLUSE automat pe --mode hil (interferenta,
  inghetata, in afara drumului critic A1). Conditia-cheie: lat200_l15.
- N >= 5 (--reps 5). Zenoh e imprevizibil -> raporteaza interval/CV, nu media punctuala.

## 0. Pe AMBELE masini, in fiecare terminal
```bash
export ROS_DOMAIN_ID=7
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp        # acelasi peste tot (faza 1)
source ~/ros2_ws/install/setup.bash
ip -br addr                                         # afla iface real (ex. eth0)
```

## 1. Preflight (gate -- nicio masuratoare pana nu-i PASS in ambele sensuri)
```bash
# M2:  cd ~/ros2_ws/src/c1_benchmark && ./hil_preflight.sh <IP_M1> <iface> --talker
# M1:  cd ~/ros2_ws/src/c1_benchmark && ./hil_preflight.sh <IP_M2> <iface>
# apoi inverseaza --talker pe M1, ca sa confirmi si sensul invers
```

## 2. Ecou pe M2 (terminal persistent)
```bash
python3 ~/ros2_ws/src/c1_benchmark/bench_echo_server.py
```

## 3. Faza 1 -- CycloneDDS (driver M1 + sync M2)
Pe M1, driver-ul bucleaza cele 8 conditii si se opreste la fiecare ca sa aplici netem pe M2:
```bash
cd ~/ros2_ws/src/c1_benchmark
DRY=1 ./hil_run_transport.sh <iface> cyclonedds     # previzualizare (optional)
./hil_run_transport.sh <iface> cyclonedds           # rularea reala (N=5)
```
La fiecare conditie C, driver-ul iti spune comanda de pe M2; ruleaz-o in terminalul M2:
```bash
sudo python3 ~/ros2_ws/src/c1_benchmark/hil_netem.py <iface> <C>   # aplica C simetric pe M2
```
La final, curata M2: `sudo python3 ~/ros2_ws/src/c1_benchmark/hil_netem.py <iface> --clear`

(Echivalent manual, fara driver, pentru o conditie C:
```bash
# M2: sudo python3 hil_netem.py <iface> C
# M1: sudo -v && python3 run_campaign.py --mode hil --iface <iface> --layers transport \
#         --reps 5 --rmws cyclonedds --conditions C
```)

## 4. Faza 2 -- Zenoh (P2P, FARA router)
```bash
# pe AMBELE: schimba RMW + mediu curat + re-preflight
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
pkill -f rmw_zenohd; rm -f /dev/shm/*zenoh* /dev/shm/fastrtps_*
source ~/ros2_ws/install/setup.bash
# NU porni rmw_zenohd. Repeta pasul 1 (preflight), apoi:
cd ~/ros2_ws/src/c1_benchmark && ./hil_run_transport.sh <iface> zenoh
```

## 5. Arhivare (NU in git)
```bash
mkdir -p ~/c1_archive
mv ~/ros2_ws/src/c1_benchmark/results_c1 ~/c1_archive/hil_$(date +%Y%m%d)/
# results_c1/ e gitignorat; in repo intra DOAR campaign_summary.csv + figuri, DUPA analiza
```

## 6. Analiza (identica SIL/HIL; vezi HIL_RUNBOOK.md sectiunea 8)
```bash
python3 analyze_campaign.py ~/c1_archive/hil_<data>/
python3 build_selector_dataset.py ~/c1_archive/hil_<data>/ -o selector_dataset.csv
python3 reproduce_selector.py selector_dataset.csv
```
Checklist final (HIL_RUNBOOK.md sectiunea 9): aceleasi conditii ca SIL, N declarat, directie netem
documentata (SIMETRICA), tc curatat, comparatie SIL vs HIL etichetata clar, nimic etichetat HIL
daca e SIL.
