"""g_sub.py -- abonat minimal pentru gate-ul C3. Scrie READY cand abonarea e facuta si
RECV cu momentul PRIMULUI mesaj livrat. Iese dupa primul mesaj sau la expirare."""
import sys
import time

T_EXEC = time.time()

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


def main():
    durata = float(sys.argv[1] if len(sys.argv) > 1 else 15)
    rclpy.init()
    n = Node("g_sub")
    stare = {"t": None, "n": 0}

    def on_msg(m):
        if stare["t"] is None:
            stare["t"] = time.time()
            print("RECV %.6f %s" % (stare["t"], m.data), flush=True)
        stare["n"] += 1

    n.create_subscription(String, "/c3_gate", on_msg, 10)
    print("T_EXEC %.6f" % T_EXEC, flush=True)
    print("READY %.6f" % time.time(), flush=True)
    t_stop = time.time() + durata
    while rclpy.ok() and time.time() < t_stop and stare["t"] is None:
        rclpy.spin_once(n, timeout_sec=0.05)
    if stare["t"] is None:
        print("NIMIC (expirat dupa %.1fs)" % durata, flush=True)
    print("TOTAL %d" % stare["n"], flush=True)
    n.destroy_node()
    rclpy.shutdown()


main()
