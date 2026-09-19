#!/usr/bin/env python3
"""rover_node.py -- nod ROS 2 SUBTIRE peste plant (rover_dyn) + filtru (brate) +
certificat (certif_core). S3. Aceeasi bucla ca episode.run_episode, dar canalul e
REAL: lo cu netem, prin rmw.

Asculta /c6/cmd_op si /c6/hazard (JSON cu t_tx); publica /c6/pose dupa fiecare pas.
  A_cmd = acum - t_tx(cmd)   (peste T_hold -> (0,0), ca in channel_core)
  A_haz = acum - t_tx(haz)   (fara taiere: Lema 1)
Pe fiecare flux castiga pachetul cu t_tx cel mai NOU (reordonarea nu intoarce starea).
Acelasi ceas pe ambele noduri (loopback) -- DECLARAT, nu masurat.

Timpul de simulare e NOMINAL: t_k = k*dt, plantul face exact un pas F la fiecare
tick al timerului de 20 Hz. Ceasul de perete conduce doar comunicatia (varstele).
Perioada reala a tick-ului se masoara si intra in metrics (tick_ms_mediu/max).

Adevarul o_true: scenariul "traversare" e analitic, evaluat la t_abs - t0 (t0 vine
in mesajul de hazard de la GCS) -- exact ce a publicat / ar fi publicat GCS-ul.
V, d_min, certificatul (i) se calculeaza pe acest adevar, ca in core.

Episodul porneste la primul cmd + primul hazard receptionate; se termina la T_G
sau T_max; scrie <outputs>/<eticheta>_{trace.csv,metrics.json,certificate.json}
prin io_core si iese (codul 0 daca a scris; launch-ul se opreste la iesirea lui).
Parametri ROS: brat, scenariu, v_o_max, seed, react, outputs, eticheta, qos.
"""
import json
import math
import os
import statistics
import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

_AICI = os.path.dirname(os.path.abspath(__file__))
if _AICI not in sys.path:
    sys.path.insert(0, _AICI)
import brate                                                 # noqa: E402
import cbf_core                                              # noqa: E402
import certif_core                                           # noqa: E402
import episode                                               # noqa: E402
import io_core                                               # noqa: E402
from operator_node import qos_din                            # noqa: E402
import models                                                # noqa: E402
import rover_dyn                                             # noqa: E402
from c6_params import Params                                 # noqa: E402


class RoverNode(Node):
    def __init__(self):
        super().__init__("c6_rover")
        for k, v in (("brat", "A2"), ("scenariu", "traversare"), ("v_o_max", 0.5), ("seed", 1),
                     ("react", False), ("outputs", ""), ("eticheta", "s3"), ("qos", "reliable"), ("mod_dt", "max"),
                     ("dt_max_admis", 0.15)):
            self.declare_parameter(k, v)
        g = lambda k: self.get_parameter(k).value                        # noqa: E731
        self.brat = g("brat")
        self.P = Params(scenariu=g("scenariu"), v_o_max=float(g("v_o_max")), seed=int(g("seed")))
        if self.brat not in brate.BRATE:
            raise SystemExit("rover_node: brat necunoscut %r" % self.brat)
        if self.P.scenariu != "traversare":
            raise SystemExit("rover_node: scenariul %r NU e suportat in S3 (vezi operator_node)" % self.P.scenariu)
        self.outputs = os.path.expanduser(g("outputs")) or None
        self.eticheta = g("eticheta")
        self.filtru, self.sf = brate.filtru_pentru(self.brat, self.P)
        if self.sf is not None:
            self.sf.mod_dt = str(g("mod_dt"))                 # "pas" | "max" (V0.1)
            self.sf.dt_max_admis = float(g("dt_max_admis"))   # P0-HIL: peste -> stare sigura, n_dt
        self.model = models.Unicycle(self.P.tau_act)
        self.haz = episode.Hazard(self.P)
        self.st = rover_dyn.Stare(x=self.P.start[0], y=self.P.start[1], theta=self.P.start[2])
        self.cmd = None          # (v, w, t_tx) cu t_tx cel mai nou
        self.hz = None           # (ox, oy, t_tx, t0)
        self.k = 0
        self.n_pasi = int(round(self.P.T_max / self.P.dt))
        self.trace = []
        self.V = self.n_inf = self.n_blocat = 0
        self.d_min = float("inf")
        self.suma_int = 0.0
        self.T_G = None
        self.t_tick = []
        self.n_rx_cmd = self.n_rx_haz = 0
        self.gata = False
        q = qos_din(g("qos"))
        self.pub_pose = self.create_publisher(String, "/c6/pose", q)
        self.create_subscription(String, "/c6/cmd_op", self._pe_cmd, q)
        self.create_subscription(String, "/c6/hazard", self._pe_haz, q)
        self.create_timer(self.P.dt, self._tick)
        self.get_logger().info("rover: brat=%s scenariu=%s v_o=%.2f seed=%d outputs=%s"
                               % (self.brat, self.P.scenariu, self.P.v_o_max, self.P.seed, self.outputs))

    def _acum(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def _pe_cmd(self, msg):
        d = json.loads(msg.data)
        self.n_rx_cmd += 1
        if self.cmd is None or d["t_tx"] > self.cmd[2]:
            self.cmd = (d["v"], d["w"], d["t_tx"])

    def _pe_haz(self, msg):
        d = json.loads(msg.data)
        self.n_rx_haz += 1
        if self.hz is None or d["t_tx"] > self.hz[2]:
            self.hz = (d["ox"], d["oy"], d["t_tx"], d["t0"])

    def _tick(self):
        if self.gata:
            return
        if self.cmd is None or self.hz is None:
            return                                  # episodul porneste cu ambele fluxuri vii
        acum = self._acum()
        self.t_tick.append(acum)
        P = self.P
        t = self.k * P.dt

        # comanda: hold-last cel mult T_hold (channel_core.primeste, flux "cmd")
        v_op, w_op, t_tx = self.cmd
        aoi = acum - t_tx
        cmd = (0.0, 0.0) if aoi > P.T_hold else (v_op, w_op)
        # pericolul raportat: fara taiere (Lema 1)
        ox_h, oy_h, t_tx_h, t0 = self.hz
        o_hat, A_haz = (ox_h, oy_h), acum - t_tx_h
        dt_m = (acum - self.t_tick[-2]) if len(self.t_tick) >= 2 else None       # V0.1: pasul REAL
        ctx = {"o_hat": o_hat, "A_haz": A_haz, "dt_masurat": dt_m}

        h = r_eff = feasible = kkt = None
        if self.filtru is not None:
            cmd, info, infez = self.filtru(self.st, cmd, P, ctx)
            self.n_inf += int(infez)
            h, feasible, kkt = info.get("h"), info.get("feasible"), info.get("kkt_res")
            r_eff = info.get("r_eff")

        st_pre = self.st
        self.st = self.model.step(self.st, cmd, P.dt)
        self.k += 1
        t = self.k * P.dt
        st = self.st
        px, py = episode.punct_control(st, P.l)
        ox, oy = self.haz.o_true(acum + P.dt - t0)     # adevarul, pe ceasul GCS
        d_o = math.hypot(px - ox, py - oy)
        d_g = math.hypot(px - P.goal[0], py - P.goal[1])
        self.d_min = min(self.d_min, d_o)
        if d_o < P.r:
            self.V += 1
        self.suma_int += math.hypot(cmd[0] - v_op, cmd[1] - w_op)
        if st.v < episode.V_BLOCAT and v_op > episode.V_OP_ACTIV:
            self.n_blocat += 1
        self.trace.append({"t": round(t, 4), "x_pre": st_pre.x, "y_pre": st_pre.y,
                           "theta_pre": st_pre.theta, "v_pre": st_pre.v, "x": st.x, "y": st.y,
                           "theta": st.theta, "v": st.v, "omega": st.omega, "v_op": v_op, "omega_op": w_op,
                           "AoI_cmd": aoi, "A_haz": A_haz, "o_hat_x": o_hat[0], "o_hat_y": o_hat[1],
                           "o_true_x": ox, "o_true_y": oy, "h": h, "r_eff": r_eff,
                           "feasible": feasible, "kkt_res": kkt, "u_v": cmd[0], "u_w": cmd[1]})
        self.pub_pose.publish(String(data=json.dumps({"x": st.x, "y": st.y, "theta": st.theta,
                                                      "v": st.v, "t": t})))
        if self.T_G is None and d_g < P.goal_tol:
            self.T_G = round(t, 4)
        if self.T_G is not None or self.k >= self.n_pasi:
            self._incheie()

    def _incheie(self):
        self.gata = True
        n = len(self.trace)
        per = [1e3 * (b - a) for a, b in zip(self.t_tick, self.t_tick[1:])]
        m = {"V": self.V, "d_min": None if n == 0 else round(self.d_min, 6),
             "J_int": round(self.suma_int / n, 6) if n else None, "T_G": self.T_G,
             "B": round(self.n_blocat / float(n), 6) if n else None,
             "n_inf": self.sf.n_inf if self.sf else 0, "n_ws": getattr(self.sf, "n_ws", 0) if self.sf else 0,
             "n_pasi": n, "brat": self.brat, "seed": self.P.seed, "model": self.model.nume,
             "A_haz_max": round(max(q["A_haz"] for q in self.trace), 4) if n else None,
             "AoI_cmd_max": round(max(q["AoI_cmd"] for q in self.trace), 4) if n else None,
             "n_rx_cmd": self.n_rx_cmd, "n_rx_haz": self.n_rx_haz,
             "tick_ms_mediu": round(statistics.mean(per), 2) if per else None,
             "tick_ms_max": round(max(per), 2) if per else None,
             "transport": "ros2/" + os.environ.get("RMW_IMPLEMENTATION", "?"), "qos": self.get_parameter("qos").value,
             # schema_v2 (F1): ce inainte se recupera din manifest / eticheta
             "schema": "v2", "scenariu": self.P.scenariu, "v_o_max": self.P.v_o_max,
             "react": bool(self.get_parameter("react").value), "dt": self.P.dt, "T_max": self.P.T_max,
             "gamma": self.sf.gamma if self.sf else None, "delta_DT": self.sf.delta_DT if self.sf else None,
             "n_dt_marginit": self.sf.n_dt_marginit if self.sf else None, "mod_dt": self.get_parameter("mod_dt").value,
             "n_dt": self.sf.n_dt if self.sf else 0, "dt_max_admis": self.sf.dt_max_admis if self.sf else None,
             "dt_max_vazut": round(self.sf.dt_max, 4) if self.sf else None}
        g = self.sf.gamma if self.sf else cbf_core.GAMMA_IMPLICIT
        poz = {q["t"]: (q["o_true_x"], q["o_true_y"]) for q in self.trace}
        c = certif_core.certify(self.trace, self.P, lambda t: poz.get(t, self.haz.o_true(t)), g)
        m["cert"] = c["verdict"]
        c["n_dt"] = m["n_dt"]                                  # K4: pasi peste dt_max_admis, in certificat
        self.get_logger().info("rover: %s" % json.dumps(m, sort_keys=True))
        if self.outputs:
            io_core.scrie(self.outputs, m, self.trace, self.eticheta, certificat=c)
            self.get_logger().info("rover: scris in %s (%s)" % (self.outputs, self.eticheta))
        raise SystemExit(0)


def main(args=None):
    rclpy.init(args=args)
    n = RoverNode()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
