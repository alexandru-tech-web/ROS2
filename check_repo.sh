#!/usr/bin/env bash
# check_repo.sh -- preflight de STRUCTURA si SANATATE a monorepo-ului.
#
# Diferit de preflight_misiune.sh (care verifica mediul ROS inainte de campania
# reala). Acesta confirma ca, dupa ce ai pus fisierele pe pozitie:
#   1. fiecare pachet are fisierele asteptate (structura);
#   2. dependentele fiecarui pachet sunt prezente (module langa el);
#   3. tot codul Python compileaza (py_compile);
#   4. testele pure trec (mesh, plugins, degradare);
#   5. SIL-urile produc rezultatele asteptate (gradient, mesh, campanie).
#
# Ruleaza fara ROS (doar Python pur). Verdict GO / NO-GO la final.
#
#   bash check_repo.sh            # din ~/ros2_ws/src
#   SRC=~/alt/cale bash check_repo.sh
set -u

SRC="${SRC:-$HOME/ros2_ws/src}"
OK=1
PASS=0
FAIL=0

nota()    { printf "  %-58s %s\n" "$1" "$2"; }
trece()   { nota "$1" "[ok]"; PASS=$((PASS+1)); }
esueaza() { nota "$1" "[NU]"; FAIL=$((FAIL+1)); OK=0; }
sectiune(){ printf "\n== %s ==\n" "$1"; }

cd "$SRC" 2>/dev/null || { echo "[eroare] nu exista $SRC"; exit 1; }
echo "== check_repo: $SRC =="

# ---------------------------------------------------------------------------
sectiune "1. Structura pachetelor (fisiere prezente)"

verifica_fisier() {  # verifica_fisier <cale> <eticheta>
  if [ -f "$1" ]; then trece "$2"; else esueaza "$2 (lipseste: $1)"; fi
}

# mesh_plugin (pachet nou)
verifica_fisier "mesh_plugin/mesh_core.py"         "mesh_plugin: mesh_core.py"
verifica_fisier "mesh_plugin/test_mesh_core.py"    "mesh_plugin: test_mesh_core.py"
verifica_fisier "mesh_plugin/sil_mesh.py"          "mesh_plugin: sil_mesh.py"
verifica_fisier "mesh_plugin/mesh_node.py"         "mesh_plugin: mesh_node.py"
verifica_fisier "mesh_plugin/mesh_demo.py"         "mesh_plugin: mesh_demo.py"
verifica_fisier "mesh_plugin/sil_mesh_mission.py"  "mesh_plugin: sil_mesh_mission.py"
verifica_fisier "mesh_plugin/README.md"            "mesh_plugin: README.md"

# sar_swarm (fisiere modificate + unelte noi)
verifica_fisier "sar_swarm/sil_run.py"             "sar_swarm: sil_run.py"
verifica_fisier "sar_swarm/netem_core.py"          "sar_swarm: netem_core.py"
verifica_fisier "sar_swarm/drone_node.py"          "sar_swarm: drone_node.py"
verifica_fisier "sar_swarm/gcs_node_ros.py"        "sar_swarm: gcs_node_ros.py"
verifica_fisier "sar_swarm/test_degradation.py"    "sar_swarm: test_degradation.py"
verifica_fisier "sar_swarm/analyze_rmw.py"         "sar_swarm: analyze_rmw.py"
verifica_fisier "sar_swarm/run_sil_campaign.py"    "sar_swarm: run_sil_campaign.py"
verifica_fisier "sar_swarm/scenarios/mesh_relay.yaml" "sar_swarm: scenarios/mesh_relay.yaml"
verifica_fisier "sar_swarm/README.md"              "sar_swarm: README.md"

# teleop_rover
verifica_fisier "teleop_rover/README.md"           "teleop_rover: README.md"

# ---------------------------------------------------------------------------
sectiune "2. Dependente pe pozitie (module langa pachet)"

# mesh_plugin are nevoie de aceste module ca sa ruleze fara ROS
for m in radio_link node_utils sar_core swarm_core netem_core world_config; do
  verifica_fisier "mesh_plugin/${m}.py" "mesh_plugin: dependenta ${m}.py"
done

# verificare CHEIE: netem_core din mesh_plugin trebuie sa fie versiunea NOUA
# (cu lat_samples in snapshot). Altfel SIL-urile cad cu KeyError.
if grep -q "lat_samples" "mesh_plugin/netem_core.py" 2>/dev/null \
   && grep -q "lat_samples" "mesh_plugin/netem_core.py" \
   && grep -A2 "def snapshot" "mesh_plugin/netem_core.py" >/dev/null 2>&1 \
   && grep "lat_samples" "mesh_plugin/netem_core.py" | grep -q "list("; then
  trece "mesh_plugin: netem_core e versiunea NOUA (lat_samples expus)"
else
  esueaza "mesh_plugin: netem_core NOU (ruleaza: cp sar_swarm/netem_core.py mesh_plugin/)"
fi
if grep "lat_samples" "sar_swarm/netem_core.py" 2>/dev/null | grep -q "list("; then
  trece "sar_swarm: netem_core e versiunea NOUA (lat_samples expus)"
else
  esueaza "sar_swarm: netem_core NOU (copiaza versiunea din Downloads)"
fi

# verificare: drone_node pune timestamp t in telemetrie (pt e2e ROS)
if grep -q '"t": self.get_clock' "sar_swarm/drone_node.py" 2>/dev/null; then
  trece "sar_swarm: drone_node pune timestamp e2e in telemetrie"
else
  esueaza "sar_swarm: drone_node cu timestamp e2e (copiaza din Downloads)"
fi

# ---------------------------------------------------------------------------
sectiune "3. Compilare Python (py_compile)"

compileaza_dir() {  # compileaza_dir <pachet>
  local pkg="$1"
  local bad=0
  while IFS= read -r f; do
    python3 -m py_compile "$f" 2>/dev/null || { bad=$((bad+1)); echo "      [!] $f"; }
  done < <(find "$pkg" -name "*.py" 2>/dev/null)
  if [ "$bad" = 0 ]; then trece "$pkg: tot Python compileaza"
  else esueaza "$pkg: $bad fisiere NU compileaza"; fi
}
compileaza_dir "mesh_plugin"
compileaza_dir "sar_swarm"
compileaza_dir "teleop_rover"

# ---------------------------------------------------------------------------
sectiune "4. Teste pure (fara ROS)"

ruleaza_test() {  # ruleaza_test <dir> <script> <eticheta> <pattern_succes>
  local dir="$1" scr="$2" et="$3" pat="$4"
  if [ ! -f "$dir/$scr" ]; then esueaza "$et (lipseste $scr)"; return; fi
  if (cd "$dir" && python3 "$scr" 2>/dev/null | grep -qE "$pat"); then
    trece "$et"
  else
    esueaza "$et (vezi: cd $dir && python3 $scr)"
  fi
}
ruleaza_test "mesh_plugin" "test_mesh_core.py" \
  "mesh_plugin: test_mesh_core 31/31" "31/31 verificari trecute"
ruleaza_test "mesh_plugin" "mesh_core.py" \
  "mesh_plugin: mesh_core selftest 20/20" "20/20 verificari trecute"

# test_plugins (daca exista sar_plugins)
if [ -f "sar_plugins/test_plugins.py" ]; then
  ruleaza_test "sar_plugins" "test_plugins.py" \
    "sar_plugins: test_plugins 55/55" "55/55 verificari trecute"
fi

# ---------------------------------------------------------------------------
sectiune "5. SIL: rezultate asteptate"

# mesh_plugin trebuie sa aiba scenariile (sau le luam din sar_swarm)
if [ ! -d "mesh_plugin/scenarios" ] && [ -d "sar_swarm/scenarios" ]; then
  echo "      [info] copiez scenariile in mesh_plugin pentru SIL"
  cp -r sar_swarm/scenarios mesh_plugin/ 2>/dev/null
fi

# sil_mesh: star vs mesh (exit 0 = toate verificarile trec)
if (cd mesh_plugin && python3 sil_mesh.py >/dev/null 2>&1); then
  trece "mesh_plugin: sil_mesh (star vs mesh OK)"
else
  esueaza "mesh_plugin: sil_mesh (vezi: cd mesh_plugin && python3 sil_mesh.py)"
fi

# sil_mesh_mission: mesh recupereaza telemetria
if (cd mesh_plugin && python3 sil_mesh_mission.py --scenario mesh_relay 2>/dev/null \
    | grep -qE "mesh afla cu .* mai devreme|verificari trecute"); then
  trece "mesh_plugin: sil_mesh_mission (mesh ajuta sub izolare)"
else
  esueaza "mesh_plugin: sil_mesh_mission (vezi rularea manuala)"
fi

# test_degradation: gradientul (5/5 GO)
if (cd sar_swarm && python3 test_degradation.py --reps 2 2>/dev/null \
    | grep -q "VERDICT: GO"); then
  trece "sar_swarm: test_degradation GO (gradient masurabil)"
else
  esueaza "sar_swarm: test_degradation GO (vezi rularea manuala)"
fi

# ---------------------------------------------------------------------------
sectiune "6. Igiena repo (.git imbricat, dubluri)"

NESTED=$(find . -mindepth 2 -name ".git" -maxdepth 3 2>/dev/null)
if [ -z "$NESTED" ]; then
  trece "niciun .git imbricat (colcon e fericit)"
else
  esueaza "GIT imbricat gasit (strica colcon): $NESTED"
fi

# ---------------------------------------------------------------------------
echo
echo "================================================================"
printf "  REZULTAT: %d trecute, %d esuate\n" "$PASS" "$FAIL"
if [ "$OK" = 1 ]; then
  echo "  VERDICT: GO -- totul pe pozitie, compilabil, rezultate OK."
else
  echo "  VERDICT: NO-GO -- rezolva liniile [NU] de mai sus."
fi
echo "================================================================"
exit $((1 - OK))
