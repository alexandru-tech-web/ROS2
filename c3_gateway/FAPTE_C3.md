# FAPTE_C3.md -- gate de fapte, etapa 1 (C3: gateway de selectie a transportului)

DOMENIU: acest fisier este gate-ul de fapte al ETAPEI 1 si ramane la ce s-a masurat la
2026-08-06. NU descrie starea curenta a pachetului -- de atunci au aparut nucleul,
IPC-ul, agentii, nodul gateway si sonda de canal, toate verificate pe loopback. Pentru
starea curenta: `README.md`. Pentru pori si decizii: `~/PHD/BORD/DECIZII.md`.

Regula C1/C2, aplicata din prima zi: FAPTELE inainte de orice cod, fiecare cifra cu
comanda care o produce. Nimic din ce urmeaza nu e citat din documentatie sau din issue-uri;
totul e masurat pe masina asta, la data de mai jos. Harness-ul e in `gate/` (nu face parte
din pachetul instalat).

Masurat: 2026-08-06, laptop M1 (acelasi pe care s-au facut C1/C2 SIL).
Mediu: ROS 2 Jazzy, `ROS_DOMAIN_ID=77` (domeniu separat, ca sa nu atinga nimic din campanii).
Interpretor: `/usr/bin/python3` 3.12.3 -- ATENTIE, `python3` implicit pe masina asta e
Anaconda 3.13 si NU poate incarca rclpy (extensiile sunt compilate pentru 3.12); harness-ul
foloseste explicit calea de sistem.

## (a) Mediu si RMW-uri disponibile

    $ ros2 doctor --report | grep -A2 "RMW MIDDLEWARE"
    RMW MIDDLEWARE
    middleware name    : rmw_fastrtps_cpp        <- implicitul masinii

    $ ros2 pkg list | grep '^rmw_'
    rmw_cyclonedds_cpp  rmw_dds_common  rmw_fastrtps_cpp  rmw_fastrtps_shared_cpp
    rmw_implementation  rmw_implementation_cmake  rmw_zenoh_cpp

    versiuni (dpkg):
      ros-jazzy-rmw-cyclonedds-cpp   2.2.3-1noble.20260412.033317
      ros-jazzy-rmw-fastrtps-cpp     8.4.3-1noble.20260412.034154
      ros-jazzy-rmw-zenoh-cpp        0.2.9-1noble.20260412.030951

rmw_zenoh_cpp e **0.2.9**, adica exact versiunea despre care aveam nevoie de cifre proprii.

## (b) Doua RMW-uri diferite NU se vad reciproc -- PREMISA Arhitecturii B

Protocol: abonat pornit primul si lasat sa se aseze (0.5 s dupa READY), apoi publicator
la 10 Hz timp de 10 s; abonatul asteapta primul mesaj maximum 12 s. Topic `/c3_gate`,
`std_msgs/String`, QoS implicit. Pentru zenoh, routerul `rmw_zenohd` a fost pornit inainte.

CONTROALELE POZITIVE SUNT OBLIGATORII: fara ele, "nu s-a livrat nimic" nu dovedeste
izolarea, ci doar ca harness-ul e stricat. (Prima varianta a harness-ului chiar era
stricata -- controlul pozitiv a picat si a scos la iveala problema de interpretor.)

    abonat            publicator          rezultat
    ----------------------------------------------------------------
    cyclonedds        cyclonedds          LIVRAT   (0.438 s de la spawn)   <- control +
    zenoh             zenoh               LIVRAT   (0.428 s de la spawn)   <- control +
    cyclonedds        zenoh               NIMIC in 12 s
    zenoh             cyclonedds          NIMIC in 12 s

CONCLUZIE: pe masina asta, doua procese cu RMW_IMPLEMENTATION diferit ruleaza simultan si
NU comunica. Premisa Arhitecturii B (stive paralele, una per RMW, in acelasi sistem) e
confirmata experimental, nu presupusa.

## (c) SetEnvironmentVariable in GroupAction izoleaza REAL

Trei procese identice pornite din acelasi launch: doua in cate un `GroupAction` cu
`SetEnvironmentVariable('RMW_IMPLEMENTATION', ...)`, al treilea in AFARA oricarui grup, ca
martor. Mediul mostenit a fost pus intentionat pe `rmw_fastrtps_cpp`, diferit de ambele
grupuri, ca o eventuala scurgere sa fie vizibila. Fiecare proces raporteaza si variabila de
mediu, si `rclpy.get_rmw_implementation_identifier()` (adevarul, nu intentia).

    SCOPE grup-cdds   env=rmw_cyclonedds_cpp   efectiv=rmw_cyclonedds_cpp
    SCOPE grup-zenoh  env=rmw_zenoh_cpp        efectiv=rmw_zenoh_cpp
    SCOPE in-afara    env=rmw_fastrtps_cpp     efectiv=rmw_fastrtps_cpp

CONCLUZIE: `GroupAction` e scoped implicit; valoarea setata intr-un grup NU se scurge nici
in celalalt grup, nici in afara. Trei RMW-uri diferite, intr-un singur `ros2 launch`, fiecare
proces cu al lui. Arhitectura B se poate lansa dintr-un singur launch file.

## (d) Cost de re-stabilire: de la lansare la PRIMUL mesaj livrat

Abonatul e deja pornit si asezat; se masoara de la `Popen` al publicatorului pana la
momentul in care abonatul primeste primul mesaj. 5 repetitii per RMW. Pentru zenoh,
routerul rula DEJA (cifra NU include pornirea routerului).

    RMW            total de la spawn [s]                    MEDIANA   primul mesaj
    ------------------------------------------------------------------------------
    cyclonedds     0.408 0.444 0.454 0.424 0.429             0.429     msg0 de 5 ori
    zenoh          0.417 0.436 0.438 0.428 0.425             0.428     msg0 de 5 ori

    din care, dupa pornirea interpretorului (de la `import rclpy` la primul mesaj):
    cyclonedds     0.381 0.408 0.427 0.396 0.389             0.396
    zenoh          0.379 0.398 0.402 0.391 0.386             0.391

Observatii ONESTE despre cifra asta:
1. Cele doua RMW-uri sunt NEDISTINGIBILE la granularitatea asta (0.429 vs 0.428 s).
2. Costul e dominat de pornirea procesului Python, nu de transport: ~0.03 s pana la
   `import rclpy`, restul e import + init + descoperire.
3. **Primul mesaj publicat (msg0) a ajuns de fiecare data, la ambele RMW-uri**: potrivirea
   publicator-abonat se terminase deja cand a plecat primul mesaj. Deci descoperirea e
   INCLUSA in cele ~0.4 s de initializare, nu adaugata dupa.
4. Cifra e pentru un proces NOU. In Arhitectura B ambele stive sunt deja pornite si
   potrivite, deci comutarea traficului intre ele costa mai putin de atat. 0.43 s e un
   plafon superior masurat, si asa il folosim la derivarea dwell-time-ului (conservator).
5. NU s-a masurat costul pornirii routerului Zenoh -- pe HIL el ruleaza permanent.

## Ce inseamna asta pentru etapa urmatoare

- Arhitectura B e viabila: (b) + (c) confirmate.
- Dwell-time-ul minim se deriveaza din 0.43 s (vezi `core/switching.py`, constanta
  `COST_RESTABILIRE_S` si factorul documentat acolo), NU dintr-o cifra aleasa din burta.
- Cele ~0.4 s de pornire a procesului sunt un argument in plus pentru stive PRE-PORNITE:
  daca gateway-ul ar porni procesul la comutare, ar plati 0.43 s de tacere la fiecare
  schimbare de transport.

## Reproducere

    bash gate/g_router.sh start                       # doar pentru scenariile zenoh
    bash gate/g_run.sh rmw_cyclonedds_cpp rmw_zenoh_cpp "cdds<-zenoh"
    bash gate/g_timing.sh rmw_cyclonedds_cpp 5
    bash gate/g_scope.sh
    bash gate/g_router.sh stop

Scripturile din `gate/` importa rclpy: sunt UNELTE DE MASURA pentru gate, nu fac parte din
pachetul instalat (`setup.py` nu le declara) si nu sunt noduri ale gateway-ului.
