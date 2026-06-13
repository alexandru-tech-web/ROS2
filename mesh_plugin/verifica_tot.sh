#!/usr/bin/env bash
# =====================================================================
# verifica_tot.sh - verificare automata end-to-end pentru mesh_plugin
#
# Ruleaza, in ordine:
#   1. verificare structura pachetului
#   2. verificare OFFLINE (Python pur: mesh_core selftest + SIL-uri)
#   3. colcon build
#   4. verificare instalare (ros2 pkg executables)
# Fiecare pas: VERDE [OK] sau ROSU [ESEC], cu rezumat la final.
#
# Utilizare:
#   ./verifica_tot.sh                 # ruleaza tot (din ~/ros2_ws sau oriunde)
#   ./verifica_tot.sh --offline       # doar pasii 1-2 (fara ROS/colcon)
#   ./verifica_tot.sh --clean         # build curat (sterge build/install pachet)
#   WS=~/alt_ws ./verifica_tot.sh     # alt workspace decat ~/ros2_ws
# =====================================================================
set -u

# ---- configurare ----
WS="${WS:-$HOME/ros2_ws}"
PKG="mesh_plugin"
SRC="$WS/src/$PKG"
CORE_DIR="$SRC/$PKG"
ONLY_OFFLINE=0
DO_CLEAN=0
for a in "$@"; do
  case "$a" in
    --offline) ONLY_OFFLINE=1 ;;
    --clean)   DO_CLEAN=1 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "argument necunoscut: $a (vezi --help)"; exit 2 ;;
  esac
done

# ---- culori (dezactivate daca nu e terminal) ----
if [ -t 1 ]; then
  G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; B=$'\033[1m'; N=$'\033[0m'
else
  G=""; R=""; Y=""; B=""; N=""
fi

PASS=0; FAIL=0; WARN=0
declare -a RESULTS

ok()   { echo "  ${G}[OK]${N}   $1";   PASS=$((PASS+1)); RESULTS+=("${G}OK${N}   $1"); }
bad()  { echo "  ${R}[ESEC]${N} $1";   FAIL=$((FAIL+1)); RESULTS+=("${R}ESEC${N} $1"); }
warn() { echo "  ${Y}[ATENTIE]${N} $1"; WARN=$((WARN+1)); RESULTS+=("${Y}ATENTIE${N} $1"); }
step() { echo; echo "${B}== $1 ==${N}"; }

# =====================================================================
step "Pasul 1 - structura pachetului"
need_files=(
  "package.xml" "setup.py" "setup.cfg" "resource/$PKG"
  "$PKG/__init__.py" "$PKG/mesh_core.py" "$PKG/mesh_node.py"
  "$PKG/sil_mesh.py" "$PKG/sil_mesh_mission.py"
  "launch/mesh_plugins.launch.py"
)
if [ ! -d "$SRC" ]; then
  bad "pachetul nu exista la $SRC  (copiaza-l in ~/ros2_ws/src/)"
else
  miss=0
  for f in "${need_files[@]}"; do
    if [ -e "$SRC/$f" ]; then :; else bad "lipseste: $f"; miss=$((miss+1)); fi
  done
  [ "$miss" -eq 0 ] && ok "toate cele ${#need_files[@]} fisiere necesare sunt prezente"
fi

# =====================================================================
step "Pasul 2 - verificare OFFLINE (Python pur, fara ROS)"
if [ ! -d "$CORE_DIR" ]; then
  bad "directorul de cod $CORE_DIR nu exista - sar peste verificarea offline"
else
  # 2a. sintaxa tuturor modulelor
  syntax_ok=1
  for py in mesh_core.py mesh_node.py sil_mesh.py sil_mesh_mission.py; do
    if python3 -c "import ast,sys; ast.parse(open('$CORE_DIR/$py').read())" 2>/dev/null; then :;
    else bad "sintaxa Python invalida: $py"; syntax_ok=0; fi
  done
  [ "$syntax_ok" -eq 1 ] && ok "sintaxa Python valida in toate modulele"

  # 2b. selftest nucleu (21 verificari)
  out="$(cd "$CORE_DIR" && python3 mesh_core.py 2>&1)"
  if echo "$out" | grep -q "toate OK"; then
    n="$(echo "$out" | grep -oE '[0-9]+ verificari' | head -1)"
    ok "mesh_core selftest: $n trecute"
  else
    bad "mesh_core selftest a esuat:"
    echo "$out" | grep -E "FAIL|ESUATE" | sed 's/^/        /'
  fi

  # 2c. SIL reachability ruleaza
  if (cd "$CORE_DIR" && python3 sil_mesh.py >/dev/null 2>&1); then
    ok "sil_mesh.py ruleaza fara erori"
  else
    bad "sil_mesh.py a esuat (ruleaza-l manual ca sa vezi eroarea)"
  fi

  # 2d. SIL misiune ruleaza + extrage cifrele
  out="$(cd "$CORE_DIR" && python3 sil_mesh_mission.py 2>&1)"
  if [ $? -eq 0 ] && echo "$out" | grep -q "MESH"; then
    star="$(echo "$out" | grep -oE 'STEA[^%]*[0-9.]+%' | grep -oE '[0-9.]+%' | head -1)"
    mesh="$(echo "$out" | grep -oE 'MESH[^%]*[0-9.]+%' | grep -oE '[0-9.]+%' | head -1)"
    ok "sil_mesh_mission.py ruleaza (acoperire stea $star -> mesh $mesh)"
  else
    bad "sil_mesh_mission.py a esuat"
  fi
fi

if [ "$ONLY_OFFLINE" -eq 1 ]; then
  echo; echo "${B}(--offline: ma opresc inainte de colcon)${N}"
fi

# =====================================================================
if [ "$ONLY_OFFLINE" -eq 0 ]; then
  step "Pasul 3 - colcon build"
  if ! command -v colcon >/dev/null 2>&1; then
    bad "colcon nu e instalat (sudo apt install python3-colcon-common-extensions)"
  elif [ -z "${ROS_DISTRO:-}" ]; then
    warn "ROS nu e sourcuit (source /opt/ros/jazzy/setup.bash) - incerc oricum"
  fi
  if command -v colcon >/dev/null 2>&1 && [ -d "$WS/src" ]; then
    if [ "$DO_CLEAN" -eq 1 ]; then
      echo "  (curat build/install pentru $PKG)"
      rm -rf "$WS/build/$PKG" "$WS/install/$PKG"
    fi
    echo "  ruleaza: colcon build --packages-select $PKG --symlink-install"
    if (cd "$WS" && colcon build --packages-select "$PKG" --symlink-install \
          >/tmp/mesh_build.log 2>&1); then
      ok "colcon build a reusit"
    else
      bad "colcon build a esuat - ultimele linii din /tmp/mesh_build.log:"
      tail -12 /tmp/mesh_build.log | sed 's/^/        /'
    fi
  fi

  # =====================================================================
  step "Pasul 4 - verificare instalare"
  if [ -f "$WS/install/setup.bash" ]; then
    # sourcing intr-un subshell ca sa nu murdarim mediul curent
    execs="$(bash -c "source '$WS/install/setup.bash' 2>/dev/null && \
             ros2 pkg executables $PKG 2>/dev/null")"
    if echo "$execs" | grep -q "mesh_node"; then
      n="$(echo "$execs" | grep -c "$PKG")"
      ok "pachetul expune $n executabile (mesh_node / sil_mesh / sil_mesh_mission)"
    else
      bad "ros2 pkg executables $PKG nu listeaza nimic (verifica setup.cfg)"
    fi
  else
    bad "$WS/install/setup.bash nu exista (build-ul nu a produs install/)"
  fi
fi

# =====================================================================
step "Rezumat"
for r in "${RESULTS[@]}"; do echo "  $r"; done
echo
echo "  ${G}OK: $PASS${N}   ${Y}ATENTIE: $WARN${N}   ${R}ESEC: $FAIL${N}"
if [ "$FAIL" -eq 0 ]; then
  echo "  ${G}${B}Totul e in regula.${N}"
  [ "$ONLY_OFFLINE" -eq 0 ] && echo "  Urmatorul pas: ros2 launch $PKG mesh_plugins.launch.py"
  exit 0
else
  echo "  ${R}${B}Sunt $FAIL probleme - vezi mai sus.${N} (Depanare: WORKFLOW_LOCAL.md, sectiunea 8)"
  exit 1
fi
