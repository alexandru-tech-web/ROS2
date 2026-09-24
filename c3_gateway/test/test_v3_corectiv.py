#!/usr/bin/env python3
"""test_v3_corectiv.py -- V13-V17: corectivul pe alpha_Tapp. SCRIS INAINTE DE IMPLEMENTARE, 24.09.2026.

Specificatia e PLAN_C3_ETAPA_A.md sec. 9 (S1-S4). Pragurile de trecere sunt cele de acolo si NU se ating;
daca V13 nu da 5/5 sau daca V14 se declanseaza, testul PICA si se raporteaza -- nu se ajusteaza pragul.

  V13 corectivul prinde tabela importata: REDARE loss_15 (r072, r032, r046, r053, r004) -> ramane pe zenoh 5/5,
      iar livrarea la T_app a politicii redate e egala cu zenoh-only in limita a 2 pp.
  V14 corectivul NU se baga pe diferente fine: REDARE ge_c2 (r014, r017, r031, r050, r054) -> 0 decizii
      'corectiv' in 5/5, si transportul final identic cu cel din evenimente.csv al rularii redate.
  V15 fereastra neumpluta: in primele 10 s (50 de mostre la 5 Hz) nu se ia NICIO decizie corectiva, oricat de
      mare ar fi diferenta aparenta pe fereastra partiala.
  V16 conflict tabela vs corectiv: tabela vrea X, corectivul vede +20 pp spre Y -> castiga Y, si jurnalul are
      pe aceeasi linie verdictul tabelei, al corectivului si campul 'castigator'.
  V17 V1-V9c neschimbate: suita determinista trebuie sa dea iesire IDENTICA BIT CU BIT cu baseline_v1_v9c.txt
      (capturat inainte de implementare), iar V1-V6 (procese reale) acelasi verdict.

Rulare: python3 test/test_v3_corectiv.py [--doar V13,V14] ; cod 0 = toate trec.
DOAR stdlib.
"""
import argparse
import csv
import difflib
import glob
import json
import os
import statistics
import subprocess
import sys

AICI = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(AICI)
sys.path.insert(0, os.path.join(PKG, "c3_gateway", "core"))
from estimator import Estimare                                      # noqa: E402
import switching                                                    # noqa: E402
from switching import Comutator, Viabilitate, DWELL_MIN_S           # noqa: E402

RADACINA = os.path.abspath(os.path.join(PKG, "..", ".."))
CAMPANIE = os.path.join(RADACINA, "DATE", "C3", "repetitie_etapaA_2026-09-22_VALIDARE", "runs")
BASELINE = os.path.join(AICI, "baseline_v1_v9c.txt")

CAI = ("zenoh", "cyclonedds")
START = "zenoh"
T_APP_MS = 250.0
FEREASTRA = 50                       # mostre; la 5 Hz = 10 s
PRAG_CORECTIV_PP = 9.0               # PLAN_C3_ETAPA_A sec. 9 (ERATA 24.09.2026)
EST = Estimare(0.0, 1.0, 0.001, 1000, 50, True)      # estimare STABILA: tabela poate decide

V13_RULARI = ("r072", "r032", "r046", "r053", "r004")
V14_RULARI = ("r014", "r017", "r031", "r050", "r054")


def _ok(cond, mesaj):
    return ("PASS" if cond else "FAIL"), mesaj


class TabelaFixa(object):
    """Stub de politica: intoarce ce a ales tabela REALA a gateway-ului la momentul t, cu marja mare.

    De ce stub si nu Politica reala: in redare, verdictul tabelei e o INTRARE (il citim din evenimente.csv
    al rularii inregistrate), nu ceva de recalculat. Asa se testeaza corectivul si interactiunea lui cu
    tabela, pe verdictele pe care tabela chiar le-a dat atunci.
    """

    class D(object):
        def __init__(self, transport, marja):
            self.transport, self.marja, self.sursa = transport, marja, "redare"

    def __init__(self, alegeri, implicit="cyclonedds"):
        self.alegeri = alegeri
        self.implicit = implicit
        self.t = 0.0

    def la(self, t):
        cur = START
        for te, la in self.alegeri:
            if te <= t:
                cur = la
            else:
                break
        return cur

    def decide(self, L_pct, B, payload):
        return TabelaFixa.D(self.la(self.t), 30.0)


def _mostre(cale):
    """[(t, primit, in_termen)] dintr-un sonda_<cale>.csv."""
    out = []
    with open(cale, newline="", encoding="utf-8") as f:
        for x in csv.DictReader(f):
            primit = x["primit"] == "1"
            rtt = float(x["rtt_ms"]) if x["rtt_ms"] not in ("", "None") else None
            out.append((float(x["t"]), primit, bool(primit and rtt is not None and rtt <= T_APP_MS)))
    return sorted(out)


def _alegeri_tabela(dosar):
    ev = []
    p = os.path.join(dosar, "evenimente.csv")
    if os.path.exists(p):
        with open(p, newline="", encoding="utf-8") as f:
            for x in csv.DictReader(f):
                if x.get("eveniment") == "comutare":
                    ev.append((float(x["t_mono"]), x["la"]))
    return sorted(ev)


def _comutari_inregistrate(dosar):
    ev = _alegeri_tabela(dosar)
    return (ev[-1][1] if ev else START), len(ev)


def redare(dosar, prag_pp=PRAG_CORECTIV_PP):
    """Ruleaza Comutatorul REAL peste sondele inregistrate. Intoarce un dict de rezultat."""
    M = {c: _mostre(os.path.join(dosar, "sonda_%s.csv" % c)) for c in CAI}
    tab = TabelaFixa(_alegeri_tabela(dosar))
    com = Comutator(tab, 4096, transport_initial=START, durata_fereastra_s=FEREASTRA / 5.0,
                    prag_corectiv=prag_pp, t_app_ms=T_APP_MS, fereastra_viab=FEREASTRA)
    # Fereastra de masurare a LIVRARII: de la aplicarea netem incolo. Metrica de referinta
    # (3_livrare_in_termen_pct din summary.json) se calculeaza pe fereastra de DUPA netem
    # (3_n_app_fereastra ~ 2016 mostre = ~40 s la 50 Hz), deci si ponderarea in timp trebuie facuta
    # pe acelasi interval -- altfel se compara un amestec pe toata rularea cu un numar post-netem.
    man = json.load(open(os.path.join(dosar, "manifest_c3.json"), encoding="utf-8"))
    t_netem = (man.get("t_netem_mono") or 0.0) - (man.get("t0_mono") or 0.0)
    fer = {c: [] for c in CAI}
    ts = sorted({t for c in CAI for t, _, _ in M[c]})
    idx = {c: {t: (p, it) for t, p, it in M[c]} for c in CAI}
    n_corectiv = n_tabela = 0
    t_prev, timp = None, {c: 0.0 for c in CAI}
    urme = []
    for t in ts:
        for c in CAI:
            if t in idx[c]:
                fer[c].append(idx[c][t])
                if len(fer[c]) > FEREASTRA:
                    del fer[c][0:len(fer[c]) - FEREASTRA]
        if t_prev is not None and t_prev >= t_netem:
            timp[com.transport] += t - t_prev
        t_prev = t
        viab = {c: Viabilitate(len(fer[c]), sum(1 for p, _ in fer[c] if p),
                               sum(1 for _, it in fer[c] if it)) for c in CAI}
        tab.t = t
        inainte = com.transport
        tr, motiv = com.decide(EST, t, viab)
        if tr != inainte:
            cast = (com.ultima_decizie or {}).get("castigator")
            urme.append((round(t, 2), inainte, tr, cast, motiv))
            if cast == "corectiv":
                n_corectiv += 1
            elif cast == "tabela":
                n_tabela += 1
    tot = sum(timp.values()) or 1.0
    return {"run": os.path.basename(dosar), "final": com.transport, "n_comutari": com.n_comutari,
            "n_corectiv": n_corectiv, "n_tabela": n_tabela,
            "f_zenoh": timp["zenoh"] / tot, "t_netem": round(t_netem, 2), "urme": urme}


def _dosar(tag):
    g = sorted(glob.glob(os.path.join(CAMPANIE, "*-" + tag)))
    return g[0] if g else None


def _livrare_brat(conditie, brat):
    """Mediana lui 3_livrare_in_termen_pct pe rularile single-arm ale unei celule."""
    v = []
    for d in sorted(glob.glob(os.path.join(CAMPANIE, "*"))):
        p = os.path.join(d, "manifest_c3.json")
        s = os.path.join(d, "summary.json")
        if not (os.path.exists(p) and os.path.exists(s)):
            continue
        try:
            m, S = json.load(open(p, encoding="utf-8")), json.load(open(s, encoding="utf-8"))
        except ValueError:
            continue
        if m.get("conditie") == conditie and m.get("brat") == brat:
            x = (S.get("metrici") or {}).get("3_livrare_in_termen_pct")
            if x is not None:
                v.append(float(x))
    return statistics.median(v) if v else None


# ---------------------------------------------------------------- V13
def v13():
    """loss_15: corectivul tine calea pe zenoh 5/5, cu livrare la T_app ca zenoh-only +-2 pp."""
    liv_z, liv_c = _livrare_brat("loss_15", "zenoh-only"), _livrare_brat("loss_15", "cyclonedds-only")
    if liv_z is None or liv_c is None:
        return _ok(False, "lipsesc rularile single-arm loss_15 (zenoh-only / cyclonedds-only)")
    rez, det = [], []
    for tag in V13_RULARI:
        d = _dosar(tag)
        if d is None:
            return _ok(False, "lipseste rularea %s" % tag)
        q = redare(d)
        rez.append(q)
        det.append("%s final=%s corectiv=%d f_zenoh=%.2f" % (tag, q["final"], q["n_corectiv"], q["f_zenoh"]))
    pe_zenoh = sum(1 for q in rez if q["final"] == "zenoh")
    cu_corectiv = sum(1 for q in rez if q["n_corectiv"] >= 1)
    # livrarea politicii redate = amestec ponderat in timp intre cele doua brate single
    liv = [q["f_zenoh"] * liv_z + (1.0 - q["f_zenoh"]) * liv_c for q in rez]
    liv_med = statistics.median(liv)
    ok = (pe_zenoh == 5 and cu_corectiv == 5 and abs(liv_med - liv_z) <= 2.0)
    return _ok(ok, "loss_15: pe zenoh %d/5, cu >=1 decizie corectiva %d/5; livrare redata %.1f%% vs "
                   "zenoh-only %.1f%% (cdds-only %.1f%%), dif %+.1f pp (prag 2.0) | %s"
               % (pe_zenoh, cu_corectiv, liv_med, liv_z, liv_c, liv_med - liv_z, "; ".join(det)))


# ---------------------------------------------------------------- V14
def v14():
    """ge_c2: corectivul NU se declanseaza, si transportul final ramane cel al tabelei."""
    det, n_cor = [], 0
    for tag in V14_RULARI:
        d = _dosar(tag)
        if d is None:
            return _ok(False, "lipseste rularea %s" % tag)
        q = redare(d)
        final_ing, n_ing = _comutari_inregistrate(d)
        n_cor += q["n_corectiv"]
        det.append("%s corectiv=%d final=%s (inregistrat %s, %d comutari)"
                   % (tag, q["n_corectiv"], q["final"], final_ing, n_ing))
        if q["final"] != final_ing:
            return _ok(False, "%s: transport final %s != cel inregistrat %s | %s"
                       % (tag, q["final"], final_ing, "; ".join(det)))
    return _ok(n_cor == 0, "ge_c2: %d decizii corective in 5 rulari (asteptat 0); transport final identic "
                           "cu inregistrarea in 5/5 | %s" % (n_cor, "; ".join(det)))


# ---------------------------------------------------------------- V15
def v15():
    """Fereastra neumpluta: nicio decizie corectiva pana nu sunt 50 de mostre pe AMBELE cai."""
    tab = TabelaFixa([])
    com = Comutator(tab, 4096, transport_initial=START, durata_fereastra_s=FEREASTRA / 5.0,
                    prag_corectiv=PRAG_CORECTIV_PP, t_app_ms=T_APP_MS, fereastra_viab=FEREASTRA)
    corective, n_pasi = [], 0
    for k in range(1, 101):                      # 100 mostre la 5 Hz = 20 s
        t = k * 0.2
        tab.t = t
        n = min(k, FEREASTRA)
        # diferenta MAXIMA: zenoh (activ) 0 %, cyclonedds 100 % -- daca regula ar decide pe fereastra
        # partiala, ar comuta la prima mostra
        viab = {"zenoh": Viabilitate(n, n, 0), "cyclonedds": Viabilitate(n, n, n)}
        inainte = com.transport
        com.decide(EST, t, viab)
        n_pasi += 1
        if com.transport != inainte and (com.ultima_decizie or {}).get("castigator") == "corectiv":
            corective.append(round(t, 2))
    devreme = [t for t in corective if t < FEREASTRA / 5.0]
    ok = (not devreme) and bool(corective)
    return _ok(ok, "%d pasi: decizii corective la %s; niciuna inainte de %.1f s (fereastra plina) -- "
                   "devreme: %s" % (n_pasi, corective[:3], FEREASTRA / 5.0, devreme))


# ---------------------------------------------------------------- V16
def v16():
    """Conflict: tabela vrea X, corectivul vrea Y cu +20 pp -> castiga Y, ambele verdicte in jurnal."""
    tab = TabelaFixa([])                                  # tabela cere mereu START = zenoh
    com = Comutator(tab, 4096, transport_initial=START, durata_fereastra_s=FEREASTRA / 5.0,
                    prag_corectiv=PRAG_CORECTIV_PP, t_app_ms=T_APP_MS, fereastra_viab=FEREASTRA)
    n = FEREASTRA
    viab = {"zenoh": Viabilitate(n, n, int(0.70 * n)), "cyclonedds": Viabilitate(n, n, int(0.90 * n))}
    d = {}
    for k in range(1, 61):                                # pana la PRIMA schimbare de transport
        t = k * 0.2
        tab.t = t
        inainte = com.transport
        com.decide(EST, t, viab)
        if com.transport != inainte:
            d = dict(com.ultima_decizie or {})
            break                                         # V16 judeca DECIZIA DE CONFLICT, nu starea de dupa
    ok = (com.transport == "cyclonedds" and d.get("castigator") == "corectiv"
          and d.get("tabela_voia") is not None and d.get("corectiv_voia") is not None
          and d.get("alpha_tapp") is not None)
    return _ok(ok, "transport=%s castigator=%s tabela_voia=%s corectiv_voia=%s alpha_tapp=%s"
               % (com.transport, d.get("castigator"), d.get("tabela_voia"),
                  d.get("corectiv_voia"), d.get("alpha_tapp")))


# ---------------------------------------------------------------- V17
COMENZI = (("c3_gateway/core/switching.py", "--selftest"), ("c3_gateway/core/policy.py", "--selftest"),
           ("c3_gateway/core/estimator.py", "--selftest"), ("c3_gateway/core/overhead.py", "--selftest"),
           ("c3_gateway/core/canal_ge.py", "--selftest"), ("test/test_c3_core.py",),
           ("test/test_nodes_fara_politica.py",), ("test/test_v2a_evacuare.py",),
           ("test/test_v2b_reordonare.py",), ("test/test_dwell_mediana.py",))


def v17():
    """Suita determinista IDENTICA bit cu bit cu baseline_v1_v9c.txt (capturat inainte de implementare)."""
    if not os.path.exists(BASELINE):
        return _ok(False, "lipseste %s" % BASELINE)
    L = []
    for c in COMENZI:
        L.append("=== %s" % " ".join(c))
        r = subprocess.run(["/usr/bin/python3"] + list(c), cwd=PKG, capture_output=True, text=True)
        L.append((r.stdout + r.stderr).rstrip("\n"))
        L.append("exit=%d" % r.returncode)
    acum = "\n".join(L) + "\n"
    baza = open(BASELINE, encoding="utf-8").read()
    if acum == baza:
        return _ok(True, "%d comenzi, iesire IDENTICA bit cu bit cu baseline_v1_v9c.txt" % len(COMENZI))
    dif = list(difflib.unified_diff(baza.splitlines(), acum.splitlines(), "baseline", "acum", lineterm="", n=1))
    return _ok(False, "DIFERA de baseline (%d linii de diff): %s" % (len(dif), " | ".join(dif[2:10])))


TESTE = (("V13", v13), ("V14", v14), ("V15", v15), ("V16", v16), ("V17", v17))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--doar", help="lista de teste, ex. V13,V14")
    a = ap.parse_args(argv)
    cerute = set(x.strip().upper() for x in a.doar.split(",")) if a.doar else None
    rez = []
    for n, f in TESTE:
        if cerute and n not in cerute:
            continue
        try:
            v, mesaj = f()
        except Exception as e:                            # noqa: BLE001 -- inainte de cod, asta e starea normala
            v, mesaj = "FAIL", "%s: %s" % (type(e).__name__, e)
        rez.append((n, v, mesaj))
        print("  (%s) %-5s %s" % (n, v, mesaj))
    picate = [n for n, v, _ in rez if v != "PASS"]
    print("TEST V3 %s (%d teste%s)" % ("OK" if not picate else "ESUAT: " + ", ".join(picate),
                                       len(rez), "" if not picate else ", %d picate" % len(picate)))
    return 0 if not picate else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
