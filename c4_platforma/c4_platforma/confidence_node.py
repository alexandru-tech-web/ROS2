#!/usr/bin/env python3
"""confidence_node.py -- ROLUL ROVER: publica /network_confidence (alpha) si /network_age (age, AoI) la `hz`, din
confidence_core.FereastraViab (v2, P0-1: fereastra de viabilitate a gateway-ului C3; DOC/CAIETE/P0_SPEC_V2.md).

Modul VIU: sonda C4 proprie /c4/ping -> /c4/pong (ecoul operatorului, ecou_node), o sonda la fiecare tick (`hz`, implicit 5);
expirarea verificata la fiecare 0.05 s (ca gateway-ul C3); t_tx si t_rx = ceasul LOCAL monoton al roverului; stamp-ul din
pong (ceasul perechii) intra DOAR in age_stamp (jurnalizata, nu publicata in control).
Modul RELUARE (`reluare:=<dosarul unei rulari C3>`): in loc de ping / pong, rezultatele sondelor caii `cale` din
out/gateway/esantioane.csv intra in nucleu in timp real, de la `t_start_rel` (implicit t_sfarsit - 61 s; istoria de dinainte
se reda instant); publica si /c4/reluare (String JSON {t_rel, k, n, alpha, age}); la capatul datelor nu mai publica.
Jurnal CSV (parametrul `jurnal`, gol = fara): t, seq_ultim, alpha, age_sonda, age_stamp, rtt_ultim (coloanele v1).
Parametri: hz (5.0), W (50), T_sonda (1.0), permite_nealiniat (false), jurnal, reluare, cale (zenoh), t_start_rel (-1 = auto).
W != 50 sau T_sonda != 1.0 fara permite_nealiniat:=true -> refuz (alpha-ul tezei e unul singur). T_dead (v1) -> ignorat."""
import csv
import json
import os
import sys
import time

import rclpy
import rclpy.executors
from rclpy.node import Node
from std_msgs.msg import Float32, String

_AICI = os.path.dirname(os.path.abspath(__file__))
if _AICI not in sys.path:
    sys.path.insert(0, _AICI)
import confidence_core as cc                                           # noqa: E402


def citeste_grupuri(dosar_rulare, cale):
    """esantioane.csv -> [(t_mono, [(primit, rtt_s sau None), ...] pentru randurile P ale caii)], un element pe GRUP (randuri
    consecutive cu acelasi t_mono = un apel al gateway-ului). Grupurile fara P pe cale raman (t, [])."""
    p = os.path.join(dosar_rulare, "out", "gateway", "esantioane.csv")
    grupuri = []
    with open(p, newline="") as f:
        for r in csv.DictReader(f):
            t = float(r["t_mono"])
            if not grupuri or grupuri[-1][0] != t:
                grupuri.append((t, []))
            if r["tip"] == "P" and r["cale"] == cale:
                grupuri[-1][1].append((r["primit"] == "1", float(r["rtt_ms"]) / 1000.0 if r["rtt_ms"] else None))
    return grupuri


class Confidence(Node):
    def __init__(self):
        super().__init__("c4_confidence_rover")
        for k, v in (("hz", cc.HZ_SONDA), ("W", cc.W_VIAB), ("T_sonda", cc.T_SONDA), ("permite_nealiniat", False),
                     ("T_dead", -1.0), ("jurnal", ""), ("reluare", ""), ("cale", "zenoh"), ("t_start_rel", -1.0)):
            self.declare_parameter(k, v)
        g = lambda k: self.get_parameter(k).value                          # noqa: E731
        W_, T_s, hz = int(g("W")), float(g("T_sonda")), float(g("hz"))
        if (W_ != cc.W_VIAB or T_s != cc.T_SONDA) and not g("permite_nealiniat"):
            raise SystemExit("c4: W=%d / T_sonda=%.3f difera de alpha-ul C3 (W=%d, T_sonda=%.1f); refuz fara permite_nealiniat:=true"
                             % (W_, T_s, cc.W_VIAB, cc.T_SONDA))
        if float(g("T_dead")) >= 0.0:
            self.get_logger().warn("c4: T_dead=%.3f e parametrul v1 (inlocuit la P0-1) -- IGNORAT" % float(g("T_dead")))
        self.hz = hz
        self.pa = self.create_publisher(Float32, "/network_confidence", 10)
        self.pg = self.create_publisher(Float32, "/network_age", 10)
        self.jurnal = open(os.path.expanduser(g("jurnal")), "w") if g("jurnal") else None
        if self.jurnal:
            self.jurnal.write("t,seq_ultim,alpha,age_sonda,age_stamp,rtt_ultim\n")
        self.seq = 0
        self.n_pong = 0
        self.n_tick = 0
        self.reluare = g("reluare")
        if self.reluare:
            self._porneste_reluare(W_, T_s, g("cale"), float(g("t_start_rel")))
        else:
            self.f = cc.FereastraViab(W_, T_s, t_start=time.monotonic())
            self.pp = self.create_publisher(String, "/c4/ping", 20)
            self.create_subscription(String, "/c4/pong", self._pe_pong, 20)
            self.create_timer(cc.PERIOADA_EXPIRARE, self._expira)
            self.create_timer(1.0 / hz, self._tick)
        self.get_logger().info("c4 confidence (rover, v2): W=%d T_sonda=%.2f s hz=%.1f; nucleu %s; switching %s; %s"
                               % (W_, T_s, hz, cc.__file__, cc._switching().__file__,
                                  "RELUARE %s cale=%s t_start_rel=%.3f" % (self.reluare, g("cale"), self.t_start_rel)
                                  if self.reluare else "VIU (/c4/ping -> /c4/pong)"))

    # ------------------------------------------------------------------ viu
    def _pe_pong(self, msg):
        d = json.loads(msg.data)
        self.f.ecou(int(d["seq"]), time.monotonic(), t_tx=d.get("t_tx"), stamp=d.get("stamp"))
        self.n_pong += 1

    def _expira(self):
        self.f.expira(time.monotonic())

    def _tick(self):
        now = time.monotonic()
        self.seq += 1
        self.f.trimite(self.seq, now)
        self.pp.publish(String(data=json.dumps({"seq": self.seq, "t_tx": now})))
        self._publica(now, now)

    # ------------------------------------------------------------------ reluare
    def _porneste_reluare(self, W_, T_s, cale, t_start_rel):
        self.grupuri = citeste_grupuri(self.reluare, cale)
        self.t_sfarsit = self.grupuri[-1][0]
        self.t_start_rel = t_start_rel if t_start_rel >= 0.0 else self.t_sfarsit - 61.0
        if self.t_start_rel < 0.0:
            raise SystemExit("c4 reluare: t_start_rel=%.3f < 0 (jurnal de %.3f s)" % (self.t_start_rel, self.t_sfarsit))
        self.f = cc.FereastraViab(W_, T_s, t_start=0.0)
        self.i = 0
        self._avanseaza(self.t_start_rel)                     # istoria de dinainte, instant
        self.pr = self.create_publisher(String, "/c4/reluare", 20)
        self.t_perete0 = time.monotonic()
        self.capat = False
        self.create_timer(1.0 / self.hz, self._tick_reluare)

    def _avanseaza(self, t_rel):
        while self.i < len(self.grupuri) and self.grupuri[self.i][0] <= t_rel:
            t, rez = self.grupuri[self.i]
            for primit, rtt in rez:
                self.f.rezolvata(primit, t_rx=t if primit else None, rtt=rtt)
                self.seq += 1
            self.i += 1

    def _tick_reluare(self):
        t_rel = self.t_start_rel + (time.monotonic() - self.t_perete0)
        if t_rel > self.t_sfarsit:
            if not self.capat:
                self.capat = True
                self.get_logger().info("c4 reluare: capatul datelor la t_rel=%.3f (t_sfarsit=%.3f); nu mai public"
                                       % (t_rel, self.t_sfarsit))
                if self.jurnal:
                    self.jurnal.write("# capatul datelor la t_rel=%.4f\n" % t_rel)
                    self.jurnal.flush()
            return
        self._avanseaza(t_rel)
        a, b = self._publica(t_rel, None)
        self.pr.publish(String(data=json.dumps({"t_rel": round(t_rel, 6), "k": self.f.k(), "n": self.f.n(),
                                                "alpha": a, "age": b})))

    # ------------------------------------------------------------------ comun
    def _publica(self, t, t_mono_viu):
        a = self.f.alpha()
        b = self.f.age(t)
        self.pa.publish(Float32(data=float(a)))
        self.pg.publish(Float32(data=float(b)))
        self.n_tick += 1
        if self.jurnal:
            st = self.f.age_stamp(self.get_clock().now().nanoseconds * 1e-9) if t_mono_viu is not None else None
            self.jurnal.write("%.4f,%d,%.4f,%.4f,%s,%s\n" % (t, self.seq, a, b, "" if st is None else "%.4f" % st,
                                                            "" if self.f.ultim is None else "%.4f" % self.f.ultim[1]))
        if self.n_tick % 100 == 0:
            self.get_logger().info("c4: alpha=%.2f (k=%d n=%d) age=%.3f s pong=%d" % (a, self.f.k(), self.f.n(), b, self.n_pong))
        return a, b


def main(args=None):
    rclpy.init(args=args)
    n = Confidence()
    try:
        rclpy.spin(n)
    except (KeyboardInterrupt, rclpy.executors.ExternalShutdownException):
        pass
    finally:
        if n.jurnal:
            n.jurnal.close()
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
