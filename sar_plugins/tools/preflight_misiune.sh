#!/usr/bin/env bash
# preflight_misiune.sh — garda de mediu INAINTEA campaniei de misiune.
# Nu modifica nimic (in afara de a crea ~/mission_results daca lipseste).
# Verdict GO / NO-GO, in oglinda cu c1_benchmark/preflight.sh.
set -u
OK=1
nota() { printf "  %-52s %s\n" "$1" "$2"; }
esueaza() { nota "$1" "[NU]"; OK=0; }
trece()   { nota "$1" "[ok]"; }

echo "== preflight campania de misiune =="

# 1) procese care NU au voie sa fie vii
if pgrep -af "run_campaign|bench_client|bench_echo|mission_experiment" >/dev/null; then
  esueaza "nicio campanie in mers (C1/misiune)"
else
  trece "nicio campanie in mers (C1/misiune)"
fi
if pgrep -af "rmw_zenohd" >/dev/null; then
  esueaza "niciun router Zenoh rezidual (kill inainte)"
else
  trece "niciun router Zenoh rezidual"
fi
if pgrep -af "gz sim|ros2 launch" >/dev/null; then
  esueaza "niciun Gazebo / launch pornit"
else
  trece "niciun Gazebo / launch pornit"
fi

# 2) qdisc rezidual pe interfetele uzuale
for IF in lo $(ip -o link show 2>/dev/null | awk -F': ' '{print $2}' | grep -v lo | head -3); do
  if tc qdisc show dev "$IF" 2>/dev/null | grep -q netem; then
    esueaza "fara netem rezidual pe $IF (tc qdisc del dev $IF root)"
  else
    trece "fara netem rezidual pe $IF"
  fi
done

# 3) RMW-urile instalate
for P in rmw_cyclonedds_cpp rmw_zenoh_cpp; do
  if ros2 pkg prefix "$P" >/dev/null 2>&1; then
    trece "pachetul $P prezent"
  else
    esueaza "pachetul $P prezent (source /opt/ros/jazzy/setup.bash?)"
  fi
done

# 4) logica pura a plugin-urilor (55 verificari, ~secunde)
HERE="$(cd "$(dirname "$0")/.." && pwd)"
if (cd "$HERE" && python3 test_plugins.py) >/tmp/preflight_misiune_tests.log 2>&1; then
  trece "test_plugins.py (55) trece"
else
  esueaza "test_plugins.py trece (vezi /tmp/preflight_misiune_tests.log)"
fi

# 5) spatiu pe disc (>= 2 GB liberi in HOME)
FREE_GB=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc '0-9')
if [ "${FREE_GB:-0}" -ge 2 ]; then
  trece "spatiu pe disc: ${FREE_GB} GB liberi"
else
  esueaza "spatiu pe disc >= 2 GB (ai ${FREE_GB:-?} GB)"
fi

# 6) destinatia rezultatelor
OUT="${OUT:-$HOME/mission_results}"
if [ -d "$OUT" ] && [ -n "$(ls -A "$OUT" 2>/dev/null)" ]; then
  nota "ATENTIE: $OUT exista si NU e gol" "[!]"
  echo "         muta-l intai: mv $OUT ~/c1_archive/\$(date +%F)_misiune_vechi"
  OK=0
else
  mkdir -p "$OUT" && trece "destinatia $OUT pregatita"
fi

echo
if [ "$OK" = 1 ]; then
  echo "VERDICT: GO — poti porni: tools/mission_experiment.sh"
else
  echo "VERDICT: NO-GO — rezolva liniile [NU]/[!] de mai sus, apoi reia."
  exit 1
fi
