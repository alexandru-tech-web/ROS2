#!/usr/bin/env bash
# netem_profiles.sh — Profiluri de degradare a retelei pentru telereabilitare,
# identice cu metodologia benchmark-ului rmw_zenoh vs CycloneDDS:
# pierdere de pachete 0 / 5 / 15 / 30 %, optional cu intarziere + jitter.
#
# Utilizare (necesita sudo):
#   ./netem_profiles.sh status            # arata regula activa
#   ./netem_profiles.sh loss5             # 5%  pierdere
#   ./netem_profiles.sh loss15            # 15% pierdere
#   ./netem_profiles.sh loss30            # 30% pierdere
#   ./netem_profiles.sh sar               # scenariu SAR: 10% pierdere + 40ms ± 20ms
#   ./netem_profiles.sh wifi_slab         # WiFi slab: 5% pierdere + 80ms ± 40ms
#   ./netem_profiles.sh clear             # elimina orice degradare (= loss0)
#
# Interfata implicita este "lo" (totul pe o singura masina, ca in benchmark).
# Pe doua masini, setati interfata reala:   IFACE=eth0 ./netem_profiles.sh loss15
#
# ATENTIE: degradarea pe "lo" afecteaza TOT traficul local (inclusiv Gazebo<->ROS
# daca ruleaza pe aceeasi masina) — exact conditia de test din articol; notati
# profilul activ in eticheta CSV a lui operator_heartbeat (parametrul "label").

set -euo pipefail

IFACE="${IFACE:-lo}"

clear_rules() {
    sudo tc qdisc del dev "$IFACE" root 2>/dev/null || true
}

apply() {
    clear_rules
    sudo tc qdisc add dev "$IFACE" root netem "$@"
    echo "aplicat pe $IFACE: netem $*"
}

case "${1:-}" in
    status)
        tc qdisc show dev "$IFACE"
        ;;
    clear|loss0)
        clear_rules
        echo "degradare eliminata pe $IFACE (conditii ideale)"
        ;;
    loss5)   apply loss 5% ;;
    loss15)  apply loss 15% ;;
    loss30)  apply loss 30% ;;
    sar)     apply loss 10% delay 40ms 20ms distribution normal ;;
    wifi_slab) apply loss 5% delay 80ms 40ms distribution normal ;;
    *)
        echo "utilizare: $0 {status|clear|loss5|loss15|loss30|sar|wifi_slab}"
        echo "interfata curenta: $IFACE (schimba cu IFACE=eth0 $0 ...)"
        exit 1
        ;;
esac
