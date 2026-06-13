#!/usr/bin/env python3
"""mesh_core.py - nucleu pur pentru retea mesh multi-hop intre drone.

Fara ROS, fara retea: logica de rutare, testabila izolat (conventia
depozitului). Sta DEASUPRA modelului radio existent (log-distance):
primeste pozitiile nodurilor, deduce cine aude pe cine si cu ce calitate,
calculeaza metrica ETX per legatura, ruteaza spre GCS (sau spre orice drona)
cu Dijkstra si simuleaza livrarea multi-hop cu releu.

De ce conteaza pentru teza: schimba povestea topologiei. In loc de stea pura
(fiecare drona vorbeste DOAR cu GCS), o drona fara legatura directa la GCS
poate ajunge prin relee. Recupereaza exact reachability-ul pe care scenariul
partition_2v2 il pierdea -> experiment direct: stea vs mesh.

Toate marimile au valori implicite rezonabile; nimic nu necesita ROS sau retea.
"""
import math
import heapq
import random

# =====================================================================
# 1. Modelul de legatura: distanta -> RSSI (log-distance) -> PDR (sigmoid)
# =====================================================================
# Acelasi principiu ca radio_link_node din sar_plugins: pierderea pe traseu
# creste logaritmic cu distanta; probabilitatea de livrare (PDR) urmeaza o
# sigmoida in jurul pragului de sensibilitate al receptorului.

def rssi_dbm(d, tx_dbm=0.0, n=3.0, d0=1.0):
    """Puterea primita [dBm] la distanta d [m], model log-distance.
    tx_dbm = putere efectiva la d0; n = exponentul de propagare
    (2 = spatiu liber, 2.5-4 = urban/obstacole). Valorile implicite sunt
    calibrate pentru o raza utila de ~25 m (WiFi slab / radio de telemetrie
    in mediu cu obstacole), ca releul multi-hop sa fie necesar pe arii SAR."""
    d = max(d, d0)
    return tx_dbm - 10.0 * n * math.log10(d / d0)


def pdr_from_rssi(rssi, sens_dbm=-40.0, width_db=3.0):
    """Probabilitatea de livrare a unui pachet (0..1) in functie de RSSI.
    Sigmoida centrata pe sensibilitatea receptorului; width = cat de
    abrupta e tranzitia 'merge / nu merge'."""
    z = (rssi - sens_dbm) / width_db
    if z < -40:
        return 0.0
    if z > 40:
        return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def link_pdr(d, tx_dbm=0.0, n=3.0, d0=1.0, sens_dbm=-40.0, width_db=3.0):
    """PDR end-to-end pe O legatura, direct din distanta. Monoton
    descrescator: ~1 aproape, ~0 departe."""
    return pdr_from_rssi(rssi_dbm(d, tx_dbm, n, d0), sens_dbm, width_db)


def etx(pdr_fwd, pdr_rev=None):
    """ETX (Expected Transmission Count) = numarul mediu de transmisii
    pentru o livrare reusita, tinand cont de ACK-ul invers. Metrica
    standard de rutare mesh (Babel/OLSR). ETX = 1/(df*dr).
    Daca legatura e simetrica, pdr_rev = pdr_fwd."""
    if pdr_rev is None:
        pdr_rev = pdr_fwd
    prod = pdr_fwd * pdr_rev
    if prod <= 1e-9:
        return math.inf
    return 1.0 / prod


# =====================================================================
# 2. Topologia: din pozitii -> graf de adiacenta cu costuri ETX
# =====================================================================

class MeshTopology:
    """Construieste graful roiului din pozitii. Un nod special e GCS (sink).
    O muchie exista doar daca PDR >= pdr_min (altfel nodurile nu se aud)."""

    def __init__(self, positions, gcs="GCS", pdr_min=0.10, etx_max=12.0,
                 radio=None):
        # positions: dict {id: (x, y)} incluzand GCS
        self.pos = dict(positions)
        self.gcs = gcs
        self.pdr_min = pdr_min
        self.etx_max = etx_max
        self.radio = radio or {}            # parametri pentru link_pdr
        self.nodes = list(self.pos.keys())
        self._build()

    def dist(self, a, b):
        (xa, ya), (xb, yb) = self.pos[a], self.pos[b]
        return math.hypot(xa - xb, ya - yb)

    def pdr(self, a, b):
        return link_pdr(self.dist(a, b), **self.radio)

    def _build(self):
        """Adiacenta + ETX per muchie (simetrica)."""
        self.adj = {u: {} for u in self.nodes}
        self.links = {}                     # (u,v) -> {pdr, etx, d}
        for i, u in enumerate(self.nodes):
            for v in self.nodes[i + 1:]:
                p = self.pdr(u, v)
                if p < self.pdr_min:
                    continue                # nu se aud
                e = etx(p)
                if e > self.etx_max:
                    continue                # legatura prea slaba ca ruta utila
                self.adj[u][v] = e
                self.adj[v][u] = e
                self.links[(u, v)] = {"pdr": p, "etx": e, "d": self.dist(u, v)}

    def neighbors(self, u):
        """Vecinii directi ai unui nod (cei pe care ii aude), cu ETX."""
        return dict(self.adj.get(u, {}))

    def direct_link(self, u, v):
        """PDR-ul legaturii directe u-v (0 daca nu se aud)."""
        p = self.pdr(u, v)
        return p if p >= self.pdr_min else 0.0


# =====================================================================
# 3. Rutarea: Dijkstra pe cost ETX -> drum + next-hop
# =====================================================================

def shortest_path(topo, src, dst):
    """Drumul de cost ETX minim de la src la dst (Dijkstra).
    Returneaza (cale [src..dst], cost_total) sau (None, inf) daca nu exista."""
    if src == dst:
        return [src], 0.0
    dist = {src: 0.0}
    prev = {}
    pq = [(0.0, src)]
    seen = set()
    while pq:
        d, u = heapq.heappop(pq)
        if u in seen:
            continue
        seen.add(u)
        if u == dst:
            break
        for v, w in topo.adj.get(u, {}).items():
            nd = d + w
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
    if dst not in dist:
        return None, math.inf
    # reconstruieste calea
    path, u = [dst], dst
    while u != src:
        u = prev[u]
        path.append(u)
    path.reverse()
    return path, dist[dst]


def routing_table(topo, dst=None):
    """Tabela de next-hop catre dst (implicit GCS) pentru fiecare nod.
    {nod: {'next': vecinul-spre-dst, 'hops': k, 'etx': cost, 'path': [...]}}"""
    dst = dst or topo.gcs
    table = {}
    for u in topo.nodes:
        if u == dst:
            continue
        path, cost = shortest_path(topo, u, dst)
        if path is None:
            table[u] = {"next": None, "hops": math.inf, "etx": math.inf,
                        "path": None, "reachable": False}
        else:
            table[u] = {"next": path[1], "hops": len(path) - 1, "etx": cost,
                        "path": path, "reachable": True}
    return table


# =====================================================================
# 4. Livrarea multi-hop: analitic + stochastic
# =====================================================================

def path_pdr(topo, path):
    """Probabilitatea ca un pachet sa strabata toata calea FARA
    retransmisii (produsul PDR per hop). Util pentru 'best_effort'."""
    if path is None or len(path) < 2:
        return 1.0 if path else 0.0
    p = 1.0
    for a, b in zip(path, path[1:]):
        p *= topo.links_pdr(a, b)
    return p


def expected_hops_tx(topo, path):
    """Numarul mediu de transmisii pe toata calea (suma ETX per hop) =
    proxy pentru intarziere si consum sub un MAC cu retransmisii."""
    if path is None or len(path) < 2:
        return 0.0
    return sum(topo.adj[a][b] for a, b in zip(path, path[1:]))


def simulate_delivery(topo, path, rng, max_retx=3, hop_ms=20.0):
    """Simuleaza o livrare multi-hop cu retransmisii per hop.
    Returneaza (livrat: bool, transmisii_totale: int, latenta_ms: float).
    La fiecare hop incearca pana la max_retx+1 ori; daca toate esueaza,
    pachetul se pierde (ca un MAC fara livrare garantata dincolo de buget)."""
    if path is None:
        return False, 0, 0.0
    if len(path) < 2:
        return True, 0, 0.0
    total_tx, latency = 0, 0.0
    for a, b in zip(path, path[1:]):
        p = topo.links_pdr(a, b)
        ok = False
        for attempt in range(max_retx + 1):
            total_tx += 1
            latency += hop_ms
            if rng.random() < p:
                ok = True
                break
        if not ok:
            return False, total_tx, latency
    return True, total_tx, latency


# mic shim ca path_pdr/simulate sa poata citi PDR-ul real al unei muchii
def _links_pdr(self, a, b):
    return self.pdr(a, b)
MeshTopology.links_pdr = _links_pdr


# =====================================================================
# 5. Experimentul-cheie: stea vs mesh (reachability catre GCS)
# =====================================================================

def reachability(topo):
    """Pentru fiecare drona: ajunge la GCS DIRECT (stea) si/sau prin mesh?
    Asta e figura de contributie: cate noduri salveaza releul multi-hop."""
    rt = routing_table(topo, topo.gcs)
    out = {}
    n_direct = n_mesh = 0
    for u in topo.nodes:
        if u == topo.gcs:
            continue
        direct = topo.direct_link(u, topo.gcs) >= topo.pdr_min
        info = rt[u]
        mesh = info["reachable"]
        n_direct += int(direct)
        n_mesh += int(mesh)
        out[u] = {
            "direct": direct,
            "mesh": mesh,
            "hops": info["hops"] if mesh else math.inf,
            "path": info["path"],
            "etx": info["etx"],
            "saved_by_relay": mesh and not direct,
        }
    out["_summary"] = {
        "n_nodes": len(topo.nodes) - 1,
        "reachable_direct": n_direct,
        "reachable_mesh": n_mesh,
        "saved_by_relay": n_mesh - n_direct,
    }
    return out


# =====================================================================
# 6. Selftest (ruleaza fara ROS: python3 mesh_core.py)
# =====================================================================

def _selftest():
    ok = 0
    fail = []

    def check(name, cond, extra=""):
        nonlocal ok
        if cond:
            ok += 1
        else:
            fail.append(f"{name} {extra}")

    # --- modelul de legatura ---
    check("rssi scade cu distanta", rssi_dbm(50) < rssi_dbm(5))
    check("pdr ~1 aproape", link_pdr(2.0) > 0.95, f"{link_pdr(2.0):.3f}")
    check("pdr ~0 departe", link_pdr(500.0) < 0.05, f"{link_pdr(500.0):.3f}")
    check("pdr monoton descrescator",
          all(link_pdr(d) >= link_pdr(d + 5) - 1e-9 for d in range(1, 200, 5)))
    check("etx simetric = 1/pdr^2", abs(etx(0.5) - 4.0) < 1e-9, f"{etx(0.5)}")
    check("etx pdr=1 -> 1", abs(etx(1.0) - 1.0) < 1e-9)
    check("etx pdr=0 -> inf", etx(0.0) == math.inf)

    # --- topologie cu releu obligatoriu: A -- B -- C, A nu aude C ---
    # A-B 18m (bun), B-C 18m (bun), A-C 36m (sub prag) cu radioul implicit
    lin = {"A": (0, 0), "B": (18, 0), "C": (36, 0), "GCS": (0, 0)}
    topo = MeshTopology(lin, gcs="GCS")
    pab = topo.direct_link("A", "B")
    pac = topo.direct_link("A", "C")
    check("A aude B", pab > 0, f"pdr={pab:.3f}")
    check("A NU aude C direct (releu necesar)", pac == 0, f"pdr={pac:.3f}")
    path, cost = shortest_path(topo, "C", "A")
    check("ruta C->A trece prin B", path == ["C", "B", "A"], f"{path}")
    check("cost ruta = suma ETX", cost > 0 and math.isfinite(cost))

    # --- Dijkstra alege calea cu ETX mai mic cand exista doua ---
    # S si T la 28m (slab direct) sau prin M la mijloc (doua hopuri bune)
    sq = {"S": (0, 0), "M": (14, 0), "T": (28, 0)}
    t2 = MeshTopology(sq, gcs="S")
    p_direct = t2.direct_link("S", "T")
    path2, c2 = shortest_path(t2, "T", "S")
    if p_direct > 0:
        # daca exista si link direct, ruta aleasa are cost <= ETX direct
        check("Dijkstra nu alege o ruta mai scumpa decat directul",
              c2 <= etx(p_direct) + 1e-9, f"ruta={c2:.2f} direct={etx(p_direct):.2f}")
    else:
        check("fara link direct, ruta merge prin M", path2 == ["T", "M", "S"])

    # --- scenariul partition_2v2: 2 drone aproape de GCS, 2 departe ---
    # d3, d4 (38m) nu aud GCS direct, dar aud d1/d2 (14m de GCS) -> releu
    p2v2 = {
        "GCS": (0, 0),
        "d1": (14, 6), "d2": (14, -6),       # aproape de GCS
        "d3": (38, 6), "d4": (38, -6),       # departe; aud d1/d2, nu GCS
    }
    tp = MeshTopology(p2v2, gcs="GCS")
    rr = reachability(tp)
    s = rr["_summary"]
    check("partition_2v2: nu toate ajung direct la GCS",
          s["reachable_direct"] < 4, f"direct={s['reachable_direct']}/4")
    check("partition_2v2: mesh recupereaza noduri",
          s["reachable_mesh"] > s["reachable_direct"],
          f"mesh={s['reachable_mesh']} direct={s['reachable_direct']}")
    check("partition_2v2: cel putin o drona salvata de releu",
          s["saved_by_relay"] >= 1, f"salvate={s['saved_by_relay']}")
    # daca d3 e salvata, calea ei are 2 hopuri si trece printr-un vecin
    if rr["d3"]["saved_by_relay"]:
        check("d3 ajunge in 2 hopuri prin releu",
              rr["d3"]["hops"] == 2 and rr["d3"]["path"][1] in ("d1", "d2"),
              f"{rr['d3']['path']}")

    # --- livrarea ---
    rng = random.Random(0)
    # cale perfecta (un hop, PDR~1) livreaza aproape mereu
    perf = {"X": (0, 0), "Y": (2, 0)}
    tperf = MeshTopology(perf, gcs="X")
    deliv = sum(simulate_delivery(tperf, ["X", "Y"], rng)[0]
                for _ in range(200))
    check("livrare pe legatura buna ~ mereu", deliv > 190, f"{deliv}/200")
    # cale lunga pe legaturi slabe livreaza mai prost decat una scurta buna
    pp = path_pdr(tp, rr["d3"]["path"]) if rr["d3"]["mesh"] else 0.0
    check("path_pdr e o probabilitate valida", 0.0 <= pp <= 1.0, f"{pp:.3f}")
    # ruta inexistenta
    iso = {"A": (0, 0), "B": (9999, 0), "GCS": (0, 0)}
    tiso = MeshTopology(iso, gcs="GCS")
    pth, cst = shortest_path(tiso, "B", "GCS")
    check("nod complet izolat: nicio ruta", pth is None and cst == math.inf)
    okd, tx, lat = simulate_delivery(tiso, None, rng)
    check("livrare pe ruta inexistenta esueaza curat",
          okd is False and tx == 0)

    # --- expected_hops_tx creste cu lungimea caii ---
    if rr["d3"]["mesh"] and rr["d1"]["mesh"]:
        e3 = expected_hops_tx(tp, rr["d3"]["path"])
        e1 = expected_hops_tx(tp, rr["d1"]["path"])
        check("calea mai lunga cere mai multe transmisii", e3 >= e1,
              f"d3={e3:.2f} d1={e1:.2f}")

    print(f"[selftest] {ok} verificari trecute"
          + (f", {len(fail)} ESUATE:" if fail else ", toate OK"))
    for f in fail:
        print("   FAIL:", f)
    return not fail


if __name__ == "__main__":
    import sys
    ok = _selftest()
    # mic demo lizibil
    print("\n--- demo: partition_2v2 (stea vs mesh) ---")
    demo = {"GCS": (0, 0), "d1": (14, 6), "d2": (14, -6),
            "d3": (38, 6), "d4": (38, -6)}
    topo = MeshTopology(demo, gcs="GCS")
    rr = reachability(topo)
    for u in ("d1", "d2", "d3", "d4"):
        i = rr[u]
        ruta = " -> ".join(i["path"]) if i["path"] else "(izolat)"
        print(f"  {u}: direct={'DA' if i['direct'] else 'NU'} "
              f"mesh={'DA' if i['mesh'] else 'NU'} "
              f"hopuri={i['hops']}  ruta: {ruta}")
    s = rr["_summary"]
    print(f"  bilant: stea {s['reachable_direct']}/4 noduri la GCS; "
          f"mesh {s['reachable_mesh']}/4; "
          f"salvate de releu: {s['saved_by_relay']}")
    sys.exit(0 if ok else 1)
