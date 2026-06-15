#!/usr/bin/env python3
"""test_mesh_core.py -- verificari automate pentru nucleul mesh multi-hop.
Ruleaza fara ROS2 (cere doar radio_link.py + mesh_core.py in cale).
Fiecare CHECK afiseaza [ok]/[FAIL]; scriptul iese != 0 daca ceva pica."""
import math
import random
import sys

sys.path.insert(0, ".")

from radio_link import make_link
from mesh_core import (etx, ETX_INF, pdr_from_link, MeshGraph, DirectedRelay,
                       deliver_once, star_reachable, mesh_vs_star)

N_OK = 0
N_FAIL = 0


def check(name, cond, detail=""):
    global N_OK, N_FAIL
    if cond:
        N_OK += 1
        print(f"[ok]   {name}")
    else:
        N_FAIL += 1
        print(f"[FAIL] {name}  {detail}")


# ============================ ETX ============================
print("--- ETX (De Couto 2004) ---")
check("etx: link perfect (PDR=1) -> 1.0", abs(etx(1.0, 1.0) - 1.0) < 1e-12)
check("etx: PDR=0.5 simetric -> 4.0", abs(etx(0.5) - 4.0) < 1e-12)
check("etx: PDR=0 -> infinit", etx(0.0) == ETX_INF)
check("etx: asimetric 1/(0.8*0.5)=2.5", abs(etx(0.8, 0.5) - 2.5) < 1e-12)
check("etx: monoton in PDR (mai bun link -> ETX mai mic)",
      etx(0.9) < etx(0.5) < etx(0.2))

# ============================ PDR din radio ============================
print("--- PDR din modelul radio ---")
link = make_link("urban_rubble", shadow_sigma_db=0.0)
check("pdr: scade cu distanta",
      pdr_from_link(link, 10) > pdr_from_link(link, 60) > pdr_from_link(link, 100))
check("pdr: aproape ~ 1", pdr_from_link(link, 10) > 0.90)
check("pdr: departe ~ 0", pdr_from_link(link, 200) < 0.05)
check("pdr: in [0,1]", 0.0 <= pdr_from_link(link, 75) <= 1.0)

# ============================ Topologie + Dijkstra ============================
print("--- MeshGraph + Dijkstra (cost ETX) ---")
# lant GCS - d1 - d2 - d3 la pas 50 m (urban_rubble: 1 hop bun, 3 imposibil direct)
pas = 50.0
g = MeshGraph(link, pdr_min=0.10)
g.set_positions({"gcs": (0, 0), "d1": (pas, 0),
                 "d2": (2 * pas, 0), "d3": (3 * pas, 0)})
star = star_reachable(g)
check("stea: doar d1 vede GCS direct", star == {"d1"}, f"star={star}")
dist, nh = g.shortest_paths_to("gcs")
check("mesh: toate dronele ajung la GCS", all(dist[d] < ETX_INF
      for d in ("d1", "d2", "d3")))
check("mesh: next-hop d3=d2, d2=d1, d1=gcs",
      nh["d3"] == "d2" and nh["d2"] == "d1" and nh["d1"] == "gcs", f"nh={nh}")
check("mesh: ETX creste cu numarul de hopuri",
      dist["d1"] < dist["d2"] < dist["d3"])
hops = g.hop_count_to("gcs")
check("mesh: hop count d1=1, d2=2, d3=3",
      hops["d1"] == 1 and hops["d2"] == 2 and hops["d3"] == 3, f"hops={hops}")

# ============================ Relay dirijat ============================
print("--- DirectedRelay (hop-by-hop, dedup, TTL) ---")
relays = {n: DirectedRelay(n, ttl=8) for n in g.pos}
res = deliver_once(g, relays, "d3", {"victima": 2})
check("relay: d3 livreaza la GCS", res["delivered"], f"res={res}")
check("relay: drum d3->d2->d1->gcs",
      res["path"] == ["d3", "d2", "d1", "gcs"], f"path={res['path']}")
check("relay: 3 hopuri raportate", res["hops"] == 3, f"hops={res['hops']}")

# dedup: acelasi (src,seq) procesat o singura data
g2 = MeshGraph(link, pdr_min=0.10)
g2.set_positions({"gcs": (0, 0), "d1": (50, 0), "d2": (100, 0)})
r = DirectedRelay("d1", ttl=8)
pkt = {"src": "d2", "seq": 1, "ttl": 5, "next": "d1", "path": ["d2"]}
a1, _ = r.on_receive(pkt, g2)
a2, why2 = r.on_receive(pkt, g2)
check("dedup: prima oara forward, a doua oara drop(dup)",
      a1 == "forward" and a2 == "drop" and why2 == "dup")

# pachet care nu e pentru mine
a, why = DirectedRelay("d1").on_receive(
    {"src": "d2", "seq": 1, "ttl": 5, "next": "d9", "path": []}, g2)
check("relay: pachet 'next' != id -> drop(not_next)",
      a == "drop" and why == "not_next")

# TTL expira
a, why = DirectedRelay("d1").on_receive(
    {"src": "d2", "seq": 7, "ttl": 1, "next": "d1", "path": ["d2"]}, g2)
check("ttl: ttl ajunge la 0 -> drop(ttl)", a == "drop" and why == "ttl")

# ============================ STEA vs MESH ============================
print("--- Bilantul star vs mesh (metrica centrala) ---")
# partition_2v2: d1/d2 la 50 m de GCS, d3/d4 la 100 m (fara link direct)
gp = MeshGraph(link, pdr_min=0.10)
gp.set_positions({"gcs": (0, 0), "d1": (50, 0), "d2": (50, 30),
                  "d3": (100, 0), "d4": (100, 30)})
bil = mesh_vs_star(gp)
check("partition: stea ajunge doar la d1,d2",
      bil["star_reachable"] == {"d1", "d2"}, f"{bil['star_reachable']}")
check("partition: mesh ajunge la toate 4",
      bil["n_mesh"] == 4, f"mesh={bil['mesh_reachable']}")
check("partition: mesh recupereaza d3,d4",
      bil["recovered_by_mesh"] == {"d3", "d4"}, f"{bil['recovered_by_mesh']}")
check("partition: nicio drona izolata in mesh",
      bil["isolated_even_in_mesh"] == set())

# ============================ Blocarea unei drone (demo) ============================
print("--- Blocarea unei drone (multi-hop se rupe) ---")
# in lantul GCS-d1-d2-d3, blocam d2 (releul) -> d3 ramane izolat
gb = MeshGraph(link, pdr_min=0.10)
gb.set_positions({"gcs": (0, 0), "d1": (50, 0),
                  "d2": (100, 0), "d3": (150, 0)})
before = gb.reachable_set("gcs")
check("inainte de blocare: d3 ajunge prin relay", "d3" in before)
gb.block_node("d2")
after = gb.reachable_set("gcs")
check("dupa blocarea d2: d3 NU mai ajunge (releu pierdut)",
      "d3" not in after, f"after={after}")
check("dupa blocarea d2: d1 inca ajunge direct", "d1" in after)
gb.unblock_node("d2")
check("dupa deblocare: d3 ajunge iar", "d3" in gb.reachable_set("gcs"))

# blocarea unei drone-frunza NU afecteaza restul
gb.block_node("d3")
check("blocarea frunzei d3 nu rupe d1,d2",
      {"d1", "d2"} <= gb.reachable_set("gcs"))
gb.unblock_node("d3")

# ============================ Livrare stochastica ============================
print("--- Livrare stochastica (PDR pe fiecare hop) ---")
# pe lant lung, livrarea stochastica reuseste cu probabilitate < 1
# dar > 0; verificam ca media e rezonabila pe multe incercari
gs = MeshGraph(link, pdr_min=0.10)
gs.set_positions({"gcs": (0, 0), "d1": (45, 0),
                  "d2": (90, 0), "d3": (135, 0)})
rng = random.Random(7)
relays_s = {n: DirectedRelay(n, ttl=8) for n in gs.pos}
n_try, n_ok_deliv = 300, 0
for _ in range(n_try):
    for n in relays_s:
        relays_s[n].seen.clear()
    r = deliver_once(gs, relays_s, "d3", {"x": 1}, rng=rng, stochastic=True)
    n_ok_deliv += r["delivered"]
ratio = n_ok_deliv / n_try
check("stochastic: livrare partiala pe lant lung (0 < rata < 1)",
      0.0 < ratio < 1.0, f"rata={ratio:.2f}")

# ============================ Reproductibilitate ============================
print("--- Determinism ---")
g_a = MeshGraph(make_link("urban_rubble", shadow_sigma_db=0.0))
g_b = MeshGraph(make_link("urban_rubble", shadow_sigma_db=0.0))
pos = {"gcs": (0, 0), "d1": (50, 10), "d2": (95, 20), "d3": (140, 5)}
g_a.set_positions(pos)
g_b.set_positions(pos)
check("determinism: aceeasi topologie -> aceleasi rute",
      g_a.shortest_paths_to("gcs")[1] == g_b.shortest_paths_to("gcs")[1])

# ================================ bilant ================================
print(f"\n=== {N_OK}/{N_OK + N_FAIL} verificari trecute ===")
sys.exit(0 if N_FAIL == 0 else 1)
