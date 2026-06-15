# sar_swarm - fisa de rezultate (campania SIL)

Sinteza rezultatelor experimentale ale roiului SAR sub degradare de retea.
Cifrele provin din campania SIL reproductibila (`run_sil_campaign.py`, seed 11,
validata pe masina de dezvoltare). Pentru cifrele de transport (Zenoh vs
Cyclone) vezi sectiunea finala - acelea se masoara pe ROS real.

---

## 1. Tabelul principal: metrici pe scenarii

| Scenariu | Acoperire | Victime | Timp [s] | e2e p95 [ms] | Goodput | Deconectat [s] | Fallback [drona*s] |
|---|---|---|---|---|---|---|---|
| baseline | 0.95 | 5/5 | 106 | 53 | 1.00 | 0 | 0 |
| loss_30 | 0.95 | 5/5 | 129 | 85 | 0.69 | 0 | 0 |
| loss_70 | 0.85 | 5/5 | 150 | 121 | 0.29 | 0 | 0 |
| gcs_delay_spike | 0.96 | 5/5 | 130 | 2296 | 0.98 | 0 | 0 |
| partition_2v2 | 0.92 | 5/5 | 150 | 18546 | 0.95 | 80 | 80 |
| drone_isolation | 0.95 | 5/5 | 112 | 77 | 0.95 | 35 | 35 |

Definitii: acoperire = fractia ariei cunoscuta la GCS; goodput = telemetrie
livrata / oferita; e2e p95 = a 95-a percentila a varstei informatiei la sosire;
fallback = drona*secunde petrecute izolat de GCS.

---

## 2. Verdicte (propozitii gata de teza)

**V1 - Degradarea produce gradient masurabil.** Goodput-ul scade monoton cu rata
de pierdere: 1.00 (baseline) -> 0.69 (loss_30) -> 0.29 (loss_70), o scadere de
70% la pierdere severa. Latenta e2e creste corespunzator: 53 -> 85 -> 121 ms.
Validat statistic pe repetitii (test_degradation: VERDICT GO).

**V2 - Roiul e rezilient la degradare moderata.** Acoperirea ramane ~0.95 si
toate cele 5 victime sunt gasite pana la loss_30; abia la loss_70 acoperirea
scade la 0.85. Sistemul isi indeplineste obiectivul de misiune chiar cand pierde
30% din pachete.

**V3 - Tipuri diferite de degradare au semnaturi diferite.**
- *Pierdere* (loss_30/70): loveste goodput-ul, e2e creste moderat.
- *Varf de latenta* (gcs_delay_spike): e2e sare la 2.3 s, dar goodput ramane
  bun (0.98) - informatia ajunge, dar veche.
- *Partitie* (partition_2v2): e2e p95 = 18.5 s (store-and-forward dupa
  reconectare), 80 drona*s in fallback - izolarea cea mai severa.
- *Izolare individuala* (drone_isolation): 35 drona*s fallback, impact limitat
  la o singura drona.

**V4 - Reteaua mesh recupereaza valoarea pierduta sub izolare.** Pe scenariul
mesh_relay (d3/d4 pierd legatura directa cu GCS): mesh-ul livreaza cu 55% mai
multa telemetrie si GCS-ul afla toate victimele cu 26 s mai devreme (64 s vs
90 s). Mesh-ul nu schimba CATE victime se gasesc, ci CAT DE REPEDE afla echipa
de salvare.

**V5 - Injectarea defectelor este efectiva (nu cosmetica).** Lantul complet
verificat in cod: fault_injector publica starea legaturilor din timeline ->
drone_node aplica gating la receptie (arunca/intarzie mesaje) -> drona intra in
fallback la caderea legaturii. Partitia produce 80 drona*s fallback, baseline 0
- defectele sunt aplicate si masurate.

---

## 3. Figuri disponibile

| Figura | Ce arata | Generata de |
|---|---|---|
| `campaign_metrics.png` | 4 metrici pe toate scenariile (medie +/- abatere) | run_sil_campaign.py |
| `mesh_mission_victims.png` | victime cunoscute la GCS in timp, cu vs fara mesh | sil_mesh_mission.py |
| `mesh_reachability.png` | drone care ajung la GCS: stea vs mesh | sil_mesh.py |
| `rmw_e2e.png` / `rmw_goodput.png` | Zenoh vs Cyclone (dupa campania ROS) | analyze_rmw.py |

---

## 4. Reproducerea rezultatelor

```bash
cd ~/ros2_ws/src/sar_swarm
python3 run_sil_campaign.py --reps 3      # tabelul principal + figuri
python3 test_degradation.py --reps 3      # verdictul V1 (gradient)
cd ~/ros2_ws/src/mesh_plugin
python3 sil_mesh_mission.py --scenario mesh_relay   # verdictul V4 (mesh)
```

Toate rezultatele sunt deterministe pe acelasi seed; repetitiile pe seed-uri
diferite dau aceleasi medii cu abateri mici (< 1% pe goodput), confirmand ca
efectele sunt robuste, nu zgomot.

---

## 5. De completat dupa campania ROS reala

Urmatoarele se masoara pe masina cu ROS2 Jazzy, NU in SIL:

- **comparatia rmw_zenoh vs rmw_cyclonedds** pe aceleasi metrici (e2e, goodput,
  acoperire) - rulata cu `mission_experiment.sh`, analizata cu `analyze_rmw.py`;
  figura money-shot `rmw_e2e.png`;
- **valorile absolute de latenta** ale fiecarui transport sub degradare reala
  (`tc netem`), nu modelate;
- **profilurile de teren** (open_field, urban_rubble, forest) pe RMW.

Structura de raportare e gata (tabel + figuri); raman de inlocuit cifrele SIL cu
masuratorile ROS pe coloana de transport.
