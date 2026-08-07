#!/usr/bin/env python3
"""app_pub.py -- aplicatia de teleoperare, simulata: publica la ritm fix pe /c3/app.
Ritmul si sarcina utila sunt cele din C1/C2 (50 Hz, 4096 B), ca cifrele sa fie comparabile."""
import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile
from std_msgs.msg import String


def main():
    hz = float(sys.argv[1]) if len(sys.argv) > 1 else 50.0
    octeti = int(sys.argv[2]) if len(sys.argv) > 2 else 4096
    durata = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
    rclpy.init()
    nod = Node("c3_app_pub")
    pub = nod.create_publisher(String, "/c3/app", QoSProfile(depth=50))
    sarcina = "x" * octeti
    t0 = time.clock_gettime(time.CLOCK_MONOTONIC)
    n = 0
    while time.clock_gettime(time.CLOCK_MONOTONIC) - t0 < durata:
        tinta = t0 + n / hz
        dt = tinta - time.clock_gettime(time.CLOCK_MONOTONIC)
        if dt > 0:
            time.sleep(dt)
        m = String()
        m.data = sarcina
        pub.publish(m)
        n += 1
        rclpy.spin_once(nod, timeout_sec=0.0)
    print("APP publicate=%d" % n, flush=True)
    nod.destroy_node()
    rclpy.shutdown()


main()
