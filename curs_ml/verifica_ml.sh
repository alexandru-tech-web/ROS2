#!/usr/bin/env bash
# verifica_ml.sh -- check verde/rosu pentru curs_ml: ASCII, selfteste, numar fisiere.
# Foloseste venv-ul dedicat ~/ros2_ws/.venv_ml daca exista (numpy/sklearn/...).
# Iesire 0 = totul verde; non-0 = ceva a picat.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PKG="$HERE/curs_ml"
VENV="$HOME/ros2_ws/.venv_ml/bin/python"
PY="python3"; [ -x "$VENV" ] && PY="$VENV"
fail=0
echo "== curs_ml: verificare ($PY) =="

# 1. ASCII: nimic non-ASCII in cod/md/sh
echo "-- ASCII --"
if grep -rnP '[^\x00-\x7F]' "$HERE" --include='*.py' --include='*.md' --include='*.sh' \
        --include='*.txt' --include='*.xml' --include='*.cfg' 2>/dev/null; then
  echo "  [ROSU] caractere non-ASCII gasite (vezi mai sus)"; fail=1
else
  echo "  [verde] tot ASCII"
fi

# 2. Selfteste: utils, date_sar, apoi fiecare *_core.py de modul
echo "-- selfteste --"
run_one() {
  local f="$1"
  if "$PY" "$f" >/dev/null 2>&1; then
    echo "  [verde] $(basename "$(dirname "$f")")/$(basename "$f")"
  else
    echo "  [ROSU]  $(basename "$(dirname "$f")")/$(basename "$f") -- selftest PICAT"; fail=1
  fi
}
run_one "$PKG/utils.py"
run_one "$PKG/date_sar.py"
for core in $(find "$PKG" -name '*_core.py' | sort); do run_one "$core"; done

# 3. Numar fisiere per modul (asteptat 7-9 la modulele complete)
echo "-- numar fisiere per modul --"
for d in $(find "$PKG" -maxdepth 1 -type d -name 'm[0-9]*' | sort); do
  n=$(find "$d" -type f | wc -l)
  printf "  %-34s %s fisiere\n" "$(basename "$d")" "$n"
done
echo "-- total fisiere curs_ml --"; find "$HERE" -type f | wc -l

if [ "$fail" -eq 0 ]; then echo "== TOTUL VERDE =="; else echo "== AU PICAT VERIFICARI =="; fi
exit "$fail"
