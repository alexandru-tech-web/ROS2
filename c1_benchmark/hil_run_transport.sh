#!/usr/bin/env bash
# hil_run_transport.sh -- driver M1 (PC) pentru campania HIL transport, CONDITIE CU CONDITIE,
# cu sincronizare manuala a netem-ului SIMETRIC pe M2 (RPi). Reduce truda celor 16 rulari
# (8 conditii x 2 RMW) si erorile de tastare. Ruleaza pe M1; M2 are ecoul pornit (bench_echo_server.py).
#
# Folosire:
#   ./hil_run_transport.sh <iface> <rmw>          # rmw = cyclonedds | zenoh
#   REPS=5 ./hil_run_transport.sh eth0 cyclonedds
#   DRY=1  ./hil_run_transport.sh eth0 cyclonedds # previzualizare: nu cere Enter, run_campaign --dry
#
# Pentru fiecare conditie: iti arata comanda EXACTA de aplicat pe M2 (netem simetric), asteapta
# Enter, apoi ruleaza run_campaign.py --mode hil pe acea conditie. La final aminteste sa cureti M2.
# Conditiile vin din bench_core (EXCLUS interferenta: *_burst / gilbert_*) -- sursa unica.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
IFACE="${1:-}"; RMW="${2:-}"; REPS="${REPS:-5}"; DRY="${DRY:-0}"

if [ -z "$IFACE" ] || [ -z "$RMW" ]; then
  echo "folosire: $0 <iface> <rmw=cyclonedds|zenoh>   (REPS=5 implicit; DRY=1 pt previzualizare)"
  exit 2
fi
case "$RMW" in cyclonedds|zenoh) ;; *) echo "rmw necunoscut: $RMW (cyclonedds|zenoh)"; exit 2 ;; esac

CONDS="$(python3 -c "import sys; sys.path.insert(0,'$HERE'); from bench_core import CONDITIONS; print(' '.join(c['name'] for c in CONDITIONS if c.get('type')!='gilbert' and 'corr' not in c))")"
if [ -z "$CONDS" ]; then echo "nu am putut citi conditiile din bench_core"; exit 1; fi

echo "== HIL transport: RMW=$RMW iface=$IFACE reps=$REPS dry=$DRY =="
echo "Conditii ($(echo "$CONDS" | wc -w)): $CONDS"
echo "ASIGURA-TE ca: ecoul ruleaza pe M2, preflight-ul a trecut (./hil_preflight.sh), RMW e setat pe ambele."
echo

for C in $CONDS; do
  echo "------------------------------------------------------------"
  echo ">> Conditia: $C"
  echo "   Pe M2 ruleaza ACUM:  sudo python3 $HERE/hil_netem.py $IFACE $C"
  if [ "$DRY" = "1" ]; then
    echo "   [DRY] sar peste Enter; rulez run_campaign --dry"
    python3 "$HERE/run_campaign.py" --mode hil --iface "$IFACE" --layers transport \
        --reps "$REPS" --rmws "$RMW" --conditions "$C" --dry
  else
    printf "   Apasa Enter dupa ce ai aplicat netem pe M2 (Ctrl+C ca sa opresti)... "
    read -r _
    sudo -v
    python3 "$HERE/run_campaign.py" --mode hil --iface "$IFACE" --layers transport \
        --reps "$REPS" --rmws "$RMW" --conditions "$C"
  fi
  echo "   [done $C]"
done

echo "============================================================"
echo "TOATE cele $(echo "$CONDS" | wc -w) conditii rulate pentru $RMW."
echo "CURATA netem pe M2:  sudo python3 $HERE/hil_netem.py $IFACE --clear"
echo "Rezultate in $HERE/results_c1/$RMW/ -- arhiveaza in ~/c1_archive (NU in git)."
