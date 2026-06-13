# PROIECT_LINK_ADAPTIVE -- design (contributia C3)

Document de design pentru pachetul `link_adaptive`. ASCII (fara diacritice),
pentru depozit. Stare: nucleu pur testat (22/22) + nod + SIL; cifrele SIL sunt
deterministe (N=1), de inlocuit cu campania reala adaptiv-vs-static (N=5).

## 1. Motivatie (de ce exista)

Campania C1 (N=5, doua straturi) a aratat ca NICIUN middleware nu domina sub
degradare:
- DDS (fiabil) cumpara supravietuirea misiunii cu intarziere uniforma -- la
  pierdere mare, un zid p95 de ~2.3 s; livreaza tot, dar tarziu;
- Zenoh (Age-of-Information) cumpara prospetimea cu pierderi -- mediana rapida,
  dar arunca ~35% la loss_30.
- CDF-urile se incruciseaza (percentila ~57-60): nu exista dominanta stochastica
  de ordinul intai.

Concluzia logica si urmatorul articol (A2): daca niciunul nu domina,
ADAPTEAZA-TE. Un strat aplicativ care isi schimba comportamentul dupa starea
masurata a legaturii, obtinand prospetimea controlului SI completitudinea
telemetriei -- doua lucruri pe care o alegere statica de middleware le pune in
opozitie.

## 2. Semnalul de stare a legaturii

Doua marimi, exact cele din campania C1:
- **RTT p95** [ms]: dintr-o fereastra glisanta de masuratori dus-intors (eco /
  heartbeat, acelasi ceas). p95, nu media -- conteaza coada, nu cazul tipic.
- **rata de pierdere**: din golurile numerelor de secventa de pe fluxul de
  telemetrie, pe o fereastra.

Extensibil cu RSSI (de la radio_link_node) ca al treilea semnal; nucleul accepta
deja praguri separate, deci adaugarea e o muchie noua in clasificare.

## 3. Modurile si politicile

Trei moduri, raspuns gradat la severitate:

| Mod | Cand | Politica (rata, fiabilitate, prospetime, payload) |
|-----|------|---------------------------------------------------|
| NOMINAL | legatura buna | 20 Hz, fiabil, prag 1000 ms, payload FULL |
| DEGRADED | legatura medie | 10 Hz, best-effort, prag 300 ms, payload REDUCED |
| CRITICAL | legatura proasta | 2 Hz, best-effort, prag 100 ms, payload CRITICAL |

Principiul per FLUX (nucleul expune politica, consumatorii o aplica pe fluxul lor):
- **Control** (comenzi de teleoperare): mereu prospat -- best-effort, arunca
  esantioanele mai vechi decat pragul, actioneaza pe cea mai noua comanda. Eviti
  zidul de retransmisii al fiabilitatii. Prospetimea bate completitudinea pentru
  control.
- **Telemetrie** (harta / acoperire): fiabila cand retransmisiile sunt ieftine si
  eficace (NOMINAL: latenta mica, pierdere mica -> recupereaza pierderile);
  best-effort cand fiabilitatea devine inutila (pierdere/latenta mare, unde si
  DDS arunca mult) -- acolo nu mai irosesti legatura pe retransmisii futile.

## 4. Histerezis si stationare (anti-palpaire)

Praguri de INTRARE (inrautatire) mai sus, de IESIRE (imbunatatire) mai jos; banda
dintre ele absoarbe zgomotul. Plus un timp minim de stationare intre schimbari.
Din CRITICAL se coboara intai la DEGRADED, nu direct la NOMINAL (revenire gradata).

Valori implicite (in `link_adaptive_core.py`):
- NOMINAL -> DEGRADED: RTT p95 > 150 ms SAU pierdere > 5%.
- ... -> CRITICAL: RTT p95 > 800 ms SAU pierdere > 20%.
- DEGRADED -> NOMINAL: RTT p95 <= 100 ms SI pierdere <= 2%.
- CRITICAL -> DEGRADED: RTT p95 <= 500 ms SI pierdere <= 12%.
- stationare minima: 2 s.

Maparea pe C1: ideal/loss_5 -> NOMINAL; loss_15 / lat200_* -> DEGRADED;
loss_30 -> CRITICAL. Verificata in selftest.

## 5. Arhitectura software (metodologia depozitului)

1. `link_adaptive_core.py` -- nucleu pur (fara ROS): LinkMonitor (p95 + pierdere),
   AdaptiveController (histerezis + stationare), tabela POLICIES. Selftest 22/22.
2. `link_adaptive_node.py` -- nod subtire: asculta RTT (heartbeat) si telemetrie
   (secvente), ruleaza controlerul, publica politica pe /link_adaptive/policy.
3. `sil_link_adaptive.py` -- SIL: adaptiv vs static (fresh/complete) pe o
   cronologie C1; figura cu modul in timp + cele doua axe.
4. pachet ament_python (package.xml, setup.py, entry-points).

## 6. Experimentul (ce masuram)

Campania adaptiv-vs-static, N=5, pe scenariile existente:
- trei strategii: STATIC-COMPLETE (DDS fiabil), STATIC-FRESH (Zenoh best-effort),
  ADAPTIVE (link_adaptive);
- doua metrici: staleness control [ms] (mai mic = mai bine) si completitudine
  telemetrie [%] (mai mare = mai bine); plus numarul de tranzitii (stabilitate).
- ipoteza: ADAPTIVE prinde coltul bun (staleness mic ca FRESH, completitudine
  mare ca COMPLETE), pe cand fiecare strategie statica pierde pe cate o axa.

Rezultat SIL (determinist, ilustrativ): control ~14x mai proaspat decat
STATIC-COMPLETE (30 vs 430 ms mediu; 100 vs 1262 ms cel mai rau), completitudine
egala/usor peste STATIC-FRESH. De inlocuit cu N=5 real.

## 7. Integrarea in roi

`link_adaptive_node` ruleaza in paralel; publica politica. Aplicarea se face
printr-un adaptor subtire `policy_adapter_node` (logica in `policy_applier`,
testata 13/13) care sta in calea telemetriei si ajusteaza rata de publicare,
aruncarea esantioanelor vechi, nivelul de payload si QoS-ul (reliable vs
best-effort, prin recrearea publisher-ului). Atasare cu o singura remapare a
iesirii dronelor (`-r /sar/telemetry:=/sar/telemetry/raw`), fara cod nou in
drone_node/gcs_node. Bucla completa: `link_adaptive_loop.launch.py`; efectul
end-to-end (debit 20->10->2 Hz, payload FULL->REDUCED->CRITICAL) e demonstrat de
SIL-ul `sil_policy_loop` (figura `docs/sil_policy_loop.png`). Stratul ramane un
controler curat: link_adaptive EXPUNE decizia, policy_adapter o aplica. Se
combina cu `mesh_plugin`: mesh decide DACA exista cale la GCS, link_adaptive
decide CUM se comporta fluxul pe acea cale.

## 8. Limite (threats to validity)

- Cifrele SIL sunt un model determinist ancorat in mediile C1; ilustreaza
  strategia, nu sunt date empirice noi.
- Modelul de staleness/completitudine e un proxy transparent (latenta de baza /
  zid p95 / pierdere livrata); campania reala il inlocuieste.
- Pragurile sunt setate din C1; transferul lor la o legatura reala (field_kit)
  trebuie verificat -- pragurile pot necesita recalibrare pe profil de canal real.
- Stratul presupune ca poti rula concurent un flux de control best-effort si unul
  de telemetrie fiabil; costul real in CRITICAL e rata redusa de telemetrie
  (rezolutie temporala mai mica a hartii), nu completitudine.

## 9. Tinta de publicare

A2 -- SSRR / ICRA-W 2027 (contributia C3, adaptive QoS / behavior). Figura de
rezultat: `docs/sil_link_adaptive.png` (de inlocuit cu cea din campania N=5).
