#!/usr/bin/env python3
"""post_run_core.py -- nucleu pur (fara ROS, fara Tk) pentru VIZUALIZATORUL post-rulare:
loadere CSV + agregari peste rezultatele unei campanii (SIL sau HIL), cu detectie de schema.
Frontend-ul (post_run_viewer.py) doar deseneaza; toata logica + testele sunt aici."""
import csv
import io
import math


def percentile(xs, q):
    if not xs:
        return 0.0
    s = sorted(xs)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * (q / 100.0)
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return float(s[int(k)])
    return s[lo] * (hi - k) + s[hi] * (k - lo)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def read_rows(text):
    """CSV (text) -> lista de dict-uri (DictReader)."""
    return list(csv.DictReader(io.StringIO(text)))


def detect_kind(header):
    """Clasifica un CSV dupa antet: transport | mission | campaign_summary | drone | unknown."""
    h = set(header or [])
    if {"seq", "rtt_ms"} <= h:
        return "transport"
    if {"t_s", "coverage", "victims_found"} <= h:
        return "mission"
    if {"rmw", "condition"} <= h and any(c.startswith("rtt") or "mission" in c for c in h):
        return "campaign_summary"
    if {"t", "x", "y"} <= h or {"t_s", "x", "y"} <= h:
        return "drone"
    return "unknown"


def summarize_transport(rows):
    """transport_p*.csv (seq, rtt_ms) -> {n, rtt_p95_ms, rtt_mean_ms, loss}."""
    rtts = [float(r["rtt_ms"]) for r in rows if r.get("rtt_ms") not in (None, "")]
    seqs = [int(r["seq"]) for r in rows if r.get("seq") not in (None, "")]
    loss = 0.0
    if len(seqs) >= 2:
        exp = max(seqs) - min(seqs) + 1
        loss = max(0.0, 1.0 - len(set(seqs)) / exp) if exp > 0 else 0.0
    return {"n": len(rtts), "rtt_p95_ms": percentile(rtts, 95),
            "rtt_mean_ms": mean(rtts) or 0.0, "loss": loss}


def summarize_mission(rows, coverage_goal=0.95, victims_total=5):
    """mission_metrics.csv -> {coverage_end, victims_end, e2e_p95_ms, mission_time_s|None}."""
    if not rows:
        return {"coverage_end": 0.0, "victims_end": 0, "e2e_p95_ms": 0.0, "mission_time_s": None}
    cov = [float(r["coverage"]) for r in rows if r.get("coverage") not in (None, "")]
    vic = [int(float(r["victims_found"])) for r in rows if r.get("victims_found") not in (None, "")]
    e2e = [float(r["e2e_telemetry_ms"]) for r in rows if r.get("e2e_telemetry_ms") not in (None, "")]
    done = None
    for r in rows:
        try:
            if (float(r["coverage"]) >= coverage_goal
                    and int(float(r["victims_found"])) >= victims_total):
                done = float(r["t_s"])
                break
        except (KeyError, ValueError):
            pass
    return {"coverage_end": cov[-1] if cov else 0.0,
            "victims_end": vic[-1] if vic else 0,
            "e2e_p95_ms": percentile(e2e, 95),
            "mission_time_s": done}


def _selftest():
    assert abs(percentile([1, 2, 3, 4], 50) - 2.5) < 1e-9 and percentile([], 95) == 0.0

    t = "seq,rtt_ms\n0,10\n1,20\n3,30\n"          # seq 2 lipseste -> loss 1/4
    rows = read_rows(t)
    assert detect_kind(list(rows[0].keys())) == "transport"
    st = summarize_transport(rows)
    assert st["n"] == 3 and abs(st["loss"] - 0.25) < 1e-9

    m = ("t_s,coverage,victims_found,e2e_telemetry_ms\n"
         "1.0,0.5,2,30\n2.0,0.96,5,40\n3.0,0.97,5,50\n")
    mrows = read_rows(m)
    assert detect_kind(list(mrows[0].keys())) == "mission"
    sm = summarize_mission(mrows)
    assert sm["mission_time_s"] == 2.0 and sm["victims_end"] == 5
    assert abs(sm["coverage_end"] - 0.97) < 1e-9 and sm["e2e_p95_ms"] >= 40

    cs = read_rows("rmw,condition,rtt_p95_ms,mission_time_s\ncyclonedds,loss_30,100,120\n")
    assert detect_kind(list(cs[0].keys())) == "campaign_summary"
    assert detect_kind(["altceva"]) == "unknown"
    print("TOATE VERIFICARILE post_run_core AU TRECUT")


if __name__ == "__main__":
    _selftest()
