# link_adaptive -- strat aplicativ adaptiv la starea legaturii pentru ROS 2 (contributia C3)

Pachet ament_python care masoara starea legaturii (RTT p95 + rata de pierdere) si
comuta intre trei moduri de comportament -- NOMINAL / DEGRADED / CRITICAL -- cu
histerezis, ca raspuns la concluzia campaniei C1 (articolul A1): niciun middleware
nu domina sub degradare, deci adapteaza-te. Nucleul decide POLITICA de date (rata,
fiabilitate, prag de prospetime, payload); un adaptor subtire o aplica pe flux.
Logica de decizie si cea de aplicare sunt nuclee pure, testabile fara ROS. Tinta
de publicare: A2 (contributia C3, adaptive QoS / behavior).

## 1. Scop

Cand alegerea statica de middleware pune in opozitie prospetimea controlului si
completitudinea telemetriei, link_adaptive ofera un strat care isi schimba
comportamentul dupa starea masurata a legaturii si tinteste ambele. Concret:

- masoara legatura din doua semnale (RTT p95 [ms] si rata de pierdere) folosind
  exact marimile din campania C1;
- clasifica starea in trei moduri cu histerezis si timp minim de stationare
  (anti-palpaire);
- expune o politica de date per mod (rata, fiabilitate, prag de prospetime,
  payload), pe care consumatorii o aplica pe fluxul lor (control vs telemetrie);
- inchide bucla cu un adaptor care sta in calea telemetriei si aplica politica,
  fara cod nou in drone_node / gcs_node.

## 2. Context si loc in arhitectura

Campania C1 (N=5, doua straturi) a aratat doua filozofii de fiabilitate, fara
castigator universal:

- DDS (fiabil) cumpara supravietuirea misiunii cu intarziere uniforma -- la
  pierdere mare un zid p95 de ~2.3 s; livreaza tot, dar tarziu;
- Zenoh (Age-of-Information) cumpara prospetimea cu pierderi -- mediana rapida,
  dar arunca ~35% la 30% pierdere;
- CDF-urile se incruciseaza (percentila ~57-60): nicio dominanta stochastica de
  ordinul intai.

Concluzia logica si urmatorul articol (A2): daca niciunul nu domina,
ADAPTEAZA-TE. link_adaptive este stratul aplicativ care realizeaza aceasta
concluzie. In arhitectura sistemului ruleaza in PARALEL cu roiul SAR: nu
modifica nodurile existente, ci expune o decizie pe care ceilalti o consuma.
Se combina cu mesh_plugin: mesh decide DACA exista cale la GCS, link_adaptive
decide CUM se comporta fluxul pe acea cale.

## 3. Arhitectura

Metodologia depozitului: nucleu pur testabil -> nod subtire (JSON pe
std_msgs/String) -> SIL. Doua nuclee pure (decizie si aplicare), doua noduri
subtiri, doua SIL-uri.

### 3.1 Lantul nucleu -> nod -> SIL

```
DECIZIE                                 APLICARE
link_adaptive_core.py (pur)             policy_applier.py (pur)
  LinkMonitor    (p95 + pierdere)         PolicyApplier (rata / prospetime / payload)
  AdaptiveController (histerezis)              |
  POLICIES (tabela mod -> politica)            |
        |                                      |
link_adaptive_node.py (ROS)             policy_adapter_node.py (ROS)
  masoara, decide, publica politica       sta in calea telemetriei, aplica + QoS
        |                                      |
        +-------------- /link_adaptive/policy -+

SIL (fara ROS):
  sil_link_adaptive.py   adaptiv vs static (fresh / complete) pe cronologie C1
  sil_policy_loop.py     bucla completa decizie + aplicare, debit + payload
```

- LinkMonitor: RTT p95 dintr-o fereastra glisanta de masuratori dus-intors;
  rata de pierdere din golurile numerelor de secventa, pe o fereastra. Ambele
  ferestre au dimensiune configurabila (rtt_window, seq_window).
- AdaptiveController: masina de stari cu histerezis (praguri de intrare/iesire
  diferite) si timp minim de stationare; coborare gradata din CRITICAL la
  DEGRADED (nu direct la NOMINAL).
- POLICIES: pentru fiecare mod, politica de date (rata, fiabilitate, prag de
  prospetime, payload). Nucleul nu trimite nimic -- decide POLITICA.
- PolicyApplier: aplica o politica pe un flux de mesaje prin trei actiuni --
  limitarea ratei (downsampling la rate_hz), aruncarea esantioanelor mai vechi
  decat max_staleness_ms, reducerea payload-ului (FULL / REDUCED / CRITICAL).
  Schimbarea fiabilitatii e doar SEMNALATA (reliability_changed); nodul subtire
  recreeaza publisher-ul cu noul QoS.

### 3.2 Topicuri (JSON pe std_msgs/String)

```
link_adaptive_node:
  publica:  /link_adaptive/policy   {mode, rate_hz, reliable, max_staleness_ms, payload}
            /link_adaptive/state     {rtt_p95_ms, loss, mode, transitions}
  asculta:  <rtt_topic>              {rtt_ms}     sursa de RTT (implicit /operator/heartbeat)
            <telemetry_topic>        {seq, ...}   pentru rata de pierdere (implicit /sar/telemetry)

policy_adapter_node:
  asculta:  <policy_topic>           politica de aplicat (implicit /link_adaptive/policy)
            <in_topic>               telemetrie bruta (implicit /sar/telemetry/raw)
  publica:  <out_topic>              telemetrie ajustata (implicit /sar/telemetry)
```

policy_adapter_node nu reconfigureaza el QoS-ul altora: pe calea telemetriei
recreeaza propriul publisher de iesire (reliable <-> best-effort) cand politica
cere -- in ROS 2 QoS-ul nu se poate schimba pe un publisher existent.
Histerezisul + stationarea din controler fac aceste recreari rare.

## 4. Inventar fisiere

| Fisier | Rol | Cum se verifica |
|--------|-----|-----------------|
| `link_adaptive/link_adaptive_core.py` | nucleu pur decizie: LinkMonitor, AdaptiveController, POLICIES | `python3 link_adaptive_core.py` -> 22/22 |
| `link_adaptive/policy_applier.py` | nucleu pur aplicare: rata / prospetime / payload, semnal QoS | `python3 policy_applier.py` -> 13/13 |
| `link_adaptive/link_adaptive_node.py` | nod subtire: masoara, decide, publica politica + stare | entry point `link_adaptive_node` |
| `link_adaptive/policy_adapter_node.py` | nod subtire: aplica politica pe telemetrie, recreeaza QoS | entry point `policy_adapter_node` |
| `link_adaptive/sil_link_adaptive.py` | SIL: adaptiv vs static (fresh/complete) pe cronologie C1 | `python3 sil_link_adaptive.py` (exit 0) |
| `link_adaptive/sil_policy_loop.py` | SIL: bucla completa decizie + aplicare (debit + payload) | `python3 sil_policy_loop.py` (exit 0) |
| `launch/link_adaptive.launch.py` | porneste doar stratul de decizie (un nod) | `ros2 launch ...` |
| `launch/link_adaptive_loop.launch.py` | bucla completa: decizie + adaptor | `ros2 launch ...` |
| `docs/sil_link_adaptive.png` | figura SIL adaptiv vs static (generata de sil_link_adaptive) | regenerabila |
| `docs/sil_policy_loop.png` | figura SIL bucla C3 (generata de sil_policy_loop) | regenerabila |
| `package.xml`, `setup.py`, `setup.cfg` | metadate ament_python + entry_points | `colcon build` |
| `resource/link_adaptive` | marker ament_index (gol) | prezenta |
| `requirements.txt` | dependinta pip externa: matplotlib (pentru figurile SIL) | `pip install -r` |
| `PROIECT_LINK_ADAPTIVE.md` | documentul de design al contributiei C3 | lectura |

Entry-points reale (din `setup.py`): `link_adaptive_node`, `policy_adapter_node`,
`sil_link_adaptive`, `sil_policy_loop`. Cele patru noduri/SIL au `main()` care
intoarce None (ca `ros2 run` sa nu raporteze fals "failure 1").

## 5. Date tehnice

### 5.1 Moduri si politici (din `link_adaptive_core.POLICIES`)

| Mod | Cand | rata | fiabilitate | prospetime (max_staleness) | payload |
|-----|------|------|-------------|----------------------------|---------|
| NOMINAL | legatura buna | 20 Hz | fiabil | 1000 ms | FULL |
| DEGRADED | legatura medie | 10 Hz | best-effort | 300 ms | REDUCED |
| CRITICAL | legatura proasta | 2 Hz | best-effort | 100 ms | CRITICAL |

Principiul per flux (consumatorii aplica politica pe fluxul lor):

- Control (comenzi de teleoperare): mereu proaspat -- best-effort, arunca
  esantioanele mai vechi decat pragul, actioneaza pe ultima comanda; eviti zidul
  de retransmisii. Prospetimea bate completitudinea pentru control.
- Telemetrie (harta / acoperire): fiabila cand retransmisiile sunt ieftine si
  eficace (NOMINAL: latenta mica, pierdere mica -> recupereaza pierderile);
  best-effort cand fiabilitatea devine inutila (pierdere/latenta mare, unde si
  DDS arunca mult).

Reducerea payload-ului in `policy_applier` (campuri pastrate, configurabile prin
parametri): REDUCED = `id, x, y, seq, t, soc, phase`; CRITICAL = `id, x, y, seq, t`;
FULL = pastreaza tot.

### 5.2 Praguri cu histerezis (din `link_adaptive_core.py`)

```
NOMINAL  -> DEGRADED : RTT p95 > 150 ms  SAU  pierdere > 5%     (DEG_ENTER)
...      -> CRITICAL : RTT p95 > 800 ms  SAU  pierdere > 20%    (CRIT_ENTER)
DEGRADED -> NOMINAL  : RTT p95 <= 100 ms SI   pierdere <= 2%    (DEG_EXIT)
CRITICAL -> DEGRADED : RTT p95 <= 500 ms SI   pierdere <= 12%   (CRIT_EXIT)
stationare minima    : 2 s                                      (MIN_DWELL_S)
```

Intrarea (inrautatire) foloseste praguri mai sus si comparatie strict mai mare
(valoarea pragului e plafonul modului mai bun; ex. pana la 5% pierdere inclusiv
ramane NOMINAL). Iesirea (imbunatatire) foloseste praguri mai jos. Banda dintre
iesire si intrare absoarbe zgomotul si previne palpairea. Maparea pe C1
(verificata in selftest): ideal / loss_5 -> NOMINAL; loss_15 / lat200_jit50 /
lat200_l15 -> DEGRADED; loss_30 -> CRITICAL.

### 5.3 Parametri ai nodurilor

`link_adaptive_node`: `rtt_topic` (/operator/heartbeat), `telemetry_topic`
(/sar/telemetry), `decide_hz` (5.0), `min_dwell_s` (2.0), `rtt_window` (50),
`seq_window` (100).

`policy_adapter_node`: `in_topic` (/sar/telemetry/raw), `out_topic`
(/sar/telemetry), `policy_topic` (/link_adaptive/policy), `stamp_field` (""),
`depth` (10), `reduced_fields`, `critical_fields`.

Nota despre aruncarea pe vechime: varsta = acum - stamp, unde stamp se citeste
din campul `stamp_field`. Implicit `stamp_field` e gol, deci aruncarea pe vechime
e DEZACTIVATA (age = 0); limitarea ratei si reducerea payload-ului merg oricum.
Pentru a o activa, telemetria trebuie sa poarte un timestamp pe ceas de perete
(secunde) in acel camp.

## 6. Sintaxe de pornire

```bash
# 0) verificari offline (fara ROS) -- numere reale
cd ~/ros2_ws/src/link_adaptive/link_adaptive
python3 link_adaptive_core.py        # 22/22 + demo traiectorie C1
python3 policy_applier.py            # 13/13
python3 sil_link_adaptive.py         # bilant adaptiv vs static + sil_link_adaptive.png
python3 sil_policy_loop.py           # bilant bucla C3 + sil_policy_loop.png

# 1) build in workspace (pachet ament_python)
cd ~/ros2_ws
colcon build --packages-select link_adaptive
source install/setup.bash            # in FIECARE terminal nou
ros2 pkg executables link_adaptive   # cele 4 entry-points

# 2) ruleaza doar stratul de decizie (in paralel cu roiul)
ros2 launch link_adaptive link_adaptive.launch.py \
    rtt_topic:=/operator/heartbeat telemetry_topic:=/sar/telemetry
ros2 topic echo /link_adaptive/policy
ros2 topic echo /link_adaptive/state

# 3) bucla C3 completa (decizie + adaptor pe calea telemetriei)
#    o singura remapare a iesirii dronelor, fara cod nou:
#    drone_node ... -r /sar/telemetry:=/sar/telemetry/raw
ros2 launch link_adaptive link_adaptive_loop.launch.py \
    rtt_topic:=/operator/heartbeat \
    in_topic:=/sar/telemetry/raw out_topic:=/sar/telemetry

# 4) SIL prin entry-points (echivalent cu rularea directa)
ros2 run link_adaptive sil_link_adaptive
ros2 run link_adaptive sil_policy_loop
```

Limitari de pornire:

- Modificarile la entry-points / setup.py necesita rebuild (wrapper-ele `ros2 run`
  se genereaza la build).
- Figurile SIL cer matplotlib (`requirements.txt`); fara el, SIL-ul ruleaza si
  sare peste figura.
- Eroare RTPS_TRANSPORT_SHM la pornire (memorie partajata reziduala, non-fatal):
  `rm -f /dev/shm/fastrtps_*`.

## 7. Verificare

Selftests pure (ROS-free), ruleaza in mediu fara colcon:

| Verificare | Comanda | Rezultat real |
|-----------|---------|---------------|
| nucleu decizie | `python3 link_adaptive_core.py` | 22/22 verificari trecute |
| nucleu aplicare | `python3 policy_applier.py` | 13/13 verificari trecute |
| SIL adaptiv vs static | `python3 sil_link_adaptive.py` | exit 0 (criteriu: ADAPTIVE mai proaspat si completitudine >= STATIC-FRESH) |
| SIL bucla C3 | `python3 sil_policy_loop.py` | exit 0 (criteriu: debit fwd scade strict NOMINAL > DEGRADED > CRITICAL) |

Selftest-ul nucleului acopera: percentila (lista goala, constanta, sir crescator),
rata de pierdere din secvente (cu goluri si reordonare in fereastra), clasificarea
pe cele sase conditii C1, histerezisul (nu palpaie in banda de oscilatie),
stationarea minima (tranzitia prea rapida e blocata), coborarea gradata din
CRITICAL, si monotonia politicilor cu severitatea. Selftest-ul applier-ului
acopera: limitarea ratei (~10 forward din 100 la 10 Hz), aruncarea pe vechime,
cele trei niveluri de payload, semnalarea schimbarii de fiabilitate si payload
non-dict tolerat.

Rezultate SIL (deterministe, N=1 -- de inlocuit cu campania reala
adaptiv-vs-static cu N=5):

`sil_link_adaptive.py`, cronologie C1 (legatura se degradeaza si isi revine),
trei strategii pe doua axe:

```
strategie         staleness control          completitudine telemetrie
                  (mediu / cel mai rau)       (medie / cea mai rea)
STATIC-COMPLETE   430 ms / 1262 ms            91% / 61%
STATIC-FRESH       30 ms /  100 ms            92% / 65%
ADAPTIVE           30 ms /  100 ms            93% / 65%
```

ADAPTIVE pastreaza controlul ~14x mai proaspat decat STATIC-COMPLETE (30 vs 430 ms
mediu; 100 vs 1262 ms cel mai rau), recuperand telemetria pe care STATIC-FRESH o
pierde cand legatura e buna (93% vs 92% mediu). Fiecare alegere statica pierde pe
cate o axa; adaptivul prinde coltul bun. Figura: `docs/sil_link_adaptive.png`.

`sil_policy_loop.py`, aceeasi cronologie C1: stratul reduce singur debitul
(20 -> 10 -> 2 Hz) si payload-ul (FULL -> REDUCED -> CRITICAL) pe masura ce
legatura se inrautateste; pe intreaga cronologie 720 esantioane intrate -> 416
forward-ate (58%), 304 aruncate pe rata, 0 pe vechime (stamp_field dezactivat in
SIL). Figura: `docs/sil_policy_loop.png`.

## 8. Igiena datelor si reproductibilitate

- Cifrele SIL sunt un model determinist ancorat in mediile C1 (N=5); ilustreaza
  strategia, NU sunt date empirice noi. Modelul de staleness / completitudine e un
  proxy transparent (latenta de baza / zid p95 / pierdere livrata) si se
  inlocuieste cu campania reala adaptiv-vs-static (N=5) inainte de orice submisie.
- Figurile `docs/*.png` sunt regenerabile ruland SIL-urile; nu sunt date brute.
  SIL-urile scriu `sil_*.png` in directorul curent de rulare -- copiaza-le in
  `docs/` daca vrei sa actualizezi figurile din pachet.
- Pragurile sunt setate din C1; transferul la o legatura reala (field_kit) cere
  verificare si eventual recalibrare pe profil de canal real.
- Costul real in CRITICAL este rata redusa de telemetrie (rezolutie temporala mai
  mica a hartii), nu completitudinea.
- TODO: verificarile de stil ament (`ament_copyright`, `ament_flake8`,
  `ament_pep257`) sunt declarate ca test_depend in package.xml dar nu exista un
  director `test/` dedicat in pachet; verificarea principala ramane selftest-urile
  pure (22/22 + 13/13).
- Documentul de design complet: `PROIECT_LINK_ADAPTIVE.md`. Licenta: MIT.
