# joint_emulator — bancul cu 6 servomotoare ABB ca articulatii (C4)

## Ce este
Trei perechi de servomotoare cuplate rigid pe cate un ax. In modelul
schematic Gazebo, cele trei A sunt in STANGA (albastru deschis), iar cele
trei B in DREAPTA (negru). Fiecare cuplaj central are doua flanse
circulare si sase suruburi ilustrative; numarul real ramane de masurat.
In fiecare pereche:
- **motorul A** aplica un cuplu comandat de operator;
- **motorul B** aplica un cuplu opus dupa legea de **impedanta**:
  tau_B = -K*(theta-theta0) - B*omega, limitat la tau_max.

Flansa rigida inseamna UN SINGUR unghi mecanic theta pentru A si B.
Nu comandam simultan pozitii +theta si -theta: drive-urile s-ar lupta
pe acelasi ax. La echilibru, un cuplu A pozitiv produce un cuplu B
negativ, aproximativ egal ca marime. Sensurile brute ale encoderelor
reale se stabilesc doar dupa montaj si calibrare. Geometria este o
schita functionala, nu CAD masurat. Profilurile sold / genunchi /
glezna sunt deocamdata o ipoteza de cercetare pentru cele trei perechi,
nu o identificare confirmata a standului. Confirmarea se face din
documentatia si masuratorile echipamentului real.

## Fisiere (toate fara ROS, rulabile oriunde)
- joint_core.py     legea de impedanta, pacientul virtual (cu "catch"
                    spastic), fizica perechii, DelayLine, EnergyMonitor
                    (pasivitate), SafetyGate (watchdog -> cuplu zero)
- drive_iface.py    contractul unic spre fier + SimBackend (backend-ul
                    real se scrie dupa identificarea drive-urilor)
- test_joint_core.py  verificari, inclusiv demonstratia-cheie:
                    aceeasi lege, stabila la 0 ms, instabila la 60 ms

## REGULILE DE SIGURANTA (inaintea oricarui test pe fier)
1. Motorul B ruleaza NUMAI in mod cuplu (torque). NICIODATA pozitie
   contra pozitie pe ax rigid — oscilatie + supracurent garantate.
2. Limita software de cuplu la <10-15% din nominal la primele teste,
   PLUS limita de curent setata in drive (doua bariere independente).
3. Watchdog pe masura: encoder mut > 100 ms => cuplu zero (testat).
4. Rampa de cuplu activata (fara salturi); E-stop fizic la indemana.
5. Primele teste pe O SINGURA pereche; nimeni cu mana pe cuplaj.

## Planul etapizat
- **L0 (GATA)** nucleul pur + teste — ruleaza oriunde, acum.
- **L1 — identificarea fierului**: modelul drive-urilor decide backend-ul
  (EtherCAT => ros2_control + ethercat_driver; analog +/-10V => alta
  cale). Apoi J si frecarea reale ale perechii dintr-un test de
  coast-down — intra direct in PairSim.
- **L2 — echilibrul pe o pereche reala**: A aplica trepte mici de cuplu,
  B tine echilibrul cu ImpedanceLaw; comparatia masurat vs simulat.
- **L3 — tele-impedanta prin legatura degradata**: masura encoderului
  trece prin DegradedChannel/linkstate (acelasi tipar ca roverul);
  Zenoh vs CycloneDDS PE FIER; apoi pacientul virtual spastic pentru
  articolul de tele-reabilitare (A4). Intrebarea noua de cercetare:
  **impedanta adaptata la calitatea legaturii** (K scade cand latenta
  creste) — masurabila direct pe acest banc.

## Ce lipseste ca sa pornim L1
O poza cu PLACUTA drive-urilor de pe perete (cutiile in care intra
cablurile portocalii de putere si verzi de feedback). Modelul lor
decide tot lantul software.

## Mediul de simulare COMPLET (fara fier, ruleaza acum)
    python3 test_joint_core.py                  # teste nucleu pur
    python3 sil_joint.py echilibru              # treapta + impedanta
    python3 sil_joint.py pacient_spastic        # B = membrul cu catch
    python3 sil_joint.py adaptiv_vs_fix --ms 60 # duelul la 60 ms
    python3 sil_joint.py delay_sweep            # tabelul E vs latenta
    python3 plot_joint.py                       # figurile (figs/*.png)
ROS2 (pe masina cu Jazzy): nodul nodes/emulator_node.py expune perechile
pe /joint/state si primeste /joint/cmd_a, /joint/impedance, /joint/estop;
degradarea masurii se injecteaza pe `/joint/linkstate`. Topic separat de
rover pentru a evita coliziunea dintre schemele JSON.

## LECTIA DE ARHITECTURA (demonstrata in teste si figuri)
Amortizarea pe o viteza intarziata POMPEAZA energie: impedanta
totul-prin-link explodeaza de la ~20-30 ms (E creste la mii de J), iar
inmuierea lui K nu o salveaza. Solutia masurata: **amortizarea LOCALA**
(langa drive) + **rigiditatea adaptiva** prin link — pasiv (E~0) pana la
120 ms, cu pretul corect: articulatia devine mai moale (th=tau/K_ef).
De aceea bucla rapida trebuie sa ramana LANGA banc, iar prin Zenoh/DDS
calatoresc doar referintele si K. Interfata fizica exacta (CAN/CANopen,
EtherCAT, Modbus etc.) ramane necunoscuta pana la identificarea drive-urilor.

## Backend-ul hardware: NEIDENTIFICAT
`modbus_backend.py` este numai un prototip istoric si NU confirma ca
drive-urile ABB folosesc Modbus. O lucrare IMSAR din 2025 descrie o
arhitectura CAN pentru un robot multi-articulatie, dar nici aceasta nu
dovedeste protocolul standului nostru. Backend-ul real se implementeaza
doar dupa modelul complet de pe placuta si manualul oficial.

## Pluginul de encodere: viteza, acceleratie, grafice
- `encoder_core.py` -- cuantizare SIM cu `counts_per_rev` si doi estimatori.
  Filtrul alpha-beta-gamma ramane pentru demonstratia la 1 kHz; nu este
  acordat pentru jurnalul ROS la 20-100 Hz. Nodul ROS foloseste implicit
  `sampled`: pozitia `th` este exact pozitia cuantizata `th_raw`, iar
  viteza/acceleratia sunt derivate discrete netezite cu constante de timp
  de 0.10 s / 0.15 s. Nu se mai poate obtine o depasire fictiva de unghi
  introdusa de filtrul de pozitie. La esantionare rara, varful real de
  viteza dintre doua mostre poate totusi sa nu fie observat; cresterea
  la 100 Hz imbunatateste observabilitatea, nu o garanteaza.
- nodes/encoder_monitor_node.py — sub /joint/state -> pub
  /joint/kinematics {th, om, acc, om_raw} + CSV cu timestamp in
  `/home/ubuntu/Analiza_Teza/ViPRO/DATE/encoders_<session_id>.csv`.
  Publica separat `/joint/motor_kinematics`: sase canale A0/B0,
  A1/B1, A2/B2 si diferenta A-B pe fiecare pereche. Scrie si
  `/home/ubuntu/Analiza_Teza/ViPRO/DATE/motor_encoders_<session_id>.csv`.
  In prezent nodul citeste numai date SIM. Parametrul `quantize_cpr:=0`
  este prevazut pentru o viitoare pozitie deja cuantizata de drive,
  dupa documentarea interfetei reale. Parametrii `estimator_kind`,
  `velocity_tau_s`, `acceleration_tau_s` se salveaza in `encoder_config`.
- plot_encoder.py — graficele de iesire: encoder_traces.png (th/om/acc)
  si encoder_filter.png (brut vs filtrat). Fara argument = demo local;
  cu argument = un CSV al nodului, de exemplu:
  `python3 plot_encoder.py ~/sar_data/encoders_20260918_225000.csv`
ATENTIE pe fier: `om_raw` este acum derivata pozitiei cuantizate, nu un
registru de viteza al drive-ului. Daca drive-ul expune viteza, acea
cale trebuie implementata si validata separat. Niciunul dintre aceste
CSV-uri nu contine masuratori ABB.

## Protocol SIL repetabil pe o singura pereche

Din directorul proiectului, fara ROS/Gazebo si fara hardware:

    /usr/bin/python3 vipro_experiment.py reference --data-dir /home/ubuntu/Analiza_Teza/ViPRO/DATE

Implicit aplica o singura treapta de `+0.24 Nm` pe A0 intre `t=1` si
`t=3 s`; A1/A2 raman la zero, B0 aplica impedanta fixa (`K=20 Nm/rad`,
`B=0.8 Nms/rad`) si simularea se incheie la `t=4 s`. Jurnalizarea este
la 100 Hz, fizica la 2 kHz. Se creeaza un `session_id` nou si fisierele
`session_*_states.csv`, `*_events.csv`, `motor_encoders_*.csv`,
`encoders_*.csv`, `*_analysis.json`, `*_pair0_plot.png` si `*_export_*.xlsx`.
Nu suprascrie o sesiune existenta. Pentru alta treapta sau rata:

    /usr/bin/python3 vipro_experiment.py reference --data-dir /home/ubuntu/Analiza_Teza/ViPRO/DATE --tau 0.3 --sample-hz 100

Raportul include unghiul final si cel asteptat `theta0 + tau_A/K`,
timpul de crestere 10-90%, stabilizarea in banda de 2%, depasirea,
cuplul B comandat la echilibru, miscarea maxima a perechilor 1/2,
diferenta encoder A-B si eroarea vitezei estimate fata de axul SIM
esantionat. Rigiditatea aparenta este calculata din cuplul COMANDAT,
nu masurata. Cuplurile si encoderele sunt 100% simulate.

Pentru o sesiune ROS deja inregistrata si incheiata:

    /usr/bin/python3 vipro_experiment.py analyze ID_SESIUNE --data-dir /home/ubuntu/Analiza_Teza/ViPRO/DATE
    /usr/bin/python3 vipro_experiment.py plot ID_SESIUNE --data-dir /home/ubuntu/Analiza_Teza/ViPRO/DATE

`analyze` afiseaza JSON fara a modifica datele (sau scrie intr-un
fisier nou cu `--output cale.json`). Alege ultima comanda A nenula a
perechii 0, implicit; `--pair 1` si `--event-index 0` selecteaza alta
pereche/treapta. Se recomanda analiza dupa oprirea sesiunii, cand CSV-ul
este complet. `plot` scrie un PNG nou si refuza suprascrierea.

Pentru experimentul manual in Gazebo/HMI, lansarea completa jurnalizeaza
implicit la `state_hz:=100.0` (anterior 20 Hz):

    ros2 launch launch/full_sim.launch.py state_hz:=100.0

Rata mai mare mareste fisierele: Excel permite maximum 1.048.576
randuri/foaie; CSV-urile raman sursa primara pentru rulari lungi.

## Suita automata SIL: 12 trepte predefinite

Aceasta comanda functioneaza si din directorul `~`, fara ROS/Gazebo si
fara nicio conexiune cu motoarele ABB:

    /usr/bin/python3 /home/ubuntu/ros2_ws/src/joint_emulator/vipro_experiment.py suite --data-dir /home/ubuntu/Analiza_Teza/ViPRO/DATE

Suita aplica pe rand, pe fiecare dintre A0, A1 si A2, cuplurile
`+0.25`, `-0.25`, `+0.5`, `-0.5 Nm`. Fiecare treapta dureaza 1 s, apoi
comanda revine la zero timp de 0.6 s; nu comanda simultan doua perechi.
K=20 Nm/rad si B=0.8 Nms/rad sunt fixe implicit. Cuplul B este
calculat local prin legea de impedanta si se opune lui A.

Se creeaza un singur `session_id`, cu CSV-uri complete si un Excel cu
foaia suplimentara `Suita` (12 randuri: unul pentru fiecare caz), un
JSON cu toate criteriile PASS/FAIL si o figura PNG cu trei randuri
(cate unul pe pereche). Comanda afiseaza `Teste: 12/12 trecute` daca
toate criteriile modelului sunt indeplinite. Codul de iesire este 1
daca un caz esueaza; artefactele raman salvate pentru investigatie.

Sunt verificate: unghiul final fata de `tau_A/K`, cuplul B opus,
izolarea perechilor necomandate, concordanta encoderelor A/B pe axul
rigid, stabilizarea in intervalul treptei si revenirea la zero in pauza.
Pragurile sunt criterii de regresie ale SIM, NU limite de siguranta
certificate pentru bancul ABB. Pentru alte amplitudini in simulare:

    /usr/bin/python3 /home/ubuntu/ros2_ws/src/joint_emulator/vipro_experiment.py suite --data-dir /home/ubuntu/Analiza_Teza/ViPRO/DATE --levels 0.2 0.4 --k 10

Suita de mai sus este offline si nu misca Gazebo. Pentru observarea
aceleiasi secvente in Gazebo, foloseste DOUA terminale. In primul:

    cd /home/ubuntu/ros2_ws/src/joint_emulator
    source /opt/ros/jazzy/setup.bash
    ros2 launch launch/full_sim.launch.py

In HMI, pune toate A la zero si asteapta oprirea axelor. Optional,
seteaza `K=2 Nm/rad`, `B=0.8 Nms/rad`, `link=0 ms` pentru o rotatie
mai vizibila; scriptul va afisa K efectiv citit din simulator. In al
doilea terminal:

    source /opt/ros/jazzy/setup.bash
    /usr/bin/python3 /home/ubuntu/ros2_ws/src/joint_emulator/nodes/suite_player_node.py

Nu actiona sliderele in timpul secventei. Playerul verifica `source=sim`
pentru toate motoarele, absenta ESTOP, modul impedanta, comenzi A initial
zero, viteze initiale mici, telemetrie proaspata si confirmarea fiecarei
comenzi. La final, `Ctrl+C` sau eroare trimite A=0 de trei ori pe fiecare
pereche. Nu poate garanta zero dupa `SIGKILL`, cadere de alimentare sau
defect de retea; ramane STRICT pentru emulator SIM. Dupa terminare,
apasa `Export Excel` in HMI. Playerul vizual NU emite verdictul PASS/FAIL:
acela este calculat numai de suita offline reproductibila.

## Vizualizare (RViz + Gazebo) si panoul operatorului
Varianta recomandata porneste totul si deschide doua ferestre: Gazebo si
panoul operatorului (slidere + grafice):

    source /opt/ros/jazzy/setup.bash
    ros2 launch launch/full_sim.launch.py

Inchiderea Gazebo sau `Ctrl+C` in terminal opreste toate componentele.

Panoul este impartit in TREI coloane: (1) comenzi A cu slider si camp
numeric exact in Nm pentru fiecare pereche, plus K/B/link/ESTOP; (2)
grafice A: cuplu comandat, encoder A si viteza A; (3) grafice B: cuplu
de reactie comandat, encoder B si viteza B. Exista sase canale SIM
separate, dar unghiurile A/B coincid in modelul rigid ideal; diferenta
A-B apare in randul de stare si in CSV ca diagnostic. Acestea NU sunt
inca encoderele fizice ABB. Campurile numerice accepta numai valori finite intre
-2 si +2 Nm; apasa Enter pentru aplicare.

Bucla ROS ruleaza implicit la 200 Hz, iar emulatorul face 10 subpasi
interni de fizica si control la 2 kHz pentru stabilitate numerica. Un
mod demonstrativ de contact virtual bilateral se porneste separat:

    ros2 launch launch/full_sim.launch.py reaction_mode:=contact contact_angle_deg:=5.0

In acest mod B nu opune cuplu in intervalul liber +/-5 grade; dupa
atingerea pragului aplica un arc/amortizor virtual limitat la tau_max.
K si B raman reglabile in HMI. Reactia de contact este locala, deci
sliderul de link nu o intarzie. Este un opritor virtual de cercetare,
nu un model identificat al unei articulatii sau al unui obiect real.
Modul implicit ramane `reaction_mode:=impedance`.

Cuplurile sunt calculate/comandate, NU masuratori reale de forta. `K`
poate reprezenta rigiditatea virtuala a unui obiect, dar nu exista inca
detectie de contact sau identificare automata a obiectului. Acesta este
pasul de cercetare urmator, dupa fotografii, senzori si masuratori ale
standului.

Pentru rotatie vizibila: `link=0 ms`, `K=2 Nm/rad`, `B=0.8 Nms/rad`,
apoi `tau_A p0=0.5 Nm` (crestere lenta). Unghiul final aproximativ
`0.25 rad = 14 grade` apare si in randul de stare al panoului. La `K=16.4` si
`tau_A=0.92` unghiul este numai `3.2 grade`. Cele doua dungi rosii
subtiri sunt pe fetele flansei rotitoare. Nu amplificam artificial
miscarea din Gazebo: acesta trebuie sa urmareasca unghiul calculat.

`ESTOP` dezarmeaza ambele motoare SIM. `RESET ESTOP` permite rearmarea
fara repornire doar dupa ce toate axele scad sub `0.05 rad/s` si linkul
encoderului este disponibil. A ramane la cuplu zero, iar B foloseste
pozitia curenta ca nou punct neutru; nu exista salt de pozitie sau
recuperare automata a comenzii vechi. Daca resetul este refuzat, motivul
apare in panou si in terminal. Acest reset este NUMAI pentru simulare;
pe hardware trebuie o procedura independenta validata.

`Export Excel` face o fotografie `.xlsx` a intregii sesiuni, de la
`t=0` pana la momentul apasarii butonului. Graficele pastreaza numai
~30 s pentru afisare, dar jurnalele CSV sunt scrise continuu pe disc;
nu pierdem tranzientul initial. Toate fisierele unei lansari au acelasi
`session_id` si se gasesc implicit in
`/home/ubuntu/Analiza_Teza/ViPRO/DATE/`. Argumentul
`data_dir:=/calea/dorita` schimba locatia. Un export nou creeaza un
fisier nou; CSV-urile continua sa creasca dupa export. Cu `hmi:=false`,
jurnalele tot se scriu, iar Excel se poate crea ulterior din CSV-uri:

    /usr/bin/python3 session_export.py <session_id>

Foile Excel sunt `Stare` (3 perechi: unghi/viteza SIM, cuplu A si B
comandat, K/B setate si efective, referinta theta0, link, energie,
ESTOP), `Encodere_6` (A0/B0, A1/B1, A2/B2: counts, unghi brut si
filtrat, viteza/acceleratie), `Axe_3`, `Evenimente` (comenzi, schimbari
de K/B/link, ESTOP si reset) si `Info` (semnificatia campurilor).
Fiecare rand de date are `time_s`/`t_s` (timpul simularii) si
`time_utc` (timestamp de ceas real, UTC ISO 8601). Cuplurile sunt
COMANDATE/CALCULATE, nu masurate pe motoarele ABB. `th_raw` este
encoderul SIM cuantizat; in modul implicit `th` este aceeasi citire,
iar `om` este o estimare filtrata, nu o masuratoare independenta.
Identificarea rigiditatii reale
necesita ulterior senzori/telemetrie de cuplu sau curent, date despre
reductor, calibrarea encoderelor si masurarea unui obiect de contact.
Excel are limita de 1.048.576 randuri pe foaie; la sesiuni foarte lungi,
foloseste CSV-urile brute sau imparte analiza in intervale. Datele CSV
nu sunt sterse daca exportul Excel nu incape intr-o foaie.

Matricea de terminale (toate cu `source /opt/ros/jazzy/setup.bash`,
din `~/ros2_ws/src/joint_emulator`). Folosim `/usr/bin/python3` pentru
nodurile ROS deoarece Python-ul din Miniconda nu este compatibil cu
instalarea ROS Jazzy de pe aceasta masina:

| T | Comanda | Rol |
|---|---|---|
| 1 | `/usr/bin/python3 nodes/emulator_node.py --ros-args -p adaptive:=true` | fizica perechilor |
| 2 | `/usr/bin/python3 nodes/encoder_monitor_node.py` | viteza/accel din encodere + CSV |
| 3 | `ros2 launch launch/viz_rviz.launch.py` | RViz: bancul se misca (marcaj rosu pe flansa) |
| 4 | `/usr/bin/python3 nodes/operator_panel_node.py` | PANOUL: comenzi A, grafice A, grafice B in 3 coloane |

Pentru exportul Excel complet, foloseste `full_sim.launch.py`: acesta da
acelasi `session_id` emulatorului, monitorului si panoului. La pornire
manuala separata, paseaza explicit acelasi `-p session_id:=NUME_UNIC` celor
trei noduri, altfel panoul nu poate identifica jurnalele aceleiasi sesiuni.

Gazebo (oglinda vizuala, optional — fizica ramane in emulator):
| T | Comanda |
|---|---|
| 5 | `gz sim -r gz/joint_bench_world.sdf` |
| 6 | `ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=gz/bridge_bench.yaml` |
| 7 | `/usr/bin/python3 nodes/gz_mirror_node.py` |

Verificari: in RViz, Fixed Frame = base_link; daca modelul nu apare,
adauga manual RobotModel cu Description Topic = /robot_description.
In gz: `gz topic -l | grep cmd_pos` trebuie sa arate cele 3 topicuri.
Decizie de arhitectura: Gazebo e OGLINDA (JointPositionController
urmareste pozitia emulatorului/fierului), nu a doua fizica — o singura
sursa de adevar, aceleasi noduri peste sim si peste banc.
