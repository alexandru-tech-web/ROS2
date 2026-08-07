#!/usr/bin/env python3
"""jurnal.py -- instrumentarea unei rulari. FARA ROS, fara retea: doar scriere de fisiere.

PRINCIPIUL: o rulare trebuie sa poata fi INTEROGATA ulterior fara sa fie repetata. Tot ce
vrem sa aflam dupa aceea trebuie sa existe deja in jurnal, per esantion:
  - livrarea per conditie          -> esantioane.csv (trimis + primit + cale)
  - numarul de comutari            -> evenimente.csv (fiecare comutare, cu motivul)
  - timpul petrecut in transportul GRESIT fata de optimul instantaneu (calculabil offline,
    fiindca fiecare esantion poarta si transportul folosit, si estimarea AMBELOR cai)
  - latenta decizie -> efect       -> evenimente.csv (t_decizie) + esantioane.csv (t_send)
  - overhead-ul sondelor           -> esantioane.csv (tip A/P + octeti) + rezumat, in
    octeti SI IN PACHETE, cu numitorul scris explicit (vezi core/overhead.py)
  - starea canalului si viabilitatea fiecarei cai in orice moment -> coloane scrise la
    FIECARE esantion, nu doar cand se schimba ceva

VALIDAREA DE INSTRUMENT (etapa 3.5)
Al treilea fisier, sonda_canal.csv, exista pentru o singura intrebare: sonda de canal chiar
masoara ce injecteaza netem? Ea scrie fiecare raport primit de la reflector -- (L,B) MASURAT
-- iar rezumatul poarta eticheta conditiei, adica (L,B) INJECTAT. Cele doua puse fata in
fata, offline si fara sa se repete nimic, dau pentru C3 exact ce da sectiunea de validare a
instrumentului pentru C2. Fara fisierul asta, singurul mod de a afla daca sonda minte ar fi
sa mai rulezi o campanie.

Formatul e cel din C2: CSV per-esantion + rezumat JSON, ca sa poata fi citit cu uneltele
deja existente (audit / burst_metrics lucreaza pe coloane de acest fel).
"""
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))
from overhead import pachete_udp                                    # noqa: E402

# Coloanele fixe; cele per-cale se adauga la construire, din lista de transporturi primita.
# Numele transporturilor NU mai sunt scrise aici: jurnalul le afla de la cine il creeaza,
# ca sa nu existe inca un loc din care sa trebuiasca sters 'zenoh' cand apare al treilea.
CAP_FIX = ["t_mono", "seq", "cale", "tip", "topic", "octeti", "primit", "rtt_ms",
           "L_canal", "B_canal", "sigma_L_canal", "stabil_canal", "n_canal"]
CAP_EVENIMENTE = ["t_mono", "eveniment", "de_la", "la", "motiv", "topic", "payload"]
CAP_SONDA_CANAL = ["t_mono", "L", "B", "n", "goluri", "stabil"]


class Jurnal(object):
    """Scrie doua CSV-uri si un JSON de rezumat. Deschide fisierele o data si le tine
    deschise: la 55 Hz, un open/close per esantion ar fi mai scump decat masuratoarea."""

    def __init__(self, director, eticheta="rulare", transporturi=()):
        os.makedirs(director, exist_ok=True)
        self.director = director
        self.eticheta = eticheta
        self.transporturi = tuple(sorted(transporturi))
        self.cap_esantioane = list(CAP_FIX)
        for t in self.transporturi:
            self.cap_esantioane += ["viab_%s" % t, "sonde_%s" % t]
        self._f_es = open(os.path.join(director, "esantioane.csv"), "w", newline="")
        self._f_ev = open(os.path.join(director, "evenimente.csv"), "w", newline="")
        self._f_sc = open(os.path.join(director, "sonda_canal.csv"), "w", newline="")
        self._w_es = csv.writer(self._f_es)
        self._w_ev = csv.writer(self._f_ev)
        self._w_sc = csv.writer(self._f_sc)
        self._w_es.writerow(self.cap_esantioane)
        self._w_ev.writerow(CAP_EVENIMENTE)
        self._w_sc.writerow(CAP_SONDA_CANAL)
        self.n_rapoarte_canal = 0
        self.ultim_raport = None
        self.n_esantioane = {"A": 0, "P": 0}
        self.octeti = {"A": 0, "P": 0}
        self.pachete = {"A": 0, "P": 0}
        self.n_primite = {"A": 0, "P": 0}
        self.n_comutari = 0
        self.t0 = time.clock_gettime(time.CLOCK_MONOTONIC)

    # ------------------------------------------------------------------- scriere
    def esantion(self, t_mono, seq, cale, tip, topic, octeti, primit, rtt_ms, stare):
        """stare: (Estimare_canal|None, {transport: Viabilitate}) -- se scrie la FIECARE
        esantion. Redundant? Da. Dar fara asta nu se poate raspunde offline la 'ce stia
        gateway-ul in clipa X', care e chiar intrebarea din C2."""
        est, viab = stare
        r = [round(t_mono - self.t0, 6), seq, cale, tip, topic, octeti,
             1 if primit else 0, "" if rtt_ms is None else round(rtt_ms, 3)]
        if est is None:
            r += ["", "", "", "", 0]
        else:
            r += [round(est.L, 5), round(est.B, 3), round(est.sigma_L, 6),
                  1 if est.stable else 0, est.n_samples]
        for t in self.transporturi:
            v = (viab or {}).get(t)
            r += ["" if v is None else round(v.livrare, 4),
                  0 if v is None else v.n_trimise]
        self._w_es.writerow(r)
        self.n_esantioane[tip] = self.n_esantioane.get(tip, 0) + 1
        self.octeti[tip] = self.octeti.get(tip, 0) + octeti
        self.pachete[tip] = self.pachete.get(tip, 0) + pachete_udp(octeti)
        if primit:
            self.n_primite[tip] = self.n_primite.get(tip, 0) + 1

    def raport_canal(self, t_mono, raport):
        """Un raport de la sonda de canal, scris ca atare. Astea sunt (L,B) MASURATE pe
        canal; (L,B) INJECTATE sunt in eticheta rularii. Compararea lor e validarea de
        instrument pentru C3 si se face offline, din fisierele astea doua."""
        self._w_sc.writerow([round(t_mono - self.t0, 6), round(raport.L, 6),
                             round(raport.B, 4), raport.n, raport.goluri,
                             1 if raport.stabil else 0])
        self.n_rapoarte_canal += 1
        self.ultim_raport = raport

    def eveniment(self, t_mono, eveniment, de_la="", la="", motiv="", topic="", payload=""):
        self._w_ev.writerow([round(t_mono - self.t0, 6), eveniment, de_la, la, motiv,
                             topic, payload])
        if eveniment == "comutare":
            self.n_comutari += 1

    # ------------------------------------------------------------------- inchidere
    def rezumat(self, extra=None):
        """OVERHEAD-UL, CU NUMITORUL DECLARAT (corectie etapa 3.5).

        Raportarea de la etapa 3 -- '338.4 octeti/s = 0.201%' -- avea numitorul nescris, si
        de aceea cifrele nu se reconciliau: fata de fluxul nominal (4096 B la 50 Hz =
        204800 B/s) aceiasi octeti dau 0.165%. Aici fiecare procent isi poarta baza in nume,
        si se raporteaza AMBELE unitati. Pachetele sunt cele care conteaza pe un link
        degradat: netem arunca pachete, nu kiloocteti.

        Aproximatie declarata: octetii numarati sunt cadrele IPC (payload + 18 octeti de
        antet UDS/protocol), folositi ca aproximare a payload-ului pus pe fir. Suprapunerea
        e de 18 octeti dintr-un cadru de 4 KB, adica sub 0.5%, si NU schimba numarul de
        fragmente pentru niciun payload din campanie."""
        durata = time.clock_gettime(time.CLOCK_MONOTONIC) - self.t0
        oct_app, oct_viab = self.octeti.get("A", 0), self.octeti.get("P", 0)
        pac_app, pac_viab = self.pachete.get("A", 0), self.pachete.get("P", 0)
        e = extra or {}

        # sonda de canal: contorizata de gateway, nu de jurnal (jurnalul vede doar
        # rapoartele, nu si sondele care le-au provocat)
        n_sc = e.get("sonde_canal_trimise", 0)
        oct_sc_unit = e.get("payload_sonda_canal", 0)
        oct_sc = n_sc * oct_sc_unit
        pac_sc = n_sc * pachete_udp(oct_sc_unit) if oct_sc_unit else 0
        oct_rap = self.n_rapoarte_canal * 37          # RAPORT.size din sonda_canal.py
        pac_rap = self.n_rapoarte_canal

        oct_sonde = oct_viab + oct_sc + oct_rap
        pac_sonde = pac_viab + pac_sc + pac_rap
        oct_tot, pac_tot = oct_app + oct_sonde, pac_app + pac_sonde
        d = durata if durata > 0 else 1.0

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
            "n_rapoarte_canal": self.n_rapoarte_canal,
            "n_comutari": self.n_comutari,
            "overhead": {
                "numitor": ("trafic total masurat in rulare (aplicatie + sonde de "
                            "viabilitate + sonda de canal + rapoarte)"),
                "aproximatie": ("octetii sunt cadre IPC (payload + 18 B antet), folosite ca "
                                "aproximare a payload-ului pe fir; MTU 1500 pentru fragmente"),
                "octeti_app": oct_app, "octeti_sonde": oct_sonde,
                "octeti_sonda_viabilitate": oct_viab, "octeti_sonda_canal": oct_sc,
                "octeti_rapoarte": oct_rap, "octeti_total": oct_tot,
                "pachete_app": pac_app, "pachete_sonde": pac_sonde,
                "pachete_sonda_viabilitate": pac_viab, "pachete_sonda_canal": pac_sc,
                "pachete_rapoarte": pac_rap, "pachete_total": pac_tot,
                "octeti_s_sonde": round(oct_sonde / d, 1),
                "pachete_s_sonde": round(pac_sonde / d, 2),
                "octeti_s_app": round(oct_app / d, 1),
                "pachete_s_app": round(pac_app / d, 2),
                "overhead_octeti_pct": round(100.0 * oct_sonde / oct_tot, 4) if oct_tot else 0.0,
                "overhead_pachete_pct": round(100.0 * pac_sonde / pac_tot, 4) if pac_tot else 0.0,
            },
        }
        if extra:
            r.update(extra)
        return r

    def inchide(self, extra=None):
        r = self.rezumat(extra)
        with open(os.path.join(self.director, "rezumat.json"), "w") as f:
            json.dump(r, f, indent=1)
        for f in (self._f_es, self._f_ev, self._f_sc):
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
            self.sigma_L = 0.004

    class V(object):
        def __init__(self, n, k):
            self.n_trimise, self.n_intoarse = n, k

        @property
        def livrare(self):
            return self.n_intoarse / float(self.n_trimise) if self.n_trimise else 0.0

    class R(object):
        def __init__(self, L, B, n, goluri, stabil):
            self.L, self.B, self.n, self.goluri, self.stabil = L, B, n, goluri, stabil

    d = tempfile.mkdtemp(prefix="jurnal_selftest_")
    try:
        j = Jurnal(d, "ge_15_8", transporturi=("cyclonedds", "zenoh"))
        stare = (E(0.1, 3.0, True, 500), {"cyclonedds": V(50, 50), "zenoh": V(50, 2)})
        for i in range(10):
            j.esantion(j.t0 + i * 0.02, i, "cyclonedds", "A", 0, 4096, i % 5 != 0, 12.5,
                       stare)
        for i in range(4):
            j.esantion(j.t0 + i * 0.2, 1000 + i, "zenoh", "P", 0, 32, True, 3.0, stare)
        for i in range(3):
            j.raport_canal(j.t0 + i * 0.5, R(0.148, 7.9, 200 + i, 30, True))
        j.eveniment(j.t0 + 1.0, "comutare", "cyclonedds", "zenoh", "marja 40 pp", 0, 4096)
        r = j.inchide({"conditie": "ge_15_8", "sonde_canal_trimise": 500,
                       "payload_sonda_canal": 12})

        assert r["n_app"] == 10 and r["n_sonda"] == 4, r
        assert r["primite_app"] == 8 and abs(r["livrare_app"] - 0.8) < 1e-9, r
        assert r["n_comutari"] == 1 and r["conditie"] == "ge_15_8", r
        assert r["n_rapoarte_canal"] == 3, r

        # OVERHEAD: numitorul e explicit si cele doua unitati NU coincid -- daca ar coincide,
        # ar insemna ca fragmentarea nu se numara nicaieri si intreaga corectie e degeaba.
        o = r["overhead"]
        assert o["octeti_app"] == 10 * 4096, o
        assert o["pachete_app"] == 10 * 3, o             # 4096 B = 3 fragmente la MTU 1500
        assert o["pachete_sonda_viabilitate"] == 4, o    # 32 B = un pachet
        assert o["pachete_sonda_canal"] == 500, o        # 500 sonde de cate un pachet
        assert o["pachete_rapoarte"] == 3, o
        assert o["pachete_total"] == 30 + 4 + 500 + 3, o
        assert o["octeti_total"] == 40960 + 128 + 6000 + 111, o
        assert o["overhead_pachete_pct"] > 5 * o["overhead_octeti_pct"], o
        assert "numitor" in o and "aproximatie" in o, o

        with open(os.path.join(d, "esantioane.csv")) as f:
            randuri = list(csv.DictReader(f))
        assert len(randuri) == 14, len(randuri)
        # starea CANALULUI, una singura, plus viabilitatea fiecarei cai
        assert randuri[0]["L_canal"] == "0.1" and randuri[0]["stabil_canal"] == "1", randuri[0]
        assert randuri[0]["viab_zenoh"] == "0.04", randuri[0]
        assert randuri[0]["viab_cyclonedds"] == "1.0", randuri[0]
        assert set(j.cap_esantioane) == set(randuri[0].keys())
        # nicio coloana de (L,B) PER CALE: daca reapare vreuna, cineva a reintrodus
        # estimarea prin transport, adica exact eroarea reparata la etapa 3.5
        for cheie in randuri[0]:
            assert not (cheie.startswith("L_") and cheie != "L_canal"), cheie
            assert not (cheie.startswith("B_") and cheie != "B_canal"), cheie

        with open(os.path.join(d, "sonda_canal.csv")) as f:
            sc = list(csv.DictReader(f))
        assert len(sc) == 3 and sc[0]["L"] == "0.148", sc
        assert set(CAP_SONDA_CANAL) == set(sc[0].keys())

        with open(os.path.join(d, "evenimente.csv")) as f:
            ev = list(csv.DictReader(f))
        assert len(ev) == 1 and ev[0]["de_la"] == "cyclonedds", ev
        print("SELFTEST jurnal OK (esantioane, sonda_canal, evenimente, overhead in "
              "octeti SI pachete cu numitor declarat).")
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
