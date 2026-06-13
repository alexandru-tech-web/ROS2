#!/usr/bin/env python3
"""link_adaptive_core.py - nucleu pur pentru stratul adaptiv (contributia C3).

Fara ROS, fara retea: logica de decizie, testabila izolat (conventia
depozitului). Premisa vine din campania C1 (N=5): NICIUN middleware nu domina --
DDS cumpara supravietuirea misiunii cu intarziere uniforma, Zenoh cumpara
prospetimea cu pierderi. Concluzia: daca niciunul nu domina, ADAPTEAZA-TE.

Acest strat masoara starea legaturii (RTT p95 + rata de pierdere) si comuta
intre trei moduri de comportament, cu HISTEREZIS si timp minim de stationare ca
sa nu palpaie pe frontiere:

  NOMINAL  - legatura buna: rata plina, livrare fiabila si completa, fara
             aruncarea esantioanelor vechi (poti avea si prospetime, si completitudine).
  DEGRADED - legatura medie: prioritizeaza controlul (best-effort + arunca vechi,
             prospetime), telemetria ramane fiabila dar la rata redusa.
  CRITICAL - legatura proasta: doar esential (heartbeat + comanda cea mai
             proaspata), arunca agresiv vechi, descarca telemetria neesentiala
             ca sa protejeze legatura pentru ce conteaza.

Nucleul nu trimite nimic: decide POLITICA. Nodul subtire (link_adaptive_node)
aplica politica si o publica; ceilalti consumatori isi ajusteaza comportamentul.
"""
import collections
import math

# ----------------------------- moduri si politici -----------------------------
NOMINAL = "NOMINAL"
DEGRADED = "DEGRADED"
CRITICAL = "CRITICAL"
ORDER = {NOMINAL: 0, DEGRADED: 1, CRITICAL: 2}   # severitate crescatoare


class Policy:
    """Politica de date pentru un mod. payload: FULL / REDUCED / CRITICAL."""
    def __init__(self, mode, rate_hz, reliable, max_staleness_ms, payload):
        self.mode = mode
        self.rate_hz = rate_hz
        self.reliable = reliable
        self.max_staleness_ms = max_staleness_ms   # arunca esantioane mai vechi de atat
        self.payload = payload

    def as_dict(self):
        return {"mode": self.mode, "rate_hz": self.rate_hz,
                "reliable": self.reliable, "max_staleness_ms": self.max_staleness_ms,
                "payload": self.payload}


# rata plina si livrare completa cand legatura permite; pe masura ce se degradeaza,
# rata scade, controlul trece pe best-effort proaspat, telemetria se reduce/descarca.
POLICIES = {
    NOMINAL:  Policy(NOMINAL,  20.0, reliable=True,  max_staleness_ms=1000, payload="FULL"),
    DEGRADED: Policy(DEGRADED, 10.0, reliable=False, max_staleness_ms=300,  payload="REDUCED"),
    CRITICAL: Policy(CRITICAL,  2.0, reliable=False, max_staleness_ms=100,  payload="CRITICAL"),
}

# ----------------------------- praguri (cu histerezis) -----------------------------
# Intrare (inrautatire) - praguri mai sus; Iesire (imbunatatire) - praguri mai jos.
# Banda dintre iesire si intrare absoarbe zgomotul si previne palpairea.
DEG_ENTER_RTT = 150.0;  DEG_ENTER_LOSS = 0.05    # NOMINAL  -> DEGRADED
CRIT_ENTER_RTT = 800.0; CRIT_ENTER_LOSS = 0.20   # ... -> CRITICAL
DEG_EXIT_RTT = 100.0;   DEG_EXIT_LOSS = 0.02     # DEGRADED -> NOMINAL
CRIT_EXIT_RTT = 500.0;  CRIT_EXIT_LOSS = 0.12    # CRITICAL -> DEGRADED
MIN_DWELL_S = 2.0                                # timp minim intre schimbari


# ----------------------------- monitorul de legatura -----------------------------
def percentile(values, p):
    """Percentila p (0..100) dintr-o lista (interpolare liniara)."""
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * (p / 100.0)
    lo = math.floor(k); hi = math.ceil(k)
    if lo == hi:
        return float(s[int(k)])
    return s[lo] * (hi - k) + s[hi] * (k - lo)


class LinkMonitor:
    """Estimeaza starea legaturii din masuratori brute:
    - RTT p95 dintr-o fereastra glisanta de masuratori dus-intors [ms];
    - rata de pierdere din golurile numerelor de secventa, pe o fereastra."""
    def __init__(self, rtt_window=50, seq_window=100):
        self.rtt = collections.deque(maxlen=rtt_window)
        self.seq = collections.deque(maxlen=seq_window)

    def ingest_rtt(self, rtt_ms):
        if rtt_ms is not None and rtt_ms >= 0:
            self.rtt.append(float(rtt_ms))

    def ingest_seq(self, seq):
        self.seq.append(int(seq))

    def rtt_p95(self):
        return percentile(list(self.rtt), 95)

    def loss(self):
        """Fractie pierduta = 1 - primite/asteptate pe fereastra (secvente
        monoton crescatoare). Robust la reordonare in cadrul ferestrei."""
        if len(self.seq) < 2:
            return 0.0
        lo, hi = min(self.seq), max(self.seq)
        expected = hi - lo + 1
        received = len(set(self.seq))
        if expected <= 0:
            return 0.0
        return max(0.0, 1.0 - received / expected)

    def metrics(self):
        return self.rtt_p95(), self.loss()


# ----------------------------- controlerul adaptiv -----------------------------
class AdaptiveController:
    """Mentine modul curent si decide tranzitiile cu histerezis + stationare.
    update() returneaza (mod, Policy) pentru masuratorile curente."""
    def __init__(self, start=NOMINAL, min_dwell_s=MIN_DWELL_S):
        self.mode = start
        self.min_dwell_s = min_dwell_s
        self.last_change = -1e9
        self.transitions = 0

    def _target(self, rtt, loss):
        """Modul tinta pentru masuratorile curente, tinand cont de modul curent
        (praguri de intrare la inrautatire, de iesire la imbunatatire).
        Intrarea foloseste '>' strict: valoarea pragului e plafonul modului mai
        bun (ex. pana la 5% pierdere inclusiv = inca NOMINAL)."""
        m = self.mode
        if m == NOMINAL:
            if rtt > CRIT_ENTER_RTT or loss > CRIT_ENTER_LOSS:
                return CRITICAL
            if rtt > DEG_ENTER_RTT or loss > DEG_ENTER_LOSS:
                return DEGRADED
            return NOMINAL
        if m == DEGRADED:
            if rtt > CRIT_ENTER_RTT or loss > CRIT_ENTER_LOSS:
                return CRITICAL
            if rtt <= DEG_EXIT_RTT and loss <= DEG_EXIT_LOSS:
                return NOMINAL
            return DEGRADED
        # CRITICAL: coboara treptat la DEGRADED (nu direct la NOMINAL)
        if rtt <= CRIT_EXIT_RTT and loss <= CRIT_EXIT_LOSS:
            return DEGRADED
        return CRITICAL

    def update(self, rtt_p95_ms, loss_frac, now_s):
        target = self._target(rtt_p95_ms, loss_frac)
        if target != self.mode and (now_s - self.last_change) >= self.min_dwell_s:
            self.mode = target
            self.last_change = now_s
            self.transitions += 1
        return self.mode, POLICIES[self.mode]


# ----------------------------- selftest -----------------------------
def _selftest():
    ok = 0
    fail = []

    def check(name, cond, extra=""):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fail.append(f"{name} {extra}")

    # --- percentila ---
    check("p95 lista goala = 0", percentile([], 95) == 0.0)
    check("p95 constanta", abs(percentile([5, 5, 5], 95) - 5) < 1e-9)
    check("p95 ~ max pentru sir crescator",
          percentile(list(range(1, 101)), 95) >= 95)

    # --- monitor: loss din secvente ---
    mon = LinkMonitor()
    for s in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
        mon.ingest_seq(s)
    check("fara goluri -> loss 0", abs(mon.loss()) < 1e-9, f"{mon.loss():.3f}")
    mon2 = LinkMonitor()
    for s in [1, 2, 4, 6, 8, 10]:        # 6 din 10 asteptate
        mon2.ingest_seq(s)
    check("4 din 10 pierdute -> loss 0.4", abs(mon2.loss() - 0.4) < 1e-9,
          f"{mon2.loss():.3f}")
    mon3 = LinkMonitor()
    for r in [10, 12, 11, 200, 13, 14]:
        mon3.ingest_rtt(r)
    check("rtt_p95 reflecta coada", mon3.rtt_p95() > 14, f"{mon3.rtt_p95():.1f}")

    # --- clasificare la conditiile C1 (rtt impus, pierdere impusa) ---
    # (rtt_ms, loss, mod asteptat) - reflecta degradarea netem din campanie
    cases = [
        ("ideal", 20, 0.00, NOMINAL),
        ("loss_5", 20, 0.05, NOMINAL),        # exact pe pragul de intrare -> ramane
        ("loss_15", 20, 0.15, DEGRADED),
        ("loss_30", 20, 0.30, CRITICAL),
        ("lat200_jit50", 200, 0.00, DEGRADED),
        ("lat200_l15", 200, 0.15, DEGRADED),
    ]
    for name, rtt, loss, expect in cases:
        c = AdaptiveController()
        # las controlerul sa se stabilizeze (dwell) hranindu-l de cateva ori
        t = 0.0
        for _ in range(5):
            mode, _pol = c.update(rtt, loss, t)
            t += MIN_DWELL_S
        check(f"clasificare {name} -> {expect}", mode == expect, f"a dat {mode}")

    # --- histerezis: NU palpaie in banda dintre iesire si intrare ---
    c = AdaptiveController()
    t = 0.0
    # urca in DEGRADED
    for _ in range(3):
        c.update(20, 0.15, t); t += MIN_DWELL_S
    check("a intrat in DEGRADED", c.mode == DEGRADED)
    tr0 = c.transitions
    # oscileaza pierderea in banda (0.03..0.06): peste exit 0.02, in jurul enter 0.05
    for i in range(20):
        c.update(20, 0.03 if i % 2 == 0 else 0.06, t); t += MIN_DWELL_S
    check("histerezis: nu palpaie in banda", c.transitions == tr0 and c.mode == DEGRADED,
          f"tranzitii in plus={c.transitions - tr0}, mod={c.mode}")

    # --- timp minim de stationare: nu schimba mai des decat min_dwell ---
    c = AdaptiveController(min_dwell_s=2.0)
    c.update(20, 0.15, 0.0)              # vrea DEGRADED la t=0
    check("prima tranzitie permisa la start", c.mode == DEGRADED)
    c.update(20, 0.00, 0.5)              # vrea NOMINAL dar prea curand (0.5<2.0)
    check("stationare: tranzitia prea rapida e blocata", c.mode == DEGRADED,
          f"mod={c.mode}")
    c.update(20, 0.00, 3.0)              # acum a trecut destul timp
    check("stationare: tranzitia permisa dupa dwell", c.mode == NOMINAL,
          f"mod={c.mode}")

    # --- coborare treptata din CRITICAL ---
    c = AdaptiveController()
    t = 0.0
    for _ in range(3):
        c.update(20, 0.30, t); t += MIN_DWELL_S   # urca in CRITICAL
    check("a intrat in CRITICAL", c.mode == CRITICAL)
    c.update(20, 0.00, t); t += MIN_DWELL_S         # legatura perfecta brusc
    check("din CRITICAL coboara intai la DEGRADED, nu direct NOMINAL",
          c.mode == DEGRADED, f"mod={c.mode}")

    # --- politicile sunt monoton mai conservatoare cu severitatea ---
    rates = [POLICIES[m].rate_hz for m in (NOMINAL, DEGRADED, CRITICAL)]
    stale = [POLICIES[m].max_staleness_ms for m in (NOMINAL, DEGRADED, CRITICAL)]
    check("rata scade cu severitatea", rates[0] > rates[1] > rates[2], f"{rates}")
    check("pragul de prospetime scade cu severitatea",
          stale[0] > stale[1] > stale[2], f"{stale}")
    check("CRITICAL renunta la fiabilitate", POLICIES[CRITICAL].reliable is False)

    print(f"[selftest] {ok} verificari trecute"
          + (f", {len(fail)} ESUATE:" if fail else ", toate OK"))
    for f in fail:
        print("   FAIL:", f)
    return not fail


if __name__ == "__main__":
    import sys
    ok = _selftest()
    print("\n--- demo: traiectoria modurilor pe conditiile C1 ---")
    c = AdaptiveController()
    t = 0.0
    seq = [("ideal", 20, 0.0), ("loss_15", 20, 0.15), ("loss_30", 20, 0.30),
           ("lat200_jit50", 200, 0.0), ("ideal", 20, 0.0)]
    for name, rtt, loss in seq:
        for _ in range(3):
            mode, pol = c.update(rtt, loss, t); t += MIN_DWELL_S
        print(f"  {name:14s} rtt={rtt:3d}ms loss={loss:.0%} -> {mode:8s} "
              f"(rata {pol.rate_hz:.0f}Hz, {'fiabil' if pol.reliable else 'best-effort'}, "
              f"payload {pol.payload})")
    sys.exit(0 if ok else 1)
