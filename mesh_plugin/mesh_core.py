#!/usr/bin/env python3
"""mesh_core.py -- nucleul pur al retelei mesh multi-hop (fara ROS2).

Schimba topologia roiului din STEA (fiecare drona vorbeste DIRECT cu GCS)
in MESH: o drona fara legatura directa cu GCS ajunge prin vecini (relay
hop-by-hop). Feeds contributia C3 a tezei.

De ce conteaza (legat de rezultate): in topologia stea, o legatura cazuta
orbeste GCS-ul (acoperirea/victimele se crediteaza doar din telemetria
LIVRATA). Stratul mesh recupereaza valoarea pierduta: daca d3 il aude pe d1
si d1 aude GCS, atunci d3 ajunge la GCS prin d1. Exact scenariul partition_2v2,
unde d3/d4 erau izolate.

Patru niveluri (aliniate la literatura - De Couto 2004 ETX, OLSR/BATMAN/Babel):

  1. Model radio: distanta -> PDR (probabilitate de livrare a unui pachet).
     Refoloseste LogDistanceRadioLink din radio_link.py (acelasi model fizic
     ca restul proiectului): PDR = 1 - loss(distanta).
  2. Metrica: ETX = 1 / (PDR_fwd * PDR_rev)  (Expected Transmission Count, De
     Couto MIT 2004). Leaga rutarea de pierderea de pachete - aceeasi moneda
     ca tot restul tezei. ETX=1 link perfect, ETX->inf link mort.
  3. Rutare: graf de adiacenta cu cost ETX pe muchii; Dijkstra catre GCS;
     tabel next-hop per nod. pdr_min defineste "exista o legatura".
  4. Relay: DIRECTED, hop-by-hop. Fiecare pachet poarta 'next' (vecinul care
     trebuie sa-l preia); doar acela il preia, isi recalculeaza next-hop,
     decrementeaza TTL, deduplica dupa (src, seq). NU flooding.

Conventii (ca swarm_core/sar_core): pozitii in metri; fara dependinte ROS;
totul determinist si testabil cu un _selftest() la final.
"""
import heapq
import math


# ============================================================
# 1. Model radio -> PDR
# ============================================================
def pdr_from_link(link, d_m, shadowed=False):
    """Probabilitatea de livrare a unui pachet (Packet Delivery Ratio) la
    distanta d_m, din modelul radio. link e un LogDistanceRadioLink (din
    radio_link.py). shadowed=False pentru rutare stabila (umbra adauga
    zgomot per-apel; rutarea vrea o estimare neteda).
    PDR in [pdr_floor, 1]. Link cazut -> 0."""
    st = link.state_for_distance(d_m, shadowed=shadowed)
    if st["down"]:
        return 0.0
    return max(0.0, 1.0 - float(st["loss"]))


# ============================================================
# 2. Metrica ETX
# ============================================================
ETX_INF = float("inf")


def etx(pdr_fwd, pdr_rev=None):
    """ETX = 1 / (PDR_fwd * PDR_rev). Daca pdr_rev lipseste, link simetric
    (pdr_rev = pdr_fwd). PDR 0 -> ETX infinit (link inutilizabil)."""
    pf = float(pdr_fwd)
    pr = pf if pdr_rev is None else float(pdr_rev)
    prod = pf * pr
    if prod <= 0.0:
        return ETX_INF
    return 1.0 / prod


# ============================================================
# 3. Topologie + rutare (Dijkstra pe cost ETX)
# ============================================================
class MeshGraph:
    """Graf de adiacenta intre noduri (drone + 'gcs'), cu cost ETX pe muchii
    bidirectionale. Pozitiile dau distantele; modelul radio da PDR -> ETX.

    nodes: dict id -> (x, y[, z]). 'gcs' e doar un id ca oricare altul.
    link: LogDistanceRadioLink comun (acelasi profil radio pentru toti).
    pdr_min: sub acest PDR pe o directie, muchia NU exista (link prea slab).
    """

    def __init__(self, link, pdr_min=0.10):
        self.link = link
        self.pdr_min = float(pdr_min)
        self.pos = {}
        self.edges = {}        # (a,b) ord. -> etx ; chei cu a<b
        self.down_nodes = set()  # noduri blocate manual (drona doborata/oprita)

    # ---- intretinerea topologiei ----
    def set_positions(self, positions):
        """positions: dict id -> (x, y[, z]). Recalculeaza toate muchiile."""
        self.pos = {k: tuple(map(float, v[:2])) for k, v in positions.items()}
        self._rebuild_edges()

    def block_node(self, node):
        """Scoate un nod din retea (drona doborata / radio mort): toate
        muchiile lui dispar. Folosit de demo-ul 'blocheaza drona'."""
        self.down_nodes.add(node)
        self._rebuild_edges()

    def unblock_node(self, node):
        self.down_nodes.discard(node)
        self._rebuild_edges()

    def _dist(self, a, b):
        (ax, ay), (bx, by) = self.pos[a], self.pos[b]
        return math.hypot(ax - bx, ay - by)

    def _rebuild_edges(self):
        self.edges = {}
        ids = [n for n in self.pos if n not in self.down_nodes]
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                d = self._dist(a, b)
                pdr = pdr_from_link(self.link, d)
                # link bidirectional simetric (acelasi PDR ambele sensuri)
                if pdr >= self.pdr_min:
                    key = (a, b) if a < b else (b, a)   # cheie sortata, ca edge_etx
                    self.edges[key] = etx(pdr, pdr)

    def neighbors(self, node):
        """Vecinii directi ai unui nod + costul ETX al muchiei."""
        out = {}
        for (a, b), c in self.edges.items():
            if a == node:
                out[b] = c
            elif b == node:
                out[a] = c
        return out

    def edge_etx(self, a, b):
        key = (a, b) if a < b else (b, a)
        return self.edges.get(key, ETX_INF)

    # ---- Dijkstra catre o destinatie (de obicei 'gcs') ----
    def shortest_paths_to(self, dest="gcs"):
        """Dijkstra pe cost ETX. Intoarce (dist, next_hop) unde:
          dist[n]     = ETX total de la n la dest (inf daca inaccesibil)
          next_hop[n] = primul vecin pe drumul de la n la dest (None daca
                        e dest sau inaccesibil).
        Rulam Dijkstra DIN dest (graf nedirectionat) si reconstruim next-hop."""
        dist = {n: ETX_INF for n in self.pos if n not in self.down_nodes}
        if dest not in dist:
            return dist, {n: None for n in dist}
        prev = {n: None for n in dist}
        dist[dest] = 0.0
        pq = [(0.0, dest)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for v, w in self.neighbors(u).items():
                nd = d + w
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u            # v -> u e pasul spre dest
                    heapq.heappush(pq, (nd, v))
        # next_hop[n] = prev[n] (primul pas de la n inapoi spre dest)
        next_hop = {n: prev[n] for n in dist}
        next_hop[dest] = None
        return dist, next_hop

    def reachable_set(self, dest="gcs"):
        """Multimea nodurilor care AJUNG la dest (ETX finit)."""
        dist, _ = self.shortest_paths_to(dest)
        return {n for n, d in dist.items() if d < ETX_INF and n != dest}

    def hop_count_to(self, dest="gcs"):
        """Numarul de hopuri (nu ETX) de la fiecare nod la dest, pe drumul
        ales de Dijkstra. Util pentru 'cate hopuri foloseste relay-ul'."""
        _, nh = self.shortest_paths_to(dest)
        out = {}
        for n in self.pos:
            if n in self.down_nodes or n == dest:
                out[n] = 0
                continue
            hops, cur, seen = 0, n, set()
            while cur is not None and cur != dest and cur not in seen:
                seen.add(cur)
                cur = nh.get(cur)
                hops += 1
                if hops > len(self.pos) + 1:
                    hops = -1            # bucla (nu ar trebui sa apara)
                    break
            out[n] = hops if cur == dest else -1
        return out


# ============================================================
# 4. Relay dirijat hop-by-hop (dedup + TTL)
# ============================================================
class DirectedRelay:
    """Un releu pe fiecare nod. Trimite un pachet spre 'gcs' punand in el
    'next' = next-hop-ul curent. Doar nodul egal cu 'next' il preia, isi
    recalculeaza propriul next-hop, decrementeaza TTL si deduplica dupa
    (src, seq). NU flooding -> trafic minim, fara furtuni de broadcast.

    Pachet (dict): {src, seq, ttl, next, path, payload}
    """

    def __init__(self, node_id, ttl=8):
        self.id = node_id
        self.ttl_default = int(ttl)
        self.seen = set()          # (src, seq) deja procesate (dedup)
        self._seq = 0

    def new_packet(self, graph, payload, dest="gcs"):
        """Creeaza un pachet de la acest nod spre dest. Intoarce pachetul
        sau None daca nodul nu are ruta (next-hop inexistent)."""
        _, nh = graph.shortest_paths_to(dest)
        nxt = nh.get(self.id)
        if nxt is None:
            return None
        self._seq += 1
        return {"src": self.id, "seq": self._seq, "ttl": self.ttl_default,
                "next": nxt, "path": [self.id], "payload": payload}

    def on_receive(self, pkt, graph, dest="gcs"):
        """Proceseaza un pachet primit. Intoarce:
          ('deliver', pkt)   daca acest nod ESTE dest (livrat la GCS)
          ('forward', pkt2)  daca trebuie retransmis (next actualizat)
          ('drop', motiv)    daca e duplicat / TTL expirat / nu e pt mine /
                             fara ruta mai departe.
        """
        # nu e pentru mine?
        if pkt.get("next") != self.id:
            return ("drop", "not_next")
        key = (pkt["src"], pkt["seq"])
        # am ajuns la destinatie?
        if self.id == dest:
            return ("deliver", pkt)
        # dedup
        if key in self.seen:
            return ("drop", "dup")
        self.seen.add(key)
        # TTL
        ttl = int(pkt.get("ttl", 0)) - 1
        if ttl <= 0:
            return ("drop", "ttl")
        # recalculez next-hop de la MINE spre dest
        _, nh = graph.shortest_paths_to(dest)
        nxt = nh.get(self.id)
        if nxt is None:
            return ("drop", "no_route")
        pkt2 = dict(pkt)
        pkt2["ttl"] = ttl
        pkt2["next"] = nxt
        pkt2["path"] = list(pkt.get("path", [])) + [self.id]
        return ("forward", pkt2)


# ============================================================
# Simulator de livrare pe un pas (pentru SIL + teste)
# ============================================================
def deliver_once(graph, relays, src, payload, dest="gcs", rng=None,
                 stochastic=False):
    """Simuleaza livrarea UNUI pachet de la src spre dest prin mesh, hop cu
    hop, intr-un pas logic (fara timp). Intoarce:
      {delivered: bool, hops: int, path: [...], reason: str}
    Daca stochastic=True, fiecare hop reuseste cu probabilitatea PDR a
    muchiei (necesita rng); altfel livrare determinista pe ruta ETX (PDR-ul
    e deja in cost). Implicit determinist - pentru reachability curata.
    """
    relay_src = relays[src]
    pkt = relay_src.new_packet(graph, payload, dest=dest)
    if pkt is None:
        return {"delivered": False, "hops": 0, "path": [src],
                "reason": "no_route"}
    guard = 0
    while True:
        guard += 1
        if guard > len(graph.pos) + 2:
            return {"delivered": False, "hops": guard, "path": pkt["path"],
                    "reason": "loop"}
        nxt = pkt["next"]
        # hop stochastic: muchia (cur, nxt) poate pica dupa PDR
        if stochastic and rng is not None:
            cur = pkt["path"][-1]
            c = graph.edge_etx(cur, nxt)
            pdr = 0.0 if c == ETX_INF else 1.0 / c   # ETX simetric -> sqrt? aprox
            # ETX = 1/(pdr*pdr) -> pdr = 1/sqrt(ETX)
            pdr = 0.0 if c == ETX_INF else 1.0 / math.sqrt(c)
            if rng.random() > pdr:
                return {"delivered": False, "hops": guard,
                        "path": pkt["path"], "reason": "hop_loss"}
        action, res = relays[nxt].on_receive(pkt, graph, dest=dest)
        if action == "deliver":
            return {"delivered": True, "hops": len(res["path"]),
                    "path": res["path"] + [dest], "reason": "ok"}
        if action == "drop":
            return {"delivered": False, "hops": guard, "path": pkt["path"],
                    "reason": res}
        pkt = res            # forward: continua


# ============================================================
# Comparatie STEA vs MESH (metrica centrala a contributiei)
# ============================================================
def star_reachable(graph, dest="gcs"):
    """In STEA, un nod ajunge la GCS doar daca are LEGATURA DIRECTA (un hop).
    Intoarce multimea nodurilor cu muchie directa la dest."""
    return set(graph.neighbors(dest).keys())


def mesh_vs_star(graph, dest="gcs"):
    """Bilantul reachability: cine ajunge la GCS in stea vs in mesh.
    Intoarce dict cu seturile si numerele - metrica figurii star-vs-mesh."""
    star = star_reachable(graph, dest)
    mesh = graph.reachable_set(dest)
    recovered = mesh - star          # nodurile pe care DOAR mesh-ul le salveaza
    all_nodes = {n for n in graph.pos
                 if n != dest and n not in graph.down_nodes}
    return {
        "star_reachable": star,
        "mesh_reachable": mesh,
        "recovered_by_mesh": recovered,
        "n_total": len(all_nodes),
        "n_star": len(star),
        "n_mesh": len(mesh),
        "n_recovered": len(recovered),
        "isolated_even_in_mesh": all_nodes - mesh,
    }


# ============================================================
# Selftest
# ============================================================
def _selftest():
    import sys
    sys.path.insert(0, ".")
    try:
        from radio_link import make_link
    except ImportError:
        print("[skip] radio_link.py nu e in cale; folosesc un link fictiv")
        make_link = None

    n_ok = [0]
    n_fail = [0]

    def check(name, cond, detail=""):
        if cond:
            n_ok[0] += 1
            print(f"[ok]   {name}")
        else:
            n_fail[0] += 1
            print(f"[FAIL] {name}  {detail}")

    # --- ETX ---
    check("etx: link perfect -> 1.0", abs(etx(1.0, 1.0) - 1.0) < 1e-12)
    check("etx: pdr 0.5 simetric -> 4.0", abs(etx(0.5) - 4.0) < 1e-12)
    check("etx: pdr 0 -> infinit", etx(0.0) == ETX_INF)
    check("etx: asimetric 1/(0.8*0.5)=2.5", abs(etx(0.8, 0.5) - 2.5) < 1e-12)

    if make_link is None:
        print(f"\n=== {n_ok[0]}/{n_ok[0]+n_fail[0]} (partial, fara radio_link) ===")
        return 0 if n_fail[0] == 0 else 1

    # urban_rubble: raza radio utila ~70 m (atenuare agresiva, realist SAR in
    # cladiri prabusite) -> distante mici forteaza multi-hop, ca pe teren.
    link = make_link("urban_rubble", shadow_sigma_db=0.0)

    # --- PDR scade cu distanta ---
    p_near = pdr_from_link(link, 10)
    p_far = pdr_from_link(link, 200)
    check("pdr: aproape > departe", p_near > p_far, f"{p_near:.3f} vs {p_far:.3f}")
    check("pdr: aproape ~ 1", p_near > 0.90)

    # --- Topologie liniara: GCS - d1 - d2 - d3, fiecare la 'pas' m ---
    # pas=50 m: un hop e bun (PDR~0.94), dar 2-3 hopuri directe la GCS sunt
    # imposibile (100 m: PDR~0.015, 150 m: ~0). Forteaza relay multi-hop real.
    pas = 50.0
    g = MeshGraph(link, pdr_min=0.10)
    g.set_positions({"gcs": (0, 0), "d1": (pas, 0),
                     "d2": (2 * pas, 0), "d3": (3 * pas, 0)})
    # d1 vede GCS direct?
    star = star_reachable(g)
    check("stea: d1 are legatura directa la GCS", "d1" in star)
    check("stea: d3 NU are legatura directa la GCS (prea departe)",
          "d3" not in star, f"star={star}")

    # mesh: d3 ajunge prin d2->d1->gcs
    dist, nh = g.shortest_paths_to("gcs")
    check("mesh: d3 ajunge la GCS prin relay", dist["d3"] < ETX_INF)
    check("mesh: next-hop d3 = d2", nh["d3"] == "d2", f"nh={nh}")
    check("mesh: next-hop d2 = d1", nh["d2"] == "d1")
    hops = g.hop_count_to("gcs")
    check("mesh: d3 la 3 hopuri", hops["d3"] == 3, f"hops={hops}")

    # --- Relay dirijat livreaza ---
    relays = {n: DirectedRelay(n, ttl=8) for n in g.pos}
    res = deliver_once(g, relays, "d3", {"msg": "victima gasita"})
    check("relay: d3 livreaza la GCS prin mesh", res["delivered"],
          f"res={res}")
    check("relay: drumul e d3->d2->d1->gcs",
          res["path"] == ["d3", "d2", "d1", "gcs"], f"path={res['path']}")

    # --- Blocare nod: d2 doborata -> d3 izolat chiar si in mesh ---
    g.block_node("d2")
    bilant = mesh_vs_star(g)
    check("blocare: d2 scos din retea",
          "d2" not in bilant["mesh_reachable"]
          and "d2" not in bilant["isolated_even_in_mesh"])
    check("blocare: d3 devine izolat (releu pierdut)",
          "d3" in bilant["isolated_even_in_mesh"], f"bilant={bilant}")
    g.unblock_node("d2")

    # --- partition_2v2: d3,d4 departe de GCS dar aproape de d1,d2 ---
    # urban_rubble: d1/d2 la 50 m de GCS (legatura directa), d3/d4 la 100 m
    # de GCS (fara legatura directa) dar la 50 m de d1/d2 (relay posibil).
    g2 = MeshGraph(link, pdr_min=0.10)
    g2.set_positions({"gcs": (0, 0), "d1": (50, 0), "d2": (50, 30),
                      "d3": (100, 0), "d4": (100, 30)})
    bil = mesh_vs_star(g2)
    check("partition: stea pierde d3/d4",
          "d3" not in bil["star_reachable"] and "d4" not in bil["star_reachable"],
          f"star={bil['star_reachable']}")
    check("partition: mesh recupereaza cel putin o drona izolata",
          bil["n_recovered"] >= 1, f"recovered={bil['recovered_by_mesh']}")

    # --- dedup ---
    r = DirectedRelay("d1", ttl=8)
    g3 = MeshGraph(link, pdr_min=0.10)
    g3.set_positions({"gcs": (0, 0), "d1": (50, 0), "d2": (100, 0)})
    pkt = {"src": "d2", "seq": 1, "ttl": 5, "next": "d1", "path": ["d2"]}
    a1, _ = r.on_receive(pkt, g3)
    a2, reason2 = r.on_receive(pkt, g3)
    check("dedup: a doua oara acelasi (src,seq) -> drop dup",
          a1 == "forward" and a2 == "drop" and reason2 == "dup")

    # --- TTL ---
    r2 = DirectedRelay("d1", ttl=8)
    pkt_ttl = {"src": "d2", "seq": 9, "ttl": 1, "next": "d1", "path": ["d2"]}
    a, reason = r2.on_receive(pkt_ttl, g3)
    check("ttl: pachet cu ttl=1 ajunge la 0 -> drop ttl",
          a == "drop" and reason == "ttl")

    print(f"\n=== {n_ok[0]}/{n_ok[0]+n_fail[0]} verificari trecute ===")
    return 0 if n_fail[0] == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
