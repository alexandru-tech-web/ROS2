#!/bin/bash
# preflight.sh — verificarea de IGIENA dinaintea oricarei masuratori C1.
# Codifica lectiile din 11 iunie: niciun proces ROS paralel, lo curat,
# o singura campanie odata. Iesire: GO / NU PLECA.
ok=1
echo "== Preflight C1 =="

stray=$(pgrep -af "rmw_zenohd|sar_swarm|bench_|sil_run|teleop" 2>/dev/null | grep -v preflight)
if [ -n "$stray" ]; then
  echo "[X] Procese ROS/benchmark inca vii (opreste-le: pkill -f <nume>):"
  echo "$stray" | sed 's/^/      /'
  ok=0
else
  echo "[ok] niciun proces ROS/benchmark paralel"
fi

if command -v tc >/dev/null 2>&1; then
  if tc qdisc show dev lo 2>/dev/null | grep -q netem; then
    echo "[X] netem inca activ pe lo — curata: sudo python3 netem.py clear --iface lo"
    ok=0
  else
    echo "[ok] lo curat (fara netem rezidual)"
  fi
else
  echo "[!] tc indisponibil aici (ok doar in container, NU pe statia de masura)"
fi

if command -v ros2 >/dev/null 2>&1; then
  for p in rmw_cyclonedds_cpp rmw_zenoh_cpp; do
    if ros2 pkg prefix "$p" >/dev/null 2>&1; then
      echo "[ok] $p instalat"
    else
      echo "[X] $p LIPSESTE: sudo apt install ros-jazzy-${p//_/-}"
      ok=0
    fi
  done
else
  echo "[!] ros2 indisponibil in acest mediu (pe statie trebuie sa fie sourced)"
fi

free_gb=$(df -BG --output=avail "$HOME" 2>/dev/null | tail -1 | tr -dc '0-9')
[ "${free_gb:-0}" -ge 2 ] && echo "[ok] spatiu liber: ${free_gb} GB" \
                          || { echo "[X] sub 2 GB liberi in HOME"; ok=0; }

python3 test_bench_core.py >/dev/null 2>&1 \
  && echo "[ok] nucleul C1: 12 verificari trec" \
  || { echo "[X] test_bench_core.py ESUEAZA"; ok=0; }

echo "=================="
if [ "$ok" = 1 ]; then echo "VERDICT: GO — poti porni campania."; exit 0
else echo "VERDICT: NU PLECA — rezolva [X]-urile de mai sus."; exit 1; fi
