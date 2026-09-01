# c3_gateway -- gateway de selectie a transportului, condus de starea linkului

Contributia C3. Ideea: traficul de teleoperare nu trebuie sa ramana pe un transport ales
la compilare. Linkul isi schimba starea (rata de pierdere L si lungimea rafalelor B), iar
transportul potrivit se schimba odata cu ea. Gateway-ul estimeaza starea ONLINE si comuta
intre stive, folosind o politica derivata din masuratorile C2, nu din intuitie.

## Starea: nucleu + noduri + sonda, verificate pe loopback

Pachetul a trecut de mult de nucleul pur. Ce exista azi:

    c3_gateway/core/estimator.py   L si B online (EWMA), cu incertitudine si flag de stabilitate
    c3_gateway/core/policy.py      politica = TABELA pe (L, B, payload), incarcata din JSON
    c3_gateway/core/switching.py   masina de stare: histerezis asimetric + dwell-time + veto
    c3_gateway/core/canal_ge.py    canal Gilbert-Elliott determinist (pentru teste)
    c3_gateway/core/overhead.py    contabilitatea traficului de sonde
    c3_gateway/core/policy_table.json   DATE, generate din tabelele C2 (nu scrise de mana)

    c3_gateway/ipc/                canal IPC local: interfata unica, UDS SEQPACKET si shm ring
    c3_gateway/agent/transport_agent.py   un agent per RMW; IESE cu cod nenul daca RMW-ul
                                          confirmat nu e cel cerut
    c3_gateway/nodes/gateway_node.py      nodul gateway; decizie per topic, ZERO politica in nod
    c3_gateway/sonda/sonda_canal.py       sonda de canal transport-neutra (rol sursa / reflector)
    launch/c3_gateway.launch.py           gateway + cei doi agenti, fiecare pe RMW-ul lui

Interdictiile din `core/` (fara `rclpy`, `socket`, `rosidl`, `std_msgs`, `rmw`, `launch`) sunt
verificate mecanic de I4 din `test/test_c3_core.py` -- daca cineva strecoara un import
interzis, testul pica.

`entry_points` din `setup.py` este INCA gol, deci `ros2 run c3_gateway ...` NU merge:
procesele se pornesc prin `ros2 launch` sau direct cu `/usr/bin/python3 <cale>`. Comentariul
din `setup.py` mai spune "ETAPA 1: NICIUN nod" si a ramas in urma fata de arbore.

## Cum se verifica

Fara ROS si fara retea:

    python3 test/test_c3_core.py                        # suita nucleului
    python3 test/test_nodes_fara_politica.py            # nodurile nu contin politica
    python3 c3_gateway/core/estimator.py --selftest
    python3 c3_gateway/core/policy.py --selftest
    python3 c3_gateway/core/switching.py --selftest
    python3 c3_gateway/core/canal_ge.py --selftest
    python3 c3_gateway/core/overhead.py --selftest
    python3 c3_gateway/ipc/channel.py --selftest
    python3 c3_gateway/sonda/sonda_canal.py --selftest

Lantul intreg, local (porneste gateway + doi agenti + doua ecouri, dureaza cateva minute):

    python3 test/test_integrare_offline.py

Smoke pe loopback, cu launch-ul real:

    ros2 launch launch/c3_gateway.launch.py jurnal:=<dir> eticheta:=smoke reflector_local:=true

`reflector_local:=true` porneste reflectorul sondei pe aceeasi masina. Implicit e `false`,
si pe buna dreptate: pierderea masurata asa e cea de pe loopback, nu de pe link -- bun
pentru probe de mecanism, NU pentru campanie.

CERINTA DE LANSARE: routerul Zenoh trebuie sa RULEZE DEJA, altfel calea zenoh e moarta:

    ros2 run rmw_zenoh_cpp rmw_zenohd        # o data pe masina, INAINTE de launch

Nu e un defect al pachetului, e conventia ROS 2: descoperirea multicast e oprita implicit
(`enabled: false` in `DEFAULT_RMW_ZENOH_SESSION_CONFIG.json5`), deci fara router doua
sesiuni zenoh nu se gasesc. Aceeasi conventie e folosita de campania C1
(`c1_benchmark/run_campaign.py:138`) si de `test/test_integrare_offline.py:113`.
Masurat: fara router sonda de viabilitate pe zenoh primeste 0 din 213 raspunsuri; cu
router, 220 din 220. Detalii in `docs/SMOKE_TRAFIC_2026-09-02.md`.

    python3 test/test_dwell_mediana.py                  # mediana e valida pentru dwell

Toate testele din `test/` ies cu cod 0.

Lansarea se face prin `ros2 launch`; `ros2 run` nu e configurat (`entry_points` gol) --
intra in DoD-ul valului V1.

## De unde vin cifrele

- `FAPTE_C3.md` -- gate-ul de fapte: izolarea intre RMW-uri (cu controale pozitive),
  scope-ul lui `SetEnvironmentVariable` in launch, si costul masurat de re-stabilire.
  Dwell-time-ul din `switching.py` se deriveaza din cifra de acolo.
- `policy_table.json` -- generata de `tools/derive_policy.py` din tabelele canonice C2 din
  `~/DATE_CAMPANIE/ANALIZA_C2/`. Fiecare intrare poarta provenienta (fisierul sursa).
  Regenerare: `python3 tools/derive_policy.py`.
- `gate/` -- harness-ul de masura al gate-ului. Foloseste rclpy, deci NU e parte din pachetul
  instalat; e pastrat ca sa fie reproductibile cifrele din FAPTE_C3.md.

## Ce urmeaza

Etapa de noduri subtiri si launch cu stive paralele per RMW (Arhitectura B) este FACUTA si
verificata pe loopback. Ce ramane:

- masuratori pe HIL, pe doua masini, cu degradare pe link real (nu pe loopback);
- `entry_points` populat, daca se decide ca `ros2 run` merita in loc de `ros2 launch`;

Starea si portile acestor elemente se tin in registrul `~/PHD/BORD/DECIZII.md`.
