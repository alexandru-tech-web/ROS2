#!/usr/bin/env python3
"""gcs_node_ros.py — Ground Control Station: fuzioneaza hartile dronelor,
aloca frontiere (re-planificare la fiecare 1 s, doar dronelor vazute recent),
confirma harta (ack monoton), publica starea misiunii si scrie metricile in
~/sar_data/mission_metrics.csv. Gating-ul legaturilor: la receptie."""
import json, math, os, sys, time
import random
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sar_core import GridWorld, DiscoveredMap, allocate_frontiers, cohesion
from world_config import WORLD, DRONES
from operator_core import OperatorState

class GcsNode(Node):
    def __init__(self):
        super().__init__("sar_gcs")
        self.world = GridWorld(**WORLD)
        self.map = DiscoveredMap(self.world)
        self.declare_parameter("autostart", True)
        self.ops = OperatorState(sorted(DRONES),
                                 autostart=bool(self.get_parameter("autostart").value))
        self.last_seen, self.pos, self.state = {}, {}, {}
        self.victims = set()
        self.links_down, self.lat_ms = set(), {}
        self.loss_p, self.jit_ms = {}, {}
        self.inbox = []
        self.cmd_pubs = {}
        self.status_pub = self.create_publisher(String, "/sar/status", 10)
        self.create_subscription(String, "/sar/telemetry", self.on_tele_raw, 30)
        self.create_subscription(String, "/sar/linkstate", self.on_link, 10)
        self.create_subscription(String, "/sar/operator", self.on_operator, 10)
        self.create_timer(1.0, self.allocate)
        self.create_timer(0.5, self.publish_status)
        self.create_timer(0.05, self.drain)
        os.makedirs(os.path.expanduser("~/sar_data"), exist_ok=True)
        self.csv = open(os.path.expanduser("~/sar_data/mission_metrics.csv"), "w")
        self.csv.write("t_s,coverage,victims_found,cohesion,drones_linked,"
                       "e2e_telemetry_ms,msgs_delivered\n")
        self.e2e_samples = []
        self.msgs_delivered = 0
        self.op_csv = open(os.path.expanduser("~/sar_data/op_commands.csv"), "w")
        self.op_csv.write("t_s,cmd_id,drone,action,phase\n")
        self.t0 = time.time()
        self.get_logger().info(
            f"GCS pornit — misiune: {self.ops.mission} "
            f"(autostart={self.ops.mission == 'RUNNING'})")

    def link_up(self, d): return f"d-gcs".replace("d", d) not in self.links_down \
        if False else ("-".join(sorted((d, "gcs"))) not in self.links_down)

    def on_link(self, msg):
        d = json.loads(msg.data)
        self.links_down = set(d.get("down", []))
        self.lat_ms = d.get("lat_ms", {})
        self.loss_p = d.get("loss", {})
        self.jit_ms = d.get("jit_ms", {})

    def on_operator(self, msg):
        cmd = json.loads(msg.data)
        if cmd.get("type") == "fault":
            return                          # tratat de fault_injector
        for did, payload in self.ops.handle(cmd):
            self._cmd(did, payload)
            self._op_log(payload["cmd_id"], did, payload["a"], "sent")
        if cmd.get("type") == "mission":
            self.get_logger().warn(f"OPERATOR: misiune -> {self.ops.mission}")

    def _op_log(self, cid, did, action, phase):
        self.op_csv.write(
            f"{time.time() - self.t0:.2f},{cid},{did},{action},{phase}\n")
        self.op_csv.flush()

    def on_tele_raw(self, msg):
        d = json.loads(msg.data)
        did = d.get("id")
        if not did or not self.link_up(did):
            return
        k = "-".join(sorted((did, "gcs")))
        if random.random() < self.loss_p.get(k, 0.0):
            return                                   # pierdere de pachet
        jit = self.jit_ms.get(k, 0.0)
        lat = max(0.0, self.lat_ms.get(k, 0.0)
                  + random.uniform(-jit, jit)) / 1000.0
        self.inbox.append((time.time() + lat, d))

    def drain(self):
        now = time.time()
        due = [m for m in self.inbox if m[0] <= now]
        self.inbox = [m for m in self.inbox if m[0] > now]
        for _, d in due:
            did = d["id"]
            self.last_seen[did] = now
            # latenta e2e: varsta informatiei cand ajunge la GCS (daca drona a
            # pus timestamp "t" la emisie). Reflecta si intarzierea S&F.
            t_emit = d.get("t")
            if t_emit is not None:
                age_ms = max(0.0, (now - float(t_emit)) * 1000.0)
                self.e2e_samples.append(age_ms)
                self.e2e_samples = self.e2e_samples[-2000:]
            if d.get("k") == "op_event":     # ack/done/fail la comanda operator
                self.ops.on_event(did, d.get("phase"))
                self._op_log(d.get("cmd_id", 0), did, "-", d.get("phase"))
                continue
            self.pos[did] = tuple(d["pos"][:2])
            self.state[did] = d.get("state", "?")
            self.map.merge_cells([tuple(c) for c in d["cells"]])
            self.victims.update(map(tuple, d["victims"]))
            self.msgs_delivered += 1
            self._cmd(did, {"k": "map_ack",
                            "upto": d["from"] + len(d["cells"])})

    def _cmd(self, did, payload):
        if did not in self.cmd_pubs:
            self.cmd_pubs[did] = self.create_publisher(String, f"/sar/cmd/{did}", 20)
        self.cmd_pubs[did].publish(String(data=json.dumps(payload)))

    def allocate(self):
        now = time.time()
        elig = self.ops.auto_eligible()
        fresh = {d: self.world.to_cell(*p) for d, p in self.pos.items()
                 if d in elig and now - self.last_seen.get(d, 0) < 4.0
                 and self.link_up(d)}
        for d, tgt in allocate_frontiers(fresh, self.map.frontiers()).items():
            self._cmd(d, {"k": "goto_frontier", "cell": list(tgt)})

    def publish_status(self):
        t = time.time() - self.t0
        cov = self.map.coverage()
        linked = sum(1 for d in self.pos if self.link_up(d))
        coh = cohesion(self.pos) if self.pos else 1.0
        self.status_pub.publish(String(data=json.dumps({
            "t": round(t, 1), "coverage": round(cov, 4),
            "mission": self.ops.mission,
            "victims": sorted(self.victims),
            "victims_total": len(self.world.victims),
            "drones": {d: {"pos": list(self.pos[d]),
                           "state": self.state.get(d, "?"),
                           "mode": self.ops.mode.get(d, "AUTO"),
                           "age_s": round(t - 0 if d not in self.last_seen
                                          else time.time()-self.last_seen[d], 1),
                           "link": self.link_up(d)} for d in self.pos}})))
        # latenta e2e curenta: media ultimelor mostre (varsta telemetriei)
        e2e_now = (round(sum(self.e2e_samples[-20:]) / len(self.e2e_samples[-20:]), 1)
                   if self.e2e_samples else 0.0)
        self.csv.write(f"{t:.1f},{cov:.4f},{len(self.victims)},{coh:.3f},"
                       f"{linked},{e2e_now},{self.msgs_delivered}\n")
        self.csv.flush()

def main():
    rclpy.init(); n = GcsNode()
    try: rclpy.spin(n)
    except KeyboardInterrupt: pass
    finally:
        n.csv.close(); n.op_csv.close(); n.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__": main()
