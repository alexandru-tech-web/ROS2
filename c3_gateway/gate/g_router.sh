#!/bin/bash
# g_router.sh start|stop -- routerul Zenoh pentru gate-ul C3 (domeniu 77, izolat)
set +u
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=77
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
export RUST_LOG=warn

case "$1" in
  start)
    setsid nohup ros2 run rmw_zenoh_cpp rmw_zenohd > "$S/router.log" 2>&1 </dev/null &
    sleep 4
    if pgrep -f "rmw_zenoh[d]$" > /dev/null; then
      echo "router PORNIT (pid $(pgrep -f 'rmw_zenoh[d]$' | head -1))"
    else
      echo "router NU a pornit; ultimele linii:"; tail -5 "$S/router.log"
    fi
    ;;
  stop)
    pkill -f "rmw_zenoh[d]$" && echo "router OPRIT" || echo "router nu rula"
    ;;
esac
