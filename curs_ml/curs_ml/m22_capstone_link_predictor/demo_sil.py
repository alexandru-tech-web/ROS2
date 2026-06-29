#!/usr/bin/env python3
"""demo_sil.py -- M22 CAPSTONE: predictor de link offline -> politica adaptiva vs statica.

Headless, fara argumente, FARA ROS. Antreneaza predictorul de link offline, apoi
simuleaza o cronologie de conditii de link variabile si compara doua politici de
teleoperatie:
  - STATICA: trimite mereu in modul plin (rata mare), indiferent de stare;
  - ADAPTIVA: cere predictorului 'usable?' la fiecare fereastra si COMUTA pe un mod
    de rezerva (degradat, dar care nu se blocheaza) cand linkul e prezis inutilizabil.

Raporteaza CASTIGUL adaptiv: cati pasi de bucla blocata evita comutand la timp.
Acesta este capatul firului care inchide cursul inapoi in teza (C3 / link_adaptive):
ML-ul nu sta intr-un notebook, ci ALIMENTEAZA o decizie de control.

Daca matplotlib exista, emite fig_adaptiv_vs_static.png; altfel tipareste numeric.
ONESTITATE: datele de link sunt SINTETICE (semanate din C1/M via date_sar.py).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from link_predictor_core import train_from_dataset, FEATURE_NAMES  # noqa: E402
from date_sar import make_link_usability_dataset, CONDITIONS  # noqa: E402
from utils import maybe_savefig  # noqa: E402


def build_timeline(n_steps=240, seed=7):
    """Cronologie de ferestre de link: la fiecare pas, alege o conditie (cu derive
    spre degradare la mijloc) si esantioneaza o fereastra din datasetul sintetic.
    Returneaza (rows, truth) -- rows = lista de dict-uri de feature-uri, truth =
    eticheta 'usable' reala a fiecarei ferestre."""
    g = np.random.default_rng(seed)
    df = make_link_usability_dataset(n_per_cond=300, seed=1)
    # regim de degradare: prima si ultima treime preferate 'bune', mijlocul 'rau'
    good = ["ideal", "loss_5", "lat200_jit50"]
    bad = ["loss_15", "loss_30", "lat200_l15"]
    rows, truth = [], []
    for t in range(n_steps):
        in_storm = (n_steps // 3) <= t < (2 * n_steps // 3)
        pool = bad if in_storm else good
        cond = pool[int(g.integers(0, len(pool)))]
        sub = df[df.condition == cond]
        r = sub.iloc[int(g.integers(0, len(sub)))]
        rows.append({k: float(r[k]) for k in FEATURE_NAMES})
        truth.append(int(r["usable"]))
    return rows, np.array(truth, dtype=int)


def simulate(model, rows, truth):
    """Simuleaza cele doua politici peste cronologie.

    Model de cost: in modul PLIN, daca linkul e de fapt inutilizabil bucla se
    BLOCHEAZA (1 pas pierdut); daca e utilizabil, pas reusit. In modul DE REZERVA
    (rata mica) bucla NU se blocheaza niciodata, dar ofera control DEGRADAT
    (penalizare mica, fixa). Politica statica sta mereu in modul plin; cea adaptiva
    comuta in rezerva cand predictorul zice 'inutilizabil'.

    Returneaza un dict cu pasii blocati / degradati pentru fiecare politica si
    seria de decizii adaptive (pentru figura)."""
    static_stall = 0
    adapt_stall = 0
    adapt_degraded = 0
    decisions = []
    for feats, real in zip(rows, truth):
        pred_label, _ = model.predict(feats)   # 1 = prezis usable
        # STATICA: mereu mod plin -> se blocheaza cand linkul e de fapt inutilizabil
        if real == 0:
            static_stall += 1
        # ADAPTIVA: comuta pe rezerva daca predictia = inutilizabil
        if pred_label == 1:                    # ramane pe modul plin
            if real == 0:                      # dar linkul era de fapt rau -> blocaj
                adapt_stall += 1
        else:                                  # comuta pe rezerva (fara blocaj)
            adapt_degraded += 1
        decisions.append(pred_label)
    return dict(static_stall=static_stall,
                adapt_stall=adapt_stall,
                adapt_degraded=adapt_degraded,
                decisions=np.array(decisions, dtype=int))


def main():
    # antrenare OFFLINE pe alt seed decat cronologia (fara scurgere)
    df_train = make_link_usability_dataset(n_per_cond=200, seed=1)
    model = train_from_dataset(df_train, seed=0)

    rows, truth = build_timeline(n_steps=240, seed=7)
    res = simulate(model, rows, truth)

    n = len(rows)
    print("CAPSTONE M22 -- predictor de link -> politica adaptiva vs statica")
    print("date SINTETICE (semanate din C1/M); %d ferestre de link." % n)
    print("conditii disponibile: %s" % ", ".join(CONDITIONS))
    print("-" * 60)
    print("politica STATICA  (mereu mod plin):  %3d pasi blocati" % res["static_stall"])
    print("politica ADAPTIVA (comuta pe rezerva): %3d pasi blocati, %3d pasi degradati"
          % (res["adapt_stall"], res["adapt_degraded"]))
    saved = res["static_stall"] - res["adapt_stall"]
    print("-" * 60)
    print("CASTIG adaptiv: %d blocaje evitate (din %d) prin comutare la timp."
          % (saved, res["static_stall"]))
    if res["static_stall"] > 0:
        print("reducere blocaje: %.1f%%" % (100.0 * saved / res["static_stall"]))

    # figura comparativa optionala
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 5), sharex=True)
        t = np.arange(n)
        ax1.fill_between(t, 0, 1 - truth, step="mid", alpha=0.35, color="tab:red",
                         label="link inutilizabil (real)")
        ax1.step(t, res["decisions"], where="mid", color="tab:blue",
                 label="predictie usable (1=plin, 0=rezerva)")
        ax1.set_ylabel("stare / decizie"); ax1.set_ylim(-0.1, 1.1); ax1.legend(loc="upper right", fontsize=8)
        ax1.set_title("Predictor de link: decizie adaptiva vs realitate (date SINTETICE)")

        labels = ["STATICA\n(blocaje)", "ADAPTIVA\n(blocaje)", "ADAPTIVA\n(degradate)"]
        vals = [res["static_stall"], res["adapt_stall"], res["adapt_degraded"]]
        ax2.bar(labels, vals, color=["tab:red", "tab:orange", "tab:green"])
        ax2.set_ylabel("nr. pasi de bucla")
        for i, v in enumerate(vals):
            ax2.text(i, v + 0.5, str(v), ha="center", fontsize=9)
        here = os.path.dirname(os.path.abspath(__file__))
        maybe_savefig(fig, os.path.join(here, "fig_adaptiv_vs_static.png"))
    except Exception as e:
        print("[fig] matplotlib indisponibil (%s) -- doar numeric." % e)


if __name__ == "__main__":
    main()
