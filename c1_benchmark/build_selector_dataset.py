#!/usr/bin/env python3
"""build_selector_dataset.py -- BRIDGE: campanie reala C1 -> dataset pentru selector.

Repara veriga rupta din workflow: ml_dataset.csv era un extract ORFAN (niciun script nu-l
genera; loss_pct=0, sent==recv, N=5, fara timp de misiune). Acest script reconstruieste un
dataset din iesirea REALA a campaniei C1 (run_campaign.py), cu loss MASURAT, N=10, 8
conditii, 3 payload-uri.

NU atinge ml_dataset.csv / reproduce_pdia.py / figurile PDIA: scrie un fisier NOU
(implicit selector_dataset.csv), pe care reproduce_selector.py il consuma direct.

Intrare: <campanie>/c1_transport/<rmw>/<cond>/rep<k>/transport_p<payload>_summary.json
         (campuri reale: rmw, payload, sent, received, loss [fractie], p95_ms ...)
Iesire : CSV cu coloane rmw,cond,rep,payload,sent,recv,loss_pct,rtt_p95_ms (loss REAL).

Uz:
  python3 build_selector_dataset.py <dir_campanie> [-o selector_dataset.csv]
  python3 build_selector_dataset.py --selftest      # nucleul pur, fara I/O
"""
import csv
import glob
import json
import os
import sys

# Normalizarea numelui de RMW din JSON / din numele de director.
RMW_MAP = {
    "rmw_cyclonedds_cpp": "cyclonedds",
    "rmw_zenoh_cpp": "zenoh",
    "cyclonedds": "cyclonedds",
    "zenoh": "zenoh",
}


def summary_to_row(d, rmw_dir, cond, rep):
    """Pur: dict-ul unui transport_*_summary.json -> rand de dataset (dict).

    loss din JSON e FRACTIE (0..1) -> loss_pct = loss * 100. rmw normalizat la
    cyclonedds/zenoh. p95_ms -> rtt_p95_ms (acelasi nume ca in ml_dataset.csv).
    """
    rmw = RMW_MAP.get(d.get("rmw", rmw_dir), rmw_dir)
    return {
        "rmw": rmw,
        "cond": cond,
        "rep": rep,
        "payload": int(d["payload"]),
        "sent": int(d["sent"]),
        "recv": int(d["received"]),
        "loss_pct": round(100.0 * float(d["loss"]), 4),
        "rtt_p95_ms": float(d["p95_ms"]),
    }


def walk_campaign(camp_dir):
    """Parcurge arborele campaniei. Intoarce (rows, skipped).

    skipped = rulari fara p95_ms (pierdere ~totala: nimic/prea putin sosit, deci nu
    se poate calcula percentila RTT). Nu inventam un RTT pentru ele -- le raportam.
    """
    base = os.path.join(camp_dir, "c1_transport")
    if not os.path.isdir(base):
        base = camp_dir  # accepta si direct .../c1_transport
    rows = []
    skipped = []
    pat = os.path.join(base, "*", "*", "rep*", "transport_p*_summary.json")
    for path in sorted(glob.glob(pat)):
        parts = path.split(os.sep)
        rep, cond, rmw_dir = parts[-2], parts[-3], parts[-4]
        with open(path) as f:
            d = json.load(f)
        if "p95_ms" not in d:
            skipped.append((path, int(d.get("sent", 0)), int(d.get("received", 0))))
            continue
        rows.append(summary_to_row(d, rmw_dir, cond, rep))
    return rows, skipped


def write_csv(rows, out):
    cols = ["rmw", "cond", "rep", "payload", "sent", "recv", "loss_pct", "rtt_p95_ms"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _selftest():
    d = {"rmw": "rmw_zenoh_cpp", "payload": "4096", "sent": "989",
         "received": "347", "loss": "0.6491", "p95_ms": "12056.397"}
    r = summary_to_row(d, "zenoh", "loss_30", "rep1")
    assert r["rmw"] == "zenoh", r
    assert r["cond"] == "loss_30" and r["rep"] == "rep1"
    assert r["payload"] == 4096 and r["sent"] == 989 and r["recv"] == 347
    assert abs(r["loss_pct"] - 64.91) < 1e-6, r["loss_pct"]
    assert abs(r["rtt_p95_ms"] - 12056.397) < 1e-3
    r2 = summary_to_row(
        {"rmw": "rmw_cyclonedds_cpp", "payload": "64", "sent": "10",
         "received": "10", "loss": "0.0", "p95_ms": "1.3"},
        "cyclonedds", "ideal", "rep2")
    assert r2["loss_pct"] == 0.0 and r2["rmw"] == "cyclonedds"
    print("OK build_selector_dataset._selftest (nucleu pur)")


def main(argv):
    if "--selftest" in argv:
        _selftest()
        return 0
    pos = [a for a in argv[1:] if not a.startswith("-")]
    if not pos:
        print("uz: python3 build_selector_dataset.py <dir_campanie> [-o out.csv]")
        return 2
    camp = pos[0]
    out = argv[argv.index("-o") + 1] if "-o" in argv else "selector_dataset.csv"
    rows, skipped = walk_campaign(camp)
    if not rows:
        print("FATAL: niciun transport_*_summary.json gasit sub %s" % camp)
        return 1
    write_csv(rows, out)
    rmws = sorted(set(r["rmw"] for r in rows))
    conds = sorted(set(r["cond"] for r in rows))
    pls = sorted(set(r["payload"] for r in rows))
    reps = sorted(set(r["rep"] for r in rows))
    nz = sum(1 for r in rows if r["loss_pct"] > 0)
    print("Scris %d randuri in %s" % (len(rows), out))
    print("  rmw=%s  cond=%s  payload=%s  reps=%d" % (rmws, conds, pls, len(reps)))
    print("  randuri cu loss_pct>0 (semnal de pierdere REAL, vs orfanul cu 0): %d/%d"
          % (nz, len(rows)))
    if skipped:
        print("  SARITE %d rulari fara p95_ms (pierdere ~totala, nimic de masurat):" % len(skipped))
        for path, sent, recv in skipped:
            short = os.sep.join(path.split(os.sep)[-4:])
            print("    %s  (sent=%d recv=%d)" % (short, sent, recv))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
