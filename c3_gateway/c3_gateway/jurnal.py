#!/usr/bin/env python3
"""jurnal.py -- instrumentarea unei rulari. FARA ROS, fara retea: doar scriere de fisiere.

PRINCIPIUL: o rulare trebuie sa poata fi INTEROGATA ulterior fara sa fie repetata. Tot ce
vrem sa aflam dupa aceea trebuie sa existe deja in jurnal, per esantion:
  - livrarea per conditie          -> esantioane.csv (trimis + primit + cale)
  - numarul de comutari            -> evenimente.csv (fiecare comutare, cu motivul)
  - timpul petrecut in transportul GRESIT fata de optimul instantaneu (calculabil offline,
    fiindca fiecare esantion poarta si transportul folosit, si estimarea AMBELOR cai)
  - latenta decizie -> efect       -> evenimente.csv (t_decizie) + esantioane.csv (t_send)
  - overhead-ul sondei             -> esantioane.csv (tip A/P + octeti) + rezumat
  - starea AMBELOR cai in orice moment, inclusiv a celei inactive -> coloanele L/B/stable
    per cale, scrise la FIECARE esantion, nu doar cand se schimba ceva

Formatul e cel din C2: CSV per-esantion + rezumat JSON, ca sa poata fi citit cu uneltele
deja existente (audit / burst_metrics lucreaza pe coloane de acest fel).
"""
import csv
import json
import os
import sys
import time

CAP_ESANTIOANE = ["t_mono", "seq", "cale", "tip", "topic", "octeti", "primit",
                  "rtt_ms", "L_cyclonedds", "B_cyclonedds", "stabil_cyclonedds",
                  "n_cyclonedds", "L_zenoh", "B_zenoh", "stabil_zenoh", "n_zenoh"]
CAP_EVENIMENTE = ["t_mono", "eveniment", "de_la", "la", "motiv", "topic", "payload"]


class Jurnal(object):
    """Scrie doua CSV-uri si un JSON de rezumat. Deschide fisierele o data si le tine
    deschise: la 55 Hz, un open/close per esantion ar fi mai scump decat masuratoarea."""

    def __init__(self, director, eticheta="rulare"):
        os.makedirs(director, exist_ok=True)
        self.director = director
        self.eticheta = eticheta
        self._f_es = open(os.path.join(director, "esantioane.csv"), "w", newline="")
        self._f_ev = open(os.path.join(director, "evenimente.csv"), "w", newline="")
        self._w_es = csv.writer(self._f_es)
        self._w_ev = csv.writer(self._f_ev)
        self._w_es.writerow(CAP_ESANTIOANE)
        self._w_ev.writerow(CAP_EVENIMENTE)
        self.n_esantioane = {"A": 0, "P": 0}
        self.octeti = {"A": 0, "P": 0}
        self.n_primite = {"A": 0, "P": 0}
        self.n_comutari = 0
        self.t0 = time.clock_gettime(time.CLOCK_MONOTONIC)

    # ------------------------------------------------------------------- scriere
    def esantion(self, t_mono, seq, cale, tip, topic, octeti, primit, rtt_ms, stari):
        """stari: {transport: Estimare|None} -- se scrie starea AMBELOR cai, la fiecare
        esantion. Redundant? Da. Dar fara asta nu se poate raspunde offline la 'ce stia
        gateway-ul despre calea inactiva in clipa X', care e chiar intrebarea din C2."""
        r = [round(t_mono - self.t0, 6), seq, cale, tip, topic, octeti,
             1 if primit else 0, "" if rtt_ms is None else round(rtt_ms, 3)]
        for t in ("cyclonedds", "zenoh"):
            e = stari.get(t)
            if e is None:
                r += ["", "", "", 0]
            else:
                r += [round(e.L, 5), round(e.B, 3), 1 if e.stable else 0, e.n_samples]
        self._w_es.writerow(r)
        self.n_esantioane[tip] = self.n_esantioane.get(tip, 0) + 1
        self.octeti[tip] = self.octeti.get(tip, 0) + octeti
        if primit:
            self.n_primite[tip] = self.n_primite.get(tip, 0) + 1

    def eveniment(self, t_mono, eveniment, de_la="", la="", motiv="", topic="", payload=""):
        self._w_ev.writerow([round(t_mono - self.t0, 6), eveniment, de_la, la, motiv,
                             topic, payload])
        if eveniment == "comutare":
            self.n_comutari += 1

    # ------------------------------------------------------------------- inchidere
    def rezumat(self, extra=None):
        durata = time.clock_gettime(time.CLOCK_MONOTONIC) - self.t0
        oct_app = self.octeti.get("A", 0)
        oct_sonda = self.octeti.get("P", 0)
        total = oct_app + oct_sonda
        r = {
            "eticheta": self.eticheta,
            "durata_s": round(durata, 3),
            "n_app": self.n_esantioane.get("A", 0),
            "n_sonda": self.n_esantioane.get("P", 0),
            "primite_app": self.n_primite.get("A", 0),
            "primite_sonda": self.n_primite.get("P", 0),
            "livrare_app": (self.n_primite.get("A", 0)
                            / float(self.n_esantioane.get("A", 0) or 1)),
            "livrare_sonda": (self.n_primite.get("P", 0)
                              / float(self.n_esantioane.get("P", 0) or 1)),
            "octeti_app": oct_app,
            "octeti_sonda": oct_sonda,
            "octeti_s_sonda": round(oct_sonda / durata, 1) if durata > 0 else 0.0,
            "overhead_sonda_pct": round(100.0 * oct_sonda / total, 3) if total else 0.0,
            "n_comutari": self.n_comutari,
        }
        if extra:
            r.update(extra)
        return r

    def inchide(self, extra=None):
        r = self.rezumat(extra)
        with open(os.path.join(self.director, "rezumat.json"), "w") as f:
            json.dump(r, f, indent=1)
        for f in (self._f_es, self._f_ev):
            try:
                f.close()
            except OSError:
                pass
        return r


def _selftest():
    import shutil
    import tempfile

    class E(object):
        def __init__(self, L, B, stable, n):
            self.L, self.B, self.stable, self.n_samples = L, B, stable, n

    d = tempfile.mkdtemp(prefix="jurnal_selftest_")
    try:
        j = Jurnal(d, "test")
        stari = {"cyclonedds": E(0.1, 3.0, True, 500), "zenoh": E(0.9, 8.0, False, 40)}
        for i in range(10):
            j.esantion(j.t0 + i * 0.02, i, "cyclonedds", "A", 0, 4096, i % 5 != 0, 12.5,
                       stari)
        for i in range(4):
            j.esantion(j.t0 + i * 0.2, 1000 + i, "zenoh", "P", 0, 32, True, 3.0, stari)
        j.eveniment(j.t0 + 1.0, "comutare", "cyclonedds", "zenoh", "marja 40 pp", 0, 4096)
        r = j.inchide({"conditie": "ge_15_8"})

        # rezumatul stie ce trebuie
        assert r["n_app"] == 10 and r["n_sonda"] == 4, r
        assert r["primite_app"] == 8 and abs(r["livrare_app"] - 0.8) < 1e-9, r
        assert r["n_comutari"] == 1 and r["conditie"] == "ge_15_8", r
        # overhead-ul sondei: 4*32 din (10*4096 + 4*32)
        # rezumatul rotunjeste la 3 zecimale, deci toleranta trebuie sa fie
        # de ordinul rotunjirii, nu 1e-6
        assert abs(r["overhead_sonda_pct"] - 100.0 * 128 / (40960 + 128)) < 5e-4, r

        # CSV-ul contine starea AMBELOR cai la fiecare rand -- fara asta nu se poate
        # reconstrui offline ce stia gateway-ul despre calea inactiva
        with open(os.path.join(d, "esantioane.csv")) as f:
            randuri = list(csv.DictReader(f))
        assert len(randuri) == 14, len(randuri)
        assert randuri[0]["L_zenoh"] == "0.9" and randuri[0]["stabil_zenoh"] == "0", randuri[0]
        assert randuri[0]["cale"] == "cyclonedds" and randuri[0]["tip"] == "A"
        assert randuri[10]["tip"] == "P" and randuri[10]["octeti"] == "32"
        assert set(CAP_ESANTIOANE) == set(randuri[0].keys())

        with open(os.path.join(d, "evenimente.csv")) as f:
            ev = list(csv.DictReader(f))
        assert len(ev) == 1 and ev[0]["eveniment"] == "comutare", ev
        assert ev[0]["de_la"] == "cyclonedds" and ev[0]["la"] == "zenoh", ev
        print("SELFTEST jurnal OK (esantioane, evenimente, rezumat, overhead).")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
