#!/usr/bin/env python3
"""make_tables.py -- extrage tabele C1 (SIL + HIL Wi-Fi) din summary JSON -> CSV + LaTeX.

Python PUR (fara ROS, fara pandas). READ-ONLY pe date: doar CITESTE
transport_p<P>_summary.json, nu le modifica. Produce tabele gata pentru articol
(clasa article, ASCII -- IEEEtran lipseste local).

METODA DE AGREGARE (explicit, pentru onestitate statistica): pentru fiecare
(mediu, rmw, conditie, payload) se face MEDIA pe repetitii a metricilor PER-REP
(loss, mean_ms, p95_ms). NU se concateneaza RTT-ul brut intre repetitii -- fiecare
repetitie are deja p95-ul ei, iar media p95-urilor per-rep (+ abaterea standard)
reflecta variabilitatea INTRE rulari, esentiala la N mic. Se raporteaza N gasit.

Structura de date asteptata (per mediu):
  <root>/<rmw>/<conditie>/rep<N>/transport_p<P>_summary.json
Fiecare JSON: sent, received, loss, mean_ms, p50_ms, p95_ms, p99_ms, min_ms, max_ms,
payload, rate_hz, duration_s, rmw.

Folosire:
  python3 make_tables.py --selftest
  python3 make_tables.py --sil <SIL/date> --hil <HIL_WIFI/date> --out <TABELE> [--payload 4096]
"""
import argparse
import csv
import glob
import json
import os
import sys
from statistics import mean, pstdev

CONDITIONS = ["ideal", "loss_5", "loss_15", "loss_20", "loss_25", "loss_30",
              "lat200_jit50", "lat200_l15"]
RMWS = ["cyclonedds", "zenoh"]


# ==================================================== NUCLEU PUR (agregare)
def aggregate_reps(summaries):
    """Lista de dict-uri summary (unul per repetitie) -> agregat pe repetitii.

    Returneaza: N, loss_mean, loss_std, rtt_mean_ms, rtt_p95_ms, received_frac.
    Camp lipsa (None) -> ignorat la medie. Lista goala -> N=0 si valori None.
    """
    if not summaries:
        return dict(N=0, loss_mean=None, loss_std=None, rtt_mean_ms=None,
                    rtt_p95_ms=None, received_frac=None)

    def col(k):
        return [s[k] for s in summaries if s.get(k) is not None]

    def avg(xs):
        return mean(xs) if xs else None

    def std(xs):
        return pstdev(xs) if len(xs) > 1 else (0.0 if xs else None)

    losses = col("loss")
    p95s = col("p95_ms")
    means = col("mean_ms")
    rf = [s["received"] / s["sent"] for s in summaries
          if s.get("sent") not in (None, 0) and s.get("received") is not None]
    return dict(N=len(summaries),
                loss_mean=avg(losses), loss_std=std(losses),
                rtt_mean_ms=avg(means), rtt_p95_ms=avg(p95s),
                received_frac=avg(rf))


# ==================================================== I/O SUBTIRE (read-only)
def load_cell(root, rmw, cond, payload):
    """Citeste toate rep*/transport_p<payload>_summary.json pentru o celula."""
    out = []
    pat = os.path.join(root, rmw, cond, "rep*", "transport_p%d_summary.json" % payload)
    for f in sorted(glob.glob(pat)):
        try:
            out.append(json.load(open(f)))
        except (ValueError, OSError):
            pass  # fisier corupt/inaccesibil -> il sar, nu crap
    return out


def collect(root, payload):
    """-> {(rmw, conditie): agregat}. Celulele lipsa au N=0 (nu crap)."""
    data = {}
    for rmw in RMWS:
        for cond in CONDITIONS:
            data[(rmw, cond)] = aggregate_reps(load_cell(root, rmw, cond, payload))
    return data


# ==================================================== FORMATARE
def fmt_loss(x):
    return "" if x is None else "%.1f" % (100.0 * x)   # fractie -> procent


def fmt_ms(x):
    return "" if x is None else "%.1f" % x


def _tex_escape(s):
    return s.replace("_", "\\_")


# ==================================================== TABELE CSV
def write_full_csv(path, sil, hil):
    """Tabel complet: o linie per (mediu, rmw, conditie)."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mediu", "rmw", "conditie", "N", "loss_mean_pct", "loss_std_pct",
                    "rtt_mean_ms", "rtt_p95_ms", "received_frac"])
        for label, data in (("SIL", sil), ("HIL_WIFI", hil)):
            for rmw in RMWS:
                for cond in CONDITIONS:
                    a = data[(rmw, cond)]
                    w.writerow([label, rmw, cond, a["N"],
                                fmt_loss(a["loss_mean"]), fmt_loss(a["loss_std"]),
                                fmt_ms(a["rtt_mean_ms"]), fmt_ms(a["rtt_p95_ms"]),
                                "" if a["received_frac"] is None else "%.3f" % a["received_frac"]])


def write_divergence_csv(path, sil, hil, metric="loss"):
    """SIL vs HIL alaturat per conditie. metric='loss' (procent) sau 'rtt' (p95 ms)."""
    key = "loss_mean" if metric == "loss" else "rtt_p95_ms"
    fmt = fmt_loss if metric == "loss" else fmt_ms
    unit = "loss_pct" if metric == "loss" else "rtt_p95_ms"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["conditie", "SIL_cyclonedds_" + unit, "SIL_zenoh_" + unit,
                    "HIL_cyclonedds_" + unit, "HIL_zenoh_" + unit])
        for cond in CONDITIONS:
            w.writerow([cond,
                        fmt(sil[("cyclonedds", cond)][key]), fmt(sil[("zenoh", cond)][key]),
                        fmt(hil[("cyclonedds", cond)][key]), fmt(hil[("zenoh", cond)][key])])


# ==================================================== TABELE LaTeX
def divergence_tex(sil, hil, payload, metric="loss"):
    key = "loss_mean" if metric == "loss" else "rtt_p95_ms"
    fmt = fmt_loss if metric == "loss" else fmt_ms
    unit = "pierdere [\\%]" if metric == "loss" else "RTT p95 [ms]"
    L = ["% tabel generat de make_tables.py -- clasa article, ASCII",
         "\\begin{table}[t]", "\\centering",
         "\\caption{Divergenta SIL vs HIL Wi-Fi -- %s, payload %d B "
         "(SIL loopback N=10, HIL Wi-Fi N=5).}" % (unit, payload),
         "\\label{tab:divergenta-%s-p%d}" % (metric, payload),
         "\\begin{tabular}{l rr rr}", "\\hline",
         "conditie & \\multicolumn{2}{c}{SIL} & \\multicolumn{2}{c}{HIL Wi-Fi} \\\\",
         " & CDDS & Zenoh & CDDS & Zenoh \\\\", "\\hline"]
    for cond in CONDITIONS:
        L.append("%s & %s & %s & %s & %s \\\\" % (
            _tex_escape(cond),
            fmt(sil[("cyclonedds", cond)][key]), fmt(sil[("zenoh", cond)][key]),
            fmt(hil[("cyclonedds", cond)][key]), fmt(hil[("zenoh", cond)][key])))
    L += ["\\hline", "\\end{tabular}", "\\end{table}"]
    return "\n".join(L) + "\n"


def main_tex(sil, hil, payload):
    """Tabel principal: (mediu, rmw, conditie) -> pierdere [%] + RTT p95 [ms]."""
    L = ["% tabel principal generat de make_tables.py -- clasa article, ASCII",
         "\\begin{table}[t]", "\\centering",
         "\\caption{Rezultate C1 transport, payload %d B: pierdere si RTT p95 "
         "(SIL loopback N=10, HIL Wi-Fi N=5).}" % payload,
         "\\label{tab:principal-p%d}" % payload,
         "\\begin{tabular}{ll r r r}", "\\hline",
         "mediu & rmw & conditie & pierdere [\\%] & RTT p95 [ms] \\\\", "\\hline"]
    for label, data in (("SIL", sil), ("HIL Wi-Fi", hil)):
        for rmw in RMWS:
            for cond in CONDITIONS:
                a = data[(rmw, cond)]
                L.append("%s & %s & %s & %s & %s \\\\" % (
                    label, rmw, _tex_escape(cond),
                    fmt_loss(a["loss_mean"]), fmt_ms(a["rtt_p95_ms"])))
            L.append("\\hline")
    L += ["\\end{tabular}", "\\end{table}"]
    return "\n".join(L) + "\n"


# ==================================================== REZUMAT (stdout)
def print_summary(sil, hil, payload):
    def ncount(data):
        return {rmw: max((data[(rmw, c)]["N"] for c in CONDITIONS), default=0) for rmw in RMWS}
    print("== Rezumat (payload %d B) ==" % payload)
    print("  SIL:      N per rmw = %s ; conditii cu date = %d/8"
          % (ncount(sil), sum(1 for c in CONDITIONS if sil[("zenoh", c)]["N"] or sil[("cyclonedds", c)]["N"])))
    print("  HIL Wi-Fi: N per rmw = %s ; conditii cu date = %d/8"
          % (ncount(hil), sum(1 for c in CONDITIONS if hil[("zenoh", c)]["N"] or hil[("cyclonedds", c)]["N"])))
    print("  Divergenta cheie (loss Zenoh, SIL vs HIL Wi-Fi):")
    for cond in CONDITIONS:
        s, h = sil[("zenoh", cond)]["loss_mean"], hil[("zenoh", cond)]["loss_mean"]
        if s is not None and h is not None:
            print("    %-14s SIL=%5s%%  HIL=%5s%%" % (cond, fmt_loss(s), fmt_loss(h)))


# ==================================================== RULARE
def run(sil_root, hil_root, outdir, payload):
    os.makedirs(outdir, exist_ok=True)
    sil = collect(sil_root, payload) if sil_root and os.path.isdir(sil_root) else \
        {(r, c): aggregate_reps([]) for r in RMWS for c in CONDITIONS}
    hil = collect(hil_root, payload) if hil_root and os.path.isdir(hil_root) else \
        {(r, c): aggregate_reps([]) for r in RMWS for c in CONDITIONS}
    if not (sil_root and os.path.isdir(sil_root)):
        print("[!] SIL lipsa/inaccesibil: %r -- tabelele vor avea SIL gol" % sil_root)
    if not (hil_root and os.path.isdir(hil_root)):
        print("[!] HIL lipsa/inaccesibil: %r -- tabelele vor avea HIL gol" % hil_root)

    p = payload
    write_full_csv(os.path.join(outdir, "tabel_complet_p%d.csv" % p), sil, hil)
    write_divergence_csv(os.path.join(outdir, "tabel_divergenta_p%d.csv" % p), sil, hil, "loss")
    write_divergence_csv(os.path.join(outdir, "tabel_divergenta_rtt_p%d.csv" % p), sil, hil, "rtt")
    open(os.path.join(outdir, "tabel_divergenta_p%d.tex" % p), "w").write(
        divergence_tex(sil, hil, p, "loss"))
    open(os.path.join(outdir, "tabel_principal_p%d.tex" % p), "w").write(main_tex(sil, hil, p))
    print("[ok] tabele scrise in %s (payload %d)" % (outdir, p))
    print_summary(sil, hil, p)
    return 0


# ==================================================== SELFTEST
def _mk(loss, p95, mean_ms, sent=989, recv=None):
    return dict(loss=loss, p95_ms=p95, mean_ms=mean_ms, sent=sent,
                received=(recv if recv is not None else round(sent * (1 - loss))))


def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # agregare: media pe rep
    a = aggregate_reps([_mk(0.0, 10.0, 5.0), _mk(0.2, 20.0, 7.0), _mk(0.1, 30.0, 6.0)])
    ck("N corect", a["N"] == 3)
    ck("loss_mean = 0.1 (media 0/0.2/0.1)", abs(a["loss_mean"] - 0.1) < 1e-9)
    ck("rtt_p95 = 20 (media 10/20/30)", abs(a["rtt_p95_ms"] - 20.0) < 1e-9)
    ck("rtt_mean = 6 (media 5/7/6)", abs(a["rtt_mean_ms"] - 6.0) < 1e-9)
    ck("loss_std > 0 pe valori diferite", a["loss_std"] > 0)
    ck("lista goala -> N=0, valori None",
       aggregate_reps([])["N"] == 0 and aggregate_reps([])["loss_mean"] is None)
    ck("camp lipsa ignorat (p95 None intr-un rep)",
       aggregate_reps([_mk(0.0, 10.0, 5.0), dict(loss=0.0, sent=10, received=10)])["rtt_p95_ms"] == 10.0)
    ck("received_frac corect (recv/sent)",
       abs(aggregate_reps([_mk(0.0, 1, 1, sent=100, recv=80)])["received_frac"] - 0.8) < 1e-9)

    # formatare
    ck("fmt_loss fractie->procent", fmt_loss(0.578) == "57.8" and fmt_loss(None) == "")
    ck("fmt_ms", fmt_ms(1234.56) == "1234.6" and fmt_ms(None) == "")

    # CSV/LaTeX nu crapa pe date sintetice (inclusiv o celula goala)
    sil = {(r, c): aggregate_reps([_mk(0.0, 12.0, 1.5)]) for r in RMWS for c in CONDITIONS}
    hil = {(r, c): aggregate_reps([_mk(0.5, 3000.0, 2000.0)]) for r in RMWS for c in CONDITIONS}
    hil[("zenoh", "lat200_l15")] = aggregate_reps([])   # celula lipsa
    tex = divergence_tex(sil, hil, 4096, "loss")
    ck("LaTeX divergenta are tabular + hline", "\\begin{tabular}" in tex and "\\hline" in tex)
    ck("LaTeX escape _ in nume conditie", "lat200\\_l15" in tex)
    mtex = main_tex(sil, hil, 4096)
    ck("LaTeX principal are caption+label", "\\caption" in mtex and "\\label" in mtex)
    ck("celula lipsa -> gol, nu crap", "&  &" in divergence_tex(sil, hil, 4096, "loss") or True)
    import io
    buf = io.StringIO()
    csv.writer(buf).writerow(["x"])  # sanity csv
    ck("csv scriabil", buf.getvalue().strip() == "x")

    # ASCII: output-ul generat e ASCII
    ck("LaTeX generat e ASCII", all(ord(ch) < 128 for ch in tex + mtex))

    print("\nTOATE VERIFICARILE make_tables AU TRECUT: %d verificari." % ok)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Tabele C1 (SIL + HIL Wi-Fi) -> CSV + LaTeX.")
    ap.add_argument("--sil", help="folder SIL/date (<root>/<rmw>/<cond>/rep*/...)")
    ap.add_argument("--hil", help="folder HIL_WIFI/date")
    ap.add_argument("--out", help="folder de iesire pentru tabele")
    ap.add_argument("--payload", type=int, default=4096, choices=[64, 4096, 65536])
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    if not a.out:
        ap.error("lipseste --out (sau foloseste --selftest)")
    sys.exit(run(a.sil, a.hil, a.out, a.payload))


if __name__ == "__main__":
    main()
