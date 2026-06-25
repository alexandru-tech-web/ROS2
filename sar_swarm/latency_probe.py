#!/usr/bin/env python3
"""latency_probe.py -- Sonda de latenta/pierdere (descendenta directa a
latency_pub/latency_sub din planul de benchmark al tezei): GCS-ul trimite
ping (2 Hz) catre fiecare drona; pong-ul masoara RTT. Scrie
~/sar_data/rtt_log.csv si publica statistici pe /sar/probe/stats
(RTT mediu/p95 si pierderea pe fereastra de 10 s, per drona)."""
import json, os, time
import random
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

IDS = ["d1", "d2", "d3", "d4"]

class LatencyProbe(Node):
    def __init__(self):
        super().__init__("latency_probe")
        self.pub = self.create_publisher(String, "/sar/probe/ping", 20)
        self.stats_pub = self.create_publisher(String, "/sar/probe/stats", 10)
        self.create_subscription(String, "/sar/probe/pong", self.on_pong, 20)
        self.create_subscription(String, "/sar/linkstate", self.on_link, 10)
        self.links_down, self.lat_ms = set(), {}
        self.loss_p, self.jit_ms = {}, {}
        self.inbox = []
        self.create_timer(0.05, self.drain)
        os.makedirs(os.path.expanduser("~/sar_data"), exist_ok=True)
        self.csv = open(os.path.expanduser("~/sar_data/rtt_log.csv"), "w")
        self.csv.write("t_s,drone,rtt_ms\n")
        self.t0 = time.time()
        self.seq = 0
        self.sent = {d: {} for d in IDS}     # seq -> t
        self.window = {d: [] for d in IDS}   # (t, rtt_ms)
        self.create_timer(0.5, self.ping_all)
        self.create_timer(2.0, self.publish_stats)

    def ping_all(self):
        for d in IDS:
            self.seq += 1
            t = time.time()
            self.sent[d][self.seq] = t
            self.pub.publish(String(data=json.dumps(
                {"to": d, "seq": self.seq, "t": t})))
            # expira ping-urile mai vechi de 5 s (pierdute)
            self.sent[d] = {s: tt for s, tt in self.sent[d].items()
                            if t - tt < 5.0 or s == self.seq}

    def on_link(self, msg):
        d = json.loads(msg.data)
        self.links_down = set(d.get("down", []))
        self.lat_ms = d.get("lat_ms", {})
        self.loss_p = d.get("loss", {})
        self.jit_ms = d.get("jit_ms", {})

    def on_pong(self, msg):
        # drumul de intoarcere sufera ACEEASI degradare ca dus-ul
        d = json.loads(msg.data)
        k = "-".join(sorted((d["id"], "gcs")))
        if k in self.links_down:
            return
        if random.random() < self.loss_p.get(k, 0.0):
            return
        jit = self.jit_ms.get(k, 0.0)
        lat = max(0.0, self.lat_ms.get(k, 0.0)
                  + random.uniform(-jit, jit)) / 1000.0
        self.inbox.append((time.time() + lat, d))

    def drain(self):
        now = time.time()
        due = [m for m in self.inbox if m[0] <= now]
        self.inbox = [m for m in self.inbox if m[0] > now]
        for _, d in due:
            self._pong_proc(d)

    def _pong_proc(self, d):
        t_emit = self.sent.get(d["id"], {}).pop(d["seq"], None)
        if t_emit is None:
            return
        now = time.time()
        rtt = (now - t_emit) * 1000.0
        self.window[d["id"]].append((now, rtt))
        self.csv.write(f"{now - self.t0:.2f},{d['id']},{rtt:.1f}\n")

    def publish_stats(self):
        now = time.time()
        out = {}
        for d in IDS:
            self.window[d] = [(t, r) for t, r in self.window[d] if now - t < 10.0]
            rtts = sorted(r for _, r in self.window[d])
            expected = 20            # 2 Hz x 10 s
            loss = max(0.0, 1.0 - len(rtts) / expected)
            out[d] = {"rtt_mean_ms": round(sum(rtts)/len(rtts), 1) if rtts else None,
                      "rtt_p95_ms": round(rtts[int(0.95*(len(rtts)-1))], 1) if rtts else None,
                      "loss_10s": round(loss, 2)}
        self.csv.flush()
        self.stats_pub.publish(String(data=json.dumps(out)))

def main():
    rclpy.init(); n = LatencyProbe()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally:
        n.csv.close(); n.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__": main()
