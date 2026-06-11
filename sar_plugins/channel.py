#!/usr/bin/env python3
"""channel.py — DegradedChannel: canal de comunicatie degradat, reutilizabil.

Acelasi model ca gating-ul din robot_node.py (cadere + pierdere + latenta +
jitter, aplicate la "receptie"), dar extras intr-o clasa pura, fara ROS2,
ca sa poata fi folosit de: link-ul radio per-drona, canalul video simulat
si orice proxy de mesaje. Testabil pe orice masina.

Conventii:
  - timpul e float, secunde (time.time() sau ceasul simularii);
  - push() intoarce True daca mesajul a intrat in canal (nu a fost pierdut);
  - pop_ready(t) intoarce mesajele a caror intarziere a expirat, in ordinea
    livrarii; implicit livrarea e monotona (fara reordonare), ca un flux TCP
    sau o coada ARQ — se poate dezactiva cu monotonic=False.
"""
import heapq
import random


class DegradedChannel:
    def __init__(self, ms=0.0, jit_ms=0.0, loss=0.0, down=False,
                 monotonic=True, seed=None):
        self.ms = float(ms)            # latenta medie [ms]
        self.jit_ms = float(jit_ms)    # deviatia jitterului [ms], gaussian>=0
        self.loss = float(loss)        # probabilitatea de pierdere [0..1]
        self.down = bool(down)         # legatura cazuta complet
        self.monotonic = bool(monotonic)
        self.rng = random.Random(seed)
        self._heap = []                # (t_livrare, nr_secventa, payload)
        self._seq = 0
        self._last_sched = -1e18       # ultima livrare programata (monoton)
        # statistici
        self.n_sent = 0
        self.n_dropped = 0
        self.n_delivered = 0

    # ---- configurare ----
    def set_state(self, ms=None, jit_ms=None, loss=None, down=None):
        if ms is not None:
            self.ms = float(ms)
        if jit_ms is not None:
            self.jit_ms = float(jit_ms)
        if loss is not None:
            self.loss = min(max(float(loss), 0.0), 1.0)
        if down is not None:
            self.down = bool(down)

    def set_from_dict(self, d):
        """Accepta schema /teleop/linkstate: {"ms":..,"jit":..,"loss":..,
        "down":..} — cheile lipsa raman neschimbate."""
        self.set_state(ms=d.get("ms"), jit_ms=d.get("jit"),
                       loss=d.get("loss"), down=d.get("down"))

    # ---- trafic ----
    def push(self, t_now, payload):
        """Trimite un mesaj prin canal la momentul t_now."""
        self.n_sent += 1
        if self.down or self.rng.random() < self.loss:
            self.n_dropped += 1
            return False
        delay = self.ms / 1000.0
        if self.jit_ms > 0.0:
            delay += abs(self.rng.gauss(0.0, self.jit_ms / 1000.0))
        t_del = t_now + max(delay, 0.0)
        if self.monotonic:
            t_del = max(t_del, self._last_sched)
            self._last_sched = t_del
        heapq.heappush(self._heap, (t_del, self._seq, payload))
        self._seq += 1
        return True

    def pop_ready(self, t_now):
        """Mesajele a caror livrare a ajuns la scadenta, ca lista
        [(t_livrare, payload), ...]."""
        out = []
        while self._heap and self._heap[0][0] <= t_now:
            t_del, _, payload = heapq.heappop(self._heap)
            self.n_delivered += 1
            out.append((t_del, payload))
        return out

    def pending(self):
        return len(self._heap)

    def clear(self):
        self._heap.clear()

    @property
    def delivery_ratio(self):
        return 0.0 if self.n_sent == 0 else (self.n_sent - self.n_dropped) / self.n_sent

    def stats(self):
        return {"sent": self.n_sent, "dropped": self.n_dropped,
                "delivered": self.n_delivered, "pending": self.pending(),
                "ratio": round(self.delivery_ratio, 4)}
