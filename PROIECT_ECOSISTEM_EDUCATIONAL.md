# Charter: ecosistemul educational open-source

STATUT: PARCAT pana pe 19.06.2026 (dupa submisia SSRR).
Kickoff: 19–21.06, sesiune dedicata de analiza + decizie.

## 1. Viziunea (condensata din propunere)

Ecosistem open-source pentru invatarea programarii si a gandirii algoritmice:
biblioteci (algoritmi, structuri de date, matematica), vizualizatoare
interactive (sortare, grafuri, pathfinding), portal de invatare cu exercitii
si judge online, documentatie completa, CI/CD, guvernanta de proiect
(issues, milestones, Kanban). Standard: portofoliu profesional + proiect
de referinta.

## 2. Doua variante strategice

### Varianta A — ecosistemul generic (Java 21 + Spring / React / PostgreSQL)
Conform promptului original, pornind de la repo-ul "JavaScript".
+ portofoliu clasic full-stack, tehnologii cerute pe piata
+ material de invatare personala excelent (arhitectura enterprise)
− concureaza frontal cu TheAlgorithms, freeCodeCamp, VisuAlgo
− zero sinergie cu teza: fiecare ora aici e o ora luata doctoratului

### Varianta B — ecosistemul de robotica educationala (RECOMANDAT)
Construit pe activele EXISTENTE din depozit:
- curs_ros2 (M0–M13, 21 executabile, lectii in docs/) = curriculum gata scris
- TEHNOLOGII.md = manualul de fundamente (ROS2/Gazebo/RViz/protocoale)
- teleop_rover + servo_control + sar_swarm = simulatoare didactice reale
- vizualizatoarele Gazebo/RViz = "Algorithm Visualizer"-ul domeniului
+ diferentiat: nu exista portal romanesc de invatare ROS2/Zenoh
+ alimenteaza teza: capitolul de diseminare, activitatea didactica IMSAR,
  vizibilitate pentru articolele A1–A4
+ continutul creste NATURAL din munca de doctorat (zero munca duplicata)
− stack diferit de Java/Spring (daca scopul e portofoliu Java, nu acopera)

Hibrid posibil ulterior: biblioteca de algoritmi (A) ca modul separat,
adaugata dupa v1.0, cand exista deja infrastructura de portal.

## 3. Bugetul de timp (regula de aur)

Doctoratul are prioritate absoluta. Ecosistemul primeste MAXIM 1–2 h/sapt
(din cele 5–10 disponibile) si se opreste complet in ferestrele de sprint
(submisii, campanii, prezentari). Milestone-urile se leaga de jaloanele
tezei, nu invers.

## 4. Roadmap-ul schitat (se detaliaza la kickoff)

| Versiune | Tinta | Continut |
|---|---|---|
| v0.1 | iul 2026 | repo public structurat; curs_ros2 + TEHNOLOGII ca prim continut; README + CONTRIBUTING; CI minimal (lint + teste curs) |
| v0.5 | oct 2026 | portal MkDocs; 2 vizualizatoare web (sortare + grafuri, JS/React — puntea spre varianta A); primele 30 issues etichetate beginner/intermediate |
| v1.0 | feb 2027 | sincronizat cu publicarea P1: sectiunea "cercetare deschisa" (benchmarkurile reproduse pas cu pas); judge simplu pentru exercitii |
| v2.0 | 2028 | simulatoarele SAR ca laboratoare ghidate; material video |
| v3.0 | 2029 | sincronizat cu finalizarea tezei: ecosistemul = anexa vie a doctoratului |

## 5. Protocolul de lucru (adoptat din propunere)

Incremental, pe etape: analiza -> propunere de arhitectura -> APROBARE ->
cod -> documentatie -> teste -> issues. Nimic generat "totul odata".

## 6. Primul pas la kickoff (19.06)

1. Inventarul repo-ului "JavaScript" existent (ce aplicatii contine, ce e
   reutilizabil).
2. Decizia A / B / hibrid — pe baza acestui charter.
3. Scheletul monorepo + primele 10 issues. Atat. (1–2 h, nu mai mult.)

## 7. Ce NU se intampla inainte de 18.06

Nimic din acest document. Drumul critic: main.tex (azi), prezentarea
(sambata), campania N=5 (in mers), submisia (joi).
