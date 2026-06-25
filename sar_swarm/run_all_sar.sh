#!/usr/bin/env bash
# run_all_sar.sh -- re-ruleaza experimentele SAR + C1 pe date curate, automat.
# Iesire: ~/ros2_ws/new_data_sar/run_<timestamp>/{sil,c1_transport,logs,SUMMARY.txt}
#
# DOUA MODURI:
#   bash run_all_sar.sh --smoke   # test ~5 min: valideaza ca tot porneste
#   bash run_all_sar.sh           # campania completa (ore) -- lasi si revii
#
# Rezistent la erori: fiecare pas e logat separat; esecul unui pas NU opreste
# restul (SIL ruleaza primul, deci datele lui sunt in siguranta orice s-ar
# intampla la C1).
#
# IMPORTANT: scris fara a putea rula ROS/Gazebo local -> RULEAZA INTAI --smoke.
# Acopera: simularea SAR (sar_swarm, toate scenariile) + benchmark-ul C1
# transport (netem real). NU include mesh/rehab (pachete separate, neverificate).
# NU include calea Gazebo (timp-real / GUI -> validare manuala separata; SIL
# foloseste acelasi nucleu verificat azi).

set -o pipefail        # NU set -u: ar rupe `source` la setup.bash ROS2 (lectie veche)

SMOKE=0
[ "${1:-}" = "--smoke" ] && SMOKE=1

SAR_DIR="$HOME/ros2_ws/src/sar_swarm"
C1_DIR="$HOME/ros2_ws/src/c1_benchmark"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$HOME/ros2_ws/new_data_sar/run_${STAMP}"
LOGS="$OUT/logs"
SUMMARY="$OUT/SUMMARY.txt"
mkdir -p "$OUT/sil" "$OUT/c1_transport" "$LOGS"

# --- parametri per mod ---
if [ "$SMOKE" = "1" ]; then
  SIL_SCENARIOS=(baseline.yaml)
  C1_REPS=1
  C1_EXTRA=(--conditions ideal,loss_30 --duration 5)
else
  SIL_SCENARIOS=(baseline.yaml drone_isolation.yaml gcs_delay_spike.yaml \
                 loss_30.yaml loss_70.yaml mesh_relay.yaml partition_2v2.yaml)
  C1_REPS=10
  C1_EXTRA=()        # toate conditiile, durata implicita
fi

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$SUMMARY"; }
hr()  { echo "----------------------------------------" | tee -a "$SUMMARY"; }

# ruleaza un pas, captureaza stdout+stderr intr-un log, noteaza rezultatul
step() {
  local name="$1"; shift
  log "START  $name"
  if "$@" >"$LOGS/${name}.log" 2>&1; then
    log "OK     $name"
  else
    log "ESEC   $name (exit $?) -- vezi logs/${name}.log"
  fi
}

# --- mediu ROS2 ---
if [ -f /opt/ros/jazzy/setup.bash ]; then
  source /opt/ros/jazzy/setup.bash
else
  log "ATENTIE: /opt/ros/jazzy/setup.bash lipseste -- nodurile ROS pot esua"
fi

# --- sudo keepalive (netem la C1 are nevoie de root) ---
log "Cer sudo o data (pentru tc netem la C1)..."
if sudo -v; then
  ( while true; do sudo -n true; sleep 50; kill -0 "$$" 2>/dev/null || exit; done ) &
  SUDO_KEEPALIVE=$!
else
  log "ATENTIE: fara sudo -- partea C1 (netem) va esua; SIL ruleaza oricum."
  SUDO_KEEPALIVE=""
fi

# curatenie la iesire, orice s-ar intampla
cleanup() {
  [ -n "${SUDO_KEEPALIVE:-}" ] && kill "$SUDO_KEEPALIVE" 2>/dev/null
  sudo tc qdisc del dev lo root 2>/dev/null
  rm -f /dev/shm/fastrtps_* 2>/dev/null
}
trap cleanup EXIT INT TERM

hr; log "RUN $STAMP  (smoke=$SMOKE)"; log "Iesire: $OUT"; hr

# ===================== 1. CAMPANIA SIL (sar_swarm) =====================
# sil_run.py pare determinist (seed fix) -> o rulare per scenariu.
log "== SIL: ${#SIL_SCENARIOS[@]} scenarii =="
if cd "$SAR_DIR"; then
  for sc in "${SIL_SCENARIOS[@]}"; do
    step "sil_${sc%.yaml}" python3 sil_run.py "scenarios/$sc" --out "$OUT/sil"
  done
else
  log "FATAL: lipseste $SAR_DIR -- sar SIL sarit"
fi

# ===================== 2. CAMPANIA C1 TRANSPORT (netem real) ===========
# run_campaign.py are deja orchestrarea interna (watchdog router Zenoh, harvest).
log "== C1 transport: reps=$C1_REPS =="
if cd "$C1_DIR"; then
  C1_ARGS=(--iface lo --reps "$C1_REPS" --out "$OUT/c1_transport" "${C1_EXTRA[@]}")
  step "c1_plan_dry" python3 run_campaign.py "${C1_ARGS[@]}" --dry   # planul, in log
  step "c1_transport" python3 run_campaign.py "${C1_ARGS[@]}"        # rularea reala
  step "c1_analyze"   python3 analyze_campaign.py "$OUT/c1_transport"
else
  log "FATAL: lipseste $C1_DIR -- C1 sarit"
fi

# ===================== MANIFEST + SUMAR FINAL =====================
hr; log "TERMINAT $STAMP"
{
  echo "=== MANIFEST $STAMP ==="
  echo "mod: $([ "$SMOKE" = 1 ] && echo SMOKE || echo COMPLET)"
  echo "SIL scenarii: ${SIL_SCENARIOS[*]}"
  echo "C1 reps: $C1_REPS  extra: ${C1_EXTRA[*]:-(toate, durata implicita)}"
  echo
  echo "=== Fisiere produse (csv/json/png) ==="
  find "$OUT" -type f \( -name '*.csv' -o -name '*.json' -o -name '*.png' \) | sort
} >> "$SUMMARY"
hr
echo
echo "GATA. Rezultate in: $OUT"
echo "Ce a mers / ce a esuat: $SUMMARY"
