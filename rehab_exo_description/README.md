# rehab_exo_description

Descrierea robotului de reabilitare LLR (demonstratorul C4 al tezei): scaun medical
+ doua picioare mecanice, 6 articulatii revolute active in plan sagital
(sold/genunchi/glezna x2) plus 5 axe prismatice de pozitionare, cu configurare
ros2_control, scripturi de control si lansari pentru RViz si Gazebo.
Model de dezvoltare/simulare, NU controller medical certificat.

## O SINGURA SURSA DE ADEVAR

`urdf/rehab_exo.urdf.xacro` este SINGURA descriere. URDF-ul e ARTEFACT generat la
build si instalat in `share/rehab_exo_description/urdf/rehab_exo.urdf`. Nu se
editeaza manual niciodata.

Pana la F1a (19 aug 2026) existau TREI surse: un URDF editat manual (620 linii), un
xacro care descria alt robot (8 linkuri, 6 DOF, 0..pi pe toate articulatiile), si un
script care mutata URDF-ul in loc dupa generare. Acest README documenta xacro-ul
gresit -- de acolo venea afirmatia "0-180 grade". Cele doua fisiere retrase sunt in
`attic/`, cu explicatie.

Generare manuala:

    xacro urdf/rehab_exo.urdf.xacro -o /tmp/rehab_exo.urdf

## Flaguri

| flag | implicit | efect |
|---|---|---|
| `gazebo:=` | **false** | cele 6 plugin-uri `ApplyJointForce` (canalul prin care `patient_model.py` aplica cupluri). Implicitul s-a schimbat pe 21 aug 2026: plugin-urile scriu `JointForceCmd` la fiecare pas si suprascriu comanda de pozitie a lui `gz_ros2_control`, deci se exclud reciproc cu controlul de pozitie |
| `senzori:=` | true | cei 3 senzori IMU la 100 Hz (base_link + ambele talpi) |
| `rmw:=` | cyclonedds | implementarea RMW, pinuita in toate lansarile |

Continutul flagurilor `gazebo` si `senzori` e cel absorbit din fostul
`patch_urdf_extensions.py`; efectul e numeric identic cu al patch-ului.

## RMW pinuit

Toate lansarile declara `rmw:=` (implicit `rmw_cyclonedds_cpp`, decizia din registrul
de pe 18 aug) si il aplica prin `SetEnvironmentVariable` intr-un `GroupAction`
**nescopat** -- scopat, grupul isi retrage mediul inainte ca nodurile pornite din
event handlers sa apuce sa porneasca.

`scripts/rmw_guard.py` face doua verificari cu coduri de esec DISTINCTE:

| verificare | intrebarea | cod la esec |
|---|---|---|
| pasiva | pe ce RMW rulez EU | 3 |
| activa (apel de serviciu real) | ajung eu la restul lantului | 6 |

si ruleaza **din lant** (`gardian_in_lant`), pe acelasi drum ca spawnerele. Din
pozitia veche, in procesul launch-ului, raporta verde in timp ce jumatate din noduri
porneau pe alt RMW. Restul lantului porneste doar daca gardianul iese cu 0.

Nota de corectie: pana pe 21 aug, aici scria ca gardianul e necesar fiindca 'rclpy
cade linistit pe implicit daca RMW-ul cerut nu e instalat'. E fals pe Jazzy --
`RMW_IMPLEMENTATION=rmw_connextdds` da eroare zgomotoasa si procesul moare cu cod 1.
Gardianul a fost construit impotriva unei amenintari inexistente si s-a dovedit
necesar pentru alta, reala si complet tacuta.

    ros2 launch rehab_exo_description display.launch.py
    ros2 launch rehab_exo_description display.launch.py rmw:=zenoh

## Conventia articulara: ZEROUL MECANIC (B-prim)

Decizia D1, 22 aug 2026. Vezi `DECIZII.md` pentru rationament si statutul dovezii.

| articulatie | zero | pozitiv | cursa documentata |
|---|---|---|---|
| sold | coapsa ORIZONTALA (postura de lucru) | RIDICARE | 90 grade |
| genunchi | gamba in prelungirea coapsei | flexie | 140 grade |
| glezna | talpa perpendiculara pe gamba | dorsiflexie | 70 grade |

Cursele TOTALE sunt din [PDF Tabel 3.1, p.10-11]. PLASAREA ferestrei in jurul
zeroului nu e in document si ramane IPOTEZA:

| postura | sold | de unde |
|---|---|---|
| `culcat` | 0 .. 90 | re-derivata la D1: in jos piciorul ar trece prin podea |
| `sezut` | 0 .. 25 | re-justificata la P2.1, IPOTEZA-ANTROPO; vezi `urdf/IPOTEZE_LIMITE.md` |

`sezut` REDUCE cursa pastrand capatul de jos, cum cere mecanismul inelului de oprire
(reper 208) descris in [PDF p.7].

### Postura initiala

`POSTURA_INITIALA` = **sold 0, genunchi 90, glezna 0**: pozitia fizica de asezare a
pacientului, coapsa pe sezut si gamba atarnand vertical. Nu e o fractie mostenita, ci
o postura descrisa direct, si e verificata pe trei conditii in `test/test_postura.py`
(apartenenta la banda de sezut, invariantul podelei pe toata rampa, si FK-ul care
arata gamba verticala la 5.6e-17).

### Cele doua conventii moarte, si de ce a murit fiecare

Ambele traiesc in `attic/`, si nu ca fisiere moarte: testele le GENEREAZA la fiecare
rulare ca sa dovedeasca echivalentele.

**Zero = SEZUT, din URDF-ul livrat initial** (`attic/rehab_exo.urdf.livrat`).
SEMANTICA lui era corecta si e chiar cea la care s-a revenit la D1. Au murit
VALORILE: cursa de sold era -25.78..+40.11 grade, adica 65.89, nu cei 90 documentati,
si asimetrica fara nicio justificare.

**Zero ANATOMIC, varianta B de la M1** (`attic/rehab_exo.xacro.conventieB`,
`attic/exercise_core.py.conventieB0`). A murit pe geometrie: fereastra ei 0..90 se
transporta in -90..0 mecanic, adica integral in jumatatea in care piciorul trece prin
podea. Ironia utila e ca tot re-derivarea de la M1 a EXPUS imposibilitatea: inainte de
ea soldul statea la 64.22..130.11, o fereastra care ascundea problema. M1 nu a fost o
greseala, a fost pasul care a facut D1 posibila.

### Traiectoriile: doua invariante diferite

La reconversia B0 spre B-prim tratamentul NU a fost acelasi peste tot, si se verifica
separat in `test/test_traiectorii.py` (3858 de verificari):

| articulatie | tratament | de ce |
|---|---|---|
| genunchi, glezna | TRANSPORT, maparea e identitatea | toate valorile cad in ferestrele B-prim; egalitate stricta, abatere 0.0 |
| sold | RE-DERIVARE PE FRACTIE | transportul ar da [-82, -35], in afara ferestrei; s-a pastrat fractia din cursa DEASUPRA repausului |

Forma e pastrata la 5.19e-06 pe 960 de puncte de sold; unghiul absolut s-a schimbat
deliberat cu pana la 35.22 grade. Zero clamp-uri: fiecare punct a incaput in fereastra
fara sa fie taiat.

## Mase si inertii: NEVERIFICATE

Toate masele si inertiile sunt PLACEHOLDER pentru simulare. Documentul-sursa nu
contine mase pe segmente, centre de masa sau inertii (GAP 1). Sunt INTERZISE pentru
concluzii dinamice. Lista completa cu statut: `urdf/MASE_NEVERIFICATE.md`.

## Teste

    colcon test --packages-select rehab_exo_description
    python3 test/test_descriere.py     # direct, fara colcon
    python3 scripts/rmw_guard.py --selftest

`test_descriere.py` genereaza URDF-ul din xacro si verifica topologia (15 linkuri,
14 jointuri, 11 DOF active), limitele, simetria stanga-dreapta joint cu joint, si
flagurile cu CONTROL NEGATIV (prezenta cand sunt active, absenta cand nu sunt).

## Simularea Gazebo: ce a fost reparat pe 21 aug 2026

`adjust_position_controller` nu urca, iar `/controller_manager/list_controllers`
raspundea la apel niciodata. Nu era un defect de `ros2_control`. Erau TREI cauze
independente, toate de mediu sau de configurare, gasite prin eliminare o variabila
pe rand:

1. **GUI-ul Gazebo omora serverul.** `gz sim gui` moare instant cu
   `symbol lookup error: /snap/core20/.../libpthread.so.0: __libc_pthread_init`,
   fiindca terminalul vine din snap-ul VSCode, care scurge biblioteci core20 in
   mediul copiilor. Cand GUI-ul moare, `gz sim` escaladeaza la SIGKILL pe SERVER;
   lumea nu mai paseste, `/clock` tace, si `controller_manager`-ul, care ruleaza IN
   bucla de update a Gazebo, nu mai e actualizat.
   Masurat: cu GUI 0 mesaje `/clock` in 8 s; server-only 667 Hz.
   Lansarea e acum implicit headless; `gui:=true` ramane, dintr-un terminal normal.

2. **Jumatate din noduri porneau pe alt RMW.** `SetEnvironmentVariable` statea
   intr-un `GroupAction` scoped, care isi scoate mediul la iesirea din grup, iar
   actiunile amanate prin `RegisterEventHandler` se executa dupa acel moment. Deci
   simulatorul pe `rmw_cyclonedds_cpp`, spawnerele pe `rmw_fastrtps_cpp`. Cele doua
   interopereaza la nivel RTPS pe pub/sub dar NU pe servicii -- de aceea topicurile
   se vedeau si doar apelurile de serviciu nu se intorceau.
   Regresie numita: `test/test_rmw_scope.py`.

3. **Comenzile de pozitie nu ajungeau in fizica.** Doua greseli suprapuse:
   `position_proportional_gain` traieste pe nodul `/gz_ros_control`, nu pe
   `/controller_manager` si nu in URDF sub `<hardware>` (pus in celelalte doua
   locuri se accepta fara eroare si nu face nimic), iar `hold_joints` era `true`.
   Ambele se seteaza acum din `config/controllers.yaml`, sectiunea `gz_ros_control`.

Rezultat, cu `ros2 launch rehab_exo_description gazebo.launch.py` nemodificat:
toate cele trei controlere `active`, `/joint_states` la ~57 Hz, homing curat pe 4
encodere absolute, si un pas comandat de +0.30 rad pe genunchi urmarit cu eroare
de 0.002 .. 0.042 rad.

### Castigul si amortizarea: ce s-a masurat pe 22 aug

Oscilatia gleznei din ziua 2 e REPARATA, dar niciuna din cele doua cauze pe care le
banuiam nu era cea reala. Ambele au fost eliminate prin masurare:

| ipoteza | test | rezultat |
|---|---|---|
| comanda de viteza loveste clema | reconstruit `v = k * eroare` la 93 Hz | max 0.42 rad/s dintr-o limita de 3.0369 -- **nu atinge clema** |
| amortizare insuficienta | `amort_glezna` 2.0 -> 20.0 | **nicio schimbare** |
| castig prea mare | 15.0 -> 1.0 | **oscilatia dispare complet** |

Explicatia care leaga totul: articulatia e comandata **cinematic**, nu prin cuplu.
`gz_ros2_control` scrie `JointVelocityCmd = k * eroare`, iar Gazebo o aplica drept
constrangere de viteza. Nu exista nimic de invins, deci amortizarea nu are ce musca
si castigul mare doar suprareactioneaza. Contra-intuitiv, castigul mai mic urmareste
mai bine: la 1.0 o treapta de 0.30 rad se aseaza la eroare 0.000, iar articulatiile
necomandate nu deriva deloc.

Castigul PER ARTICULATIE nu e posibil: `gz_ros2_control` 1.2.17 expune doar un
`position_proportional_gain` global (verificat in simbolurile bibliotecii).

Amortizarea si frecarea sunt acum argumente xacro per articulatie
(`amort_sold|genunchi|glezna`, `frec_*`), cu statut **NEVERIFICAT**, ca si masele.
Valorile raman cele dinainte; parametrizarea a fost pastrata fiindca a reparat un
bug separat: ca proprietati, `amort_glezna:=99` era acceptat fara eroare si ignorat
in tacere.

Consecinta de stiut: cu comanda cinematica NU exista rejectie de perturbatie. Cand
modelul de pacient va aplica forte reale, e nevoie de comanda in EFORT, si atunci
acordarea se reia de la zero.

## Exercitii

Toate sunt in conventia B-prim (`convention_version B1`). Se pornesc fie ca
argument al demo-ului, fie trimise la runtime:

```bash
ros2 launch rehab_exo_description demo_c4.launch.py exercitiu:=knee_extension
ros2 topic pub --once /exercise_cmd std_msgs/msg/String "{data: 'hip_raise'}"
```

| exercitiu | articulatii | puncte | durata | repetari |
|---|---|---:|---:|---:|
| `alternating_march` | hip+knee | 192 | 19.2 s | 3 |
| `ankle_alternating` | knee+ankle | 171 | 17.1 s | 3 |
| `ankle_holds` | knee+ankle | 243 | 24.3 s | 2 |
| `ankle_pump` | knee+ankle | 160 | 15.9 s | 3 |
| `full_extension` | hip+knee+ankle | 191 | 19.0 s | 2 |
| `hip_alternating` | hip | 185 | 18.4 s | 2 |
| `hip_hold` | hip | 181 | 18.0 s | 2 |
| `hip_raise` | hip | 196 | 19.5 s | 3 |
| `knee_alternating` | knee+ankle | 211 | 21.0 s | 2 |
| `knee_extension` | knee+ankle | 226 | 22.5 s | 3 |
| `knee_pulses` | knee+ankle | 187 | 18.6 s | 2 |
| `leg_wave` | hip+knee+ankle | 233 | 23.2 s | 2 |

### Smoke pe toate cele 12, cu supervizor activ (22 aug 2026)

Rulate intr-o singura sesiune Gazebo, trimise pe rand pe `/exercise_cmd`.
Verdictele sunt calculate cu ACELEASI functii pure ca monitorul.

| exercitiu | URMARIRE | COERENTA | CANALE | VITEZA | eroare max |
|---|---|---|---|---|---:|
| `alternating_march` | OK | OK | OK | OK | 0.0000 |
| `ankle_alternating` | OK | OK | OK | OK | 0.0000 |
| `ankle_holds` | OK | OK | OK | OK | 0.0000 |
| `ankle_pump` | OK | OK | OK | OK | 0.0000 |
| `full_extension` | OK | OK | OK | OK | 0.0000 |
| `hip_alternating` | ATENTIE | OK | OK | OK | 1.1145 |
| `hip_hold` | ATENTIE | OK | OK | OK | 1.1935 |
| `hip_raise` | OK | OK | OK | OK | 0.0000 |
| `knee_alternating` | OK | OK | OK | OK | 0.0011 |
| `knee_extension` | OK | OK | OK | OK | 0.0000 |
| `knee_pulses` | OK | OK | OK | OK | 0.0000 |
| `leg_wave` | ATENTIE | OK | OK | OK | 0.2335 |

**Trei exercitii pica pe URMARIRE, si toate trei din ACEEASI cauza.**
Nu e o problema de geometrie sau de urmarire: e supervizorul care s-a
declansat devreme, a facut latch si a tinut articulatia pentru tot restul
sesiunii. Vezi sectiunea urmatoare. Coloana de declansari nu apare in tabel
fiindca proba se abonase DUPA ce latch-ul pornise si le subnumara; cifra
corecta, din log, e 4 declansari in toata sesiunea.

## Panoul de date

Trei nivele, de la cel mai ieftin la cel mai complet.

**1. Tabloul din terminal**, 2 Hz, patru verdicte, NaN vizibil ca NaN. Porneste
odata cu demo-ul; separat:

```bash
ros2 run rehab_exo_description monitor_senzori.py
```

**2. Grafice live cu rqt_plot.** NU exista un config salvat in pachet: contextul in
care se lucra il presupunea existent, dar nu e nicaieri, si se noteaza aici in loc
sa fie inventat. Pana atunci, topicurile se dau direct:

```bash
ros2 run rqt_plot rqt_plot \
  /joint_states/position[1] /joint_states/position[4] \
  /rehab/cuplu/left_knee/data /rehab/cuplu/right_knee/data
```

**PlotJuggler NU e instalat** pe masina asta (verificat: 0 pachete). Nu se instaleaza
nimic; daca apare, un layout salvat isi are locul aici.

**3. Inregistrare pe disc si figuri post-sesiune.** Fiecare rulare poate lasa un CSV
cu antet de provenienta:

```bash
ros2 launch rehab_exo_description demo_c4.launch.py \
    exercitiu:=knee_extension inregistrare:=true
python3 scripts/plot_sesiune.py ~/DATE_TWIN/<sesiunea>/
```

### Unde se scriu datele

`~/DATE_TWIN/<AAAALLZZ_HHMMSS>_<exercitiu>/sesiune.csv`, si **niciodata** in
`~/DATE_CAMPANIE`. Acolo stau datele canonice de campanie ale tezei, care sunt
read-only si nu se amesteca cu date de simulare; un twin care ar scrie in ele ar
contamina exact ce nu are voie.

CSV-ul se autodocumenteaza. Antet cu data, commit-ul de la build, conventia
articulara, exercitiul, parametrii si ipotezele active; subsol cu numarul de randuri,
RTF-ul mediu al sesiunii si contoarele de mesaje primite pe fiecare canal. NaN se
scrie NaN: niciodata 0, niciodata camp gol.

Contoarele nu reclama canalele LENTE, si asta e deliberat: rigla merge la 10 Hz iar
esantionarea la 50, deci va avea mereu mai putine mesaje decat randuri, si e corect.
Pragul prinde canalul MUT sau aproape mut.

## DEFECT DESCHIS: pragul electric inferior intra in conflict cu exercitiile

Gasit de smoke-ul complet pe 22 aug. Se raporteaza cu cifre si NU se repara tacit;
e o decizie despre stratul de siguranta, nu o corectie de model.

Pragul electric sta la 5 grade INAUNTRU fata de limita mecanica, la AMBELE capete.
Dar exercitiile folosesc legitim capatul de jos al ferestrei documentate:

| articulatie | prag electric inferior | cea mai mica valoare ceruta de exercitii |
|---|---:|---:|
| sold | 5.00 grade | **0.00 grade** (repausul insusi) |
| genunchi | 5.00 grade | **4.06 grade** |

Deci orice exercitiu care revine la repaus trece sub prag, declanseaza, iar
supervizorul FACE LATCH si tine articulatia pana la finalul sesiunii. Masurat: 4
declansari, toate pe capatul `min`, la 0.0664 pana la 0.0781 rad.

Cauza de fond e o ordonare gresita a straturilor. Corect ar fi
`mecanic > electric > software`, adica traiectoriile sa stea INAUNTRUL ferestrei
electrice. La noi traiectoriile ating capatul MECANIC, deci il incalca pe cel
electric prin constructie.

Doua rezolvari, ambele aparabile, si alegerea e a omului:

1. **Traiectoriile se re-deriva in fereastra electrica** (`[5, 85]` in loc de
   `[0, 90]`). Respecta ordonarea manualelor, dar inseamna inca o remapare si
   pierde 10 grade din cursa documentata.
2. **Pragul inferior dispare acolo unde limita mecanica E pozitia de repaus.**
   In B-prim, soldul la 0 e coapsa orizontala, adica exact unde sta dispozitivul; un
   proximity montat acolo ar fi apasat permanent. Pericolul e SUB acel punct, iar
   fereastra nu are loc dedesubt.

Pana la decizie, demo-ul cu supervizor activ va declansa pe exercitiile care revin
la repaus. `supervizor:=false` il scoate din lant pentru demonstratii.

## Siguranta: cele TREI straturi

Nu se inlocuiesc si nu se sincronizeaza. Fiecare prinde alta clasa de esec.

| strat | ce vede | unde traieste | statutul cifrelor |
|---|---|---|---|
| 1. MECANIC | opritoarele fizice | `<limit>` din URDF (`urdf/IPOTEZE_LIMITE.md`) | cursele TOTALE sunt din [PDF Tabel 3.1]; impartirea min/max e IPOTEZA |
| 2. ELECTRIC | POZITIA | `scripts/supervizor_electric.py` + `supervizor_core.py` | marja de 5 grade sub opritor e IPOTEZA; proximitatile reale nu au fost masurate |
| 3. SOFTWARE | cuplu, viteza, heartbeat | `config/safety_limits.yaml` + `scripts/safety_supervisor.py` | praguri terapeutice, de stabilit cu personal clinic |

Stratul electric emuleaza proximitatile [PDF p.7]. Praguri de pozitie strict
inauntrul celor mecanice, cu **armare per articulatie**: la pornire toate
articulatiile sunt la 0.0 rad, iar `sold_min` si `genunchi_min` sunt tot 0.0 -- deci
pornirea E pe margine si un supervizor naiv ar declansa la fiecare boot. O
articulatie se armeaza abia dupa ce a fost vazuta o data bine inauntru; pana atunci
e observata, nu supravegheata. Starea fiecarei articulatii se publica pe
`/rehab/supervizor/stare`, tocmai fiindca "nearmat" inseamna "nu poate declansa".

Comutarea `culcat <-> sezut` se face prin serviciul `/rehab/supervizor/postura`
(`std_srvs/SetBool`, true = sezut) si e REFUZATA cu motiv daca pozitia curenta ar
cadea in afara noului set -- altfel dispozitivul ar deveni ilegal fara sa se fi
miscat, iar articulatia nu s-ar mai arma niciodata in noul set.

La declansare se publica o traiectorie de un punct la pozitia curenta, care
inlocuieste traiectoria in curs. Nu e o oprire de siguranta certificata si nu
pretinde sa fie.

### Masurat pe 22 aug 2026

| verificare | rezultat |
|---|---|
| pornire pe margine | sold si genunchi NEARMAT, glezna ARMAT; 0 declansari |
| exercitiu normal (genunchi 1.2 rad) | 0 declansari false |
| traiectorie peste pragul electric (comandat 1.5500) | oprit la **1.4956 rad**, prag 1.4835, limita mecanica 1.5708 |
| comutare la sezut din 0.80 rad | permisa; praguri sold 0.5236..1.4835 |
| comutare din pozitie ilegala | refuzata, cu articulatia si valoarea in mesaj |
| 0.30 rad dupa comutare (legal in culcat) | declansare pe capatul **min**, la 0.5235 vs prag 0.5236 |

### Ce ramane deschis

Masele, inertiile, amortizarile si frecarile sunt placeholder -- nicio concluzie
dinamica. Senzorii sunt sintetici.

Demonstratia asamblata si ce inseamna fiecare cifra din ea: `README_DEMO.md`.
