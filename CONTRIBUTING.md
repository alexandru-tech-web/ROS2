# Contributii si reproductibilitate

Ghid scurt pentru a contribui la depozit si a reproduce experimentele.

## Dependinte Python

Pachetele ROS 2 (`rclpy`, `*_msgs`, `launch`) vin din mediul ROS 2 (Jazzy).
Dependintele Python externe (pip) sunt documentate per pachet in `*/requirements.txt`:

```bash
# instaleaza dependintele unui pachet (exemplu)
python3 -m pip install -r c1_benchmark/requirements.txt
```

`tkinter` (folosit de panourile/ecranele din `sar_swarm`, `teleop_rover`,
`mesh_plugin`, `rehab_exo_description`) nu se instaleaza cu pip -- foloseste sistemul:
`sudo apt install python3-tk`.

## Protocol de reproductibilitate pentru benchmark-uri (C1)

Campania de transport compara `rmw_zenoh` vs `rmw_cyclonedds_cpp` sub `tc netem`.
Mediul TREBUIE sa fie curat inainte de masurare -- altfel apar artefacte de stare
reziduala (de ex. Zenoh apare fals "imun" la pierdere). Orchestratorul echitabil este
[`c1_benchmark/run_campaign_fair.sh`](c1_benchmark/run_campaign_fair.sh); protocolul lui:

1. **Purge inainte de fiecare rulare** (per RMW x conditie):
   ```bash
   pkill -f rmw_zenohd
   rm -f /dev/shm/*zenoh* /dev/shm/fastrtps_*
   ```
2. **Peer-to-peer, FARA router.** Routerul Zenoh crapa sub pierdere; comparatia
   cap-la-cap se face cu ambele RMW in P2P (ca DDS).
3. **Shared-memory (SHM) off.** Implicit pe ROS 2 Jazzy; nu reactiva SHM in campanie.
4. **Repetitiile prin `--reps`.** Lasa `run_campaign.py --reps N` sa scrie `rep1..repN`
   distincte; NU rula o bucla externa cu `--reps 1` (suprascrie `rep1/` -> N=1).
5. **Exclude conditiile `*_burst`.** netem corelat (burst) nu pastreaza media medie ->
   nereproductibil. Conditii valide: `ideal`, `loss_5/15/20/25/30`, `lat200_jit50`, `lat200_l15`.

Inainte de campanie ruleaza pre-flight-ul (`./preflight.sh`, respectiv pre-flight-ul din
`run_campaign_fair.sh`): daca Zenoh apare "imun" (p95 < 50 ms si pierdere < 2%) la
`loss_30`, mediul e murdar -- opreste si curata inainte de a continua.

## Igiena datelor

Datele experimentale NU se versioneaza (vezi `.gitignore` si `README.md`). Rezultatele
campaniilor se scriu in afara depozitului (`~/ros2_ws/new_data_sar/...`) si se regenereaza
cu scripturile. In git intra doar codul, scripturile de analiza si figurile
reprezentative din `*/docs/`.
