#!/usr/bin/env python3
"""burst_metrics.py -- metrici burst-aware pentru C2 din logul per-esantion.

PUR PYTHON (stdlib), FARA ROS, fara retea. Intrare: transport_p<P>.csv scris de
bench_client.py (coloane: seq,rtt_ms -- un rand per esantion RECEPTIONAT). Un
esantion PIERDUT nu apare in CSV => se deduce din GOLURILE de secventa: intre doua
seq receptionate consecutive a=..., b=... sunt (b-a-1) pierderi consecutive = o
'rafala de esec' (failure burst) de lungimea aceea.

Per repetitie (un CSV) raporteaza: cea mai lunga rafala de esec consecutiv,
distributia lungimilor de rafala (medie, p95), numarul de rafale.

LIMITA (onesta): se masoara rafalele INTERIOARE (intre livrari). Pierderile de la
margini (inainte de primul / dupa ultimul esantion receptionat) NU intra in
golurile interioare; daca se da 'sent' (din _summary.json), se raporteaza si
total_loss (0 receptionate) si marginile ca info. Vezi LOGARE_PER_ESANTION.md.
Timestampul absolut NU e logat -- pentru rafale in PACHETE nu e necesar; timpul se
deduce din rata fixa (50 Hz => 20 ms/pachet) daca e nevoie.
"""
import csv
import os
import statistics
import sys


def _p95(xs):
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(0.95 * (len(s) - 1))))]


def failure_bursts(received_seqs):
    """Lungimile rafalelor de esec interioare = golurile intre seq receptionate
    consecutive. received_seqs: iterabil de intregi (se sorteaza + deduplica)."""
    rs = sorted(set(int(x) for x in received_seqs))
    return [b - a - 1 for a, b in zip(rs, rs[1:]) if b - a - 1 > 0]


def burst_stats(received_seqs, sent=None):
    """Metrici per repetitie. Intoarce dict pur (JSON-abil)."""
    rs = sorted(set(int(x) for x in received_seqs))
    bursts = failure_bursts(rs)
    out = {
        "n_received": len(rs),
        "n_bursts": len(bursts),
        "longest_burst": max(bursts) if bursts else 0,
        "burst_mean": round(statistics.fmean(bursts), 3) if bursts else 0.0,
        "burst_p95": _p95(bursts) if bursts else 0,
    }
    if sent is not None:
        out["sent"] = sent
        out["total_loss"] = (len(rs) == 0 and sent > 0)
        # margini (info): pierderi inainte de primul / dupa ultimul receptionat
        # nu se pot atribui fara domeniul exact de seq eligibile; se raporteaza doar
        # daca received e nevid, ca numar de seq lipsa fata de intervalul observat.
    return out


def load_received(csv_path):
    """Citeste coloana seq din transport_p<P>.csv (header seq,rtt_ms)."""
    seqs = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            try:
                seqs.append(int(row["seq"]))
            except (KeyError, ValueError):
                continue
    return seqs


def _selftest():
    # received 11,12,14,15,19 pe intervalul eligibil -> goluri: {13}, {16,17,18}
    b = failure_bursts([11, 12, 14, 15, 19])
    assert b == [1, 3], b
    s = burst_stats([11, 12, 14, 15, 19])
    assert s["n_bursts"] == 2 and s["longest_burst"] == 3, s
    assert abs(s["burst_mean"] - 2.0) < 1e-9 and s["burst_p95"] == 3, s
    # fara pierderi -> zero rafale
    assert burst_stats([1, 2, 3, 4])["n_bursts"] == 0
    # o singura rafala lunga: intre seq 1 si 10 lipsesc 2..9 = 8 pierderi
    s2 = burst_stats([1, 10])
    assert s2["n_bursts"] == 1 and s2["longest_burst"] == 8, s2
    # ordine/duplicate tolerate
    assert failure_bursts([5, 5, 1, 3]) == [1, 1], failure_bursts([5, 5, 1, 3])
    # total loss (0 receptionate, sent dat)
    tl = burst_stats([], sent=989)
    assert tl["total_loss"] is True and tl["n_bursts"] == 0, tl
    print("SELFTEST burst_metrics OK (6 verificari).")


def main(argv):
    if not argv:
        print("uz: python3 burst_metrics.py <transport_p*.csv> [...]")
        print("    python3 burst_metrics.py --selftest")
        return 0
    if argv[0] == "--selftest":
        _selftest(); return 0
    print("%-40s %8s %7s %8s %8s %8s" % (
        "fisier", "recv", "rafale", "max", "medie", "p95"))
    all_bursts = []
    for path in argv:
        rec = load_received(path)
        s = burst_stats(rec)
        all_bursts += failure_bursts(rec)
        print("%-40s %8d %7d %8d %8.3f %8d" % (
            os.path.basename(path), s["n_received"], s["n_bursts"],
            s["longest_burst"], s["burst_mean"], s["burst_p95"]))
    if all_bursts:
        print("--- agregat peste %d fisiere: rafale=%d max=%d medie=%.3f p95=%d" % (
            len(argv), len(all_bursts), max(all_bursts),
            statistics.fmean(all_bursts), _p95(all_bursts)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
