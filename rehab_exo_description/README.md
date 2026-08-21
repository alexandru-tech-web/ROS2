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

## Conventia articulara: ZERO ANATOMIC

Plan sagital, pentru fiecare articulatie:

| articulatie | zero | pozitiv | cursa (documentata) | split (ipoteza, GAP 4) |
|---|---|---|---|---|
| sold | coapsa colineara cu trunchiul | FLEXIE | 90 grade | 0 .. +90 |
| genunchi | gamba colineara cu coapsa | FLEXIE | 140 grade | 0 .. +140 |
| glezna | talpa perpendiculara pe gamba | DORSIFLEXIE | 70 grade | -35 .. +35 |

Cursele TOTALE sunt din [PDF Tabel 3.1, p.10-11]. Impartirea min/max NU e in document
si e ipoteza locala, motivata in `urdf/IPOTEZE_LIMITE.md`; sunt parametri xacro, cu
suma asertata egala cu cursa documentata.

`postura:=culcat|sezut` schimba DOAR limita inferioara a soldului: in sezut, inelul de
oprire (reper 208, PDF p.7) reduce mecanic cursa la 25..90 grade. Restul articulatiilor
raman neatinse (verificat in test).

### Conventia veche, si de ce s-a pensionat

Pana la M1, zeroul era postura SEZUT (coapsa orizontala, gamba verticala), declarata in
antetul URDF-ului livrat. Se pastreaza in `attic/rehab_exo.urdf.livrat`. Echivalenta
fizica dintre cele doua conventii e dovedita programatic, nu prin citire
(`test/test_conventie.py`: 62 de configuratii x 2 picioare, abatere maxima 2.5e-16 m,
plus control negativ cu o mapare gresita).

ATENTIE la genunchi: in conventia veche unghiul crestea spre EXTENSIE; acum creste spre
FLEXIE. Inversarea de semn e reala si e materializata in axa jointului.

### Postura initiala

`POSTURA_INITIALA` din `scripts/exercise_core.py`, in conventia noua:

| articulatie | valoare | de unde |
|---|---|---|
| sold | **35.22 grade** | RE-DERIVATA: fractia 0.3913 (unde cadea vechiul zero in cursa veche) din noua cursa de 90 |
| genunchi | **90.00 grade** | convertita exact: vechiul zero era gamba verticala sub coapsa orizontala |
| glezna | **0.00 grade** | neschimbata |

ATENTIE, si e o consecinta de stiut, nu un detaliu: soldul de 35.22 grade e IN setul de
limite `postura:=sezut` (25..90), dar NU e postura sezut. Sezutul fizic inseamna 90 de
grade de flexie de sold; vechea stare initiala chiar acolo era. Fractia s-a pastrat,
postura fizica de plecare nu -- exact acelasi compromis ca la traiectoriile de sold.
Daca se prefera ca dispozitivul sa PORNEASCA fizic din sezut, valoarea devine 90 si
primul segment al fiecarui exercitiu se schimba; e o decizie deschisa, nu o scapare.

### Schimbari DELIBERATE de domeniu (registrul complet)

Trei domenii articulare s-au schimbat intentionat la M1. Doua dintre ele nu au legatura
cu traiectoriile si de aceea sunt usor de trecut cu vederea:

| # | schimbare | vechi (anatomic) | nou | efect |
|---|---|---|---|---|
| 1 | sold RE-DERIVAT | 64.22 .. 130.11 | 0 .. 90 | traiectoriile pastreaza fractia, nu unghiul |
| 2 | **hiperextensia genunchiului ELIMINATA** | -10.27 .. 90 | 0 .. 140 | vechiul model permitea 10.27 grade de hiperextensie; niciun exercitiu nu o folosea (dovedit de test), dar disparitia ei e DECIZIE, nu consecinta |
| 3 | glezna largita | -34.38 .. +34.38 (68.75) | -35 .. +35 (70) | +0.62 grade pe fiecare parte, spre cursa documentata |

### Traiectoriile: doua invariante diferite

Genunchi si glezna au fost CONVERTITE (unghi fizic identic). Soldul a fost RE-DERIVAT:
cursa lui veche, exprimata anatomic, era 64.22..130.11 grade -- sold permanent flectat,
peste flexia umana normala -- si nu incape in cei 90 documentati. Punctele pastreaza
FRACTIA din cursa disponibila, adica forma exercitiului, nu unghiul absolut.
Verificat in `test/test_traiectorii.py` (1908 valori, cele doua invariante separate).

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

### Ce ramane deschis

Masele, inertiile, amortizarile si frecarile sunt placeholder -- nicio concluzie
dinamica. Senzorii sunt sintetici.

Demonstratia asamblata si ce inseamna fiecare cifra din ea: `README_DEMO.md`.
