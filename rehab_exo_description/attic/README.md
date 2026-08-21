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
