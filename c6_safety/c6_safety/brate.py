#!/usr/bin/env python3
"""brate.py -- cele patru brate S2b, pe pericol MOBIL raportat prin canal. Fara ROS.

  A0  fara filtru: arata ca scenariul e greu (V >= 1)
  A1  filtru pe o_hat, marja_extra = 0: CBF ne-constient de retea (baseline SotA)
  A2  A_ef = min(A_haz, A_max): contributia (Lema 1, M0 sec. 4)
  A3  A_ef = A_max: cel mai rau caz, scump
  toate cu r_eff = r + (v + v_o)^2/(2a) + v_o*A_ef + delta_DT (ERATA 4 viteza de inchidere,
  ERATA 5 rezerva de fezabilitate). H2: pericolul NU urmareste; urmarirea e doar raportata.

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

    ERATA 4: r_eff = r + (v + v_o)^2/(2a) + v_o*A_ef (viteza de inchidere), in TOATE bratele;
    cbf_core.marja_inchidere da partea de peste d_fr(v).
      A1: A_ef = 0            A2: A_ef = min(A, A_max)            A3: A_ef = A_max
    A2 peste A_max -> stare sigura u=(0,0), n_ws. Cu tau_act (doar g'): A_ef += tau_act."""
    if brat == "A0":
        return None, None
    sf = cbf_core.SafetyFilter(params, gamma)
    v_o, a = params.v_o_max, params.a_max
    dmv = v_o / a                                   # d(marja_extra)/dv, ERATA 4

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
        m = cbf_core.marja_inchidere(st.v, v_o, a, A_ef)
        o = ctx.get("o_hat") if ctx.get("o_hat") is not None else p.obst
        u, info = sf.apply(st, cmd, o, m, None, dm, dmv, dt_masurat=ctx.get("dt_masurat"))
        return u, info, (info["feasible"] is False)     # None = stare sigura (n_ws / n_dt), nu infezabil
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
    m["n_dt"] = getattr(sf, "n_dt", 0) if sf else 0      # P0-HIL: pasi peste dt_max_admis
    m["brat"] = brat
    m["seed"] = seed
    g = sf.gamma if sf else cbf_core.GAMMA_IMPLICIT
    # o_true pentru certificat: din urma (valabil si pentru urmarire, unde nu e analitic)
    poz = {q["t"]: (q["o_true_x"], q["o_true_y"]) for q in tr}
    c = certif_core.certify(tr, params, lambda t: poz.get(t, hz.o_true(t)), g)
    c["n_dt"] = m["n_dt"]
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

    def canal(nume, Ps, s):
        return (channel_core.IdealChannel(Ps) if nume == "ideal"
                else channel_core.DelayLossChannel(0.2, 0.05, 0.15, seed=s, T_hold=Ps.T_hold))

    def bloc(scen, brate, canale=("DL",), seeds=SEEDS, react=False, **kw):
        Ps = Params(scenariu=scen, **kw)
        for cn in canale:
            for b in brate:
                for s in seeds:
                    m, tr, c = ruleaza_brat(b, Ps, s, canal=canal(cn, Ps, s), react=react)
                    tab[(scen, cn, b, s)] = (m, c)
                    urme[(scen, cn, b, s)] = tr
        return Ps

    Pt = bloc("traversare", ("A0", "A1", "A2", "A3"), canale=("ideal", "DL"))
    Pu = bloc("urmarire", ("A1", "A2"), canale=("ideal", "DL"))
    print("  ERATA 4+5: r_eff = r + (v + v_o)^2/(2a) + v_o*A_ef + delta_DT; DL = DelayLoss(0.2,0.05,0.15); seed 1-5; react=False")
    print("  delta_DT = (v_o dt + eps_lin)/gamma = %.5f m (rezerva de fezabilitate, Lema 3)" % cbf_core.SafetyFilter(P).delta_DT)
    print("  traversare: t_cross=%.1f -> start %s; urmarire: start %s; v_o=%.1f, f_haz=%.0f Hz"
          % (P.t_cross, tuple(round(x, 2) for x in Pt.hazard_start), Pu.hazard_start, P.v_o_max, P.f_haz))
    print("  %-11s %-5s %-4s %-4s %s" % ("scenariu", "canal", "brat", "seed", "V    d_min  J_int  T_G    n_inf n_ws  v_min  (i)/(ii) cert"))
    for (scen, cn, b, s), (m, c) in sorted(tab.items()):
        vmin = min(q["v"] for q in urme[(scen, cn, b, s)])
        print("  %-11s %-5s %-4s %-4d %-4d %.3f  %.4f %-6s %-5d %-5d %6.3f %d/%d %s"
              % (scen, cn, b, s, m["V"], m["d_min"], m["J_int"], m["T_G"], m["n_inf"], m["n_ws"], vmin,
                 c["incalcari_i"], c["incalcari_ii"], c["verdict"]))

    def V(scen, cn, b): return [tab[(scen, cn, b, s)][0]["V"] for s in SEEDS]
    def C(scen, cn, b, k): return [tab[(scen, cn, b, s)][1][k] for s in SEEDS]
    def N(scen, cn, b, k): return [tab[(scen, cn, b, s)][0][k] for s in SEEDS]
    def zero(L): return all(x == 0 for x in L)

    ok = zero(V("traversare", "ideal", "A2")) and zero(C("traversare", "ideal", "A2", "incalcari_i"))
    rez.append(("j", "PASS" if ok else "FAIL", "A2 IDEAL traversare: V=%s (i)=%s n_inf=%s d_min=%s"
                % (V("traversare", "ideal", "A2"), C("traversare", "ideal", "A2", "incalcari_i"),
                   N("traversare", "ideal", "A2", "n_inf"), [round(x, 3) for x in N("traversare", "ideal", "A2", "d_min")])))
    # ERATA 5 / H2: urmarirea NU mai e in DoD (S3.1: cursa decisa de cm, apoi evadare) -- doar raportata
    rez.append(("k", "RAPORTAT", "urmarire IDEAL: A1 V=%s d_min=%s | A2 V=%s d_min=%s"
                % (V("urmarire", "ideal", "A1"), [round(x, 2) for x in N("urmarire", "ideal", "A1", "d_min")],
                   V("urmarire", "ideal", "A2"), [round(x, 2) for x in N("urmarire", "ideal", "A2", "d_min")])))
    ok = zero(V("traversare", "DL", "A2")) and zero(C("traversare", "DL", "A2", "incalcari_i"))
    rez.append(("b", "PASS" if ok else "FAIL", "A2 DL traversare: V=%s (i)=%s n_inf=%s n_ws=%s"
                % (V("traversare", "DL", "A2"), C("traversare", "DL", "A2", "incalcari_i"),
                   N("traversare", "DL", "A2", "n_inf"), N("traversare", "DL", "A2", "n_ws"))))
    rez.append(("i", "RAPORTAT", "urmarire DL: A1 V=%s d_min=%s | A2 V=%s d_min=%s"
                % (V("urmarire", "DL", "A1"), [round(x, 2) for x in N("urmarire", "DL", "A1", "d_min")],
                   V("urmarire", "DL", "A2"), [round(x, 2) for x in N("urmarire", "DL", "A2", "d_min")])))
    ok = zero(N("traversare", "DL", "A2", "n_inf"))
    rez.append(("m", "PASS" if ok else "FAIL", "A2 DL traversare n_inf=%s (efectul rezervei delta_DT)"
                % N("traversare", "DL", "A2", "n_inf")))
    n_a0 = sum(1 for v in V("traversare", "DL", "A0") if v >= 1)
    rez.append(("a", "PASS" if n_a0 >= 4 else "FAIL", "A0 traversare DL: V>=1 in %d/5, V=%s; ideal V=%s"
                % (n_a0, V("traversare", "DL", "A0"), V("traversare", "ideal", "A0"))))
    rez.append(("c", "RAPORTAT", "A1 traversare: ideal V=%s | DL V=%s" % (V("traversare", "ideal", "A1"), V("traversare", "DL", "A1"))))
    rez.append(("e", "RAPORTAT", "A3 traversare: ideal V=%s n_inf=%s | DL V=%s n_inf=%s (S3.1, fara rezerva: [0,2,77,2,1])"
                % (V("traversare", "ideal", "A3"), N("traversare", "ideal", "A3", "n_inf"),
                   V("traversare", "DL", "A3"), N("traversare", "DL", "A3", "n_inf"))))

    # (d) regresie: v_o = 0 -> (v + 0)^2/(2a) = v^2/(2a), identic cu S2.1(a) pe pericol fix
    hz0 = episode.Hazard(P, v_o=0.0, start=P.obst, scenariu="traversare")
    P0 = Params(v_o_max=0.0)
    m_ref, _, _ = ruleaza_brat("A1", P0, 1, canal=channel_core.IdealChannel(P0), hazard=hz0)
    sf = cbf_core.SafetyFilter(P0)
    m_s21, _ = episode.run_episode(P0, models.Unicycle(), channel_core.IdealChannel(P0),
                                   safety_filter=cbf_core.ca_safety_filter(sf), react=False)
    dif = max(abs(m_ref[k] - m_s21[k]) for k in ("d_min", "J_int"))
    dif_t = abs((m_ref["T_G"] or 0) - (m_s21["T_G"] or 0))
    # cu delta_DT = eps_lin/gamma la v_o=0 (~0.007 m), cifrele S2.1(a) (T_G 44.3, d_min 1.0029,
    # J_int 1.0833) se deplaseaza cu acest offset; ce se cere identic e brate == ca_safety_filter
    rez.append(("d", "PASS" if max(dif, dif_t) <= 1e-9 else "FAIL",
                "v_o=0 pericol fix, brate == ca_safety_filter: dif max %.1e; cu offset delta_DT=%.5f: "
                "T_G %s d_min %.4f J_int %.4f (S2.1: 44.3, 1.0029, 1.0833)"
                % (max(dif, dif_t), sf.delta_DT, m_ref["T_G"], m_ref["d_min"], m_ref["J_int"])))

    nr = [ruleaza_brat("A2", Pt, s, react=True)[0]["n_reactii"] for s in SEEDS]
    n_f = sum(1 for x in nr if x >= 1)
    rez.append(("f", "PASS" if n_f >= 4 else "FAIL", "A2 react=True traversare DL: n_reactii=%s -> %d/5" % (nr, n_f)))
    mg, _, cg = ruleaza_brat("A2", Pu, 1, tau_act=0.2)
    rez.append(("g'", "RAPORTAT", "A2 urmarire DL, plant lag 0.2: V=%d d_min=%.3f n_inf=%d cert=%s" % (mg["V"], mg["d_min"], mg["n_inf"], cg["verdict"])))
    m10, _, _ = ruleaza_brat("A2", Pt, 1, gamma=1.0)
    m03 = tab[("traversare", "DL", "A2", 1)][0]
    rez.append(("h", "RAPORTAT", "A2 traversare DL seed 1: gamma 1.0 n_inf=%d V=%d | 0.3 n_inf=%d V=%d" % (m10["n_inf"], m10["V"], m03["n_inf"], m03["V"])))

    print()
    for k, v, cif in rez:
        print("  (%s) %-8s %s" % (k, v, cif))
    OBLIG = ("j", "b", "m", "a", "d")
    picate = [k for k, v, _ in rez if v == "FAIL" and k in OBLIG]
    for k in picate:
        if k in ("j", "b", "m"):
            scen, cn = {"j": ("traversare", "ideal"), "b": ("traversare", "DL"), "m": ("traversare", "DL")}[k]
            s_p = next((s for s in SEEDS if tab[(scen, cn, "A2", s)][0]["V"] > 0
                        or tab[(scen, cn, "A2", s)][0]["n_inf"] > 0), 1)
            tr = urme[(scen, cn, "A2", s_p)]
            k_inf = next((i for i, q in enumerate(tr) if q["feasible"] is False), len(tr) - 1)
            print("  traiectoria primului seed picat, (%s) %s %s seed %d, in jurul primului pas infezabil k=%d:" % (k, scen, cn, s_p, k_inf))
            print(_traiectorie(tr, P, max(0, k_inf - 30), k_inf + 60, pas=5))
    if dir_iesire:
        import io_core
        for (scen, cn, b, s), tr in urme.items():
            m, c = tab[(scen, cn, b, s)]
            io_core.scrie(dir_iesire, m, tr, "s32_%s_%s_%s_seed%d" % (scen, cn, b, s), certificat=c)
        print("  urme + certificate in %s" % dir_iesire)
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
