#!/usr/bin/env python3
"""metrici_calibrare_core.py -- nucleul M09, numpy pur (scikit-learn INTERZIS).

Metrici pentru clasificare cu clase DEZECHILIBRATE si calibrare de probabilitati,
toate de la zero:
  - roc_auc(y, scor): aria sub curba ROC (TPR vs FPR) prin ranguri (statistica
    Mann-Whitney U), echivalenta cu regula trapezului pe punctele ROC;
  - roc_curve / pr_curve: TPR-FPR si precizie-recall vs prag;
  - alegerea pragului: dupa F1 maxim sau dupa un recall-tinta (cel mai mare prag
    care inca atinge recall-ul cerut);
  - calibrare: curba de fiabilitate pe bin-uri (probabilitate medie vs frecventa
    reala) + scalare Platt (o regresie logistica 1D pe scoruri, antrenata cu
    gradient determinist).

Metricele de baza (precizie/recall/F1, matrice de confuzie, acuratete) vin din
utils (SURSA UNICA). Aici stau doar lucrurile noi ale modulului.

Determinism: orice aleator trece prin numpy.random.default_rng(seed).
_selftest() verifica:
  - AUC al unui clasificator PERFECT = 1.0, al unuia ALEATOR ~ 0.5 (toleranta);
  - precizie/recall pe caz cunoscut (acelasi numar ca exemplul din teorie.md);
  - alegerea pragului pe recall-tinta CRESTE recall-ul fata de pragul 0.5;
  - dupa calibrare Platt, probabilitatea medie pe bin ~ frecventa reala (calibrare
    mai buna decat scorurile brute necalibrate);
  - AUC pe 3-4 scoruri (exemplul numeric din teorie.md) = valoarea calculata de mana.

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python metrici_calibrare_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import precision_recall_f1, confusion_matrix  # noqa: E402


# ============================================================ ROC / AUC
def roc_auc(y_true, scores):
    """Aria sub curba ROC prin ranguri (statistica Mann-Whitney U).

    AUC = P(scor(pozitiv) > scor(negativ)), estimata ca fractia de perechi
    (pozitiv, negativ) in care pozitivul are scor mai mare; egalitatile conteaza
    cu 0.5. Echivalenta cu trapezul pe punctele ROC, dar numeric stabila si fara
    sa depinda de alegerea pragurilor. Fara o clasa -> intoarce 0.5 (nedefinit)."""
    y = np.asarray(y_true).astype(int).reshape(-1)
    s = np.asarray(scores, dtype=float).reshape(-1)
    pos = s[y == 1]
    neg = s[y == 0]
    n_pos, n_neg = pos.size, neg.size
    if n_pos == 0 or n_neg == 0:
        return 0.5
    # rangurile mediaza egalitatile; U = sum_ranguri_pozitivi - n_pos*(n_pos+1)/2
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(s.size, dtype=float)
    s_sorted = s[order]
    i = 0
    n = s.size
    while i < n:
        j = i
        while j < n and s_sorted[j] == s_sorted[i]:
            j += 1
        avg_rank = 0.5 * (i + j - 1) + 1.0  # ranguri 1..n, mediate pe egalitati
        ranks[order[i:j]] = avg_rank
        i = j
    sum_rank_pos = ranks[y == 1].sum()
    u_pos = sum_rank_pos - n_pos * (n_pos + 1) / 2.0
    return float(u_pos / (n_pos * n_neg))


def roc_curve(y_true, scores):
    """Puncte ale curbei ROC (FPR, TPR) la praguri descrescatoare.

    Returneaza (fpr, tpr, thresholds), cu (0,0) la inceput. Pragul scade -> se
    declara tot mai multe pozitive -> TPR si FPR cresc monoton catre (1,1)."""
    y = np.asarray(y_true).astype(int).reshape(-1)
    s = np.asarray(scores, dtype=float).reshape(-1)
    n_pos = int((y == 1).sum())
    n_neg = int((y == 0).sum())
    if n_pos == 0 or n_neg == 0:
        raise ValueError("roc_curve are nevoie de ambele clase prezente")
    order = np.argsort(-s, kind="mergesort")  # scor descrescator
    y_sorted = y[order]
    s_sorted = s[order]
    tps = np.cumsum(y_sorted == 1)
    fps = np.cumsum(y_sorted == 0)
    # pastram doar capatul fiecarui grup de scoruri egale (praguri distincte)
    distinct = np.r_[np.where(np.diff(s_sorted) != 0)[0], s.size - 1]
    tpr = np.r_[0.0, tps[distinct] / n_pos]
    fpr = np.r_[0.0, fps[distinct] / n_neg]
    thr = np.r_[np.inf, s_sorted[distinct]]
    return fpr, tpr, thr


def auc_trapezoid(fpr, tpr):
    """Aria sub o curba (TPR vs FPR) prin regula trapezului. fpr trebuie crescator."""
    fpr = np.asarray(fpr, dtype=float)
    tpr = np.asarray(tpr, dtype=float)
    return float(np.trapezoid(tpr, fpr))


# ============================================================ PRECIZIE-RECALL
def pr_curve(y_true, scores):
    """Puncte ale curbei precizie-recall la praguri descrescatoare.

    Returneaza (precision, recall, thresholds) aliniate: pentru fiecare prag
    distinct, predictia este (scor >= prag). Recall creste cu pragul in scadere;
    precizia oscileaza (de aici 'dinte de fierastrau')."""
    y = np.asarray(y_true).astype(int).reshape(-1)
    s = np.asarray(scores, dtype=float).reshape(-1)
    n_pos = int((y == 1).sum())
    if n_pos == 0:
        raise ValueError("pr_curve are nevoie de cel putin un pozitiv")
    order = np.argsort(-s, kind="mergesort")
    y_sorted = y[order]
    s_sorted = s[order]
    tps = np.cumsum(y_sorted == 1)
    fps = np.cumsum(y_sorted == 0)
    distinct = np.r_[np.where(np.diff(s_sorted) != 0)[0], s.size - 1]
    tp = tps[distinct]
    fp = fps[distinct]
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / n_pos
    thr = s_sorted[distinct]
    return precision, recall, thr


def average_precision(y_true, scores):
    """Precizie medie = aria sub curba PR, suma ponderata cu cresterea recall-ului.

    AP = sum_k (R_k - R_{k-1}) * P_k. Rezumat scalar al curbei PR, recomandat la
    dezechilibru in locul AUC-ROC cand clasa rara e cea care conteaza."""
    precision, recall, _ = pr_curve(y_true, scores)
    r_prev = 0.0
    ap = 0.0
    for p, r in zip(precision, recall):
        ap += (r - r_prev) * p
        r_prev = r
    return float(ap)


# ============================================================ ALEGEREA PRAGULUI
def best_threshold_f1(y_true, scores):
    """Pragul care maximizeaza F1 al clasei pozitive. Returneaza (prag, f1)."""
    y = np.asarray(y_true).astype(int).reshape(-1)
    s = np.asarray(scores, dtype=float).reshape(-1)
    cand = np.unique(s)
    best_thr, best_f1 = float(cand[0]), -1.0
    for t in cand:
        _, _, f1 = precision_recall_f1(y, (s >= t).astype(int))
        if f1 > best_f1:
            best_f1, best_thr = f1, float(t)
    return best_thr, float(best_f1)


def threshold_for_recall(y_true, scores, target_recall):
    """Cel mai MARE prag care inca atinge recall >= target_recall.

    La dezechilibru, pragul implicit 0.5 rateaza clasa rara; coboram pragul exact
    cat e nevoie ca sa prindem o fractie ceruta din pozitive, fara sa coboram mai
    mult decat trebuie (ca sa nu umflam fals-pozitivele). Returneaza (prag, recall)."""
    y = np.asarray(y_true).astype(int).reshape(-1)
    s = np.asarray(scores, dtype=float).reshape(-1)
    cand = np.unique(s)[::-1]  # de la mare la mic
    chosen = float(cand[-1])
    chosen_rec = 1.0
    for t in cand:
        _, rec, _ = precision_recall_f1(y, (s >= t).astype(int))
        if rec >= target_recall:
            return float(t), float(rec)
        chosen, chosen_rec = float(t), float(rec)
    return chosen, chosen_rec


# ============================================================ CALIBRARE
def reliability_curve(y_true, prob, n_bins=10):
    """Curba de fiabilitate (calibrare): probabilitate medie vs frecventa reala.

    Imparte [0,1] in n_bins egale; pentru fiecare bin returneaza (prob_medie,
    frac_pozitivi, numar). Un model bine calibrat sta pe diagonala. Bin-urile
    goale sunt sarite. Returneaza (mean_prob, frac_pos, counts)."""
    y = np.asarray(y_true).astype(int).reshape(-1)
    p = np.asarray(prob, dtype=float).reshape(-1)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1], right=False), 0, n_bins - 1)
    mean_prob, frac_pos, counts = [], [], []
    for b in range(n_bins):
        m = idx == b
        c = int(m.sum())
        if c == 0:
            continue
        mean_prob.append(float(p[m].mean()))
        frac_pos.append(float(y[m].mean()))
        counts.append(c)
    return np.array(mean_prob), np.array(frac_pos), np.array(counts)


def expected_calibration_error(y_true, prob, n_bins=10):
    """Eroarea de calibrare asteptata (ECE): media ponderata |prob - frecventa|.

    0 = perfect calibrat. Rezumatul scalar al curbei de fiabilitate."""
    y = np.asarray(y_true).astype(int).reshape(-1)
    p = np.asarray(prob, dtype=float).reshape(-1)
    mean_prob, frac_pos, counts = reliability_curve(y, p, n_bins=n_bins)
    if counts.sum() == 0:
        return 0.0
    w = counts / counts.sum()
    return float(np.sum(w * np.abs(mean_prob - frac_pos)))


def platt_fit(scores, y_true, lr=0.1, n_iter=2000, seed=0):
    """Scalare Platt: regresie logistica 1D care mapeaza scoruri -> probabilitati.

    Invata a, b in sigmoid(a*scor + b) prin gradient descendent determinist pe
    log-pierdere. Standardizam scorul intern (medie/abatere) pentru conditionare
    buna; intoarcem un dict cu parametrii in spatiul scorului brut.
    Returneaza dict(a, b)."""
    s = np.asarray(scores, dtype=float).reshape(-1)
    y = np.asarray(y_true, dtype=float).reshape(-1)
    mu, sd = s.mean(), s.std()
    sd = sd if sd > 1e-12 else 1.0
    z = (s - mu) / sd
    rng = np.random.default_rng(seed)
    a = float(rng.normal(0, 0.01))
    b = 0.0
    n = z.size
    for _ in range(n_iter):
        p = 1.0 / (1.0 + np.exp(-(a * z + b)))
        err = p - y
        ga = float(np.mean(err * z))
        gb = float(np.mean(err))
        a -= lr * ga
        b -= lr * gb
    # readucem in spatiul scorului brut: a*z+b = (a/sd)*s + (b - a*mu/sd)
    return dict(a=a / sd, b=b - a * mu / sd)


def platt_predict(scores, params):
    """Aplica scalarea Platt: sigmoid(a*scor + b) -> probabilitate calibrata."""
    s = np.asarray(scores, dtype=float).reshape(-1)
    z = params["a"] * s + params["b"]
    return 1.0 / (1.0 + np.exp(-z))


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    rng = np.random.default_rng(0)

    # --- AUC: clasificator PERFECT = 1.0 ---------------------------------
    y = np.r_[np.zeros(50), np.ones(50)].astype(int)
    s_perfect = np.r_[rng.uniform(0.0, 0.4, 50), rng.uniform(0.6, 1.0, 50)]
    ck("AUC clasificator perfect = 1.0", abs(roc_auc(y, s_perfect) - 1.0) < 1e-9)

    # --- AUC: clasificator ALEATOR ~ 0.5 (toleranta) ---------------------
    s_random = rng.uniform(0.0, 1.0, 100)
    auc_rand = roc_auc(y, s_random)
    ck("AUC clasificator aleator ~ 0.5 (+-0.12)", abs(auc_rand - 0.5) < 0.12)

    # --- AUC == trapez pe curba ROC --------------------------------------
    fpr, tpr, _ = roc_curve(y, s_perfect)
    ck("AUC ranguri ~ AUC trapez (perfect)",
       abs(roc_auc(y, s_perfect) - auc_trapezoid(fpr, tpr)) < 1e-9)
    fpr2, tpr2, _ = roc_curve(y, s_random)
    ck("AUC ranguri ~ AUC trapez (aleator)",
       abs(roc_auc(y, s_random) - auc_trapezoid(fpr2, tpr2)) < 1e-9)

    # --- AUC pe exemplul numeric din teorie.md ---------------------------
    # 4 puncte: pozitivi cu scoruri {0.9, 0.4}, negativi cu scoruri {0.6, 0.3}.
    # perechi (poz, neg): (0.9>0.6)=1, (0.9>0.3)=1, (0.4>0.6)=0, (0.4>0.3)=1 -> 3/4.
    y_ex = np.array([1, 0, 1, 0])
    s_ex = np.array([0.9, 0.6, 0.4, 0.3])
    ck("AUC exemplu numeric = 0.75", abs(roc_auc(y_ex, s_ex) - 0.75) < 1e-12)

    # --- precizie / recall pe caz cunoscut (acelasi ca exemplul din teorie) ---
    # y=[1,1,1,0,0], pred=[1,1,0,1,0]: TP=2, FP=1, FN=1 -> prec=2/3, rec=2/3
    yt = np.array([1, 1, 1, 0, 0])
    yp = np.array([1, 1, 0, 1, 0])
    cm = confusion_matrix(yt, yp)
    ck("confuzie [[TN,FP],[FN,TP]] = [[1,1],[1,2]]", np.array_equal(cm, [[1, 1], [1, 2]]))
    prec, rec, f1 = precision_recall_f1(yt, yp)
    ck("precizie = 2/3", abs(prec - 2.0 / 3.0) < 1e-12)
    ck("recall = 2/3", abs(rec - 2.0 / 3.0) < 1e-12)
    ck("F1 = 2/3", abs(f1 - 2.0 / 3.0) < 1e-12)

    # --- alegerea pragului pe recall-tinta CRESTE recall-ul --------------
    # clase dezechilibrate: pozitivii rari au scoruri ceva mai mari, dar nu mereu > 0.5
    yb = np.r_[np.zeros(180), np.ones(20)].astype(int)
    sb = np.r_[rng.uniform(0.0, 0.7, 180), rng.uniform(0.3, 1.0, 20)]
    _, rec_default, _ = precision_recall_f1(yb, (sb >= 0.5).astype(int))
    thr_rec, rec_at_thr = threshold_for_recall(yb, sb, target_recall=0.9)
    ck("prag pe recall: recall obtinut >= 0.9", rec_at_thr >= 0.9 - 1e-9)
    ck("prag pe recall: recall creste fata de pragul 0.5", rec_at_thr > rec_default)
    ck("prag pe recall: pragul ales <= 0.5 (coboram ca sa prindem rarii)",
       thr_rec <= 0.5 + 1e-9)

    # --- best_threshold_f1 alege un prag rezonabil -----------------------
    thr_f1, f1_val = best_threshold_f1(y, s_perfect)
    ck("best_threshold_f1: F1 perfect = 1.0 pe clasificatorul perfect", abs(f1_val - 1.0) < 1e-9)

    # --- precizie medie (AP) intre 0 si 1, perfect -> 1.0 ----------------
    ck("AP clasificator perfect = 1.0", abs(average_precision(y, s_perfect) - 1.0) < 1e-9)

    # --- CALIBRARE: dupa Platt, prob medie pe bin ~ frecventa reala ------
    # construim scoruri NECALIBRATE: prob reala p, dar scorul brut e o functie
    # monotona deformata (sigmoida brusca), deci dezacordat fata de frecventa.
    n = 4000
    p_true = rng.uniform(0.05, 0.95, n)
    yc = (rng.uniform(0, 1, n) < p_true).astype(int)
    logit = np.log(p_true / (1.0 - p_true))
    raw = 1.0 / (1.0 + np.exp(-(0.4 * logit - 1.2)))  # scor brut DEFORMAT (sub-increzator)
    ece_raw = expected_calibration_error(yc, raw, n_bins=10)
    params = platt_fit(raw, yc, lr=0.5, n_iter=4000, seed=0)
    cal = platt_predict(raw, params)
    ece_cal = expected_calibration_error(yc, cal, n_bins=10)
    ck("calibrare: ECE dupa Platt < ECE brut", ece_cal < ece_raw)
    ck("calibrare: ECE dupa Platt mic (< 0.05)", ece_cal < 0.05)
    mean_prob, frac_pos, counts = reliability_curve(yc, cal, n_bins=10)
    # pe bin-urile cu suficiente puncte, prob medie ~ frecventa reala
    big = counts >= 50
    ck("calibrare: prob medie pe bin ~ frecventa reala (|d|<0.06)",
       np.all(np.abs(mean_prob[big] - frac_pos[big]) < 0.06))

    print("\nTOATE VERIFICARILE metrici_calibrare_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
