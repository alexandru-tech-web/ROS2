#!/usr/bin/env python3
"""rf_interference.py -- nucleu pur (fara ROS, fara I/O) pentru modelarea INTERFERENTEI RF:
pierdere CORELATA in rafale (Gilbert-Elliott) + degradare CO-CANAL (SINR).

Doua niveluri ortogonale, ambele deterministe (seed):
  1. BurstProcess (Gilbert-Elliott, 2 stari GOOD/BAD): pierderea nu mai e independenta, ci vine in
     rafale. PARITATE DE MODEL cu netem nativ -- 'loss gemodel p% r% loss_bad% loss_good%' -- deci
     ACELASI lant Markov (aceiasi parametri si statistici) ruleaza in SIL (Python) si pe fier (tc).
     Inchide gap-ul SIL->HIL al burst-ului (NOTA_METODOLOGICA_C1.md: burst-ul vechi 'loss p% r%'
     era un model mai sarac decat Gilbert complet).
  2. cochannel_sinr: cand mai multi transmitatori emit pe aceeasi banda, SINR scade -> degradare
     dependenta de geometrie + trafic, nu doar de distanta.

Metodologie: nucleu pur + test_rf_interference.py. NU atinge nimic existent; alte module il DECOREAZA.
Decizii (OVERNIGHT_PLAN_2.md): model 4-param cu default simplu; co-canal disponibil dar integrarea e
Faza 2; parametri din sweep SINTETIC (nu calibrati pe trace real).
"""
import math
import random


class BurstProcess:
    """Gilbert-Elliott cu 2 stari: GOOD (G) si BAD (B).

    p = P(G->B), r = P(B->G). Pierdere conditionata de stare: loss_bad in B, loss_good in G.
    Default (loss_bad=1.0, loss_good=0.0) = Gilbert simplu: pierdere doar in rafale (in starea BAD).
    draw() avanseaza un pas (Markov) si intoarce True daca pachetul e PIERDUT.
    """

    GOOD, BAD = 0, 1

    def __init__(self, p, r, loss_bad=1.0, loss_good=0.0, seed=0, start_bad=False):
        if not (0.0 < p <= 1.0 and 0.0 < r <= 1.0):
            raise ValueError("p, r trebuie in (0, 1]")
        if not (0.0 <= loss_good <= loss_bad <= 1.0):
            raise ValueError("cer 0 <= loss_good <= loss_bad <= 1")
        self.p, self.r = p, r
        self.loss_bad, self.loss_good = loss_bad, loss_good
        self.state = self.BAD if start_bad else self.GOOD
        self._rng = random.Random(seed)

    @property
    def steady_bad(self):
        """Probabilitatea stationara de a fi in BAD = p/(p+r)."""
        return self.p / (self.p + self.r)

    @property
    def steady_loss(self):
        """Pierderea medie stationara: (r*loss_good + p*loss_bad)/(p+r)."""
        return (self.r * self.loss_good + self.p * self.loss_bad) / (self.p + self.r)

    @property
    def mean_burst_len(self):
        """Durata medie in starea BAD (proxy de lungime a rafalei) = 1/r."""
        return 1.0 / self.r

    def draw(self):
        """Avanseaza un pas si intoarce True = pachet PIERDUT."""
        if self.state == self.GOOD:
            if self._rng.random() < self.p:
                self.state = self.BAD
        else:
            if self._rng.random() < self.r:
                self.state = self.GOOD
        ploss = self.loss_bad if self.state == self.BAD else self.loss_good
        return self._rng.random() < ploss

    def to_netem_gemodel(self):
        """Sintaxa tc netem echivalenta: 'loss gemodel p% r% loss_bad% loss_good%'.
        Paritate de MODEL (aceiasi parametri/statistici) SIL <-> HIL, nu paritate de secventa."""
        return ("loss gemodel %.3f%% %.3f%% %.3f%% %.3f%%"
                % (100 * self.p, 100 * self.r, 100 * self.loss_bad, 100 * self.loss_good))

    @classmethod
    def from_steady(cls, steady_loss, mean_burst_len, seed=0):
        """Gilbert simplu (loss_bad=1, loss_good=0) dintr-o pierdere medie tinta si o lungime medie
        de rafala: r = 1/mean_burst_len; din steady=p/(p+r) -> p = steady*r/(1-steady)."""
        if not (0.0 < steady_loss < 1.0):
            raise ValueError("steady_loss in (0,1)")
        if mean_burst_len < 1.0:
            raise ValueError("mean_burst_len >= 1")
        r = 1.0 / mean_burst_len
        p = steady_loss * r / (1.0 - steady_loss)
        p = min(1.0, max(1e-9, p))
        return cls(p, r, loss_bad=1.0, loss_good=0.0, seed=seed)


def parse_netem_gemodel(s):
    """Invers partial al to_netem_gemodel: 'loss gemodel p% r% lb% lg%' -> (p,r,lb,lg) in [0,1]."""
    toks = s.replace("%", "").split()
    if len(toks) < 3 or toks[0] != "loss" or toks[1] != "gemodel":
        raise ValueError("nu e o clauza 'loss gemodel ...': %r" % (s,))
    nums = [float(t) / 100.0 for t in toks[2:6]]
    while len(nums) < 4:
        nums.append(0.0)
    return tuple(nums)


def cochannel_sinr(rx_dbm, interferers_dbm, noise_dbm=-95.0):
    """SINR (dB) si degradarea de interferenta (dB) la receptie co-canal.

    rx_dbm: puterea semnalului dorit la receptor [dBm]; interferers_dbm: lista de puteri ale
    interferentilor la acelasi receptor [dBm]; noise_dbm: zgomotul de fond [dBm].
    Intoarce (sinr_db, interference_db), unde interference_db = SNR - SINR = 10log10(1 + I/N) >= 0
    (cat a scazut SINR fata de cazul fara interferenta). Se da apoi la radio_link.loss_from_snr(snr - interference_db).
    """
    def mw(dbm):
        return 10.0 ** (dbm / 10.0)
    s = mw(rx_dbm)
    n = mw(noise_dbm)
    i = sum(mw(x) for x in interferers_dbm)
    sinr_db = 10.0 * math.log10(s / (n + i))
    interference_db = 10.0 * math.log10((n + i) / n)
    return sinr_db, interference_db


def conditions_gilbert(steady_losses=(0.20, 0.25, 0.30), burst_lens=(5.0, 5.0, 5.0)):
    """Intrari de tip CONDITIONS (gilbert_*) cu aceeasi pierdere medie ca loss_* dar rafale
    parametrizate. {nume: dict(name, type='gilbert', loss, mean_burst_len, p, r)}.
    SWEEP SINTETIC (parametrizat, nu calibrat pe trace real) -- OVERNIGHT_PLAN_2.md decizia 3.
    """
    out = {}
    for sl, bl in zip(steady_losses, burst_lens):
        bp = BurstProcess.from_steady(sl, bl)
        name = "gilbert_%d" % round(100 * sl)
        out[name] = dict(name=name, type="gilbert", loss=sl,
                         mean_burst_len=bl, p=bp.p, r=bp.r)
    return out


def _selftest():
    """Verificari pure, fara I/O. Apelat din test_rf_interference.py si din __main__."""
    bp = BurstProcess(p=0.1, r=0.4, loss_bad=1.0, loss_good=0.0, seed=1)
    assert abs(bp.steady_loss - (0.1 * 1.0) / (0.1 + 0.4)) < 1e-12
    assert abs(bp.mean_burst_len - 1.0 / 0.4) < 1e-12
    assert abs(bp.steady_bad - 0.2) < 1e-12

    # empiric: media pierderii ~ steady_loss pe N mare
    bp2 = BurstProcess(p=0.05, r=0.2, seed=7)
    N = 200000
    emp = sum(bp2.draw() for _ in range(N)) / N
    assert abs(emp - bp2.steady_loss) < 0.01, (emp, bp2.steady_loss)

    # determinism: acelasi seed -> aceeasi secventa
    a = [BurstProcess(0.1, 0.3, seed=42).draw() for _ in range(1000)]
    b = [BurstProcess(0.1, 0.3, seed=42).draw() for _ in range(1000)]
    assert a == b

    # from_steady recupereaza tinta
    bp3 = BurstProcess.from_steady(0.3, 5.0, seed=0)
    assert abs(bp3.steady_loss - 0.3) < 1e-9 and abs(bp3.mean_burst_len - 5.0) < 1e-9

    # netem gemodel: sintaxa + round-trip
    s = bp.to_netem_gemodel()
    assert s.startswith("loss gemodel ") and s.count("%") == 4
    p, r, lb, lg = parse_netem_gemodel(s)
    assert abs(p - 0.1) < 1e-3 and abs(r - 0.4) < 1e-3 and abs(lb - 1.0) < 1e-3 and abs(lg) < 1e-3

    # co-canal: SINR scade monoton in nr. interferenti; interference_db creste
    s0, i0 = cochannel_sinr(-60.0, [], noise_dbm=-95.0)
    s1, i1 = cochannel_sinr(-60.0, [-80.0], noise_dbm=-95.0)
    s2, i2 = cochannel_sinr(-60.0, [-80.0, -75.0], noise_dbm=-95.0)
    assert s0 > s1 > s2 and 0.0 == i0 < i1 < i2

    # conditions_gilbert
    cg = conditions_gilbert()
    assert "gilbert_30" in cg and abs(cg["gilbert_30"]["loss"] - 0.30) < 1e-9

    print("TOATE VERIFICARILE rf_interference AU TRECUT")


if __name__ == "__main__":
    _selftest()
