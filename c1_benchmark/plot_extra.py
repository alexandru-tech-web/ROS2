#!/usr/bin/env python3
"""plot_extra.py -- figuri SUPLIMENTARE pentru campania C1 HIL (citeste results_c1/).

Scoate mai mult din datele existente, fara a atinge analyze_campaign.py:
  fig_loss_vs_latency.png/.pdf  doua panouri: pierdere sub LOSS pur vs sub LATENTA
                                (cele doua moduri de esec; Zenoh cedeaza pe ambele axe)
  fig_rtt_log.png/.pdf          RTT p95 pe scara LOGARITMICA (vede si degradarea usoara)
  fig_payload.png/.pdf          efectul sarcinii utile (64/4096/65536 B) asupra pierderii

Reutilizeaza culorile, ordinea conditiilor, eticheta de mediu si salvarea (.png+.pdf)
din analyze_campaign.py -- consistenta intre figuri. ONESTITATE: oriunde received=0
(100% loss), marcheaza explicit, nu lasa gol mut.

Folosire (pe datele DEJA generate, fara ROS):
  python3 plot_extra.py results_c1 --env hil_wifi --out results_c1/analysis_hil_wifi_v2
  python3 plot_extra.py --selftest
"""
import argparse
import glob
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_campaign import COL, COND_ORDER, env_label, _savefig, REF_PAYLOAD  # noqa: E402

LOSS_CONDS = ["ideal", "loss_5", "loss_15", "loss_20", "loss_25", "loss_30"]
LAT_CONDS = ["ideal", "lat200_jit50", "lat200_l15"]
PAYLOAD_CONDS = ["ideal", "loss_15"]
FAIL_RED = "#b22222"


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else 0.0


def collect_all(root):
    """Citeste TOATE payload-urile -> {(rmw, cond, payload): {loss, p95, recv, sent}}."""
    out = {}
    for sj in glob.glob(os.path.join(root, "*", "*", "rep*",
                                     "transport_p*_summary.json")):
        parts = sj.split(os.sep)
        rmw, cond = parts[-4], parts[-3]
        try:
            d = json.load(open(sj))
        except (ValueError, OSError):
            continue
        payload = d.get("payload")
        if payload is None:
            continue
        e = out.setdefault((rmw, cond, payload),
                           dict(loss=[], p95=[], recv=[], sent=[]))
        e["loss"].append(d.get("loss", 0.0))
        if d.get("p95_ms") is not None:
            e["p95"].append(d["p95_ms"])
        e["recv"].append(d.get("received", 0))
        e["sent"].append(d.get("sent", 0))
    return out


def _rmws(data):
    return sorted({k[0] for k in data})


def _present(data, conds, payload, rmws):
    return [c for c in conds if any((r, c, payload) in data for r in rmws)]


# ---------------------------------------------------------------- GRAFIC NOU 1
def fig_loss_vs_latency(data, outdir, env, payload=REF_PAYLOAD):
    rmws = _rmws(data)
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    panels = ((axL, LOSS_CONDS, "pierdere injectata (loss_*)"),
              (axR, LAT_CONDS, "latenta + jitter (lat200_*)"))
    for ax, conds, title in panels:
        conds = _present(data, conds, payload, rmws)
        w = 0.8 / max(1, len(rmws))
        for j, rmw in enumerate(rmws):
            xs = [i + j * w for i in range(len(conds))]
            ys = [100 * mean(data.get((rmw, c, payload), {}).get("loss", []))
                  for c in conds]
            ax.bar(xs, ys, width=w, label=rmw, color=COL.get(rmw, "#888"),
                   edgecolor="black", linewidth=0.5)
            for x, y in zip(xs, ys):
                ax.text(x, y, "%.0f%%" % y, ha="center", va="bottom", fontsize=8)
        ax.set_xticks([i + w * (len(rmws) - 1) / 2 for i in range(len(conds))],
                      conds, rotation=15, fontsize=9)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("conditie de retea (tc netem)", fontsize=10)
        ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6)
        ax.set_axisbelow(True)
    axL.set_ylabel("pierdere masurata [%]", fontsize=11)
    axL.legend(title="RMW", fontsize=9)
    fig.suptitle("Doua moduri de esec: pierdere pura vs latenta "
                 "(Zenoh cedeaza pe AMBELE axe)", fontsize=12)
    _savefig(fig, outdir, "fig_loss_vs_latency",
             "%s; N=5 repetitii; sarcina utila %d B." % (env_label(env), payload))


# ---------------------------------------------------------------- GRAFIC NOU 2
def fig_rtt_log(data, outdir, env, payload=REF_PAYLOAD):
    rmws = _rmws(data)
    conds = _present(data, COND_ORDER, payload, rmws)
    fig, ax = plt.subplots(figsize=(9, 5))
    w = 0.8 / max(1, len(rmws))
    seen = set()
    for j, rmw in enumerate(rmws):
        for i, c in enumerate(conds):
            p95 = mean(data.get((rmw, c, payload), {}).get("p95", []))
            x = i + j * w
            if p95 > 0:
                ax.bar(x, p95, width=w, color=COL.get(rmw, "#888"),
                       edgecolor="black", linewidth=0.5,
                       label=(rmw if rmw not in seen else None))
                seen.add(rmw)
            else:
                # received=0 -> nimic de plotat pe log; marcaj explicit la baza
                ax.text(x, 0.02, "received=0", transform=ax.get_xaxis_transform(),
                        rotation=90, ha="center", va="bottom", fontsize=6.5,
                        color=FAIL_RED)
    ax.set_yscale("log")
    ax.set_xticks([i + w * (len(rmws) - 1) / 2 for i in range(len(conds))],
                  conds, rotation=15, fontsize=10)
    ax.set_xlabel("conditie de retea (tc netem)", fontsize=11)
    ax.set_ylabel("RTT p95 [ms] (scara log)", fontsize=11)
    ax.set_title("RTT p95 pe scara logaritmica "
                 "(vede si degradarea la conditii usoare)", fontsize=12)
    if seen:
        ax.legend(title="RMW", fontsize=10)
    ax.grid(axis="y", which="both", linestyle=":", linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    _savefig(fig, outdir, "fig_rtt_log",
             "%s; N=5 repetitii; sarcina utila %d B; received=0 marcat explicit."
             % (env_label(env), payload))


# ---------------------------------------------------------------- GRAFIC NOU 3
def fig_payload(data, outdir, env):
    rmws = _rmws(data)
    payloads = sorted({k[2] for k in data})
    conds = [c for c in PAYLOAD_CONDS
             if any((r, c, p) in data for r in rmws for p in payloads)]
    if not conds or len(payloads) < 2:
        print("[skip] fig_payload: prea putine payload-uri/conditii pentru grafic")
        return
    fig, axes = plt.subplots(1, len(conds), figsize=(6 * len(conds), 5),
                             sharey=True, squeeze=False)
    axes = axes[0]
    w = 0.8 / max(1, len(rmws))
    for ax, c in zip(axes, conds):
        for j, rmw in enumerate(rmws):
            xs = [i + j * w for i in range(len(payloads))]
            ys = [100 * mean(data.get((rmw, c, p), {}).get("loss", []))
                  for p in payloads]
            ax.bar(xs, ys, width=w, label=rmw, color=COL.get(rmw, "#888"),
                   edgecolor="black", linewidth=0.5)
            for x, y in zip(xs, ys):
                ax.text(x, y, "%.0f%%" % y, ha="center", va="bottom", fontsize=8)
        ax.set_xticks([i + w * (len(rmws) - 1) / 2 for i in range(len(payloads))],
                      ["%d B" % p for p in payloads], fontsize=9)
        ax.set_title("conditia '%s'" % c, fontsize=11)
        ax.set_xlabel("sarcina utila [octeti]", fontsize=10)
        ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6)
        ax.set_axisbelow(True)
    axes[0].set_ylabel("pierdere masurata [%]", fontsize=11)
    axes[0].legend(title="RMW", fontsize=9)
    fig.suptitle("Efectul sarcinii utile asupra pierderii "
                 "(banda Wi-Fi limitata loveste payload-ul mare)", fontsize=12)
    _savefig(fig, outdir, "fig_payload",
             "%s; N=5 repetitii; payload-uri %s B."
             % (env_label(env), "/".join(str(p) for p in payloads)))


def run(root, outdir, env):
    data = collect_all(root)
    if not data:
        print("[!] niciun transport_p*_summary.json gasit sub", root)
        return 1
    os.makedirs(outdir, exist_ok=True)
    fig_loss_vs_latency(data, outdir, env)
    fig_rtt_log(data, outdir, env)
    fig_payload(data, outdir, env)
    print("[ok] figuri suplimentare in", outdir)
    return 0


def _selftest():
    """Genereaza date sintetice minimale + ruleaza fluxul (fara ROS)."""
    import tempfile
    root = tempfile.mkdtemp(prefix="plot_extra_st_")
    for rmw in ("cyclonedds", "zenoh"):
        for cond in ("ideal", "loss_15", "lat200_l15"):
            for payload in (64, 4096, 65536):
                d = os.path.join(root, rmw, cond, "rep1")
                os.makedirs(d, exist_ok=True)
                fail = (rmw == "zenoh" and cond == "lat200_l15")
                rec = 0 if fail else 900
                s = dict(n=rec, sent=900, received=rec,
                         loss=1.0 if fail else 0.1, payload=payload)
                if not fail:
                    s["p95_ms"] = 15.0 if cond == "ideal" else 1200.0
                json.dump(s, open(os.path.join(d, "transport_p%d_summary.json" % payload), "w"))
    out = os.path.join(root, "analysis_extra")
    rc = run(root, out, "hil_wifi")
    ok = rc == 0 and all(os.path.exists(os.path.join(out, n + ".png"))
                         for n in ("fig_loss_vs_latency", "fig_rtt_log", "fig_payload"))
    print("SELFTEST plot_extra:", "OK (3 figuri generate, cedare totala gestionata)"
          if ok else "ESUAT")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="Figuri suplimentare C1 HIL (loss-vs-latenta, RTT log, payload).")
    ap.add_argument("root", nargs="?", help="radacina results_c1")
    ap.add_argument("--out", default=None,
                    help="director de iesire (implicit <root>/analysis_extra)")
    ap.add_argument("--env", default="hil_wifi",
                    help="eticheta mediu: sil | hil_wifi | hil_switch")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(_selftest())
    if not a.root:
        ap.error("lipseste 'root' (sau foloseste --selftest)")
    outdir = a.out or os.path.join(a.root, "analysis_extra")
    sys.exit(run(a.root, outdir, a.env))


if __name__ == "__main__":
    main()
