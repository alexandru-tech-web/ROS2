#!/bin/bash
# g_timing.sh <rmw> <repetitii> -- timpul de la lansarea publicatorului pana la primul
# mesaj LIVRAT, cu abonatul deja pornit si asezat. Raporteaza fiecare repetitie si mediana.
set +u
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
RMW=$1; REP=${2:-5}
export ROS_DOMAIN_ID=77
source /opt/ros/jazzy/setup.bash

for i in $(seq 1 "$REP"); do
  rm -f "$S/sub.out" "$S/pub.out"
  RMW_IMPLEMENTATION=$RMW /usr/bin/python3 "$S/g_sub.py" 12 > "$S/sub.out" 2>/dev/null &
  SUBPID=$!
  for _ in $(seq 1 200); do grep -q READY "$S/sub.out" 2>/dev/null && break; sleep 0.05; done
  sleep 0.5
  T0=$(/usr/bin/python3 -c "import time; print('%.6f' % time.time())")
  RMW_IMPLEMENTATION=$RMW /usr/bin/python3 "$S/g_pub.py" 10 > "$S/pub.out" 2>/dev/null &
  PUBPID=$!
  wait $SUBPID 2>/dev/null
  kill $PUBPID 2>/dev/null; wait $PUBPID 2>/dev/null
  RECV=$(grep -m1 "^RECV" "$S/sub.out" | awk '{print $2}')
  MSG=$(grep -m1 "^RECV" "$S/sub.out" | awk '{print $4}')
  TINIT=$(grep -m1 "^T_INIT" "$S/pub.out" | awk '{print $2}')
  TEXEC=$(grep -m1 "^T_EXEC" "$S/pub.out" | awk '{print $2}')
  if [ -n "$RECV" ]; then
    echo "$T0 $RECV $TINIT $TEXEC msg$MSG"
  else
    echo "NIMIC"
  fi
done | tee "$S/timing_$RMW.txt" | /usr/bin/python3 "$S/g_stats.py" "$RMW"
