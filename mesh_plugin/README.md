# mesh_plugin

Strat de retea MESH multi-hop intre drone pentru ROS 2 (Search-and-Rescue): o
drona fara legatura directa cu statia de la sol (GCS) ajunge la GCS prin vecini,
prin relay dirijat hop-cu-hop. Schimba topologia roiului din STEA (fiecare drona
vorbeste DIRECT cu GCS) in MESH si recupereaza telemetria pe care o partitie de
roi ar pierde-o. (Descriere si rol din docstring-urile `mesh_core.py` si din
`package.xml`.)

## Scop

Cand o drona iese din raza radio directa a GCS (sau o partitie taie legatura),
in topologia STEA GCS-ul orbeste: acoperirea/victimele se crediteaza doar din
telemetria LIVRATA. Stratul MESH recupereaza valoarea pierduta: daca d3 il aude
pe d1 si d1 aude GCS, atunci d3 ajunge la GCS prin relay d3 -> d1 -> gcs.

Contributia C3: docstring-ul `mesh_core.py` scrie literal 'Feeds contributia C3
a tezei.', iar `package.xml` descrie pachetul ca extindere a razei prin relee si
rezilienta la partitie. Restul afirmatiilor despre C3 vin tot din docstring-uri.

Metrica si rutarea (din docstring-uri / comentarii):
- model radio log-distance: distanta -> PDR (refoloseste `radio_link.py`);
- ETX = 1 / (PDR_fwd * PDR_rev), aliniat la De Couto (MIT 2004), OLSR / BATMAN /
  Babel (citat in docstring `mesh_core.py`);
- rutare Dijkstra pe cost ETX; relay dirijat cu deduplicare pe `(src, seq)` si
  TTL.

## Arhitectura

Pachetul respecta lantul metodologic al proiectului (nucleu pur cu `_selftest`
-> nod ROS subtire pe JSON / `std_msgs/String` -> SIL). ATENTIE: pachetul contine
DOUA implementari paralele ale aceluiasi concept, in directoare diferite, cu
API-uri DIFERITE. Distinctia e verificata in cod (entry_points din `setup.py`,
import-uri si topicuri).

Implementarea CANONICA (cea instalata si rulata de `ros2 run` / `ros2 launch`)
este pachetul ament intern `mesh_plugin/mesh_plugin/`. Entry_points din `setup.py`
trimit acolo:

```
mesh_node        = mesh_plugin.mesh_node:main
sil_mesh         = mesh_plugin.sil_mesh:main
sil_mesh_mission = mesh_plugin.sil_mesh_mission:main
```

`launch/mesh_plugins.launch.py` foloseste `executable="mesh_node"`, deci si el
ruleaza versiunea interna.

Cele trei straturi ale versiunii CANONICE (`mesh_plugin/mesh_plugin/`):

- nucleu pur cu `_selftest`: `mesh_core.py` (`MeshTopology`, `shortest_path`,
  `routing_table`, `reachability`, `simulate_delivery`; `if __name__ ==
  "__main__": _selftest()`);
- nod ROS subtire: `mesh_node.py` (`MeshNode(Node)`, beacon + relay dirijat,
  publica tabela de rute);
- SIL: `sil_mesh.py` (reachability stea vs mesh) si `sil_mesh_mission.py`
  (experiment de misiune stea vs mesh).

A doua implementare se afla in RADACINA pachetului (`mesh_plugin/*.py`). Are alt
nucleu (`MeshGraph` + `DirectedRelay`, Dijkstra centralizat), un nod agregator
(`mesh_node.py`), un demo Tkinter (`mesh_demo.py`), SIL-uri cuplate la scenarii
si suita externa `test_mesh_core.py`. Aceste fisiere se ruleaza cu `python3
<fisier>.py`, NU prin `ros2 run`: ele importa module care exista doar in radacina
(`radio_link.py`, `node_utils.py`, `sar_core.py`, ...) si care NU sunt instalate
de `setup.py` (`data_files` instaleaza doar `launch/*.launch.py`, `docs/*.png`,
`package.xml` si markerul `resource/`). Cele doua implementari nu se importa
reciproc.

## Fisiere

### Pachetul ament intern (`mesh_plugin/mesh_plugin/`) -- versiunea instalata

| Fisier | Ce face (din docstring / cod) |
|--------|-------------------------------|
| `mesh_core.py` | Nucleu pur pentru retea mesh multi-hop, fara ROS. Functii publice (verificate in cod): `rssi_dbm`, `pdr_from_rssi`, `link_pdr`, `etx`, clasa `MeshTopology`, `shortest_path`, `routing_table`, `path_pdr`, `expected_hops_tx`, `simulate_delivery`, `reachability`. Are `_selftest()` rulat din `__main__`. |
| `mesh_node.py` | Nod ROS2 subtire (`MeshNode(Node)`, unul per drona + unul pentru GCS). Emite beacon cu pozitia proprie, reconstruieste topologia din beacon-uri, publica tabela de rutare, releaza pachete DIRIJAT hop-cu-hop (`next`, dedup, TTL). Optional: ingesteaza telemetria proprie si o transporta multi-hop pana la GCS, care o republica pe `egress_topic`. |
| `sil_mesh.py` | SIL fara ROS: 4 drone in pattern lawnmower care se departeaza de GCS; masoara la fiecare pas cate noduri ajung la GCS in STEA (link direct) vs MESH (orice releu). Importa `MeshTopology, reachability`. `main()` apeleaza `run()` (fara argparse). Genereaza, daca matplotlib e disponibil, `sil_mesh_reachability.png` si `sil_mesh_snapshot.png` (din docstring). |
| `sil_mesh_mission.py` | SIL fara ROS: experiment de misiune (cautare in adancime a unui coridor), masoara cat din acoperire si cate victime recupereaza releul multi-hop fata de stea. `main()` apeleaza `run()` (fara argparse). Genereaza `sil_mesh_mission.png` (din docstring). |
| `__init__.py` | Marker de pachet (gol). |

### Rescrierea din radacina (`mesh_plugin/*.py`) -- rulabila doar cu `python3`

| Fisier | Ce face (din docstring / cod) |
|--------|-------------------------------|
| `mesh_core.py` | Nucleu pur alternativ (fara ROS). Functii publice (verificate in cod): `pdr_from_link`, `etx`, clasa `MeshGraph` (Dijkstra), clasa `DirectedRelay` (dedup + TTL), `deliver_once`, `star_reachable`, `mesh_vs_star`. Are `_selftest()` rulat din `__main__`. |
| `test_mesh_core.py` | Suita externa de verificari pentru nucleul din radacina. Importa din `radio_link` si `mesh_core` (`etx`, `ETX_INF`, `pdr_from_link`, `MeshGraph`, `DirectedRelay`, `deliver_once`, `star_reachable`, `mesh_vs_star`). Fiecare CHECK afiseaza `[ok]`/`[FAIL]`; iese != 0 daca ceva pica. |
| `mesh_node.py` | Nod ROS2 agregator (`MeshNode(Node)`) peste `MeshGraph`. Asculta pozitiile pe `pose_topic` (implicit `/sar/telemetry`), publica `/mesh/routes` (latched) si `/mesh/status`, accepta comenzi `block`/`unblock`/`reset` pe `/mesh/control`. Are `main()` + `__main__` dar NU e entry_point (vezi nota). |
| `sil_mesh.py` | SIL stea vs mesh (geometric): reachability + livrare; produce `mesh_reachability.png`, `mesh_delivery.png`, `mesh_topology.png` (din docstring). Are argparse: `--profile`, `--t_max`, `--seed`, `--out`. |
| `sil_mesh_mission.py` | SIL de misiune CU vs FARA mesh, cuplat la scenariile de degradare; produce `mesh_mission_victims.png`, `mesh_mission_delivery.png` (din docstring). Are argparse: `--scenario`, `--profile`, `--seed`, `--out`. |
| `mesh_demo.py` | Demo LIVE Tkinter: harta cu link direct / relay / izolat / blocat; buton de blocare drona. Standalone implicit; `--ros` citeste pozitiile din `/sar/telemetry` si publica pe `/mesh/control`. Are argparse: `--ros`. |
| `radio_link.py` | Model radio log-distance partajat (`LogDistanceRadioLink`); distanta -> RSSI -> SNR -> loss(SNR). Importat de nucleul din radacina. |
| `node_utils.py` | Utilitare ROS2 comune: profiluri QoS (`qos_reliable`, `qos_best_effort`, `qos_latched`), parsare telemetrie JSON. Importat de `mesh_node.py` din radacina. |
| `sar_core.py` | Nucleul misiunii Search & Rescue (Python pur): grila de ocupare, frontiere, A*, metrici de acoperire / victime, comportamente de avarie. Dependinta a SIL-ului de misiune. |
| `swarm_core.py` | Logica pura a roiului (cinematica, formatii, cautare, failsafe), fara ROS. Dependinta a SIL-ului de misiune. |
| `netem_core.py` | Modelul de degradare a retelei (Python pur): latenta + jitter + pierdere per legatura, store-and-forward optional, scenarii din YAML. Dependinta a SIL-ului de misiune. |
| `world_config.py` | Lumea (ruine, fum, victime, drone) ca sursa unica de adevar pentru SIL / noduri / Gazebo. Dependinta a SIL-ului de misiune. |

### Alte fisiere

| Fisier | Ce este |
|--------|---------|
| `launch/mesh_plugins.launch.py` | Lanseaza un `mesh_node` (versiunea interna) per drona din lista `DRONES = ["d1","d2","d3","d4"]` + unul pentru GCS cu pozitie fixa. |
| `scenarios/*.yaml` | 7 scenarii de degradare: `baseline`, `loss_30`, `loss_70`, `gcs_delay_spike`, `drone_isolation`, `partition_2v2`, `mesh_relay`. Citite de SIL-ul de misiune din radacina. |
| `verifica_tot.sh` | Verificare end-to-end: structura, offline (selftest + SIL-uri), `colcon build`, `ros2 pkg executables`. Argumente: `--offline`, `--clean`, `--help`; var. mediu `WS`. |
| `requirements.txt` | Dependinte pip: `matplotlib`, `numpy`, `PyYAML`. `tkinter` nu e pip -> `sudo apt install python3-tk`. |
| `docs/*.png`, `mesh_*.png` (radacina) | Figuri (instalate prin `data_files`; cele din radacina sunt regenerate de SIL-uri). |
| `package.xml`, `setup.py`, `setup.cfg`, `resource/mesh_plugin` | Metadate `ament_python`. |

Nota: `mesh_node.py`, `sil_mesh.py`, `sil_mesh_mission.py` si `mesh_core.py`
exista in DOUA exemplare (radacina vs `mesh_plugin/`) cu CONTINUT DIFERIT. Doar
exemplarele interne sunt entry_points; cele din radacina ruleaza cu `python3`.

## Sintaxe de rulare

Build (ament_python; `build_type` din `package.xml`):

```bash
cd ~/ros2_ws && colcon build --packages-select mesh_plugin --symlink-install
source install/setup.bash               # in FIECARE terminal nou
```

Selftest offline (nucleele pure, fara ROS; din directorul pachetului):

```bash
cd ~/ros2_ws/src/mesh_plugin
python3 mesh_core.py                     # nucleul din radacina (MeshGraph) -- _selftest
python3 mesh_plugin/mesh_core.py         # nucleul intern (MeshTopology) -- _selftest
python3 test_mesh_core.py                # suita externa pentru nucleul din radacina
```

Rulare prin ament (entry_points REALE din `setup.py`):

```bash
ros2 pkg executables mesh_plugin         # mesh_node, sil_mesh, sil_mesh_mission

# nod per drona (versiunea interna beacon/relay):
ros2 run mesh_plugin mesh_node --ros-args -p id:=d3 -p gcs:=GCS \
    -p pose_topic:=/sar/pose/d3
# SIL-uri interne (main() apeleaza run() FARA argparse -> nu accepta argumente CLI):
ros2 run mesh_plugin sil_mesh
ros2 run mesh_plugin sil_mesh_mission
```

Launch (argumente expuse REALE din `mesh_plugins.launch.py`):

```bash
ros2 launch mesh_plugin mesh_plugins.launch.py
ros2 launch mesh_plugin mesh_plugins.launch.py path_loss_n:=3.5
# transport de telemetrie prin mesh (prefixul de ingestare e fix in launch:
# INGEST_PREFIX = "/sar/telemetry/"):
ros2 launch mesh_plugin mesh_plugins.launch.py ingest:=true \
    egress_topic:=/sar/telemetry
```

Argumente de lansare declarate in `mesh_plugins.launch.py`: `ingest`,
`egress_topic`, `gcs_x`, `gcs_y`, `tx_dbm`, `path_loss_n`, `sens_dbm`,
`width_db`, `pdr_min`, `relay_ttl`.

Scripturile din radacina (NU prin `ros2 run`; argumente argparse reale):

```bash
cd ~/ros2_ws/src/mesh_plugin
python3 sil_mesh.py [--profile P] [--t_max F] [--seed N] [--out PATH]
python3 sil_mesh_mission.py [--scenario S] [--profile P] [--seed N] [--out PATH]
python3 mesh_demo.py [--ros]
python3 mesh_node.py --ros-args -p profile:=urban_rubble -p pdr_min:=0.10
```

Verificare automata:

```bash
cd ~/ros2_ws/src/mesh_plugin
./verifica_tot.sh --offline     # structura + selftest + SIL-uri (fara colcon)
./verifica_tot.sh               # + colcon build + ros2 pkg executables
./verifica_tot.sh --clean       # build curat (sterge build/install pachet)
```

Numarul exact de verificari trecute de `_selftest()` / `test_mesh_core.py` si
cifrele de performanta (castig de telemetrie, procente de reachability) NU sunt
raportate aici fiindca nu au fost rulate la documentare. TODO: de confirmat prin
rulare (`python3 mesh_core.py`, `python3 mesh_plugin/mesh_core.py`, `python3
test_mesh_core.py`, SIL-urile).

## Parametri si topicuri

### Nodul intern `mesh_plugin/mesh_plugin/mesh_node.py` (rulat de `ros2 run` / launch)

Parametri (din `declare_parameter`, cu valori implicite reale):

| Parametru | Implicit |
|-----------|----------|
| `id` | `d1` |
| `gcs` | `GCS` |
| `pose_topic` | `/sar/pose/d1` |
| `static_x`, `static_y` | `9.0e9` (= nesetat; sub `8.0e9` -> pozitie fixa) |
| `beacon_hz` | `2.0` |
| `route_hz` | `1.0` |
| `pdr_min` | `0.10` |
| `relay_ttl` | `8` |
| `tx_dbm`, `path_loss_n`, `sens_dbm`, `width_db` | `0.0`, `3.0`, `-40.0`, `3.0` |
| `ingest`, `ingest_topic`, `egress_topic` | `False`, `""`, `""` |

Topicuri (JSON pe `std_msgs/String`):

| Topic | Sens | Forma mesajului (din cod) |
|-------|------|---------------------------|
| `/mesh/beacon` | publica + asculta | `{"id", "x", "y", "t", "seq"}` |
| `/mesh/relay` | publica + asculta | `{"src", "dst", "seq", "ttl", "next", "path", "payload"?}`; proceseaza doar daca `next == id` |
| `/mesh/route/<id>` | publica | `{"id", "next", "hops", "etx", "path", "reachable"}` |
| `<pose_topic>` | asculta (daca nodul nu e static) | `{"x", "y", ...}` |
| `<ingest_topic>` | asculta (daca `ingest=true`) | telemetria proprie (impachetata in `payload`) |
| `<egress_topic>` | publica (doar daca e setat; tipic GCS) | `payload`-ul livrat, repus in circuit |

### Nodul din radacina `mesh_node.py` (rulat doar cu `python3`)

Parametri (din `declare_parameter`): `pose_topic` (`/sar/telemetry`), `profile`
(`urban_rubble`), `pdr_min` (`0.10`), `ttl` (`8`), `gcs_x` (`0.0`), `gcs_y`
(`0.0`), `rate_hz` (`1.0`).

Topicuri (JSON pe `std_msgs/String`):

| Topic | Sens |
|-------|------|
| `pose_topic` (implicit `/sar/telemetry`) | asculta (pozitiile dronelor) |
| `/mesh/control` | asculta; `{"action":"block"|"unblock"|"reset","id":"d3"}` |
| `/mesh/routes` | publica (latched, depth 1) |
| `/mesh/status` | publica |

Cele doua noduri folosesc topicuri si parametri DIFERITI si nu sunt
interoperabile; `mesh_plugins.launch.py` lanseaza doar versiunea interna
(`/mesh/beacon` + `/mesh/relay`).
