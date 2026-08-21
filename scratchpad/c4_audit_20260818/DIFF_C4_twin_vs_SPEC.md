# Audit twin LLR -- diff contra SPEC_LLR_twin_din_PDF.md

Sursa spec: /home/ubuntu/Downloads/SPEC_LLR_twin_din_PDF.md (158 linii, md5 ca15601a30f2)
Pachet auditat: ros2_ws/src/rehab_exo_description @ commit cf4b43d (2026-06-29)
Data auditului: 2026-08-18. Nicio sursa modificata.

DOUA DESCRIERI LOCALE, deci tabelul are TREI coloane de realitate. `urdf/rehab_exo.urdf`
(livrat, 620 linii) si `urdf/rehab_exo.xacro` (125 linii) descriu roboti DIFERITI; ambele
trec check_urdf. Verdictul pe rand spune care dintre ele (daca vreuna) e conforma.

| # | element din SPEC | SPEC | URDF livrat | xacro | verdict |
|---|---|---|---|---|---|
| 1 | DOF revolute active | 3/picior x2 = 6, sagital | 6 revolute, axa 0 +/-1 0 | 6 revolute, axa sagitala | CONFORM (ambele) |
| 2 | DOF totale active | 6 rev + push rod-uri | 11 (6 rev + 5 prism) | 6 (6 rev + 0 prism) | URDF CONFORM / xacro DIVERGENT |
| 3 | cursa sold | 90 grade (Tabel 3.1) | 65,89 grade | 180,00 grade | ambele DIVERGENT (vezi nota A) |
| 4 | cursa genunchi | 140 grade | 100,27 grade | 180,00 grade | ambele DIVERGENT |
| 5 | cursa glezna | 70 grade | 68,75 grade | 180,00 grade | URDF near-miss (-1,25 grade) / xacro DIVERGENT |
| 6 | impartire min/max | GAP 4 in spec | -0,45..0,70 / 0..1,75 / +-0,60 rad | 0..pi pe toate | IPOTEZE LOCALE, neetichetate ca atare |
| 7 | rapoarte transmisie 2700:11, 2160:11, 100 | Tabel 3.1 | absent | absent | LIPSESTE (ambele) |
| 8 | lungimi coapsa/gamba ca parametri | ajustabile | constante in geometrie; ajustare prin prismatice 0..0,08 m | xacro:property thigh_len/shank_len = 0,42 m | partial: xacro are parametri, URDF nu |
| 9 | limita VARIABILA de sold (2 seturi comutabile) | PDF p.7, inel 208 | un singur set | un singur set | LIPSESTE (ambele) |
| 10 | senzor cuplu sold/genunchi (M2210B) | PDF p.23 | absent | absent | LIPSESTE |
| 11 | senzor forta 6D sub talpa (TR69-1500) | PDF p.23 | absent | absent | LIPSESTE |
| 12 | senzor unghi glezna (BWK216) | PDF p.23 | absent | absent | LIPSESTE |
| 13 | rigla electronica gamba (406) | PDF p.9 | absent | absent | LIPSESTE |
| 13b | (senzori LOCALI, in afara spec) | -- | 3 IMU la 100 Hz + ApplyJointForce x6, injectate de patch_urdf_extensions.py | absent | PESTE SPEC |
| 14 | encodere absolute -> joint_states | PDF p.10 | /joint_states publicat | (nu se ruleaza) | CONFORM (URDF) |
| 15 | ros2_control interfete | position/velocity/effort | cmd position+velocity; state position/velocity/effort | absent | CONFORM (URDF) / LIPSESTE (xacro) |
| 16 | controllers YAML + update_rate | -- | controllers.yaml, update_rate 100 Hz | -- | CONFORM |
| 17 | push rod-uri pozitionare | prismatice pasive sau fixe param. | 5 prismatice cu effort/velocity, controller dedicat | absente | CONFORM ca modelare (vezi nota B) |
| 18 | mase / inertii | GAP 1 (nu exista in PDF) | 14 mase, total 95,2 kg, cu izz | absente | CIFRE FARA SURSA |
| 19 | lungimi numerice | GAP 2 | 0,485 m inaltime scaun; 0..0,15 / 0..0,08 m curse | 0,42 m coapsa si gamba | CIFRE FARA SURSA |
| 20 | rata trafic ROS 2 | 50 Hz x 4096 B (C1/C2) | 9,997 Hz x ~409 B | -- | DIVERGENT: ~x50 pe banda |

NOTA A -- soldul nu e o simpla divergenta. URDF-ul declara in antet "Conform Fig 2.2 din
documentul-sursa" si "Postura zero = SEZUT". Cursa lui de 65,89 grade cade in banda
65-80 grade a restrictiei de sezut din literatura LLR-Ro. IPOTEZA: e setul de SEZUT,
iar setul complet (90 grade) lipseste -- ceea ce e chiar mecanismul dual din PDF p.7.
NU e confirmata de spec (impartirea min/max e GAP 4); ramane ipoteza locala.

NOTA B -- push rod-urile sunt actuatoare electrice reale (101/113/306/307/403), deci
modelarea lor ca prismatice actionabile e CORECTA. Doua rezerve: nu fac parte din bucla
de training, iar gamba (403) e comandata FARA feedback de pozitie, cu rigla electronica
separata -- twin-ul o modeleaza ca prismatica obisnuita, deci pierde exact particularitatea.

## Cifre locale fara sursa in spec (semnatura de fabricatie veche)

| valoare | unde | GAP atins |
|---|---|---|
| 14 mase, 0,6 .. 32,0 kg (total 95,2 kg) | URDF, toate linkurile | GAP 1 |
| inertii izz pe toate linkurile | URDF | GAP 1 |
| thigh_len = shank_len = 0,42 m | xacro:property | GAP 2 |
| seat_lift 0..0,15 m | URDF | GAP 2 |
| extensii coapsa/gamba 0..0,08 m | URDF | GAP 2 |
| inaltime scaun 0,485 m | URDF, origin seat_lift | GAP 2 |
| limitele revolute (-0,45/0,70/1,75/+-0,60 rad) | URDF | GAP 4 |
| effort 120/300/500 Nm, velocity 2,0/0,03/0,05 | URDF | GAP 5 + sectiunea 4 din spec |

Observatie: masa human_torso = 32 kg e un MODEL DE PACIENT, nu o piesa a robotului.
Spec-ul nu contine sarcina maxima pacient (GAP 7), deci si cifra asta e locala.

## Ce exista LOCAL peste spec -- de pastrat / de decis

DE PASTRAT (sprijina DoD-ul C4):
- extensii de telereabilitare: operator_heartbeat.py, safety_supervisor.py,
  sensor_recorder.py, telemetry_display.py, session_report.py
- launch-uri de exercitii (sold/genunchi/glezna/combinat), operator.launch.py,
  telerehab.launch.py
- config/patient_demo.yaml, config/safety_limits.yaml, config/gz_patient_bridge.yaml
- worlds/rehab_world.sdf, rviz/rehab.rviz

DE DECIS:
- model de pacient integrat in URDF (human_torso 32 kg + backrest): utilitate vizuala,
  dar contamineaza masa robotului si nu are sursa
- exercise_controller.py, patient_model.py, plot_recording.py: scop clinic, nu C4
- scripts/patch_urdf_extensions.py: CONFIRMAT ca insereaza in rehab_exo.urdf, inainte de
  </robot>, sase plugin-uri ApplyJointForce si trei senzori IMU (base_link + ambele talpi,
  100 Hz). E a TREIA sursa de adevar asupra descrierii, si singura care o muteaza in loc.
  IMU-urile NU apar in spec: nu inlocuiesc familia de senzori ceruta (cuplu, forta 6D,
  unghi glezna, rigla), dar arata ca exista deja un drum local de senzori pe care F5 poate
  sa se aseze.
