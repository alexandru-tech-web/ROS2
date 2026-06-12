# Dictionarul parametrilor si transferul in mediul real

Documentul de referinta al celor doua campanii experimentale: ce inseamna
fiecare parametru, ce s-a intamplat in simulare si ce efect ar avea — sau ce
s-ar schimba — intr-un test pe mediu real. Sectiunile marcate
[DE COMPLETAT] se umplu cu cifrele din `mission_summary.csv` si din campania
completa de noapte.

---

## 1. Harta campaniilor

| | Campania C1 (transport+misiune) | Campania M (misiune spatiala) |
|---|---|---|
| Intrebarea | ce face FIRUL sub degradare uniforma | ce simte OPERATIUNEA cand canalul depinde de distanta si teren |
| Degradarea | FIZICA: tc netem pe interfata (identica pentru toti) | SIMULATA SPATIAL: radio_link_node (log-distance + profil) |
| Unitatea | 2 RMW x 6 conditii x N rep x 2 straturi | 2 RMW x 2 profiluri x N rep |
| Durata | ~40 min (N=2) / ~3–4 h (N=5, noaptea) | ~45 min (N=2) / ~110 min (N=5) |
| Iesirea | campaign_summary.csv + fig_transport/mission/cdf | mission_summary.csv + 4 figuri de misiune |
| Instrument | `c1_benchmark/run_campaign.py` | `sar_plugins/tools/mission_experiment.sh` |

Regula comuna: o singura campanie pe masina la un moment dat; preflight inainte;
datele brute in `~/c1_archive/`, in git doar sumarele si figurile.

## 2. Campania C1 — parametrii si semnificatia lor

### 2.1 Parametrii orchestratorului (`run_campaign.py`)

| Parametru | Implicit | In simulare | Daca il cresti / scazi |
|---|---|---|---|
| `--iface` | `lo` | interfata pe care tc aplica degradarea; `lo` = ambele capete pe aceeasi masina (ceas comun, zero zgomot extern) | interfata reala (`wlp4s0`) = pasul spre testul pe doua masini |
| `--reps` | 5 | repetitii per celula; N=2 a fost repetitia generala | N mare = bare de eroare mici; N=5 e minimul pentru a desparti semnalul de zgomotul de ~8% observat |
| `--duration` | 20 s | fereastra unei rulari de transport PER sarcina utila | mai lung = percentile p99 mai stabile, campanie mai lunga |
| `--mission-timeout` | 170 s | plafonul unei misiuni (cenzurare la dreapta) | prea mic = misiuni taiate artificial; prea mare = campanie lunga |
| `PAYLOADS` | 64 / 4096 / 65536 B | trei clase de trafic: COMANDA (64 B, ex. rth), TELEMETRIE (4 KB, poza+stare), HARTA/IMAGINE (64 KB, fragment de harta sau cadru comprimat) | clasa mare streseaza fragmentarea UDP — acolo se vad cel mai tare diferentele RMW |

### 2.2 Conditiile de retea si corespondentul lor real

| Conditie | tc netem | Corespondent in mediul real |
|---|---|---|
| `ideal` | — | laborator, cablu, aceeasi masa |
| `loss_5` | `loss 5%` | WiFi bun la distanta medie; legatura LTE stabila |
| `loss_15` | `loss 15%` | NLOS urban; WiFi la marginea acoperirii; interferenta moderata |
| `loss_30` | `loss 30%` | marginea razei radio; subsoluri/moloz; mediul de dezastru tipic |
| `lat200_jit50` | `delay 200ms 50ms` | releu satelit/LTE aglomerat; VPN peste retele incarcate |
| `lat200_l15` | `delay 200ms loss 15%` | LEGATURA DE DEZASTRU REALISTA: releu departat + interferenta — conditia-cheie a articolului |

Ce modeleaza si ce NU modeleaza tc netem (amenintari la validitate, de spus
cinstit in articol):
- pierderea netem e Bernoulli INDEPENDENTA per pachet; radio-ul real pierde in
  RAFALE (fading corelat). Rafalele lovesc mai tare mecanismele de recuperare
  DDS — rezultatele noastre sunt deci mai degraba OPTIMISTE pentru DDS.
- pe WiFi real, stratul MAC retransmite singur: pierderea „dispare" si reapare
  ca LATENTA si JITTER. Conditiile noastre cu pierdere modeleaza mai bine
  legaturile fara ARQ (radiouri de telemetrie pe distanta lunga, UDP brut).
- `lo` elimina sincronizarea ceasurilor (masuram RTT pe ecou) — corect
  metodologic, dar fara efectele plăcii de retea reale.

### 2.3 Ce s-a intamplat in simulare (N=2, cifrele actuale)

1. Degradare usoara (loss_5): Zenoh tine coada p95 la 25 ms vs 146 ms DDS —
   filozofia „livreaza proaspat" plateste imediat.
2. Pierdere medie (loss_15): compromisul pe fata — DDS recupereaza aproape tot
   (1.1% pierdere) cu pretul cozii de ~1 s; Zenoh livreaza in ~0.76 s dar
   accepta 25% esantioane pierdute.
3. Conditia de dezastru (lat200_l15): la coada EGALA (~2.5 s), DDS pierde
   45.6%, Zenoh 14.9% — separarea decisiva, fraza de titlu.
4. Compresia: p95 se degradeaza de pana la ~1800–2200x; timpul de misiune cu
   cel mult 14% — autonomia absoarbe; un singur esec (Zenoh, loss_30,
   acoperire stagnata la 0.90).
5. Costul de pornire Zenoh (~14 s si in ideal) apartine lansatorului
   (descoperire/sesiune prin router), nu planului de date.

[DE COMPLETAT dupa campania de noapte N=5: aceleasi cinci puncte cu mediile si
abaterile noi; tabelul din articol se regenereaza automat din CSV.]

## 3. Campania M — parametrii si semnificatia lor

### 3.1 Variabilele scriptului (`mission_experiment.sh`)

| Variabila | Implicit | In simulare | Corespondent real |
|---|---|---|---|
| `RMWS` | cyclonedds zenoh | middleware-ul sub test; routerul Zenoh pornit automat per bloc | identic pe fier — doar exporti RMW_IMPLEMENTATION |
| `PROFILES` | open_field urban_rubble | profilul canalului radio (vezi 3.2) | tipul de teren al operatiunii |
| `REPS` | 2 | repetitii per celula (seed incrementat) | N=3–5 pentru statistica de articol |
| `DUR` | 300 s | fereastra unei rulari (plafon) | durata unui sector de cautare |
| `SEED0` | 42 | determinism: victime + umbrirea canalului reproductibile | n/a (realitatea nu are seed — de aceea repetam) |
| `BATT_WH` | 8 | capacitatea bateriei SCALATA ca failsafe-ul sa fie observabil in 5 min: la P_hover ~120 W, 8 Wh = ~4 min de zbor | drona reala: 50–100 Wh la 150–300 W = 15–25 min; raportul timp-de-zbor / durata-sector e pastrat |
| `OUT` | ~/mission_results | arborele rezultatelor | — |

### 3.2 Modelul de canal (`radio_link_node`, profilurile)

Model log-distance cu umbrire: puterea recepionata scade cu
`10·n·log10(d)` + o componenta aleatoare (shadowing); din SNR rezulta
latenta/jitter/pierdere per drona, recalculate continuu din DISTANTA fata de
GCS. `open_field` = exponent mic, praguri blande (camp deschis, linie de
vedere); `urban_rubble` = atenuare agresiva + umbrire mare (moloz, beton).
In real: profilul se CALIBREAZA — masori RSSI/pierdere vs. distanta cu
hardware-ul tau si potrivesti exponentul si pragurile; restul campaniei ramane
identic.

### 3.3 Roiul si etajul de misiune

| Parametru | Valoare | Semnificatie / efect real |
|---|---|---|
| drone | 4, pozitii initiale fixe (3.5/6.5 m) | marimea echipei; in real: numarul de UAV-uri pe sector |
| `use_gazebo` | false | cinematica interna (fara fizica) — vant, GPS, dinamica lipsesc; timpii absoluti se schimba in real, ORDINEA efectelor RMW e ipoteza care se pastreaza |
| `sensor_r` | 6.0 m | raza discului de detectie; in real: amprenta camerei termice la altitudinea de zbor |
| aria de acoperire | −5..65 m (70x70 m) | sectorul de cautare; timpii scaleaza ~ arie/(viteza x latime de baleiaj) |
| `n_victims` (plugin) | 6 | victimele etajului de misiune (evenimentele calatoresc prin link); lumea roiului are separat 5 victime — completarea misiunii se judeca pe cele 5 |
| failsafe baterie | rth la prag (static 30% + dinamic dupa distanta de casa) | identic conceptual cu RTL-ul autopilotelor reale (ArduPilot/PX4) |

### 3.4 Metricile (definitii exacte)

| Metrica | Definitie | De ce conteaza |
|---|---|---|
| T90 | primul t cu acoperire >= 0.90 | viteza utila a cautarii; sensibila direct la prospetimea telemetriei (acoperirea se marcheaza LA GCS doar din telemetria LIVRATA) |
| mission_time / completed | primul t cu acoperire >= 0.95 SI victims_found >= 5; altfel plafon, completed=0 | rezultatul agregat, comparabil cu stratul de misiune C1 |
| coverage_end | acoperirea la final | cat a ramas neacoperit cand legatura a fost proasta |
| victims_found | victimele confirmate la GCS | eficacitatea; evenimentul de detectie traverseaza link-ul |
| rtl_events | comenzile rth emise de failsafe | bugetul energetic; arata daca degradarea comunicatiei costa energie |

### 3.5 Ce s-a intamplat in simulare (N=2, 12.06.2026)

1. Toate cele 8 misiuni s-au incheiat cu acoperire 100% si 5/5 victime, pe
   ambele profiluri si ambele middleware-uri — sub canalul spatial, degradarea
   nu a atins pragul de esec pe aria de 70x70 m.
2. M1 (compresia) CONFIRMATA: T90 difera cu cel mult 14% intre RMW-uri
   (camp deschis: Zenoh 96 s vs DDS 111 s; teren greu: 103 vs 104.5 s) —
   fata de ordinele de marime de la transport.
3. M2 (amplificarea pe teren greu) INDECIDABILA la N=2: diferenta medie intre
   RMW-uri (1.5–15 s) este sub variatia interna dintre repetitii (10–27 s).
   Decizia vine din campania extinsa (REPS=5).
4. M3 (RTL) N/A in aceasta rulare: zero evenimente raportate desi pragul
   dinamic ar fi trebuit sa declanseze — diagnostic in curs (parse-ul
   telemetriei in nodurile-plugin sau numaratoarea din analiza); metricile
   T90/acoperire/victime nu depind de acest lant.
5. M4: niciun esec — granita operationala spatiala e dincolo de conditiile
   acestor profiluri pe aceasta arie; testul ei cere arie mai mare sau profil
   mai agresiv.

## 4. Transferul in mediul real

### 4.1 Pasul 1 — reteaua devine reala (cel mai ieftin test real)

Acelasi cod, doua masini (laptop + al doilea calculator/Raspberry Pi),
interfata reala in loc de `lo`:

```bash
# masina A (operator): clientul / roiul
# masina B: ecoul / a doua statie
python3 run_campaign.py --iface wlp4s0 --reps 3 --out ~/c1_real
```

Capcane REALE de stiut dinainte: (1) descoperirea DDS foloseste multicast —
multe AP-uri WiFi o filtreaza („client isolation"): foloseste un AP propriu
sau hotspot dedicat; (2) la Zenoh, routerul trebuie accesibil de pe ambele
masini (porneste-l pe masina operatorului si verifica IP-ul in sesiune);
(3) pentru latenta intr-un singur sens ai nevoie de sincronizare de ceas
(chrony) — pe ecou (RTT) nu ai nevoie de nimic; (4) jurnalizeaza pe AMBELE
capete. Protocolul complet: `c1_benchmark/paper/experimental_protocol.md`.

### 4.2 Pasul 2 — canalul se calibreaza, nu se inventeaza

Mers pe jos cu o drona/statie: la 10/20/40/80 m masori RSSI si pierderea
(acelasi `latency_probe`), potrivesti exponentul si umbrirea, salvezi ca
profil nou (`campus_real`) si re-rulezi campania M neschimbata.

### 4.3 Ce se schimba si ce ramane (ipoteza de transfer)

Se SCHIMBA cifrele absolute: dinamica reala (vant, GPS, acceleratii), MAC-ul
WiFi care transforma pierderea in latenta, bateriile reale cu curba LiPo.
Se PASTREAZA (ipoteza tezei, de verificat): ordinea RMW-urilor pe fiecare
regim, forma compromisului (coada vs. prospetime), compresia transport ->
misiune si pragul de esec ca FENOMEN (valoarea lui se recalibreaza).

### 4.4 Lista minima de masuratori pe teren

1. RTT de referinta pe legatura curata (ambele RMW) — ancora.
2. RSSI + pierdere vs. distanta -> profilul calibrat.
3. O misiune scurta per RMW pe profilul calibrat (T90 + victime + RTL).
4. Acelasi manifest JSON per rulare — trasabilitate identica cu simularea.

## 5. Campania de noapte (C1 complet, ~3–4 h) — procedura

```bash
# DUPA ce campania de misiune s-a terminat si ai arhivat rezultatele:
cd ~/ros2_ws/src/c1_benchmark
./preflight.sh                                   # VERDICT: GO

# sudo nu are voie sa expire la ora 2 noaptea — improspatare automata:
sudo -v
( while true; do sudo -n true; sleep 240; done ) &
SUDO_KEEP=$!

# fara suspendare cat ruleaza campania (laptopul in priza, capacul deschis):
systemd-inhibit --what=sleep:idle \
  python3 run_campaign.py --iface lo --reps 5 --out ~/c1_results_full

kill $SUDO_KEEP

# dimineata:
python3 analyze_campaign.py ~/c1_results_full
mkdir -p ~/c1_archive && cp -r ~/c1_results_full ~/c1_archive/$(date +%F)_c1_N5/
# campaign_summary.csv -> la Claude: regenerez tabelul din articol cu N=5
```

Nota: nu atinge masina in timpul rularii (fara build-uri, fara browser greu);
tc este curatat automat la final si la Ctrl+C.
