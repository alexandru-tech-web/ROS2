# Nota metodologica C1 -- benchmark transport rmw_zenoh vs rmw_cyclonedds

Scop: documenteaza ce masoara benchmark-ul de transport C1, ce s-a verificat,
si concluzia de validitate. Serveste ca referinta de reproductibilitate in
pachetul c1_benchmark.

## 1. Montajul

- Un singur host (laptop Ubuntu), comunicatie pe interfata loopback `lo`.
- Degradare de retea emulata cu `tc netem` pe `lo` (pierdere Bernoulli
  independenta: loss_5..loss_30; latenta: lat200_jit50, lat200_l15).
- bench_client <-> bench_echo_server (noduri ROS 2), RTT masurat per mesaj,
  50 Hz, payload 64 / 4096 / 65536 B.
- Doua middleware: rmw_cyclonedds_cpp si rmw_zenoh_cpp, peer-to-peer (fara broker).

## 2. Ce s-a verificat (investigatie de integritate)

Punct de plecare: o campanie initiala arata Zenoh aparent imun la pierdere mica
(loss_15: p95 ~2 ms, 0% pierdere) -- fizic implauzibil pentru un transport care
ar trebui sa traverseze 15% pierdere. Verificari directe:

- **Shared-memory NU e cauza.** In rmw_zenoh pe ROS 2 Jazzy, SHM e dezactivat
  implicit (config DEFAULT_RMW_ZENOH_SESSION_CONFIG.json5, "enabled: false",
  nota "disabled by default until fully tested"). Confirmat in fisier.
- **Traficul Zenoh trece prin `lo`.** `ifstat` arata ~400 KB/s pe `lo` in timpul
  rularilor (rata asteptata 50 Hz x 4096 B x 2 sensuri), deci netem se aplica.
- **Router-ul Zenoh e instabil sub pierdere.** `rmw_zenohd` a crapat repetat in
  timpul conditiilor cu pierdere ("routerul Zenoh a murit"); rularile au cazut
  pe peer-to-peer.
- **Cu mediu CURAT (P2P, fara stare reziduala), Zenoh e lovit consistent.**
  Trei rulari independente loss_15: p95 499 / 307 / 711 ms, pierdere ~0-2%.
  Niciuna nu reproduce imunitatea (2 ms) din campania initiala.

Concluzie partiala: imunitatea Zenoh din campania initiala era un **artefact de
stare reziduala de mediu** (router/proces ramas dintr-o sesiune anterioara,
conditii de cursa la pornire), NU comportamentul real al transportului. Valorile
respective sunt nereproductibile si nu trebuie folosite.

## 3. Ce ramane solid

- **CycloneDDS**: reproductibil, monoton, fizic coerent. Pierderea masurata
  round-trip se incadreaza sub predictia 1-(1-p)^2 (recuperare prin retransmisie),
  iar conditiile de latenta dau RTT ~2x latenta one-way, ca asteptat.
- **Conditiile de latenta** (lat200_*) si **fizica round-trip**: corecte pentru
  ambele middleware.

## 4. Concluzia de validitate

Benchmark-ul pe loopback (un singur host) este **fiabil pentru CycloneDDS**, dar
**nu produce rezultate reproductibile pentru Zenoh** -- sensibil la starea de
mediu si la instabilitatea router-ului sub pierdere. Prin urmare:

> Comparatia echitabila Zenoh vs CycloneDDS sub degradare de retea NU poate fi
> stabilita fiabil pe un singur host cu netem pe `lo`. Comparatia autoritara
> necesita DOUA masini fizice (hardware-in-the-loop) cu netem pe legatura reala.

Campania curata P2P cu N=10 (daca exista) este o **referinta de loopback** cu
aceasta limitare documentata; rezultatul de comparatie se ia de pe HIL.

## 5. Protocol de reproductibilitate (obligatoriu)

Inainte de fiecare rulare:
- `pkill -f rmw_zenohd; rm -f /dev/shm/*zenoh* /dev/shm/fastrtps_*` (mediu curat).
- Rulare peer-to-peer, FARA router (ca CycloneDDS). Router-ul crapa sub pierdere.
- SHM ramane off (implicit pe Jazzy) -- nimic de configurat.
- Repetitiile se lasa in seama `run_campaign.py --reps N` (scrie rep1..repN);
  NU se face bucla externa cu --reps 1 (suprascrie rep1 -> N=1).
- Conditiile *_burst se EXCLUD (netem corelat nu pastreaza media; invalid).

## 6. De citat vs de obtinut din HIL

- De citat acum: comportamentul CycloneDDS sub pierdere/latenta; fizica round-trip.
- De obtinut din HIL (doua masini): comparatia Zenoh vs DDS pe legatura reala.

## 7. Rezultat N=10 (referinta loopback, campanie curata P2P)

Campanie echitabila: ambele RMW peer-to-peer, mediu curat inainte de fiecare,
N=10 (9 pentru zenoh/loss_30), payload 4096 B. p95 [ms], CV = std/medie:

| RMW        | conditie     | N  | p95 medie | CI95 +/- | CV    | min-max        | pierdere |
|------------|--------------|----|-----------|----------|-------|----------------|----------|
| CycloneDDS | loss_15      | 10 | 1019      | 77       | 10%   | 796-1173       | 1.4%     |
| CycloneDDS | loss_20      | 10 | 1746      | 73       | 6%    | 1573-1889      | 7.7%     |
| CycloneDDS | loss_25      | 10 | 2145      | 43       | 3%    | 2083-2302      | 26.5%    |
| CycloneDDS | loss_30      | 10 | 2317      | 39       | 2%    | 2243-2403      | 41.0%    |
| CycloneDDS | lat200_l15   | 10 | 2548      | 23       | 1%    | 2513-2616      | 36.0%    |
| Zenoh      | loss_15      | 10 | 560       | 91       | 23%   | 317-726        | 8.5%     |
| Zenoh      | loss_20      | 10 | 972       | 381      | 55%   | 563-2225       | 16.9%    |
| Zenoh      | loss_25      | 10 | 5392      | 3867     | 100%  | 902-18485      | 34.1%    |
| Zenoh      | loss_30      | 9  | 8709      | 4216     | 63%   | 1713-15687     | 57.8%    |
| Zenoh      | lat200_l15   | 10 | 3893      | 1354     | 49%   | 1955-8290      | 20.8%    |

Interpretare:
- **CycloneDDS**: latenta de coada mare dar PREDICTIBILA sub degradare (CV < 20%,
  CI95 strans). Scaleaza monoton si neted cu pierderea.
- **Zenoh**: latenta de coada mare SI IMPREVIZIBILA (CV 50-100%; la loss_25,
  variatie de un ordin de marime, 0.9-18.5 s intre rulari identice).
  Imprevizibilitatea se reproduce (vazuta si pe N=1, si pe N=10) -> caracteristica
  reala pe acest montaj, nu zgomot.

Concluzie (loopback): pentru teleoperare in timp real, PREDICTIBILITATEA conteaza.
Un transport cu p95 intre 0.9 s si 18 s la aceeasi conditie este nefolosibil
pentru control, indiferent de medie. Pe acest criteriu CycloneDDS e net preferabil.

Atentie / limite:
- CV-ul mare Zenoh face mediile punctuale ne-semnificative; se raporteaza
  variabilitatea (interval, CV), nu o singura cifra.
- Rezultat de LOOPBACK. Confirmarea pe legatura fizica (HIL, doua masini) este
  pasul urmator si autoritar pentru comparatia Zenoh vs DDS.

## 8. Limitari -- discovery Zenoh pe HIL fara multicast

Montaj: rmw_zenoh_cpp 0.2.9, ROS 2 Jazzy. M1=192.168.100.14 (WiFi, wlp4s0),
M2=192.168.100.17 (eth0, cablu), ROS_DOMAIN_ID=7. Reteaua (ONT HG8121H) NU permite multicast
intre WiFi si Ethernet. CycloneDDS HIL e complet (arhivat in ~/c1_archive/hil_cyclonedds_*).
Zenoh router-less inca NU propaga declaratiile de topicuri intre masini, desi TCP 7447 se conecteaza.

### Ce s-a incercat (toate au esuat pentru discovery cross-masina)
- scouting multicast: blocat de retea.
- rmw_zenohd router pe M1: peers nu-l descopera (tot prin multicast).
- endpoint-uri TCP explicite (connect = IP-ul celuilalt, listen = IP propriu:7447, multicast off,
  gossip.target.peer=["router","peer"]): TCP OPEN (nc confirma), DAR `ros2 topic list` nu vede
  topicurile peer-ului. Declaratiile nu se propaga peste link-ul TCP.

### Cauza-radacina din config-ul default (rmw_zenoh_cpp 0.2.9)
DEFAULT_RMW_ZENOH_SESSION_CONFIG.json5: `scouting.gossip.target.peer = ["router"]` (un peer trimite
gossip DOAR catre routere) + `routing.peer.mode = "peer_to_peer"` (presupune mesh complet sau un
router care face "failover brokering"). Adica rmw_zenoh e PROIECTAT in jurul unui router; peers se
descopera PRIN router. Doc-urile confirma: router-less cere fie un router, fie endpoint-uri connect
explicite (cazul nostru).

### Diagnostic pe loopback (dovada, nu speculatie)
Experiment local: doi peers pe 127.0.0.1 (porturi 7601/7602), router-less, multicast OFF, endpoint-uri
connect explicite, configuri minimale via ZENOH_SESSION_CONFIG_URI. Rezultat: listener-ul a primit
12/12 mesaje in AMBELE moduri de rutare -- `linkstate` SI `peer_to_peer`. Avertismentul "Unable to
connect to a Zenoh router ... peers will not discover" apare in ambele, dar datele CURG oricum -> e
BENIGN cand exista endpoint-uri connect explicite.

CONCLUZIE: mecanismul router-less (endpoint-uri explicite + multicast off) FUNCTIONEAZA pe loopback,
indiferent de `routing.peer.mode`. Deci modul de rutare NU este cauza esecului cross-masina. Cauza e
specifica CAII DE RETEA WiFi<->Ethernet (reachability / binding / sesiune), nu config-ului de rutare.

### Urmatorul pas de diagnostic (cross-masina; nc OPEN != sesiune Zenoh stabilita)
1. Reachability BIDIRECTIONALA, nu doar M1->M2: ruleaza `nc -zv 192.168.100.14 7447` DE PE M2. Daca
   sensul invers esueaza -> izolare de client pe AP / asimetrie WiFi<->Ethernet = suspectul principal.
2. Listen pe TOATE interfetele pe ambele: `listen.endpoints: ["tcp/0.0.0.0:7447"]` (nu pe IP fix sau localhost).
3. Confirma SESIUNEA (nu doar TCP): porneste nodul cu `RUST_LOG=zenoh=debug` si cauta o sesiune noua
   acceptata, nu doar conexiunea TCP.
4. Cum face CycloneDDS (care MERGE pe aceasta retea fara multicast): verifica `CYCLONEDDS_URI` pentru o
   lista de Peers unicast. Daca DDS foloseste discovery unicast configurat, reteaua PERMITE unicast-ul
   necesar -> esecul Zenoh e de config/binding, nu de retea. Documenteaza lista de peers DDS ca referinta.

### Bug reparat (in acest commit)
`hil_preflight.sh` rula `pkill rmw_zenohd` la curatare -> isi omora propriul router cand testai cu
router pornit. Adaugat flag `--keep-router` care sare pkill-ul (pastreaza /dev/shm curat oricum).

### Stare
Discovery Zenoh cross-masina pe aceasta retea: NEREZOLVAT. Regula de aur ramane: NU se ruleaza
masuratori Zenoh HIL pana cand `ros2 topic list` pe o masina nu vede topicurile peer-ului. CycloneDDS
HIL ramane NEATINS (complet, arhivat). Cifrele Zenoh raman SIL/loopback pana la rezolvarea discovery-ului.
