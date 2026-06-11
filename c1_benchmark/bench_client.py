#!/usr/bin/env python3
"""bench_client.py — microbenchmarkul de transport (latency pub/sub din
planul tezei): publica mesaje cu timbru de timp si sarcina utila de
dimensiune data, masoara RTT pe ecou, scrie CSV-ul brut + rezumatul JSON.

  python3 bench_client.py --payload 4096 --rate 50 --duration 30 \
          --out results_c1/.../transport_p4096.csv
"""
import argparse, json, os, sys, time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bench_core import make_payload, rtt_stats

class Client(Node):
    def __init__(self, a):
        super().__init__("bench_client")
        self.a = a
        self.data = make_payload(a.payload)
        self.sent = {}
        self.rtts = []
        self.seq = 0
        self.warm = 10                      # primele 10: incalzire, ignorate
        self.t_end = time.time() + a.duration + 1.0
        self.pub = self.create_publisher(String, "/bench/ping", 50)
        self.create_subscription(String, "/bench/pong", self.on_pong, 50)
        self.create_timer(1.0 / a.rate, self.tick)

    def tick(self):
        if time.time() >= self.t_end - 1.0:
            return
        self.seq += 1
        self.sent[self.seq] = time.time()
        self.pub.publish(String(data=json.dumps(
            {"seq": self.seq, "t": self.sent[self.seq], "d": self.data})))

    def on_pong(self, msg):
        d = json.loads(msg.data)
        t0 = self.sent.pop(d["seq"], None)
        if t0 is None or d["seq"] <= self.warm:
            return
        self.rtts.append((d["seq"], (time.time() - t0) * 1000.0))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", type=int, default=4096)
    ap.add_argument("--rate", type=float, default=50.0)
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--out", default="transport.csv")
    a = ap.parse_args()
    rclpy.init(); n = Client(a)
    t_stop = time.time() + a.duration + 1.5   # +1.5 s: ecourile in zbor
    while rclpy.ok() and time.time() < t_stop:
        rclpy.spin_once(n, timeout_sec=0.05)
    sent_eff = max(0, n.seq - n.warm)
    st = rtt_stats([r for _, r in n.rtts], sent_eff, len(n.rtts))
    st.update(payload=a.payload, rate_hz=a.rate, duration_s=a.duration,
              rmw=os.environ.get("RMW_IMPLEMENTATION", "default"))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        f.write("seq,rtt_ms\n")
        for s, r in n.rtts:
            f.write(f"{s},{r:.3f}\n")
    with open(os.path.splitext(a.out)[0] + "_summary.json", "w") as f:
        json.dump(st, f, indent=1)
    print(json.dumps(st, indent=1))
    n.destroy_node()
    if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__": main()
