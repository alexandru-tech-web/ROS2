# Nepotrivirea de RMW care a aratat luni de zile ca un defect de ros2_control

Simptom: `/controller_manager/list_controllers` exista si nu raspunde niciodata;
spawnerele dau timeout, iar topicurile merg impecabil. Cauza: launch-ul pinuia
`rmw_cyclonedds_cpp` intr-un `GroupAction` scoped, care isi retrage mediul inainte
ca nodurile nascute din `RegisterEventHandler` sa porneasca -- deci ele porneau pe
implicit, `rmw_fastrtps_cpp`.

Relevanta pentru teza: e o dovada experimentala directa ca in ROS 2 interoperarea
intre implementari RMW **nu e uniforma pe tipuri de comunicare** -- discovery-ul de
noduri si pub/sub-ul trec, request/reply-ul nu. Un sistem mixt pare sanatos la orice
inspectie bazata pe topicuri si e complet nefunctional pe servicii. Asta atinge
direct C1 (comparatia Zenoh vs CycloneDDS) si disciplina de instrumentare din teza:
un indicator care se uita doar la topicuri poate raporta verde pe un sistem mort.

## Fisiere

| fisier | ce arata |
|---|---|
| `MATRICE_TEST_CM.md` | testul pe ipoteze, o variabila pe rand |
| `serviciu_fastrtps_cpp.log` | acelasi apel, client pe FastRTPS: cod 124 (timeout) |
| `serviciu_cyclonedds_cpp.log` | acelasi apel, client pe CycloneDDS: cod 0, trei controlere |
| `pubsub_vs_servicii_fastrtps.log` | contrastul in patru pasi, pe acelasi client nepotrivit |
| `gazebo_gui_crash.log` | cauza independenta #1: GUI-ul care ia serverul cu el |

Toate rulate pe 21 aug 2026, ROS 2 Jazzy, `gz_ros2_control` 1.2.17, Gazebo Sim 8.11.0.
