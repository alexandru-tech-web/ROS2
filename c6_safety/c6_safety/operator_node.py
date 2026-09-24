#!/usr/bin/env python3
"""operator_node.py -- nod ROS 2 SUBTIRE peste operator_core + Hazard (partea GCS). S3.

Publica:
  /c6/cmd_op  (std_msgs/String, JSON {"v","w","t_tx"})        la 20 Hz  (1/dt)
  /c6/hazard  (std_msgs/String, JSON {"ox","oy","t_tx","t0"}) la f_haz
Asculta:
  /c6/pose    (JSON {"x","y","theta","v"}) -- ce vede operatorul; vine prin ACELASI lo
              cu netem, deci e INTARZIAT (in core feedbackul e instantaneu -- declarat).

t_tx = ceasul nodului (secunde, float) la emitere: joaca rolul lui header.stamp. Pe
loopback ambele noduri au acelasi ceas, deci receptorul poate calcula A = acum - t_tx.
t0 = momentul pornirii episodului la GCS; roverul evalueaza adevarul o_true(t - t0)
cu el (scenariul "traversare" e analitic in t). Pana la prima poza, operatorul
comanda din params.start, pe care il stie (altfel nimeni nu porneste).

NICIO logica aici: Operator.cmd si Hazard.o_true vin din core. Parametri ROS:
scenariu, v_o_max, react, f_haz, qos (suprascriu c6_params).
"""
import json
import os
import sys

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

_AICI = os.path.dirname(os.path.abspath(__file__))
if _AICI not in sys.path:
    sys.path.insert(0, _AICI)
import episode                                               # noqa: E402
import operator_core                                         # noqa: E402
import rover_dyn                                             # noqa: E402
import c6_params
from c6_params import Params                                 # noqa: E402


def qos_din(nume, adancime=10):
    """reliable = implicitul rclpy (pierderea devine retransmisie, deci latenta);
    best_effort = pierderea ramane pierdere, ca in DelayLossChannel."""
    r = {"reliable": ReliabilityPolicy.RELIABLE, "best_effort": ReliabilityPolicy.BEST_EFFORT}[nume]
    return QoSProfile(depth=adancime, reliability=r)


class OperatorNode(Node):
    def __init__(self):
        super().__init__("c6_operator")
        self.declare_parameter("scenariu", "traversare")
        self.declare_parameter("v_o_max", 0.5)
        self.declare_parameter("react", False)
        self.declare_parameter("f_haz", 5.0)
        self.declare_parameter("qos", "reliable")       # | best_effort; factor pentru S4
        g = lambda k: self.get_parameter(k).value                        # noqa: E731
        self.P = Params(scenariu=g("scenariu"), v_o_max=float(g("v_o_max")), f_haz=float(g("f_haz")))
        if self.P.scenariu not in c6_params.SCENARII_NODURI:
            raise SystemExit("operator_node: scenariul %r NU e suportat de noduri; suportate: %s "
                             "(urmarirea cere pozitia roverului la GCS, care ajunge intarziata)"
                             % (self.P.scenariu, ", ".join(c6_params.SCENARII_NODURI)))
        self.op = operator_core.Operator(self.P, react=bool(g("react")))
        self.haz = episode.Hazard(self.P)
        self.st = rover_dyn.Stare(x=self.P.start[0], y=self.P.start[1], theta=self.P.start[2])
        self.t0 = self._acum()
        self.n_cmd = self.n_haz = self.n_pose = 0
        q = qos_din(g("qos"))
        self.pub_cmd = self.create_publisher(String, "/c6/cmd_op", q)
        self.pub_haz = self.create_publisher(String, "/c6/hazard", q)
        self.create_subscription(String, "/c6/pose", self._pe_pose, q)
        self.create_timer(self.P.dt, self._tick_cmd)
        self.create_timer(1.0 / self.P.f_haz, self._tick_haz)
        self.get_logger().info("operator: scenariu=%s v_o=%.2f f_haz=%.1f react=%s t0=%.3f"
                               % (self.P.scenariu, self.P.v_o_max, self.P.f_haz, self.op.react, self.t0))

    def _acum(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _pe_pose(self, msg):
        d = json.loads(msg.data)
        self.st = rover_dyn.Stare(x=d["x"], y=d["y"], theta=d["theta"], v=d["v"])
        self.n_pose += 1

    def _tick_cmd(self):
        t = self._acum()
        v, w = self.op.cmd(self.st, t - self.t0)
        self.pub_cmd.publish(String(data=json.dumps({"v": v, "w": w, "t_tx": t})))
        self.n_cmd += 1

    def _tick_haz(self):
        t = self._acum()
        ox, oy = self.haz.o_true(t - self.t0)
        self.pub_haz.publish(String(data=json.dumps({"ox": ox, "oy": oy, "t_tx": t, "t0": self.t0})))
        self.n_haz += 1


def main(args=None):
    rclpy.init(args=args)
    n = OperatorNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        print("operator: cmd=%d haz=%d pose=%d n_reactii=%d"
              % (n.n_cmd, n.n_haz, n.n_pose, n.op.n_reactii), file=sys.stderr)
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
