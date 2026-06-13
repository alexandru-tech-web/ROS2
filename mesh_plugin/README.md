# mesh_plugin — retea mesh multi-hop intre drone (ROS 2 / SAR)

Pachet ROS 2 (ament_python) care adauga roiului un strat de comunicatie
**mesh multi-hop**: o drona fara legatura DIRECTA la statia de la sol (GCS)
ajunge prin relee, in mai multe hopuri. Schimba topologia roiului din **stea**
(fiecare drona vorbeste doar cu GCS) in **mesh** (drona -> vecin -> ... -> GCS).

> Pozitionare in teza: rezultatul de baza al benchmarkului a aratat ca, in
> topologia in stea, o legatura proasta orbeste harta — o drona izolata zboara,
> dar raportul ei nu ajunge la GCS. Acest pachet ataca exact acea limita si
> deschide contributia C3 (adaptarea la starea legaturii). Vezi
> `dezvoltare/PROIECT_LINK_ADAPTIVE.md`.

---

## 1. Motivatie si intrebare de cercetare

In scenariul `partition_2v2`, doua drone pierd legatura cu GCS (100% pierdere)
si zonele lor raman neexplorate pe harta, desi fizic sunt survolate. Intrebarea:

> **Cat din acoperire si cate victime recupereaza un strat mesh multi-hop fata
> de topologia in stea, si cu ce cost (hopuri / latenta / energie)?**

Stratul mesh nu inlocuieste middleware-ul (DDS / Zenoh) si nu modifica
nodurile existente; sta deasupra modelului radio si remapeaza fluxul de
telemetrie prin relee.

## 2. Arhitectura (patru niveluri)

| Nivel | Ce face | Unde |
|------|---------|------|
| 1. Model radio | distanta -> RSSI (log-distance) -> PDR (sigmoida pe sensibilitate) | `mesh_core.rssi_dbm`, `pdr_from_rssi`, `link_pdr` |
| 2. Metrica | ETX = 1/(PDR_dus x PDR_intors) = nr. mediu de transmisii / livrare | `mesh_core.etx` |
| 3. Rutare | graf de adiacenta cu cost ETX; Dijkstra spre GCS; tabela next-hop | `mesh_core.MeshTopology`, `shortest_path`, `routing_table` |
| 4. Releu | forwardare DIRIJATA hop-cu-hop (pachetul poarta `next`), TTL anti-bucla | `mesh_node.on_relay`, `on_ingest` |

ETX este metrica standard a retelelor mesh (OLSR, Babel); aici leaga rutarea
de aceeasi marime ca tot restul tezei — **pierderea de pachete**.

## 3. Structura pachetului

```
mesh_plugin/
  package.xml                      manifest ament (rclpy, std_msgs)
  setup.py / setup.cfg             build ament_python + entry-points
  resource/mesh_plugin             marker ament
  mesh_plugin/
    mesh_core.py                   NUCLEU pur (fara ROS): radio, ETX, Dijkstra,
                                   releu, comparatie stea vs mesh. 21 verificari.
    mesh_node.py                   nod ROS 2 subtire: beacon, topologie, releu
                                   dirijat, ingest/egress telemetrie (optional)
    sil_mesh.py                    SIL reachability (stea vs mesh in timp)
    sil_mesh_mission.py            SIL de misiune (acoperire + victime)
  launch/
    mesh_plugins.launch.py         un mesh_node per drona + unul pentru GCS
  docs/
    sil_mesh_mission.png           figura de rezultat (acoperire stea vs mesh)
    sil_mesh_reachability.png      reachability in timp
    sil_mesh_snapshot.png          snapshot spatial cu rutele
```

## 4. Instalare in ros2_ws

```bash
# 1. Copiaza pachetul in workspace (din folderul descarcat)
cp -r mesh_plugin ~/ros2_ws/src/

# 2. (optional) verifica local nucleul si SIL-urile, FARA ROS
cd ~/ros2_ws/src/mesh_plugin/mesh_plugin
python3 mesh_core.py            # selftest: 21 verificari + demo partition_2v2
python3 sil_mesh_mission.py     # experimentul de misiune + figura

# 3. Construieste pachetul
cd ~/ros2_ws
colcon build --packages-select mesh_plugin
source install/setup.bash

# 4. Confirma executabilele
ros2 pkg executables mesh_plugin
#   mesh_plugin mesh_node
#   mesh_plugin sil_mesh
#   mesh_plugin sil_mesh_mission

# 5. Versioneaza in monorepo
cd ~/ros2_ws/src
git add mesh_plugin
git commit -m "mesh_plugin: retea mesh multi-hop intre drone (pachet ament_python, C3)"
git pull --rebase && git push
```

## 5. Utilizare

### 5.1 Offline (fara ROS) — verificare si figuri
```bash
cd ~/ros2_ws/src/mesh_plugin/mesh_plugin
python3 mesh_core.py            # logica de rutare + demo partition_2v2
python3 sil_mesh.py             # reachability stea vs mesh + 2 figuri
python3 sil_mesh_mission.py     # acoperire + victime, stea vs mesh + figura
```

### 5.2 Sub ROS — stratul mesh peste roi
```bash
# un mesh_node per drona (d1..d4) + unul pentru GCS
ros2 launch mesh_plugin mesh_plugins.launch.py

# un singur nod, pentru depanare
ros2 run mesh_plugin mesh_node --ros-args -p id:=d3 -p gcs:=GCS \
    -p pose_topic:=/sar/pose/d3

# inspecteaza rutarea live
ros2 topic echo /mesh/route/d3
ros2 topic echo /mesh/beacon
```

### 5.3 Integrare in roi (transport de telemetrie prin mesh)
Cu `ingest:=true`, fiecare drona isi impacheteaza telemetria proprie
(`/sar/telemetry/<id>`) si o trimite multi-hop spre GCS, care o republica pe
`egress_topic` (`/sar/telemetry`) pentru consumatorii existenti
(`coverage_node`, dashboard). Telemetria unei drone fara legatura directa
ajunge astfel la GCS prin relee:

```bash
ros2 launch mesh_plugin mesh_plugins.launch.py ingest:=true \
    ingest_prefix:=/sar/telemetry/ egress_topic:=/sar/telemetry
```

Precizare: aceasta presupune ca `drone_node` publica telemetria pe topic-uri
per-drona (`/sar/telemetry/<id>`). Remaparea completa a roiului este pasul de
integrare descris la sectiunea 8.

## 6. Topicuri (JSON pe std_msgs/String)

```
publica:  /mesh/beacon       {id, x, y, t, seq}
          /mesh/relay        {src, dst, seq, ttl, next, path, payload?}
          /mesh/route/<id>   {next, hops, etx, path, reachable}
          <egress_topic>     (doar GCS) telemetria livrata, repusa in circuit
asculta:  /mesh/beacon       (de la toate dronele)
          /mesh/relay        (proceseaza doar ce ii e adresat: next == id)
          <pose_topic>       pozitia proprie (daca nu are pozitie statica)
          <ingest_topic>     (daca ingest=true) telemetria proprie a dronei
```

## 7. Experimente si metrici

### 7.1 Reachability (stea vs mesh)
`python3 sil_mesh.py` — un lant de drone care se intinde dincolo de raza
directa a GCS. Metrica: numarul de noduri conectate la GCS in timp.
Rezultat tipic: **mesh 4/4 vs stea 1/4** (castig mediu ~2.5 noduri).

### 7.2 Misiune (acoperire + victime)
`python3 sil_mesh_mission.py` — cautare in adancime a unui coridor, 4 drone
esalonate pe zone, lant de relee. Acoperirea se crediteaza la GCS **doar din
telemetria livrata** (ca in sistemul real). Metrici: % acoperire creditata si
victime raportate, stea vs mesh vs plafon fizic.

Rezultat (prag de creditare PDR >= 0.30):

| Metrica | Stea | Mesh | Plafon fizic |
|---------|------|------|--------------|
| Acoperire creditata | 41% | **84%** | 84% |
| Victime raportate | 2/5 | **5/5** | 5/5 |

Figura `docs/sil_mesh_mission.png`: jumatatea adanca a coridorului e creditata
DOAR datorita releului multi-hop, iar victimele din adancime ajung la GCS doar
prin mesh. Aceasta este figura de rezultat propusa pentru un articol.

## 8. Reproducere

```bash
cd ~/ros2_ws/src/mesh_plugin/mesh_plugin
python3 mesh_core.py            # 21/21 verificari (determinist)
python3 sil_mesh.py             # regenereaza figurile de reachability
python3 sil_mesh_mission.py     # regenereaza figura de misiune
```
Parametrii scenariului (raza radio, adancimea zonelor, pragul de creditare)
sunt constante in capul fisierelor SIL; modelul radio implicit da o raza utila
de rutare de ~25 m, calibrata pentru un mediu cu obstacole.

## 9. Limite (threats to validity)

- **Cuplaj cu pierderea reala**: SIL-ul crediteaza acoperirea cand EXISTA o cale
  la GCS; presupune livrare odata ce calea exista. Combinarea celor doua
  straturi (mesh x pierdere/latenta reala a DDS/Zenoh) este pasul urmator.
- **Compromis acoperire–conectivitate**: castigul mesh depinde de topologie.
  Cu putine drone sau raza mica, releul recupereaza doar partial — exista o
  tensiune reala intre imprastierea pentru acoperire si mentinerea lantului.
- **Model radio i.i.d.**, nu rafale (aceeasi limita ca in campania principala).
- **Nivel de rutare, nu PHY/MAC**: nu modeleaza coliziuni / congestie pe canalul
  partajat la multe hopuri; e un strat de rutare, nu un simulator complet.

## 10. Pasi urmatori (daca devine articol)

1. **Integrare in roi** — remaparea telemetriei prin `/mesh/relay`
   (`drone_node` publica per-drona; GCS republica agregat) si campanie
   stea-vs-mesh pe scenariile existente, `partition_2v2` in primul rand.
2. **Metrica de misiune** — cate victime / cat % acoperire recupereaza mesh-ul,
   pe toate scenariile, cu N=5 repetari (ca in campania C1).
3. **Cost** — hopurile suplimentare cresc latenta si consumul; de cuantificat
   compromisul: reachability castigata vs latenta/energie platita (numar mediu
   de hopuri, ETX cumulat pe cale, transmisii totale).

## 11. Referinte

- D. S. J. De Couto, D. Aguayo, J. Bicket, R. Morris, "A High-Throughput Path
  Metric for Multi-Hop Wireless Routing," ACM MobiCom, 2003. (metrica ETX)
- T. Clausen, P. Jacquet, "Optimized Link State Routing Protocol (OLSR),"
  RFC 3626, 2003.
- J. Chroboczek, "The Babel Routing Protocol," RFC 6126 / RFC 8966.
- C. Perkins, E. Belding-Royer, S. Das, "Ad hoc On-Demand Distance Vector
  (AODV) Routing," RFC 3561, 2003.
