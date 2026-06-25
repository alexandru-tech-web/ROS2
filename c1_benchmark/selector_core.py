#!/usr/bin/env python3
"""selector_core.py -- nucleu pur (fara ROS, fara I/O, fara sklearn) pentru SELECTORUL
de middleware din campania C1.

Ridica analiza de la CARACTERIZATOR (reproduce_pdia.py: prezice RTT din severitate +
payload, ARUNCA rmw) la SELECTOR: din parametrii de retea + payload, ALEGE rmw-ul care
minimizeaza obiectivul. Obiectiv implementat: CONTROL = min RTT p95.

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
    "ideal":        (0.0,   0.0,  0.0),
    "loss_5":       (5.0,   0.0,  0.0),
    "loss_15":      (15.0,  0.0,  0.0),
    "loss_30":      (30.0,  0.0,  0.0),
    "lat200_jit50": (0.0, 200.0, 50.0),
    "lat200_l15":   (15.0, 200.0,  0.0),
}


def parse_cond(cond):
    """Intoarce (loss_pct, lat_ms, jit_ms) pentru o conditie cunoscuta."""
    if cond not in COND_NETEM:
        raise ValueError("conditie necunoscuta: %r" % (cond,))
    return COND_NETEM[cond]


def cell_features(cond, payload):
    """Vectorul de feature-uri al unei celule: [loss, lat, jit, log10(payload)]."""
    loss, lat, jit = parse_cond(cond)
    return [loss, lat, jit, math.log10(float(payload))]


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

    print("TOATE VERIFICARILE selector_core AU TRECUT")


if __name__ == "__main__":
    _selftest()
