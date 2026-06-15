#!/usr/bin/env python3
"""
sar_core.py — Nucleul misiunii Search & Rescue (Python pur, fara ROS).

Lumea: grila de ocupare cu ruine (no-fly), zone de fum (raza senzorului
redusa) si victime. Dronele dezvaluie celule in jurul lor (cartografiere),
GCS-ul fuzioneaza hartile (cooperative mapping), frontierele (celule libere
vazute, adiacente necunoscutului) sunt alocate dronelor, drumurile ocolesc
ruinele prin A*. Victimele sunt detectate cand celula lor e dezvaluita.

Metrici: acoperire (% din celulele libere vazute), victime gasite, coeziunea
roiului. Comportamente de avarie (fallback) la pierderea legaturii cu GCS:
LOCAL_EXPLORE -> RETURN_TO_LINK -> LOITER.
"""

import heapq
import math

UNKNOWN, FREE_SEEN, OBSTACLE_SEEN = 0, 1, 2


class GridWorld:
    """Adevarul-teren + harta descoperita (per drona sau fuzionata la GCS)."""

    def __init__(self, w_cells: int, h_cells: int, cell: float,
                 ruins=None, smoke=None, victims=None):
        self.w, self.h, self.cell = int(w_cells), int(h_cells), float(cell)
        self.obstacle = [[False] * self.w for _ in range(self.h)]
        for (cx0, cy0, cx1, cy1) in (ruins or []):
            for j in range(max(0, cy0), min(self.h, cy1 + 1)):
                for i in range(max(0, cx0), min(self.w, cx1 + 1)):
                    self.obstacle[j][i] = True
        self.smoke = list(smoke or [])          # (cx, cy, raza_celule)
        self.victims = [tuple(v) for v in (victims or [])]
        self.total_free = sum(1 for j in range(self.h) for i in range(self.w)
                              if not self.obstacle[j][i])

    # ---- conversii ----
    def to_cell(self, x: float, y: float):
        return (max(0, min(self.w - 1, int(x / self.cell))),
                max(0, min(self.h - 1, int(y / self.cell))))

    def to_xy(self, ci: int, cj: int):
        return ((ci + 0.5) * self.cell, (cj + 0.5) * self.cell)

    def in_smoke(self, ci, cj) -> bool:
        return any((ci - sx) ** 2 + (cj - sy) ** 2 <= r * r
                   for sx, sy, r in self.smoke)


class DiscoveredMap:
    """Harta cunoscuta (a unei drone sau fuzionata la GCS)."""

    def __init__(self, world: GridWorld):
        self.world = world
        self.state = [[UNKNOWN] * world.w for _ in range(world.h)]
        self.seen_free = 0

    def reveal_disc(self, x: float, y: float, radius_m: float,
                    smoke_factor: float = 0.4):
        """Dezvaluie celulele pe un disc; in fum, raza scade. Returneaza
        (celule_noi:[(i,j,stare)], victime_detectate:[(i,j)])."""
        w = self.world
        ci, cj = w.to_cell(x, y)
        r = radius_m / w.cell
        if w.in_smoke(ci, cj):
            r *= smoke_factor
        rc = int(math.ceil(r))
        new_cells, found = [], []
        for j in range(max(0, cj - rc), min(w.h, cj + rc + 1)):
            for i in range(max(0, ci - rc), min(w.w, ci + rc + 1)):
                if (i - ci) ** 2 + (j - cj) ** 2 > r * r:
                    continue
                if self.state[j][i] != UNKNOWN:
                    continue
                st = OBSTACLE_SEEN if w.obstacle[j][i] else FREE_SEEN
                self.state[j][i] = st
                if st == FREE_SEEN:
                    self.seen_free += 1
                new_cells.append((i, j, st))
                if (i, j) in w.victims:
                    found.append((i, j))
        return new_cells, found

    def merge_cells(self, cells):
        """Fuziune cooperativa: aplica diff-urile primite de la o drona."""
        for (i, j, st) in cells:
            if self.state[j][i] == UNKNOWN:
                self.state[j][i] = st
                if st == FREE_SEEN:
                    self.seen_free += 1

    def coverage(self) -> float:
        return self.seen_free / max(1, self.world.total_free)

    def frontiers(self):
        """Celule libere vazute adiacente (4-vec) necunoscutului."""
        out = []
        st, w, h = self.state, self.world.w, self.world.h
        for j in range(h):
            for i in range(w):
                if st[j][i] != FREE_SEEN:
                    continue
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ni, nj = i + di, j + dj
                    if 0 <= ni < w and 0 <= nj < h and st[nj][ni] == UNKNOWN:
                        out.append((i, j))
                        break
        return out

    def astar(self, start, goal):
        """A* 4-vecini pe harta cunoscuta (necunoscut = traversabil optimist,
        obstacol vazut = blocat). Returneaza lista de celule sau None."""
        w, h, st = self.world.w, self.world.h, self.state
        if st[goal[1]][goal[0]] == OBSTACLE_SEEN:
            return None
        openq = [(0.0, start)]
        g = {start: 0.0}
        came = {}
        while openq:
            _, cur = heapq.heappop(openq)
            if cur == goal:
                path = [cur]
                while cur in came:
                    cur = came[cur]
                    path.append(cur)
                return path[::-1]
            ci, cj = cur
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = ci + di, cj + dj
                if not (0 <= ni < w and 0 <= nj < h):
                    continue
                if st[nj][ni] == OBSTACLE_SEEN:
                    continue
                ng = g[cur] + 1.0
                if ng < g.get((ni, nj), 1e18):
                    g[(ni, nj)] = ng
                    came[(ni, nj)] = cur
                    f = ng + abs(ni - goal[0]) + abs(nj - goal[1])
                    heapq.heappush(openq, (f, (ni, nj)))
        return None


def allocate_frontiers(drone_pos: dict, frontiers, min_sep_cells: float = 4.0):
    """Alocare lacoma: fiecare drona primeste cea mai apropiata frontiera
    nealocata, cu separare minima intre tinte (evita ingramadeala).
    drone_pos: {id: (ci, cj)}. Returneaza {id: (ci, cj)}."""
    remaining = list(frontiers)
    out = {}
    for did in sorted(drone_pos):
        if not remaining:
            break
        ci, cj = drone_pos[did]
        remaining.sort(key=lambda f: (f[0] - ci) ** 2 + (f[1] - cj) ** 2)
        pick = None
        for f in remaining:
            ok = all((f[0] - t[0]) ** 2 + (f[1] - t[1]) ** 2
                     >= min_sep_cells ** 2 for t in out.values())
            if ok:
                pick = f
                break
        if pick is None:
            pick = remaining[0]
        out[did] = pick
        remaining = [f for f in remaining
                     if (f[0] - pick[0]) ** 2 + (f[1] - pick[1]) ** 2
                     >= min_sep_cells ** 2]
    return out


def cohesion(positions, radius_m: float = 25.0) -> float:
    """Fractia perechilor de drone aflate sub raza data (1.0 = roi compact)."""
    ids = list(positions)
    if len(ids) < 2:
        return 1.0
    pairs = ok = 0
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            xa, ya = positions[ids[a]][:2]
            xb, yb = positions[ids[b]][:2]
            pairs += 1
            if (xa - xb) ** 2 + (ya - yb) ** 2 <= radius_m ** 2:
                ok += 1
    return ok / pairs


# ---------- comportamentul de avarie (fallback) la pierderea GCS ----------
LINKED, LOCAL_EXPLORE, RETURN_TO_LINK, LOITER = (
    "LINKED", "LOCAL_EXPLORE", "RETURN_TO_LINK", "LOITER")


class FallbackPolicy:
    """LINKED -> (link pierdut) -> LOCAL_EXPLORE (t_local s, continua misiunea
    pe harta locala) -> RETURN_TO_LINK (zboara spre ultimul punct cu legatura)
    -> LOITER (cerc lent). Orice mesaj de la GCS readuce in LINKED."""

    def __init__(self, t_local: float = 15.0):
        self.state = LINKED
        self.t_local = t_local
        self.lost_at = None
        self.last_link_pos = (0.0, 0.0)

    def on_gcs_contact(self, pos_xy):
        self.state = LINKED
        self.lost_at = None
        self.last_link_pos = tuple(pos_xy)

    def on_link_lost(self, t: float):
        if self.state == LINKED:
            self.state = LOCAL_EXPLORE
            self.lost_at = t

    def tick(self, t: float, pos_xy, reached_link_pos: bool):
        if self.state == LOCAL_EXPLORE and t - self.lost_at >= self.t_local:
            self.state = RETURN_TO_LINK
        if self.state == RETURN_TO_LINK and reached_link_pos:
            self.state = LOITER
        return self.state
