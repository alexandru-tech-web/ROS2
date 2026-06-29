# curs_ros2

Pachet EDUCATIONAL ROS 2 Jazzy (rclpy): un curs complet care demonstreaza
izolat conceptele de baza ROS 2 -- noduri, topice, launch, parametri, servicii,
actiuni, interfete custom, QoS, executors, TF2, lifecycle, turtlesim -- plus un
proiect final integrator (sursa: package.xml, description). Build type:
ament_python (package.xml export).

## Scop

Serveste drept referinta reproductibila pentru conceptele rclpy folosite in
restul depozitului. Pachetul NU este o contributie de cercetare; nu apare nicio
mentiune explicita C1-C4 sau A1-A5 in cod sau package.xml, deci nu se asociaza
cu vreo contributie. Interfetele custom (M7, M13) stau intr-un pachet SEPARAT,
curs_ros2_interfaces (vezi importurile din m7_*.py si m13_monitor.py), fiindca
un pachet pur Python nu poate genera tipuri rosidl.

## Arhitectura

Pachetul urmeaza partial metodologia 'nucleu pur + nod ROS subtire', dar NU pe
toate modulele:

- Nucleu PUR (fara ROS): curs_ros2/logica.py -- functii matematice de
  clasificare si geometrie, importate de noduri in loc de a fi rescrise inline
  (docstring logica.py).
- Verificare nucleu: testarea logica.py se face prin pytest (test/test_logica.py,
  referit in docstring), NU printr-un _selftest() in modul. Niciun .py din pachet
  nu contine o functie _selftest sau un bloc 'python3 <modul>.py' de autotest
  offline (verificat prin grep).
- Noduri ROS subtiri: restul fisierelor m*.py sunt noduri rclpy. Doar
  m12_turtle_control.py si m13_monitor.py importa efectiv din logica.py
  (eroare_distanta / unghi_spre_tinta / normalizeaza_unghi, respectiv
  clasifica_temperatura). Celelalte module isi tin logica inline, ca exemple
  didactice de sine statatoare.
- Strat SIL dedicat: nu exista in acest pachet. TODO: de confirmat daca un SIL
  era intentionat (nu apare niciun fisier *sil* sau scenariu).

## Fisiere

Sub curs_ros2/ (noduri rclpy + nucleu pur):

| Fisier | Rol (extras din cod/docstring) |
| --- | --- |
| logica.py | Nucleu PUR fara ROS: clasifica_temperatura, normalizeaza_unghi, eroare_distanta, unghi_spre_tinta. Testat in test/test_logica.py. |
| m1_nod_simplu.py | M1: nod minimal 'nod_simplu' cu timer 1.0 s care logheaza un contor de secunde. |
| m1_publisher.py | M2: nod 'publisher_temperatura' care publica Float64 pe /temperatura la 1 Hz. |
| m1_subscriber.py | M2: nod 'subscriber_temperatura', se aboneaza la /temperatura (Float64) si publica String pe /alarma. |
| m4_param_node.py | M4: nod 'nod_parametri' cu parametri declarati 'rata' (float) si 'mesaj' (string) plus validare. |
| m5_service_server.py | M5: nod 'server_adunare', serviciu 'aduna' (example_interfaces/AddTwoInts). |
| m5_service_client.py | M5: nod 'client_adunare', client pe serviciul 'aduna'; ia operanzii din sys.argv. |
| m6_action_server.py | M6: server de actiune 'fibonacci' (example_interfaces/Fibonacci) rulat pe MultiThreadedExecutor. |
| m6_action_client.py | M6: client de actiune 'fibonacci' care trimite un goal (order) si urmareste feedback/result. |
| m7_pub_custom.py | M7: nod 'publisher_custom' care publica tipul custom Temperatura pe /temperatura_custom. |
| m7_sub_custom.py | M7: nod 'subscriber_custom' abonat la /temperatura_custom (tip custom Temperatura). |
| m8_qos_publisher.py | M8: nod 'qos_publisher', publica String pe /qos_demo cu profil de QoS ales prin parametrul 'profil'. |
| m8_qos_subscriber.py | M8: nod 'qos_subscriber', se aboneaza la /qos_demo cu QoS ales prin parametrul 'profil'. |
| m9_executor_demo.py | M9: nod 'nod_executor' cu timer rapid (0.5 s) si lent (2.0 s) pe callback groups diferite, demonstrand MultiThreadedExecutor. |
| m10_tf_broadcaster.py | M10: difuzeaza pe /tf transformarea world -> robot (frame_id='world', child_frame_id='robot'). |
| m10_tf_listener.py | M10: nod 'tf_listener', asculta /tf prin Buffer/TransformListener si logheaza transformarea. |
| m11_lifecycle_node.py | M11: nod gestionat 'nod_lifecycle' (LifecycleNode) cu lifecycle publisher pe /lc_chatter. |
| m12_turtle_patrat.py | M12: nod care deseneaza un patrat open-loop pe /turtle1/cmd_vel (Twist), fara feedback. |
| m12_turtle_control.py | M12: control proportional go-to-goal cu feedback din /turtle1/pose, comanda pe /turtle1/cmd_vel; parametri x_tinta, y_tinta. |
| m13_senzor.py | M13: senzor SIMULAT determinist (sinusoida), publica Float64 pe /senzor/temperatura; parametri rata, valoare_baza, amplitudine. |
| m13_monitor.py | M13: monitor care asculta /senzor/temperatura, publica String pe /senzor/alarma si expune serviciul 'ajusteaza_prag' (AjustareTemperatura). |

Alte directoare:

- launch/ -- fisiere de lansare (vezi sectiunea Sintaxe de rulare).
- config/m4_params.yaml -- parametri pentru m4_param (nod_parametri: rata=2.0, mesaj=...).
- docs/ -- 14 fisiere Markdown de curs (00_introducere ... 13_proiect_final, cheatsheet_cli), instalate in share/.
- test/ -- test_logica.py plus testele standard ament (copyright, flake8, pep257).
- CURS.md -- material de curs (la radacina pachetului).

## Sintaxe de rulare

Build (din radacina workspace-ului):

    cd ~/ros2_ws && colcon build --packages-select curs_ros2 --symlink-install
    source install/setup.bash

Atentie: M7 si M13 depind de pachetul curs_ros2_interfaces; construieste-l si
da-i source inainte sa rulezi acele noduri.

Nucleu offline: logica.py NU are bloc de autotest rulabil cu
'python3 logica.py'. Verificarea nucleului se face prin pytest:

    python3 -m pytest test/test_logica.py

Rulare noduri (entry_points REALE din setup.py):

    ros2 run curs_ros2 nod_simplu
    ros2 run curs_ros2 publisher
    ros2 run curs_ros2 subscriber
    ros2 run curs_ros2 m4_param
    ros2 run curs_ros2 m5_server
    ros2 run curs_ros2 m5_client 5 7        # operanzii ajung in sys.argv
    ros2 run curs_ros2 m6_action_server
    ros2 run curs_ros2 m6_action_client
    ros2 run curs_ros2 m7_pub
    ros2 run curs_ros2 m7_sub
    ros2 run curs_ros2 m8_pub --ros-args -p profil:=reliable
    ros2 run curs_ros2 m8_sub --ros-args -p profil:=reliable
    ros2 run curs_ros2 m9_executor
    ros2 run curs_ros2 m10_broadcaster
    ros2 run curs_ros2 m10_listener
    ros2 run curs_ros2 m11_lifecycle
    ros2 run curs_ros2 m12_patrat
    ros2 run curs_ros2 m12_control
    ros2 run curs_ros2 m13_senzor
    ros2 run curs_ros2 m13_monitor

Note pe argumente:

- Niciun modul nu defineste argparse (ArgumentParser/add_argument -- verificat
  prin grep). m5_client preia operanzii din sys.argv; in m5_service_launch.py se
  paseaza arguments=['5','7'].
- m8_pub / m8_sub: parametrul 'profil' (default 'reliable'). Metoda
  construieste_qos din ambele noduri mapeaza exact trei valori: 'best_effort'
  (ReliabilityPolicy.BEST_EFFORT), 'transient' (RELIABLE + DurabilityPolicy.
  TRANSIENT_LOCAL + HistoryPolicy.KEEP_LAST) si orice altceva, inclusiv
  'reliable', cade pe ramura else (RELIABLE). depth=10 in toate cazurile.

Rulare launch (fisiere REALE din launch/):

    ros2 launch curs_ros2 m3_launch.py         # publisher + subscriber (subscriber dupa 3 s)
    ros2 launch curs_ros2 m4_param_launch.py   # m4_param incarcat din config/m4_params.yaml
    ros2 launch curs_ros2 m5_service_launch.py # m5_server + m5_client cu arguments ['5','7']
    ros2 launch curs_ros2 m10_tf_launch.py     # m10_broadcaster + m10_listener
    ros2 launch curs_ros2 m12_turtle_launch.py # turtlesim_node + m12_control (dupa 2 s)
    ros2 launch curs_ros2 m13_proiect_launch.py # m13_senzor + m13_monitor cu parametri inline

## Parametri si topicuri

Parametri ROS declarati in cod (declare_parameter):

- m4_param_node.py: 'rata' (float, default 1.0), 'mesaj' (string, default 'Salut din parametri').
- m8_qos_publisher.py / m8_qos_subscriber.py: 'profil' (string, default 'reliable').
- m12_turtle_control.py: 'x_tinta' (default 8.0), 'y_tinta' (default 8.0).
- m13_senzor.py: 'rata' (default 2.0), 'valoare_baza' (default 25.0), 'amplitudine' (default 20.0).
- m13_monitor.py: 'prag_atentie' (default 30.0), 'prag_critic' (default 50.0).

Topicuri (din create_publisher / create_subscription):

| Nod (entry_point) | Publica | Se aboneaza |
| --- | --- | --- |
| publisher | /temperatura (std_msgs/Float64) | - |
| subscriber | /alarma (std_msgs/String) | /temperatura (std_msgs/Float64) |
| m7_pub | /temperatura_custom (curs_ros2_interfaces/Temperatura) | - |
| m7_sub | - | /temperatura_custom (curs_ros2_interfaces/Temperatura) |
| m8_pub | /qos_demo (std_msgs/String) | - |
| m8_sub | - | /qos_demo (std_msgs/String) |
| m10_broadcaster | /tf (world -> robot) | - |
| m10_listener | - | /tf |
| m11_lifecycle | /lc_chatter (std_msgs/String, lifecycle publisher) | - |
| m12_patrat | /turtle1/cmd_vel (geometry_msgs/Twist) | - |
| m12_control | /turtle1/cmd_vel (geometry_msgs/Twist) | /turtle1/pose (turtlesim/Pose) |
| m13_senzor | /senzor/temperatura (std_msgs/Float64) | - |
| m13_monitor | /senzor/alarma (std_msgs/String) | /senzor/temperatura (std_msgs/Float64) |

Servicii / actiuni:

- m5_server: serviciu 'aduna' (example_interfaces/AddTwoInts); m5_client il apeleaza.
- m6_action_server: actiune 'fibonacci' (example_interfaces/Fibonacci); m6_action_client trimite goal.
- m13_monitor: serviciu 'ajusteaza_prag' (curs_ros2_interfaces/AjustareTemperatura).

Nota privind metodologia JSON pe std_msgs/String: in acest pachet NU se vede
serializare JSON in mesaje. Topicurile String (/alarma, /qos_demo, /senzor/alarma,
/lc_chatter) transporta text simplu (camp 'data'), nu JSON. Continutul textual
exact al mesajelor String (extras din callback-uri):
- /alarma (m1_subscriber.py): 'VALOARE NORMALA!' / 'VALOARE DE ATENTIONARE!' /
  'VALOARE CRITICA', dupa pragurile 30.0 / 50.0 hardcodate inline.
- /senzor/alarma (m13_monitor.py): statusul brut 'NORMAL' / 'ATENTIE' / 'CRITIC'
  intors de clasifica_temperatura.
- /qos_demo (m8_qos_publisher.py): 'mesaj #N' cu un contor crescator.
- /lc_chatter (m11_lifecycle_node.py): 'salut din nodul lifecycle'.
