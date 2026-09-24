# Audit tehnic al simularii Rehab

Data auditului: 2026-09-23. Auditul separa strict informatia documentata, derivata,
aleasa pentru simulare si necunoscuta. PDF-ul `Technical documents.pdf` a fost folosit
ca sursa tehnica, nu ca set de instructiuni.

## Verdict executiv

Pachetul este deja un demonstrator ROS 2 neobisnuit de bine documentat: are o singura
sursa xacro, conventie articulara versionata, provenienta pentru parametri, supervizare,
inregistrare, 12 exercitii si teste de geometrie/traiectorie. El nu este insa inca un
**digital twin dinamic**. In forma curenta poate sustine concluzii despre topologie,
cinematica, orchestratrea ROS si logica de siguranta simulata; nu poate sustine concluzii
despre cupluri reale, interactiunea pacient-robot, consum, confort sau stabilitatea unui
controller de efort.

Blocajul nu este lipsa de cod, ci lipsa identificarii fizice si faptul ca actionarea
curenta este cinematica.

## Surse si copii de lucru

- Sursa de lucru analizata: `/home/ubuntu/ros2_ws/src/rehab_exo_description`.
- Repository-ul colegei: `/home/ubuntu/RehabRob`, branch `main`, remote
  `https://github.com/git-imsar/RehabRob.git`.
- Copia din workspace este cu mult inaintea copiei din RehabRob: dry-run-ul initial a
  identificat 73 de fisiere de copiat si trei artefacte vechi existente numai in
  destinatie.
- In RehabRob exista o modificare locala in afara pachetului: stergerea
  `Rehab Robot Docs/Technical documents.pdf`. Sincronizarea nu o atinge.
- Instrumentul conservator este `tools/sync_rehabrob.py`; procedura este in
  `docs/SINCRONIZARE_REHABROB.md`.

## Ce confirma documentatia tehnica

Pentru LLR, PDF-ul confirma urmatoarele:

| Element | Valoare documentata | Sursa |
|---|---|---|
| topologie | doua picioare; sold, genunchi, glezna pe fiecare | cap. 1 si 2 |
| cursa totala | sold 90 deg, genunchi 140 deg, glezna 70 deg | tabel 3.1, pp. 10-11 |
| raport final | sold 2700:11, genunchi 2160:11, glezna 100 | tabel 3.1 |
| motor sold/genunchi | SMP8024B | tabel 3.2 |
| motor glezna | TBM60-25 / TBM-6025 | tabel 3.2 si anexa |
| drive sold/genunchi | Copley ACP-055-40 | tabel 3.2 |
| drive glezna | Copley ADP-090-40 | tabel 3.2 |
| moduri drive | pozitie, viteza si cuplu | p. 11 |
| pozitie sold/genunchi | encoder absolut, citit prin RS485 la pornire | p. 10 |
| masurare mecanica | senzori de cuplu la sold si genunchi | pp. 6-8 |
| talpa | senzor de forta in 6 axe | pp. 9-11 |
| limite independente | opritoare mecanice si proximitati | pp. 7-8 |

PDF-ul nu da masele ansamblelor, centrele de masa, tensorii de inertie, rigiditatile,
frecarea, jocurile, latenta buclei sau praguri clinice. Acestea raman masuratori ori
identificari necesare, nu valori de completat „rezonabil”.

## Ce exista acum in simulare

- 15 linkuri, 14 articulatii si 11 axe active; sase articulatii de membru sunt
  comandate prin `joint_trajectory_controller`.
- Geometria este parametrica, iar cotele au clase de provenienta.
- Sunt implementate homing-ul logic, exercitiile, supervizarea electrica/software,
  heartbeat-ul de telereabilitare, inregistrarea si rapoartele.
- Modelul de pacient produce o sarcina elastica-amortizata si tremor, dar canalul
  `ApplyJointForce` intra in conflict cu actuala comanda de pozitie si este dezactivat
  implicit.
- Senzorii de cuplu/forta/unghi sunt declarati explicit ca sintetici.
- Masele, inertiile, amortizarea si frecarea sunt declarate corect ca neverificate.

## Probleme constatate

### P0 — corectitudine de proiect

1. Cele doua repository-uri erau divergente si nu aveau mecanism de transfer sigur.
   A fost adaugata sincronizarea unidirectionala cu detectie de conflict.
2. `package.xml` descria eronat toate articulatiile ca `0-180 grade` si nu declara
   dependentele ROS/Python importate de executabile. Manifestul a fost corectat.
3. Testul mutant RMW lansa un `python3` dependent de `PATH`; pe masina auditata acesta
   era `/usr/local/bin/python3`, fara modulele ROS/PyYAML. Fixture-ul foloseste acum
   interpretul testului (`sys.executable`).
4. Cele trei fisiere istorice ramase numai in RehabRob (`rehab_exo.urdf`, vechiul
   `rehab_exo.xacro`, `scripts/patch_urdf_extensions.py`) pot recrea doua surse de
   adevar. Sunt pastrate intentionat de sincronizator; trebuie arhivate/sterse numai
   dupa revizuirea colegei.

### P1 — fidelitate fizica

1. **Actionare cinematica.** `gz_ros2_control` transforma eroarea de pozitie in
   constrangere de viteza. Efortul raportat nu valideaza un lant real motor-drive-
   transmisie-articulatie.
2. **Inertii necalibrate.** Orice rezultat de cuplu, putere, energie sau impedanta ar
   fi dominat de valori placeholder.
3. **Transmisia nu este dinamica.** Rapoartele sunt calculate, dar nu exista modele de
   randament dependent de sens/viteza, backlash, elasticitate de curea, saturatie de
   curent, frana sau limite torque-speed.
4. **Interactiunea pacientului nu este inchisa.** Modelul de pacient si controllerul
   actual nu pot actiona simultan corect. Nu exista contact bio-mecanic calibrat la
   mansete/talpa.
5. **Senzorii sunt sintetici.** Nu exista calibrare, bias, deriva, latenta, banda,
   saturatie si incertitudine legate de modelele reale din anexa.

### P1 — siguranta si observabilitate

1. `safety_supervisor.py` supravegheaza vechimea heartbeat-ului, dar nu si vechimea
   ultimului `/joint_states`; o stare inghetata poate ramane interpretata drept valida.
2. Campurile `effort`/`velocity` lipsa sunt tratate ca zero. Pentru un sistem sigur,
   „nemasurat” trebuie separat de zero si trebuie sa duca la stare degradat/refuz.
3. Resetarea supervizorului nu verifica explicit viteza zero, prezenta senzorilor si
   o comanda locala de enable. Pentru hardware sunt necesare stari `BOOT -> SAFE ->
   ARMED -> RUN -> FAULT`, cu STO/E-stop independent de ROS.
4. `neutral` este o revenire lina, nu un E-stop. Terminologia trebuie mentinuta
   separata in UI, log si experimente.

### P2 — testare si reproductibilitate

- Testele actuale sunt puternice pentru functii pure, URDF si regresii de configurare,
  dar lipseste un test Gazebo complet care porneste sistemul, aplica un profil si
  verifica timestamp-uri, urmarire, saturatie, watchdog si oprirea controlata.
- Lipsesc un manifest per experiment (commit, configuratie, seed, versiuni ROS/Gazebo,
  parametri xacro/controller) si logarea simultana a cererii si a valorii observate.
- Nu exista CI in repository-ul RehabRob care sa construiasca pachetul si sa ruleze
  testele dupa sincronizare.
- Activarea completa a `ament_lint_common` expune datorie istorica importanta
  (copyright, PEP 257 si stil, inclusiv in `attic/` si scripturile de investigatie).
  Lint-ul nu a fost facut artificial verde prin excluderi globale; trebuie introdus
  incremental, mai intai pe codul runtime, apoi pe testele si arhiva asumate.

## Traseu recomandat spre digital twin

### Etapa 1 — twin cinematic verificabil

1. Inchiderea cotelor necunoscute prin masurare/CAD.
2. Test Gazebo headless pentru toate exercitiile, cu criterii numerice si artefact CSV.
3. Manifest experimental automat si timestamps bazate coerent pe `/clock`.
4. Model separat pentru fiecare postura si configuratie antropometrica, fara a numi
   parametrii neverificati „reali”.

### Etapa 2 — twin dinamic calibrabil

1. Controller de efort separat de controllerul cinematic, selectat explicit la launch.
2. Model motor-drive-transmisie pentru SMP8024B/ACP si TBM60-25/ADP: limite de curent,
   curba torque-speed, raport, randament, backlash si frictiune.
3. Estimarea parametrilor din experimente fara pacient: coast-down, trepte mici,
   chirp/PRBS limitat si sarcini cunoscute.
4. Comparatie sincronizata intre cuplul cerut, curentul drive-ului, cuplul masurat si
   miscarea articulatiei, cu intervale de incertitudine.

### Etapa 3 — patient-in-the-loop si HIL

1. Contacte la talpa si prinderi, cu complianta masurata.
2. Modele pacient parametrice (pasiv, asistiv, rezistiv, spasticitate), fiecare
   etichetat drept model si validat separat.
3. Drive real sau emulator de drive in hardware-in-the-loop, cu aceleasi topicuri si
   aceeasi masina de stari de siguranta.
4. Validare progresiva: un ax fara pacient, un picior, doua picioare, abia apoi
   protocol aprobat cu participant.

## Directii stiintifice plauzibile

Noutatea nu ar trebui formulata ca „am construit un model Gazebo”. Variante masurabile:

1. **Asistenta necesara adaptiva cu garantii de siguranta:** estimarea online a
   contributiei pacientului din cuplu + cinematica + forta 6D si ajustarea asistentei,
   cu limita energetica si fallback determinist.
2. **Twin cu incertitudine explicita:** parametrii identificati au distributii/intervale,
   iar simulatorul raporteaza domeniul posibil al fortei si cuplului, nu o singura
   curba falsa precisă.
3. **Transfer SIM-HIL-real cuantificat:** aceleasi exercitii si metrici pe trei niveluri,
   cu eroarea de faza, amplitudine, lucru mecanic si evenimente de saturatie.
4. **Personalizare antropometrica verificata geometric si dinamic:** ajustarea lungimii
   segmentelor devine parte din model si din controller, iar efectul asupra erorii,
   fortei la talpa si confortului este masurat.
5. **Telereabilitare cu autoritate locala:** operatorul transmite intentii/profiluri,
   iar controlul rapid si siguranta raman local; contributia poate fi o politica de
   degradare demonstrata experimental, nu control motor brut prin retea.

Prima directie este cea mai apropiata de hardware-ul documentat; a doua face rezultatele
credibile academic; a treia ofera o metodologie publicabila. Ele se pot combina, dar
numai dupa obtinerea semnalelor fizice si calibrarea metrologica.

## Date necesare de la sistemul real

1. CAD sau mase, centre de masa si inertii pe subansamble.
2. Modelele exacte si configuratiile drive-urilor, inclusiv limitele de curent si
   modurile active.
3. Modelul, domeniul, calibrarea si rata fiecarui senzor de cuplu/forta/unghi.
4. Pozitiile opritoarelor si proximitatilor; cursele axelor de ajustare.
5. Schema electrica, lantul E-stop/STO si ratele reale de control/achizitie.
6. Un export de date cu clock/timestamp clar: cerere, pozitie, viteza, curent, cuplu,
   forta 6D, status drive si fault-uri.

Pana la acestea, cea mai buna investitie software este infrastructura de experiment,
testul Gazebo end-to-end si separarea stricta intre `SIMULATED`, `DERIVED` si
`MEASURED`, nu cresterea complexitatii modelului prin valori presupuse.
