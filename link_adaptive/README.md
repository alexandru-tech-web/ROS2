# link_adaptive

Strat aplicativ adaptiv pentru ROS 2 (contributia C3): masoara starea legaturii
(RTT p95 + rata de pierdere) si comuta intre moduri de comportament (NOMINAL /
DEGRADED / CRITICAL) cu histerezis, expunand pe ROS o politica de date (rata,
fiabilitate, prag de prospetime, payload) pe care ceilalti noduri o consuma.
Logica de decizie e un nucleu pur, testabil fara ROS, conform metodologiei tezei.

## Scop

Premisa, citata in docstring-urile codului, vine din campania C1 (N=5): niciun
middleware nu domina -- DDS cumpara supravietuirea misiunii cu intarziere
uniforma, Zenoh cumpara prospetimea cu pierderi. Concluzia scrisa in cod: daca
niciunul nu domina, adapteaza-te. Pachetul alimenteaza explicit contributia C3
(asa cum apare in package.xml si in docstring-uri).

Cele trei moduri (din docstring-ul lui link_adaptive_core.py):
- NOMINAL  -- legatura buna: rata plina, livrare fiabila si completa.
- DEGRADED -- legatura medie: prioritizeaza controlul (best-effort + arunca
  vechi), telemetria ramane fiabila dar la rata redusa.
- CRITICAL -- legatura proasta: doar esential (heartbeat + comanda cea mai
  proaspata), arunca agresiv vechi, descarca telemetria neesentiala.

## Arhitectura

Pachetul urmeaza metodologia nucleu pur + _selftest -> nod ROS subtire -> SIL,
pe doua bucle:

- Decizie: nucleul link_adaptive_core.py (cu _selftest) DECIDE politica; nodul
  subtire link_adaptive_node.py masoara legatura si o PUBLICA pe ROS.
- Aplicare: nucleul policy_applier.py (cu _selftest) APLICA o politica pe un
  flux; nodul subtire policy_adapter_node.py sta in calea telemetriei si o
  aplica efectiv.
- SIL: sil_link_adaptive.py (adaptiv vs. alegeri statice de middleware) si
  sil_policy_loop.py (bucla end-to-end decizie + aplicare). Ambele fara ROS,
  deterministe.

## Fisiere

| Fisier | Rol |
|---|---|
| link_adaptive/link_adaptive_core.py | Nucleu pur (fara ROS): monitorul de legatura, controlerul cu histerezis si timp minim de stationare, decide modul + politica. Are `_selftest()`. |
| link_adaptive/link_adaptive_node.py | Nod ROS subtire: masoara RTT (din topic heartbeat) si rata de pierdere (din secventele telemetriei), ruleaza controlerul si publica politica + starea. |
| link_adaptive/policy_applier.py | Nucleu pur (fara ROS) care APLICA o politica pe un flux: limitarea ratei, aruncarea esantioanelor vechi, reducerea payload-ului. Semnaleaza schimbarea de fiabilitate. Are `_selftest()`. |
| link_adaptive/policy_adapter_node.py | Nod ROS subtire: sta in calea telemetriei (in_topic -> out_topic), aplica politica de pe /link_adaptive/policy si recreeaza publisher-ul cand QoS-ul (reliable/best-effort) se schimba. |
| link_adaptive/sil_link_adaptive.py | SIL (fara ROS): compara stratul adaptiv cu alegeri statice de middleware pe o cronologie de degradare; genereaza figura sil_link_adaptive.png. |
| link_adaptive/sil_policy_loop.py | SIL (fara ROS): bucla end-to-end decizie + aplicare; arata cum debitul si payload-ul telemetriei se string automat la inrautatirea legaturii. |
| launch/link_adaptive.launch.py | Porneste doar link_adaptive_node (masoara si publica politica). |
| launch/link_adaptive_loop.launch.py | Porneste bucla C3 completa: link_adaptive_node + policy_adapter_node. |

## Sintaxe de rulare

Build:

    cd ~/ros2_ws && colcon build --packages-select link_adaptive --symlink-install

Selftest offline (fara ROS) pe nucleele pure:

    python3 link_adaptive/link_adaptive_core.py
    python3 link_adaptive/policy_applier.py

SIL offline (fara ROS):

    python3 link_adaptive/sil_link_adaptive.py
    python3 link_adaptive/sil_policy_loop.py

Entry points reale (din setup.py):

    ros2 run link_adaptive link_adaptive_node
    ros2 run link_adaptive policy_adapter_node
    ros2 run link_adaptive sil_link_adaptive
    ros2 run link_adaptive sil_policy_loop

Exemplu cu parametri (din docstring-ul lui link_adaptive_node.py):

    ros2 run link_adaptive link_adaptive_node --ros-args \
        -p rtt_topic:=/operator/heartbeat -p telemetry_topic:=/sar/telemetry

Atasare a adaptorului in calea telemetriei (din docstring-ul lui
policy_adapter_node.py):

    drone_node ... -r /sar/telemetry:=/sar/telemetry/raw
    ros2 run link_adaptive policy_adapter_node --ros-args \
        -p in_topic:=/sar/telemetry/raw -p out_topic:=/sar/telemetry

Launch:

    ros2 launch link_adaptive link_adaptive.launch.py
    ros2 launch link_adaptive link_adaptive.launch.py \
        rtt_topic:=/operator/heartbeat telemetry_topic:=/sar/telemetry

    ros2 launch link_adaptive link_adaptive_loop.launch.py
    ros2 launch link_adaptive link_adaptive_loop.launch.py \
        rtt_topic:=/operator/heartbeat in_topic:=/sar/telemetry/raw out_topic:=/sar/telemetry

Nota: scripturile SIL nu folosesc argparse (niciun add_argument in pachet), deci
nu accepta argumente CLI.

## Parametri si topicuri

Mesajele sunt JSON pe std_msgs/String, ca tot depozitul.

link_adaptive_node (parametri din declare_parameter):

| Parametru | Implicit |
|---|---|
| rtt_topic | /operator/heartbeat |
| telemetry_topic | /sar/telemetry |
| decide_hz | 5.0 |
| min_dwell_s | 2.0 |
| rtt_window | 50 |
| seq_window | 100 |

Topicuri link_adaptive_node:
- publica /link_adaptive/policy -- politica curenta. Forma JSON (din
  Policy.as_dict): `{mode, rate_hz, reliable, max_staleness_ms, payload}`.
- publica /link_adaptive/state -- `{rtt_p95_ms, loss, max_burst, mode, transitions}`.
- asculta rtt_topic -- citeste campul `rtt_ms` din JSON.
- asculta telemetry_topic -- citeste campul `seq` din JSON (pentru rata de pierdere).

policy_adapter_node (parametri din declare_parameter):

| Parametru | Implicit |
|---|---|
| in_topic | /sar/telemetry/raw |
| out_topic | /sar/telemetry |
| policy_topic | /link_adaptive/policy |
| stamp_field | "" (gol = aruncarea pe vechime dezactivata) |
| depth | 10 |
| reduced_fields | ["id", "x", "y", "seq", "t", "soc", "phase"] |
| critical_fields | ["id", "x", "y", "seq", "t"] |

Topicuri policy_adapter_node:
- publica out_topic -- fluxul de telemetrie dupa aplicarea politicii (QoS
  reliable/best-effort recreat dupa politica).
- asculta policy_topic -- politica (JSON), QoS reliable.
- asculta in_topic -- telemetria bruta (JSON), QoS best-effort.

Valorile de politica pe mod (din POLICIES in link_adaptive_core.py):
- NOMINAL:  rate_hz=20.0, reliable=True,  max_staleness_ms=1000, payload=FULL.
- DEGRADED: rate_hz=10.0, reliable=False, max_staleness_ms=300,  payload=REDUCED.
- CRITICAL: rate_hz=2.0,  reliable=False, max_staleness_ms=100,  payload=CRITICAL.
