#!/usr/bin/env bash
# run_campaign_fair.sh -- campanie transport C1 ECHITABILA, REPRODUCTIBILA, N=10.
#
# Context: campania veche avea coloana Zenoh anormala (imun la pierdere) din
# stare reziduala de mediu, NU din transport. SHM e off implicit (linia 760);
# router-ul Zenoh crapa sub pierdere. Cu mediu CURAT + P2P, Zenoh e lovit
# consistent de netem. Comparatie cap-la-cap: ambele RMW peer-to-peer.
#
# FIX fata de versiunea anterioara: lasam run_campaign.py sa faca cele 10
# repetitii (--reps 10), care scrie rep1..rep10 distincte. (Bucla externa cu
# --reps 1 suprascria mereu rep1/ -> N=1. Gresit.)
#
# Curatenie O DATA inainte de fiecare (RMW x conditie); repetitiile aceleiasi
# conditii raman in acelasi mediu (corect statistic). PRE-FLIGHT inainte de ore.
#
# NOTA: scris fara a putea rula ROS local. Urmareste pre-flight-ul cu ochii.

set -o pipefail

C1_DIR="$HOME/ros2_ws/src/c1_benchmark"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$HOME/ros2_ws/new_data_sar/fair_${STAMP}"
mkdir -p "$OUT"
LOG="$OUT/run.log"
log(){ echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG"; }

purge(){
  pkill -f rmw_zenohd 2>/dev/null
  pkill -f 'gz sim' 2>/dev/null
  rm -f /dev/shm/*zenoh* /dev/shm/fastrtps_* 2>/dev/null
  sleep 1
}

source /opt/ros/jazzy/setup.bash 2>/dev/null
# Fara router (P2P, ca DDS). SHM off implicit pe Jazzy.

log "sudo pentru netem..."; sudo -v || { log "fara sudo"; exit 1; }
( while true; do sudo -n true; sleep 50; kill -0 $$ 2>/dev/null || exit; done ) & KA=$!
cleanup(){
  [ -n "${KA:-}" ] && kill "$KA" 2>/dev/null
  purge
  sudo tc qdisc del dev lo root 2>/dev/null
  log "curatenie finala facuta"
}
trap cleanup EXIT INT TERM

cd "$C1_DIR" || { log "FATAL: lipseste $C1_DIR"; exit 1; }

LAYERS=""
grep -q "layers" run_campaign.py 2>/dev/null && LAYERS="--layers transport"
log "layers: ${LAYERS:-(implicit; ruleaza si misiunea)}"

# ---------- PRE-FLIGHT ----------
log "== PRE-FLIGHT: Zenoh loss_30, P2P, mediu curat =="
purge
PRE="$OUT/preflight"
python3 run_campaign.py --iface lo --reps 1 --rmws zenoh \
    --conditions loss_30 --duration 20 --out "$PRE" $LAYERS \
    >"$OUT/preflight.log" 2>&1
PJ="$(find "$PRE" -name 'transport_p4096_summary.json' 2>/dev/null | head -1)"
[ -z "$PJ" ] && { log "FATAL: pre-flight fara rezultat (vezi preflight.log)"; exit 1; }
P95="$(python3 -c "import json;print(json.load(open('$PJ'))['p95_ms'])")"
LOSS="$(python3 -c "import json;print(json.load(open('$PJ'))['loss'])")"
log "PRE-FLIGHT Zenoh loss_30: p95=${P95}ms pierdere=${LOSS}"
VERDICT="$(python3 -c "print('IMMUNE' if (float('$P95')<50 and float('$LOSS')<0.02) else 'HIT')")"
if [ "$VERDICT" = "IMMUNE" ]; then
  log "!!! Zenoh IMUN chiar P2P + mediu curat. Nereproductibil. NU pornesc campania."
  echo; echo "STOP: vezi $LOG"; exit 2
fi
log "OK Zenoh lovit (p95 ${P95}ms) -> mediu valid. Continui."

# ---------- CAMPANIA: --reps 10 lasat in seama run_campaign (rep1..rep10) ----------
CONDS=(ideal loss_5 loss_15 loss_20 loss_25 loss_30 lat200_jit50 lat200_l15)
RMWS=(cyclonedds zenoh)
REPS=10
log "== Campanie: ${RMWS[*]} x ${#CONDS[@]} conditii x ${REPS} reps (run_campaign face repetitiile) =="
for rmw in "${RMWS[@]}"; do
  for cond in "${CONDS[@]}"; do
    purge   # mediu curat o data inainte de fiecare (RMW x conditie)
    if python3 run_campaign.py --iface lo --reps "$REPS" --rmws "$rmw" \
          --conditions "$cond" --out "$OUT/c1_transport" $LAYERS \
          >>"$OUT/campaign.log" 2>&1; then
      n=$(find "$OUT/c1_transport/$rmw/$cond" -name 'transport_p4096_summary.json' 2>/dev/null | wc -l)
      log "OK $rmw/$cond  (rep-uri salvate: $n)"
    else
      log "ESEC $rmw/$cond"
    fi
  done
done

log "== analiza =="
python3 analyze_campaign.py "$OUT/c1_transport" >>"$OUT/campaign.log" 2>&1
log "TERMINAT. Date in: $OUT/c1_transport"
echo; echo "GATA: $OUT"
echo "Verifica N: python3 ~/ros2_ws/src/c1_benchmark/spread_c1.py $OUT/c1_transport"
