#!/usr/bin/env python3
"""certif_core.py -- certificatul de rulare: dovada PRIN EXECUTIE ca sistemul a
urmat functia matematica. Nu verifica "e sigur", verifica "a facut exact ce
spune nota M0 ca trebuie sa faca", pas cu pas, pe urma inregistrata.

Patru verificari, per pas k (M0 sec. 6):
  (i)   siguranta REALA: h_true_k = ||p_c,k - o_true(t_k)|| - r >= 0, pe
        obstacolul ADEVARAT, nu pe cel estimat -- singura care conteaza fizic;
  (ii)  DT-CBF pe h_A (h-ul filtrului): h_A,k+1 - (1 - gamma) h_A,k >= -eps;
  (iii) optimalitate: kkt_res <= eps, sau u pe frontiera fezabila;
  (iv)  consistenta dinamicii: x_{k+1} == F(x_k, u_k), re-simulat, |diff| <= 1e-9.
        Daca (iv) pica, nimic din (i)-(iii) nu mai vorbeste despre plantul real.

Iesire: certificate.json {pasi, incalcari_i..iv, min_h_true, min_rezid_cbf,
verdict PASS/FAIL, eps}. Verdictul e PASS doar cu ZERO incalcari pe toate patru.

Selftestul e construit pe CONTROALE NEGATIVE: un certificat care nu prinde o
abatere injectata nu certifica nimic. Rulare: python3 certif_core.py --selftest
"""
import json
import math
import os
import sys

_AICI = os.path.dirname(os.path.abspath(__file__))
if _AICI not in sys.path:
    sys.path.insert(0, _AICI)
import rover_dyn                                             # noqa: E402

EPS = 1e-6
EPS_DIN = 1e-9


def certify(trace, params, o_true, gamma, eps=EPS):
    """o_true: callable t -> (ox, oy). gamma: cel folosit de filtru."""
    n = len(trace)
    inc = {"i": 0, "ii": 0, "iii": 0, "iv": 0}
    min_h_true = float("inf")
    min_rez = float("inf")
    for k, q in enumerate(trace):
        # (i) pe obstacolul adevarat, la timpul pasului
        ox, oy = o_true(q["t"])
        cx = q["x"] + params.l * math.cos(q["theta"])
        cy = q["y"] + params.l * math.sin(q["theta"])
        h_true = math.hypot(cx - ox, cy - oy) - params.r
        min_h_true = min(min_h_true, h_true)
        if h_true < 0:
            inc["i"] += 1

        # (ii) DT-CBF pe h-ul filtrului, intre pasi consecutivi
        if k + 1 < n and q.get("h") is not None and trace[k + 1].get("h") is not None:
            rez = trace[k + 1]["h"] - (1.0 - gamma) * q["h"]
            min_rez = min(min_rez, rez)
            if rez < -eps:
                inc["ii"] += 1

        # (iii) optimalitate: reziduu KKT mic, sau comanda pe o frontiera a cutiei
        if q.get("feasible") is not None:
            kkt = q.get("kkt_res")
            pe_frontiera = (abs(abs(q["u_v"]) - params.v_max) < 1e-9
                            or abs(abs(q["u_w"]) - params.omega_max) < 1e-9
                            or abs(abs(q["u_v"] - q["v_pre"]) - params.a_max * params.dt) < 1e-9)
            if not q["feasible"]:
                pass                         # infezabil -> (0,0), nu e problema de KKT
            elif not ((kkt is not None and kkt <= eps) or pe_frontiera):
                inc["iii"] += 1

        # (iv) re-simulare pe F, din starea DINAINTE de pas
        pre = rover_dyn.Stare(x=q["x_pre"], y=q["y_pre"], theta=q["theta_pre"], v=q["v_pre"])
        st = rover_dyn.step(pre, (q["u_v"], q["u_w"]), params.dt)
        d = max(abs(st.x - q["x"]), abs(st.y - q["y"]), abs(st.theta - q["theta"]),
                abs(st.v - q["v"]))
        if d > EPS_DIN:
            inc["iv"] += 1

    verdict = "PASS" if all(v == 0 for v in inc.values()) else "FAIL"
    return {"pasi": n, "incalcari_i": inc["i"], "incalcari_ii": inc["ii"],
            "incalcari_iii": inc["iii"], "incalcari_iv": inc["iv"],
            "min_h_true": None if min_h_true == float("inf") else round(min_h_true, 6),
            "min_rezid_cbf": None if min_rez == float("inf") else round(min_rez, 9),
            "verdict": verdict, "eps": eps, "eps_dinamica": EPS_DIN, "gamma": gamma}


def scrie(cert, dir_iesire, eticheta="episod"):
    os.makedirs(dir_iesire, exist_ok=True)
    p = os.path.join(dir_iesire, "%s_certificate.json" % eticheta)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cert, f, indent=2, sort_keys=True)
        f.write("\n")
    return p


# --- selftest ------------------------------------------------------------
def _selftest():
    from c6_params import Params
    import cbf_core
    import channel_core
    import episode
    import models
    P = Params()
    o_fix = lambda t: P.obst                                 # noqa: E731
    G = cbf_core.GAMMA_IMPLICIT
    rez = []

    # (a) rularea S2.1(a): certificat PASS, zero incalcari
    sf = cbf_core.SafetyFilter(P, G)
    m, tr = episode.run_episode(P, models.Unicycle(), channel_core.IdealChannel(P),
                                safety_filter=cbf_core.ca_safety_filter(sf), react=True)
    c = certify(tr, P, o_fix, G)
    ok = c["verdict"] == "PASS"
    rez.append(("a", "PASS" if ok else "FAIL",
                "verdict=%s i=%d ii=%d iii=%d iv=%d min_h_true=%.4f min_rezid=%.3e"
                % (c["verdict"], c["incalcari_i"], c["incalcari_ii"], c["incalcari_iii"],
                   c["incalcari_iv"], c["min_h_true"], c["min_rezid_cbf"])))
    cert_a = c

    # (b) INJECTIE: filtrul e ocolit (u = u_op) pe 20 de pasi, in zona obstacolului.
    #     Se RE-SIMULEAZA, ca urma sa fie una reala; certificatul trebuie sa prinda
    #     abaterea la (ii). Operatorul e cel paralizat, ca sa existe ce prinde.
    sf2 = cbf_core.SafetyFilter(P, G)
    baza = cbf_core.ca_safety_filter(sf2)
    contor = {"k": 0}

    def sabotat(st, cmd, params):
        contor["k"] += 1
        if 70 <= contor["k"] < 90:
            u, info, inf = baza(st, cmd, params)
            return cmd, info, inf                            # comanda operatorului, nu a filtrului
        return baza(st, cmd, params)
    _, trb = episode.run_episode(P, models.Unicycle(), channel_core.IdealChannel(P),
                                 safety_filter=sabotat, react=False)
    cb = certify(trb, P, o_fix, G)
    ok = cb["verdict"] == "FAIL" and cb["incalcari_ii"] > 0
    rez.append(("b", "PASS" if ok else "FAIL",
                "injectie u=u_op pe 20 pasi -> verdict=%s ii=%d (i=%d)"
                % (cb["verdict"], cb["incalcari_ii"], cb["incalcari_i"])))

    # (c) INJECTIE: x_{k+1} perturbat cu 1e-3 pe un pas -> (iv) > 0
    trc = [dict(q) for q in tr]
    trc[50]["x"] += 1e-3
    cc = certify(trc, P, o_fix, G)
    ok = cc["incalcari_iv"] > 0
    rez.append(("c", "PASS" if ok else "FAIL",
                "x perturbat cu 1e-3 la pasul 50 -> iv=%d verdict=%s" % (cc["incalcari_iv"], cc["verdict"])))

    # (d) fara filtru (A0): incalcari_i == V din episode
    m0, tr0 = episode.run_episode(P, models.Unicycle(), channel_core.IdealChannel(P), react=False)
    c0 = certify(tr0, P, o_fix, G)
    ok = c0["incalcari_i"] == m0["V"]
    rez.append(("d", "PASS" if ok else "FAIL",
                "A0: incalcari_i=%d, V din episode=%d" % (c0["incalcari_i"], m0["V"])))

    for k_, v_, cif in rez:
        print("  (%s) %-5s %s" % (k_, v_, cif))
    print("  certificat S2.1(a): %s" % json.dumps(cert_a, sort_keys=True))
    picate = [k_ for k_, v_, _ in rez if v_ == "FAIL"]
    if picate:
        print("SELFTEST certif_core: FAIL %s" % picate)
        return 1
    print("SELFTEST certif_core OK (4 cazuri, 2 controale negative).")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__.splitlines()[0]); print("Foloseste --selftest.")
