#!/usr/bin/env python3
"""bench_core.py -- nucleul PUR al campaniei C1 (fara ROS, testat automat):
conditiile de retea SAR-realiste, statisticile de transport, comenzile tc
netem, planul de campanie si extragerea timpului de finalizare a misiunii.

Metodologia C1 (cheia articolului): degradarea este REALA (tc netem pe
interfata), nu simulata -- de aceea misiunea ruleaza cu scenario:=none.yaml
(injectorul publica stare curata; singura degradare e cea fizica), iar
diferentele masurate apartin EXCLUSIV middleware-ului (RMW) sub acea retea.
"""
import csv
import sys as _sys; csv.field_size_limit(min(_sys.maxsize, 2**31 - 1))
import io

# RMW-urile comparate (cheia = numele scurt folosit in foldere/figuri)
RMWS = {"cyclonedds": "rmw_cyclonedds_cpp",
        "zenoh": "rmw_zenoh_cpp",
        "fastdds": "rmw_fastrtps_cpp"}     # optional, al treilea punct

# Conditiile SAR-realiste: planul original (pierderi 0/5/15/30%) + doua
# combinatii cu latenta (varful descoperit in simulari: latenta doare).
CONDITIONS = [
    dict(name="ideal",        base_ms=0,   jitter_ms=0,  loss=0.00),
    dict(name="loss_5",       base_ms=0,   jitter_ms=0,  loss=0.05),
    dict(name="loss_15",      base_ms=0,   jitter_ms=0,  loss=0.15),
    dict(name="loss_20",      base_ms=0,   jitter_ms=0,  loss=0.20),
    dict(name="loss_25",      base_ms=0,   jitter_ms=0,  loss=0.25),
    dict(name="loss_30",      base_ms=0,   jitter_ms=0,  loss=0.30),
    # rafale simple (netem 'loss p% r%'): pierdere CORELATA, aceeasi medie
    dict(name="loss_20_burst", base_ms=0,   jitter_ms=0,  loss=0.20, corr=0.50),
    dict(name="loss_25_burst", base_ms=0,   jitter_ms=0,  loss=0.25, corr=0.50),
    dict(name="loss_30_burst", base_ms=0,   jitter_ms=0,  loss=0.30, corr=0.50),
    # gilbert_*: Gilbert-Elliott nativ netem ('loss gemodel'); aceeasi medie ca loss_*,
    # mean_burst_len=5 -> p, r din rf_interference.BurstProcess.from_steady (paritate SIL<->HIL).
    dict(name="gilbert_20",   base_ms=0,   jitter_ms=0,  loss=0.20, type="gilbert", p=0.0500, r=0.2000),
    dict(name="gilbert_25",   base_ms=0,   jitter_ms=0,  loss=0.25, type="gilbert", p=0.0667, r=0.2000),
    dict(name="gilbert_30",   base_ms=0,   jitter_ms=0,  loss=0.30, type="gilbert", p=0.0857, r=0.2000),
    dict(name="lat200_jit50", base_ms=200, jitter_ms=50, loss=0.00),
    dict(name="lat200_l15",   base_ms=200, jitter_ms=50, loss=0.15),
]


def make_payload(n: int) -> str:
    """Sarcina utila de n octeti (ASCII determinist)."""
    return ("x" * max(0, n))


def rtt_stats(rtts_ms, sent, received):
    """Statisticile unei rulari de transport: percentile + pierdere."""
    if not rtts_ms:
        return {"n": 0, "sent": sent, "received": received,
                "loss": 1.0 if sent else 0.0}
    s = sorted(rtts_ms)
    p = lambda q: s[min(len(s) - 1, round(q * (len(s) - 1)))]
    return {"n": len(s), "sent": sent, "received": received,
            "loss": round(1.0 - received / sent, 4) if sent else 0.0,
            "mean_ms": round(sum(s) / len(s), 3),
            "p50_ms": round(p(0.50), 3), "p95_ms": round(p(0.95), 3),
            "p99_ms": round(p(0.99), 3),
            "min_ms": round(s[0], 3), "max_ms": round(s[-1], 3)}


#def netem_cmd(iface: str, c: dict) -> str:
#    """Comanda tc care aplica o conditie (replace = idempotent)."""
#    return (f"tc qdisc replace dev {iface} root netem "
#            f"delay {c.get('base_ms', 0)}ms {c.get('jitter_ms', 0)}ms "
#            f"loss {100 * c.get('loss', 0.0):.1f}%")

def netem_cmd(iface: str, c: dict) -> str:
    """Comanda tc care aplica o conditie (replace = idempotent).
    type=='gilbert': pierdere CORELATA prin Gilbert-Elliott nativ netem
    ('loss gemodel p% r% loss_bad% loss_good%') -- paritate de model SIL<->HIL cu
    rf_interference.BurstProcess. Altfel 'corr'>0: rafale simple ('loss p% r%');
    implicit memoryless ('loss p%')."""
    if c.get("type") == "gilbert":
        loss_tok = "loss gemodel %.3f%% %.3f%% 100%% 0%%" % (100 * c["p"], 100 * c["r"])
    else:
        loss_tok = f"loss {100 * c.get('loss', 0.0):.1f}%"
        if c.get("corr", 0.0):
            loss_tok += f" {100 * c['corr']:.1f}%"
    return (f"tc qdisc replace dev {iface} root netem "
            f"delay {c.get('base_ms', 0)}ms {c.get('jitter_ms', 0)}ms "
            f"{loss_tok}")

def netem_clear_cmd(iface: str) -> str:
    return f"tc qdisc del dev {iface} root"


def build_plan(rmws, conditions, reps, layers=("transport", "mission")):
    """Planul ordonat al campaniei: blocat pe RMW (routerul Zenoh pornit o
    singura data per bloc), conditiile in ordine crescatoare de severitate,
    repetitiile consecutive. Intoarce o lista de rulari-dict."""
    plan = []
    for rmw in rmws:
        if rmw not in RMWS:
            raise ValueError(f"RMW necunoscut: {rmw!r} "
                             f"(stiute: {sorted(RMWS)})")
        for c in conditions:
            for rep in range(1, reps + 1):
                for layer in layers:
                    plan.append(dict(
                        rmw=rmw, rmw_impl=RMWS[rmw], condition=c["name"],
                        netem=c, rep=rep, layer=layer,
                        needs_router=(rmw == "zenoh")))
    return plan


def mission_done_time(metrics_csv_text: str, victims_total: int = 5,
                      coverage_goal: float = 0.95):
    """Primul t la care misiunea e completa, din mission_metrics.csv;
    None daca nu s-a terminat (plafon)."""
    rdr = csv.DictReader(io.StringIO(metrics_csv_text))
    for row in rdr:
        try:
            if (float(row["coverage"]) >= coverage_goal
                    and int(row["victims_found"]) >= victims_total):
                return float(row["t_s"])
        except (KeyError, ValueError):
            return None
    return None
