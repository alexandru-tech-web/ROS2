#!/usr/bin/env python3
"""brate.py -- cele patru brate S2b, pe pericol MOBIL raportat prin canal. Fara ROS.

  A0  fara filtru: arata ca scenariul e greu (V >= 1)
  A1  filtru pe o_hat, marja_extra = 0: CBF ne-constient de retea (baseline SotA)
  A2  marja_extra = v_o_max * A_haz: contributia (Lema 1, M0 sec. 4)
  A3  r_eff FIX = r + d_fr(v_max) + v_o_max * AoI_max: cel mai rau caz, scump

V si d_min se calculeaza pe o(t) ADEVARAT (episode.py), certificatul M1 pe fiecare
rulare. Selftestele ruleaza TOATE pe react=False (ERATA v0.2), cu exceptia (f).

Rulare: python3 brate.py --selftest [--outputs DIR]
"""
import hashlib
import json
import os
import statistics
import sys

_AICI = os.path.dirname(os.path.abspath(__file__))
if _AICI not in sys.path:
    sys.path.insert(0, _AICI)
import cbf_core                                              # noqa: E402
import certif_core                                           # noqa: E402
import channel_core                                          # noqa: E402
import episode                                               # noqa: E402
import models                                                # noqa: E402
import rover_dyn                                             # noqa: E402
from c6_params import Params                                 # noqa: E402

BRATE = ("A0", "A1", "A2", "A3")


def filtru_pentru(brat, params, gamma=None, tau_act=0.0):
    """(safety_filter callable sau None, SafetyFilter sau None).

    ERATA 3: marja_extra = v_o * (A_ef + v/a_max), d_fr(v) = v^2/(2a) in TOATE bratele.
      A1: A_ef = 0            A2: A_ef = min(A, A_max)            A3: A_ef = A_max
    A2 peste A_max -> stare sigura u=(0,0), n_ws. Cu tau_act (doar g'): A_ef += tau_act."""
    if brat == "A0":
        return None, None
    sf = cbf_core.SafetyFilter(params, gamma)
    v_o, a = params.v_o_max, params.a_max
    dmv = v_o / a                                   # d(marja)/dv, ERATA 3

    def f(st, cmd, p, ctx=None):
        ctx = ctx or {}
        A = ctx.get("A_haz")
        if brat == "A1":
            A_ef, dm = 0.0, 0.0
        elif brat == "A2":
            if A is None or A > p.AoI_max:
                sf.n_ws += 1
                return (0.0, 0.0), {"h": None, "feasible": None, "kkt_res": None,
                                    "marja_extra": None, "ws": True}, False
            A_ef, dm = min(A, p.AoI_max), (v_o if A < p.AoI_max else 0.0)
        else:                                       # A3
            A_ef, dm = p.AoI_max, 0.0
        A_ef += tau_act
        m = v_o * (A_ef + st.v / a)
        o = ctx.get("o_hat") if ctx.get("o_hat") is not None else p.obst
        u, info = sf.apply(st, cmd, o, m, None, dm, dmv)
        return u, info, (not info["feasible"])
    return f, sf


def ruleaza_brat(brat, params, seed, canal=None, react=False, tau_act=0.0, hazard=None, gamma=None):
    """(metrics, trace, certificat). canal=None -> DelayLoss(0.2, 0.05, 0.15, seed)."""
    if canal is None:
        canal = channel_core.DelayLossChannel(0.2, 0.05, 0.15, seed=seed, T_hold=params.T_hold)
    hz = hazard if hazard is not None else episode.Hazard(params)
    f, sf = filtru_pentru(brat, params, gamma, tau_act)
    m, tr = episode.run_episode(params, models.Unicycle(tau_act), canal,
                                safety_filter=f, react=react, hazard=hz)
    m["n_inf"] = sf.n_inf if sf else 0
    m["n_ws"] = getattr(sf, "n_ws", 0) if sf else 0
    m["brat"] = brat
    m["seed"] = seed
    g = sf.gamma if sf else cbf_core.GAMMA_IMPLICIT
    # o_true pentru certificat: din urma (valabil si pentru urmarire, unde nu e analitic)
    poz = {q["t"]: (q["o_true_x"], q["o_true_y"]) for q in tr}
    c = certif_core.certify(tr, params, lambda t: poz.get(t, hz.o_true(t)), g)
    return m, tr, c


def _rand(m, c):
    return "V=%-3d d_min=%.3f J_int=%.4f T_G=%-6s B=%.3f n_inf=%d cert=%s" % (
        m["V"], m["d_min"], m["J_int"], m["T_G"], m["B"], m["n_inf"], c["verdict"])


def _traiectorie(tr, P, k0, k1, pas=10):
    import math
    L = ["    %5s %6s %6s %6s %6s %6s %6s" % ("t", "x", "v", "y_haz", "h_A", "d_real", "feas")]
    for k in range(k0, min(k1, len(tr)), pas):
        q = tr[k]
        d = math.hypot(q["x"] + P.l * math.cos(q["theta"]) - q["o_true_x"],
                       q["y"] + P.l * math.sin(q["theta"]) - q["o_true_y"])
        L.append("    %5.2f %6.2f %6.3f %6.2f %6s %6.3f %s"
                 % (q["t"], q["x"], q["v"], q["o_true_y"],
                    "-" if q["h"] is None else "%.3f" % q["h"], d, q["feasible"]))
    return "\n".join(L)


def _selftest(dir_iesire=None):
    P = Params()
    SEEDS = (1, 2, 3, 4, 5)
    rez, tab, urme = [], {}, {}

    def bloc(scen, brate, seeds=SEEDS, react=False):
        Ps = Params(scenariu=scen)
        for b in brate:
            for s in seeds:
                m, tr, c = ruleaza_brat(b, Ps, s, react=react)
                tab[(scen, b, s)] = (m, c)
                urme[(scen, b, s)] = tr
        return Ps

    Pt = bloc("traversare", BRATE)
    Pu = bloc("urmarire", ("A1", "A2"))
    m_id, _, _ = ruleaza_brat("A0", Pt, 1, canal=channel_core.IdealChannel(Pt))
    print("  traversare: t_cross=%.1f -> start %s; urmarire: start %s, spre rover; v_o=%.1f, f_haz=%.0f Hz"
          % (P.t_cross, tuple(round(x, 2) for x in Pt.hazard_start), Pu.hazard_start, P.v_o_max, P.f_haz))
    print("  A0 ideal traversare: d_min REAL=%.3f (<r: %s), V=%d" % (m_id["d_min"], m_id["d_min"] < P.r, m_id["V"]))
    print("  %-11s %-4s %-4s %s" % ("scenariu", "brat", "seed", "V   d_min  J_int  T_G    B     n_inf n_ws  (i)/(ii)"))
    for (scen, b, s), (m, c) in sorted(tab.items()):
        print("  %-11s %-4s %-4d %-3d %.3f  %.4f %-6s %.3f %-5d %-5d %d/%d %s"
              % (scen, b, s, m["V"], m["d_min"], m["J_int"], m["T_G"], m["B"], m["n_inf"], m["n_ws"],
                 c["incalcari_i"], c["incalcari_ii"], c["verdict"]))

    def V(scen, b): return [tab[(scen, b, s)][0]["V"] for s in SEEDS]
    def C(scen, b, k): return [tab[(scen, b, s)][1][k] for s in SEEDS]
    def N(scen, b, k): return [tab[(scen, b, s)][0][k] for s in SEEDS]

    n_a0 = sum(1 for v in V("traversare", "A0") if v >= 1)
    rez.append(("a", "PASS" if n_a0 >= 4 else "FAIL", "A0 traversare: V>=1 in %d/5, V=%s" % (n_a0, V("traversare", "A0"))))
    ok_b = (all(v == 0 for v in V("traversare", "A2")) and all(x == 0 for x in C("traversare", "A2", "incalcari_i"))
            and all(x == 0 for x in C("traversare", "A2", "incalcari_ii")))
    rez.append(("b", "PASS" if ok_b else "FAIL", "A2 traversare: V=%s (i)=%s (ii)fez=%s n_inf=%s n_ws=%s"
                % (V("traversare", "A2"), C("traversare", "A2", "incalcari_i"), C("traversare", "A2", "incalcari_ii"),
                   N("traversare", "A2", "n_inf"), N("traversare", "A2", "n_ws"))))
    ok_i = all(v == 0 for v in V("urmarire", "A2")) and all(x == 0 for x in C("urmarire", "A2", "incalcari_i"))
    rez.append(("i", "PASS" if ok_i else "FAIL", "A2 urmarire (corolarul): V=%s (i)=%s n_inf=%s n_ws=%s"
                % (V("urmarire", "A2"), C("urmarire", "A2", "incalcari_i"), N("urmarire", "A2", "n_inf"), N("urmarire", "A2", "n_ws"))))
    rez.append(("c", "RAPORTAT", "A1: traversare V=%s | urmarire V=%s" % (V("traversare", "A1"), V("urmarire", "A1"))))
    rez.append(("e", "RAPORTAT", "A3 traversare: V=%s n_inf=%s (S2b.1: 111-117)" % (V("traversare", "A3"), N("traversare", "A3", "n_inf"))))

    hz0 = episode.Hazard(P, v_o=0.0, start=P.obst, scenariu="traversare")
    P0 = Params(v_o_max=0.0)
    m_ref, _, _ = ruleaza_brat("A1", P0, 1, canal=channel_core.IdealChannel(P0), hazard=hz0)
    sf = cbf_core.SafetyFilter(P0)
    m_s21, _ = episode.run_episode(P0, models.Unicycle(), channel_core.IdealChannel(P0),
                                   safety_filter=cbf_core.ca_safety_filter(sf), react=False)
    dif = max(abs(m_ref[k] - m_s21[k]) for k in ("d_min", "J_int"))
    dif_t = abs((m_ref["T_G"] or 0) - (m_s21["T_G"] or 0))
    rez.append(("d", "PASS" if max(dif, dif_t) <= 1e-9 else "FAIL",
                "v_o=0 pericol fix == S2.1(a): dif max %.1e (T_G %s d_min %.4f J_int %.4f)"
                % (max(dif, dif_t), m_ref["T_G"], m_ref["d_min"], m_ref["J_int"])))

    nr = [ruleaza_brat("A2", Pt, s, react=True)[0]["n_reactii"] for s in SEEDS]
    n_f = sum(1 for x in nr if x >= 1)
    rez.append(("f", "PASS" if n_f >= 4 else "FAIL", "A2 react=True traversare: n_reactii=%s -> %d/5" % (nr, n_f)))
    mg, _, cg = ruleaza_brat("A2", Pu, 1, tau_act=0.2)
    rez.append(("g'", "RAPORTAT", "A2 urmarire, plant lag 0.2: V=%d d_min=%.3f n_inf=%d cert=%s" % (mg["V"], mg["d_min"], mg["n_inf"], cg["verdict"])))
    m10, _, _ = ruleaza_brat("A2", Pt, 1, gamma=1.0)
    m03 = tab[("traversare", "A2", 1)][0]
    rez.append(("h", "RAPORTAT", "A2 traversare seed 1: gamma 1.0 n_inf=%d V=%d | 0.3 n_inf=%d V=%d" % (m10["n_inf"], m10["V"], m03["n_inf"], m03["V"])))

    print("\n  sweep URMARIRE (seed 1-3): V / d_min / n_inf")
    print("  %-5s %-34s %s" % ("v_o", "A1", "A2"))
    for vo in (0.5, 1.0, 1.5):
        Pv = Params(v_o_max=vo, scenariu="urmarire")
        r = {}
        for b in ("A1", "A2"):
            ms = [ruleaza_brat(b, Pv, s)[0] for s in (1, 2, 3)]
            r[b] = "V=%s dmin=%s ninf=%s" % ([m["V"] for m in ms], [round(m["d_min"], 2) for m in ms], [m["n_inf"] for m in ms])
        print("  %-5.1f %-34s %s" % (vo, r["A1"], r["A2"]))

    print()
    for k, v, cif in rez:
        print("  (%s) %-8s %s" % (k, v, cif))
    picate = [k for k, v, _ in rez if v == "FAIL" and k in ("a", "b", "i", "d")]
    for k in picate:
        if k in ("b", "i"):
            scen = "traversare" if k == "b" else "urmarire"
            s_p = next(s for s in SEEDS if tab[(scen, "A2", s)][0]["V"] > 0 or tab[(scen, "A2", s)][1]["incalcari_i"] > 0)
            print("  traiectoria primului seed picat, (%s) %s seed %d:" % (k, scen, s_p))
            print(_traiectorie(urme[(scen, "A2", s_p)], P, 80, 200))
    if dir_iesire:
        import io_core
        for (scen, b, s), tr in urme.items():
            m, c = tab[(scen, b, s)]
            io_core.scrie(dir_iesire, m, tr, "s2b2_%s_%s_seed%d" % (scen, b, s), certificat=c)
        print("  urme + certificate in %s (%d rulari)" % (dir_iesire, len(urme)))
    if picate:
        print("SELFTEST brate: FAIL pe obligatorii %s" % picate)
        return 1
    print("SELFTEST brate OK.")
    return 0


if __name__ == "__main__":
    d = sys.argv[sys.argv.index("--outputs") + 1] if "--outputs" in sys.argv else None
    if "--selftest" in sys.argv:
        sys.exit(_selftest(d))
    print(__doc__.splitlines()[0]); print("Foloseste --selftest.")
