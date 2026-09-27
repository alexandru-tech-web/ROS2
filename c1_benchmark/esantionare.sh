#!/usr/bin/env bash
# esantionare.sh -- esantionare PASIVA pentru DIAG-Z (27.09.2026), pe M1 si pe M2 (acelasi fisier, paritate sha256).
# NU porneste, NU opreste si NU modifica nimic in afara fisierului de iesire. Un bloc per tact:
#   "T <epoch cu nanosecunde>" urmat de iesirea neatinsa a comenzii.
#
#   esantionare.sh ss <interval_s> <out> [port]    ss -tinH pe port (implicit 7447): stare, rtt, cwnd, bytes, retrans
#   esantionare.sh iw <interval_s> <out> <iface>   iw dev <iface> station dump: semnal, tx retries, tx failed
#
# Scrie PID-ul in <out>.pid; se opreste cu: kill $(cat <out>.pid). Plasa de siguranta: iese singur dupa
# ESANT_MAX_S secunde (implicit 900), ca un esantionator uitat sa nu ruleze la nesfarsit pe Pi.
set -u
mod=${1:?mod: ss sau iw}
dt=${2:?interval in secunde}
out=${3:?fisier de iesire}
arg=${4:-}
max=${ESANT_MAX_S:-900}
case "$mod" in
  ss) arg=${arg:-7447} ;;
  iw) [ -n "$arg" ] || { echo "iw cere interfata" >&2; exit 2; } ;;
  *) echo "mod necunoscut: $mod" >&2; exit 2 ;;
esac
echo $$ > "$out.pid"
t_end=$(( $(date +%s) + max ))
while [ "$(date +%s)" -lt "$t_end" ]; do
  echo "T $(date +%s.%N)"
  if [ "$mod" = ss ]; then
    ss -tinH "( sport = :$arg or dport = :$arg )" 2>&1
  else
    iw dev "$arg" station dump 2>&1
  fi
  sleep "$dt"
done >> "$out"
