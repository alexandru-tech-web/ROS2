#!/usr/bin/env python3
"""sil_policy_loop.py - SIL end-to-end al buclei C3: decizie + aplicare.

Inchide bucla pe care o cerea analiza: link_adaptive DECIDE politica, iar
policy_applier o APLICA pe fluxul de telemetrie. Conduce ambele printr-o
cronologie de degradare (conditiile C1 variabile in timp) si arata cum debitul
efectiv de telemetrie si dimensiunea payload-ului se string automat cand
legatura se inrautateste -- adica stratul protejeaza singur legatura, fara sa
modificam drone_node sau gcs_node.

Fara ROS. Determinist. Telemetria de intrare e sintetica (20 Hz, payload tipic).

  python3 sil_policy_loop.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from link_adaptive_core import AdaptiveController, NOMINAL, DEGRADED, CRITICAL
from policy_applier import PolicyApplier

# conditiile C1 (rtt impus [ms], pierdere impusa) care variaza in timp
C1 = {"ideal": (20, 0.0), "loss_5": (20, 0.05), "loss_15": (20, 0.15),
      "loss_30": (20, 0.30), "lat200_jit50": (200, 0.0), "lat200_l15": (200, 0.15)}
TIMELINE = ["ideal", "loss_5", "loss_15", "loss_30", "loss_15",
            "lat200_jit50", "lat200_l15", "loss_5", "ideal"]
STEP_S = 4.0
TEL_HZ = 20.0          # debitul de telemetrie de intrare (de la drona)

# un esantion de telemetrie "plin" tipic /sar/telemetry
def sample(seq, t):
    return {"id": "d1", "x": 12.3, "y": 4.5, "z": 0.0, "vx": 1.1, "vy": 0.2,
            "seq": seq, "t": round(t, 3), "soc": 0.74, "phase": "scan",
            "coverage": 0.41, "cohesion": 0.88, "battery_state": "NORMAL"}


def run():
    ctrl = AdaptiveController()
    ap = PolicyApplier()
    dt = 1.0 / TEL_HZ
    t = 0.0
    seq = 0
    rows = []     # (t, cond, mode, fwd_rate_hz, payload_bytes)
    full_bytes = len(json.dumps(sample(0, 0.0)))

    for cond in TIMELINE:
        rtt, loss = C1[cond]
        mode, pol = ctrl.update(rtt, loss, t)
        ap.set_policy(pol)
        # numara forward-urile pe fereastra acestei conditii
        win_fwd = 0; win_bytes = []
        steps = int(STEP_S / dt)
        for _ in range(steps):
            out = ap.on_sample(t, t, sample(seq, t))   # esantioane proaspete
            if out is not None:
                win_fwd += 1
                win_bytes.append(len(json.dumps(out)))
            seq += 1
            t += dt
        fwd_rate = win_fwd / STEP_S
        pbytes = (sum(win_bytes) / len(win_bytes)) if win_bytes else 0
        rows.append((t, cond, mode, fwd_rate, pbytes))

    st = ap.stats()
    vol_in = st["in"]; vol_out = st["fwd"]
    print("--- SIL bucla C3: link_adaptive decide -> policy_applier aplica ---")
    print(f"  telemetrie intrare: {TEL_HZ:.0f} Hz, payload plin: {full_bytes} octeti")
    print(f"  {'conditie':14s} {'mod':9s} {'debit fwd':>10s} {'payload':>9s}")
    for (_t, cond, mode, fwd, pb) in rows:
        print(f"  {cond:14s} {mode:9s} {fwd:7.1f} Hz {pb:6.0f} B")
    print()
    print(f"  Total: {vol_in} esantioane intrate -> {vol_out} forward-ate "
          f"({100*vol_out/max(vol_in,1):.0f}%); "
          f"aruncate pe rata {st['drop_rate']}, pe vechime {st['drop_stale']}.")
    print(f"  Pe legatura proasta, stratul reduce singur debitul (20 -> 10 -> 2 Hz)")
    print(f"  si payload-ul (FULL -> REDUCED -> CRITICAL), protejand legatura.")

    _plot(rows, full_bytes)
    # criteriu: debitul efectiv scade strict cu severitatea (NOMINAL>DEGRADED>CRITICAL)
    by_mode = {}
    for (_t, _c, mode, fwd, _pb) in rows:
        by_mode.setdefault(mode, []).append(fwd)
    avg = {m: sum(v) / len(v) for m, v in by_mode.items()}
    okn = avg.get(NOMINAL, 0) > avg.get(DEGRADED, 0) > avg.get(CRITICAL, 0)
    return okn


def _plot(rows, full_bytes):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("\n  (matplotlib indisponibil - sar peste figura)"); return
    ts = [r[0] for r in rows]
    yv = {NOMINAL: 0, DEGRADED: 1, CRITICAL: 2}

    fig = plt.figure(figsize=(13.5, 3.8), dpi=130)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.1, 1.1, 1.0], wspace=0.34)

    axA = fig.add_subplot(gs[0, 0])
    axA.step(ts, [yv[r[2]] for r in rows], where="post", lw=2.4, color="#1C7293")
    axA.set_yticks([0, 1, 2]); axA.set_yticklabels(["NOMINAL", "DEGRADED", "CRITICAL"])
    axA.set_ylim(-0.3, 2.4); axA.set_xlabel("timp [s]")
    axA.set_title("Modul decis de link_adaptive"); axA.grid(alpha=0.3)
    last = None
    for r in rows:
        if r[1] != last:
            axA.axvline(r[0] - STEP_S, color="#ccc", lw=0.7, ls=":")
            axA.annotate(r[1], (r[0] - STEP_S, 2.3), fontsize=6.5, rotation=90,
                         va="top", ha="left", color="#777")
            last = r[1]

    axB = fig.add_subplot(gs[0, 1])
    axB.step(ts, [r[3] for r in rows], where="post", lw=2.6, color="#1C7293",
             label="debit telemetrie efectiv")
    axB.axhline(TEL_HZ, color="#E8A33D", ls="--", lw=1.6, label=f"intrare {TEL_HZ:.0f} Hz")
    axB.set_ylim(0, TEL_HZ * 1.15); axB.set_xlabel("timp [s]")
    axB.set_ylabel("debit telemetrie [Hz]")
    axB.set_title("Applier-ul limiteaza debitul"); axB.grid(alpha=0.3)
    axB.legend(fontsize=7, loc="upper right")

    axC = fig.add_subplot(gs[0, 2])
    axC.step(ts, [r[4] for r in rows], where="post", lw=2.6, color="#3FA34D")
    axC.axhline(full_bytes, color="#999", ls=":", lw=1.2)
    axC.set_ylim(0, full_bytes * 1.15); axC.set_xlabel("timp [s]")
    axC.set_ylabel("payload mediu [octeti]")
    axC.set_title("...si reduce payload-ul"); axC.grid(alpha=0.3)

    fig.suptitle("Bucla C3 inchisa: cand legatura se degradeaza, stratul reduce "
                 "singur debitul SI payload-ul telemetriei", fontsize=11.5, y=1.05)
    fig.savefig("sil_policy_loop.png", bbox_inches="tight")
    print("\n  [figura] sil_policy_loop.png")


def main():
    run()


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
