#!/usr/bin/env python3
"""demo_sil.py -- demonstratie headless M01 pe date_sar (FARA argumente).

Scenariu: latentele RTT per-pachet ale unei conditii din make_latency_dataset
sunt aproximativ lognormale (cozi lungi spre dreapta). Demonstram:
  1. fit lognormal prin MLE pe rtt_ms (conditie + middleware fixate);
  2. histograma rtt_ms suprapusa cu densitatea lognormala fit-ata;
  3. interval bootstrap (95%) pentru MEDIA RTT.

Daca matplotlib exista, salveaza fig_*.png prin utils.maybe_savefig; altfel
tipareste totul numeric. Ruleaza fara crash, headless:
  /home/ubuntu/ros2_ws/.venv_ml/bin/python demo_sil.py

ONESTITATE: rtt_ms din make_latency_dataset sunt SINTETICE (semanate din campania
C1), nu masuratori reale. Servesc demonstratiei statistice, nu raportarii de teza.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml
from utils import maybe_savefig  # noqa: E402
from date_sar import make_latency_dataset  # noqa: E402

from probabilitate_core import (  # noqa: E402
    lognormal_pdf, lognormal_mean, mle_lognormal, bootstrap_mean_ci,
)

HERE = os.path.dirname(os.path.abspath(__file__))
COND = "loss_15"      # conditie degradata: cozi lungi, lognormal evident
MW = "DDS"


def main():
    df = make_latency_dataset(n_per_cond=300, seed=0)
    sub = df[(df.condition == COND) & (df.middleware == MW)]
    rtt = sub.rtt_ms.to_numpy(dtype=float)
    rtt = rtt[rtt > 0]  # lognormala cere valori strict pozitive

    print("=== M01 demo: fit lognormal pe RTT (%s / %s) ===" % (COND, MW))
    print("n esantion         : %d pachete (sintetice, semanate din C1)" % rtt.size)
    print("media empirica RTT : %.2f ms" % float(np.mean(rtt)))
    print("mediana empirica   : %.2f ms" % float(np.median(rtt)))
    print("p95 empiric        : %.2f ms" % float(np.percentile(rtt, 95)))

    # 1. fit lognormal prin MLE (parametrii normalei subiacente)
    mu_hat, sigma_hat = mle_lognormal(rtt)
    mean_fit = lognormal_mean(mu_hat, sigma_hat)
    print("\n-- fit lognormal (MLE) --")
    print("mu_hat (pe log)    : %.4f" % mu_hat)
    print("sigma_hat (pe log) : %.4f" % sigma_hat)
    print("media implicata exp(mu+sig^2/2) : %.2f ms (vs %.2f empiric)"
          % (mean_fit, float(np.mean(rtt))))

    # 3. interval bootstrap 95% pentru media RTT
    lo, hi, boot = bootstrap_mean_ci(rtt, n_boot=3000, alpha=0.05, seed=1)
    print("\n-- bootstrap (95%) pentru media RTT --")
    print("interval mediei    : [%.2f, %.2f] ms" % (lo, hi))
    print("largime interval   : %.2f ms" % (hi - lo))
    print("(la N=5 acest interval ar fi mult mai larg -- vezi teorie.md)")

    # 2. histograma + densitatea fit-ata
    fig = None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

        ax = axes[0]
        ax.hist(rtt, bins=40, density=True, color="#9ecae1",
                edgecolor="white", label="RTT empiric (densitate)")
        grid = np.linspace(max(1e-3, rtt.min() * 0.5), rtt.max() * 1.05, 500)
        ax.plot(grid, lognormal_pdf(grid, mu=mu_hat, sigma=sigma_hat),
                color="#d62728", lw=2.0, label="lognormal MLE")
        ax.axvline(float(np.mean(rtt)), color="black", ls="--", lw=1.0,
                   label="media empirica")
        ax.set_xlabel("RTT [ms]")
        ax.set_ylabel("densitate")
        ax.set_title("Fit lognormal pe RTT (%s / %s)" % (COND, MW))
        ax.legend(fontsize=8)

        ax2 = axes[1]
        ax2.hist(boot, bins=40, color="#a1d99b", edgecolor="white")
        ax2.axvline(lo, color="#d62728", ls="--", lw=1.2, label="CI 95% jos")
        ax2.axvline(hi, color="#d62728", ls="--", lw=1.2, label="CI 95% sus")
        ax2.axvline(float(np.mean(rtt)), color="black", lw=1.0, label="media obs.")
        ax2.set_xlabel("media RTT a reesantionului [ms]")
        ax2.set_ylabel("frecventa bootstrap")
        ax2.set_title("Bootstrap pentru media RTT")
        ax2.legend(fontsize=8)

        fig.tight_layout()
        maybe_savefig(fig, os.path.join(HERE, "fig_m01_lognormal_rtt.png"))
    except Exception as e:  # pragma: no cover - depinde de mediu
        print("\n[fig] matplotlib indisponibil sau eroare la desen (%s);"
              " rezultatele numerice de mai sus sunt suficiente." % e)

    print("\n[demo] gata.")
    return 0


if __name__ == "__main__":
    main()
    sys.exit(0)
