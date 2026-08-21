# Matricea testului CM (21 aug 2026)

O variabila pe rand. Ipotezele au fost testate in ordinea din planul zilei.

| # | ipoteza testata | masuratoare | verdict |
|---|---|---|---|
| 1 | ceasul `/clock` nu ajunge la CM | bridge prezent, 1 publisher, **0 mesaje** in 8 s | simptom, nu cauza |
| 2 | lumea nu paseste | `gz sim -s -r` -> 667 Hz; `gz sim -r` (cu GUI) -> **0 mesaje** | **CAUZA #1** |
| 2b | de ce moare cu GUI | `symbol lookup error: /snap/core20/.../libpthread.so.0: __libc_pthread_init`, apoi `Escalating to SIGKILL on [Gazebo Sim Server]` | mediu snap VSCode |
| 2c | se poate curata din `LD_LIBRARY_PATH` | nu: crapa identic (snap injecteaza si `LOCPATH`, `GTK_PATH`, `GIO_MODULE_DIR`) | se ruleaza headless |
| 3 | spawnere / timeout prea mic | serviciile exista, apelul nu se intoarce in 30 s; timeout 60 nu ajuta | simptom |
| 3b | executor infometat vs mutex pe `controllers_lock_` | **nici serviciul de parametri** nu raspunde | nu e mutex |
| 3c | nepotrivire de RMW | gardianul raporta `rmw_cyclonedds_cpp`; CLI-ul si spawnerele erau pe `rmw_fastrtps_cpp` | **CAUZA #2** |
| 4 | headless vs GUI, threading de executor | acoperit la 2 | inchis |

## Proba pentru cauza #2

Aceeasi simulare pornita, acelasi apel, la cateva secunde distanta; singura
variabila schimbata e RMW-ul clientului:

    RMW_IMPLEMENTATION=rmw_fastrtps_cpp    ros2 control list_controllers -> cod 124 (timeout)
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp  ros2 control list_controllers -> cod 0, 3 controlere

Iar pe acelasi client nepotrivit, in patru pasi:

| pas | rezultat |
|---|---|
| `ros2 node list` | **merge** -- 9 noduri, inclusiv `/controller_manager` |
| `ros2 topic hz /joint_states` | **merge** -- ~95 Hz |
| `ros2 service list \| grep controller_manager` | **gol** in aceasta rulare |
| `ros2 control list_controllers` | **timeout**, cod 124 |

Nota de onestitate: la o rulare anterioara din aceeasi zi, `ros2 service list`
CHIAR a aratat servicii ale lui `controller_manager` sub RMW nepotrivit, desi
apelul tot nu s-a intors. Deci discovery-ul de servicii peste implementari
diferite e neconsecvent, nu uniform absent. Ce a fost consecvent in toate
rularile: apelul nu se intoarce niciodata.

## De ce a fost greu de vazut

A treia cauza -- gardianul RMW din Valul 1 -- raporta VERDE. El se executa in
procesul launch-ului, unde mediul grupului era inca activ, deci masura exact
partea care functiona. Este a patra aparitie a clasei "trece din motivul gresit"
in acest proiect.
