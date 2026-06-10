#!/usr/bin/env python3
import math, random, sys
sys.path.insert(0, '.')
from sar_core import (GridWorld, DiscoveredMap, allocate_frontiers, cohesion,
                      FallbackPolicy, LINKED, LOCAL_EXPLORE, RETURN_TO_LINK,
                      LOITER, FREE_SEEN, OBSTACLE_SEEN, UNKNOWN)
from netem_core import Channel, load_scenario, apply_due_events, link_key

ok = 0
def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1
    print(f"  ok  {msg}")

print("== 1. GridWorld + dezvaluire + acoperire ==")
w = GridWorld(20, 20, 1.0, ruins=[(5,5,8,8)], smoke=[(15,15,3)], victims=[(2,10)])
m = DiscoveredMap(w)
cells, found = m.reveal_disc(2.5, 2.5, 4.0)
check(len(cells) > 30 and all(s in (FREE_SEEN, OBSTACLE_SEEN) for *_xy, s in cells),
      "discul dezvaluie celule cu stari valide")
check(0 < m.coverage() < 0.2, f"acoperirea initiala plauzibila ({m.coverage():.2%})")
_, found = m.reveal_disc(2.5, 10.5, 4.0)
check((2,10) in found, "victima detectata cand celula ei e dezvaluita")
big = DiscoveredMap(w)
big.reveal_disc(15.5, 15.5, 5.0)
small_r = sum(1 for j in range(20) for i in range(20) if big.state[j][i] != UNKNOWN)
big2 = DiscoveredMap(w)
big2.reveal_disc(2.5, 2.5, 5.0)
full_r = sum(1 for j in range(20) for i in range(20) if big2.state[j][i] != UNKNOWN)
check(small_r < full_r, f"fumul reduce raza senzorului ({small_r} < {full_r} celule)")

print("== 2. Frontiere + alocare ==")
fr = m.frontiers()
check(len(fr) > 0 and all(m.state[j][i] == FREE_SEEN for i, j in fr),
      "frontierele sunt celule libere vazute la marginea necunoscutului")
alloc = allocate_frontiers({"d1": (2,2), "d2": (2,11)}, fr)
check(set(alloc) == {"d1","d2"} and alloc["d1"] != alloc["d2"],
      "alocarea da tinte distincte fiecarei drone")

print("== 3. A* ocoleste ruinele ==")
m2 = DiscoveredMap(w)
for j in range(20):
    for i in range(20):
        m2.state[j][i] = OBSTACLE_SEEN if w.obstacle[j][i] else FREE_SEEN
        if not w.obstacle[j][i]: m2.seen_free += 1
path = m2.astar((3,6), (12,6))
check(path is not None and path[0]==(3,6) and path[-1]==(12,6), "A* gaseste drum")
check(all(not w.obstacle[j][i] for i,j in path), "drumul A* nu trece prin ruine")
check(len(path) > (12-3)+1, "drumul ocoleste (mai lung decat linia dreapta)")

print("== 4. Fallback: LINKED -> LOCAL -> RETURN -> LOITER ==")
fb = FallbackPolicy(t_local=5.0)
fb.on_gcs_contact((0,0))
fb.on_link_lost(10.0)
check(fb.state == LOCAL_EXPLORE, "pierderea legaturii -> LOCAL_EXPLORE")
fb.tick(16.0, (30,30), False)
check(fb.state == RETURN_TO_LINK, "dupa t_local -> RETURN_TO_LINK")
fb.tick(20.0, (0.5,0.5), True)
check(fb.state == LOITER, "ajuns la ultimul punct de legatura -> LOITER")
fb.on_gcs_contact((1,1))
check(fb.state == LINKED, "orice contact GCS readuce LINKED")

print("== 5. Canal: pierdere masurata ~ configurata ==")
ch = Channel(["gcs","d1"], default={"base_ms":50,"jitter_ms":5,"loss":0.30}, seed=7)
N = 4000
for i in range(N): ch.send("gcs","d1",{"i":i}, t=i*0.001)
got = ch.deliver(t=100.0)
L = ch.links[link_key("gcs","d1")]
meas = L.lost / L.sent
check(abs(meas - 0.30) < 0.03, f"pierdere masurata {meas:.3f} ~ 0.30 configurat")
lat = sum(l for *_x,l in [(0,0,s) for s in L.lat_samples])/len(L.lat_samples)
check(abs(lat - 50) < 3, f"latenta medie masurata {lat:.1f} ms ~ 50 ms")
check(len(got) == L.delivered == N - L.lost, "livrate + pierdute = trimise")

print("== 6. Store-and-forward: nimic pierdut pe legatura cazuta ==")
ch2 = Channel(["gcs","d1"], default={"base_ms":40,"jitter_ms":5,"loss":0.0}, seed=3)
ch2.set_link("gcs","d1", up=False, t=1.0)
for i in range(50): ch2.send("d1","gcs",{"i":i}, t=1.0+i*0.01)
check(len(ch2.deliver(5.0)) == 0, "legatura jos: nicio livrare")
ch2.set_link("gcs","d1", up=True, t=6.0)
got2 = ch2.deliver(20.0)
check(len(got2) == 50, "la restabilire, tot tamponul e livrat (S&F)")
check([m["i"] for _s,_d,m,_t0,_td in got2] == list(range(50)),
      "ordinea emiterii pastrata la golirea tamponului")
st = ch2.links[link_key("gcs","d1")].snapshot()
check(abs(st["down_total_s"] - 5.0) < 1e-6, f"timp deconectat masurat {st['down_total_s']} s")
check(len(st["recovery_times_s"]) == 1 and st["recovery_times_s"][0] < 2.0,
      "timpul de recuperare inregistrat dupa restabilire")

print("== 7. Partitie + izolare din scenariu YAML ==")
sc = load_scenario("scenarios/partition_2v2.yaml")
ch3 = Channel(["gcs","d1","d2","d3","d4"], default=sc["default_link"], seed=1)
apply_due_events(ch3, sc["events"], 0.0, 31.0)
check(not ch3.link_up("gcs","d3") and not ch3.link_up("d1","d4")
      and ch3.link_up("d3","d4") and ch3.link_up("gcs","d1"),
      "partitia 2v2 taie exact legaturile dintre grupuri")
apply_due_events(ch3, sc["events"], 31.0, 71.0)
check(ch3.link_up("gcs","d3"), "heal_partition restabileste legaturile")
sc2 = load_scenario("scenarios/drone_isolation.yaml")
ch4 = Channel(["gcs","d1","d2","d3","d4"], default=sc2["default_link"], seed=1)
apply_due_events(ch4, sc2["events"], 0.0, 26.0)
check(all(not ch4.link_up("d2", o) for o in ("gcs","d1","d3","d4")),
      "izolarea d2 taie toate legaturile ei")

print("== 8. Coeziune ==")
c1 = cohesion({"a":(0,0),"b":(5,5),"c":(8,2)}, radius_m=25)
c2 = cohesion({"a":(0,0),"b":(100,0),"c":(0,100)}, radius_m=25)
check(c1 == 1.0 and c2 == 0.0, f"coeziune compact={c1}, dispersat={c2}")

print(f"\nTOATE TESTELE SAR AU TRECUT: {ok} verificari noi (+41 existente in swarm_core).")
