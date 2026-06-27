#!/usr/bin/env python3
"""selector_core.py -- nucleu pur (fara ROS, fara I/O, fara sklearn) pentru SELECTORUL
de middleware din campania C1.

Ridica analiza de la CARACTERIZATOR (reproduce_pdia.py: prezice RTT din severitate +
payload, ARUNCA rmw) la SELECTOR: din parametrii de retea + payload, ALEGE rmw-ul care
minimizeaza obiectivul. Obiective: CONTROL = min RTT p95; CONSTIENT DE PIERDERE = min cost
asteptat (un esantion livrat costa RTT p95; unul pierdut costa un deadline D de control).

Fisier-FRATE; NU atinge reproduce_pdia.py si figurile PDIA.

Limitari de date (verificate in ml_dataset.csv, vezi reproduce_selector.py):
- loss_pct == 0 si sent == recv pe TOATE randurile: setul masoara doar RTT sub livrare
  fiabila; pierderea netem apare ca latenta, nu ca esantioane pierdute. Deci feature-ul
  'loss %' provine din PARSAREA conditiei (numele netem), nu din coloana loss_pct.
- nu exista coloana de timp de misiune: obiectivul 'telemetrie = min timp misiune' NU se
  poate construi din acest set (necesita join cu date de misiune sar_swarm).

Metodologie: nucleu pur + test_selector_core.py. Validarea e leave-one-condition-out
(LOCO), NU split aleator: repetitiile aceleiasi (cond x payload) ar scurge informatie
intre train si test si ar da scoruri optimist umflate.
"""
import math

RMWS = ("cyclonedds", "zenoh")

# Parametrii netem REALI codati in numele conditiei: (loss %, latenta ms, jitter ms).
COND_NETEM = {
    "ideal":         (0.0,   0.0,  0.0),
    "loss_5":        (5.0,   0.0,  0.0),
    "loss_15":       (15.0,  0.0,  0.0),
    "loss_20":       (20.0,  0.0,  0.0),
    "loss_25":       (25.0,  0.0,  0.0),
    "loss_30":       (30.0,  0.0,  0.0),
    # variante CORELATE (rafale): aceeasi (loss, lat, jit), dar le distinge feature-ul
    # mean_burst_len (vezi COND_BURST). gilbert_* = sweep sintetic (rf_interference.BurstProcess).
    "loss_20_burst": (20.0,  0.0,  0.0),
    "loss_25_burst": (25.0,  0.0,  0.0),
    "loss_30_burst": (30.0,  0.0,  0.0),
    "gilbert_20":    (20.0,  0.0,  0.0),
    "gilbert_25":    (25.0,  0.0,  0.0),
    "gilbert_30":    (30.0,  0.0,  0.0),
    "lat200_jit50":  (0.0, 200.0, 50.0),
    "lat200_l15":    (15.0, 200.0,  0.0),
}

# Lungimea medie a rafalei de pierderi per conditie (feature de BURSTINESS). Default 1.0 =
# pierdere INDEPENDENTA. Corelate: gilbert_* (sweep sintetic) + vechile *_burst (netem corr).
COND_BURST = {
    "gilbert_20": 5.0, "gilbert_25": 5.0, "gilbert_30": 5.0,
    "loss_20_burst": 2.0, "loss_25_burst": 2.0, "loss_30_burst": 2.0,
}


def parse_cond(cond):
    """Intoarce (loss_pct, lat_ms, jit_ms) pentru o conditie cunoscuta."""
    if cond not in COND_NETEM:
        raise ValueError("conditie necunoscuta: %r" % (cond,))
    return COND_NETEM[cond]


def cell_features(cond, payload):
    """Vectorul de feature-uri: [loss, lat, jit, log10(payload), mean_burst_len].

    mean_burst_len (lungimea medie a rafalei de pierderi; 1.0 = independent) distinge conditiile
    corelate (gilbert_*, *_burst) de pierderea independenta -- inchide TODO-ul de burstiness al
    selectorului (conditiile cu aceeasi loss/lat/jit nu mai sunt indistinctibile)."""
    loss, lat, jit = parse_cond(cond)
    return [loss, lat, jit, math.log10(float(payload)), COND_BURST.get(cond, 1.0)]


def median(xs):
    s = sorted(xs)
    n = len(s)
    if n == 0:
        raise ValueError("median pe lista goala")
    m = n // 2
    return s[m] if n % 2 else 0.5 * (s[m - 1] + s[m])


def build_cells(rows, metric="rtt_p95_ms", agg=median):
    """rows: iterabil de dict cu chei cond, payload, rmw, <metric>.

    Intoarce {(cond, payload): {rmw: valoare_agregata}} -- mediana peste repetitii.
    """
    acc = {}
    for r in rows:
        key = (r["cond"], int(r["payload"]))
        acc.setdefault(key, {}).setdefault(r["rmw"], []).append(float(r[metric]))
    return {k: {rmw: agg(v) for rmw, v in d.items()} for k, d in acc.items()}


def cell_winner(cell):
    """rmw cu metrica minima (obiectiv control = min RTT p95). Tie -> ordine RMWS."""
    best = min(cell.values())
    for rmw in RMWS:
        if rmw in cell and cell[rmw] == best:
            return rmw
    return min(cell, key=cell.get)


def regret(choice, cell):
    """Penalizarea (in unitatea metricii, ex. ms) a alegerii fata de oracol (min)."""
    return cell[choice] - min(cell.values())


def loss_aware_cost(rtt_p95, loss_frac, penalty_ms):
    """Cost CONSTIENT DE PIERDERE pentru un (cond, payload, rmw).

    Model de control: fiecare esantion fie soseste (cost = RTT p95 al cozii), fie e
    pierdut (cost = penalty_ms, un deadline/stall). Costul ASTEPTAT pe esantion:
        (1 - loss_frac) * rtt_p95 + loss_frac * penalty_ms
    La loss_frac = 0 colapseaza la RTT p95 (== obiectivul control). penalty_ms reprezinta
    deadline-ul de control si ar trebui ales >= cozile RTT, ca obiectivul sa fie monoton
    crescator in pierdere (un drop = mai rau decat o livrare lenta).
    """
    return (1.0 - loss_frac) * rtt_p95 + loss_frac * penalty_ms


def build_cost_cells(rows, penalty_ms, rtt_metric="rtt_p95_ms", loss_metric="loss_pct", agg=median):
    """Ca build_cells, dar cu obiectiv CONSTIENT DE PIERDERE.

    Agrega median(RTT p95) si median(loss %) peste repetitii per (cond, payload, rmw),
    apoi cost = loss_aware_cost(med_rtt, med_loss/100, penalty_ms). Intoarce
    {(cond, payload): {rmw: cost}} -- aceeasi forma ca build_cells, deci cell_winner /
    regret / loco_folds / evaluate_selector / nn_predict merg neatins pe rezultat.
    """
    rtt_acc, loss_acc = {}, {}
    for r in rows:
        key = (r["cond"], int(r["payload"]), r["rmw"])
        rtt_acc.setdefault(key, []).append(float(r[rtt_metric]))
        loss_acc.setdefault(key, []).append(float(r[loss_metric]))
    cells = {}
    for key, rtts in rtt_acc.items():
        cond, pl, rmw = key
        loss_frac = agg(loss_acc[key]) / 100.0
        cells.setdefault((cond, pl), {})[rmw] = loss_aware_cost(agg(rtts), loss_frac, penalty_ms)
    return cells


def build_mission_cells(rows, ref_payload=4096, metric="mission_time_s"):
    """Celule pentru obiectivul TELEMETRIE (min timp de misiune).

    rows = dict-uri tip campaign_summary.csv (chei: rmw, condition, <metric>).
    Misiunea e payload-agnostica -> o cheie per conditie, la payload-ul de referinta
    (feature inert), ca masinaria de selector (cell_winner / regret / loco_folds /
    evaluate_selector / nn_predict) sa mearga neatins. Randurile cu <metric> gol
    (misiune neterminata / cenzurata) sunt sarite -- apelantul le raporteaza.
    """
    cells = {}
    for r in rows:
        v = r.get(metric, "")
        if v in ("", None):
            continue
        cells.setdefault((r["condition"], ref_payload), {})[r["rmw"]] = float(v)
    return cells


def loco_folds(keys):
    """Leave-one-condition-out: pentru fiecare conditie, (chei_train, chei_test).

    keys = iterabil de (cond, payload). Testul = toate celulele unei conditii.
    """
    conds = []
    for cond, _pl in keys:
        if cond not in conds:
            conds.append(cond)
    out = []
    for held in conds:
        test = [k for k in keys if k[0] == held]
        train = [k for k in keys if k[0] != held]
        out.append((held, train, test))
    return out


# ---- selector transparent, fara dependinte: 1-NN pe feature-uri standardizate ----

def _standardizer(train_feats):
    """Intoarce (mean, std) pe coloane, std=1 unde varianta e 0 (feature constant)."""
    n = len(train_feats)
    d = len(train_feats[0])
    mean = [sum(f[j] for f in train_feats) / n for j in range(d)]
    std = []
    for j in range(d):
        var = sum((f[j] - mean[j]) ** 2 for f in train_feats) / n
        std.append(math.sqrt(var) if var > 1e-12 else 1.0)
    return mean, std


def _z(feat, mean, std):
    return [(feat[j] - mean[j]) / std[j] for j in range(len(feat))]


def nn_predict(train_feats, train_labels, query):
    """1-NN euclidian pe feature-uri standardizate (determinist).

    train_feats: lista de vectori; train_labels: rmw castigator per celula de train;
    query: vectorul celulei de test. La egalitate de distanta, prima aparitie.
    """
    mean, std = _standardizer(train_feats)
    q = _z(query, mean, std)
    best_i, best_d = 0, float("inf")
    for i, f in enumerate(train_feats):
        zf = _z(f, mean, std)
        dist = sum((zf[j] - q[j]) ** 2 for j in range(len(q)))
        if dist < best_d:
            best_d, best_i = dist, i
    return train_labels[best_i]


def evaluate_selector(cells, predict_fn):
    """Ruleaza LOCO si intoarce metrici pentru selector + baseline-uri.

    cells: {(cond,payload): {rmw: metrica}}.
    predict_fn(train_feats, train_labels, query_feats) -> rmw prezis.
    Intoarce dict cu: accuracy (selector), regret total/mediu pentru
    selector / always-<rmw> / oracle.
    """
    keys = list(cells.keys())
    n = len(keys)
    correct = 0
    sel_regret = 0.0
    per_cell = []
    for _held, train, test in loco_folds(keys):
        tf = [cell_features(*k) for k in train]
        tl = [cell_winner(cells[k]) for k in train]
        for k in test:
            pred = predict_fn(tf, tl, cell_features(*k))
            true = cell_winner(cells[k])
            r = regret(pred, cells[k])
            sel_regret += r
            correct += (pred == true)
            per_cell.append((k, pred, true, r))

    out = {
        "n_cells": n,
        "accuracy": correct / n if n else 0.0,
        "selector_regret_total": sel_regret,
        "selector_regret_mean": sel_regret / n if n else 0.0,
        "oracle_regret_total": 0.0,
        "per_cell": per_cell,
    }
    for rmw in RMWS:
        tot = sum(regret(rmw, cells[k]) for k in keys if rmw in cells[k])
        out["always_%s_regret_total" % rmw] = tot
        out["always_%s_regret_mean" % rmw] = tot / n if n else 0.0
    return out


def sweep_deadline(rows, penalties, predict_fn=None):
    """Sweep FIN pe deadline-ul de control D (obiectiv loss-aware). Pentru fiecare D din penalties,
    regretul mediu (cost ms; oracol = 0) al always-cyclonedds, always-zenoh si al selectorului LOCO.
    Gaseste d_star = primul D la care regretul selectorului devine <= always-cyclonedds (incrucisarea
    DEPENDENTEI DE DEADLINE). PUR -- orchestreaza build_cost_cells + evaluate_selector; predict_fn
    implicit = nn_predict (1-NN transparent)."""
    predict_fn = predict_fn or nn_predict
    curve = []
    d_star = None
    for D in penalties:
        cells = build_cost_cells(rows, float(D))
        res = evaluate_selector(cells, predict_fn)
        point = {"D": float(D),
                 "always_cyclonedds": res["always_cyclonedds_regret_mean"],
                 "always_zenoh": res["always_zenoh_regret_mean"],
                 "selector": res["selector_regret_mean"]}
        curve.append(point)
        if d_star is None and point["selector"] <= point["always_cyclonedds"]:
            d_star = float(D)
    return {"curve": curve, "d_star": d_star}


def _selftest():
    """Verificari pure, fara I/O. Apelat din test_selector_core.py si din __main__."""
    assert parse_cond("ideal") == (0.0, 0.0, 0.0)
    assert parse_cond("lat200_l15") == (15.0, 200.0, 0.0)
    try:
        parse_cond("inexistent")
        raise AssertionError("ar fi trebuit ValueError")
    except ValueError:
        pass
    assert cell_features("loss_30", 4096)[0] == 30.0
    assert abs(cell_features("loss_30", 100)[3] - 2.0) < 1e-9

    assert median([3, 1, 2]) == 2
    assert median([1, 2, 3, 4]) == 2.5

    rows = [
        {"cond": "ideal", "payload": "64", "rmw": "cyclonedds", "rtt_p95_ms": "1.0"},
        {"cond": "ideal", "payload": "64", "rmw": "cyclonedds", "rtt_p95_ms": "2.0"},
        {"cond": "ideal", "payload": "64", "rmw": "zenoh", "rtt_p95_ms": "5.0"},
    ]
    cells = build_cells(rows)
    assert cells[("ideal", 64)]["cyclonedds"] == 1.5
    assert cell_winner(cells[("ideal", 64)]) == "cyclonedds"
    assert regret("cyclonedds", cells[("ideal", 64)]) == 0.0
    assert regret("zenoh", cells[("ideal", 64)]) == 3.5

    # winner flip: cyclone castiga la payload mic, zenoh la payload mare
    cflip = {
        ("loss_15", 64): {"cyclonedds": 1.0, "zenoh": 2.0},
        ("loss_15", 65536): {"cyclonedds": 9.0, "zenoh": 3.0},
        ("loss_30", 64): {"cyclonedds": 1.0, "zenoh": 5.0},
        ("loss_30", 65536): {"cyclonedds": 9.0, "zenoh": 4.0},
    }
    folds = loco_folds(list(cflip.keys()))
    assert len(folds) == 2  # doua conditii
    for _h, train, test in folds:
        assert len({k[0] for k in test}) == 1  # testul = o singura conditie
        assert all(k[0] != _h for k in train)

    res = evaluate_selector(cflip, nn_predict)
    assert res["n_cells"] == 4
    assert res["oracle_regret_total"] == 0.0
    # always-cyclonedds plateste regret pe celulele de payload mare (zenoh castiga)
    assert res["always_cyclonedds_regret_total"] > 0.0
    assert res["always_zenoh_regret_total"] > 0.0
    # selectorul nu poate fi mai bun decat oracolul
    assert res["selector_regret_total"] >= 0.0
    assert 0.0 <= res["accuracy"] <= 1.0

    # obiectiv constient de pierdere: cost asteptat cu deadline
    assert loss_aware_cost(100.0, 0.0, 1000.0) == 100.0       # loss=0 -> pur RTT (== control)
    assert loss_aware_cost(10.0, 1.0, 1000.0) == 1000.0       # pierdere totala -> deadline
    assert loss_aware_cost(100.0, 0.2, 1000.0) == 280.0       # 0.8*100 + 0.2*1000
    lossrows = [
        {"cond": "loss_30", "payload": "64", "rmw": "cyclonedds", "rtt_p95_ms": "100", "loss_pct": "20"},
        {"cond": "loss_30", "payload": "64", "rmw": "zenoh", "rtt_p95_ms": "10", "loss_pct": "60"},
    ]
    # control (min RTT): zenoh castiga (10 < 100), ignorand ca pierde 60%
    assert cell_winner(build_cells(lossrows)[("loss_30", 64)]) == "zenoh"
    # loss-aware (D=1000): cyclonedds castiga (280 < 604) -- winner-ul se INVERSEAZA
    assert cell_winner(build_cost_cells(lossrows, 1000.0)[("loss_30", 64)]) == "cyclonedds"

    # obiectiv telemetrie (min timp de misiune) din randuri tip campaign_summary
    srows = [
        {"rmw": "cyclonedds", "condition": "loss_30", "mission_time_s": "120"},
        {"rmw": "zenoh", "condition": "loss_30", "mission_time_s": "150"},
        {"rmw": "cyclonedds", "condition": "ideal", "mission_time_s": "100"},
        {"rmw": "zenoh", "condition": "ideal", "mission_time_s": ""},   # cenzurat -> sarit
    ]
    mc = build_mission_cells(srows, ref_payload=4096)
    assert mc[("loss_30", 4096)] == {"cyclonedds": 120.0, "zenoh": 150.0}
    assert cell_winner(mc[("loss_30", 4096)]) == "cyclonedds"          # timp mai mic castiga
    assert "zenoh" not in mc[("ideal", 4096)]                          # randul gol a fost sarit

    # sweep_deadline: cu predictor FIX (mereu cyclonedds), regretul selectorului == always-cyclonedds,
    # deci d_star = primul D din grila (selector <= always-cyclonedds prin egalitate). Orchestrare corecta.
    swrows = [
        {"cond": "loss_15", "payload": "64", "rmw": "cyclonedds", "rtt_p95_ms": "50", "loss_pct": "5"},
        {"cond": "loss_15", "payload": "64", "rmw": "zenoh", "rtt_p95_ms": "40", "loss_pct": "40"},
        {"cond": "loss_30", "payload": "64", "rmw": "cyclonedds", "rtt_p95_ms": "100", "loss_pct": "10"},
        {"cond": "loss_30", "payload": "64", "rmw": "zenoh", "rtt_p95_ms": "10", "loss_pct": "50"},
    ]
    always_cyc = lambda tf, tl, q: "cyclonedds"
    sw = sweep_deadline(swrows, [100.0, 1000.0], predict_fn=always_cyc)
    assert len(sw["curve"]) == 2
    assert set(sw["curve"][0]) >= {"D", "always_cyclonedds", "always_zenoh", "selector"}
    assert all(abs(p["selector"] - p["always_cyclonedds"]) < 1e-9 for p in sw["curve"])
    assert sw["d_star"] == 100.0

    print("TOATE VERIFICARILE selector_core AU TRECUT")


if __name__ == "__main__":
    _selftest()
