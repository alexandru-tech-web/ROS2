#!/bin/bash
# g_scope.sh -- ruleaza launch-ul de scope. Mediul mostenit e pus INTENTIONAT pe fastrtps,
# ca sa se vada daca procesul din afara grupurilor il pastreaza (scope respectat) sau
# primeste valoarea vreunui grup (scurgere).
set +u
S=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=77
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp        # martorul
timeout 30 ros2 launch "$S/g_scope.launch.py" 2>&1 | grep -E "SCOPE|ERROR" | sed 's/^\[[^]]*\] //'
