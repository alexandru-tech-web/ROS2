#!/bin/bash
# g_run.sh <rmw_sub> <rmw_pub> [eticheta]
# Porneste abonatul, asteapta READY, apoi porneste publicatorul si raporteaza daca
# mesajele au ajuns si dupa cat timp de la lansarea publicatorului.
set +u
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
RMW_SUB=$1; RMW_PUB=$2; ET=${3:-}
export ROS_DOMAIN_ID=77
source /opt/ros/jazzy/setup.bash

rm -f "$S/sub.out" "$S/pub.out"
RMW_IMPLEMENTATION=$RMW_SUB /usr/bin/python3 "$S/g_sub.py" 12 > "$S/sub.out" 2>"$S/sub.err" &
SUBPID=$!
for _ in $(seq 1 200); do grep -q READY "$S/sub.out" 2>/dev/null && break; sleep 0.05; done
sleep 0.5                                    # abonatul s-a asezat

T0=$(/usr/bin/python3 -c "import time; print('%.6f' % time.time())")
RMW_IMPLEMENTATION=$RMW_PUB /usr/bin/python3 "$S/g_pub.py" 10 > "$S/pub.out" 2>"$S/pub.err" &
PUBPID=$!
wait $SUBPID 2>/dev/null
kill $PUBPID 2>/dev/null; wait $PUBPID 2>/dev/null

RECV=$(grep -m1 "^RECV" "$S/sub.out" | awk '{print $2}')
TINIT=$(grep -m1 "^T_INIT" "$S/pub.out" | awk '{print $2}')
if [ -n "$RECV" ]; then
  /usr/bin/python3 - "$T0" "$RECV" "$TINIT" "$ET" <<'EOF'
import sys
t0, recv, tinit, et = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3] or 0), sys.argv[4]
print("REZULTAT %s LIVRAT total_de_la_spawn=%.3f s | init_rclpy=%.3f s | descoperire=%.3f s"
      % (et, recv - t0, (tinit - t0) if tinit else float('nan'),
         (recv - tinit) if tinit else float('nan')))
EOF
else
  echo "REZULTAT $ET NIMIC_LIVRAT (12 s)"
fi
