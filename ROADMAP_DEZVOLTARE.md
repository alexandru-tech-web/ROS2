# Roadmap de dezvoltare — starea depozitului si urmatoarele proiecte

Document ADITIV (nu inlocuieste nimic): fotografia depozitului la 12.06.2026
si planul de dezvoltare de dupa submisia SSRR. Regula de fier ramane:
NIMIC nu se construieste inainte de 18.06 in afara diagnosticelor.

## 1. Starea depozitului (9 pachete + documentatie)

| Pachet / zona | Stare | Ce mai poate primi |
|---|---|---|
| `c1_benchmark` | INCHEIAT (N=5, articol in paper/) | dupa 18.06: varianta pe retea reala (vezi T2) |
| `sar_swarm` | INCHEIAT, sub inghet | dupa 18.06: integrarea stratului adaptiv (T1) |
| `sar_plugins` | functional; lant baterie/radio de DIAGNOSTICAT | fix parse telemetrie; campania M cu REPS=5 (decide M2) |
| `joint_emulator` | complet in simulare | T3: ModbusBackend din placuta drive-urilor -> fier |
| `rehab_exo_description` | complet v0.3.0 | testul 6a (failsafe pe down) — mic, 2-3 h |
| `teleop_rover` | complet, arhiva activa | nimic necesar; demonstrator pentru prezentari |
| `servo_control` | arhiva | nimic |
| `curs_ros2(_interfaces)` | complet M0-M13 | devine continutul v0.1 al ecosistemului educational |
| documentatie (README-uri, TEHNOLOGII, PARAMETRI...) | completa si impinsa | se actualizeaza odata cu codul nou |

## 2. Cele trei piste de dezvoltare (dupa 18.06)

### T1 — NOU DE LA ZERO: `link_adaptive` (contributia C3 din planul tezei)
Rezultatul N=5 a demonstrat ca NICIUN middleware nu domina: DDS cumpara
supravietuirea misiunii cu intarziere uniforma, Zenoh cumpara prospetimea cu
pierderi care devin pierderi de misiune. Concluzia logica si urmatorul articol:
DACA niciunul nu domina, ADAPTEAZA-TE. Un strat aplicativ care isi schimba
comportamentul dupa starea legaturii. Design complet: PROIECT_LINK_ADAPTIVE.md.
Efort: ~25-35 h pe 8-10 saptamani. Tinta publicare: A2 (SSRR/ICRA-W 2027).

### T2 — IMBUNATATIRE: `field_kit` (ucide critica "doar simulare")
Cel mai ieftin pas spre real: a doua masina + AP dedicat + mers-pe-jos cu
RSSI -> profil de canal CALIBRAT + tabelul C1 pe legatura reala. Reutilizeaza
TOT ce exista. Design: PROIECT_FIELD_KIT.md. Efort: ~10-14 h total (kit 4-6 h
+ sesiune de teren 3-4 h + analiza). Alimenteaza camera-ready A1 si A3.

### T3 — HARDWARE: bancul ABB pe fier (contributia C4)
Conditionat de poza placutei drive-urilor (seria 300): CONFIG Modbus ->
coast-down -> echilibru pe O pereche -> tele-impedanta Zenoh vs DDS PE FIER.
Drumul L1-L3 e deja scris in joint_emulator/README. Efort: ~15-20 h, dependent
de acces la stand. Plus testul 6a rehab (2-3 h) — inchide singurul pending
documentat al pachetului.

## 3. Ordinea recomandata si calendarul

| Saptamana | Activitate | Pista |
|---|---|---|
| pana la 18.06 | DOAR: PPT, articol, diagnostic RTL (30 s), submisie | — |
| 19-21.06 | diagnostic+fix lant plugin; campania M REPS=5 (decide M2); kickoff ecosistem (1-2 h, charter) | sar_plugins |
| 22.06-05.07 | `link_adaptive`: nucleul pur + teste (fara ROS) | T1 |
| 06-19.07 | `link_adaptive`: nodul + integrarea in roi; campania adaptiv-vs-static | T1 |
| paralel, 1 weekend | `field_kit`: kit + sesiunea de teren + profil calibrat | T2 |
| la sosirea placutei | bancul pe fier L1-L3 + testul 6a rehab | T3 |
| continuu | ecosistem educational: max 1-2 h/sapt (charter) | — |

Bugetul total ramane 5-10 h/sapt, IMPARTIT cu scrisul tezei — pistele nu
ruleaza simultan; T1 e coloana vertebrala, T2 intra intr-un weekend, T3 e
declansata de hardware, nu de calendar.

## 4. Maparea pe contributii si articole

| Pista | Contributie teza | Articol |
|---|---|---|
| (incheiat) benchmark 2 straturi N=5 | C1 | A1 — SSRR 2026 (18.06) |
| T1 link_adaptive | C3 (adaptive QoS/behavior) | A2 — SSRR/ICRA-W 2027 |
| T2 field_kit + campania M REPS=5 | C1 extins + C2 | A3 — canal spatial + real |
| T3 banc + telerehab | C4 | A4 — tele-impedanta pe fier |

## 5. Ce NU facem (lista de protectie)

1. Niciun proiect nou inainte de 18.06.
2. Nicio rescriere a pachetelor incheiate "ca sa fie mai frumoase".
3. Ecosistemul educational nu depaseste 1-2 h/sapt si nu intra in ferestre
   de sprint.
4. Nu se pornesc T1+T2+T3 simultan — o singura pista activa.

## 6. Datorii tehnice (audit 2026-06-25, de rezolvat inainte de submisie)

Audit read-only pe tot src/. Repo sanatos; urmatoarele sunt amanate constient (nu
blocheaza, dar de curatat inainte de orice articol):

- DUPLICARE de core-uri vendorizate: sar_core.py, swarm_core.py, world_config.py,
  netem_core.py sunt copii BYTE-IDENTICE in mesh_plugin / sar_swarm / sar_plugins /
  teleop_rover (incarcate via sys.path.insert in SIL-uri). Risc de divergenta in timp.
  Decizie arhitecturala: modul 'shared core' comun vs dual-track documentat.
- ASCII in COD incalcat sistematic (CLAUDE.md sec 3): sar_swarm (~20 .py), joint_emulator,
  servo_control, rehab_exo_description, gen_articol, curs_ros2. c1_benchmark / mesh_plugin /
  link_adaptive sunt curate. De transliterat batch inainte de submisie.
- servo_control (arhiva): package.xml are placeholder-uri (version 0.0.0, TODO description/
  license) vs setup.py cu valori reale; servo_teleop.py are non-ASCII. De aliniat.
- rehab_exo_description/CMakeLists.txt: blocuri install(DIRECTORY) si programe duplicate.
- mesh_plugin: doua implementari paralele (MeshTopology intern vs MeshGraph root) -- de
  marcat care e canonica / de consolidat (TODO existent in README).
