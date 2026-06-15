# sar_swarm + GCS - documentatie tehnica detaliata

Roi de drone SAR (Search and Rescue) coordonat printr-o statie de sol (GCS),
operand peste o retea degradata. Al doilea demonstrator al tezei (control la
distanta in timp real), complementar roverului teleoperat: aici degradarea
loveste coordonarea MULTI-AGENT si fuziunea hartilor la GCS, nu o singura bucla
de teleoperare.

Acelasi principiu de inginerie ca tot proiectul: nuclee pure testabile fara ROS
(`sar_core`, `swarm_core`, `netem_core`) impachetate in noduri ROS2 subtiri.
Logica se valideaza prin SIL (Software-in-the-Loop) inainte de rularea reala.

---

## 1. Ideea si bucla completa

Patru drone (`d1..d4`) exploreaza o arie cu ruine si fum, cautand 5 victime.
Fiecare drona:
- isi alege o tinta de explorare (frontiera hartii necunoscute);
- zboara, descopera celule libere si victime cu senzorul de bord;
- trimite periodic telemetrie la GCS (pozitie, celule noi, victime gasite).

GCS-ul fuzioneaza hartile partiale ale tuturor dronelor intr-o harta globala,
calculeaza acoperirea si tine evidenta victimelor raportate. Comenzile (tinte,
RTL) merg de la GCS spre drone.

**Unde intra degradarea:** fiecare mesaj trece printr-un canal cu latenta,
jitter, pierdere si caderi. Gating-ul se aplica la RECEPTIE: un mesaj e
intarziat, aruncat sau blocat dupa starea legaturii. Cand o drona pierde
legatura cu GCS, intra in FALLBACK (continua local, tampon store-and-forward) si
livreaza tot la reconectare. Astfel, degradarea retelei devine o variabila
masurabila a misiunii: cat de bine isi face roiul treaba cand reteaua e proasta.

**Rezultatul masurabil (contributia):** acoperirea, timpul misiunii, latenta
end-to-end a telemetriei si goodput-ul se degradeaza controlat cu severitatea
scenariului. Comparatia rmw_zenoh vs rmw_cyclonedds pe aceleasi metrici, sub
aceeasi degradare, e payoff-ul de transport al tezei.

---

## 2. Lumea (world_config.py, gen_world.py)

Lumea e UNICA sursa de adevar (`world_config.py`), folosita identic de SIL,
nodurile ROS, dashboard si generarea lumii Gazebo (1 celula = 1 m):
- arie 60 x 60 m;
- 7 zone de ruine (obstacole/zone inaccesibile);
- 3 zone de fum (senzor degradat);
- 5 victime in pozitii fixe (reproducibil).

`gen_world.py` produce lumea Gazebo (SDF) din aceeasi configuratie, ca simularea
3D sa coincida cu modelul SIL.

---

## 3. Nodurile

### 3.1 drone_node.py - drona SAR
Localizare + navigatie + descoperire + comunicatie. Publica telemetrie pe
`/sar/telemetry` (cu timestamp de emisie, pentru latenta e2e), pozitia pe
`/sar/pose/{id}`. Asculta comenzi pe `/sar/operator`. La pierderea legaturii cu
GCS trece prin masina de stari de avarie: LINKED -> LOCAL -> RETURN -> LOITER,
tamponand telemetria; la reconectare livreaza tamponul.

### 3.2 gcs_node_ros.py - statia de sol
Fuzioneaza hartile (`merge_cells`), calculeaza acoperirea si coeziunea, tine
evidenta victimelor, trimite comenzi. Scrie `mission_metrics.csv` (serie de
timp: acoperire, victime, coeziune, drone conectate, latenta e2e, mesaje
livrate). Calculeaza latenta e2e din timestamp-ul telemetriei.

### 3.3 fault_injector_node.py - injectarea defectelor
Parcurge timeline-ul scenariului YAML si, la momentul fiecarui eveniment,
modifica starea legaturilor si publica `/sar/linkstate`. Tipuri de evenimente:
`isolate` (o drona), `partition` (doua grupuri), `set_link` (o legatura),
`set_all` (toate), `heal_partition`, `restore_node`. Logheaza fiecare eveniment.

### 3.4 dashboard_node.py - vizualizare live
Harta Tkinter cu pozitiile dronelor, victimele, acoperirea, starea legaturilor.
Buton de comanda (click pe harta = tinta pentru drona).

### 3.5 latency_probe.py - sonda RTT
Trimite ping-uri periodice si masoara RTT-ul la GCS (complementar latentei e2e a
telemetriei reale).

---

## 4. Topicuri

| Topic | Tip | Producator -> Consumator | Continut |
|---|---|---|---|
| `/sar/telemetry` | String (JSON) | drone -> GCS | `{k:telemetry, id, pos, t, cells, victims}` |
| `/sar/pose/{id}` | String (JSON) | drone -> dashboard | pozitia live |
| `/sar/operator` | String (JSON) | GCS -> drone | comenzi (goto, rth) |
| `/sar/linkstate` | String (JSON) | fault_injector -> drone | `{down:[...], lat_ms, jit_ms, loss}` |
| `/sar/battery` | String (JSON) | battery_node -> GCS | SOC + stare per drona |
| `/mission/coverage` | String (JSON) | coverage -> GCS | acoperire + jaloane |
| `/sar/probe/stats` | String (JSON) | latency_probe -> GCS | RTT |

**Regula unui singur publisher pe `/sar/linkstate`:** ori `fault_injector_node`
(scenarii), ori `radio_link_node` din sar_plugins (degradare pe distanta) -
niciodata ambele simultan.

---

## 5. Cum se ruleaza

### 5.1 SIL (fara ROS, orice masina) - recomandat pentru validare
```bash
cd ~/ros2_ws/src/sar_swarm

# o singura misiune:
python3 sil_run.py scenarios/baseline.yaml
python3 sil_run.py scenarios/partition_2v2.yaml

# campania completa (toate scenariile x N repetitii) + verdict:
python3 run_sil_campaign.py --reps 3

# validarea ca degradarea produce gradient masurabil:
python3 test_degradation.py --reps 3
```

### 5.2 ROS real (campania de benchmark Zenoh vs Cyclone)
```bash
# preflight (mediul curat):
bash sar_plugins/tools/preflight_misiune.sh

# campania (2 RMW x profiluri x repetitii):
RMWS="cyclonedds zenoh" REPS=5 DUR=300 bash sar_plugins/tools/mission_experiment.sh

# analiza:
python3 sar_plugins/tools/analyze_missions.py ~/mission_results
python3 analyze_rmw.py ~/mission_results       # figura money-shot Zenoh vs Cyclone
```

**REGULA C1:** in timpul campaniei de benchmark NU rula nimic altceva (Gazebo,
dashboard) - masuratorile se otravesc.

---

## 6. Metrici si analiza (payoff-ul stiintific)

Metrici produse (atat SIL cat si ROS, consistente):
- **acoperire** - cat din arie cunoaste GCS-ul (din ce i-a ajuns);
- **victime gasite** - obiectivul misiunii (5 = succes);
- **timp misiune** - pana la 95% acoperire + 5 victime;
- **latenta e2e telemetrie (p50/p95)** - cat de veche e informatia la GCS;
  diferit de RTT-ul sondei: masoara fluxul real de date al misiunii;
- **goodput** - fractia de telemetrie care ajunge (livrate/oferite);
- **timp deconectat / fallback** - cat sunt dronele izolate de GCS.

### Rezultate SIL (campania de validare, seed 11)

| Scenariu | Acoperire | Victime | Timp [s] | e2e p95 [ms] | Goodput | Deconectat [s] | Fallback [drona*s] |
|---|---|---|---|---|---|---|---|
| baseline | 0.95 | 5/5 | 106 | 53 | 1.00 | 0 | 0 |
| loss_30 | 0.95 | 5/5 | 129 | 85 | 0.69 | 0 | 0 |
| loss_70 | 0.85 | 5/5 | 150 | 121 | 0.29 | 0 | 0 |
| gcs_delay_spike | 0.96 | 5/5 | 130 | 2296 | 0.98 | 0 | 0 |
| partition_2v2 | 0.92 | 5/5 | 150 | 18546 | 0.95 | 80 | 80 |
| drone_isolation | 0.95 | 5/5 | 112 | 77 | 0.95 | 35 | 35 |

Observatii cheie:
- **goodput scade monoton cu pierderea** (1.00 -> 0.69 -> 0.29) - degradarea e
  cuantificabila, validata statistic (test_degradation: GO).
- **e2e p95 la partition = 18.5 s** - informatia ajunge foarte veche prin
  store-and-forward dupa reconectare; RTT-ul sondei nu ar fi prins asta.
- **gcs_delay_spike: e2e 2.3 s** - varful de latenta injectat se vede direct.
- **acoperirea ramane robusta** (~0.95) pana la loss_70 - roiul isi face treaba
  chiar sub degradare moderata; abia la 70% pierdere scade la 0.85.
- **victime 5/5 peste tot** - obiectivul se atinge; ce difera e CAT DE REPEDE
  afla GCS-ul (vezi stratul mesh).

### Stratul mesh (contributia C3)
Pe scenariul `mesh_relay` (d3/d4 pierd legatura directa cu GCS dar pastreaza
vecinii), comparatia CU vs FARA mesh:
- **+55% telemetrie livrata** prin relay multi-hop;
- **GCS afla toate victimele cu 26 s mai devreme** (64 s vs 90 s).

Mesh-ul nu schimba CATE victime se gasesc, ci CAT DE REPEDE afla echipa de
salvare - metrica de impact direct in SAR.

---

## 7. Rolul in teza

`sar_swarm` e demonstratorul de coordonare multi-agent al tezei. Acopera trei
contributii:
- **rezilienta roiului la degradarea retelei** - acoperire/victime mentinute sub
  pierdere, partitie, izolare (datele de mai sus);
- **comparatia de transport** rmw_zenoh vs rmw_cyclonedds pe aceleasi metrici de
  misiune, sub aceeasi degradare (articolul aplicativ);
- **reteaua mesh multi-hop** (`mesh_plugin`) - recuperarea telemetriei dronelor
  izolate, cuantificata in context de misiune.

Impreuna cu teleop_rover (teleoperare in bucla inchisa) si benchmarkul C1
(microbenchmark pub-sub), formeaza argumentul complet: de la stratul de transport
la aplicatia SAR.

---

## 8. Limite oneste

- **SIL aproximeaza, nu inlocuieste ROS real.** Modelul de canal (gating la
  receptie) reproduce efectul observabil al degradarii, dar nu dinamica fina a
  stivei DDS/Zenoh. Cifrele de transport (Zenoh vs Cyclone) trebuie masurate pe
  ROS real; SIL valideaza ca metricile si scenariile sunt corecte.
- **Mesh-ul in SIL e rutat centralizat** (Dijkstra global); un mesh real e
  distribuit, cu vedere partiala. Nodul ROS aproximeaza asta cu beacon-uri.
- **Latenta e2e la partition (18.5 s) e dominata de store-and-forward** - e
  corecta (informatia chiar ajunge veche), dar trebuie raportata ca atare, nu ca
  latenta de transport.
- **Victime 5/5 in toate scenariile SIL** - obiectivul se atinge mereu pentru ca
  store-and-forward + timp suficient livreaza tot; diferenta e in dinamica
  (timpul pana la cunoastere), nu in rezultatul final.

---

## 9. Harta fisierelor

```
sar_swarm/
├── nuclee pure (fara ROS, testate):
│   ├── sar_core.py          lume, harta descoperita, alocare frontiere, coeziune
│   ├── swarm_core.py        cinematica drone, legi de viteza
│   ├── netem_core.py        canalul degradat (Channel, LinkState, scenarii)
│   └── world_config.py      lumea (sursa unica de adevar)
├── noduri ROS:
│   ├── drone_node.py        drona (telemetrie cu timestamp e2e, fallback)
│   ├── gcs_node_ros.py      statia de sol (fuziune, metrici e2e)
│   ├── fault_injector_node.py  injectarea defectelor din scenariu
│   ├── dashboard_node.py    vizualizare live
│   └── latency_probe.py     sonda RTT
├── SIL si analiza:
│   ├── sil_run.py           SIL o misiune (metrici complete)
│   ├── run_sil_campaign.py  orchestrator: toate scenariile x N + figuri
│   ├── test_degradation.py  validarea gradientului (GO/NO-GO)
│   ├── analyze_rmw.py        figura money-shot Zenoh vs Cyclone
│   ├── analyze_disconnect.py cronologia deconectarilor
│   └── plot_comparison.py    comparatii pe scenarii
├── scenarios/               baseline, loss_30/70, partition_2v2,
│                            drone_isolation, gcs_delay_spike, mesh_relay
├── gen_world.py             lumea Gazebo din world_config
└── sar_launcher.py          lansarea roiului
```

---

## 10. Depanare rapida

| Simptom | Cauza | Solutie |
|---|---|---|
| `KeyError: lat_samples` la SIL | netem_core vechi | copiaza versiunea noua (lat_samples in snapshot) |
| `RTPS_TRANSPORT_SHM` (Fast DDS) | procese omorate | `rm -f /dev/shm/fastrtps_*` |
| linkstate cu doi publisheri | fault_injector + radio_link simultan | porneste doar unul |
| victime 5/5 nu separa scenariile | normal (obiectivul se atinge) | uita-te la timpul pana la cunoastere / e2e |
| `mesh_relay.yaml not found` din mesh_plugin | scenariile-s in sar_swarm | da calea completa sau copiaza scenarios/ |
| colcon nu vede pachetul | `.git` imbricat | `bash check_repo.sh` (sectiunea 6) |
