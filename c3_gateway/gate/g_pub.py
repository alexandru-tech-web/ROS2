"""g_pub.py -- publicator minimal pentru gate-ul C3. Tipareste, pe stdout, momentele
cheie cu time.time() (acelasi ceas ca abonatul, deci comparabile intre procese)."""
import sys
import time

T_EXEC = time.time()            # cat mai devreme posibil in proces

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def main():
    rclpy.init()
    n = Node("g_pub")
    pub = n.create_publisher(String, "/c3_gate", 10)
    print("T_EXEC %.6f" % T_EXEC, flush=True)
    print("T_INIT %.6f" % time.time(), flush=True)
    i = 0
    t_stop = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 12)
    while rclpy.ok() and time.time() < t_stop:
        m = String()
        m.data = "msg %d" % i
        pub.publish(m)
        if i == 0:
            print("T_FIRST_PUB %.6f" % time.time(), flush=True)
        i += 1
        rclpy.spin_once(n, timeout_sec=0.0)
        time.sleep(0.1)
    n.destroy_node()
    rclpy.shutdown()


main()
