#!/usr/bin/env python3
"""date_features_sklearn.py -- VALIDARE incrucisata a nucleului M04 cu scikit-learn.

Ruleaza nucleul pur (date_features_core) si echivalentele din scikit-learn pe
ACELEASI date si aserteaza ca rezultatele coincid sub o toleranta. Comparam:

  - OneHotEncoder            vs fit_one_hot / transform_one_hot
  - OrdinalEncoder           vs fit_ordinal / transform_ordinal
  - SimpleImputer(mean)      vs fit_mean_imputer / transform_mean_imputer (TRAIN->TEST)
  - PolynomialFeatures(d=2)  vs polynomial_features (pe multimi de coloane,
                                comparam dupa sortare ca ordinea sa nu conteze)
  - ColumnTransformer        vs compunerea manuala one-hot + standardizare

scikit-learn este permis DOAR aici (si in *_sklearn.py al fiecarui modul), nu in
nucleu. Scopul e increderea: daca cele doua cai dau acelasi rezultat, nucleul e
corect.

Ruleaza: python3 date_features_sklearn.py   (iesire 0 = PASS, non-0 = FAIL).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from date_features_core import (  # noqa: E402
    fit_mean_imputer, transform_mean_imputer,
    fit_one_hot, transform_one_hot,
    fit_ordinal, transform_ordinal,
    polynomial_features,
)
from utils import standardize  # noqa: E402

from sklearn.preprocessing import (  # noqa: E402
    OneHotEncoder, OrdinalEncoder, PolynomialFeatures, StandardScaler,
)
from sklearn.impute import SimpleImputer  # noqa: E402
from sklearn.compose import ColumnTransformer  # noqa: E402


def _sorted_rows(M):
    """Sorteaza coloanele unei matrice (pe rand) pentru comparare invarianta la ordine."""
    M = np.asarray(M, dtype=float)
    return np.sort(M, axis=1)


def main():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    rng = np.random.default_rng(0)

    # ---------------------------------------------------- one-hot
    labels = np.array(["DDS", "Zenoh", "DDS", "Zenoh", "Zenoh", "DDS"]).reshape(-1, 1)
    cats = fit_one_hot(labels)
    M_core = transform_one_hot(labels, cats)
    enc = OneHotEncoder(sparse_output=False, categories=[cats])
    M_skl = enc.fit_transform(labels)
    ck("one-hot: nucleu == OneHotEncoder", np.allclose(M_core, M_skl))
    print("    [cmp] one-hot core[:2]=%s  sklearn[:2]=%s" %
          (M_core[:2].tolist(), M_skl[:2].tolist()))

    # ---------------------------------------------------- ordinal
    order = ["mic", "mediu", "mare"]
    raw = np.array(["mare", "mic", "mediu", "mic", "mare"]).reshape(-1, 1)
    mp = fit_ordinal(order)
    o_core = transform_ordinal(raw, mp)
    oe = OrdinalEncoder(categories=[order])
    o_skl = oe.fit_transform(raw).ravel()
    ck("ordinal: nucleu == OrdinalEncoder", np.allclose(o_core, o_skl))
    print("    [cmp] ordinal core=%s  sklearn=%s" % (o_core.tolist(), o_skl.tolist()))

    # ---------------------------------------------------- imputare medie (TRAIN->TEST)
    X = rng.normal(5.0, 2.0, size=(40, 3))
    # injectam NaN-uri
    nan_idx = (rng.integers(0, 40, size=10), rng.integers(0, 3, size=10))
    X[nan_idx] = np.nan
    Xtr, Xte = X[:30], X[30:]
    means = fit_mean_imputer(Xtr)
    Xtr_c, Xte_c = transform_mean_imputer(Xtr, means), transform_mean_imputer(Xte, means)
    imp = SimpleImputer(strategy="mean")
    Xtr_s = imp.fit_transform(Xtr)
    Xte_s = imp.transform(Xte)  # foloseste media de pe TRAIN -> fara scurgere
    ck("imputare: media nucleu == SimpleImputer.statistics_",
       np.allclose(means, imp.statistics_, equal_nan=False))
    ck("imputare: TRAIN nucleu == sklearn", np.allclose(Xtr_c, Xtr_s))
    ck("imputare: TEST nucleu == sklearn (media TRAIN)", np.allclose(Xte_c, Xte_s))

    # ---------------------------------------------------- polinomiale grad 2
    Xp = rng.normal(0.0, 1.0, size=(12, 3))
    P_core, _ = polynomial_features(Xp, degree=2, include_bias=False)
    pf = PolynomialFeatures(degree=2, include_bias=False)
    P_skl = pf.fit_transform(Xp)
    ck("poly: acelasi numar de coloane", P_core.shape == P_skl.shape)
    # ordinea termenilor poate diferi -> comparam multimile de coloane (sortate pe rand)
    ck("poly: aceleasi coloane (invariant la ordine)",
       np.allclose(_sorted_rows(P_core), _sorted_rows(P_skl)))
    print("    [cmp] poly shape core=%s sklearn=%s" % (P_core.shape, P_skl.shape))

    # ---------------------------------------------------- ColumnTransformer end-to-end
    # 1 coloana categoriala (middleware) + 2 numerice; one-hot pe cat, z-score pe num.
    mids = np.array(["DDS", "Zenoh", "Zenoh", "DDS", "DDS", "Zenoh", "DDS", "Zenoh"])
    num = rng.normal(100.0, 30.0, size=(8, 2))
    ntr = 6
    # --- cale nucleu ---
    cats2 = fit_one_hot(mids[:ntr])
    oh_tr = transform_one_hot(mids[:ntr], cats2)
    oh_te = transform_one_hot(mids[ntr:], cats2)
    num_tr_s, num_te_s, _, _ = standardize(num[:ntr], num[ntr:])
    F_core_tr = np.column_stack([oh_tr, num_tr_s])
    F_core_te = np.column_stack([oh_te, num_te_s])
    # --- cale sklearn (ColumnTransformer) ---
    # construim un cadru 'amestecat' ca array de obiect: col0 = middleware, col1,2 = num
    Xmix_tr = np.column_stack([mids[:ntr], num[:ntr]]).astype(object)
    Xmix_te = np.column_stack([mids[ntr:], num[ntr:]]).astype(object)
    ct = ColumnTransformer([
        ("cat", OneHotEncoder(sparse_output=False, categories=[cats2]), [0]),
        ("num", StandardScaler(), [1, 2]),
    ])
    F_skl_tr = ct.fit_transform(Xmix_tr)
    F_skl_te = ct.transform(Xmix_te)
    # StandardScaler imparte la abaterea de populatie (ddof=0), la fel ca utils.standardize.
    ck("ColumnTransformer: TRAIN nucleu == sklearn", np.allclose(F_core_tr, F_skl_tr, atol=1e-9))
    ck("ColumnTransformer: TEST nucleu == sklearn", np.allclose(F_core_te, F_skl_te, atol=1e-9))
    print("    [cmp] feature matrix TRAIN shape core=%s sklearn=%s" %
          (F_core_tr.shape, F_skl_tr.shape))

    print("\nVALIDARE INCRUCISATA M04: %d verificari, nucleu == scikit-learn." % ok)
    return ok


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
