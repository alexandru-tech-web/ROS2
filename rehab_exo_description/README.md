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
| `gazebo:=` | true | cele 6 plugin-uri `ApplyJointForce` (canalul prin care `patient_model.py` aplica cupluri) |
| `senzori:=` | true | cei 3 senzori IMU la 100 Hz (base_link + ambele talpi) |
| `rmw:=` | cyclonedds | implementarea RMW, pinuita in toate lansarile |

Continutul flagurilor `gazebo` si `senzori` e cel absorbit din fostul
`patch_urdf_extensions.py`; efectul e numeric identic cu al patch-ului.

## RMW pinuit

Toate lansarile declara `rmw:=` (implicit `rmw_cyclonedds_cpp`, decizia din registrul
de pe 18 aug) si il aplica prin `SetEnvironmentVariable` intr-un `GroupAction` scoped.
`scripts/rmw_guard.py` verifica la runtime implementarea EFECTIV incarcata si iese cu
cod 3 la nepotrivire: pinuirea singura nu ajunge, fiindca daca RMW-ul cerut nu e
instalat, rclpy cade linistit pe implicit.

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

## Limita cunoscuta

`adjust_position_controller` nu urca sub `gazebo.launch.py`. Serviciul
`/controller_manager/list_controllers` exista dar nu raspunde; un timeout de 60 s nu
ajuta. Prezent sub ambele RMW-uri testate, cu variabilitate intre rulari. Cauza NU e
stabilita -- item deschis, vezi raportul F0b.
