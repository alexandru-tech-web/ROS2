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

## Conventia de zero (se schimba la F1b)

Zeroul articular actual este **zero = SEZUT**, mostenit de la autorul initial
(declarat in antetul URDF-ului livrat: "Postura zero = SEZUT"). Cursele actuale --
sold 65,89 grade, genunchi 100,27, glezna 68,75 -- sunt IPOTEZE LOCALE (GAP 4 din
`SPEC_LLR_twin_din_PDF.md`), nu valori din documentatia tehnica, care cere
90 / 140 / 70 grade.

La F1b (Valul 2) zeroul se redefineste ANATOMIC conform documentului-sursa, cursele
se aliniaza la 90/140/70, si apare al doilea set de limite (`postura:=sezut|culcat`,
mecanismul inelului de oprire din documentatie).

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
