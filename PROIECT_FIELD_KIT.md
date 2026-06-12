# field_kit — masuratori pe legatura reala (ucide critica "doar simulare")

Design document, pista T2. Un weekend de lucru, reutilizeaza integral
infrastructura C1 si campania M.

## 1. Scopul

Trei livrabile pe hardware real: (1) tabelul C1 (RTT/pierdere) pe o legatura
WiFi reala intre doua masini; (2) profilul de canal CALIBRAT (exponent
log-distance + umbrire) din mers-pe-jos cu RSSI; (3) campania M re-rulata cu
profilul calibrat. Impreuna transforma sectiunea Limitations din "future
work" in "am facut".

## 2. Echipament (lista de cumparaturi/imprumut)

| Obiect | Rol | Observatii |
|---|---|---|
| a doua masina (Raspberry Pi 4/5 sau laptop vechi) | capatul B: ecou + RSSI | Ubuntu 24.04 + ROS 2 Jazzy |
| AP/hotspot dedicat | legatura sub control | NU retea de campus (client isolation, multicast filtrat) |
| powerbank + rucsac | mobilitatea capatului B | sesiune de ~1 h pe teren |
| ruleta / GPS telefon | distantele 10/20/40/80 m | precizia de metru ajunge |

## 3. Componentele software (mici, noi)

```
field_kit/
├── rssi_logger.py       # 1 Hz: `iw dev <if> link` -> CSV (t, rssi_dbm, bitrate)
├── fit_profile.py       # CSV rssi+pierdere vs distanta -> exponent n, sigma
│                        #   -> profil YAML compatibil radio_link_node
├── remote_echo.sh       # porneste bench_echo_server pe masina B (systemd opt.)
└── PROTOCOL_TEREN.md    # pasii sesiunii, cu bife
```

bench_client/bench_echo_server raman NEATINSE — ruleaza pe doua masini prin
simpla pornire pe host-uri diferite (descoperirea RMW face restul).

## 4. Protocolul sesiunii de teren (3-4 h)

1. Acasa: AP dedicat, ambele masini in retea, `ros2 multicast receive/send`
   intre ele (testul de descoperire DDS); routerul Zenoh pe masina A,
   sesiunea B configurata spre IP-ul lui.
2. Ancora: RTT pe legatura curata la 2 m, ambele RMW (referinta).
3. Mersul: la 10/20/40/80 m, cate 3 min per punct per RMW:
   rssi_logger pe B + latency_probe intre masini -> pierdere si RTT reale.
4. fit_profile -> `profiles/campus_real.yaml`.
5. Acasa: campania M cu profile:=campus_real (nicio alta schimbare).

## 5. Capcanele cunoscute (din PARAMETRI sectiunea 4)

Multicastul DDS pe WiFi: daca descoperirea nu merge, se trece pe unicast
initial peers (CYCLONEDDS_URI) — de documentat in PROTOCOL_TEREN. MAC-ul
WiFi transforma pierderea in latenta: ne asteptam ca "loss" masurat sa fie
mic si jitterul mare — asta E rezultatul, nu o eroare. Ceasuri: raman pe
RTT (ecou), zero sincronizare necesara.

## 6. Definitia succesului

Un tabel "real vs simulat" pe aceleasi metrici + un profil YAML calibrat
+ o fraza in articol(e): "the spatial channel model was calibrated against
field measurements". Efort total: 10-14 h.
