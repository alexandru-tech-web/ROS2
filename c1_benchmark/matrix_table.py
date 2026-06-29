#!/usr/bin/env python3
"""matrix_table.py -- tabel de comparatie pentru MATRICEA 2x2 (mediu x middleware) a benchmark-ului.

Doua axe ORTOGONALE per punct de date:
  MEDIU (transport fizic): sil | hil_wifi | hil_switch
  MIDDLEWARE (RMW):        cyclonedds | zenoh

GARANTIE METODOLOGICA: comparatia VALIDA e doar IN INTERIORUL aceluiasi mediu (cyclonedds vs zenoh pe
acelasi transport fizic). Celulele din MEDII DIFERITE (ex. zenoh-wifi vs cyclonedds-switch) NU sunt
direct comparabile -- transport fizic diferit. Tabelul marcheaza explicit asta. Sferturile nerulate
apar ca 'nerulat' (NU se inventeaza valori). Axa secundara (acelasi middleware, intre medii) =
'efectul transportului fizic', clar etichetata separat.

Nucleu pur (fara ROS, fara matplotlib); refoloseste env_label + summarize_reps din sil_vs_hil_table.
Ruleaza: python3 matrix_table.py --selftest
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sil_vs_hil_table import env_label, summarize_reps   # noqa: E402

ENVS = ("sil", "hil_wifi", "hil_switch")
MWS = ("cyclonedds", "zenoh")


def matrix_summarize(groups):
    """groups = {(env, middleware): [p95_per_rep]} -> {(env, middleware): summary}. Cheile fara date
    raman absente (= nerulat in tabel). Refoloseste summarize_reps (mean, std, cv, interval, n)."""
    return {key: summarize_reps(vals) for key, vals in groups.items() if vals}


def _cell(summ, key):
    s = summ.get(key)
    if not s or s["n"] == 0:
        return "nerulat"
    return "%.0f ms (N=%d)" % (s["mean"], s["n"])


def format_matrix(summ, envs=ENVS, mws=MWS):
    """Tabelul matricei 2x2 + comparatia VALIDA intra-mediu + efectul transportului fizic + nota de
    non-comparabilitate. Pur (intoarce text). summ = {(env, middleware): summary}."""
    out = []
    out.append("== Matrice 2x2: mediu x middleware (RTT p95 [ms] mediu per repetitie) ==")
    hdr = "%-22s" % "mediu" + "".join("| %-17s" % m for m in mws)
    out.append(hdr)
    out.append("-" * len(hdr))
    for env in envs:
        out.append("%-22s" % env_label(env) + "".join("| %-17s" % _cell(summ, (env, m)) for m in mws))

    out.append("")
    out.append("Comparatie VALIDA (in interiorul aceluiasi mediu -- %s):" % " vs ".join(mws))
    for env in envs:
        a, b = summ.get((env, mws[0])), summ.get((env, mws[1]))
        if a and b and a["n"] and b["n"]:
            d = a["mean"] - b["mean"]
            who = mws[1] if d > 0 else mws[0]
            out.append("  %-22s: %s %.0f vs %s %.0f -> %s mai mic cu %.0f ms"
                       % (env_label(env), mws[0], a["mean"], mws[1], b["mean"], who, abs(d)))
        else:
            out.append("  %-22s: cel putin un middleware nerulat -> comparatie indisponibila"
                       % env_label(env))

    out.append("")
    out.append("Efectul transportului fizic (acelasi middleware, intre medii -- AXA SECUNDARA,")
    out.append("NU comparatie de validitate intre RMW-uri):")
    for m in mws:
        present = [(e, summ[(e, m)]) for e in envs if (e, m) in summ and summ[(e, m)]["n"]]
        if len(present) >= 2:
            parts = ["%s %.0f" % (env_label(e), s["mean"]) for e, s in present]
            out.append("  %-11s: %s" % (m, " | ".join(parts)))
        else:
            out.append("  %-11s: sub 2 medii rulate -> efect indisponibil" % m)

    out.append("")
    out.append("NOTA METODOLOGICA: celulele din MEDII DIFERITE nu sunt direct comparabile (transport")
    out.append("fizic diferit: loopback vs Wi-Fi vs Gigabit). Comparatia valida e DOAR pe verticala")
    out.append("(acelasi mediu, cyclonedds vs zenoh). 'nerulat' = fara date inca, NU valoare inventata.")
    return "\n".join(out)


def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, name
        ok += 1

    # date SINTETICE etichetate (synthetic_for_test) -- matrice PARTIALA (sferturi lipsa intentionat)
    groups = {
        ("sil", "cyclonedds"): [1000, 1050, 980],     # synthetic_for_test
        ("sil", "zenoh"): [560, 600, 520],            # synthetic_for_test
        ("hil_wifi", "cyclonedds"): [2500, 2600],     # synthetic_for_test
        # ("hil_wifi", "zenoh") LIPSA -> nerulat
        # hil_switch ambele LIPSA -> nerulat
    }
    summ = matrix_summarize(groups)
    ck("3 celule prezente (restul nerulate)", len(summ) == 3)
    txt = format_matrix(summ)
    ck("aliniere: cele 3 medii in tabel", all(env_label(e) in txt for e in ENVS))
    ck("middleware in antet", all(m in txt for m in MWS))
    ck("sfert lipsa -> 'nerulat'", "nerulat" in txt)
    ck("nota de non-comparabilitate intre medii prezenta", "nu sunt direct comparabile" in txt)
    ck("comparatie VALIDA computata pe SIL (ambele rulate)", "mai mic cu" in txt)
    ck("comparatie indisponibila unde lipseste un middleware (hil_wifi/zenoh)", "indisponibila" in txt)
    ck("axa secundara 'efectul transportului fizic' prezenta + handle date insuficiente",
       "Efectul transportului fizic" in txt and "efect indisponibil" in txt)
    # nu se inventeaza valori: nicio celula lipsa nu primeste numar
    ck("NU inventeaza valori pt celule lipsa", "hil_switch" not in [k[0] for k in summ])
    print("TOATE VERIFICARILE matrix_table AU TRECUT: %d verificari." % ok)


def main():
    ap = argparse.ArgumentParser(description="Tabel matrice 2x2 (mediu x middleware). Vezi HIL_RUNBOOK.md.")
    ap.add_argument("--selftest", action="store_true",
                    help="verifica structura tabelului pe date SINTETICE etichetate")
    a = ap.parse_args()
    if not a.selftest:
        print("Datele matricei 2x2 nu exista inca complet (HIL in curs). Ruleaza cu --selftest")
        print("pentru a verifica structura tabelului pe date sintetice etichetate.")
        return
    _selftest()


if __name__ == "__main__":
    main()
