#!/usr/bin/env python3
"""link_predictor_core.py -- nucleul M22 (CAPSTONE), numpy PUR (scikit-learn INTERZIS).

Predictor OFFLINE de stare a linkului: din feature-uri de fereastra de link
(p95 RTT, fractia de pierdere, jitter, middleware, distanta) prezice eticheta
binara 'usable' -- linkul mai suporta teleoperatie in timp real sau nu.

Acesta este nucleul CAPSTONE care INCHIDE cursul inapoi in teza (contributia C3 /
link_adaptive): se antreneaza aici, in afara ROS (numpy pur, testabil izolat), si
apoi se IMPACHETEAZA intr-un nod ROS subtire (link_predictor_node.py) care publica
predictia pe un topic consumabil de stratul adaptiv.

Modelul: regresie logistica binara prin coborare pe gradient (reluare a M08), cu
standardizare invatata pe TRAIN (mean/std memorate in model, fara scurgere la
inferenta) -- exact tiparul de care are nevoie un nod ROS: invata o data, apoi
aplica pe feature-uri proaspete.

Persistenta: save(path) scrie un .npz cu greutatile, statisticile de standardizare,
ordinea feature-urilor si pragul; load(path) reconstruieste un model care da
predictii IDENTICE. predict(features) accepta un dict (cheile = nume de feature)
SAU un vector aliniat la feature_names si intoarce eticheta {0,1}.

Determinism: orice aleator trece prin numpy.random.default_rng(seed).
ONESTITATE: datele de antrenare sunt SINTETICE (semanate din C1/M via date_sar.py).

_selftest() VERIFICA (corectitudine, nu doar ca ruleaza):
  - modelul antrenat bate baza triviala (majoritatea) cu o marja pe TEST;
  - save -> load reproduce EXACT aceleasi probabilitati si etichete;
  - predict pe un dict si pe vectorul aliniat dau acelasi rezultat valid {0,1};
  - probabilitatile raman in [0, 1].

Ruleaza: /home/ubuntu/ros2_ws/.venv_ml/bin/python link_predictor_core.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .../curs_ml/curs_ml

from utils import accuracy  # noqa: E402

# Ordinea CANONICA a feature-urilor. Nodul ROS si save/load se bazeaza pe ea ca
# un dict de feature-uri sa fie mereu asamblat in acelasi vector.
FEATURE_NAMES = ["p95_ms", "loss_frac", "jitter_ms", "base_lat_ms", "mw_zenoh", "distance_m"]


# ============================================================ PRIMITIVE
def _sigmoid(z):
    """Sigmoida logistica stabila numeric (fara overflow), in (0, 1). Vezi M08."""
    z = np.asarray(z, dtype=float)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def features_to_vector(features, feature_names=FEATURE_NAMES):
    """Transforma un dict {nume: valoare} SAU un iterabil ordonat intr-un vector
    1D aliniat la feature_names. Cheile lipsa dintr-un dict -> ValueError (nodul
    ROS trebuie sa primeasca toate feature-urile, altfel predictia nu e valida)."""
    if isinstance(features, dict):
        missing = [k for k in feature_names if k not in features]
        if missing:
            raise ValueError("feature-uri lipsa: %s" % missing)
        return np.array([float(features[k]) for k in feature_names], dtype=float)
    vec = np.asarray(features, dtype=float).reshape(-1)
    if vec.size != len(feature_names):
        raise ValueError("astept %d feature-uri, primit %d" % (len(feature_names), vec.size))
    return vec


# ============================================================ MODEL
class LinkUsabilityPredictor:
    """Predictor binar 'usable' pentru ferestre de link (regresie logistica GD).

    Standardizeaza intern feature-urile cu media/abaterea invatate pe TRAIN si
    pastreaza aceste statistici, ca inferenta pe feature-uri proaspete (in nodul
    ROS) sa fie consecventa cu antrenarea -- fara scurgere de date.

    Parametri:
      lr        -- pasul de coborare pe gradient;
      n_iter    -- numarul de iteratii full-batch;
      seed      -- samanta pentru initializarea greutatilor;
      threshold -- pragul pe probabilitate pentru eticheta {0,1} (implicit 0.5).

    Atribute dupa train:
      w_         -- greutatile (interceptul pe pozitia 0);
      mean_, std_-- statistici de standardizare invatate pe TRAIN;
      loss_      -- istoricul log-loss-ului (diagnoza convergentei).
    """

    def __init__(self, lr=0.2, n_iter=3000, seed=0, threshold=0.5,
                 feature_names=FEATURE_NAMES):
        self.lr = float(lr)
        self.n_iter = int(n_iter)
        self.seed = int(seed)
        self.threshold = float(threshold)
        self.feature_names = list(feature_names)
        self.w_ = None
        self.mean_ = None
        self.std_ = None
        self.loss_ = None

    # ---- standardizare cu statistici memorate ----
    def _standardize_fit(self, X, eps=1e-12):
        self.mean_ = X.mean(axis=0)
        std = X.std(axis=0)
        self.std_ = np.where(std < eps, eps, std)
        return (X - self.mean_) / self.std_

    def _standardize_apply(self, X):
        return (np.asarray(X, dtype=float) - self.mean_) / self.std_

    @staticmethod
    def _add_bias(X):
        X = np.asarray(X, dtype=float)
        return np.column_stack([np.ones(X.shape[0]), X])

    # ---- antrenare OFFLINE ----
    def train(self, X, y):
        """Antreneaza OFFLINE pe (X, y). X: (n, d) feature-uri brute (in ordinea
        feature_names); y in {0, 1}. Standardizeaza, adauga interceptul, coboara
        pe gradientul log-loss-ului. Returneaza self (interfata fluenta)."""
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).reshape(-1)
        Xs = self._standardize_fit(X)
        Phi = self._add_bias(Xs)
        rng = np.random.default_rng(self.seed)
        w = 0.01 * rng.standard_normal(Phi.shape[1])
        loss = np.empty(self.n_iter)
        eps = 1e-12
        for t in range(self.n_iter):
            p = _sigmoid(Phi @ w)
            pc = np.clip(p, eps, 1.0 - eps)
            loss[t] = float(-np.mean(y * np.log(pc) + (1.0 - y) * np.log(1.0 - pc)))
            w = w - self.lr * (Phi.T @ (p - y)) / Phi.shape[0]
        self.w_ = w
        self.loss_ = loss
        return self

    # ---- inferenta ----
    def predict_proba(self, X):
        """Probabilitatea prezisa pentru clasa 'usable' (1), in [0, 1]. X: (n, d)."""
        if self.w_ is None:
            raise RuntimeError("modelul nu e antrenat (cheama train() sau load()).")
        Phi = self._add_bias(self._standardize_apply(np.atleast_2d(X)))
        return _sigmoid(Phi @ self.w_)

    def predict_label(self, X):
        """Eticheta {0, 1} aplicand pragul pe probabilitate. X: (n, d)."""
        return (self.predict_proba(X) >= self.threshold).astype(int)

    def predict(self, features):
        """Predictie pe UN exemplu dat ca dict {nume: valoare} sau vector ordonat.
        Returneaza (label:int, prob:float) -- forma pe care o publica nodul ROS."""
        vec = features_to_vector(features, self.feature_names)
        prob = float(self.predict_proba(vec.reshape(1, -1))[0])
        label = int(prob >= self.threshold)
        return label, prob

    # ---- persistenta ----
    def save(self, path):
        """Salveaza modelul intr-un .npz (greutati + statistici + meta). Adauga
        extensia .npz daca lipseste. Suficient ca load() sa reproduca exact."""
        if self.w_ is None:
            raise RuntimeError("nu pot salva un model neantrenat.")
        np.savez(path,
                 w=self.w_, mean=self.mean_, std=self.std_,
                 feature_names=np.array(self.feature_names),
                 threshold=np.array([self.threshold], dtype=float))
        return path if path.endswith(".npz") else path + ".npz"

    @classmethod
    def load(cls, path):
        """Reconstruieste un predictor dintr-un fisier salvat de save(). Adauga
        extensia .npz daca lipseste si fisierul fara ea nu exista."""
        if not os.path.exists(path) and os.path.exists(path + ".npz"):
            path = path + ".npz"
        data = np.load(path, allow_pickle=False)
        names = [str(s) for s in data["feature_names"].tolist()]
        m = cls(threshold=float(data["threshold"][0]), feature_names=names)
        m.w_ = np.asarray(data["w"], dtype=float)
        m.mean_ = np.asarray(data["mean"], dtype=float)
        m.std_ = np.asarray(data["std"], dtype=float)
        return m


# ============================================================ ANTRENARE DIN DATE
def train_from_dataset(df, feature_names=FEATURE_NAMES, label="usable",
                       lr=0.2, n_iter=3000, seed=0):
    """Comoditate: antreneaza un LinkUsabilityPredictor direct dintr-un DataFrame
    cu coloanele feature_names + label. Folosit de demo si de nodul ROS la pornire."""
    X = df[feature_names].to_numpy(dtype=float)
    y = df[label].to_numpy(dtype=float)
    return LinkUsabilityPredictor(lr=lr, n_iter=n_iter, seed=seed).train(X, y)


# ============================================================ SELFTEST
def _selftest():
    ok = 0

    def ck(name, cond):
        nonlocal ok
        assert cond, "FAIL: " + name
        ok += 1
        print("  [ok] " + name)

    # date SINTETICE din date_sar (calibrate pe C1)
    from date_sar import make_link_usability_dataset
    from utils import train_test_split

    df = make_link_usability_dataset(n_per_cond=200, seed=1)
    X = df[FEATURE_NAMES].to_numpy(dtype=float)
    y = df["usable"].to_numpy(dtype=int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_frac=0.30, seed=0)

    model = LinkUsabilityPredictor(lr=0.2, n_iter=3000, seed=0).train(Xtr, ytr)

    # baza triviala = a prezice mereu clasa majoritara din TRAIN
    maj = int(round(ytr.mean()))            # 0 daca usable minoritar (cazul nostru)
    base_acc = accuracy(yte, np.full_like(yte, maj))
    model_acc = accuracy(yte, model.predict_label(Xte))
    ck("model bate baza triviala pe TEST (%.3f > %.3f + 0.05)" % (model_acc, base_acc),
       model_acc > base_acc + 0.05)
    ck("acuratete model rezonabila pe TEST (> 0.85)", model_acc > 0.85)

    # probabilitati valide
    proba = model.predict_proba(Xte)
    ck("predict_proba in [0, 1]", float(proba.min()) >= 0.0 and float(proba.max()) <= 1.0)

    # log-loss scade (convergenta sanatoasa)
    ck("log-loss finala < initiala", model.loss_[-1] < model.loss_[0])

    # save -> load reproduce EXACT
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "_selftest_model.npz")
    model.save(path)
    loaded = LinkUsabilityPredictor.load(path)
    ck("load: aceleasi probabilitati ca modelul salvat",
       np.allclose(model.predict_proba(Xte), loaded.predict_proba(Xte), atol=0.0))
    ck("load: aceleasi etichete ca modelul salvat",
       np.array_equal(model.predict_label(Xte), loaded.predict_label(Xte)))
    ck("load: meta pastrate (feature_names, threshold)",
       loaded.feature_names == FEATURE_NAMES and loaded.threshold == model.threshold)
    try:
        os.remove(path)
    except OSError:
        pass

    # predict pe dict == predict pe vector aliniat, iesire valida {0,1}
    row = df.iloc[0]
    feat_dict = {k: float(row[k]) for k in FEATURE_NAMES}
    feat_vec = [feat_dict[k] for k in FEATURE_NAMES]
    lab_d, prob_d = model.predict(feat_dict)
    lab_v, prob_v = model.predict(feat_vec)
    ck("predict(dict) == predict(vector) (eticheta + prob)",
       lab_d == lab_v and abs(prob_d - prob_v) < 1e-12)
    ck("predict: eticheta in {0,1} si prob in [0,1]",
       lab_d in (0, 1) and 0.0 <= prob_d <= 1.0)

    # dict cu feature lipsa -> eroare clara
    bad = dict(feat_dict)
    del bad["p95_ms"]
    raised = False
    try:
        model.predict(bad)
    except ValueError:
        raised = True
    ck("predict: dict incomplet -> ValueError", raised)

    print("\nTOATE VERIFICARILE link_predictor_core AU TRECUT: %d verificari." % ok)
    return ok


if __name__ == "__main__":
    try:
        _selftest()
        sys.exit(0)
    except AssertionError as e:
        print(e)
        sys.exit(1)
