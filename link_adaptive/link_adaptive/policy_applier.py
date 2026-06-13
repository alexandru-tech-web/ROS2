#!/usr/bin/env python3
"""policy_applier.py - nucleul pur care APLICA o politica link_adaptive pe un flux.

link_adaptive_core DECIDE politica (mod + rata + fiabilitate + prag de prospetime
+ payload). Acest modul o APLICA pe un flux de mesaje (ex. telemetria roiului),
fara ROS, deci testabil izolat. Trei actiuni:
  1. limitarea ratei (downsampling): nu forward-eaza mai des decat rate_hz;
  2. aruncarea esantioanelor vechi: drop daca varsta > max_staleness_ms;
  3. reducerea payload-ului: FULL = tot; REDUCED = subset; CRITICAL = doar esential.

Schimbarea fiabilitatii (reliable<->best-effort) nu se face aici -- nucleul doar
o SEMNALEAZA (reliability_changed), iar nodul subtire isi recreeaza publisher-ul
cu noul QoS (QoS-ul nu se poate schimba pe un publisher existent in ROS 2).

Astfel bucla C3 se inchide: link_adaptive_node (decide) -> policy_adapter_node
(aplica) -> fluxul efectiv catre GCS se ajusteaza dupa starea legaturii, fara sa
modificam drone_node sau gcs_node.
"""
import math

# campurile pastrate la fiecare nivel de payload (configurabile ca sa se
# potriveasca schemei reale /sar/telemetry). FULL = pastreaza tot.
DEFAULT_REDUCED = ["id", "x", "y", "seq", "t", "soc", "phase"]
DEFAULT_CRITICAL = ["id", "x", "y", "seq", "t"]


class _Pol:
    """Politica minima acceptata de applier (acelasi camp ca link_adaptive_core.Policy)."""
    def __init__(self, rate_hz=20.0, reliable=True, max_staleness_ms=1000, payload="FULL"):
        self.rate_hz = rate_hz
        self.reliable = reliable
        self.max_staleness_ms = max_staleness_ms
        self.payload = payload


def _as_pol(p):
    """Accepta fie un obiect cu campurile cerute, fie un dict (de pe topic)."""
    if isinstance(p, dict):
        return _Pol(float(p.get("rate_hz", 20.0)), bool(p.get("reliable", True)),
                    float(p.get("max_staleness_ms", 1000)), str(p.get("payload", "FULL")))
    return p


class PolicyApplier:
    """Aplica politica curenta pe esantioane sosite. Pastreaza si statistici
    (cate intra / forward / aruncate pe rata / aruncate pe vechime)."""
    def __init__(self, reduced_fields=None, critical_fields=None):
        self.policy = _Pol()
        self.reduced = set(reduced_fields if reduced_fields is not None else DEFAULT_REDUCED)
        self.critical = set(critical_fields if critical_fields is not None else DEFAULT_CRITICAL)
        self.last_fwd = -1e18
        self.reliability_changed = False
        self.n_in = 0
        self.n_fwd = 0
        self.n_drop_rate = 0
        self.n_drop_stale = 0

    def set_policy(self, policy):
        """Actualizeaza politica. Intoarce True daca fiabilitatea s-a schimbat
        (nodul isi recreeaza publisher-ul cu noul QoS)."""
        new = _as_pol(policy)
        self.reliability_changed = (new.reliable != self.policy.reliable)
        self.policy = new
        return self.reliability_changed

    def on_sample(self, now_s, sample_time_s, payload):
        """Decide ce se intampla cu un esantion sosit la now_s, generat la
        sample_time_s. Intoarce payload-ul (eventual redus) de forward-at, sau
        None daca e aruncat."""
        self.n_in += 1
        # 1) prospetime: un esantion prea vechi e inutil (mai ales pentru control)
        if (now_s - sample_time_s) * 1000.0 > self.policy.max_staleness_ms:
            self.n_drop_stale += 1
            return None
        # 2) rata: nu forward-a mai des decat rate_hz
        min_dt = 1.0 / max(self.policy.rate_hz, 0.1)
        if (now_s - self.last_fwd) < min_dt - 1e-9:
            self.n_drop_rate += 1
            return None
        self.last_fwd = now_s
        self.n_fwd += 1
        # 3) payload: reduce campurile dupa nivel
        return self._reduce(payload)

    def _reduce(self, payload):
        if self.policy.payload == "FULL" or not isinstance(payload, dict):
            return dict(payload) if isinstance(payload, dict) else payload
        keep = self.critical if self.policy.payload == "CRITICAL" else self.reduced
        return {k: v for k, v in payload.items() if k in keep}

    def stats(self):
        return {"in": self.n_in, "fwd": self.n_fwd,
                "drop_rate": self.n_drop_rate, "drop_stale": self.n_drop_stale}


# ----------------------------- selftest -----------------------------
def _selftest():
    ok = 0; fail = []
    def check(name, cond, extra=""):
        nonlocal ok
        if cond: ok += 1
        else: fail.append(f"{name} {extra}")

    full = {"id": "d1", "x": 1.0, "y": 2.0, "z": 3.0, "seq": 5, "t": 10.0,
            "soc": 0.8, "phase": "scan", "cohesion": 0.9, "extra": "junk"}

    # --- limitarea ratei: 100 Hz intrare, politica 10 Hz -> ~10 forward ---
    ap = PolicyApplier()
    ap.set_policy(_Pol(rate_hz=10.0, reliable=False, max_staleness_ms=10000, payload="FULL"))
    t = 0.0
    for _ in range(100):
        ap.on_sample(t, t, full); t += 0.01      # 100 esantioane pe ~1 s
    check("rata: ~10 forward din 100 la 10 Hz", 9 <= ap.n_fwd <= 12, f"fwd={ap.n_fwd}")
    check("rata: restul aruncate pe rata", ap.n_drop_rate == 100 - ap.n_fwd,
          f"drop_rate={ap.n_drop_rate}")

    # --- prospetime: esantion vechi aruncat ---
    ap2 = PolicyApplier()
    ap2.set_policy(_Pol(rate_hz=100.0, reliable=False, max_staleness_ms=100, payload="FULL"))
    out_fresh = ap2.on_sample(1.0, 1.0, full)         # varsta 0
    out_old = ap2.on_sample(2.0, 1.7, full)           # varsta 300 ms > 100
    check("prospetime: esantionul proaspat trece", out_fresh is not None)
    check("prospetime: esantionul vechi e aruncat", out_old is None and ap2.n_drop_stale == 1)

    # --- reducerea payload-ului ---
    ap3 = PolicyApplier()
    ap3.set_policy(_Pol(rate_hz=100.0, max_staleness_ms=10000, payload="FULL"))
    f = ap3.on_sample(0.0, 0.0, full)
    check("FULL pastreaza toate campurile", set(f.keys()) == set(full.keys()))
    ap3.set_policy(_Pol(rate_hz=100.0, max_staleness_ms=10000, payload="REDUCED"))
    r = ap3.on_sample(1.0, 1.0, full)
    check("REDUCED pastreaza doar subsetul", set(r.keys()) == (set(DEFAULT_REDUCED) & set(full)),
          f"chei={sorted(r.keys())}")
    check("REDUCED chiar reduce", len(r) < len(full))
    ap3.set_policy(_Pol(rate_hz=100.0, max_staleness_ms=10000, payload="CRITICAL"))
    c = ap3.on_sample(2.0, 2.0, full)
    check("CRITICAL pastreaza doar esentialul", set(c.keys()) == (set(DEFAULT_CRITICAL) & set(full)),
          f"chei={sorted(c.keys())}")
    check("CRITICAL <= REDUCED ca dimensiune", len(c) <= len(r))

    # --- semnalarea schimbarii de fiabilitate ---
    ap4 = PolicyApplier()                              # implicit reliable=True
    changed1 = ap4.set_policy(_Pol(reliable=False))    # True->False
    changed2 = ap4.set_policy(_Pol(reliable=False))    # False->False
    changed3 = ap4.set_policy(_Pol(reliable=True))     # False->True
    check("schimbare fiabilitate detectata (T->F)", changed1 is True)
    check("nicio schimbare cand ramane la fel", changed2 is False)
    check("schimbare detectata (F->T)", changed3 is True)

    # --- payload non-dict tolerat ---
    ap5 = PolicyApplier()
    ap5.set_policy(_Pol(rate_hz=100.0, max_staleness_ms=10000, payload="CRITICAL"))
    check("payload non-dict trece neatins", ap5.on_sample(0.0, 0.0, "sir-brut") == "sir-brut")

    print(f"[selftest] {ok} verificari trecute" + (f", {len(fail)} ESUATE:" if fail else ", toate OK"))
    for x in fail:
        print("   FAIL:", x)
    return not fail


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
