#!/usr/bin/env python3
"""test_v2a_evacuare.py -- V7-V9b: frana de evacuare (DECIZII D7, V2a). SCRIS INAINTE DE IMPLEMENTARE, 21.09.2026.
Serii sintetice de alpha (viabilitate), fara ROS, fara retea. Pragurile de trecere sunt cele din specificatie si NU se ating:
  V7  evacuare asimetrica: alpha_activ 1.0 -> 0.0 liniar in 10 s, celalalt 1.0  -> exact 1 comutare, motiv 'evacuare', t <= 11 s, fara dwell
  V8  moarte simultana:    ambele 1.0 -> 0.0 in 10 s                           -> 0 comutari, nicio_cale_viabila=True in <= 11 s
  V9  oscilatie activ:     alpha_activ intre 0.05 si 0.20 (perioada 4 s), 60 s; celalalt 1.0 -> <= 2 comutari (1 evacuare + <= 1 intoarcere cu dwell complet)
  V9b oscilatie celalalt:  alpha_activ 1.0; celalalt 0.40-0.60 in jurul prag_sus, 60 s        -> 0 comutari
Parametri: prag_jos = 0.10 (LIVRARE_MINIMA_PCT), prag_sus = 0.50 (PROVIZORIU, DECIZII), fereastra 50 mostre la 5 Hz (durata 10 s),
dwell = DWELL_MIN_S (8.55 s). Tabela: sintetica, o celula (0,1) -> cyclonedds marja 0 (nu cere nimic; ca la ideal). Pas de decizie: 20 ms (50 Hz).
"""
import math
import os
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AICI), "c3_gateway", "core"))
from estimator import Estimare                                      # noqa: E402
from policy import Politica                                         # noqa: E402
import switching                                                    # noqa: E402
from switching import Comutator, Viabilitate, DWELL_MIN_S           # noqa: E402

FEREASTRA, HZ_VIAB, PAS = 50, 5.0, 0.02
PRAG_JOS, PRAG_SUS = switching.LIVRARE_MINIMA_PCT / 100.0, 0.50
EST = Estimare(0.0, 1.0, 0.001, 1000, 50, False)                    # canal curat: tabela nu vrea nimic
POL = Politica({"schema": "c3_policy_table/1", "default_transport": "cyclonedds", "default_motiv": "sintetic",
                "celule": [{"L": 0.0, "B": 1.0, "payload": 4096, "transport": "cyclonedds", "marja": 0.0, "covered": True, "sursa": "t.md"}]})


def viab(alpha):
    return Viabilitate(FEREASTRA, int(round(alpha * FEREASTRA)))


def comutator(start="zenoh", **kw):
    """**kw (B2, 22.09): dwell_min_s / prag_plecare / prag_intoarcere, pentru baleiajul pre-inregistrat sec. 8b.
    Fara kw -> exact parametrii pre-inregistrati ai V2a (dwell 8.55 s, 12/5 pp); verdictele V7-V9c nu se schimba."""
    return Comutator(POL, 4096, transport_initial=start, prag_jos_alpha=PRAG_JOS, prag_sus_alpha=PRAG_SUS,
                     durata_fereastra_s=FEREASTRA / HZ_VIAB, **kw)


def ruleaza(com, alpha_fn, durata, t0=100.0):
    """alpha_fn(t) -> {transport: alpha}. Intoarce lista evenimentelor (t, de_la, la, motiv) si primul t cu nicio_cale_viabila."""
    ev, t_niciuna = [], None
    n = int(durata / PAS)
    for k in range(n + 1):
        t = k * PAS
        al = alpha_fn(t)
        inainte = com.transport
        tr, motiv = com.decide(EST, t0 + t, {c: viab(a) for c, a in al.items()})
        if tr != inainte:
            ev.append((round(t, 3), inainte, tr, motiv))
        if t_niciuna is None and com.stare().get("nicio_cale_viabila"):
            t_niciuna = round(t, 3)
    return ev, t_niciuna


def cadere(t, t_start, durata=10.0):
    return max(0.0, min(1.0, 1.0 - (t - t_start) / durata)) if t >= t_start else 1.0


def v7():
    com = comutator("zenoh")
    ev, _ = ruleaza(com, lambda t: {"zenoh": cadere(t, 5.0), "cyclonedds": 1.0}, 40.0)
    ok = (len(ev) == 1 and ev[0][1] == "zenoh" and ev[0][2] == "cyclonedds" and "evacuare" in ev[0][3] and (ev[0][0] - 5.0) <= 11.0)
    fara_dwell = ok and com.n_comutari == 1
    return ok and fara_dwell, "V7 evacuare asimetrica: %d comutari %s; t = %.2f s de la inceputul caderii (<= 11)" % (
        len(ev), [(e[0], e[1], e[2]) for e in ev], (ev[0][0] - 5.0) if ev else float("nan"))


def v7_dwell():
    """E1 spune FARA dwell: o evacuare imediat dupa o comutare din tabela trebuie sa treaca."""
    com = comutator("zenoh")
    com.t_ultima_comutare = 100.0 + 4.9                             # 'abia am comutat' (0.1 s inainte de cadere)
    ev, _ = ruleaza(com, lambda t: {"zenoh": cadere(t, 5.0), "cyclonedds": 1.0}, 30.0)
    ok = len(ev) == 1 and "evacuare" in ev[0][3] and (ev[0][0] - 5.0) <= 11.0
    return ok, "V7' evacuare fara dwell (t_ultima_comutare recent): %d comutari, t = %s" % (len(ev), (ev[0][0] - 5.0) if ev else None)


def v8():
    com = comutator("zenoh")
    ev, t_n = ruleaza(com, lambda t: {"zenoh": cadere(t, 5.0), "cyclonedds": cadere(t, 5.0)}, 40.0)
    st = com.stare()
    ok = (len(ev) == 0 and t_n is not None and (t_n - 5.0) <= 11.0 and st["nicio_cale_viabila"] is True and st["alpha_activ"] == 0.0)
    return ok, "V8 moarte simultana: %d comutari; nicio_cale_viabila la t = %s s de la cadere (<= 11); alpha_activ = %s" % (
        len(ev), (t_n - 5.0) if t_n is not None else None, st.get("alpha_activ"))


def v9_evenimente(**kw):
    """B2: seria V9 (60 s) cu parametrii dati -> (comutator, evenimente). Metrica baleiajului e len(evenimente).
    v9() e verdictul pre-inregistrat citit peste aceeasi serie; seria NU se schimba intre baleiaje."""
    com = comutator("zenoh", **kw)
    osc = lambda t: 0.125 + 0.075 * math.sin(2 * math.pi * t / 4.0)          # noqa: E731  intre 0.05 si 0.20, perioada 4 s
    ev, _ = ruleaza(com, lambda t: {"zenoh": osc(t), "cyclonedds": 1.0}, 60.0)
    return com, ev


def v9(**kw):
    com, ev = v9_evenimente(**kw)
    intoarceri = [e for e in ev if "intoarcere" in e[3]]
    ok = len(ev) <= 2 and len([e for e in ev if "evacuare" in e[3]]) == 1 and len(intoarceri) <= 1
    if intoarceri:
        ok = ok and (intoarceri[0][0] - ev[0][0]) >= com.dwell_min_s
    return ok, "V9 oscilatie activ: %d comutari in 60 s %s" % (len(ev), [(e[0], e[1], e[2], e[3][:10]) for e in ev])


def v9b():
    com = comutator("zenoh")
    osc = lambda t: 0.50 + 0.10 * math.sin(2 * math.pi * t / 4.0)           # noqa: E731  0.40-0.60 in jurul prag_sus
    ev, _ = ruleaza(com, lambda t: {"zenoh": 1.0, "cyclonedds": osc(t)}, 60.0)
    return len(ev) == 0, "V9b oscilatie celalalt: %d comutari (asteptat 0: nu evacuezi de pe o cale buna)" % len(ev)


def v9c():
    """E2: tabela vrea INAPOI pe calea evacuata (celula sintetica zenoh marja 40 pp); intoarcerea cere dwell complet SI alpha > prag_sus
    pe o fereastra intreaga (10 s). alpha_zenoh: cade la t=5 (evacuare), sta 0.05-0.20 pana la t=30 (tabela vrea zenoh, dar E2 blocheaza),
    apoi 1.0 -> intoarcere la >= max(dwell, fereastra) dupa t=30, deci in [40, 41] s; total exact 2 comutari."""
    pol = Politica({"schema": "c3_policy_table/1", "default_transport": "cyclonedds", "default_motiv": "sintetic",
                    "celule": [{"L": 0.0, "B": 1.0, "payload": 4096, "transport": "zenoh", "marja": 40.0, "covered": True, "sursa": "t.md"}]})
    com = Comutator(pol, 4096, transport_initial="zenoh", prag_jos_alpha=PRAG_JOS, prag_sus_alpha=PRAG_SUS, durata_fereastra_s=FEREASTRA / HZ_VIAB)
    est = Estimare(0.0, 1.0, 0.001, 1000, 50, True)
    osc = lambda t: 0.125 + 0.075 * math.sin(2 * math.pi * t / 4.0)          # noqa: E731

    def alpha(t):
        if t < 5.0:
            return {"zenoh": 1.0, "cyclonedds": 1.0}
        if t < 30.0:
            return {"zenoh": osc(t), "cyclonedds": 1.0}
        return {"zenoh": 1.0, "cyclonedds": 1.0}
    ev, t_n = [], None
    for k in range(int(60.0 / PAS) + 1):
        t = k * PAS
        inainte = com.transport
        tr, motiv = com.decide(est, 100.0 + t, {c: viab(a) for c, a in alpha(t).items()})
        if tr != inainte:
            ev.append((round(t, 3), inainte, tr, motiv))
    ok = (len(ev) == 2 and "evacuare" in ev[0][3] and ev[0][2] == "cyclonedds" and "intoarcere" in ev[1][3] and ev[1][2] == "zenoh"
          and 40.0 <= ev[1][0] <= 41.0 and (ev[1][0] - ev[0][0]) >= DWELL_MIN_S)
    return ok, "V9c intoarcere conditionata (E2): %d comutari %s" % (len(ev), [(e[0], e[1], e[2], e[3][:10]) for e in ev])


def main():
    rez = [v7(), v7_dwell(), v8(), v9(), v9b(), v9c()]
    for ok, txt in rez:
        print("  %s  %s" % ("PASS" if ok else "FAIL", txt))
    if all(ok for ok, _ in rez):
        print("TESTE V2a (V7, V7', V8, V9, V9b, V9c) OK.")
        return 0
    print("TESTE V2a: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
