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
ISI-ul selectorului: ridica analiza ML de la *caracterizator* la *selector*.
Acum reproduce_pdia.py foloseste X = [severitate, log_payload] si ARUNCA `rmw` ->
nu alege middleware, doar prezice "utilizabil / RTT". De facut, ca FISIER-FRATE
(NU atinge reproduce_pdia.py si figurile PDIA):
  - feature-uri: rmw + parametri netem reali (loss %, latenta ms, jitter ms) +
    log_payload;
  - eticheta: care rmw castiga per (cond x payload) per obiectiv
    (control = min RTT p95; telemetrie = min timp misiune);
  - validare leave-one-condition-out (NU split aleator -- repetitiile scurg si dau
    scoruri optimiste);
  - raporteaza acuratete + REGRET fata de always-zenoh / always-cyclonedds / oracol.
Fapt din date reale: castigatorul se schimba cu payload-ul in interiorul aceleiasi
conditii (cyclonedds 10/18 celule, zenoh 8/18) -- exista interactiune conditie x
payload, deci o regula globala greseste in ~40% din celule.
Provenance de verificat: ml_dataset.csv are loss_pct = 0 pe randurile agregate, vs
pierderile din c1_benchmark/README.md sectiunea 6 -- clarifica ce masoara coloana
inainte sa intre in articol.
