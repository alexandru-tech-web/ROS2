# link_adaptive

Strat aplicativ adaptiv la starea legaturii pentru ROS 2 (contributia C3 din
teza). Masoara starea legaturii (RTT p95 + rata de pierdere) si comuta intre trei
moduri de comportament -- NOMINAL / DEGRADED / CRITICAL -- cu histerezis, ca
raspuns la concluzia campaniei C1: niciun middleware nu domina, deci adapteaza-te.

Stare: nucleu pur testat (selftest 22/22) + nod ROS 2 + SIL. Cifrele din SIL sunt
deterministe (N=1) si ilustreaza strategia; se inlocuiesc cu campania reala
adaptiv-vs-static (N=5) inainte de publicare (tinta A2).

## 1. De ce

Campania C1 (N=5, doua straturi) a aratat doua filozofii de fiabilitate, fara
castigator universal:
- DDS (fiabil) cumpara supravietuirea misiunii cu intarziere uniforma -- la
  pierdere mare un zid p95 de ~2.3 s; livreaza tot, dar tarziu.
- Zenoh (Age-of-Information) cumpara prospetimea cu pierderi -- mediana rapida,
  dar arunca ~35% la 30% pierdere.
- CDF-urile se incruciseaza (percentila ~57-60): nicio dominanta de ordinul intai.

Daca alegerea statica de middleware pune in opozitie prospetimea controlului si
completitudinea telemetriei, raspunsul e un strat care isi schimba comportamentul
dupa starea masurata a legaturii si obtine ambele.

## 2. Arhitectura

Metodologia depozitului -- nucleu pur testabil, apoi nod subtire, apoi SIL:

    link_adaptive/
      link_adaptive/
        link_adaptive_core.py    nucleu pur (fara ROS): LinkMonitor + AdaptiveController + POLICIES
        link_adaptive_node.py    nod subtire: masoara, decide, publica politica
        sil_link_adaptive.py     SIL: adaptiv vs static (fresh/complete), figura
      launch/link_adaptive.launch.py
      docs/sil_link_adaptive.png
      package.xml  setup.py  setup.cfg  resource/link_adaptive

- **LinkMonitor**: RTT p95 dintr-o fereastra glisanta de masuratori dus-intors;
  rata de pierdere din golurile numerelor de secventa.
- **AdaptiveController**: masina de stari cu histerezis (praguri de intrare/iesire
  diferite) si timp minim de stationare; coborare gradata din CRITICAL.
- **POLICIES**: pentru fiecare mod, politica de date (rata, fiabilitate, prag de
  prospetime, payload). Nucleul nu trimite nimic -- decide POLITICA.

## 3. Moduri si politici

    Mod        Cand                        rata   fiabilitate   prospetime  payload
    NOMINAL    legatura buna               20 Hz  fiabil        1000 ms     FULL
    DEGRADED   legatura medie              10 Hz  best-effort   300 ms      REDUCED
    CRITICAL   legatura proasta             2 Hz  best-effort   100 ms      CRITICAL

Per flux (consumatorii aplica politica pe fluxul lor):
- Control: mereu proaspat (best-effort, arunca vechi, actioneaza pe ultima
  comanda) -- eviti zidul de retransmisii; prospetimea bate completitudinea.
- Telemetrie: fiabila cand retransmisiile sunt ieftine (NOMINAL), best-effort
  cand fiabilitatea devine inutila (pierdere/latenta mare, unde si DDS arunca mult).

## 4. Histerezis (anti-palpaire)

    NOMINAL  -> DEGRADED : RTT p95 > 150 ms SAU pierdere > 5%
    ...      -> CRITICAL : RTT p95 > 800 ms SAU pierdere > 20%
    DEGRADED -> NOMINAL  : RTT p95 <= 100 ms SI pierdere <= 2%
    CRITICAL -> DEGRADED : RTT p95 <= 500 ms SI pierdere <= 12%
    stationare minima    : 2 s

Banda dintre pragul de iesire si cel de intrare absoarbe zgomotul. Maparea pe C1
(verificata in selftest): ideal/loss_5 -> NOMINAL; loss_15 / lat200_* -> DEGRADED;
loss_30 -> CRITICAL.

## 5. Topicuri (JSON pe std_msgs/String)

    publica:  /link_adaptive/policy   {mode, rate_hz, reliable, max_staleness_ms, payload}
              /link_adaptive/state     {rtt_p95_ms, loss, mode, transitions}
    asculta:  <rtt_topic>              {rtt_ms}     sursa de RTT (ex. heartbeat)
              <telemetry_topic>        {seq, ...}   pentru rata de pierdere

## 6. Build si rulare

    # verificare offline (fara ROS)
    cd link_adaptive && python3 link_adaptive_core.py        # 22/22
    python3 sil_link_adaptive.py                              # bilant + docs/sil_link_adaptive.png

    # build in workspace
    cd ~/ros2_ws && colcon build --packages-select link_adaptive --symlink-install
    source install/setup.bash
    ros2 pkg executables link_adaptive

    # ruleaza stratul (in paralel cu roiul)
    ros2 launch link_adaptive link_adaptive.launch.py \
        rtt_topic:=/operator/heartbeat telemetry_topic:=/sar/telemetry
    ros2 topic echo /link_adaptive/policy
    ros2 run link_adaptive sil_link_adaptive

Nota: modificarile la entry-points / setup.py necesita rebuild (wrapper-ele se
genereaza la build). Daca apar erori RTPS_TRANSPORT_SHM: rm -f /dev/shm/fastrtps_*.

## 7. Rezultate (SIL determinist, N=1)

Pe o cronologie C1 (legatura se degradeaza si isi revine), trei strategii pe doua
axe care conteaza in teleoperare:

    strategie         staleness control          completitudine telemetrie
                      (mediu / cel mai rau)       (medie / cea mai rea)
    STATIC-COMPLETE   430 ms / 1262 ms            91% / 61%
    STATIC-FRESH       30 ms /  100 ms            92% / 65%
    ADAPTIVE           30 ms /  100 ms            93% / 65%

ADAPTIVE pastreaza controlul ~14x mai proaspat decat STATIC-COMPLETE, recuperand
in acelasi timp telemetria pe care STATIC-FRESH o pierde cand legatura e buna.
Fiecare alegere statica pierde pe cate o axa; adaptivul prinde coltul bun.
Figura: docs/sil_link_adaptive.png.

## 8. Integrare

`link_adaptive_node` ruleaza in paralel si publica politica; consumatorii
(`drone_node`, `gcs_node`, bridge-ul de telemetrie) citesc /link_adaptive/policy
si ajusteaza rata, QoS-ul (reliable vs best-effort), aruncarea esantioanelor
vechi si nivelul de payload. Stratul nu reconfigureaza el QoS-ul altora -- expune
DECIZIA, ca un controler curat (la fel ca mesh_node cu rutele).

Se combina cu `mesh_plugin`: mesh decide DACA exista cale la GCS, link_adaptive
decide CUM se comporta fluxul pe acea cale.

## 9. Limite

- Cifrele SIL sunt un model determinist ancorat in mediile C1; ilustreaza
  strategia, nu sunt date empirice noi. De inlocuit cu campania reala N=5.
- Modelul de staleness/completitudine e un proxy transparent (latenta de baza /
  zid p95 / pierdere livrata).
- Pragurile sunt setate din C1; transferul la o legatura reala (field_kit) cere
  verificare si eventual recalibrare pe profil de canal real.
- Costul real in CRITICAL e rata redusa de telemetrie (rezolutie temporala mai
  mica a hartii), nu completitudine.

## 10. Tinta de publicare

A2 -- SSRR / ICRA-W 2027 (contributia C3, adaptive QoS / behavior). Design
complet: PROIECT_LINK_ADAPTIVE.md.

## Licenta

MIT.
