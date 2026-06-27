# GHID_INVATARE -- cum folosesc si testez tot ce am construit

Punct de pornire ca sa inveti, sa rulezi si sa verifici fiecare piesa. Nu
inlocuieste README-urile per pachet (la care trimite), ci le leaga intr-o cale de
invatare cu comenzi gata de copiat.

## 0. Cum e gandit ghidul -- trei niveluri de testare

Orice piesa se testeaza pe niveluri, de la simplu la complet. Incepe de la L0.

- **L0 -- nucleu pur, fara ROS:** `python3 <modul>.py` ruleaza un selftest
  (zeci de asertii). Verzi = logica e corecta. Nu cere ROS, retea sau date.
- **L1 -- SIL (Software-in-the-Loop):** `python3 <sil>.py` ruleaza scenariul
  complet fara ROS si scrie o figura (.png in directorul curent). Aici INTELEGI
  povestea (ce demonstreaza piesa).
- **L2 -- ROS pe masina:** `colcon build` + `ros2 run` / `ros2 launch`. Aici se
  vede comportamentul real, pe topicuri.

Conventii peste tot: cod/documente ASCII; mesaje JSON pe `std_msgs/String`; un
singur publisher pe `/sar/linkstate`.

## 1. Imaginea de ansamblu (cum se leaga totul)

Teza: `rmw_zenoh` vs CycloneDDS sub retea degradata, pentru SAR. Se masoara pe
doua straturi: transport (RTT) si misiune (roi de drone).

```
                 tc netem (degradare FIZICA pe interfata)
                              |
        +---------------------+----------------------+
        |                                            |
  TRANSPORT (RTT pe ecou)                   MISIUNE (roi SAR)
  c1_benchmark/run_campaign.py              sar_swarm + sar_plugins
        |                                            |
        +----------------> campaign_stats <----------+   (rigoare: CI, KS, CDF)

  Concluzia C1: NICIUN middleware nu domina  ->  doua raspunsuri de cercetare:
    - mesh_plugin   : recupereaza acoperirea pierduta la partitii  (DACA exista cale)
    - link_adaptive : adapteaza comportamentul fluxului dupa legatura (CUM se comporta)
```

Pe scurt: `mesh_plugin` si `link_adaptive` sunt cele doua contributii C3, iar
`campaign_stats` da rigoarea statistica peste oricare campanie.

## 2. Componentele NOI (construite impreuna) -- hands-on

### 2.1 mesh_plugin -- retea mesh multi-hop
**De ce:** in topologia stea, o legatura cazuta orbeste harta GCS. Mesh-ul ruteaza
prin vecini: daca d3 aude d1 si d1 aude GCS, d3 ajunge la GCS prin d1. Recupereaza
misiunea pierduta la partitii.

```bash
# L0 -- nucleul pur
python3 ~/ros2_ws/src/mesh_plugin/mesh_plugin/mesh_core.py        # astept: 21/21

# L1 -- SIL (figuri in directorul curent)
cd ~/ros2_ws/src/mesh_plugin/mesh_plugin
python3 sil_mesh.py            # reachability stea vs mesh in timp
python3 sil_mesh_mission.py    # acoperire + victime, stea vs mesh, cu cost

# L2 -- ROS
cd ~/ros2_ws && colcon build --packages-select mesh_plugin --symlink-install
source install/setup.bash
ros2 launch mesh_plugin mesh_plugins.launch.py        # tesatura mesh (per drona + GCS)
ros2 topic echo /mesh/route/d3                        # ruta live a dronei d3
```
**Ce ar trebui sa vezi:** `partition_2v2` stea 2/4 -> mesh 4/4 (doua drone salvate
prin releu); misiune coridor: acoperire 41% -> 84%, victime 2/5 -> 5/5; cost ~2.5
hopuri, ETX ~3.05, ~30 ms latenta in plus.
**Detalii:** `mesh_plugin/README.md`.

### 2.2 link_adaptive -- strat adaptiv la starea legaturii (+ adaptorul)
**De ce:** daca niciun middleware nu domina, adapteaza-te. Masoara legatura
(RTT p95 + pierdere) si comuta moduri (NOMINAL/DEGRADED/CRITICAL) cu histerezis;
adaptorul aplica decizia pe telemetrie (rata, prospetime, payload, QoS).

```bash
# L0 -- cele doua nuclee
python3 ~/ros2_ws/src/link_adaptive/link_adaptive/link_adaptive_core.py   # 22/22
python3 ~/ros2_ws/src/link_adaptive/link_adaptive/policy_applier.py        # 13/13

# L1 -- SIL-uri
cd ~/ros2_ws/src/link_adaptive/link_adaptive
python3 sil_link_adaptive.py    # adaptiv vs static (control ~14x mai proaspat)
python3 sil_policy_loop.py      # bucla completa decide+aplica (debit 20->10->2 Hz)

# L2 -- ROS: decizia singura
cd ~/ros2_ws && colcon build --packages-select link_adaptive --symlink-install
source install/setup.bash
ros2 launch link_adaptive link_adaptive.launch.py
ros2 topic echo /link_adaptive/policy                 # politica publicata

# L2 -- bucla completa (decizie + adaptor pe calea telemetriei)
ros2 launch link_adaptive link_adaptive_loop.launch.py
```
**Demo live de tranzitie** (in 3 terminale, fiecare cu `source install/setup.bash`):
```bash
# T1: ros2 launch link_adaptive link_adaptive.launch.py
# T2: ros2 topic echo /link_adaptive/state
# T3: forteaza CRITICAL injectand RTT mare:
ros2 topic pub -r 5 /operator/heartbeat std_msgs/msg/String '{data: "{\"rtt_ms\": 900}"}'
#  -> in ~2 s T2 arata mode=CRITICAL; pune 300 pt DEGRADED; opreste pub -> revine la NOMINAL
```
**Ce ar trebui sa vezi:** modul urmareste legatura; pe bucla, debitul scade
20->10->2 Hz si payload-ul FULL->REDUCED->CRITICAL cand legatura se degradeaza.
**Detalii:** `link_adaptive/README.md`.

### 2.3 campaign_stats -- rigoarea statistica (orice campanie)
**De ce:** un recenzent cere bare de eroare si semnificatie, nu o singura rulare.
Da intervale de incredere (bootstrap) pe percentile, test KS (zenoh vs DDS) si
CDF cu benzi de incredere.

```bash
# L0
python3 ~/ros2_ws/src/c1_benchmark/campaign_stats.py --selftest          # 17/17

# L1 -- pe date sintetice (vezi formatul + figurile)
python3 ~/ros2_ws/src/c1_benchmark/campaign_stats.py --demo --out /tmp/stats_demo
ls /tmp/stats_demo     # stats_summary.csv, stats_compare.csv, fig_cdf_band_*, fig_p95_ci

# pe DATELE REALE (dupa o campanie)
python3 ~/ros2_ws/src/c1_benchmark/campaign_stats.py ~/c1_results_full --out ~/c1_results_full/stats
#  daca nu gaseste coloana RTT: adauga --rtt-col NUME sau --glob 'transport_*.csv'
```
**Ce ar trebui sa vezi:** `stats_summary.csv` (p95 cu CI), `stats_compare.csv`
(KS D+p, CI pe diferenta p95), `fig_cdf_band_<cond>.png`, `fig_p95_ci.png`.

## 3. Componentele EXISTENTE -- unde sunt documentate si comanda de start

| Pachet | README | Start rapid |
|--------|--------|-------------|
| `c1_benchmark` | `c1_benchmark/README.md` | `./preflight.sh` apoi `python3 run_campaign.py --dry` |
| `sar_swarm` | `sar_swarm/README.md` | `python3 sil_run.py` (L0); `ros2 launch launch/sar_ros.launch.py scenario:=partition_2v2.yaml` |
| `sar_plugins` | `sar_plugins/README_PLUGINS.md` | `ros2 launch nodes/mission_sar.launch.py profile:=urban_rubble seed:=42` |
| `rehab_exo_description` | `rehab_exo_description/README.md` | `ros2 launch rehab_exo_description display.launch.py` (RViz) |
| `joint_emulator` | `joint_emulator/README.md` | `python3 tools/gen_bench_model.py` apoi vezi README |
| `teleop_rover` | `teleop_rover/README*` | vezi matricea de terminale din README |

## 4. Calea de invatare recomandata (in ordine)

1. **Offline (L0):** ruleaza toate selftest-urile (blocul din sectiunea 5.1).
   Daca-s verzi, logica intregului proiect e sanatoasa.
2. **SIL-uri (L1):** ruleaza-le si UITA-TE LA FIGURI. Aici intelegi povestea:
   mesh-ul recupereaza acoperirea; link_adaptive pastreaza controlul proaspat;
   campania arata cele doua filozofii de fiabilitate.
3. **ROS local (L2):** `colcon build` pe tot; porneste roiul (`sar_swarm`) +
   etajul de misiune (`sar_plugins`); ataseaza `mesh_plugin` si `link_adaptive`
   in paralel.
4. **Campanii + statistica:** `c1_benchmark/run_campaign.py` -> `analyze_campaign.py`
   -> `campaign_stats.py`.

REGULA: nu rula campanii si demo-uri in acelasi timp -- masuratorile se otravesc.
Inainte de orice campanie: `preflight.sh` (verdict GO/NO-GO).

## 5. Cheat-sheet de terminal

### 5.1 Toate verificarile offline (fara ROS, fara date) -- copy-paste
```bash
# nucleele NOI
python3 ~/ros2_ws/src/mesh_plugin/mesh_plugin/mesh_core.py                 # 21/21
python3 ~/ros2_ws/src/link_adaptive/link_adaptive/link_adaptive_core.py    # 22/22
python3 ~/ros2_ws/src/link_adaptive/link_adaptive/policy_applier.py        # 13/13
python3 ~/ros2_ws/src/c1_benchmark/campaign_stats.py --selftest            # 17/17
# tot depozitul (suitele existente: sar_swarm, sar_plugins, c1, joint_emulator)
cd ~/ros2_ws/src && ./smoke_all.sh
```

### 5.2 Toate SIL-urile (figuri, fara ROS)
```bash
cd ~/ros2_ws/src/mesh_plugin/mesh_plugin && python3 sil_mesh.py && python3 sil_mesh_mission.py
cd ~/ros2_ws/src/link_adaptive/link_adaptive && python3 sil_link_adaptive.py && python3 sil_policy_loop.py
python3 ~/ros2_ws/src/c1_benchmark/campaign_stats.py --demo --out /tmp/stats_demo
# figurile SIL apar in directorul curent; cele de statistica in /tmp/stats_demo
```

### 5.3 Build + rulare ROS
```bash
cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash
colcon build --symlink-install && source install/setup.bash
ros2 pkg executables mesh_plugin
ros2 pkg executables link_adaptive
# exemple de rulare: vezi sectiunile 2.1 / 2.2
```

### 5.4 Gotchas rapide
- `RTPS_TRANSPORT_SHM` la pornire -> `rm -f /dev/shm/fastrtps_*` (inofensiv).
- `Package not found` -> ai uitat `source ~/ros2_ws/install/setup.bash`.
- `ros2 run` zice "failure 1" desi a mers -> entry-point intoarce bool; folosim
  `main()` care intoarce None (deja rezolvat in pachetele noastre).
- ai schimbat `setup.py`/entry-points -> rebuild obligatoriu (wrapper-ele se
  genereaza la build).
- linie "stderr output" la colcon despre `pytest-repeat` -> cosmetica, nu eroare.

## 6. Unde gasesti restul

- **skill `sar-swarm-ros2`** -- contextul proiectului pentru sesiuni viitoare cu
  asistentul (convetii, cifre, gotchas).
- **`ROADMAP_DEZVOLTARE.md`** -- starea pachetelor, pistele de dezvoltare si
  imbunatatirile legate de articole.
