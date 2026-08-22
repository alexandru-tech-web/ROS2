# attic -- mecanisme retrase

## patch_urdf_extensions.py (retras la F1a, 2026-08-19)

Insera in urdf/rehab_exo.urdf, dupa generare, sase plugin-uri ApplyJointForce si
trei senzori IMU. Era A TREIA sursa de adevar asupra descrierii si singura care
MUTA artefactul in loc: dupa prima rulare, artefactul si generatorul lui divergeau
ireversibil, iar backup-ul .bak nu ajuta pe nimeni sa mai stie care e originalul.

Continutul lui e absorbit integral in urdf/rehab_exo.urdf.xacro, ca blocuri
conditionate de flagurile gazebo:= si senzori:=. Efectul e numeric identic --
dovedit prin diff canonicalizat, vezi raportul F1a.

Se pastreaza aici pentru arheologie, NU se mai ruleaza.

## rehab_exo.urdf.livrat (retras la F1a)

URDF-ul editat manual, 620 linii. Acum e ARTEFACT generat din
urdf/rehab_exo.urdf.xacro la build. Se pastreaza aici ca REFERINTA A
INVARIANTULUI: diff-ul canonicalizat numeric dintre (acest fisier + efectul
patch-ului) si URDF-ul generat cu gazebo:=true senzori:=true este GOL,
pe 44 de elemente comparate.

## rehab_exo.xacro.vechi (retras la F1a)

Xacro-ul de 125 de linii care descria ALT robot: 8 linkuri, 7 jointuri, 6 DOF,
fara scaun si fara extensii, cu 0..pi pe toate articulatiile revolute. README-ul
pachetului il documenta pe ACESTA ("0-180 grade"), nu URDF-ul livrat -- de aici
enigma care a dus la audit. Nu are continut recuperabil: structura-tinta e cea
din URDF-ul livrat.

## rehab_exo.xacro.conventieB (retras 22 aug 2026)

Descrierea in conventia B (zero anatomic), asa cum a iesit din M1. NU e o copie
moarta: `test/test_conventie.py` o GENEREAZA la fiecare rulare si dovedeste prin FK
ca modelul nou (conventia B', decizia D1) descrie acelasi lant fizic. Fara ea,
echivalenta ar fi o afirmatie in loc de o masuratoare. Se sterge doar impreuna cu
testul.

## exercise_core.py.conventieB0 (retras 22 aug 2026)

Traiectoriile in conventia B0 (zero anatomic), inainte de reconversia la B-prim. Ca si
`rehab_exo.xacro.conventieB`, NU e o copie moarta: `test/test_traiectorii.py` o
incarca la fiecare rulare si dovedeste ca reconversia a pastrat FORMA exercitiilor si
a schimbat DELIBERAT unghiul absolut. Se sterge doar impreuna cu testul.

## De ce a murit fiecare conventie

**Zero = SEZUT (URDF-ul livrat).** Semantica era CORECTA si e cea la care s-a revenit
la D1. Au murit valorile: sold -25.78..+40.11 grade, adica o cursa de 65.89 in loc de
cei 90 documentati, si asimetrica fara justificare.

**Zero ANATOMIC (varianta B, M1).** A murit pe geometrie: fereastra 0..90 se
transporta in -90..0 mecanic, integral sub orizontala, unde piciorul trece prin podea.
Dar tot re-derivarea M1 a expus imposibilitatea; inainte de ea soldul statea la
64.22..130.11, fereastra care o ascundea.
