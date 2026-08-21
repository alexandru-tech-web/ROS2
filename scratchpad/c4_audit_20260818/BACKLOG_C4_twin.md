# Backlog propus -- digital twin LLR (C4). PROPUNERE, nu decizie.

Calibrare: 5-10 h/saptamana, o sesiune ~3 h. Orice item peste 2-3 sesiuni (~9 h) e spart.
Estimarile sunt ESTIMARI, nu angajamente.
DoD C4: fidelitate CINEMATICA + trafic ROS 2 REALIST. Dinamica de forta NU intra.

---------------------------------------------------------------------------
## F0 -- Pinuirea RMW in bringup + diagnostic serviciu CM        [2-3 h]

SCOP. Bringup-ul isi declara explicit RMW-ul, in loc sa il ia din environment.
Masurat azi: RMW_IMPLEMENTATION nesetat -> rmw_fastrtps_cpp; niciun launch nu-l pinuieste.
Intr-un proiect a carui teza e ca alegerea middleware-ului schimba comportamentul, a o lasa
implicita e anti-reproducibilitate.

CRITERIU DE ACCEPTARE. SetEnvironmentVariable("RMW_IMPLEMENTATION", ...) in GroupAction
scoped, tiparul validat la C3 etapa 1c; argument de launch rmw:=cyclonedds|zenoh|fastrtps;
rularea logheaza RMW-ul efectiv la pornire, si un test verifica potrivirea (nodul iese cu
cod nenul daca rclpy.get_rmw_implementation_identifier() nu se potriveste -- tiparul din
transport_agent.py).

CE NU FACE. Nu repara starvation-ul serviciului CM (vezi mai jos); nu schimba nimic in
descriere; nu adauga controllere.

DEPENDINTE. Niciuna. Se poate face azi.

DECIZIE CERUTA. Care e RMW-ul implicit al twin-ului: cyclonedds (castigatorul C2 pe 12/13
celule) sau zenoh (subiectul contributiei)? Recomandarea mea: cyclonedds ca implicit,
zenoh ca optiune -- twin-ul trebuie sa mearga, comparatia se face la F3.

SUBITEM F0b (diagnostic, 2 h). adjust_position_controller nu urca. Masurat: serviciul
/controller_manager/list_controllers EXISTA in fereastra de esec, dar nu raspunde; un
timeout de 60 s nu ajuta. Ipoteza: executorul CM e infometat de bucla de update Gazebo
dupa activarea celui de-al doilea controller. De verificat: rulare headless (gz -s) si
executor multi-threaded. NU e confirmat -- e ipoteza cu dovezi, nu diagnostic.

---------------------------------------------------------------------------
## F1a -- Sursa canonica unica: xacro care GENEREAZA URDF-ul      [6-8 h]

SCOP. Defectul-radacina: trei surse de adevar (rehab_exo.urdf 620 linii, rehab_exo.xacro
125 linii care descrie alt robot, patch_urdf_extensions.py care MUTEAZA urdf-ul in loc).
Ramane UNA: xacro parametrizat, din care URDF-ul se genereaza la build.

CRITERIU DE ACCEPTARE.
 - xacro-ul reproduce topologia URDF-ului livrat: 15 linkuri, 14 jointuri, 11 DOF active;
 - continutul lui patch_urdf_extensions.py devine OPTIUNI de xacro (gazebo:=true/false,
   senzori:=true/false), nu mutatie post-hoc; scriptul dispare;
 - selftest pe URDF-ul GENERAT (echivalentul lui validate.py): numar de DOF, limitele
   fiecarui joint, simetria stanga-dreapta joint cu joint, prezenta plugin-urilor cand
   flag-ul e activ si ABSENTA lor cand nu e (control negativ);
 - check_urdf verde pe artefactul generat;
 - README regenerat din xacro, nu din memorie (azi documenteaza descrierea gresita).

CE NU FACE. NU schimba nicio limita si niciun numar -- e refactorizare cu invariant:
URDF-ul generat trebuie sa fie echivalent cu cel livrat azi. Alinierea la spec e F1b.

DEPENDINTE. Niciuna. Atinge GAP 2 (lungimile devin parametri, dar raman aceleasi cifre).

DECIZIE CERUTA. Niciuna -- e curatenie pura, cu invariant verificabil.

---------------------------------------------------------------------------
## F1b -- Alinierea cinematica la Tabelul 3.1 + limita duala      [4-6 h]

SCOP. Cursele locale vs spec: sold 65,89 vs 90; genunchi 100,27 vs 140; glezna 68,75 vs 70.
Plus mecanismul dual de la sold (PDF p.7), azi absent.

CRITERIU DE ACCEPTARE. Cursele totale = 90/140/70 grade; al doilea set de limite exista ca
postura:=sezut|culcat; selftestul din F1a verifica AMBELE seturi; fiecare impartire min/max
poarta in comentariu eticheta "ipoteza locala (GAP 4)".

CE NU FACE. NU pretinde ca stie zeroul anatomic. NU atinge masele, senzorii, traficul.

DEPENDINTE. F1a. Atinge GAP 4 (impartirea min/max ramane necunoscuta).

DECIZIE CERUTA -- e a ta, si o pun cu implicatii, fara sa aleg:
 OPTIUNEA A: pastrez conventia autorului initial ("Postura zero = SEZUT", declarata in
   antetul URDF-ului) si adaug setul complet ca postura:=culcat.
   + continuitate cu ce exista; antetul devine adevarat, nu contrazis
   + cele 65,89 grade capata sens retroactiv (setul de sezut)
   - zeroul nu corespunde niciunei conventii anatomice standard
   - orice comparatie cu literatura cere o conversie explicita
 OPTIUNEA B: redefinesc zeroul anatomic conform PDF si recalculez ambele seturi.
   + comparabil direct cu literatura si cu PDF-ul
   - invalideaza toate traiectoriile din launch-urile de exercitii (sold/genunchi/glezna/
     combinat) si config/patient_demo.yaml -- trebuie recalculate
   - antetul URDF-ului si conventia autorului initial se pierd

---------------------------------------------------------------------------
## F1c -- Restatusarea maselor + pacientul sub flag               [2-3 h]

SCOP. 14 mase (total 95,2 kg) si inertiile izz sunt cifre fara sursa; spec-ul le are GAP 1.
NU se sterg -- Gazebo are nevoie de inertii ca sa ruleze -- dar isi schimba statutul.

CRITERIU DE ACCEPTARE. Fiecare masa/inertie poarta comentariu "PLACEHOLDER NEVERIFICAT --
doar pentru simulare, NU pentru concluzii"; human_torso (32 kg) devine pacient:=true/false;
cu pacient:=false masa robotului e raportata separat de cea a pacientului; un test verifica
ca ambele variante trec check_urdf.

CE NU FACE. NU inventeaza mase mai bune. NU justifica cifrele. NU deschide F4.

DEPENDINTE. F1a. Atinge GAP 1 si GAP 7 (sarcina maxima pacient ramane necunoscuta).

DECIZIE CERUTA. Confirmi ca pacientul ramane in twin (util pentru replay-ul C4) sau iese?

---------------------------------------------------------------------------
## F2 -- Interfata ROS 2 realista                                  [6-8 h]

SCOP. Twin-ul publica azi 9,997 Hz x ~409 octeti = ~4 KB/s, fata de referinta C1/C2 de
50 Hz x 4096 B = ~200 KB/s. Factor ~50 pe banda. Traficul trebuie sa fie cel masurat in
teza, nu unul de jucarie.

ARHITECTURA PROPUSA -- trei cai, si NU propun umflarea artificiala:
 (a) rata: joint_states la 50 Hz, ca in benchmark. Ieftin, onest, imediat.
 (b) volum: prin TELEMETRIE COMPLETA, nu prin umplutura -- familia de senzori din F5 la
     ratele ei reale. Suma lor se apropie de referinta prin continut real.
 (c) payload exact de benchmark: doar acolo unde replay-ul C2 o cere, iar sarcina
     transportata e CHIAR traficul redat din arhive (F3), nu octeti inventati.
Nucleu pur cu _selftest (generarea traiectoriei, serializarea, contabilitatea de rata),
nod ROS subtire deasupra.

CRITERIU DE ACCEPTARE. ros2 topic hz/bw masoara rata si banda tinta pe fiecare topic;
selftestul verifica contabilitatea de rata fara ROS; un test de integrare arata ca rata
ceruta e si rata livrata (nu doar configurata).

CE NU FACE. NU adauga umplutura ca sa atinga o cifra. NU pretinde fidelitate dinamica.

DEPENDINTE. F1a (descriere stabila). F5 pentru calea (b). F3 pentru calea (c).

DECIZIE CERUTA. Care din cele trei cai intra si in ce ordine? Recomandarea mea: (a) acum,
(b) impreuna cu F5, (c) doar daca F3 chiar cere payload identic.

---------------------------------------------------------------------------
## F3 -- Integrarea cu replay-ul C2                                [8-10 h -> SPART]

SCOP. Redarea arhivelor C2 -> comenzi catre twin + RViz. Criteriu din DoD-ul tau: o
sesiune moarta din campanie se VEDE murind pe twin.

SPART IN DOUA, altfel nu incape:
 F3a (4-5 h) cititor de arhiva -> flux de comenzi. Nucleu pur: citeste un director de
   rulare C2 (esantioane.csv / transport_p*.csv), reconstruieste secventa cu golurile ei,
   si o expune ca generator temporizat. _selftest pe o rulare cu n0 cunoscut.
 F3b (4-5 h) legarea la twin + RViz: comenzile ajung la JTC, iar o rulare moarta produce
   inghetarea vizibila a twin-ului. Criteriu de acceptare: doua rulari din aceeasi celula,
   una vie si una n0, dau comportamente vizibil diferite, inregistrate.

CE NU FACE. NU modifica arhivele (~/DATE_CAMPANIE ramane sigilat, doar citire). NU
recalculeaza statistici de campanie -- consuma ce exista.

DEPENDINTE. F1a, F0. Arhivele C2 sigilate (read-only). Niciun GAP din spec.

DECIZIE CERUTA. Ce celula/celule se redau in demonstratia canonica? Sugestia mea:
ge_15_8 zenoh 64 KB (2/10 n0) -- are si supravietuitori, si morti, deci contrastul se vede.

---------------------------------------------------------------------------
## F4 -- Dinamica Gazebo fidela                     [IN AFARA SCOPULUI]

Ramane afara pana apar inertii masurate sau CAD. Motiv: GAP 1-3 din spec. Orice cifra
dinamica pe placeholder-ele din F1c ar fi fabricatie cu aparenta de rigoare.
Conditie de reactivare: CAD sau inertii din documentatia fizica.

---------------------------------------------------------------------------
## F5 -- Senzori sintetici ca topicuri                             [6-8 h]

SCOP. Azi twin-ul publica DOAR /joint_states. Spec-ul cere patru familii: cuplu
sold/genunchi (M2210B), forta 6D sub talpa (TR69-1500), unghi glezna (BWK216), rigla de
gamba (406). Toate LIPSESC.

CRITERIU DE ACCEPTARE. Patru topicuri, la ratele lor, cu tipurile ROS potrivite
(WrenchStamped pentru 6D, etc.); gamba modelata corect: comanda in bucla DESCHISA +
topic separat de lungime masurata (particularitatea din PDF p.9 pe care twin-ul o pierde
azi); fiecare mesaj poarta in header o eticheta "sintetic, fara pretentie de fidelitate
fizica"; nucleu pur cu _selftest pentru generarea semnalelor.

CE NU FACE. NU pretinde fidelitate fizica. NU inlocuieste senzorii reali. NU deschide F4.

DEPENDINTE. F1a. Exista deja un drum local de senzori (3 IMU la 100 Hz injectate de
patch_urdf_extensions.py) pe care F5 se poate aseza -- dar IMU-urile NU sunt in spec si nu
tin locul familiilor cerute.

DECIZIE CERUTA. Senzorii sunt sintetici (semnal plauzibil, etichetat) sau derivati din
starea simularii (ex. forta 6D din contactul Gazebo)? A doua e mai scumpa si atinge F4.
