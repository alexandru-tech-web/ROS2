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
