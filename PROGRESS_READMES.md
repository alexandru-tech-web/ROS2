# Progres READMEuri per pachet

## STARE: TERMINAT (10 pachete documentate + 1 SKIP justificat)
Branch: overnight-readmes (din main). Anti-fabricare STRICTA respectata: fiecare README scris de un
agent care a CITIT codul real, apoi AUDITAT adversarial de un al doilea agent care a verificat fiecare
afirmatie fata de cod (entry_points vs setup.py, argparse, declare_parameter, topicuri, docstring-uri).
FARA merge in main, FARA push.

## Pachete
ACTIVE (amanuntit):
- [x] mesh_plugin   -- DONE (231 linii; cele 2 implementari paralele documentate cu sursa)
- [x] sar_swarm     -- DONE (248 linii; audit a corectat 2 sintaxe -- vezi mai jos)
MEDIU:
- [x] sar_plugins            -- DONE (224 linii)
- [x] rehab_exo_description  -- DONE (170 linii)
- [x] joint_emulator         -- DONE (151 linii; are TODO: de confirmat unde codul nu era clar)
- [x] curs_ros2             -- DONE (175 linii)
- [x] curs_ros2_interfaces   -- DONE (143 linii; pachet de interfete .msg/.srv)
- [x] link_adaptive          -- DONE (142 linii; entry_points verificate 1:1 cu setup.py)
ARHIVA:
- [x] teleop_rover   -- DONE (79 linii -- vezi nota de proportionalitate)
- [x] servo_control  -- DONE (57 linii)
- [x] gen_articol    -- DONE (52 linii)
SKIP:
- c1_benchmark -- SKIP pana la merge-ul matricei 2x2 (conflict de continut; pe acest branch
  c1_benchmark e la starea PRE-matrice, deci README-ul ar fi stale). De facut dupa merge.
- stats_out    -- nu e pachet (director-artefact campaign_stats).

## RAPORT FINAL
- TOATE cele 10 README-uri (non-c1_benchmark) regenerate din cod real, ASCII curat, comise PER PACHET
  (diff reviewable). Pipeline: 11 agenti draft + 11 agenti audit anti-fabricare (workflow).
- ANTI-FABRICARE confirmata: auditul a verificat fiecare README fata de sursa. Unde codul nu permite o
  afirmatie sigura, README-ul are "TODO: de confirmat" (ex. joint_emulator; cifrele de performanta din
  mesh_plugin marcate TODO, nu inventate).
- CORECTII facute de audit (afirmatii initial gresite, reparate fata de cod):
  * sar_swarm: --scenarios ia NUME fara extensie .yaml (codul adauga .yaml); --down foloseste interval
    a:b (ex. 25:60), nu valori separate.
  * (restul auditurilor: "nimic de corectat" sau corectii minore de sintaxa -- vezi transcriptul workflow.)
- SPOT-CHECK manual (eu, dupa audit): link_adaptive entry_points din README == setup.py EXACT (4 noduri);
  joint_emulator NU are setup.py -> README zice corect zero-build/python3.

## DE VAZUT ALEXANDRU
1. c1_benchmark NU are README regenerat -- SKIP intentionat pana la merge-ul matricei 2x2 in main.
   Dupa merge: reia pe un branch nou si documenteaza c1_benchmark din starea corecta (cu env_label,
   matrix_table.py, --mode hil_wifi/hil_switch).
2. PROPORTIONALITATE: tier-ul ARHIVA a iesit mai lung decat 10-20 randuri din brief (teleop_rover 79,
   servo_control 57, gen_articol 52). Motiv: teleop_rover are 27 .py (mai multe ca mesh_plugin), deci
   "arhiva scurta" nu prea i se potriveste -- README-ul listeaza fisierele reale. Daca vrei archive
   mai scurte, se pot taia; eu am preferat acuratete (toate dovedite din cod). Tu decizi.
3. joint_emulator README are un "TODO: de confirmat" + o fraza despre build putin stangace -- de revazut
   (pachetul nu are setup.py; e zero-build/python3, dar formularea exacta merita un ochi).
4. Toate README-urile au inlocuit versiunile vechi (git M, nu fisiere noi). Daca vreun README vechi avea
   continut pe care voiai sa-l pastrezi, e in istoricul git.
