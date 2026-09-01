# Smoke cu trafic: livreaza AMBELE cai?

Masurat 2026-09-01 (numele fisierului vine din planul zilei). Laptop, loopback,
`ROS_DOMAIN_ID` 76 si 77. Montaj: `launch/c3_gateway.launch.py` cu
`reflector_local:=true`, plus un `test/echo_node.py` per transport si
`test/app_pub.py` (50 Hz, 4096 B). Runner: `scratchpad/smoke_trafic.sh`.

## Intrebarea

Smoke-ul de ieri a dat `n_app 0` si un `WARN: Unable to connect to a Zenoh router`.
Livreaza ambele cai trafic real prin lantul lansat, sau doar cyclonedds?

## Ce am gasit inainte de a rula

1. C1 pornea routerul EXPLICIT in campanie. `c1_benchmark/run_campaign.py:138`:

       ["ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"]

   cu `"ZENOH_ROUTER_CHECK_ATTEMPTS": "10"` la linia 118.

2. Descoperirea multicast e OPRITA implicit. In
   `/opt/ros/jazzy/share/rmw_zenoh_cpp/config/DEFAULT_RMW_ZENOH_SESSION_CONFIG.json5`:

       multicast: {
         /// Whether multicast scouting is enabled or not
         ///
         /// ROS setting: disable multicast discovery by default
         enabled: false,

   Fara router si fara multicast, doua sesiuni zenoh nu au cum sa se gaseasca.

3. Testul de integrare al C3 porneste deja routerul, la
   `test/test_integrare_offline.py:113`. Doar `launch/c3_gateway.launch.py` nu.

## Rezultat

| | FARA `rmw_zenohd` | CU `rmw_zenohd` |
|---|---|---|
| `cyclonedds A` (aplicatie) | 1751 / 1751 | 1751 / 1751 |
| `cyclonedds P` (viabilitate) | 218 / 218 | 220 / 220 |
| `zenoh P` (viabilitate) | **213 / 0** | **220 / 220** |
| `primite_sonda` (rezumat) | 218 | 440 |
| rapoarte de canal | 83 | 84 |
| comutari | 0 | 0 |
| erori / traceback | 0 | 0 |
| `WARN Unable to connect to a Zenoh router` | 2 | 0 |

Aplicatia curge pe calea ACTIVA (cyclonedds), deci `cyclonedds A` nu distinge
cele doua cazuri. Calea zenoh se vede prin sonda de viabilitate, si acolo
diferenta e totala: **0 raspunsuri fara router, 100% cu router.**

## Verdict

VERDE, cu o conditie de lansare. Nu este un defect: este CONVENTIA C1.
`rmw_zenoh_cpp` cere un router pornit, fiindca descoperirea multicast e oprita
implicit in ROS 2. Aceeasi conventie e respectata de campania C1 si de testul de
integrare C3.

Fara router, calea zenoh e moarta si comutatorul nu ar avea unde sa comute --
iar rularea ar arata valida (livrare 100% pe cyclonedds) fara sa fie. Exact
genul de rezultat pe care vetoul de cale moarta il previne.

## Ce NU am schimbat, si de ce

Nu am adaugat `rmw_zenohd` in `c3_gateway.launch.py`. Motiv: routerul este un
daemon de gazda, nu un proces al experimentului. Pe HIL se porneste O DATA pe
masina, cu configul ei (`router_pi.json5` / `router_m1.json5` din C1), inaintea
oricarei rulari. Daca l-ar porni launch-ul, fiecare rulare ar ridica un router
nou, iar campania ar masura si costul pornirii lui.

Cerinta e scrisa in `README.md`, la sectiunea de smoke. Daca se decide totusi
adaugarea in launch, ea trebuie sa fie conditionata (`router_local:=true`), la
fel ca `reflector_local`, si cu acelasi avertisment.
