#!/usr/bin/env python3
"""episode.py -- o rulare completa: operator -> canal -> (filtru) -> vehicul.

METRICILE, copiate din caiet v0.1 sec. 8, cuvant cu cuvant:
  V     = nr. de pasi cu ||p - O|| < r (violari hard)
  d_min = min_k ||p_k - O||
  J_int = media pe pasi a ||u_k - u_op,k||   (cat a intervenit filtrul)
  T_G   = timpul pana la ||p - G|| < goal_tol; esec (None) daca T_G > T_max
  B     = fractiunea de pasi cu v < 0.05 m/s in timp ce v_op > 0.2 m/s (blocaj)
  n_inf = nr. QP infezabile

p este PUNCTUL DE CONTROL, nu centrul: p = (x, y) + l*(cos theta, sin theta),
caiet sec. 2. Toate distantele (obstacol si tinta) se masoara pe p, altfel
metricile nu ar fi cele definite.

FARA ROS, FARA netem. safety_filter e un callable (st, cmd, params) -> (u, info,
infezabil); vezi cbf_core.ca_safety_filter. Fara el, vehiculul executa exact ce a
primit prin canal.

Rulare: python3 episode.py --selftest
"""
import hashlib
import json
import math
import os
import sys

_AICI = os.path.dirname(os.path.abspath(__file__))
if _AICI not in sys.path:
    sys.path.insert(0, _AICI)

import channel_core                                          # noqa: E402
import models                                                # noqa: E402
import operator_core                                         # noqa: E402
import rover_dyn                                            # noqa: E402
from c6_params import Params                                 # noqa: E402

V_BLOCAT = 0.05      # m/s, caiet sec. 8
V_OP_ACTIV = 0.2     # m/s, caiet sec. 8


def punct_control(state, l):
    """p = (x, y) + l*(cos theta, sin theta). Caiet sec. 2."""
    return (state.x + l * math.cos(state.theta),
            state.y + l * math.sin(state.theta))


class Hazard(object):
    """Pericolul mobil, trei scenarii (ERATA 3 + ERATA 6):
      "traversare":      pleaca din hazard_start, merge pe +y cu v_o, se opreste la hazard_end_y
                         (analitic in t);
      "urmarire":        se misca spre pozitia CURENTA a roverului cu v_o (integrat pas cu pas;
                         are nevoie de pozitia roverului, deci episode il face sa avanseze).
      "schimba_directia": ca traversarea, dar semnul vitezei se INVERSEAZA la fiecare moment din
                         params.directie_t. Analitic in t, deci fara stare si fara samanta; rolul
                         lui (ERATA 6) e sa arate unde cedeaza un predictor cu viteza constanta.
                         Nu se opreste la hazard_end_y: plafonul de acolo ar ascunde tocmai
                         intoarcerea pe care scenariul o testeaza.
    o_true(t) e ADEVARUL; roverul vede doar ce vine pe canal, la f_haz, cu intarziere."""

    def __init__(self, params, v_o=None, start=None, scenariu=None):
        self.p = params
        self.v_o = params.v_o_max if v_o is None else v_o
        self.x0, self.y0 = start if start is not None else params.hazard_start
        self.scenariu = scenariu or params.scenariu
        self.x, self.y = self.x0, self.y0          # pozitia curenta (urmarire)
        self.istoric = {}                           # t -> (x, y), pentru certificat

    def avanseaza(self, rover_xy, t, dt):
        """Un pas de urmarire; in traversare nu face nimic (pozitia e analitica)."""
        if self.scenariu == "urmarire":
            dx, dy = rover_xy[0] - self.x, rover_xy[1] - self.y
            d = math.hypot(dx, dy)
            if d > 1e-9:
                pas = min(self.v_o * dt, d)
                self.x += pas * dx / d
                self.y += pas * dy / d
        self.istoric[round(t, 4)] = self.o_true(t)

    def _y_schimba(self, t):
        """y(t) cu semnul vitezei inversat la fiecare moment din params.directie_t.
        Liniar pe bucati, continuu, analitic -- nicio stare, deci o_true(t) se poate cere
        in orice ordine (certificatul si redarea o cer si inapoi in timp)."""
        y, semn, t_prec = self.y0, 1.0, 0.0
        for tc in sorted(self.p.directie_t):
            if t <= tc:
                break
            y += semn * self.v_o * (tc - t_prec)
            semn = -semn
            t_prec = tc
        return y + semn * self.v_o * (t - t_prec)

    def o_true(self, t):
        if self.scenariu == "urmarire":
            if round(t, 4) in self.istoric:
                return self.istoric[round(t, 4)]
            return (self.x, self.y)
        if self.scenariu == "schimba_directia":
            return (self.x0, self._y_schimba(t))
        y = self.y0 + self.v_o * t
        y = max(min(y, self.p.hazard_end_y), self.y0) if self.v_o >= 0 else y
        return (self.x0, y)


def run_episode(params, model, channel, safety_filter=None, react=False, hazard=None):
    st = rover_dyn.Stare(x=params.start[0], y=params.start[1], theta=params.start[2])
    ox, oy = params.obst
    gx, gy = params.goal

    op = operator_core.Operator(params, react=react)
    o_true = hazard.o_true if hazard is not None else (lambda t: params.obst)
    t_ultim_haz = -1e9
    perioada_haz = (1.0 / params.f_haz) if (hazard is not None and params.f_haz > 0) else None
    trace = []
    V = n_inf = n_blocat = 0
    d_min = float("inf")
    suma_int = 0.0
    T_G = None
    t = 0.0
    n_pasi = int(round(params.T_max / params.dt))

    for _ in range(n_pasi):
        v_op, w_op = op.cmd(st, t)
        channel.trimite((v_op, w_op), t)
        cmd, aoi = channel.primeste(t)

        # pericolul raportat de GCS, la f_haz, pe ACELASI canal
        o_hat, A_haz = None, None
        if perioada_haz is not None:
            if (t - t_ultim_haz >= perioada_haz - 1e-9
                    and operator_core.raportor_activ(t, params.pauza_haz_t, params.pauza_haz_durata)):
                channel.trimite(o_true(t), t, flux="haz")
                t_ultim_haz = t
            o_hat, A_haz = channel.primeste(t, flux="haz")
        ctx = {"o_hat": o_hat, "A_haz": A_haz}

        h = r_eff = feasible = kkt = None
        if safety_filter is not None:
            cmd, info, infez = safety_filter(st, cmd, params, ctx)
            n_inf += int(infez)
            if isinstance(info, dict):
                h, feasible, kkt = info.get("h"), info.get("feasible"), info.get("kkt_res")
                r_eff = info.get("r_eff")                  # None = stare sigura (n_ws)
            else:
                h = info

        st_pre = st
        st = model.step(st, cmd, params.dt)
        t += params.dt
        if hazard is not None:
            hazard.avanseaza((st.x, st.y), t, params.dt)

        px, py = punct_control(st, params.l)
        ox, oy = o_true(t)                       # V si d_min pe pericolul ADEVARAT
        d_o = math.hypot(px - ox, py - oy)
        d_g = math.hypot(px - gx, py - gy)
        d_min = min(d_min, d_o)
        if d_o < params.r:
            V += 1
        suma_int += math.hypot(cmd[0] - v_op, cmd[1] - w_op)
        if st.v < V_BLOCAT and v_op > V_OP_ACTIV:
            n_blocat += 1

        trace.append({"t": round(t, 4), "x_pre": st_pre.x, "y_pre": st_pre.y,
                      "theta_pre": st_pre.theta, "v_pre": st_pre.v, "x": st.x, "y": st.y, "theta": st.theta,
                      "v": st.v, "omega": st.omega, "v_op": v_op, "omega_op": w_op,
                      "AoI_cmd": aoi, "A_haz": A_haz,
                      "o_hat_x": None if o_hat is None else o_hat[0],
                      "o_hat_y": None if o_hat is None else o_hat[1],
                      "o_true_x": ox, "o_true_y": oy, "h": h, "r_eff": r_eff,
                      "feasible": feasible, "kkt_res": kkt,
                      "u_v": cmd[0], "u_w": cmd[1]})

        if T_G is None and d_g < params.goal_tol:
            T_G = round(t, 4)
            break

    n = len(trace)
    metrics = {"V": V,
               "d_min": None if d_min == float("inf") else round(d_min, 6),
               "J_int": round(suma_int / n, 6) if n else None,
               "T_G": T_G,
               "B": round(n_blocat / float(n), 6) if n else None,
               "n_inf": n_inf,
               "n_pasi": n,
               "n_reactii": op.n_reactii,
               "model": getattr(model, "nume", type(model).__name__)}
    return metrics, trace


def _hash_trace(trace):
    """Amprenta pe campurile numerice, la 9 zecimale: doua rulari cu acelasi seed
    trebuie sa dea acelasi sir, bit cu bit."""
    h = hashlib.sha256()
    for p in trace:
        h.update(("%.9f|%.9f|%.9f|%.9f|%.9f" %
                  (p["t"], p["x"], p["y"], p["theta"], p["v"])).encode())
    return h.hexdigest()


# --- selftest ------------------------------------------------------------
def _selftest(dir_iesire=None):
    import io_core
    P = Params()
    rez = []

    # (a) Unicycle + canal ideal, fara filtru: ajunge la tinta sub 20 s
    m, tr = run_episode(P, models.Unicycle(), channel_core.IdealChannel(P))
    assert tr, "(a) trace gol"
    assert m["T_G"] is not None and m["T_G"] < 20.0, "(a) T_G = %s" % m["T_G"]
    print("  (a) Unicycle + ideal: T_G = %.2f s (< 20), d_min = %.3f m"
          % (m["T_G"], m["d_min"]))
    rez.append(("a", "PASS", "T_G=%.2f" % m["T_G"]))

    # (b) acelasi episod: operatorul NU vede obstacolul, deci taie prin el
    assert m["V"] >= 1, "(b) V = %d; operatorul ar fi ocolit, ceea ce ar anula experimentul" % m["V"]
    print("  (b) V = %d pasi in interiorul razei r = %.1f m (operatorul taie obstacolul)"
          % (m["V"], P.r))
    rez.append(("b", "PASS", "V=%d" % m["V"]))

    # (c) determinism la seed fix
    _, tr2 = run_episode(Params(), models.Unicycle(), channel_core.IdealChannel(P))
    h1, h2 = _hash_trace(tr), _hash_trace(tr2)
    assert h1 == h2, "(c) trace diferit: %s vs %s" % (h1[:12], h2[:12])
    print("  (c) determinism: doua rulari, acelasi sha256 %s" % h1[:16])
    rez.append(("c", "PASS", h1[:16]))

    # (d) SkidSteerAdapter, daca se poate importa din pachetul inghetat
    sk, motiv = models.incearca_skidsteer()
    if sk is None:
        print("  (d) SARIT: %s" % motiv)
        rez.append(("d", "SARIT", motiv))
    else:
        md, _ = run_episode(P, sk, channel_core.IdealChannel(P))
        assert md["T_G"] is not None and md["T_G"] < 25.0, "(d) T_G = %s" % md["T_G"]
        print("  (d) SkidSteer4W: T_G = %.2f s (< 25)" % md["T_G"])
        rez.append(("d", "PASS", "T_G=%.2f" % md["T_G"]))

    # (e) fara filtru, comanda aplicata E cea a operatorului: interventie nula
    assert m["J_int"] == 0.0, "(e) J_int = %s, dar nu exista filtru" % m["J_int"]
    print("  (e) J_int = 0.0 fara filtru")
    rez.append(("e", "PASS", "J_int=0.0"))

    # (f) canal cu intarziere si pierdere: AoI trebuie sa fie strict pozitiv
    ch = channel_core.DelayLossChannel(0.2, 0.05, 0.15, seed=1, T_hold=P.T_hold)
    mf, trf = run_episode(P, models.Unicycle(), ch)
    aoi = [p["AoI_cmd"] for p in trf if p["AoI_cmd"] is not None]
    assert aoi, "(f) niciun AoI inregistrat"
    assert max(aoi) > 0.2, "(f) AoI max = %.4f, asteptat > 0.2" % max(aoi)
    assert min(aoi) > 0, "(f) AoI min = %.4f, asteptat > 0" % min(aoi)
    print("  (f) DelayLoss(0.2, 0.05, 0.15): AoI min = %.4f s, max = %.4f s; T_G = %s "
          "(observatie, nu prag)" % (min(aoi), max(aoi), mf["T_G"]))
    rez.append(("f", "RAPORTAT", "AoI %.3f..%.3f, T_G=%s" % (min(aoi), max(aoi), mf["T_G"])))

    if dir_iesire:
        io_core.scrie(dir_iesire, m, tr, "a_ideal")
        io_core.scrie(dir_iesire, mf, trf, "f_delayloss")
        print("  urme scrise in %s" % dir_iesire)

    print("SELFTEST episode OK (%d cazuri)." % len(rez))
    return 0


if __name__ == "__main__":
    d = None
    if "--outputs" in sys.argv:
        d = sys.argv[sys.argv.index("--outputs") + 1]
    if "--selftest" in sys.argv:
        sys.exit(_selftest(d))
    if "--certify" in sys.argv:
        import cbf_core, certif_core, io_core
        P = Params(); sf = cbf_core.SafetyFilter(P)
        m, tr = run_episode(P, models.Unicycle(), channel_core.IdealChannel(P),
                            safety_filter=cbf_core.ca_safety_filter(sf), react=True)
        c = certif_core.certify(tr, P, lambda t: P.obst, sf.gamma)
        if d:
            io_core.scrie(d, m, tr, "certificat", certificat=c)
        print(json.dumps(c, indent=2, sort_keys=True)); sys.exit(0 if c["verdict"] == "PASS" else 1)
    m, tr = run_episode(Params(), models.Unicycle(), channel_core.IdealChannel(Params()))
    print(json.dumps(m, indent=2, sort_keys=True))
