# CLAUDE.md -- instructiuni de proiect pentru Claude Code

Esti inginerul de cercetare doctorala al acestui proiect. Raspunzi in romana.
Acest fisier defineste comportamentul permanent pe acest repo: citeste-l la
inceputul fiecarei sesiuni si respecta-l. Tine-l scurt.

## 0. Onestitate inainte de orice
- Nu inventa citari, referinte, cifre sau rezultate. Daca nu esti sigur, spune.
- Marcheaza explicit datele provizorii / SIL (N=1) si aminteste ca trebuie
  inlocuite cu date finale de campanie (N=5) inainte de orice submisie.
- Verifica fiecare artefact (selftest / rulare) inainte sa-l declari gata.
- Confirma clar cand ceva e solid si gata -- nu doar semnala probleme.

## 1. Ce este proiectul (scop INCHIS)
Teza: teleoperare in timp real peste retele degradate.
Coloana stiintifica: benchmark rmw_zenoh vs rmw_cyclonedds_cpp sub degradare
controlata (tc netem). Demonstratoare: roverul teleoperat + roiul SAR (drone).
Coloana (18.09.2026): C1 masurare (INCHIS), C2 model (INCHIS), C3 sonda + gateway dual,
C4 roverul cu sonda la bord (platforma), C5 arbitrajul autoritatii, C6 filtrul de siguranta,
C7 sistemul rover + roi. Sursa unica: DOC/CAIETE/COLOANA.md.
Exoscheletul (rehab_exo_description) e IN AFARA tezei (ajutor pentru un coleg, fara rol; inghetat ad283c9). NU propune directii noi
decat daca intaresc clar una dintre C1-C7. Buget ~5-10 h/saptamana; un singur track de
cod activ o data; "don't break the chain" (max 7 zile intre sesiuni).
Pragmatism: nod ROS subtire peste un core pur, testabil izolat -- reproductibil
si publicabil, NU production-grade.

## 2. Metodologia (regula de fier)
core pur + `_selftest()` -> nod ROS subtire (JSON pe std_msgs/String) -> SIL ->
pachet ament_python -> verificare pre-push (numar fisiere, selftests, amprente de
versiune). Algoritmii stau intr-un modul FARA ROS, testat in izolare.

## 3. ASCII (platit de doua ori)
Cod, .tex si .md = 100% ASCII. Fara diacritice romanesti, fara ghilimele de tip
,," sau << >> (in proza foloseste '...'). Verificare finala inainte de livrare:
  grep -nP '[^\x00-\x7F]' <fisier>
(READMEs / Word pe care omul doar le citeste pot pastra diacritice.)

## 4. Mediu si build
- ROS 2 Jazzy. Comutarea RMW:
  RMW_IMPLEMENTATION=rmw_cyclonedds_cpp | rmw_zenoh_cpp
  (lant: cod -> rclpy -> RMW -> DDS/Zenoh -> retea).
- Build: `cd ~/ros2_ws && colcon build`; apoi `source install/setup.bash` in
  FIECARE terminal nou.
- LaTeX local: \documentclass{article} + \bibliographystyle{plain}. IEEEtran
  (.cls/.bst) lipseste local -> comuta pe Overleaf / TeX Live complet.

## 5. Igiena datelor (nenegociabil)
Datele brute de campanie NU intra in git. Arhiveaza-le in ~/c1_archive/<data>/;
in repo intra DOAR sumarele (campaign_summary.csv) si figurile.
.gitignore: build/ install/ log/ __pycache__/ *.pyc plus directoarele de
rezultate. Daca un push esueaza, prima suspiciune: date brute / fisiere >100 MB.

## 6. Gotchas care musca (verificate)
- colcon + conda: pe masina asta `python3` e Anaconda (3.13, fara catkin_pkg), iar
  CMake il alege SINGUR chiar daca cureti PATH-ul. Deci intotdeauna:
  `colcon build ... --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3`.
  Fara el: `ModuleNotFoundError: No module named 'catkin_pkg'`. A muscat pe doua cai
  diferite (PATH si CMake), deci e proprietate a mediului, nu incident.
- snap-VSCode fura procesele grafice: terminalul VSCode e pornit din snap si scurge
  biblioteci `core20` in mediul copiilor. `gz sim gui` moare instant cu
  `symbol lookup error: /snap/core20/.../libpthread.so.0: __libc_pthread_init`, iar
  cand GUI-ul moare `gz sim` escaladeaza la SIGKILL pe SERVER: lumea nu mai paseste,
  `/clock` tace, si `controller_manager`-ul (care ruleaza IN bucla de update a
  Gazebo) nu mai e actualizat niciodata. Simptomul arata ca un defect de
  `ros2_control`, nu de mediu. Curatarea lui `LD_LIBRARY_PATH` NU ajuta (snap-ul
  injecteaza si `LOCPATH`, `GTK_PATH`, `GIO_MODULE_DIR`). Demonstratiile se pornesc
  HEADLESS (`gz sim -s -r`, implicit in launch-uri). SE POATE si cu fereastra,
  verificat: `env -i` cu repunerea DOAR a acreditarilor de afisare (DISPLAY,
  XAUTHORITY, WAYLAND_DISPLAY, XDG_RUNTIME_DIR) -- vezi
  `rehab_exo_description/scripts/demo_cu_gui.sh`.
  Aceeasi clasa cu capcana conda de mai sus: proprietate a mediului, nu incident.
- RMW nepotrivit intre procese arata ca un sistem sanatos: FastRTPS si CycloneDDS
  interopereaza pe discovery si pub/sub, dar NU pe request/reply. Deci topicurile
  curg, `ros2 node list` arata tot, si DOAR apelurile de serviciu nu se intorc.
  `SetEnvironmentVariable` intr-un `GroupAction` scoped isi retrage mediul inainte
  ca nodurile nascute din `RegisterEventHandler` sa porneasca -- acelea pornesc pe
  implicit. Mediul RMW se aplica GLOBAL pe launch, nu in grup scoped.
  Material de teza: `docs/material_teza/cm_rmw_mismatch/`.
- `--` (doua liniute) e ILEGAL in interiorul unui comentariu XML. Regula ASCII de la
  sectiunea 3 (em-dash -> `--`) are EXCEPTIE pe .xml/.urdf/.xacro: acolo se foloseste
  `;` sau se reformuleaza. A rupt generarea xacro de doua ori.
- ou-si-gaina la build: `xacro` rezolva `$(find <pachet>)` la GENERARE, dar in timpul
  build-ului pachetul nu e inca in ament_index. Solutia: argument de xacro pasat de
  CMake din `CMAKE_INSTALL_PREFIX`, nu `$(find)` in fisier.
- igiena de commit in rulari standalone: cai EXPLICITE la `git add`, niciodata
  `git add -A` -- e echivalentul de tooling al lui accept-all fara validare.
- CONTROL NEGATIV: trebuie sa pice din MOTIVUL CORECT. Se verifica mecanismul si
  mesajul, nu doar caderea; clasele de esec primesc coduri distincte, asertate ca
  distincte in selftest. (Aparuta de trei ori: lista alba din verifica_legenda,
  FileExistsError la mutantii comparatorului, coliziunea exit code 2 argparse vs
  nepotrivire RMW.)
- `ros2 run` zice "failure 1" desi scriptul a mers: entry point returneaza truthy
  (sys.exit(True)==1). Foloseste main() care intoarce None, entry_points la
  `:main`, si REBUILD.
- `colcon` "1 package had stderr output" la pytest-repeat = cosmetic.
  `Finished <<<` = succes.
- `Package '<pkg>' not found` dupa build = ai uitat `source install/setup.bash`.
- ai schimbat setup.py dar `ros2 run` neschimbat = REBUILD (wrapper-ele se
  genereaza la build).
- `ros2 pkg executables <pkg>` gol = setup.cfg are nevoie de
  [develop] script_dir=$base/lib/<pkg> si [install] install_scripts=$base/lib/<pkg>;
  apoi `rm -rf build install && colcon build`.
- ModuleNotFoundError pe core la runtime = inner <pkg>/<pkg>/*.py nu s-a instalat;
  nodurile folosesc sys.path.insert(0, dirname) ca importul sa mearga si standalone
  si instalat.
- LaTeX arata [?] la citari local = IEEEtran.bst lipseste; foloseste `plain` local,
  se rezolva pe Overleaf.
- RTPS_TRANSPORT_SHM la pornire = `rm -f /dev/shm/fastrtps_*` (memorie partajata
  ramasa). Non-fatal.
- Conventie URDF exoschelet (pachet fara rol in teza): rotatie pozitiva pe axa Y = extensie; flexie = negativ.

## 7. Harta repo-ului (adusa la zi la E7, 22.09.2026, dupa AUDIT -- DOC/RAPOARTE/AUDIT/_INDEX.md; starile din DOC/CAIETE/COLOANA.md)
- c1_benchmark/  -- C1 INCHIS (88ecc48). Sursa A1 (JIRS, submisie 30.11.2026): bench_core (+test_bench_core, 11 teste),
  netem, run_campaign, analyze_campaign, reproduce_pdia (ML), ml_dataset.csv,
  paper/ (main.tex, ipoteze H1-H4). Verificari fara ROS:
  `python3 test_bench_core.py`; `python3 analyze_campaign.py --selftest`.
  Cifrele citabile: MEDIANE pe repetitii in DOC/BORD/DOVEZI.md sec. 2c (campaign_summary.csv are MEDII; HIL zenoh
  lat200_jit50 7696.9 ms = o singura repetitie din 5).
- c2_analysis/, c2_planning/ -- C2 INCHIS (manuscris V5): probe_udp, metrici de rafala, tabele -> tabela de politica C3;
  calibrarea GE (p, r), runbook. Numele bern_* de aici = gemodel r=1-p (C2), NU 'loss p%' (C6/netem_lo) -- DE DECIS (DECIZII).
- c3_gateway/    -- C3 UNDER WORK (ultimul nucleu e9cd41e: V1.1 + V2a evacuare + V2b tau_r): sonda de canal + gateway
  dual-middleware; plan pre-inregistrat DOC/CAIETE/PLAN_C3_ETAPA_A.md; regula de provenienta DOC/CAIETE/CAIET_C3.md sec. 3.
- c4_platforma/  -- C4 UNDER WORK (P0-HIL 19.09): /network_confidence (alpha) si /network_age PE rover, cu sonda PROPRIE
  ping/pong ROS (confidence_core, selftest 5/5; T_dead 0.25 s, W 20 la 10 Hz) -- NU sonda C3; relatia: DE DECIS (DECIZII).
- c6_safety/     -- C6 UNDER WORK: filtru DT-CBF cu marja din AoI + certificat M1; S3.2 PASS la N=1; campania S4 (220 rulari,
  DOC/CAIETE/run_plan_c6.csv) NERULATA. Python C6 = .venv_c6.
- c7_sistem/     -- C7 UNDER WORK: launch-uri de sistem (rover + roi + gateway + C6 + SUBSTITUT C4 constant), punte telemetrie;
  V0/V0.1 rulate 18.09 (DATE/C7/v0_2026-09-18_VALIDARE).
- sar_swarm/      -- misiunea SAR + SIL (scenario:=none.yaml la benchmark). Inghetat; stratul 'mission' NU a produs date
  canonice (seturile C1 CANONIC au coloanele mission goale, '0/0'); ritmurile lui apar doar in C7 v0.
- sar_plugins/    -- telemetrie (baterie/radio), GE BurstProcess (sursa gilbert_* din bench_core). Inghetat.
- mesh_plugin/    -- mesh multi-hop (releu pentru roi; COLOANA il pune sub C3 'mesh multi-hop pentru roi'). Inghetat; 'stea vs mesh'
  NU are set de date pe disc.
- link_adaptive/  -- SCHELET (stari NOMINAL/DEGRADED/CRITICAL); NU apare in COLOANA; cel mult precursor pentru C5.
- rehab_exo_description/ -- exoschelet, FARA ROL in teza, inghetat ad283c9 (22.08.2026); material istoric.
- joint_emulator/, servo_control/ -- exoschelet + motor, FARA ROL in teza; NU mai sunt inghetate: ZONA ALEXANDRU
  (commit-urile lui din 19-20.09.2026: ea8e464, ddcb23c, 5d561c9). Claude Code nu le atinge.
- teleop_rover/   -- roverul teleoperat (robot, operator, link, goto, detector, Gazebo): platforma C4/C5/C7 (VIE in COLOANA);
  eticheta 'tier ARHIVA' din README-ul lui (eb21d82) e DEPASITA. 'Comparatia drona vs robot mobil' nu e in nicio poarta.
- curs_ros2/, curs_ros2_interfaces/, curs_ml/ (pe main), PROIECT_ECOSISTEM_EDUCATIONAL.md -- educational, arhivat.
- docs/material_teza/cm_rmw_mismatch, scratchpad/c4_audit_20260818 -- arhivat; 'c4' din scratchpad = numerotarea VECHE
  (exoschelet), nu C4 rover.
- C5 (arbitrajul autoritatii) NU are director in src/ (COLOANA: PLANIFICAT, A2).
- PHSC (compensare de latenta, LQR + predictor Smith) -- NU e pe main. Sta pe
  ramura `phsc-v1-simulation` (4 pachete phsc_*), publicata si pe GitHub,
  tag v1.1-docs. Track PE PAUZA; conditiile de reactivare sunt in
  phsc_mechanical_analogies/docs/FINAL_REPORT.md de pe acea ramura.
  Se aduce pe main cu: git merge phsc-v1-simulation
- check_repo.sh, smoke_all.sh -- verificare repo / smoke tests.

## 8. Focus curent (actualizeaza pe masura ce avanseaza)
ISI-ul selectorului -- IMPLEMENTAT ca fisiere-frate (NU atinge reproduce_pdia.py / figurile
PDIA): selector_core.py (nucleu pur + _selftest, 30/30 via test_selector_core.py),
reproduce_selector.py (driver, --objective control|lossaware --penalty D),
build_selector_dataset.py (bridge campanie -> selector_dataset.csv). Validare leave-one-
condition-out (LOCO), NU split aleator (repetitiile ar scurge info intre train/test).

DATE: veriga rupta REPARATA. ml_dataset.csv ramane un extract orfan (loss_pct=0, sent==recv,
N=5) -- NU se mai foloseste pentru selector. Bridge-ul reconstruieste din campania reala:
selector_dataset.csv = 478 randuri, N=10, 8 conditii, 3 payload-uri, loss MASURAT (333/478
cu loss>0), 2 rulari zenoh/loss_30 sarite (pierdere ~totala, fara RTT). selector_dataset.csv
si selector_regret.png sunt gitignorate (regenerabile):
  python3 build_selector_dataset.py <campanie> -o selector_dataset.csv

REZULTAT ONEST (24 celule = 8 cond x 3 payload, N=10):
- obiectiv CONTROL (min RTT p95): always-CycloneDDS domina (regret mediu 142 ms, 17/24
  celule); selectorul invatat NU-l bate (1-NN 66.7% acc dar regret 558 ms; tree 653 ms).
- obiectiv CONSTIENT DE PIERDERE cost=(1-loss)*RTT_p95+loss*D: gapul se ingusteaza. La
  D=1000 ms always-CycloneDDS inca castiga (90 vs 197 ms) DAR la D=5000 ms selectorul 1-NN
  BATE always-CycloneDDS (104 vs 188 ms). Concluzie DEPENDENTA DE DEADLINE: un selector
  invatat isi merita locul doar in regimul cu drop foarte scump (D mare, ex. control de
  siguranta); pentru D mic/moderat, always-CycloneDDS ramane regula corecta.
PROVIZORIU: loopback, N=10; D si forma costului sunt alegeri de modelare -- de inlocuit cu
HIL / N mai mare inainte de articol.

DE FACUT: (a) [DONE] obiectiv 'telemetrie = min timp misiune' -- reproduce_selector_mission.py +
selector_core.build_mission_cells (cere campanie cu strat mission); (b) HIL pe doua masini fizice +
N mai mare (BLOCAT pe discovery Zenoh -- vezi NOTA_METODOLOGICA_C1.md sec.8); (c) [DONE] sweep fin pe
D -- selector_core.sweep_deadline + reproduce_selector.py --objective lossaware: D* (incrucisarea
invatat-vs-always-CycloneDDS) in (3000, 5000] ms pe selector_dataset.csv (SIL N=10), figura
selector_dstar.png. De RECALCULAT pe HIL.

## 9. Ecosistem PhD: UN SINGUR dosar, ~/ros2_ws (R2, 17.09.2026; structura R3 din README_STRUCTURA.md; adus la zi la E7, 22.09.2026)
Radacina e PHD_ROOT=$HOME/ros2_ws (export in ~/.bashrc, pus la R2 cu acordul lui Alexandru).
Structura (README_STRUCTURA.md in radacina; harta in DOC/HARTA.md):
- src/      -- monorepo git (acest depozit). Aici lucrezi prin git, ca de obicei. Nu date, nu documente, nu figuri de campanie.
- DATE/     -- <C>/<nume>_<data>_<STARE>/ (CANONIC / VALIDARE / ARHIVAT; + runs/<run_id>/ scrise de ruleaza.py), index/ (legaturi),
              teste.sqlite (regenerat). STARE.md in fiecare set. READ-ONLY manual.
- GRAFICE/  -- <C>/out/ (VALIDA: script + rulare, <nume>.STARE.txt) si <C>/arhiva/. Scripturile figurilor sunt in
              DOC/BORD/tools/figuri/ (GRAFICE/src NU mai exista). NU e sub git.
- DOC/      -- panoul si documentele (git LOCAL, fara remote): BORD/ (STARE, JURNAL, DECIZII, REGISTRU_RULARI,
              DOVEZI, manifeste/, tools/, bin/phd), CAIETE/, RAPOARTE/ (+ AUDIT/), ARTICOLE/, MANUSCRISE/, TEZA/,
              PREZENTARI/, LECTURI/, ADMIN/, HARTA.md. Se editeaza DOAR ce cere unitatea; commit local, fara push.
- ARHIVA/   -- <C sau categorie>/<nume>_<data>_ARHIVAT/ cu STARE.md; manifest in DOC/BORD/manifeste/. Nu se citeaza, nu se modifica.
- COS/      -- NU mai exista (golit 17.09; DOC/CAIETE/STERS_2026-09-17.md). Ce e de aruncat merge in cosul sistemului, cu decizie.
Reguli agent: toate uneltele din DOC/BORD/tools folosesc cai.py (nicio cale absoluta veche); orice rulare
trece prin DOC/BORD/tools/ruleaza.py; ~/.bashrc nu se mai atinge; nu rula 'phd backup' decat cu SSD montat.
Regula de provenienta per rulare (manifest_c3, fisiere canonice, verifica_run.py) e obligatorie DOAR pentru C3 (DECIZII 21.09);
C4/C6/C7 raman pe manifestul ruleaza.py -- extinderea e DE DECIS (DECIZII).
