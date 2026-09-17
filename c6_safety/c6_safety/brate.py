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
        def marja(ctx, p):
            a = ctx.get("A_haz")
            return p.v_o_max * (a if a is not None else p.AoI_max)   # fara pachet: presupunem cel mai rau
        # CBF variabil in timp (M0 sec. 5): marja creste cu v_o*dt intre pachete
        return cbf_core.ca_safety_filter(sf, marja_fn=marja, dmarja_dt=params.v_o_max), sf
    if brat == "A3":
        r_fix = params.r + rover_dyn.d_fr(params.v_max, params.a_max) + params.v_o_max * params.AoI_max
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
    tab = {}          # (brat, seed) -> (m, c)
    urme = {}

    print("  scenariu: pericol %s -> y=%.1f, v_o=%.1f m/s, f_haz=%.0f Hz, canal DelayLoss(0.2, 0.05, 0.15)"
          % (P.hazard_start, P.hazard_end_y, P.v_o_max, P.f_haz))
    for brat in BRATE:
        for s in SEEDS:
            m, tr, c = ruleaza_brat(brat, P, s)
            tab[(brat, s)] = (m, c)
            urme[(brat, s)] = tr
    print("  %-4s %-5s %s" % ("brat", "seed", "rezultat"))
    for brat in BRATE:
        for s in SEEDS:
            m, c = tab[(brat, s)]
            print("  %-4s %-5d %s" % (brat, s, _rand(m, c)))

    # (a) A1 esueaza cu informatie veche in >= 1 seed (raportat, nu prag)
    n_a1 = sum(1 for s in SEEDS if tab[("A1", s)][0]["V"] >= 1)
    rez.append(("a", "RAPORTAT", "A1: V>=1 in %d/5 seed-uri (asteptat >= 1; daca 0, scenariul e al lui Alexandru)" % n_a1))

    # (b) A2: V = 0 si certificat PASS pe toate 5 -- OBLIGATORIU
    ok_b = all(tab[("A2", s)][0]["V"] == 0 and tab[("A2", s)][1]["verdict"] == "PASS" for s in SEEDS)
    rez.append(("b", "PASS" if ok_b else "FAIL",
                "A2: V = %s; certificat = %s" % ([tab[("A2", s)][0]["V"] for s in SEEDS],
                                                 [tab[("A2", s)][1]["verdict"] for s in SEEDS])))

    # (c) A3: V = 0 si mediana J_int(A3) >= mediana J_int(A2)
    j2 = statistics.median(tab[("A2", s)][0]["J_int"] for s in SEEDS)
    j3 = statistics.median(tab[("A3", s)][0]["J_int"] for s in SEEDS)
    ok_c = all(tab[("A3", s)][0]["V"] == 0 for s in SEEDS) and j3 >= j2
    rez.append(("c", "RAPORTAT", "A3: V = %s; mediana J_int A3=%.4f %s A2=%.4f"
                % ([tab[("A3", s)][0]["V"] for s in SEEDS], j3, ">=" if j3 >= j2 else "<", j2)))

    # (d) regresie: v_o = 0, pericol FIX la params.obst, canal ideal, A2 == S2.1(a) la 1e-9
    hz0 = episode.Hazard(P, v_o=0.0, start=P.obst)
    m_ref, _, _ = ruleaza_brat("A1", P, 1, canal=channel_core.IdealChannel(P), hazard=hz0)
    sf = cbf_core.SafetyFilter(P)
    m_s21, _ = episode.run_episode(P, models.Unicycle(), channel_core.IdealChannel(P),
                                   safety_filter=cbf_core.ca_safety_filter(sf), react=False)
    dif = max(abs(m_ref[k] - m_s21[k]) for k in ("d_min", "J_int"))
    dif_t = abs((m_ref["T_G"] or 0) - (m_s21["T_G"] or 0))
    ok_d = dif <= 1e-9 and dif_t <= 1e-9
    rez.append(("d", "PASS" if ok_d else "FAIL",
                "v_o=0, pericol fix la obst: T_G %s vs %s, d_min %.6f vs %.6f, J_int %.6f vs %.6f (dif max %.1e)"
                % (m_ref["T_G"], m_s21["T_G"], m_ref["d_min"], m_s21["d_min"],
                   m_ref["J_int"], m_s21["J_int"], max(dif, dif_t))))

    # (e) A0: V >= 1 pe >= 4 seed-uri (scenariul e greu)
    n_a0 = sum(1 for s in SEEDS if tab[("A0", s)][0]["V"] >= 1)
    rez.append(("e", "RAPORTAT", "A0: V>=1 in %d/5 seed-uri (asteptat >= 4)" % n_a0))

    # (f) react=True la DelayLoss, A2: n_reactii >= 1 si T_G < T_G(react=False)
    mf, _, cf = ruleaza_brat("A2", P, 1, react=True)
    m_nr = tab[("A2", 1)][0]
    ok_f = (mf["n_reactii"] >= 1 and mf["T_G"] is not None and
            (m_nr["T_G"] is None or mf["T_G"] < m_nr["T_G"]))
    rez.append(("f", "PASS" if ok_f else "FAIL",
                "A2 react=True seed 1: n_reactii=%d T_G=%s V=%d cert=%s | react=False: T_G=%s"
                % (mf["n_reactii"], mf["T_G"], mf["V"], cf["verdict"], m_nr["T_G"])))

    # (g') plant cu lag 0.2, filtru clamp, A2, react=False: V raportat
    mg, _, cg = ruleaza_brat("A2", P, 1, tau_act=0.2)
    rez.append(("g'", "RAPORTAT", "A2 pe plant lag 0.2, seed 1: V=%d d_min=%.3f T_G=%s cert=%s"
                % (mg["V"], mg["d_min"], mg["T_G"], cg["verdict"])))

    print()
    for k, v, cif in rez:
        print("  (%s) %-8s %s" % (k, v, cif))
    if dir_iesire:
        import io_core
        for (brat, s), tr in urme.items():
            m, c = tab[(brat, s)]
            io_core.scrie(dir_iesire, m, tr, "s2b_%s_seed%d" % (brat, s), certificat=c)
        print("  urme + certificate scrise in %s (%d rulari)" % (dir_iesire, len(urme)))
    picate = [k for k, v, _ in rez if v == "FAIL" and k in ("b", "d", "f")]
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
