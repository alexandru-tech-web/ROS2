#!/usr/bin/env bash
# hil_preflight.sh -- verificari pre-zbor HIL (M1 PC <-> M2 RPi) INAINTE de orice masuratoare.
# REGULA DE AUR: nicio masuratoare pana cand toate verificarile nu sunt PASS (exit 0).
#
# Ruleaza pe FIECARE masina, cu IP-ul CELEILALTE:
#   M2 (RPi):  ./hil_preflight.sh <IP_M1> [iface] --talker   # publica un talker pt verificarea inversa
#   M1 (PC):   ./hil_preflight.sh <IP_M2> [iface]            # verifica /chatter de la M2
# Inverseaza rolurile (--talker pe cealalta) ca sa confirmi discovery in AMBELE sensuri.
#
# Cere INAINTE, in ACELASI terminal pe ambele masini:
#   export ROS_DOMAIN_ID=7
#   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp   # sau rmw_zenoh_cpp (P2P, FARA router)
#   source ~/ros2_ws/install/setup.bash
set -u

PEER=""; IFACE=""; TALKER=0
for arg in "$@"; do
  case "$arg" in
    --talker) TALKER=1 ;;
    *) if [ -z "$PEER" ]; then PEER="$arg"; elif [ -z "$IFACE" ]; then IFACE="$arg"; fi ;;
  esac
done

if [ -z "$PEER" ]; then
  echo "folosire: $0 <IP_celeilalte_masini> [iface] [--talker]"
  exit 2
fi

FAIL=0
pass(){ printf '  [PASS] %s\n' "$1"; }
warn(){ printf '  [WARN] %s\n' "$1"; }
fail(){ printf '  [FAIL] %s\n' "$1"; FAIL=$((FAIL + 1)); }

echo "== HIL preflight (peer=$PEER) =="

echo "-- mediu ROS --"
if command -v ros2 >/dev/null 2>&1; then pass "ros2 in PATH"; else fail "ros2 NU e in PATH (source ~/ros2_ws/install/setup.bash)"; fi
if [ -n "${ROS_DOMAIN_ID:-}" ]; then pass "ROS_DOMAIN_ID=$ROS_DOMAIN_ID (TREBUIE identic pe ambele masini)"; else fail "ROS_DOMAIN_ID nesetat (export ROS_DOMAIN_ID=7)"; fi
if [ -n "${RMW_IMPLEMENTATION:-}" ]; then pass "RMW_IMPLEMENTATION=$RMW_IMPLEMENTATION"; else warn "RMW_IMPLEMENTATION nesetat (export rmw_cyclonedds_cpp sau rmw_zenoh_cpp)"; fi
case "${RMW_IMPLEMENTATION:-}" in
  *zenoh*) warn "Zenoh: ruleaza P2P, FARA router (rmw_zenohd crapa sub pierdere -- NOTA_METODOLOGICA_C1.md). Daca scouting-ul multicast nu merge pe Wi-Fi, seteaza endpoint-uri connect explicite." ;;
esac

echo "-- curatare reziduala (mediu curat OBLIGATORIU) --"
if pkill -f rmw_zenohd 2>/dev/null; then warn "am oprit un rmw_zenohd ramas"; else pass "niciun rmw_zenohd rezidual"; fi
rm -f /dev/shm/*zenoh* /dev/shm/fastrtps_* 2>/dev/null || true
pass "curatat /dev/shm/*zenoh* + /dev/shm/fastrtps_*"

echo "-- firewall --"
if command -v ufw >/dev/null 2>&1; then
  if ufw status 2>/dev/null | grep -qi "Status: active"; then fail "ufw ACTIV -- opreste-l: sudo ufw disable (altfel blocheaza discovery DDS/Zenoh)"; else pass "ufw inactiv"; fi
else
  pass "ufw neinstalat (nimic de oprit)"
fi

echo "-- retea --"
if ping -c 2 -W 2 "$PEER" >/dev/null 2>&1; then pass "ping $PEER OK"; else fail "ping $PEER ESUAT (verifica IP, cablu/AP, rute)"; fi
if [ -n "$IFACE" ]; then
  if ip -br addr show "$IFACE" >/dev/null 2>&1; then
    pass "iface $IFACE: $(ip -br addr show "$IFACE" | awk '{print $3}')"
    if [ -d "/sys/class/net/$IFACE/wireless" ]; then
      warn "iface $IFACE e WIRELESS -> AP poate avea 'client isolation' (M1<->M2 blocat) si poate ARUNCA traficul multicast (discovery DDS pica). Prefera cablu / AP fara izolare; pt netem simetric aplica regula pe iface-ul real al FIECAREI masini."
    fi
  else
    warn "iface $IFACE nu exista local (verifica: ip -br addr)"
  fi
else
  warn "iface nespecificat -- afla cu 'ip -br addr' (o folosesti la run_campaign --iface si la hil_netem.py)"
fi

echo "-- discovery ROS (ambele sensuri) --"
if [ "$TALKER" = "1" ]; then
  if [ "$FAIL" -gt 0 ]; then
    echo "== $FAIL fail inainte de talker -- repara intai, nu porni talker pe setup stricat. =="
    exit 1
  fi
  echo "  pornesc talker (Ctrl+C dupa ce cealalta masina confirma /chatter):"
  exec ros2 run demo_nodes_cpp talker
fi

echo "  caut /chatter de la peer (porneste pe PEER: 'ros2 run demo_nodes_cpp talker' SAU ruleaza acolo scriptul cu --talker)"
if timeout 10 ros2 topic list 2>/dev/null | grep -qx "/chatter"; then
  pass "/chatter VIZIBIL de la peer (discovery peer->local OK)"
else
  fail "/chatter INVIZIBIL in 10s (ROS_DOMAIN_ID diferit? ufw? multicast aruncat pe Wi-Fi? talker pornit pe peer?)"
fi
echo "  INVERSEAZA apoi: --talker AICI + fara --talker pe peer, ca sa confirmi si sensul invers."

echo
if [ "$FAIL" -eq 0 ]; then
  echo "== PREFLIGHT OK (0 fail). Poti incepe masuratorile (vezi HIL_RUNBOOK.md sectiunea 5). =="
  exit 0
else
  echo "== PREFLIGHT PICAT ($FAIL fail). REGULA DE AUR: nicio masuratoare pana nu trec TOATE. =="
  exit 1
fi
