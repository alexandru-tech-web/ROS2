# START AICI — modelul LLR de reabilitare

Acest pachet este un **twin de cercetare**, nu un dispozitiv medical si nu un
controler pregatit pentru pacient. El reproduce structura functionala a robotului
LLR din documentatia tehnica: doua membre mecanice, fiecare cu sold, genunchi si
glezna, reglaje antropometrice, senzori si o statie de operator.

Pentru instructiunile complete destinate operatorului nou, vezi mai intai
[GHID_UTILIZARE.md](GHID_UTILIZARE.md).

## Pornire recomandata

```bash
cd /home/ubuntu/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select rehab_exo_description --symlink-install \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
ros2 launch rehab_exo_description demo_c4.launch.py gui:=true
```

Dintr-un terminal pornit in VS Code/Snap, foloseste scriptul care curata mediul:

```bash
/home/ubuntu/ros2_ws/src/rehab_exo_description/scripts/demo_cu_gui.sh
```

Lansarea deschide Gazebo, HMI-ul si graficele live. Modelul este asezat pe podea
cu `inaltime:=0.0`. Recorderul porneste automat si afiseaza in HMI calea CSV.

## Ce face operatorul

1. In fila **Exercitii**, selecteaza un exercitiu sau una dintre cele patru serii.
2. Alege repetarile si factorul temporal; acesta schimba durata, nu amplitudinea.
3. Urmareste valorile in **Senzori LLR** si graficele live.
4. Butonul STOP cere revenire controlata la postura de lucru. **Nu este E-STOP**.
5. Opreste lansarea cu `Ctrl+C`; CSV-ul este inchis si validat.

Pentru graficele exportate:

```bash
ros2 run rehab_exo_description plot_sesiune.py \
  /home/ubuntu/DATE_TWIN/<directorul_sesiunii>
```

Pentru raport PDF si metrici CSV/JSON:

```bash
ros2 run rehab_exo_description session_report.py \
  /home/ubuntu/DATE_TWIN/<directorul_sesiunii>
```

## Regula de interpretare a datelor

- pozitia, viteza si `effort_sim` vin din fizica Gazebo;
- cuplurile M2210B, fortele TR69-1500, unghiurile BWK216 si riglele sunt momentan
  **SINTETICE** si poarta aceasta eticheta pe ROS si in CSV;
- masele si inertiile sunt inca placeholdere, deci nu se trag concluzii dinamice;
- exercitiile sunt protocoale ingineresti demonstrative, nu prescriptii clinice.

Citeste apoi [MANUAL_TEHNIC_LLR.md](MANUAL_TEHNIC_LLR.md),
[HARTA_FISIERELOR.md](HARTA_FISIERELOR.md) si
[RAPORT_DATE_SI_GRAFICE.md](RAPORT_DATE_SI_GRAFICE.md), apoi
[README_DEMO.md](../README_DEMO.md).
