#!/usr/bin/env python3
"""test_control_ws.py -- controlul pozitiv al STARII SIGURE (A2), offline. SCRIS INAINTE DE NODURI.

De ce exista: in S4 v2 lot A, A2 a dat certificat PASS pe toate cele 60 de rulari -- dar calea lui de stare
sigura NU s-a exercitat niciodata (n_ws = 0 pe tot lotul; A_haz_max a ajuns cel mult 0.977 s, sub AoI_max =
1.0 s, pe o masina mai linistita decat cea a lui v1, unde se declansase in 22 de rulari). Un PASS obtinut
fara ca ramura sa fie atinsa nu spune nimic despre ramura. Controlul de fata o forteaza: raportorul de
pericol tace 1.5 s incepand de la t = 8 s, deci A_haz trece de plafon si A2 TREBUIE sa intre in stare sigura.

Asteptarile, pre-inregistrate (aceleasi ca ale celulei de lot B):
  (c1) n_ws > 0                       -- ramura chiar s-a exercitat
  (c2) V = 0                          -- siguranta nu se pierde in stare sigura
  (c3) certificat PASS                -- (i) si (ii) tin si pe episodul cu pauza
  (c4) u = (0,0) pe toti pasii de stare sigura, si numarul lor >= durata_pauza - AoI_max, la dt
  (c5) CONTROL NEGATIV, TEMPORAL: fara pauza nu exista pasi de stare sigura IN FEREASTRA pauzei, iar cu
       pauza exista. Prima versiune a testului cerea n_ws = 0 fara pauza; masurat, canalul DelayLoss al
       nucleului (15 % pierdere) atinge singur plafonul in cateva rulari (seed 1: n_ws = 5). Asteptarea
       aceea era gresita despre CANAL, nu despre cod, si a fost inlocuita cu una care izoleaza CAUZA in
       timp -- ce conteaza e ca pauza produce starea sigura ACOLO unde tace raportorul.

Rulare: python3 test/test_control_ws.py   (cod 0 = toate trec). DOAR stdlib + .venv_c6.
"""
import math
import os
import sys

_AICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_AICI), "c6_safety"))
import brate                                                     # noqa: E402
import channel_core                                              # noqa: E402
import operator_core                                             # noqa: E402
from c6_params import Params                                     # noqa: E402

T_PAUZA, DURATA = 8.0, 1.5
SEEDS = (1, 2, 3, 4, 5)


def _ruleaza(seed, cu_pauza):
    P = Params(pauza_haz_t=(T_PAUZA if cu_pauza else -1.0),
               pauza_haz_durata=(DURATA if cu_pauza else 0.0))
    canal = channel_core.DelayLossChannel(0.2, 0.05, 0.15, seed=seed, T_hold=P.T_hold)
    return brate.ruleaza_brat("A2", P, seed, canal=canal) + (P,)


def _ok(cond, mesaj):
    return ("PASS" if cond else "FAIL"), mesaj


def c0_predicat():
    """Fereastra de tacere e [t_pauza, t_pauza + durata), si fara pauza raportorul e mereu activ."""
    r = operator_core.raportor_activ
    bun = (r(7.99, 8.0, 1.5) and not r(8.0, 8.0, 1.5) and not r(9.49, 8.0, 1.5)
           and r(9.5, 8.0, 1.5) and r(8.0, -1.0, 0.0) and r(8.0, 8.0, 0.0))
    return _ok(bun, "raportor_activ: [8.0, 9.5) tace; pauza_t<0 sau durata<=0 -> mereu activ")


def c1_c4_cu_pauza():
    """Cu pauza: n_ws > 0, V = 0, certificat PASS, si u = (0,0) pe pasii de stare sigura."""
    det = []
    for s in SEEDS:
        m, tr, c, P = _ruleaza(s, True)
        ws = [q for q in tr if q["r_eff"] is None]          # stare sigura: filtrul nu a rezolvat QP
        u_nenul = [q for q in ws if abs(q["u_v"]) > 1e-12 or abs(q["u_w"]) > 1e-12]
        # cati pasi ar trebui sa fie cel putin: cat timp A_haz depaseste plafonul, adica
        # durata pauzei minus cat dureaza pana varsta urca peste AoI_max
        minim = max(1, int((DURATA - P.AoI_max) / P.dt))
        if m["n_ws"] <= 0:
            return _ok(False, "seed %d: n_ws = 0 -- pauza NU a fortat starea sigura" % s)
        if m["V"] != 0:
            return _ok(False, "seed %d: V = %d in stare sigura (asteptat 0)" % (s, m["V"]))
        if c["verdict"] != "PASS":
            return _ok(False, "seed %d: certificat %s (i)=%d (ii)=%d"
                       % (s, c["verdict"], c["incalcari_i"], c["incalcari_ii"]))
        if u_nenul:
            return _ok(False, "seed %d: %d pasi de stare sigura cu u != (0,0)" % (s, len(u_nenul)))
        if len(ws) < minim:
            return _ok(False, "seed %d: %d pasi de stare sigura, asteptat >= %d" % (s, len(ws), minim))
        det.append("s%d n_ws=%d pasi_u0=%d d_min=%.3f" % (s, m["n_ws"], len(ws), m["d_min"]))
    return _ok(True, "pauza %.1f s la t=%.1f: " % (DURATA, T_PAUZA) + " | ".join(det))


def _ws_in_fereastra(tr, P):
    """Pasii de stare sigura care cad in fereastra pauzei, plus plafonul de varsta care o urmeaza."""
    return [q for q in tr if q["r_eff"] is None
            and T_PAUZA <= q["t"] < T_PAUZA + DURATA + P.AoI_max]


def c5_control_negativ():
    """Pauza e CAUZA: fara ea, zero pasi de stare sigura IN fereastra; cu ea, mai multi."""
    rez = []
    for s in SEEDS:
        m0, tr0, c0, P = _ruleaza(s, False)
        m1, tr1, c1, _ = _ruleaza(s, True)
        in0, in1 = len(_ws_in_fereastra(tr0, P)), len(_ws_in_fereastra(tr1, P))
        if in0 != 0:
            return _ok(False, "CONTROL NEGATIV PICAT: seed %d are %d pasi de stare sigura in fereastra "
                              "FARA pauza (n_ws total %d)" % (s, in0, m0["n_ws"]))
        if in1 <= 0:
            return _ok(False, "seed %d: pauza nu a produs stare sigura in propria fereastra" % s)
        rez.append("s%d in_fereastra %d->%d (n_ws total %d->%d)" % (s, in0, in1, m0["n_ws"], m1["n_ws"]))
    return _ok(True, "fara pauza: 0 pasi de stare sigura in fereastra, cu pauza: >0 -- " + " | ".join(rez))


TESTE = (("c0", c0_predicat), ("c1-c4", c1_c4_cu_pauza), ("c5", c5_control_negativ))


def main():
    rez = []
    for n, f in TESTE:
        try:
            v, mesaj = f()
        except Exception as e:                                   # noqa: BLE001
            v, mesaj = "FAIL", "%s: %s" % (type(e).__name__, e)
        rez.append((n, v, mesaj))
        print("  (%s) %-5s %s" % (n, v, mesaj))
    picate = [n for n, v, _ in rez if v != "PASS"]
    print("TEST CONTROL-WS %s (%d teste%s)"
          % ("OK" if not picate else "ESUAT: " + ", ".join(picate), len(rez),
             "" if not picate else ", %d picate" % len(picate)))
    return 0 if not picate else 1


if __name__ == "__main__":
    sys.exit(main())
