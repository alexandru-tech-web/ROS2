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
  python3 confidence_core.py --selftest   (v1: 5 cazuri; v2: S1-S8 + controalele negative)

v2 (P0-1, DOC/CAIETE/PLAN_P0_1.md 4073918a, RATIFICAT 08.10.2026; spec DOC/CAIETE/P0_SPEC_V2.md): `FereastraViab` = fereastra
de viabilitate a gateway-ului C3, transcrisa din c3_gateway/nodes/gateway_node.py (Cale, _citeste_ecouri, _expira_in_zbor,
_goleste_in_zbor): o sonda se rezolva o data -- 1 la ecoul procesat cat e in zbor, 0 la expirare (t_now - t_trimis > T_sonda,
strict) sau la golire; fereastra = ultimele W REZULTATE in ordinea rezolvarii; alpha = k / n (0.0 la n = 0) =
switching.Viabilitate.livrare. 'Calea e vie in 1 s', nu punctualitate: latenta trece prin varsta (age). Ce e pur in C3
(Viabilitate, Comutator / regula E1) se importa, intarziat (_switching). `Fereastra` de mai jos = v1 INLOCUITA, pastrata
doar pentru reproducerea DATE/C4/2026-09-23_redare_din_c3_PROBA (DOC/BORD/tools/redare_c4_din_c3.py).
"""
import os
import sys
from collections import deque

T_DEAD = 0.25       # s, parametru ROS in nod
W = 20              # mostre (2 s la 10 Hz)


class Fereastra(object):
    """v1 INLOCUITA (P0-1): ultimele W mostre trimise; fiecare: [t_tx, t_rx sau None, stamp sau None]."""

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


# ------------------------------------------------------------------------------------------------ v2 (P0-1)
HZ_SONDA = 5.0              # gateway_node.py --hz-sonda (implicit 5.0); Etapa A: manifest hz_sonda_viabilitate 5.0
W_VIAB = 50                 # switching.FEREASTRA_VIAB = gateway_node.py --fereastra-sonda (implicit 50)
T_SONDA = 1.0               # s, gateway_node.py --timeout-ecou (implicit 1.0); Etapa A: c3_hil.py T_SONDA_S = 1.0
PERIOADA_EXPIRARE = 0.05    # s, gateway_node.py l. 157: create_timer(0.05, self._expira)


def _switching():
    """Nucleul pur C3 (c3_gateway/core/switching.py; importa doar sys): instalat, altfel din sursa, ca gateway_node.py l. 47-52."""
    try:
        from c3_gateway.core import switching
        return switching
    except ImportError:
        aici = os.path.dirname(os.path.abspath(__file__))
        core = os.path.normpath(os.path.join(aici, "..", "..", "c3_gateway", "c3_gateway", "core"))
        if core not in sys.path:
            sys.path.insert(0, core)
        import switching                                            # noqa: E402
        return switching


class FereastraViab(object):
    """Fereastra de viabilitate C3 (sec. 2 din PLAN_P0_1). Timpii in orice unitate, aceeasi cu T_sonda (nodul: s, selftest: ms).
    in_zbor e un dict: ordinea insertiei = ordinea trimiterii, ca la gateway (expirarile din acelasi apel, in ordinea trimiterii)."""

    def __init__(self, W_=W_VIAB, T_sonda=T_SONDA, t_start=0.0):
        self.W, self.T_sonda, self.t_start = int(W_), T_sonda, t_start
        self.fereastra = deque(maxlen=self.W)
        self.in_zbor = {}                    # seq -> t_trimis
        self.ultim = None                    # (t_rx, rtt, stamp) al ecoului procesat cel mai proaspat (dupa t_rx), si tarziu

    def _noteaza(self, primit):
        self.fereastra.append(1 if primit else 0)

    def trimite(self, seq, t):
        self.in_zbor[seq] = t

    def ecou(self, seq, t_rx, t_tx=None, stamp=None):
        """Ecoul PROCESAT al sondei seq. In zbor -> 1 in fereastra; tarziu (deja expirata) / necunoscut -> fereastra neschimbata.
        Varsta se actualizeaza cu orice ecou cu RTT cunoscut (t_tx din zbor sau din mesajul ecoului), daca e cel mai proaspat."""
        t_z = self.in_zbor.pop(seq, None)
        t0 = t_z if t_z is not None else t_tx
        if t0 is not None and (self.ultim is None or t_rx >= self.ultim[0]):
            self.ultim = (t_rx, t_rx - t0, stamp)
        if t_z is None:
            return False
        self._noteaza(True)
        return True

    def expira(self, t_now):
        """Ce e in zbor de MAI MULT de T_sonda (strict, gateway_node.py l. 277) -> 0, in ordinea trimiterii."""
        exp = [s for s, t in self.in_zbor.items() if t_now - t > self.T_sonda]
        for s in exp:
            del self.in_zbor[s]
            self._noteaza(False)
        return len(exp)

    def goleste(self):
        """La oprire, tot ce e in zbor -> 0, dupa seq (gateway_node.py _goleste_in_zbor)."""
        exp = sorted(self.in_zbor)
        for _ in exp:
            self._noteaza(False)
        self.in_zbor.clear()
        return len(exp)

    def rezolvata(self, primit, t_rx=None, rtt=None):
        """Reluare: un rezultat deja rezolvat de gateway (un rand P din esantioane.csv)."""
        self._noteaza(primit)
        if primit and t_rx is not None and rtt is not None and (self.ultim is None or t_rx >= self.ultim[0]):
            self.ultim = (t_rx, rtt, None)

    def k(self):
        return sum(self.fereastra)

    def n(self):
        return len(self.fereastra)

    def alpha(self):
        return self.k() / float(self.n()) if self.fereastra else 0.0

    def viabilitate(self):
        return _switching().Viabilitate(self.n(), self.k())

    def age(self, t_now):
        """AoI clasic: RTT_ultim / 2 + (t_now - t_rx_ultim); fara niciun ecou: t_now - t_start."""
        if self.ultim is None:
            return t_now - self.t_start
        return self.ultim[1] / 2.0 + (t_now - self.ultim[0])

    def age_stamp(self, t_now_wall):
        if self.ultim is None or self.ultim[2] is None:
            return None
        return float(t_now_wall) - float(self.ultim[2])


class _Politica(object):
    """Doar ce cere Comutator.__init__ / _evacuare (implicitul); tabela nu se consulta (d = None)."""
    def __init__(self, implicit):
        self.implicit = implicit


def comutator_e1(transport_initial):
    """Comutatorul C3 importat, pentru regula E1 (_evacuare): praguri 0.10 / 0.50, MIN_ESANTIOANE_CANDIDAT 20 -- ale lui."""
    if not transport_initial:
        raise ValueError("transport_initial lipsa: Comutator ar cadea pe implicitul tabelei (revizia B2)")
    sw = _switching()
    return sw.Comutator(_Politica(transport_initial), 4096, transport_initial=transport_initial)


def evacueaza(com, acum, ferestre):
    """E1 pe ferestrele date ({cale: FereastraViab}). Intoarce calea noua daca E1 a COMUTAT (motiv 'evacuare'), altfel None
    ('nicio cale viabila' = E3, fara comutare)."""
    inainte = com.transport
    r = com._evacuare(acum, {c: f.viabilitate() for c, f in ferestre.items()}, None)
    if r is not None and r[0] != inainte and r[1].startswith("evacuare"):
        return r[0]
    return None


# --- controalele negative (mutanti): fiecare trebuie sa pice un caz din motivul lui
class _MutantGe(FereastraViab):
    def expira(self, t_now):                 # >= in loc de >
        exp = [s for s, t in self.in_zbor.items() if t_now - t >= self.T_sonda]
        for s in exp:
            del self.in_zbor[s]
            self._noteaza(False)
        return len(exp)


class _MutantOrdineSeq(FereastraViab):
    """Fereastra ordonata dupa seq (ordinea trimiterii), nu dupa rezolvare."""
    def __init__(self, *a, **k):
        FereastraViab.__init__(self, *a, **k)
        self._toate = []                     # (seq, rezultat)
        self._seq_curent = None

    def ecou(self, seq, t_rx, t_tx=None, stamp=None):
        self._seq_curent = seq
        return FereastraViab.ecou(self, seq, t_rx, t_tx, stamp)

    def expira(self, t_now):
        exp = [s for s, t in self.in_zbor.items() if t_now - t > self.T_sonda]
        for s in exp:
            del self.in_zbor[s]
            self._seq_curent = s
            self._noteaza(False)
        return len(exp)

    def _noteaza(self, primit):
        self._toate.append((self._seq_curent, 1 if primit else 0))
        self._toate.sort(key=lambda x: x[0])
        self.fereastra = deque((r for _, r in self._toate[-self.W:]), maxlen=self.W)


def _simuleaza(f, t0, taie, verificari, rtt=15, n_inainte=50, pana_la=None, perioada=200):
    """Sonde la t = t0 - n_inainte*perioada, ..., din perioada in perioada (ms intregi); cele trimise la t >= taie nu se intorc.
    Expirarea se verifica DOAR in momentele din `verificari`; intoarce {t: (k, n)} in acele momente (dupa verificare)."""
    ev = []
    t, seq = t0 - n_inainte * perioada, 0
    pana_la = pana_la if pana_la is not None else max(verificari)
    while t <= pana_la:
        seq += 1
        ev.append((t, 1, "trimite", seq))
        if taie is None or t < taie:
            ev.append((t + rtt, 2, "ecou", seq))
        t += perioada
    for v in verificari:
        ev.append((v, 0, "verifica", None))      # la acelasi moment, verificarea inaintea trimiterii (ca un tick separat)
    ev.sort()
    out = {}
    for t, _, ce, s in ev:
        if ce == "trimite":
            f.trimite(s, t)
        elif ce == "ecou":
            f.ecou(s, t)
        else:
            f.expira(t)
            out[t] = (f.k(), f.n())
    return out


def _selftest_v2():
    ok = []
    T0 = 10000                                                            # ms; taietura la o trimitere
    V = [T0 + 5799, T0 + 5800, T0 + 5801, T0 + 9999, T0 + 10001]
    # S1 / S2
    f = FereastraViab(W_VIAB, 1000)
    _simuleaza(f, 0, None, [12000], n_inainte=0)
    assert f.alpha() == 1.0 and f.n() == 50, (f.k(), f.n())
    f = FereastraViab(W_VIAB, 1000)
    _simuleaza(f, 0, 0, [11801 + 1000], n_inainte=0, pana_la=11800)
    assert f.alpha() == 0.0 and f.n() == 50, (f.k(), f.n())
    ok.append("S1 toate intoarse -> alpha 1.00, n 50; S2 niciuna -> alpha 0.00, n 50")
    # S3 taietura (strict >, ms intregi)
    def s3(f):
        return _simuleaza(f, T0, T0, V)
    r = s3(FereastraViab(W_VIAB, 1000))
    assert r[T0 + 5799] == (26, 50) and r[T0 + 5800] == (26, 50) and r[T0 + 5801] == (25, 50), r
    assert r[T0 + 9999] == (5, 50) and r[T0 + 10001] == (4, 50), r
    ok.append("S3 taietura la t0: 0.52 la t0+5799/5800 ms, 0.50 la t0+5801; 0.10 la t0+9999, 0.08 la t0+10001 (strict >)")
    # S4 ecou tarziu
    f = FereastraViab(W_VIAB, 1000)
    f.trimite(1, 0); f.expira(1001)
    k, n = f.k(), f.n()
    assert (k, n) == (0, 1) and f.ecou(1, 1200, t_tx=0) is False and (f.k(), f.n()) == (k, n), (f.k(), f.n())
    assert f.ultim[0] == 1200 and f.ultim[1] == 1200 and abs(f.age(1300) - (600 + 100)) < 1e-9
    ok.append("S4 ecou tarziu: fereastra neschimbata (0/1), varsta actualizata (RTT 1200 -> age 700 la +100)")
    # S5 ordinea rezolvarii, fereastra plina
    def s5(f):
        s = 0
        for i in range(50):                                               # fereastra plina de 1
            s += 1; f.trimite(s, i * 200); f.ecou(s, i * 200 + 15)
        s += 1; a = s; f.trimite(a, 10000)                                # A ramane in zbor
        for i in range(1, 6):                                             # B1..B5 trimise si intoarse
            s += 1; f.trimite(s, 10000 + i * 200); f.ecou(s, 10000 + i * 200 + 15)
        f.expira(11001)                                                   # A expira: 0-ul intra ULTIMUL
        val = []
        for i in range(6, 6 + 45):                                        # inca 45 intoarse
            s += 1; f.trimite(s, 10000 + i * 200); f.ecou(s, 10000 + i * 200 + 15)
            val.append((f.k(), f.n()))
        return val
    v = s5(FereastraViab(W_VIAB, 1000))
    assert v[-1] == (49, 50), v[-1]                                       # 0-ul lui A inca in fereastra (46-lea de la capat)
    ok.append("S5 ordinea rezolvarii: dupa A expirata + 45 intoarse, 0-ul e inca in fereastra -> 49/50")
    # S6 traiul = reluarea
    class _Inreg(FereastraViab):
        def __init__(self, *a, **k):
            FereastraViab.__init__(self, *a, **k); self.rez = []
        def _noteaza(self, primit):
            FereastraViab._noteaza(self, primit); self.rez.append((1 if primit else 0, self.k(), self.n()))
    f = _Inreg(W_VIAB, 1000)
    s3(f)
    g = FereastraViab(W_VIAB, 1000)
    for p, k, n in f.rez:
        g.rezolvata(p)
        assert (g.k(), g.n()) == (k, n), (g.k(), g.n(), k, n)
    ok.append("S6 trimite/ecou/expira = rezolvata pe aceeasi secventa (%d rezultate, k/n identice la fiecare pas)" % len(f.rez))
    # S7 E1 importat
    sw = _switching()
    # reface starea la fiecare verificare si judeca E1 (comutatorul e acelasi pe toate verificarile)
    def judeca(trans_init, taie_z, taie_c):
        com = comutator_e1(trans_init)
        decizii = {}
        for v_ in V:
            fz, fc = FereastraViab(W_VIAB, 1000), FereastraViab(W_VIAB, 1000)
            _simuleaza(fz, T0, taie_z, [v_]); _simuleaza(fc, T0, taie_c, [v_])
            decizii[v_] = evacueaza(com, v_, {"zenoh": fz, "cyclonedds": fc})
        return decizii, com
    d, com = judeca("zenoh", T0, None)
    assert d[T0 + 9999] is None and d[T0 + 10001] == "cyclonedds", d
    d2, com2 = judeca("zenoh", T0, T0)
    assert all(x is None for x in d2.values()) and com2.transport == "zenoh" and com2.nicio_cale_viabila, (d2, com2.transport)
    f = FereastraViab(W_VIAB, 1000)
    for i in range(19):
        f.rezolvata(0)
    com3 = comutator_e1("zenoh")
    assert evacueaza(com3, 0, {"zenoh": f, "cyclonedds": FereastraViab(W_VIAB, 1000)}) is None and com3.transport == "zenoh"
    try:
        comutator_e1(None)
        raise AssertionError("transport_initial None acceptat")
    except ValueError:
        pass
    ok.append("S7 E1 importat (%s): evacuare la t0+10001 ms, nu la t0+9999; ambele taiate -> nicio cale viabila, fara "
              "comutare; sub 20 de rezultate -> nicio decizie; transport_initial None refuzat" % os.path.basename(sw.__file__))
    # S8 varsta (v1 1, 2, 4 pe v2; secunde)
    f = FereastraViab(W_VIAB, 1.0, t_start=0.0)
    for i in range(30):
        t = 0.2 * i; f.trimite(i, t); f.ecou(i, t + 0.020, stamp=t + 0.010)
    a, b = f.age_stamp(6.0), f.age(6.0)
    assert abs(a - b) < 1e-9, (a, b)
    f = FereastraViab(W_VIAB, 1.0, t_start=0.0)
    for i in range(20):
        t = 0.2 * i; f.trimite(i, t); f.ecou(i, t + 0.02)
    for i in range(20, 60):
        f.trimite(i, 0.2 * i)
    b1, b2 = f.age(5.0), f.age(7.0)
    assert abs((b2 - b1) - 2.0) < 1e-9
    f = FereastraViab(W_VIAB, 1.0)
    for i in range(30):
        t = 0.2 * i; f.trimite(i, t); f.ecou(i, t + 0.100, stamp=t + 0.010)
    t_now = 6.05; b = f.age(t_now); adevar = t_now - (5.8 + 0.010)
    assert abs(b - adevar) <= 0.050 + 1e-9, (b, adevar)
    f = FereastraViab(W_VIAB, 1.0, t_start=2.0)
    assert f.age(5.0) == 3.0
    ok.append("S8 varsta: = age_stamp cu ecou simetric; blackout liniar (+2.000 s in 2 s); asimetrie <= RTT/2; fara ecou t-t_start")
    # controalele negative: fiecare pica din motivul lui
    cn = []
    r49 = s3(FereastraViab(49, 1000))
    cn.append(("W=49", r49[T0 + 5801] != (25, 50)))
    r250 = s3(FereastraViab(W_VIAB, 250))
    cn.append(("T_sonda=250", r250[T0 + 5801] != (25, 50)))
    rge = s3(_MutantGe(W_VIAB, 1000))
    cn.append((">=", rge[T0 + 5800] == (25, 50) and rge[T0 + 5800] != (26, 50)))
    vs = s5(_MutantOrdineSeq(W_VIAB, 1000))
    cn.append(("ordine dupa seq", vs[-1] == (50, 50)))
    assert all(x for _, x in cn), cn
    ok.append("controale negative: W=49 pica S3 (%s la t0+5801), T_sonda=250 pica S3 (%s), '>=' pica S3 la t0+5800 (%s in loc de "
              "26/50), ordinea dupa seq pica S5 (%s in loc de 49/50)" % ("%d/%d" % r49[T0 + 5801], "%d/%d" % r250[T0 + 5801],
                                                                         "%d/%d" % rge[T0 + 5800], "%d/%d" % vs[-1]))
    for l in ok:
        print("  " + l)
    print("SELFTEST confidence_core v2 OK (S1-S8 + %d controale negative)." % len(cn))
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest() or _selftest_v2())
    sys.exit(0)
