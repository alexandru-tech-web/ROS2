#!/usr/bin/env python3
"""
netem_core.py — Modelul de degradare a retelei (Python pur).

Canal de mesaje intre noduri (gcs, d1..dN) cu, per legatura:
  - latenta de baza + jitter gaussian,
  - pierdere de pachete (probabilitate),
  - legatura sus/jos (izolare drona, partitie de roi, ferestre programate),
  - varfuri de latenta programate (ex. GCS delay spike 50 ms -> 2000 ms).

Tolerare la intreruperi: STORE-AND-FORWARD optional — mesajele catre o
legatura cazuta se pun in tampon (capacitate limitata) si se livreaza
la restabilire (delay-tolerant, in ordinea emiterii).

MODUL DE INREGISTRARE: canalul masoara per legatura trimise / pierdute /
livrate / tamponate, esantioanele de latenta, timpul deconectat si timpul
de recuperare dupa restabilire. Scenariile se incarca din FISIERE YAML
SEPARATE (un fisier per caz de simulare).
"""

import heapq
import random


def link_key(a: str, b: str) -> str:
    return "-".join(sorted((a, b)))


class LinkState:
    def __init__(self, base_ms=40.0, jitter_ms=10.0, loss=0.0):
        self.base_ms = float(base_ms)
        self.jitter_ms = float(jitter_ms)
        self.loss = float(loss)
        self.up = True
        # statistici (modulul de inregistrare)
        self.sent = self.lost = self.delivered = self.buffered = 0
        self.lat_samples = []          # ms, doar mesaje livrate
        self.down_since = None
        self.down_total = 0.0
        self.recovery_times = []       # s: restabilire -> prima livrare

    def snapshot(self):
        lat = sorted(self.lat_samples)
        p95 = lat[int(0.95 * (len(lat) - 1))] if lat else 0.0
        mean = sum(lat) / len(lat) if lat else 0.0
        meas_loss = self.lost / max(1, self.sent)
        return {"sent": self.sent, "lost": self.lost,
                "delivered": self.delivered, "buffered": self.buffered,
                "lat_mean_ms": mean, "lat_p95_ms": p95,
                "loss_measured": meas_loss, "down_total_s": self.down_total,
                "recovery_times_s": list(self.recovery_times),
                "lat_samples": list(self.lat_samples)}


class Channel:
    """Canalul degradat dintre toate nodurile. Determinist cu seed."""

    def __init__(self, nodes, default=None, overrides=None,
                 store_and_forward=True, buffer_cap=400, seed=1):
        self.rng = random.Random(seed)
        self.links = {}
        d = default or {}
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                k = link_key(a, b)
                spec = dict(d)
                spec.update((overrides or {}).get(k, {}))
                self.links[k] = LinkState(
                    spec.get("base_ms", 40.0), spec.get("jitter_ms", 10.0),
                    spec.get("loss", 0.0))
        self.saf = store_and_forward
        self.cap = buffer_cap
        self.buffers = {k: [] for k in self.links}     # (t_emis, src, dst, msg)
        self._q = []                                   # heap (t_livrare, seq, ...)
        self._seq = 0
        self._restored_at = {}                         # k -> t restabilire

    # ---------- controlul legaturilor (evenimentele scenariului) ----------
    def set_link(self, a, b, *, up=None, base_ms=None, jitter_ms=None,
                 loss=None, t=0.0):
        L = self.links[link_key(a, b)]
        if base_ms is not None:
            L.base_ms = float(base_ms)
        if jitter_ms is not None:
            L.jitter_ms = float(jitter_ms)
        if loss is not None:
            L.loss = float(loss)
        if up is not None and up != L.up:
            L.up = up
            if not up:
                L.down_since = t
            else:
                if L.down_since is not None:
                    L.down_total += t - L.down_since
                    L.down_since = None
                self._restored_at[link_key(a, b)] = t
                self._flush(link_key(a, b), t)

    def isolate(self, node, t):
        for k in self.links:
            if node in k.split("-"):
                a, b = k.split("-")
                self.set_link(a, b, up=False, t=t)

    def restore(self, node, t):
        for k in self.links:
            if node in k.split("-"):
                a, b = k.split("-")
                self.set_link(a, b, up=True, t=t)

    def partition(self, group_a, group_b, t):
        """Taie toate legaturile intre grupul A si grupul B."""
        for a in group_a:
            for b in group_b:
                self.set_link(a, b, up=False, t=t)

    # ---------- trafic ----------
    def send(self, src, dst, msg, t):
        k = link_key(src, dst)
        L = self.links[k]
        L.sent += 1
        if not L.up:
            if self.saf and len(self.buffers[k]) < self.cap:
                self.buffers[k].append((t, src, dst, msg))
                L.buffered += 1
            else:
                L.lost += 1
            return
        if self.rng.random() < L.loss:
            L.lost += 1
            return
        lat = max(1.0, L.base_ms + self.rng.gauss(0.0, L.jitter_ms))
        self._push(t + lat / 1000.0, t, src, dst, msg)

    def _push(self, t_del, t_emis, src, dst, msg):
        self._seq += 1
        heapq.heappush(self._q, (t_del, self._seq, t_emis, src, dst, msg))

    def _flush(self, k, t):
        """La restabilire: livreaza tamponul cu ritm de 50 msg/s."""
        L = self.links[k]
        for n, (t0, src, dst, msg) in enumerate(self.buffers[k]):
            lat = max(1.0, L.base_ms + self.rng.gauss(0.0, L.jitter_ms))
            self._push(t + n * 0.02 + lat / 1000.0, t0, src, dst, msg)
        self.buffers[k].clear()

    def deliver(self, t):
        """Returneaza mesajele scadente: lista (src, dst, msg, t_emis)."""
        out = []
        while self._q and self._q[0][0] <= t:
            t_del, _, t0, src, dst, msg = heapq.heappop(self._q)
            k = link_key(src, dst)
            L = self.links[k]
            L.delivered += 1
            L.lat_samples.append((t_del - t0) * 1000.0)
            if k in self._restored_at:
                L.recovery_times.append(t_del - self._restored_at.pop(k))
            out.append((src, dst, msg, t0, t_del))
        return out

    def link_up(self, a, b) -> bool:
        return self.links[link_key(a, b)].up

    def stats(self):
        return {k: L.snapshot() for k, L in self.links.items()}


# ---------- scenarii din fisiere YAML separate ----------
def load_scenario(path):
    import yaml
    with open(path) as f:
        sc = yaml.safe_load(f)
    sc.setdefault("name", path)
    sc.setdefault("duration_s", 120)
    sc.setdefault("default_link", {})
    sc.setdefault("link_overrides", {})
    sc.setdefault("events", [])
    sc.setdefault("store_and_forward", True)
    sc["events"].sort(key=lambda e: e.get("t", 0))
    return sc


def apply_due_events(channel: Channel, events, t_prev, t_now):
    """Aplica evenimentele cu t in (t_prev, t_now]."""
    for ev in events:
        te = float(ev.get("t", 0))
        if not (t_prev < te <= t_now):
            continue
        typ = ev["type"]
        if typ == "isolate":
            channel.isolate(ev["node"], te)
        elif typ == "restore_node":
            channel.restore(ev["node"], te)
        elif typ == "partition":
            channel.partition(ev["group_a"], ev["group_b"], te)
        elif typ == "heal_partition":
            for a in ev["group_a"]:
                for b in ev["group_b"]:
                    channel.set_link(a, b, up=True, t=te)
        elif typ == "set_link":
            channel.set_link(ev["a"], ev["b"], t=te,
                             base_ms=ev.get("base_ms"),
                             jitter_ms=ev.get("jitter_ms"),
                             loss=ev.get("loss"), up=ev.get("up"))
        elif typ == "set_all":
            for k in channel.links:
                a, b = k.split("-")
                channel.set_link(a, b, t=te,
                                 base_ms=ev.get("base_ms"),
                                 jitter_ms=ev.get("jitter_ms"),
                                 loss=ev.get("loss"))
