#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reproduce_pdia.py
Reproduce complet analiza ML din prezentarea PDIA, pe ml_dataset.csv.

Produce:
  - cifrele in consola (R2, acuratete, coeficienti, matrice confuzie)
  - 3 figuri (figA_dataset.png, figB_regresie.png, figC_frontiera.png)
  - 2 CSV cu predictii (predictii_regresie.csv, predictii_clasificare.csv)

Rulare:
  python3 reproduce_pdia.py

Dependinte:
  pip install numpy pandas scikit-learn matplotlib
"""

import os
import sys
import numpy as np
import pandas as pd

# PDF reproductibil pe octeti: matplotlib scrie un timestamp in metadatele PDF;
# il fixam ca regenerarea figurilor sa nu murdareasca git la fiecare rulare.
os.environ.setdefault("SOURCE_DATE_EPOCH", "1718700000")
import matplotlib
matplotlib.use("Agg")  # nu deschide ferestre; salveaza direct in fisiere
import matplotlib.pyplot as plt

from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import r2_score, accuracy_score, confusion_matrix

# ----------------------------------------------------------------------
# PARAMETRI FIXATI - identici cu cei din prezentare (NU schimba daca vrei aceleasi cifre)
# ----------------------------------------------------------------------
HERE           = os.path.dirname(os.path.abspath(__file__))
OUTDIR         = os.path.join(HERE, "Analiza_ML_18.06.2026")  # figurile urmarite ale articolului
CSV_PATH       = os.path.join(HERE, "ml_dataset.csv")   # cele 177 de masuratori (langa script)
RANDOM_STATE   = 42                 # samanta pentru split reproductibil
TEST_SIZE      = 0.30               # 30% holdout pentru test
RIDGE_LAMBDA   = 1.0                # regularizare L2 (alpha in scikit-learn)
PRAG_SAR_MS    = 500.0              # prag RTT pentru "link utilizabil"
CV_FOLDS       = 5                  # numarul de fold-uri la cross-validation

# Codificarea severitatii retelei (ordinala, justificata fizic: usor -> greu)
SEVERITATE = {
    "ideal": 0,
    "loss_5": 1,
    "loss_15": 2,
    "lat200_jit50": 2,
    "loss_30": 3,
    "lat200_l15": 3,
}

# Paleta de culori (identica cu prezentarea)
NAVY = "#1F2D5A"; GOLD = "#E0A800"; TEAL = "#2C7A7B"; RED = "#C0392B"; GRAY = "#5A6478"


def _savefig(fig, name, caption=""):
    """Salveaza in OUTDIR la standard academic: caption SIL sub axe, .png + .pdf, DPI 200."""
    os.makedirs(OUTDIR, exist_ok=True)
    fig.tight_layout(rect=(0, 0.06, 1, 1) if caption else (0, 0, 1, 1))
    if caption:
        fig.text(0.5, 0.01, caption, ha="center", va="bottom", fontsize=8)
    stem = os.path.join(OUTDIR, name)
    for ext in ("png", "pdf"):
        fig.savefig(stem + "." + ext, dpi=200)
    plt.close(fig)
    print(f"  [salvat] {stem}.{{png,pdf}}")


def incarca_date(path):
    """Citeste CSV-ul si construieste variabilele de intrare/iesire."""
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        print(f"[EROARE] Nu gasesc '{path}'. Pune scriptul langa ml_dataset.csv.")
        sys.exit(1)

    # verific coloanele necesare
    necesare = {"cond", "payload", "rtt_p95_ms"}
    lipsa = necesare - set(df.columns)
    if lipsa:
        print(f"[EROARE] Lipsesc coloanele: {lipsa}")
        sys.exit(1)

    # variabile predictor
    df["severitate"] = df["cond"].map(SEVERITATE)
    if df["severitate"].isna().any():
        conditii_nemapate = df.loc[df["severitate"].isna(), "cond"].unique()
        print(f"[EROARE] Conditii necunoscute (nu-s in SEVERITATE): {conditii_nemapate}")
        sys.exit(1)

    df["log_payload"] = np.log10(df["payload"].astype(float))
    df["log_rtt"]     = np.log10(df["rtt_p95_ms"].astype(float))
    return df


def studiu1_regresie(df):
    """
    REGRESIE (predictia latentei).
    Model: log10(RTT) = b + a1*severitate + a2*log10(payload), Ridge L2.
    """
    print("\n" + "=" * 64)
    print("STUDIUL 1 - REGRESIE: predictia log10(RTT)")
    print("=" * 64)

    X = df[["severitate", "log_payload"]].values
    y = df["log_rtt"].values

    # split train/test reproductibil
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
    )

    model = Ridge(alpha=RIDGE_LAMBDA).fit(X_tr, y_tr)

    r2_tr = r2_score(y_tr, model.predict(X_tr))
    r2_te = r2_score(y_te, model.predict(X_te))
    cv    = cross_val_score(Ridge(alpha=RIDGE_LAMBDA), X, y, cv=CV_FOLDS, scoring="r2")

    b  = model.intercept_
    a1, a2 = model.coef_

    print(f"  Model:  log10(RTT) = {b:.2f} + {a1:.2f}*severitate + {a2:.2f}*log10(payload)")
    print(f"  R2 train       = {r2_tr:.3f}")
    print(f"  R2 TEST        = {r2_te:.3f}   <- cifra principala din prezentare")
    print(f"  R2 CV {CV_FOLDS}-fold   = {cv.mean():.3f} +/- {cv.std():.3f}")
    print(f"  Interpretare   : +1 nivel severitate => RTT x{10**a1:.0f}")

    # CSV cu predictii (pe tot setul, marcand train/test)
    df_out = df.copy()
    df_out["log_rtt_prezis"] = model.predict(X)
    df_out["rtt_prezis_ms"]  = 10 ** df_out["log_rtt_prezis"]
    df_out[["cond", "payload", "rtt_p95_ms", "log_rtt",
            "log_rtt_prezis", "rtt_prezis_ms"]].to_csv(
        os.path.join(OUTDIR, "predictii_regresie.csv"), index=False)
    print(f"  [salvat] {os.path.join(OUTDIR, 'predictii_regresie.csv')}")

    # ---- FIGURA A: setul de date (severitate vs log10 RTT, colorat pe payload) ----
    fig, ax = plt.subplots(figsize=(5.8, 4.2))
    rng = np.random.RandomState(3)
    jit = df["severitate"] + rng.uniform(-0.13, 0.13, len(df))
    for pv, lab, col in [(np.log10(64), "64 B", NAVY),
                         (np.log10(4096), "4 KB", TEAL),
                         (np.log10(65536), "64 KB", GOLD)]:
        m = np.abs(df["log_payload"] - pv) < 0.01
        ax.scatter(jit[m], df["log_rtt"][m], s=50, alpha=0.7, color=col,
                   label=f"sarcina utila {lab}", edgecolors="white", linewidth=0.6)
    ax.set_xlabel("severitatea retelei (0 = ideal ... 3 = sever)", fontsize=11)
    ax.set_ylabel("log10(RTT p95 [ms])", fontsize=11)
    ax.set_title("Set de date PDIA: log10(RTT p95) vs severitatea retelei", fontsize=12)
    ax.set_xticks([0, 1, 2, 3]); ax.legend(fontsize=9)
    ax.grid(linestyle=":", linewidth=0.5, alpha=0.6); ax.set_axisbelow(True)
    _savefig(fig, "figA_dataset",
             f"SIL (loopback); {len(df)} masuratori (ml_dataset.csv); "
             "severitate ordinala din conditia netem.")

    # ---- FIGURA B: predictie vs masuratoare ----
    fig, ax = plt.subplots(figsize=(5.8, 4.2))
    ax.scatter(y_tr, model.predict(X_tr), c=GRAY, s=40, alpha=0.55,
               label=f"train (R2={r2_tr:.2f})", edgecolors="white", linewidth=0.5)
    ax.scatter(y_te, model.predict(X_te), c=GOLD, s=58, alpha=0.9, marker="D",
               label=f"test (R2={r2_te:.2f})", edgecolors=NAVY, linewidth=0.7)
    lims = [-0.2, 4.5]
    ax.plot(lims, lims, "--", c=NAVY, lw=1.3, label="predictie perfecta")
    ax.set_xlabel("log10(RTT p95) masurat", fontsize=11)
    ax.set_ylabel("log10(RTT p95) prezis", fontsize=11)
    ax.set_title("Regresie Ridge: predictie vs masuratoare (train/test)", fontsize=12)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(linestyle=":", linewidth=0.5, alpha=0.6); ax.set_axisbelow(True)
    ax.set_xlim(lims); ax.set_ylim(lims)
    _savefig(fig, "figB_regresie",
             f"SIL (loopback); regresie Ridge (lambda={RIDGE_LAMBDA:.0f}); "
             f"split {int((1-TEST_SIZE)*100)}/{int(TEST_SIZE*100)} (seed {RANDOM_STATE}); "
             f"R2 test={r2_te:.2f}.")

    return model


def studiu2_clasificare(df):
    """
    CLASIFICARE (link utilizabil pentru SAR).
    Eticheta: 1 daca RTT p95 < 500ms (utilizabil), 0 altfel (degradat).
    Model: regresie logistica pe (severitate, log10 payload).
    """
    print("\n" + "=" * 64)
    print("STUDIUL 2 - CLASIFICARE: link utilizabil (RTT < 500ms)")
    print("=" * 64)

    X = df[["severitate", "log_payload"]].values
    y = (df["rtt_p95_ms"].values < PRAG_SAR_MS).astype(int)  # 1 = utilizabil

    n_util = int(y.sum()); n_degr = len(y) - n_util
    print(f"  Clase: utilizabil={n_util}  degradat={n_degr}  (echilibrate)")

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )

    clf = LogisticRegression().fit(X_tr, y_tr)

    acc_tr = accuracy_score(y_tr, clf.predict(X_tr))
    acc_te = accuracy_score(y_te, clf.predict(X_te))
    cv     = cross_val_score(LogisticRegression(), X, y, cv=CV_FOLDS)
    cm     = confusion_matrix(y_te, clf.predict(X_te))

    print(f"  Acuratete train = {acc_tr:.3f}")
    print(f"  Acuratete TEST  = {acc_te:.3f}   <- cifra principala din prezentare")
    print(f"  Acuratete CV    = {cv.mean():.3f} +/- {cv.std():.3f}")
    print(f"  Matrice confuzie (test):")
    print(f"      real\\prezis   degradat  utilizabil")
    print(f"      degradat        {cm[0,0]:3d}       {cm[0,1]:3d}")
    print(f"      utilizabil      {cm[1,0]:3d}       {cm[1,1]:3d}")
    print(f"  Corecte: {cm[0,0]+cm[1,1]} din {cm.sum()}")
    print(f"  Coeficienti: severitate={clf.coef_[0][0]:.2f}  "
          f"log_payload={clf.coef_[0][1]:.2f}  (negativ => scade P(utilizabil))")

    # CSV cu predictii + probabilitati
    df_out = df.copy()
    df_out["eticheta_reala"] = y
    df_out["prezis"]         = clf.predict(X)
    df_out["P_utilizabil"]   = clf.predict_proba(X)[:, 1]
    df_out[["cond", "payload", "rtt_p95_ms",
            "eticheta_reala", "prezis", "P_utilizabil"]].to_csv(
        os.path.join(OUTDIR, "predictii_clasificare.csv"), index=False)
    print(f"  [salvat] {os.path.join(OUTDIR, 'predictii_clasificare.csv')}")

    # ---- FIGURA C: frontiera de decizie ----
    fig, ax = plt.subplots(figsize=(5.8, 4.2))
    xx, yy = np.meshgrid(np.linspace(-0.4, 3.4, 250), np.linspace(1.5, 5.0, 250))
    Z = clf.predict(np.c_[xx.ravel(), yy.ravel()]).reshape(xx.shape)
    ax.contourf(xx, yy, Z, alpha=0.12, colors=[RED, TEAL], levels=[-0.5, 0.5, 1.5])
    rng = np.random.RandomState(7)
    jit = df["severitate"] + rng.uniform(-0.12, 0.12, len(df))
    m1 = y == 1; m0 = y == 0
    ax.scatter(jit[m1], df["log_payload"][m1], c=TEAL, s=45, alpha=0.75,
               label="utilizabil (RTT < 500 ms)", edgecolors="white", linewidth=0.5)
    ax.scatter(jit[m0], df["log_payload"][m0], c=RED, s=45, alpha=0.75, marker="X",
               label="degradat (RTT >= 500 ms)", edgecolors="white", linewidth=0.5)
    ax.set_xlabel("severitatea retelei", fontsize=11)
    ax.set_ylabel("log10(sarcina utila [B])", fontsize=11)
    ax.set_title("Clasificare 'link utilizabil': frontiera de decizie", fontsize=12)
    ax.set_xticks([0, 1, 2, 3]); ax.legend(fontsize=8.5, loc="lower left")
    ax.grid(linestyle=":", linewidth=0.5, alpha=0.6); ax.set_axisbelow(True)
    _savefig(fig, "figC_frontiera",
             f"SIL (loopback); regresie logistica; prag link utilizabil RTT < {PRAG_SAR_MS:.0f} ms; "
             f"acuratete test {acc_te:.0%}.")

    return clf


def main():
    print("Reproducere analiza PDIA - regresie + clasificare pe date reale")
    os.makedirs(OUTDIR, exist_ok=True)
    df = incarca_date(CSV_PATH)
    print(f"Incarcate {len(df)} masuratori din '{CSV_PATH}'.")

    # rezumat pe severitate (tabelul de pe slide 5)
    print("\nRezumat RTT p95 mediu pe nivel de severitate:")
    rez = df.groupby("severitate")["rtt_p95_ms"].agg(["mean", "count"])
    for sev, row in rez.iterrows():
        print(f"  severitate {sev}: RTT mediu = {row['mean']:7.0f} ms   (n={int(row['count'])})")

    studiu1_regresie(df)
    studiu2_clasificare(df)

    print("\n" + "=" * 64)
    print(f"GATA. Fisiere regenerate in {OUTDIR}:")
    print("  figuri:    figA_dataset, figB_regresie, figC_frontiera (.png + .pdf)")
    print("  predictii: predictii_regresie.csv, predictii_clasificare.csv")
    print("=" * 64)


if __name__ == "__main__":
    main()
