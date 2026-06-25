#!/usr/bin/env python3
"""fault_injector_node.py -- Injecteaza degradarea retelei din FISIERUL de
scenariu YAML (aceleasi fisiere ca SIL-ul): publica starea legaturilor pe
/sar/linkstate (gating + latenta aplicate de noduri la receptie) si, optional
(use_tc:=true, iface:=wlan0), aplica tc netem REAL pe interfata -- pentru
rulari pe masini separate (masuratorile de teza)."""
import json, os, subprocess, sys, time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from netem_core import load_scenario, link_key

NODES = ["gcs", "d1", "d2", "d3", "d4"]

class FaultInjector(Node):
    def __init__(self):
        super().__init__("fault_injector")
        self.declare_parameter("scenario", "scenarios/baseline.yaml")
        self.declare_parameter("use_tc", False)
        self.declare_parameter("iface", "lo")
        path = self.get_parameter("scenario").value
        import os.path as _p
        if _p.basename(str(path)) in ("none", "none.yaml", "manual"):
            self.sc = {"name": "manual (doar butoanele operatorului)",
                       "default_link": {"base_ms": 40.0}, "events": []}
        else:
            self.sc = load_scenario(path)
        self.use_tc = bool(self.get_parameter("use_tc").value)
        self.iface = self.get_parameter("iface").value
        self.pub = self.create_publisher(String, "/sar/linkstate", 10)
        self.create_subscription(String, "/sar/operator", self.on_operator, 10)
        d = self.sc["default_link"]
        self.down = set()
        self.lat = {link_key(a, b): d.get("base_ms", 40.0)
                    for i, a in enumerate(NODES) for b in NODES[i+1:]}
        self.jit = {k: d.get("jitter_ms", 0.0) for k in self.lat}
        self.loss = {k: d.get("loss", 0.0) for k in self.lat}
        self.t0 = time.time()
        self.done = set()
        self.create_timer(0.2, self.tick)
        self.get_logger().info(f"scenariu: {self.sc['name']} ({path}); "
                               f"tc={'ON iface='+self.iface if self.use_tc else 'off'}")
        if self.use_tc:
            self._tc(d.get("base_ms", 0), d.get("jitter_ms", 0),
                     d.get("loss", 0.0))

    def on_operator(self, msg: String):
        """Defecte injectate LIVE de operator (din dashboard), peste scenariu."""
        c = json.loads(msg.data)
        if c.get("type") != "fault":
            return
        a = c.get("action")
        self.get_logger().warn(f"OPERATOR defect: {a} {c}")
        if a == "isolate" and c.get("id"):
            self.down |= {k for k in self.lat if c["id"] in k.split("-")}
        elif a == "restore" and c.get("id"):
            self.down -= {k for k in self.lat if c["id"] in k.split("-")}
        elif a == "partition":
            from netem_core import link_key as lk
            self.down |= {lk(x, y) for x in ("gcs", "d1", "d2")
                          for y in ("d3", "d4")}
        elif a == "heal_all":
            self.down.clear()
        elif a == "latency" and c.get("ms") is not None:
            for k in self.lat:
                self.lat[k] = float(c["ms"])
            if self.use_tc:
                self._tc(float(c["ms"]), 0, 0.0)
        elif a in ("set_all", "set_link"):
            ks = list(self.lat) if a == "set_all" else (
                [c["link"]] if c.get("link") in self.lat else [])
            for k in ks:
                if c.get("ms") is not None:
                    self.lat[k] = float(c["ms"])
                if c.get("jit") is not None:
                    self.jit[k] = float(c["jit"])
                if c.get("loss") is not None:
                    self.loss[k] = max(0.0, min(1.0, float(c["loss"])))
                if c.get("down") is True:
                    self.down.add(k)
                elif c.get("down") is False:
                    self.down.discard(k)
            if self.use_tc and a == "set_all":
                self._tc(float(c.get("ms", 40.0)), float(c.get("jit", 0.0)),
                         float(c.get("loss", 0.0)))

    def _tc(self, base, jit, loss):
        cmd = (f"tc qdisc replace dev {self.iface} root netem "
               f"delay {base}ms {jit}ms loss {loss*100:.1f}%")
        self.get_logger().info(f"tc: {cmd}")
        subprocess.run(["sudo", "bash", "-c", cmd], check=False)

    def tick(self):
        t = time.time() - self.t0
        for i, ev in enumerate(self.sc["events"]):
            if i in self.done or t < ev.get("t", 0):
                continue
            self.done.add(i)
            typ = ev["type"]
            self.get_logger().warn(f"t={t:.0f}s EVENIMENT: {typ} {ev}")
            if typ == "isolate":
                self.down |= {k for k in self.lat if ev["node"] in k.split("-")}
            elif typ == "restore_node":
                self.down -= {k for k in self.lat if ev["node"] in k.split("-")}
            elif typ == "partition":
                self.down |= {link_key(a, b) for a in ev["group_a"]
                              for b in ev["group_b"]}
            elif typ == "heal_partition":
                self.down -= {link_key(a, b) for a in ev["group_a"]
                              for b in ev["group_b"]}
            elif typ in ("set_all", "set_link"):
                ks = list(self.lat) if typ == "set_all" \
                     else [link_key(ev["a"], ev["b"])]
                for k in ks:
                    if ev.get("base_ms") is not None:
                        self.lat[k] = float(ev["base_ms"])
                    if ev.get("jitter_ms") is not None:
                        self.jit[k] = float(ev["jitter_ms"])
                    if ev.get("loss") is not None:
                        self.loss[k] = float(ev["loss"])
                if self.use_tc and typ == "set_all":
                    self._tc(ev.get("base_ms", 0), ev.get("jitter_ms", 0),
                             ev.get("loss", 0.0))
        self.pub.publish(String(data=json.dumps(
            {"scenario": self.sc["name"], "t": round(t, 1),
             "down": sorted(self.down), "lat_ms": self.lat,
             "jit_ms": self.jit, "loss": self.loss})))

def main():
    rclpy.init(); n = FaultInjector()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally:
        n.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__": main()
