#!/usr/bin/env python3
"""demo_sil.py -- M19: prognoza RTT pe seria mea de latenta.

Headless, fara argumente. Ia o serie temporala de RTT (o conditie de degradare),
o imparte TEMPORAL (primele 70% train, restul test, fara look-ahead), potriveste
un AR(p) pe partea de train, prognozeaza un-pas RTT pe test si compara RMSE-ul
modelului AR cu cel al persistentei (ultima valoare).

Daca matplotlib exista, emite fig_prognoza_rtt.png (serie reala vs prognoza);
altfel tipareste numeric. Datele sunt SINTETICE (semanate din C1/M via date_sar).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from serii_temporale_core import (  # noqa: E402
    fit_ar, temporal_split, ar_predict_onestep, persistence_forecast,
)
from date_sar import make_latency_series  # noqa: E402
from utils import rmse, maybe_savefig  # noqa: E402

COND = "loss_15"   # o singura conditie
P = 3              # ordinul AR


def main():
    df = make_latency_series(cond=COND, length=300, seed=4, middleware="DDS")
    series = df["rtt_ms"].to_numpy(dtype=float)

    train, test, idx_tr, idx_te = temporal_split(series, train_frac=0.7)
    print("conditie=%s  AR(%d)  train=%d  test=%d (split temporal, fara look-ahead)"
          % (COND, P, train.size, test.size))

    c, phi = fit_ar(train, p=P)
    print("coeficienti AR: c=%.3f  phi=%s" % (c, np.array2string(phi, precision=3)))

    yt_ar, yp_ar = ar_predict_onestep(test, c, phi, warmup=train)
    yt_pe, yp_pe = persistence_forecast(train, test)
    rmse_ar = rmse(yt_ar, yp_ar)
    rmse_pe = rmse(yt_pe, yp_pe)
    print("RMSE pe test [ms]:  AR=%.3f   persistenta=%.3f" % (rmse_ar, rmse_pe))
    if rmse_ar < rmse_pe:
        print("  -> AR bate persistenta cu %.1f%%" % (100.0 * (1 - rmse_ar / rmse_pe)))
    else:
        print("  -> AR NU bate persistenta pe aceasta serie (zgomot/spike-uri).")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(idx_tr, train, color="0.6", lw=1, label="train (real)")
        ax.plot(idx_te, yt_ar, color="C0", lw=1.2, label="test (real)")
        ax.plot(idx_te, yp_ar, color="C1", lw=1.2, ls="--", label="prognoza AR (un-pas)")
        ax.plot(idx_te, yp_pe, color="C2", lw=1.0, ls=":", label="persistenta")
        ax.set_xlabel("t (pas)"); ax.set_ylabel("RTT [ms]")
        ax.set_title("M19 prognoza RTT, conditie %s (date SINTETICE)" % COND)
        ax.legend(fontsize=8)
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_prognoza_rtt.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
