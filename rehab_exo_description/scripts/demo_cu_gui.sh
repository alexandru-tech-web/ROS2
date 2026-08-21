#!/usr/bin/env bash
# demo_cu_gui.sh -- porneste demonstratia CU fereastra Gazebo, dintr-un terminal snap.
#
# DE CE E NEVOIE DE ASTA
# Terminalul VSCode e pornit din snap si scurge biblioteci 'core20' in mediul
# proceselor copil. 'gz sim gui' moare atunci instant cu
#     symbol lookup error: /snap/core20/.../libpthread.so.0: __libc_pthread_init
# iar cand GUI-ul moare, 'gz sim' escaladeaza la SIGKILL pe SERVER: lumea nu mai
# paseste, /clock tace si controller_manager-ul nu mai e actualizat.
#
# Curatarea doar a lui LD_LIBRARY_PATH NU ajuta -- snap-ul injecteaza si LOCPATH,
# GTK_PATH, GDK_PIXBUF_MODULEDIR, GIO_MODULE_DIR, GSETTINGS_SCHEMA_DIR, XDG_DATA_DIRS.
# Scriptul porneste deci cu 'env -i' si repune DOAR ce trebuie, inclusiv acreditarile
# de afisare (pe Wayland: DISPLAY + XAUTHORITY pentru Xwayland, WAYLAND_DISPLAY si
# XDG_RUNTIME_DIR). Verificat pe 22 aug 2026: demonstratia completa ruleaza cu
# fereastra, toate cele patru verdicte ale monitorului verzi.
#
# Utilizare:  ./scripts/demo_cu_gui.sh [argumente pentru demo_c4.launch.py]
#   ./scripts/demo_cu_gui.sh exercitiu:=ankle_pump viteza:=1.5
#
# Dintr-un terminal care NU vine din snap, scriptul nu e necesar:
#   ros2 launch rehab_exo_description demo_c4.launch.py gui:=true
set -euo pipefail

: "${DISPLAY:?DISPLAY nu e setat -- nu exista afisaj catre care sa porneasca fereastra}"
INSTALL="${REHAB_INSTALL:-$HOME/ros2_ws/install/setup.bash}"
if [ ! -f "$INSTALL" ]; then
  echo "Nu gasesc '$INSTALL'. Seteaza REHAB_INSTALL catre setup.bash-ul tau." >&2
  exit 2
fi

exec env -i \
  HOME="$HOME" USER="$USER" TERM="${TERM:-xterm}" \
  DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
  WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-}" \
  XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
  XDG_SESSION_TYPE="${XDG_SESSION_TYPE:-x11}" \
  PATH=/usr/local/bin:/usr/bin:/bin \
  ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}" \
  RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}" \
  bash -c "source /opt/ros/jazzy/setup.bash; source '$INSTALL'; \
           exec ros2 launch rehab_exo_description demo_c4.launch.py gui:=true $*"
