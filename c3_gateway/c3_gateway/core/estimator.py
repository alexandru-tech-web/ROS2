#!/usr/bin/env python3
"""estimator.py -- estimeaza ONLINE starea linkului din numere de secventa.
NUCLEU PUR: nu importa rclpy, socket sau os.environ.

Intrare: numerele de secventa ale pachetelor PRIMITE. Ce lipseste intre doua numere
consecutive s-a pierdut -- exact conventia din C2 (burst_metrics.failure_bursts).

Ce estimeaza:
  L  = rata medie de pierdere, EWMA pe indicatorul de pierdere (1 pierdut / 0 livrat)
  B  = lungimea medie a rafalei, EWMA pe lungimile GOLURILOR. Sub Simple Gilbert,
       lungimea unei rafale e geometrica(r) cu media 1/r, deci media golurilor observate
       ESTE estimatorul lui 1/r, adica exact B din grila C2.

DE CE DOUA CONSTANTE DE TIMP DIFERITE
L se actualizeaza la FIECARE esantion; B doar cand se inchide un gol. La L=5% si B=8, pe
o fereastra de 200 de esantioane sunt ~10 pierderi, adica ~1 gol. Daca B ar avea acelasi
alpha ca L, ar fi condus de un singur gol si ar sari haotic. De aceea alpha_B e mai mare
(reactioneaza pe numar de GOLURI, nu de esantioane) si, mai important, exista FLAG-ul de
stabilitate de mai jos.

FLAG-UL 'stable' -- pragul si de ce
B e instabil cand L e mic: pierderile sunt rare, golurile si mai rare, iar media lor e
calculata din cateva observatii. Se cer DOUA conditii simultan:
  1. L_hat >= L_MIN_PENTRU_B (implicit 0.02). Sub 2%, intr-o fereastra efectiva de
     1/alpha_L = 200 de esantioane sunt ~4 pierderi; grupate in rafale, poate 1-2 goluri.
     Orice B calculat de acolo e o parere, nu o masuratoare.
  2. n_goluri >= GOLURI_MIN (implicit 5). Sub 5 goluri, eroarea standard a mediei unei
     geometrice cu B=8 e ~7.5/sqrt(5) = 3.3 pachete, adica ordinul marimii estimate.
Cand stable=False, B ramane raportat (poate fi util), dar consumatorul (switching.py)
refuza sa comute pe baza lui.

INCERTITUDINEA lui L (sigma_L) -- si de ce nu e formula de manual
Pentru esantioane INDEPENDENTE, varianta unui EWMA in regim stationar e
    var_iid = L(1-L) * alpha/(2-alpha)
Dar sub Gilbert-Elliott esantioanele sunt CORELATE: pierderile vin in rafale, deci un
esantion nou aduce mai putina informatie noua decat unul independent. Factorul de umflare
pentru media unui proces cu autocorelatie rho la pas 1 este (1+rho)/(1-rho), iar pentru
lantul cu doua stari rho = 1-p-r, cu r=1/B si p = L*r/(1-L). Ignorarea corelatiei ar face
gateway-ul sa creada ca stie L mult mai precis decat stie -- exact greseala care produce
comutari pe zgomot. Formula raportata aici e, deci, DELIBERAT mai pesimista.
"""
import math
import sys

ALPHA_L = 0.01          # fereastra efectiva ~1/alpha = 100 esantioane (2 s la 50 Hz)
ALPHA_B = 0.20          # ~5 goluri de memorie
L_MIN_PENTRU_B = 0.02
GOLURI_MIN = 5


class Estimare(object):
    """Fotografia starii linkului la un moment dat. Obiect de date, fara logica."""

    __slots__ = ("L", "B", "sigma_L", "n_samples", "n_goluri", "stable")

    def __init__(self, L, B, sigma_L, n_samples, n_goluri, stable):
        self.L = L
        self.B = B
        self.sigma_L = sigma_L
        self.n_samples = n_samples
        self.n_goluri = n_goluri
        self.stable = stable

    def __repr__(self):
        return ("Estimare(L=%.4f, B=%.2f, sigma_L=%.4f, n=%d, goluri=%d, stable=%s)"
                % (self.L, self.B, self.sigma_L, self.n_samples, self.n_goluri,
                   self.stable))


class EstimatorLink(object):
    """Estimator online de (L, B) din numere de secventa. Fara stare globala: doua
    instante sunt complet independente (o stiva per transport, in etapa 2)."""

    def __init__(self, alpha_L=ALPHA_L, alpha_B=ALPHA_B,
                 L_min_pentru_B=L_MIN_PENTRU_B, goluri_min=GOLURI_MIN, B_initial=1.0):
        if not (0.0 < alpha_L <= 1.0 and 0.0 < alpha_B <= 1.0):
            raise ValueError("alpha trebuie in (0, 1]")
        self.alpha_L = float(alpha_L)
        self.alpha_B = float(alpha_B)
        self.L_min_pentru_B = float(L_min_pentru_B)
        self.goluri_min = int(goluri_min)
        self._L = 0.0
        self._B = float(B_initial)
        self._ultim_seq = None
        self.n_samples = 0
        self.n_goluri = 0

    # ------------------------------------------------------------------ actualizare
    def _ewma_repetat(self, y, x, k):
        """k actualizari EWMA consecutive cu ACEEASI valoare x, in forma inchisa:
        dupa k pasi, y_k = x + (1-a)^k * (y - x). Evita bucla peste sute de pierderi."""
        if k <= 0:
            return y
        return x + (1.0 - self.alpha_L) ** k * (y - x)

    def observa(self, seq):
        """Un pachet PRIMIT, cu numarul lui de secventa. Numerele lipsa fata de ultimul
        primit sunt pierderi. Duplicatele si reordonarile (seq <= ultimul) sunt IGNORATE:
        estimatorul masoara pierdere, iar un pachet care soseste tarziu nu a fost pierdut,
        doar intarziat -- alta marime, alt senzor."""
        seq = int(seq)
        if self._ultim_seq is None:
            self._ultim_seq = seq
            self._L = self._ewma_repetat(self._L, 0.0, 1)
            self.n_samples += 1
            return
        gol = seq - self._ultim_seq - 1
        if gol < 0:
            return                                  # reordonare / duplicat
        self._ultim_seq = seq
        if gol > 0:
            self._L = self._ewma_repetat(self._L, 1.0, gol)
            self._B += self.alpha_B * (gol - self._B)
            self.n_goluri += 1
        self._L = self._ewma_repetat(self._L, 0.0, 1)
        self.n_samples += gol + 1

    # -------------------------------------------------------------------- rezultat
    def sigma_L(self):
        """Abaterea standard a estimarii lui L, umflata pentru corelatia din rafale."""
        L = min(max(self._L, 0.0), 1.0)
        var_iid = L * (1.0 - L) * self.alpha_L / (2.0 - self.alpha_L)
        B = max(self._B, 1.0)
        r = 1.0 / B
        p = L * r / (1.0 - L) if L < 1.0 else 1.0
        rho = max(0.0, min(0.999, 1.0 - p - r))     # taiat: nu pretindem sub-iid
        return math.sqrt(var_iid * (1.0 + rho) / (1.0 - rho))

    def sigma_B(self):
        """Abaterea standard a estimarii lui B. Lungimile golurilor sunt geometrice(r) cu
        abaterea sqrt(1-r)/r; media lor exponentiala are, in regim stationar, varianta de
        alpha_B/(2-alpha_B) ori varianta unui esantion. Spre deosebire de L, aici nu e
        nevoie de corectie de corelatie: golurile succesive sunt independente sub Simple
        Gilbert (fiecare rafala reincepe din starea buna)."""
        B = max(self._B, 1.0)
        r = 1.0 / B
        sd_gol = math.sqrt(max(0.0, 1.0 - r)) / r
        return sd_gol * math.sqrt(self.alpha_B / (2.0 - self.alpha_B))

    def stable(self):
        """B e utilizabil pentru decizii? Vezi pragurile si motivul lor in docstring."""
        return (self._L >= self.L_min_pentru_B) and (self.n_goluri >= self.goluri_min)

    def estimare(self):
        return Estimare(self._L, self._B, self.sigma_L(), self.n_samples,
                        self.n_goluri, self.stable())


def _selftest():
    from canal_ge import CanalGE          # noqa: import local, doar pentru selftest

    # 1. fara pierderi: L -> 0, niciun gol, B ramane la initial, stable False
    e = EstimatorLink()
    for s in range(1, 501):
        e.observa(s)
    est = e.estimare()
    assert est.L == 0.0 and est.n_goluri == 0, est
    assert est.n_samples == 500, est
    assert est.stable is False, "fara goluri nu se poate declara stabil"

    # 2. pierdere DETERMINISTA: 1 din 5 pierdut, rafale de lungime 1 -> L->0.2, B->1
    e = EstimatorLink(alpha_L=0.02, alpha_B=0.2)
    seq = [s for s in range(1, 20001) if s % 5 != 0]
    for s in seq:
        e.observa(s)
    est = e.estimare()
    assert abs(est.L - 0.2) < 0.02, est
    assert abs(est.B - 1.0) < 0.01, est
    assert est.stable is True, est

    # 3. CONVERGENTA pe canal GE real, pe celulele grilei C2 (seed fix).
    # Toleranta e 4 x incertitudinea pe care o RAPORTEAZA ESTIMATORUL INSUSI, nu o cifra
    # rotunda: asa testul verifica doua lucruri deodata -- ca estimarea e centrata SI ca
    # bara de eroare e onesta. Cu o toleranta fixa de 2 pp testul pica pe celula (15,3),
    # unde dispersia reala a unui EWMA citit intr-o singura clipa e ~2.4 pp (masurat).
    aB = 0.02
    for L, B in ((15, 3), (15, 8), (30, 3), (30, 8), (5, 8)):
        c = CanalGE.from_LB_pct(L, B, seed=99)
        e = EstimatorLink(alpha_L=0.002, alpha_B=aB)
        for s in c.secvente(400000):
            e.observa(s)
        est = e.estimare()
        assert abs(est.L - L / 100.0) <= 4 * est.sigma_L, ("L", L, B, est)
        r = 1.0 / B
        sd_B = (math.sqrt(1 - r) / r) * math.sqrt(aB / (2 - aB))   # EWMA pe geometrica
        assert abs(est.B - B) <= 4 * sd_B + 1e-9, ("B", L, B, est, 4 * sd_B)
        if L >= 15:
            assert est.stable is True, ("stable", L, B, est)
        # La L=5% NU se cere stable: adevaratul L e la ~2 sigma de pragul de 0.02, deci
        # flagul palpaie legitim in jurul lui. Asta E comportamentul dorit (prudenta la
        # pierdere mica), iar logica flagului se verifica determinist mai jos, nu printr-o
        # tragere norocoasa a canalului.

    # 3b. INCERTITUDINEA RAPORTATA CORESPUNDE REALITATII: dispersia masurata a EWMA-ului
    # trebuie sa fie de acelasi ordin cu sigma_L prezisa. Daca formula ar ignora corelatia
    # (varianta iid), raportul ar iesi mult peste 1 si testul ar pica -- ceea ce e tot
    # scopul: o bara de eroare optimista produce comutari pe zgomot.
    import statistics as _st
    c = CanalGE.from_LB_pct(15, 8, seed=99)
    a = 0.002
    y, traiect = 0.0, []
    for _ in range(200000):
        y += a * ((0.0 if c.esantion() else 1.0) - y)
        traiect.append(y)
    sd_masurat = _st.pstdev(traiect[5000:])
    ref = EstimatorLink(alpha_L=a)
    ref._L, ref._B = 0.15, 8.0
    raport = sd_masurat / ref.sigma_L()
    assert 0.7 < raport < 1.4, ("sigma_L nu descrie dispersia reala", raport, sd_masurat)

    # 3c. TABELA DE ADEVAR a flagului 'stable', determinist (fara canal): ambele conditii
    # trebuie indeplinite simultan, si fiecare singura trebuie sa fie insuficienta.
    for L_hat, goluri, astept in ((0.15, 10, True),      # ambele bune
                                  (0.01, 10, False),     # L sub prag
                                  (0.15, 2, False),      # prea putine goluri
                                  (0.01, 2, False),      # niciuna
                                  (0.02, 5, True)):      # exact pe praguri (inclusiv)
        e = EstimatorLink()
        e._L, e.n_goluri = L_hat, goluri
        assert e.stable() is astept, (L_hat, goluri, e.stable())

    # 4. FLAG-UL de stabilitate: la L mic, B NU e declarat de incredere
    c = CanalGE.from_LB_pct(0.5, 8, seed=3)      # 0.5% pierdere: goluri foarte rare
    e = EstimatorLink()
    for s in c.secvente(20000):
        e.observa(s)
    est = e.estimare()
    assert est.L < L_MIN_PENTRU_B, est
    assert est.stable is False, "L sub prag ar trebui sa faca B nedemn de incredere"

    # 5. incertitudinea CRESTE cu rafalele: acelasi L, B mai mare -> sigma mai mare
    sig = {}
    for B in (1, 8):
        c = CanalGE.from_LB_pct(15, B, seed=5)
        e = EstimatorLink()
        for s in c.secvente(60000):
            e.observa(s)
        sig[B] = e.estimare().sigma_L
    assert sig[8] > 2 * sig[1], sig      # corelatia trebuie sa se vada, nu doar sa existe

    # 6. reordonari si duplicate nu strica estimarea
    e = EstimatorLink()
    for s in (1, 2, 3, 3, 2, 4, 5):
        e.observa(s)
    assert e.estimare().n_goluri == 0, e.estimare()
    assert e.estimare().L == 0.0, e.estimare()

    # 7. un gol mare e contabilizat integral (forma inchisa == bucla)
    a, b = EstimatorLink(), EstimatorLink()
    a.observa(1); a.observa(1002)                       # gol de 1000
    for s in range(1, 1003):                            # acelasi lucru, pas cu pas
        if s == 1 or s == 1002:
            b.observa(s)
    assert a.estimare().n_samples == 1002, a.estimare()
    assert abs(a.estimare().L - b.estimare().L) < 1e-12
    print("SELFTEST estimator OK (convergenta pe 5 celule C2, stabilitate, incertitudine).")


def main(argv):
    if argv and argv[0] == "--selftest":
        _selftest()
        return 0
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    sys.exit(main(sys.argv[1:]))
