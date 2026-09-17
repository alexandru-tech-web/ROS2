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


def filtru_pentru(brat, params, gamma=None):
    """(safety_filter callable sau None, SafetyFilter sau None)."""
    if brat == "A0":
        return None, None
    sf = cbf_core.SafetyFilter(params, gamma)
    if brat == "A1":
        return cbf_core.ca_safety_filter(sf, marja_extra=0.0), sf
    if brat == "A2":
        # ERATA 2: marja PLAFONATA la v_o*A_max; peste A_max -> stare sigura u=(0,0), n_ws
        baza = cbf_core.ca_safety_filter(sf)
        def f(st, cmd, p, ctx=None):
            ctx = ctx or {}
            a = ctx.get("A_haz")
            if a is None or a > p.AoI_max:
                sf.n_ws += 1
                info = {"h": None, "feasible": None, "kkt_res": None, "marja_extra": None, "ws": True}
                return (0.0, 0.0), info, False
            m = p.v_o_max * min(a, p.AoI_max)
            dm = p.v_o_max if a < p.AoI_max else 0.0          # plafonata: nu mai creste
            u, info = sf.apply(st, cmd, ctx["o_hat"], m, None, dm)
            return u, info, (not info["feasible"])
        return f, sf
    if brat == "A3":
        r_fix = params.r + rover_dyn.d_fr(params.v_max, params.a_max) + params.v_o_max * params.AoI_max_A3
        return cbf_core.ca_safety_filter(sf, r_eff_fix=r_fix), sf
    raise ValueError(brat)


def ruleaza_brat(brat, params, seed, canal=None, react=False, tau_act=0.0, hazard=None):
    """(metrics, trace, certificat). canal=None -> DelayLoss(0.2, 0.05, 0.15, seed)."""
    if canal is None:
        canal = channel_core.DelayLossChannel(0.2, 0.05, 0.15, seed=seed, T_hold=params.T_hold)
    hz = hazard if hazard is not None else episode.Hazard(params)
    f, sf = filtru_pentru(brat, params)
    m, tr = episode.run_episode(params, models.Unicycle(tau_act), canal,
                                safety_filter=f, react=react, hazard=hz)
    m["n_inf"] = sf.n_inf if sf else 0
    m["n_ws"] = getattr(sf, "n_ws", 0) if sf else 0
    m["brat"] = brat
    m["seed"] = seed
    gamma = sf.gamma if sf else cbf_core.GAMMA_IMPLICIT
    c = certif_core.certify(tr, params, hz.o_true, gamma)
    return m, tr, c


def _rand(m, c):
    return "V=%-3d d_min=%.3f J_int=%.4f T_G=%-6s B=%.3f n_inf=%d cert=%s" % (
        m["V"], m["d_min"], m["J_int"], m["T_G"], m["B"], m["n_inf"], c["verdict"])


def _selftest(dir_iesire=None):
    P = Params()
    SEEDS = (1, 2, 3, 4, 5)
    rez = []
    tab = {}
    urme = {}

    # pasul 2 (ERATA 2): pe A0 ideal, pericolul si roverul chiar se intalnesc
    m_id, tr_id, _ = ruleaza_brat("A0", P, 1, canal=channel_core.IdealChannel(P))
    print("  scenariu ERATA 2: t_cross=%.1f s -> pericol din %s, v_o=%.1f, f_haz=%.0f Hz"
          % (P.t_cross, tuple(round(x, 2) for x in P.hazard_start), P.v_o_max, P.f_haz))
    print("  intalnire pe A0 ideal: d_min REAL = %.3f %s r = %.1f  (V=%d, T_G=%s)"
          % (m_id["d_min"], "<" if m_id["d_min"] < P.r else ">=", P.r, m_id["V"], m_id["T_G"]))

    for brat in BRATE:
        for s in SEEDS:
            m, tr, c = ruleaza_brat(brat, P, s)
            tab[(brat, s)] = (m, c)
            urme[(brat, s)] = tr
    print("  %-4s %-4s %s" % ("brat", "seed", "V   d_min  J_int  T_G    B     n_inf n_ws  cert(i/ii)"))
    for brat in BRATE:
        for s in SEEDS:
            m, c = tab[(brat, s)]
            print("  %-4s %-4d %-3d %.3f  %.4f %-6s %.3f %-5d %-5d %d/%d %s"
                  % (brat, s, m["V"], m["d_min"], m["J_int"], m["T_G"], m["B"], m["n_inf"],
                     m["n_ws"], c["incalcari_i"], c["incalcari_ii"], c["verdict"]))

    def V(b): return [tab[(b, s)][0]["V"] for s in SEEDS]
    def C(b, k): return [tab[(b, s)][1][k] for s in SEEDS]

    n_a0 = sum(1 for v in V("A0") if v >= 1)
    rez.append(("a", "PASS" if n_a0 >= 4 else "FAIL", "A0: V>=1 in %d/5 (V=%s)" % (n_a0, V("A0"))))

    ok_b = (all(v == 0 for v in V("A2")) and all(x == 0 for x in C("A2", "incalcari_i"))
            and all(x == 0 for x in C("A2", "incalcari_ii")))
    rez.append(("b", "PASS" if ok_b else "FAIL",
                "A2: V=%s; (i)=%s; (ii) pe fezabili=%s; n_inf=%s; n_ws=%s"
                % (V("A2"), C("A2", "incalcari_i"), C("A2", "incalcari_ii"),
                   [tab[("A2", s)][0]["n_inf"] for s in SEEDS], [tab[("A2", s)][0]["n_ws"] for s in SEEDS])))

    rez.append(("c", "RAPORTAT", "A1: V=%s (fara prag la v_o=0.5)" % V("A1")))

    hz0 = episode.Hazard(P, v_o=0.0, start=P.obst)
    m_ref, _, _ = ruleaza_brat("A1", P, 1, canal=channel_core.IdealChannel(P), hazard=hz0)
    sf = cbf_core.SafetyFilter(P)
    m_s21, _ = episode.run_episode(P, models.Unicycle(), channel_core.IdealChannel(P),
                                   safety_filter=cbf_core.ca_safety_filter(sf), react=False)
    dif = max(abs(m_ref[k] - m_s21[k]) for k in ("d_min", "J_int"))
    dif_t = abs((m_ref["T_G"] or 0) - (m_s21["T_G"] or 0))
    rez.append(("d", "PASS" if max(dif, dif_t) <= 1e-9 else "FAIL",
                "v_o=0, pericol fix la obst == S2.1(a): dif max %.1e (T_G %s, d_min %.4f, J_int %.4f)"
                % (max(dif, dif_t), m_ref["T_G"], m_ref["d_min"], m_ref["J_int"])))

    rez.append(("e", "RAPORTAT", "A3: V=%s cert=%s n_inf=%s -- explicat la pasul 1 (dh/dv=0 cu r_eff fix)"
                % (V("A3"), C("A3", "verdict"), [tab[("A3", s)][0]["n_inf"] for s in SEEDS])))

    nr = []
    for s in SEEDS:
        mf, _, _ = ruleaza_brat("A2", P, s, react=True)
        nr.append(mf["n_reactii"])
    n_f = sum(1 for x in nr if x >= 1)
    rez.append(("f", "PASS" if n_f >= 4 else "FAIL", "A2 react=True: n_reactii=%s -> >=1 in %d/5" % (nr, n_f)))

    mg, _, cg = ruleaza_brat("A2", P, 1, tau_act=0.2)
    rez.append(("g'", "RAPORTAT", "A2 pe plant lag 0.2, seed 1: V=%d d_min=%.3f n_inf=%d cert=%s"
                % (mg["V"], mg["d_min"], mg["n_inf"], cg["verdict"])))

    m10, _, _ = _ruleaza_gamma(P, 1, 1.0)
    m03 = tab[("A2", 1)][0]
    rez.append(("h", "RAPORTAT", "A2 seed 1: gamma=1.0 n_inf=%d V=%d J_int=%.4f | gamma=0.3 n_inf=%d V=%d J_int=%.4f"
                % (m10["n_inf"], m10["V"], m10["J_int"], m03["n_inf"], m03["V"], m03["J_int"])))

    # 6. sweep mic de sanatate
    print("\n  sweep v_o (A1, A2; seed 1-3): V per seed")
    print("  %-6s %-14s %s" % ("v_o", "A1", "A2"))
    for vo in (1.0, 1.5):
        Pv = Params(v_o_max=vo)
        r1 = [ruleaza_brat("A1", Pv, s)[0]["V"] for s in (1, 2, 3)]
        r2 = [ruleaza_brat("A2", Pv, s)[0]["V"] for s in (1, 2, 3)]
        print("  %-6.1f %-14s %s" % (vo, r1, r2))

    print()
    for k, v, cif in rez:
        print("  (%s) %-8s %s" % (k, v, cif))
    if dir_iesire:
        import io_core
        for (brat, s), tr in urme.items():
            m, c = tab[(brat, s)]
            io_core.scrie(dir_iesire, m, tr, "s2b1_%s_seed%d" % (brat, s), certificat=c)
        print("  urme + certificate in %s (%d rulari)" % (dir_iesire, len(urme)))
    picate = [k for k, v, _ in rez if v == "FAIL" and k in ("a", "b", "d")]
    if picate:
        print("SELFTEST brate: FAIL pe obligatorii %s" % picate)
        return 1
    print("SELFTEST brate OK.")
    return 0


def _ruleaza_gamma(params, seed, gamma):
    canal = channel_core.DelayLossChannel(0.2, 0.05, 0.15, seed=seed, T_hold=params.T_hold)
    hz = episode.Hazard(params)
    sf = cbf_core.SafetyFilter(params, gamma)
    f, _ = filtru_pentru("A2", params, gamma)
    # filtru_pentru creeaza propriul sf; refolosim structura dar cu gamma dat
    sf2 = cbf_core.SafetyFilter(params, gamma)
    def f2(st, cmd, p, ctx=None):
        ctx = ctx or {}
        a = ctx.get("A_haz")
        if a is None or a > p.AoI_max:
            sf2.n_ws += 1
            return (0.0, 0.0), {"h": None, "feasible": None, "kkt_res": None, "marja_extra": None}, False
        u, info = sf2.apply(st, cmd, ctx["o_hat"], p.v_o_max * min(a, p.AoI_max), None,
                            p.v_o_max if a < p.AoI_max else 0.0)
        return u, info, (not info["feasible"])
    m, tr = episode.run_episode(params, models.Unicycle(), canal, safety_filter=f2, hazard=hz)
    m["n_inf"] = sf2.n_inf
    return m, tr, sf2


if __name__ == "__main__":
    d = sys.argv[sys.argv.index("--outputs") + 1] if "--outputs" in sys.argv else None
    if "--selftest" in sys.argv:
        sys.exit(_selftest(d))
    print(__doc__.splitlines()[0]); print("Foloseste --selftest.")
