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
controlata (tc netem). Demonstratoare: roi SAR (drone) + exoschelet rehab.
Patru contributii C1-C4, harta de articole A1-A5. NU propune directii noi decat
daca intaresc clar una dintre C1-C4. Buget ~5-10 h/saptamana; un singur track de
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
- Conventie URDF exoschelet: rotatie pozitiva pe axa Y = extensie; flexie = negativ.

## 7. Harta repo-ului
- c1_benchmark/  -- sursa A1 (SSRR 2026): bench_core (+test_bench_core, 11 teste),
  netem, run_campaign, analyze_campaign, reproduce_pdia (ML), ml_dataset.csv,
  paper/ (main.tex, ipoteze H1-H4). Verificari fara ROS:
  `python3 test_bench_core.py`; `python3 analyze_campaign.py --selftest`.
- sar_swarm/      -- misiunea SAR + SIL (scenario:=none.yaml la benchmark).
- sar_plugins/    -- telemetrie (baterie/radio).
- mesh_plugin/    -- mesh multi-hop (C3).
- link_adaptive/  -- adaptare / selector link-aware (C3).
- rehab_exo_description/, servo_control/, joint_emulator/ -- exoschelet + motor (C4).
- teleop_rover/   -- robot mobil (comparatie drona vs robot mobil).
- curs_ros2/, curs_ros2_interfaces/, PROIECT_ECOSISTEM_EDUCATIONAL.md -- educational.
- gen_articol/    -- generare schelete de articol.
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
