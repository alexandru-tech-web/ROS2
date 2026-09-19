#!/usr/bin/env python3
"""confidence_core.py -- nucleul pur al lui C4: alpha (increderea in retea) si VARSTA informatiei de la pereche,
in doua estimari calculate in paralel. Fara ROS. Spec: DOC/CAIETE/P0_SPEC_RECONSTRUIT.md (RECONSTRUIT).

Mostre: roverul trimite mostra i la t_tx_i (ceasul LOCAL, monoton); ecoul intors soseste la t_rx_i (acelasi ceas) si
poarta si marcajul de timp al perechii stamp_i (ceasul PERECHII, wall). Toate marimile de mai jos sunt in secunde.

  alpha(mostre, T_dead, W) = (mostre la timp: intoarse cu RTT_i = t_rx_i - t_tx_i <= T_dead, dintre ultimele W trimise) / min(W, trimise)
      fara nicio mostra trimisa -> 0.0 (fereastra partiala: numitorul e cate s-au trimis)
  (a) age_stamp(t_now)  = t_now_wall - stamp_ultim        -- CORECTA doar cu ceasuri comune; jurnalizata, NICIODATA in control
  (b) age_sonda(t_now)  = RTT_ultim / 2 + (t_now - t_rx_ultim)   -- numai ceasul local: varsta informatiei purtate de ultimul ecou
      in momentul sosirii (RTT/2, cai presupuse simetrice; asimetria e eroare de cel mult RTT/2) plus timpul scurs de atunci.
      fara nicio mostra intoarsa -> t_now - t_start (varsta creste liniar de la pornire; blackout: liniar de la ultima intoarsa)
  Filtrul C6 / arbitrajul C5 primesc (b).
  python3 confidence_core.py --selftest   (5 cazuri)
"""
import sys
from collections import deque

T_DEAD = 0.25       # s, parametru ROS in nod
W = 20              # mostre (2 s la 10 Hz)


class Fereastra(object):
    """Ultimele W mostre trimise; fiecare: [t_tx, t_rx sau None, stamp sau None]."""

    def __init__(self, T_dead=T_DEAD, W_=W, t_start=0.0):
        self.T_dead, self.W, self.t_start = float(T_dead), int(W_), float(t_start)
        self.mostre = deque(maxlen=self.W)
        self.seq = 0
        self.ultim = None                   # (t_tx, t_rx, stamp) al ultimei mostre INTOARSE

    def trimite(self, t_tx):
        self.seq += 1
        self.mostre.append([self.seq, float(t_tx), None, None])
        return self.seq

    def intoarsa(self, seq, t_rx, stamp=None):
        """Ecoul mostrei seq a sosit la t_rx (local); stamp = marcajul perechii (optional)."""
        for m in self.mostre:
            if m[0] == seq:
                m[2], m[3] = float(t_rx), stamp
                rtt = m[2] - m[1]
                if self.ultim is None or m[2] >= self.ultim[1]:
                    self.ultim = (m[1], m[2], stamp, rtt)
                return rtt
        return None                          # mostra prea veche (a iesit din fereastra) sau necunoscuta

    def alpha(self, t_now=None):
        """Mostrele DECISE = intoarse, sau neintoarse dar mai vechi decat T_dead (au expirat). Cele neintoarse si mai
        tinere decat T_dead sunt IN ASTEPTARE si nu intra in numitor (altfel plafonul ar fi (W-1)/W la fiecare tick)."""
        if not self.mostre:
            return 0.0
        dec = [m for m in self.mostre if m[2] is not None or (t_now is not None and t_now - m[1] >= self.T_dead)]
        if t_now is None:
            dec = list(self.mostre)
        if not dec:
            return 0.0
        n_ok = sum(1 for m in dec if m[2] is not None and (m[2] - m[1]) <= self.T_dead)
        return n_ok / float(len(dec))

    def age_sonda(self, t_now):
        if self.ultim is None:
            return float(t_now) - self.t_start
        t_tx, t_rx, _, rtt = self.ultim
        return rtt / 2.0 + (float(t_now) - t_rx)

    def age_stamp(self, t_now_wall):
        if self.ultim is None or self.ultim[2] is None:
            return None
        return float(t_now_wall) - float(self.ultim[2])


def alpha(mostre, T_dead=T_DEAD, W_=W, t_now=None):
    """Forma functionala: mostre = lista de (t_tx, t_rx sau None); ia ultimele W; t_now decide ce e in asteptare."""
    f = Fereastra(T_dead, W_)
    for t_tx, t_rx in mostre:
        s = f.trimite(t_tx)
        if t_rx is not None:
            f.intoarsa(s, t_rx)
    return f.alpha(t_now)


def _selftest():
    ok = []
    # (1) fara pierderi, ceasuri comune: a ~ b (diferenta = RTT/2 - asimetrie = RTT/2 cu ecou instantaneu simetric)
    f = Fereastra(0.25, 20, t_start=0.0)
    for i in range(30):
        t = 0.1 * i; s = f.trimite(t); f.intoarsa(s, t + 0.020, stamp=t + 0.010)      # RTT 20 ms, stamp la mijloc
    a, b = f.age_stamp(3.0), f.age_sonda(3.0)
    assert f.alpha() == 1.0 and abs(a - b) < 1e-9, (f.alpha(), a, b)
    ok.append("(1) fara pierderi: alpha=1.0, age_stamp=%.3f age_sonda=%.3f (identice cu ecou simetric)" % (a, b))
    # (2) blackout: ambele cresc liniar cu t
    f = Fereastra(0.25, 20, t_start=0.0)
    for i in range(20):
        t = 0.1 * i; s = f.trimite(t); f.intoarsa(s, t + 0.02, stamp=t + 0.01)
    for i in range(20, 60):
        f.trimite(0.1 * i)                                                              # nimic nu se intoarce
    a1, b1 = f.age_stamp(3.0), f.age_sonda(3.0); a2, b2 = f.age_stamp(5.0), f.age_sonda(5.0)
    assert f.alpha() == 0.0 and abs((a2 - a1) - 2.0) < 1e-9 and abs((b2 - b1) - 2.0) < 1e-9, (a1, a2, b1, b2)
    ok.append("(2) blackout: alpha=0.0, ambele varste cresc cu 2.000 s in 2 s (liniar): a %.3f->%.3f, b %.3f->%.3f" % (a1, a2, b1, b2))
    # (3) deviatie de ceas +1.0 s pe stamp-ul perechii: (a) se strica cu 1 s, (b) neschimbata
    f0, f1 = Fereastra(0.25, 20), Fereastra(0.25, 20)
    for i in range(30):
        t = 0.1 * i
        s0 = f0.trimite(t); f0.intoarsa(s0, t + 0.02, stamp=t + 0.01)
        s1 = f1.trimite(t); f1.intoarsa(s1, t + 0.02, stamp=t + 0.01 + 1.0)
    da, db = f1.age_stamp(3.0) - f0.age_stamp(3.0), f1.age_sonda(3.0) - f0.age_sonda(3.0)
    assert abs(da + 1.0) < 1e-9 and abs(db) < 1e-12, (da, db)
    ok.append("(3) deviatie +1.0 s pe stamp: age_stamp se muta cu %.3f s, age_sonda cu %.1e s (neschimbata)" % (da, db))
    # (4) RTT asimetric (dus 10 ms, intors 90 ms): b = RTT/2 + scurs -> eroare fata de adevar (dus) = 40 ms <= RTT/2
    f = Fereastra(0.25, 20)
    for i in range(30):
        t = 0.1 * i; s = f.trimite(t); f.intoarsa(s, t + 0.100, stamp=t + 0.010)
    t_now = 3.05; b = f.age_sonda(t_now); adevar = t_now - (2.9 + 0.010)               # informatia perechii generata la t_tx + dus (10 ms)
    assert abs(b - adevar) <= 0.100 / 2 + 1e-9, (b, adevar)
    ok.append("(4) RTT asimetric dus 10 / intors 90 ms: age_sonda=%.3f vs adevar %.3f: eroare %.3f, marginita de RTT/2=0.050 (semnul depinde de calea lenta)" % (b, adevar, b - adevar))
    # (5) fereastra partiala: 5 mostre trimise, 4 intoarse la timp, 1 tarzie (RTT 300 ms > T_dead)
    f = Fereastra(0.25, 20)
    for i in range(5):
        t = 0.1 * i; s = f.trimite(t); f.intoarsa(s, t + (0.30 if i == 2 else 0.02))
    assert abs(f.alpha(t_now=1.0) - 0.8) < 1e-9 and alpha([(0, 0.02), (0.1, None)], 0.25, 20, t_now=1.0) == 0.5
    assert alpha([(0, 0.02), (0.1, None)], 0.25, 20, t_now=0.2) == 1.0          # a doua e IN ASTEPTARE (0.1 s < T_dead)
    ok.append("(5) fereastra partiala: 5 trimise, 4 la timp, 1 tarzie -> alpha=0.8; 2 mostre/1 pierduta -> 0.5; 1 in asteptare -> 1.0")
    for l in ok:
        print("  " + l)
    print("SELFTEST confidence_core OK (5 cazuri).")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else 0)
