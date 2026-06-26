# BRIEF TEZA DOCTORALA -- TELEOPERARE IN TIMP REAL PESTE RETELE DEGRADATE

Acest document este AUTONOM. Contine tot contextul necesar pentru a discuta pasii urmatori, fara acces la cod sau la conversatii anterioare. Toate cifrele sunt din fisiere reale ale proiectului. Acolo unde un rezultat e provizoriu (obtinut in simulare/loopback, nu pe hardware real) am marcat asta explicit. NU inventa cifre, citari sau rezultate suplimentare; daca ai nevoie de o cifra care nu e aici, intreaba-ma.

---

## 1. CONTEXT TEZA

**Scopul tezei:** teleoperare in timp real peste retele degradate. Coloana stiintifica este un benchmark riguros intre doua middleware-uri ROS 2 -- rmw_zenoh vs rmw_cyclonedds_cpp -- sub degradare de retea controlata cu `tc netem` (pierdere, latenta, jitter). Intrebarea centrala: ce middleware si ce politica de adaptare sustin teleoperarea atunci cand legatura se deterioreaza.

**Cele patru contributii C1-C4** (atentie la onestitate: in CLAUDE.md set-ul e numit "C1-C4" dar NU toate sunt definite individual; redau doar ce e ancorat concret in repo):
- **C1** -- benchmark-ul rmw sub degradare controlata (pachet `c1_benchmark/`), sursa articolului A1. Definitia textuala explicita lipseste, dar asocierea C1 = benchmark este clara din context.
- **C2** -- NU este mapata explicit pe un pachet in fisiere (datorie tehnica deschisa, audit 2026-06-25, punctul "C2 de clarificat"). Din harta articolelor pare legata de canalul spatial/real (A3). DE CLARIFICAT.
- **C3** -- mesh multi-hop (`mesh_plugin/`) + adaptare/selector link-aware (`link_adaptive/`).
- **C4** -- exoschelet de reabilitare + motor (`rehab_exo_description/`, `servo_control/`, `joint_emulator/`).

**Harta articolelor A1-A5** (singura intrare complet ancorata e A1; restul vin din documentele de roadmap):
- **A1 = SSRR 2026** -- benchmark CycloneDDS vs Zenoh, sursa in `c1_benchmark/` (cu `paper/main.tex`). Singurul articol cu schelet de paper scris.
- **A2 = SSRR/ICRA-W 2027** -- `link_adaptive` (C3).
- **A3** -- canal spatial + real (field_kit + campania M la N>=5), C1 extins + C2.
- **A4** -- tele-impedanta pe fier (banc + telerehab), C4.
- A5 mentionata ca exista in harta, fara detalii in fisiere.

**Demonstratoarele tezei:**
- **Roi SAR (drone)** -- `sar_swarm` (roi 4 drone + statie de control la sol GCS + injector de defecte + sonda; >100 teste, inghetat) si `sar_plugins` (canal radio/baterie/acoperire/victime, 55 teste).
- **Exoschelet rehab** -- `rehab_exo_description` v0.3.0 + `joint_emulator` (banc 6 servo ABB cuplate in perechi, in simulare).
- **Rover** -- `teleop_rover` (link degradat, pilot/manual, perceptie HSV + go-to-goal); demonstrator secundar pentru prezentari.

---

## 2. ARHITECTURA SI METODOLOGIE

**Stack ROS 2:** ROS 2 Jazzy. Benchmark-ul compara doua implementari RMW (ROS MiddleWare):
- `rmw_cyclonedds_cpp` (DDS clasic).
- `rmw_zenoh_cpp` (Zenoh, cu router dedicat `rmw_zenohd`).
Degradarea se aplica cu `tc netem` pe egress-ul unei interfete. In SIL pe `lo` (loopback); in HIL pe interfata reala intre doua masini.

**Regula de fier (metodologia de dezvoltare, lant fix, neviolabil):**
1. **Nucleu pur** -- algoritmul scris intr-un modul FARA ROS, fara I/O, fara dependinte grele (sklearn etc.), DETERMINIST cu seed, cu `_selftest()` integrat.
2. **Nod ROS subtire** -- un wrapper subtire peste nucleu; comunica JSON pe `std_msgs/String`.
3. **SIL** -- software-in-the-loop pe loopback (`lo`), bucla de dezvoltare.
4. **Pachet ament_python** -- impachetare standard ROS 2.
5. **Verificare pre-push** -- numar de fisiere, toate selftest-urile verzi, amprente de versiune.
Consecinta: algoritmii se testeaza in izolare, complet decuplati de ROS. Acelasi nucleu serveste SIL si HIL fara modificare de cod.

**Pachetele cheie:**
- `c1_benchmark/` -- benchmark-ul + selectorul + scheletul articolului A1.
- `link_adaptive/` -- strat aplicativ care isi schimba comportamentul dupa starea legaturii (NOMINAL/DEGRADED/CRITICAL cu histerezis), C3.
- `mesh_plugin/` -- mesh multi-hop, relay hop-by-hop, ETX, C3.
- `sar_swarm/`, `sar_plugins/` -- demonstratorul SAR + canalul radio/baterie.
- `joint_emulator/`, `rehab_exo_description/` -- C4.
- `teleop_rover/` -- rover.

**Punct metodologic critic (din nota metodologica C1):** comparatia echitabila Zenoh vs CycloneDDS NU poate fi stabilita fiabil pe un singur host cu netem pe `lo`. Pe loopback Zenoh nu produce rezultate reproductibile (sensibil la stare reziduala si la instabilitatea routerului sub pierdere). O campanie initiala a aratat Zenoh aparent imun la pierdere -- fizic implauzibil, dovedit ARTEFACT de stare reziduala (router/proces ramas din sesiune anterioara, conditii de cursa la pornire). Concluzie textuala: comparatia autoritara necesita DOUA masini fizice (hardware-in-the-loop) cu netem pe legatura reala. Cheia: schema de date si pipeline-ul de analiza sunt IDENTICE SIL/HIL, deci dupa colectare `analyze_campaign.py` + selectorul ruleaza fara modificare de cod.

---

## 3. STADIUL ACTUAL (cu cifre exacte)

**Setup selector (focus curent):** 24 celule = 8 conditii x 3 payload-uri, **N=10**. Validare leave-one-condition-out (LOCO), NU split aleator. Toate cifrele de mai jos sunt SIL/loopback, PROVIZORII.

**Obiectiv CONTROL (minimizeaza RTT p95 -- latenta de coada):**
- always-CycloneDDS domina: regret mediu **142 ms**, castiga in **17/24** celule.
- Selectorul invatat NU il bate: 1-NN are **66.7% acuratete** dar regret **558 ms**; arborele de decizie are regret **653 ms**. (Regretul regulii global-Zenoh este 1143 ms, ca referinta.)

**Obiectiv CONSTIENT DE PIERDERE (loss-aware),** cost = `(1-loss)*RTT_p95 + loss*D`, unde D = deadline de control (penalizarea unui pachet pierdut):
- La **D=1000 ms**: always-CycloneDDS inca castiga (**90 ms vs 197 ms**).
- La **D=5000 ms**: selectorul 1-NN BATE always-CycloneDDS (**104 ms vs 188 ms**).
- **Concluzie dependenta de deadline:** selectorul invatat se justifica DOAR in regimul cu drop foarte scump (D mare, ex. control de siguranta). Pentru D mic/moderat, always-CycloneDDS ramane regula corecta.

**Caracterizare ML auxiliara (PDIA):** regresie log RTT prezis cu R^2_test=**0.90**; clasificator "link utilizabil" (<500 ms) acuratete **0.94**.

**Datele selectorului:** veriga rupta a fost REPARATA. `ml_dataset.csv` era extract orfan (loss_pct=0, sent==recv, N=5) -- NU se mai foloseste. Bridge-ul (`build_selector_dataset.py`) reconstruieste din campania reala `selector_dataset.csv` = **478 randuri, N=10, 8 conditii, 3 payload-uri, loss MASURAT (333/478 cu loss>0)**, cu 2 rulari zenoh/loss_30 sarite (pierdere ~totala, fara RTT). `selector_dataset.csv` si `selector_regret.png` sunt gitignorate (regenerabile).

**Referinta loopback N=10 (campanie curata P2P, payload 4096 B), p95 [ms] -- PROVIZORIU:**
- CycloneDDS loss_15..loss_30: **1019 / 1746 / 2145 / 2317** (CV 10/6/3/2% -- predictibil).
- Zenoh loss_15..loss_30: **560 / 972 / 5392 / 8709** (CV 23/55/100/63% -- imprevizibil; loss_25 variaza intre 0.9 si 18.5 s intre rulari identice).
- Pierderi round-trip masurate (SIL N=10): loss_15 DDS 1.4% / Zenoh 8.5%; loss_30 DDS 41% / Zenoh 57.8%; lat200_l15 DDS 36% / Zenoh 20.8%.

**Ce e SOLID si citabil chiar din SIL (nu afectat de problema Zenoh):** CycloneDDS este reproductibil, monoton, fizic coerent -- pierderea round-trip sub predictia `1-(1-p)^2`, conditiile de latenta dau RTT ~2x latenta one-way, CV < 20%. Fizica round-trip si conditiile `lat200_*` sunt corecte pentru ambele middleware.

**Ce e gata (cod):** `c1_benchmark` (schelet paper + selector), `link_adaptive` (nucleu + selector link-aware, selftest verde), `mesh_plugin` (functional), demonstratoarele SAR/rover/rehab in simulare. NIMIC nu e inca validat pe hardware real (HIL).

---

## 4. CE S-A CONSTRUIT RECENT (faza OVERNIGHT, commit-uri ad63675..d8efa2f, 15 commit-uri RF/HMI/C4 peste baza b63ae96)

Toate selftest-urile si smoke_all au fost re-rulate live: **smoke_all = 11 ok / 0 fail**.

**4.1 Pluginul de interferenta RF** -- nucleu pur `sar_plugins/rf_interference.py`, zero ROS/IO, determinist cu seed. Trei componente:
- **Gilbert-Elliott** -- `BurstProcess(p, r, loss_bad, loss_good, seed)`: model cu doua stari (good/bad) pentru pierderi in RAFALE; expune `draw()`, `steady_loss`, `mean_burst_len=1/r`, `from_steady()`, si `to_netem_gemodel()` (paritate de model SIL<->HIL, emite sintaxa `loss gemodel` pentru netem).
- **Co-canal SINR** -- `cochannel_sinr(rx_dbm, interferers_dbm, noise_dbm) -> (sinr_db, interference_db)`, functie pura.
- **Punte pura** -- `linkstate_to_netem(ls, iface)`: din dict `/sar/linkstate` construieste comanda `tc netem` (gemodel daca exista p,r; altfel memoryless).
- **TESTAT SIL:** `test_rf_interference.py` **14/14 PASS** (convergenta steady_loss, mean_burst_len empiric, determinism seed, monotonia SINR, sintaxa to_netem_gemodel SI linkstate_to_netem). Deci nucleul puntii e testat, nu doar compilat.

**4.2 Integrarea (canal SIL + campanie + selector + link_adaptive):**
- **Canal SIL** -- hook aditiv de rafale (`LinkState.drops` + BurstProcess) in `netem_core.py` din sar_swarm, mesh_plugin, teleop_rover (identic, determinist, aditiv).
- **Conditii gilbert_*** -- `gilbert_20/25/30` adaugate in `bench_core.CONDITIONS` cu ACEEASI pierdere medie ca `loss_20/25/30` dar in rafale (p=0.05/0.0667/0.0857, r=0.2); `netem_cmd` emite `loss gemodel`.
- **Selector** -- feature noua `mean_burst_len` in `selector_core.py` (inchide TODO-ul de burstiness); `gilbert_*` se disting de `loss_*` DOAR pe burst.
- **link_adaptive** -- a treia metrica `max_run_of_gaps` -> escaladare la CRITICAL la rafala (backward-compatible).
- **TESTAT SIL:** `test_burst_channel.py` PASS -- la aceeasi medie 0.3, **outage burst=7.96 vs memoryless=1.43 (5.6x)**; `test_bench_core.py` 13/13 (incl. gemodel); `test_selector_core.py` 37/37 (incl. gilbert_30 vs loss_30 identice pe loss/lat/jit, distincte pe burst); `link_adaptive_core.py` selftest 26/26.

**4.3 Nodurile ROS** (`sar_plugins/nodes/`, noduri subtiri peste nucleu):
- `rf_channel_node.py` -- publisher `/sar/linkstate` imbogatit (Gilbert-Elliott in timp), params p/r/rate_hz.
- `netem_bridge_node.py` -- punte SIL->HIL; asculta `/sar/linkstate`, construieste `tc netem` via `linkstate_to_netem`. **DRY-RUN implicit** (doar logheaza; `enable:=true` executa cu sudo).
- **STATUS:** DOAR py_compile (ambele importa rclpy). NU rulate headless (nu exista ROS pornit in acest mediu). Singura parte testata e logica de fond `linkstate_to_netem`. Schema `/sar/linkstate` e extinsa aditiv (`loss, burst_len, instant_drop, p, r`) -- contractul vechi nu se rupe prin design, dar nu verificat la runtime.

**4.4 HMI x3:**
- `post_run_viewer.py` (nucleu `post_run_core.py`) -- OFFLINE, fara ROS. PARTIAL TESTAT SIL: nucleul selftest PASS; viewer-ul a fost rulat pe campania reala `c1_transport` + **verificat vizual**. Singurul HMI cu validare end-to-end (fiind offline).
- `dashboard_node.py` + `fault_panel.py` (nucleu `rf_status_core.py`) -- dashboard arata RF status (loss/burst_len/interf_db, ok/warn/crit) + link_adaptive; fault_panel injecteaza burst_len + interf_db. Nucleu selftest PASS. DOAR py_compile (rclpy + tkinter). **Layout GUI NEVERIFICAT vizual** (headless).
- `campaign_panel.py` (nucleu `campaign_hmi_core.py`) -- orchestrare SIL/locala (`subprocess.Popen` pe run_campaign, fara SSH/remote). Nucleu selftest PASS. DOAR py_compile (tkinter). **GUI neverificat vizual.**

**4.5 C4: stability margin + ESTOP** (`joint_emulator`):
- **EnergyMonitor** in `joint_core.py` -- margine de stabilitate glisanta pe 1s (`win_energy = integ(tau_B*om)`); cresterea = semn de instabilitate.
- `emulator_node` + `operator_panel_node` -- emulatorul publica aditiv `win_energy`/`estopped` (un monitor pe pereche); `estop_energy=0.0` implicit = doar monitorizeaza (comportament NESCHIMBAT), `>0` = auto-ESTOP opt-in (taie cuplul). operator_panel afiseaza margine + `[ESTOP]`.
- **TESTAT SIL:** `test_joint_core.py` **38/38 PASS** (incl. stability margin + ESTOP + reset_estop). Nodurile: DOAR py_compile (rclpy + tkinter), nu rulate headless.

---

## 5. STATUS ONEST: SIL vs HIL

**Ce e provizoriu / nu se poate afirma inca:**
- **Loopback:** TOATE cifrele din repo sunt SIL pe `lo`. Comparatia echitabila Zenoh vs CycloneDDS NU se poate afirma din loopback (vezi sectiunea 2). Valorile de "imunitate Zenoh" din campania initiala sunt nereproductibile (artefact de stare reziduala) si NU trebuie folosite.
- **N mic:** selectorul ruleaza pe N=10 loopback; regula de proiect cere N>=5 pe HIL inainte de submisie (N>=cel din SIL). Cifrele selectorului si pragurile sunt provizorii.
- **D si forma costului:** deadline-ul D si forma functionala `(1-loss)*RTT_p95 + loss*D` sunt ALEGERI DE MODELARE, nu rezultate masurate. Concluzia "always-CycloneDDS vs selector" e dependenta de D -> trebuie validata cu sweep mai fin.
- **Parametrii Gilbert SINTETICI:** p,r din `gilbert_*` provin dintr-un SWEEP SINTETIC, NU calibrati pe trace radio real. `5.6x` (outage burst vs memoryless) e o PROPRIETATE A MODELULUI la parametrii alesi, nu o masura de fier.
- **Co-canal NEINTEGRAT:** `cochannel_sinr` e functie pura testata, dar grep o gaseste DOAR in core + test -- nelegata de lant. Integrarea co-canal este declarata explicit **Faza 2 (post-A1)**. Produce doar cifre de model sintetic.
- **GUI neverificat vizual:** dashboard_node, fault_panel, operator_panel_node, campaign_panel -- doar py_compile, niciun layout verificat vizual (headless). Singurul HMI validat end-to-end e post_run_viewer (offline).
- **Noduri ROS doar py_compile:** rf_channel_node, netem_bridge_node, emulator_node -- importa rclpy, NU rulate cu ROS pornit.
- **Pragul ESTOP** (`estop_energy`) si forma energiei sunt alegeri de modelare, de validat pe HIL.
- **C2** nu e mapata pe un pachet; **datorii tehnice:** duplicare byte-identica de core-uri vendorizate (sar_core, swarm_core, world_config, netem_core in 4 pachete); incalcari ASCII in cod (de transliterat batch inainte de submisie); lant baterie/radio de diagnosticat in sar_plugins (M3/RTL raporteaza zero evenimente -- parse telemetrie suspectat).

**Ce ramane SOLID chiar din SIL:** caracterizarea CycloneDDS (reproductibil, monoton, predictibil, CV<20%), fizica round-trip, conditiile de latenta `lat200_*`. Acestea sunt citabile.

---

## 6. URMATORII PASI (detaliati si prioritizati)

Ordinea propusa de mine: (a) si (b) si (f) sunt pe drumul critic spre A1; (c) intareste calitatea HIL; (d) e Faza 2 (post-A1); (e) ruleaza in paralel; (g) e cost mic, oricand.

### (a) [PRIORITATE 1] HIL pe doua masini (PC + RaspberryPi 4B)
Topologie: **M1 = PC** (client bench + `tc netem` + GCS), **M2 = RPi** (echo bench + drone). Link prin LAN/AP Wi-Fi.
Sub-pasi:
1. Mediu IDENTIC pe ambele: ROS 2 Jazzy aceeasi versiune, acelasi workspace `~/ros2_ws`, `colcon build` + `source install/setup.bash` in fiecare terminal nou, acelasi `ROS_DOMAIN_ID` exportat (ex. 7). Pe M1: `sudo -v` (netem cere privilegii).
2. Verifica conectivitatea ROS INAINTE de masuratori: talker pe M2 (`ros2 run demo_nodes_cpp talker`), `ros2 topic list` pe M1 trebuie sa arate `/chatter`. Daca discovery esueaza: ROS_DOMAIN_ID identic, firewall, (pt Zenoh) routerul.
3. Netem pe fier: `run_campaign.py --mode hil --iface <iface_real>` aplica `tc netem` pe egress-ul interfetei reale de pe M1 (afla iface cu `ip -br addr`). **Decizie de documentat:** netem pe M1 degradeaza DOAR sensul M1->M2; pentru simetrie aplica aceeasi regula si pe M2 manual. Alegerea (unidirectional vs simetric) DEFINESTE experimentul.
4. Zenoh: ruleaza UN router accesibil ambelor masini SAU (recomandat, fiindca routerul crapa sub pierdere) P2P fara router, ca CycloneDDS. Mediu curat inainte de fiecare rulare: `pkill -f rmw_zenohd; rm -f /dev/shm/*zenoh* /dev/shm/fastrtps_*`.
5. Porneste cu transportul (nu mission): pe M2 echo server; pe M1 `run_campaign.py --mode hil --iface <iface> --layers transport --reps 5 --rmws cyclonedds`, apoi `--rmws zenoh`. Banner `mod: HIL` confirma ca NU se porneste ecou local.
6. Ceas: RTT-ul e masurat round-trip pe M1, deci NU cere sincronizare. chrony/PTP DOAR daca masori latenta e2e telemetrie cross-masina (de notat atunci).
7. Paritate model: foloseste ACELEASI `bench_core.CONDITIONS` ca SIL; **EXCLUDE conditiile `*_burst`/gilbert_*** pe HIL (netem corelat nu pastreaza media -> invalid pentru gemodel direct; vezi (c) pentru calibrare separata).
**Criteriu de gata:** campanie HIL transport completa pentru ambele RMW la N>=5, `analyze_campaign.py` ruleaza fara modificare, tabel SIL vs HIL etichetat clar, comparatia Zenoh-vs-CycloneDDS afirmata cu variabilitate (interval/CV), nu medii punctuale.

### (b) [PRIORITATE 1] Campanie reala N>=5 cu conditii loss_* si gilbert_*
Sub-pasi:
1. Ruleaza `--reps 5` pe `run_campaign.py` (NU bucla externa cu `--reps 1` -- ar suprascrie rep1 -> N=1). Declara N explicit, >= cel din SIL.
2. Conditii `loss_*` si `lat200_*` pe HIL direct. Conditia-cheie a articolului: **lat200_l15** (legatura de dezastru realista: releu departat + interferenta).
3. Conditiile `gilbert_*` se ruleaza DOAR dupa calibrarea de la (c) -- altfel netem gemodel pe fier nu corespunde modelului SIL.
4. Pentru Zenoh raporteaza interval + CV (CV mare 50-100%), nu o singura cifra.
**Criteriu de gata:** `selector_dataset.csv` regenerat din campania HIL (loss masurat, N>=5), selectorul re-evaluat sub LOCO, regret recalculat pe date reale.

### (c) [PRIORITATE 2] Calibrarea parametrilor Gilbert pe trace radio real
Sub-pasi:
1. Mers pe jos cu drona/statie, masori la 10/20/40/80 m: RSSI + pierderea (sonda `latency_probe`).
2. Din secventa de pierdere/recuperare estimeaza p (good->bad) si r (bad->good) si lungimea medie a rafalei; potriveste exponentul log-distance + umbrirea, salveaza ca profil nou (`campus_real`).
3. Inlocuieste p,r SINTETICE (0.05/0.0667/0.0857, r=0.2) cu valorile estimate; re-genereaza `to_netem_gemodel`.
4. Re-ruleaza campania M neschimbata pe profilul calibrat.
**Criteriu de gata:** `gilbert_*` au p,r derivate dintr-un trace masurat (nu sweep sintetic); `5.6x` inlocuit cu un raport burst/memoryless calibrat; declarat in articol ca amenintare-la-validitate rezolvata.

### (d) [PRIORITATE 3, FAZA 2 post-A1] Co-canal Faza 2 -- legarea cochannel_sinr de radio_link
Sub-pasi:
1. Decide unde se conecteaza: `cochannel_sinr` -> degradare in `LinkState` (probabil mapezi SINR scazut la crestere de loss/burst).
2. Integreaza in lant (acum e doar in core+test): rf_channel_node sau netem_core consuma interference_db.
3. Adauga selftest pentru lantul integrat (acum doar functia pura e testata).
**Criteriu de gata:** grep gaseste `cochannel_sinr` folosit in pipeline, nu doar in test; un selftest acopera efectul co-canal asupra LinkState. NU intra in A1.

### (e) [PARALEL] Finalizarea articolului A1
Stare: schelet DRAFT, cifre PROVIZORII SIL/loopback N=10. Titlu draft: "Selectia middleware-ului ROS 2 sub degradare controlata de retea: un benchmark CycloneDDS vs Zenoh si limitele unui selector invatat". Conferinta: SSRR 2026 (in README, nu in .tex).
Sectiuni PREZENTE: Abstract (schelet), Introducere (completa, 4 contributii), Metodologie (completa), Configuratie experimentala (partial, TODO hardware/versiuni/payload), Rezultate PROVIZORII (transport 17/24 CycloneDDS, regret 142 ms vs 1143 ms; selector 1-NN 66.7%/regret 558 ms NU bate always-CycloneDDS; lossaware D=5000 ms 1-NN 104 ms bate 188 ms; PDIA R^2=0.90, acc 0.94), Discutie (4 limitari), Concluzii.
Ce LIPSESTE:
1. Sectiunea **Lucrari conexe** goala (doar TODO).
2. **references.bib** = SEED, TOATE intrarile placeholder comentate (TODO_ros2, TODO_dds_qos, TODO_zenoh, TODO_netem, TODO_selection_regret, TODO_sar_teleop). NICIO citare reala, niciun `\cite{}` activ.
3. **Figuri:** `paper/figs/` contine doar `.gitkeep`. main.tex are `\includegraphics` comentate, inlocuite cu `\fbox{TODO}` pentru fig_transport.pdf si selector_regret.pdf. Figurile exista generate in alte locuri (`docs/`, `analysis/`) dar NU copiate in figs/. Figuri-tinta: Fig.2 fig_transport (RTT p95 per conditie/RMW), Fig.3 fig_mission (timp misiune), Fig.4 fig_cdf (CDF RTT).
4. Afiliere autor = TODO; proza finala per sectiune; configuratie experimentala (hardware, versiuni Jazzy, payload).
5. Cifrele PROVIZORII trebuie inlocuite cu HIL N>=5 inainte de submisie.
**Ipoteze de testat (H1-H4, marcate "derivate ONEST din SIL"; NU sunt etichetate ca atare in .tex):** H1 CycloneDDS = coada mai mica si mai predictibila; H2 (negativ) selectorul de control NU bate always-CycloneDDS sub LOCO; H3 sub obiectiv loss-aware politica optima e DEPENDENTA DE DEADLINE; H4 (de testat) la stratul de misiune alegerea rmw afecteaza timpul de misiune (date in curs, infrastructura construita, date reale inca inexistente).
**Criteriu de gata:** toate cifrele HIL, figuri reale in figs/, bib cu citari reale, Lucrari conexe scrisa, comparatie SIL vs HIL explicita.

### (f) [PRIORITATE 1, cuplat cu (b)] Validarea modelului de cost al selectorului (D, forma)
Sub-pasi:
1. Sweep fin pe D (nu doar 1000/5000 ms): gaseste pragul D* unde selectorul incepe sa bata always-CycloneDDS.
2. Justifica D din aplicatie (deadline de control de siguranta real), nu ales arbitrar.
3. Testeaza forme alternative de cost (de ce liniar `(1-loss)*RTT + loss*D`?).
**Criteriu de gata:** D* raportat cu interpretare fizica; concluzia "dependenta de deadline" sustinuta de un sweep, nu de doua puncte.

### (g) [COST MIC, oricand] Verificarea vizuala a celor 3 HMI
Sub-pasi: porneste mediu cu ecran (sau X virtual), ruleaza dashboard_node, fault_panel, operator_panel_node, campaign_panel; verifica layout-ul, ca datele se afiseaza, ca panourile nu crapa.
**Criteriu de gata:** screenshot al fiecarui HMI cu date reale; dashboard cu RF status verde/galben/rosu; fault_panel injecteaza burst_len/interf_db si dashboard reactioneaza.

---

## 7. INTREBARI / DECIZII DESCHISE PENTRU CLAUDE CHAT

1. **Structura campaniei HIL:** ce ORDINE de rulare minimizeaza riscul (intai transport ambele RMW la toate conditiile, apoi reluare? sau conditie-cu-conditie ambele RMW)? Cum gestionez timpul (campanie de noapte cu systemd-inhibit)?
2. **Netem unidirectional vs simetric:** pentru o teza despre teleoperare (comanda sus + telemetrie jos), care alegere e mai defensabila stiintific? Daca simetric, cum sincronizez regulile pe M1 si M2 fara drift?
3. **Trace radio pentru calibrare Gilbert:** ce protocol de masurare recomanzi (distante, numar de treceri, durata per punct) ca sa obtin un estimator stabil pentru p si r? Pot estima Gilbert-Elliott din pierderi observate fara echipament radio scump?
4. **Pozitionarea contributiei de interferenta in articol:** burst-ul (gilbert_*) intra in A1 ca amenintare-la-validitate + extensie, sau il pastrez pentru A3 (canal real)? Co-canal e clar Faza 2 -- dar mention in A1?
5. **Modelul de cost al selectorului:** e onest sa raportez un rezultat "dependent de deadline" ca rezultat principal, sau il pozitionez ca rezultat negativ nuantat (selectorul invatat nu se justifica in regimul tipic)? Cum evit sa para ca am ales D ca sa "fac selectorul sa castige"?
6. **Ordinea optima a pasilor:** dat fiind bugetul 5-10 h/sapt si un singur track de cod activ o data, e corect sa pun HIL (a+b+f) inaintea finalizarii prozei A1, sau scriu proza pe cifre provizorii si o actualizez? Care minimizeaza riscul de deadline SSRR?
7. **Riscuri:** care sunt capcanele cele mai probabile la HIL (discovery DDS filtrat de "client isolation" pe AP, router Zenoh care crapa sub pierdere, stare reziduala /dev/shm)? Ce checklist de pre-flight reduce cel mai mult timpul pierdut?
8. **C2 nedefinit:** C2 nu e mapat pe un pachet. Merita sa-l definesc acum (canal spatial/real?) ca sa am C1-C4 coerente in introducerea tezei, sau il las pentru A3? Cum il formulez fara sa par ca umplu un gol?

---

## 8. ANEXA -- comenzi de verificare rapida

**Selftest-uri pe nuclee pure (rezultate ultima rulare live):**
```
python3 sar_plugins/rf_interference.py                  # PASS
python3 sar_plugins/test_rf_interference.py             # 14/14 PASS
python3 sar_swarm/test_burst_channel.py                 # PASS (burst 7.96 vs memoryless 1.43)
python3 c1_benchmark/test_bench_core.py                 # 13/13 PASS
python3 c1_benchmark/test_selector_core.py              # 37/37 PASS
python3 link_adaptive/link_adaptive/link_adaptive_core.py --selftest   # 26/26 PASS
python3 joint_emulator/test_joint_core.py               # 38/38 PASS
```

**Smoke test agregat:** `smoke_all` -> **11 ok / 0 fail**.

**Reproducerea selectorului:**
```
python3 c1_benchmark/build_selector_dataset.py <campanie> -o selector_dataset.csv
python3 c1_benchmark/reproduce_selector.py --objective control --selftest
python3 c1_benchmark/reproduce_selector.py --objective lossaware --penalty 5000
```

**Campanie (SIL vs HIL, schema identica):**
```
python3 c1_benchmark/run_campaign.py --mode sil --reps 5                          # loopback
python3 c1_benchmark/run_campaign.py --mode hil --iface <iface> --layers transport --reps 5 --rmws cyclonedds
python3 c1_benchmark/analyze_campaign.py    # -> campaign_summary.csv + fig_transport/fig_mission/fig_cdf
```

**Documente de referinta in repo:** `c1_benchmark/HIL_RUNBOOK.md`, `c1_benchmark/NOTA_METODOLOGICA_C1.md`, `c1_benchmark/paper/experimental_protocol.md`, `c1_benchmark/paper/main.tex`, `GHID_INTERFERENTA_RF.md`, `ROADMAP_DEZVOLTARE.md`, `PARAMETRI_SI_TRANSFER_REAL.md`.

**Cod pe GitHub:** alexandru-tech-web/ROS2 (workspace `ros2_ws/src`).

---

*Nota de onestitate inclusa in brief: toate cifrele sunt SIL/loopback (N=10 sau N=1), PROVIZORII; parametrii gilbert_* sunt sintetici, necalibrati; co-canal neintegrat (Faza 2); GUI-urile (3 HMI cu rclpy/tkinter) neverificate vizual; nodurile ROS doar py_compile, nerulate cu ROS pornit. Inainte de submisia A1: HIL pe doua masini, N>=5, parametri calibrati pe trace real.*
