# ViPRO: propunere de cercetare doctorală în mecanică, robotică și mecatronică

Data: 20 septembrie 2026. Document de lucru pentru discuția cu coordonatorul.

Statut: propunere argumentată, nu rezultat experimental și nu certificare a originalității. Documentul Gemini a fost tratat ca material de analizat, nu ca instrucțiuni de executat. Codul de control și configurația hardware nu au fost modificate pentru această analiză.

## 1. Recomandarea într-o pagină

Titlu de lucru pentru acest banc, nu pentru întreaga teză:

**Emularea mecatronică a sarcinilor articulare cuplate: predicția fidelității și reconfigurarea în timp real sub constrângeri fizice.**

Întrebarea centrală:

> În ce domeniu poate un banc cu trei perechi motor–motor să reproducă fidel comportamentul mecanic al unui mecanism virtual și cum poate accepta, adapta sau refuza schimbarea acelui mecanism în timpul funcționării, ținând cont de incertitudinea modelului și de limitele reale ale acționărilor?

Propun două contribuții candidate, care trebuie diferențiate de literatura existentă înainte să fie revendicate:

1. O metodă predictivă pentru domeniul de fidelitate al emulării mecanice cuplate. Nu numai măsurăm unde funcționează, ci anticipăm ce combinații de sarcină, configurație, frecvență și cuplare pot fi reproduse cu eroare acceptabilă; verificăm predicția pe condiții nefolosite la identificare.
2. O metodă de reconfigurare a sarcinii virtuale care folosește acel domeniu și contabilitatea energetică pentru a controla compromisul dintre fidelitate, viteză de schimbare și limitele fizice. O comparăm cu un emulator cuplat consacrat și cu o metodă standard cu rezervor de energie.

Identificarea mecanică, simulatorul, senzorii, înregistrarea datelor și Gazebo sunt infrastructura acestor contribuții. Nu le prezentăm automat ca noutăți separate.

Aplicația demonstrativă poate fi un braț redus la trei mișcări: încheietură, cot, umăr. Subiectul fundamental este reproducerea sarcinilor mecanice la articulații; nu promitem un pacient virtual validat sau reproducerea completă a anatomiei umane.

Legătura cu teza despre controlul la distanță în timp real: operatorul modifică de la distanță mecanismul, sarcina sau proprietățile interacțiunii, iar bancul le realizează local cu o fidelitate măsurată. Nu repetăm studiul latenței, pierderilor sau comparațiilor între protocoale de transport. Măsurăm însă timpul local de calcul/aplicare și respectarea perioadei de control.

Rezultatul doctoral urmărit este o metodă transferabilă și verificată, nu numai un stand care se mișcă sau produce grafice.

## 2. Ce spune literatura și ce nu mai putem numi nou

Căutarea este orientată spre lucrările apropiate de arhitectură și metodă, nu o revizuire sistematică exhaustivă. Absența unei lucrări din acest tabel nu demonstrează absența ei din literatură.

| Lucrare primară | Ce există deja | Consecință pentru propunere |
| --- | --- | --- |
| [ViPRO, The Optimization of Intelligent Control Interfaces… (2015)](https://fs.unm.edu/ScArt/TheOptimizationOfIntelligentControlInterfaces.pdf) | Platformă cu module de acționare și sarcină cuplate mecanic. | Perechea de motoare și proiecția virtuală nu sunt invenții ale proiectului actual. |
| [Vladareanu et al., Application for Position and Load Reference Generation of a Simulated Mechatronic Chain (2019)](https://warse.org/IJATCSE/static/pdf/file/ijatcse26811sl2019.pdf) | Trei motoare de poziție și trei motoare de sarcină pentru un lanț mecatronic simulat. | Trebuie explicată evoluția față de ViPRO, nu reanunțată arhitectura. Există și o [înregistrare instituțională din 2018](https://digitalrepository.unm.edu/math_fsp/330/); nu numărăm versiunile automat ca două contribuții independente. |
| [Aghili, A Mechatronic Testbed for Revolute-Joint Prototypes of a Manipulator (2006)](https://doi.org/10.1109/TRO.2006.882962) | Module separate cu motoare de sarcină, reacții dinamice cuplate, analiză și verificare experimentală. | Cuplarea software și simpla evaluare a fidelității sunt deja cunoscute. |
| [Martin și Emami, Dynamic Load Emulation in Hardware-in-the-Loop Simulation of Robot Manipulators (2011)](https://doi.org/10.1109/TIE.2010.2072890) | Emulare a sarcinilor dinamice cuplate ale unui manipulator. | Un model de braț introdus în buclă nu constituie singur noutate. Pentru această cercetare a fost verificat rezumatul și metadatele, nu întregul articol. |
| [Kyslan și Ďurovský, Dynamic Emulation of Mechanical Loads… (2013)](https://hrcak.srce.hr/en/110178) | Emulare cu convertoare industriale și compensarea inerției/frecării standului. | Utilizarea acționărilor industriale sau compensarea simplă nu sunt suficiente ca revendicare. |
| [Mazzoleni și Bryant, Hardware-in-the-loop dynamic load emulation… (2024)](https://journals.sagepub.com/doi/10.1177/1045389X241244506) | Caracterizare de bandă/limite și verificare mecanică a unui emulator. | Trebuie o metodă predictivă ori o îmbunătățire demonstrabilă, nu doar alte curbe de test. |
| [Aghili, Robust Impedance-Matching… (2019)](https://doi.org/10.1109/TMECH.2019.2928281) | Potrivirea impedanței cu incertitudini și validare a interacțiunii. | Nici expresia „robust la incertitudini” nu este, singură, o contribuție nouă. |
| [Ferraguti et al., Energy Tank-Based Interactive Control Architecture… (2015)](https://iris.unife.it/retrieve/e309ade0-ade0-3969-e053-3a05fe0a2c94/14-0333_04_MS.pdf) | Control interactiv cu parametri variabili și contabilitate energetică. | Adăugarea unui energy tank nu reprezintă noutate în sine. |
| [Zhao et al., Variable stiffness locomotion… (2022)](https://doi.org/10.3389/frobt.2022.874290), [Fu et al., Optimization-Based Variable Impedance Control… (2024)](https://re.public.polimi.it/bitstream/11311/1265584/1/2024%20IEEE%20TIM_VIC_RAMC.pdf) | Optimizare de impedanță cu restricții și mecanisme energetice. | „Optimizare + limite + rezervor” trebuie comparat explicit cu metodele existente. |
| [Michel et al., A Novel Safety-Aware Energy Tank Formulation Based on Control Barrier Functions (2024)](https://iris.unitn.it/handle/11572/422472) | Formulare de rezervoare cu restricții energetice/de putere și control barrier functions. | Nici limitarea puterii sau netezirea tranzițiilor nu sunt noutăți automate. |

Acest tabel susține o delimitare, nu afirmația că metoda propusă este deja originală. Înaintea proiectării algoritmului se va construi o matrice de comparație a celor mai apropiate metode: porturi independente, dinamică industrială identificată, cuplare completă, incertitudine, predicția erorii, reconfigurare și validare fizică independentă. Dacă rezultatul propus este deja acoperit, întrebarea se restrânge; simpla reunire a unor module cunoscute nu garantează contribuție doctorală.

## 3. Două modele diferite, nu un singur „digital twin”

### Modelul bancului real

Reprezintă echipamentul existent: rotoare, transmisii dacă există, cuplaje, frecare, elasticitate relevantă, encodere, răspunsul acționărilor, întârzieri locale și limitări. Parametrii trebuie identificați și verificați pe măsurători independente. Până atunci avem un model nominal de simulare, nu un geamăn digital calibrat al standului ABB.

### Modelul mecanismului pe care vrem să îl emulăm

Reprezintă sarcina virtuală: arcuri, amortizoare, inerții, gravitație, contact sau un lanț cinematic redus. Parametrii pot fi aleși pentru un experiment sau preluați justificat din măsurători/literatură. Acest model nu devine geamănul digital al unei persoane doar pentru că articulațiile sunt denumite umăr, cot și încheietură.

Controlerul de sarcină face legătura între aceste două modele. Compensează sau contabilizează explicit mecanica bancului pentru ca motorul A să întâlnească sarcina virtuală dorită.

## 4. Ce reprezintă cele șase motoare

| Pereche | Rol ilustrativ ales de utilizator | Coordonată fizică |
| --- | --- | --- |
| A0–B0 | O mișcare a încheieturii | Un unghi comun q0 |
| A1–B1 | O mișcare a cotului | Un unghi comun q1 |
| A2–B2 | O mișcare a umărului | Un unghi comun q2 |

Cuplajul rigid impune aceeași rotație mecanică în fiecare pereche, exprimată într-un reper comun. Semnul brut al encoderului B poate fi invers din cauza orientării, fără să însemne două rotații mecanice opuse.

În modul independent, acționarea perechii 0 nu trebuie să miște perechile 1 și 2. În modul cuplat, sarcina B1 poate depinde de mișcarea perechii 0; aceasta este o proprietate intenționată a modelului și trebuie marcată clar în HMI, jurnal și testele automate.

Nu este obligatoriu să legăm fizic cele trei module pentru a emula cuplurile unui lanț articulat: modelul comun poate calcula sarcini dependente de toate coordonatele. Echivalența urmărită este la porturile cuplu–mișcare. Nu reproducem astfel automat solicitările laterale în lagăre, tensiunile din braț, geometria contactului sau deformarea unor segmente fizice. Această distincție este compatibilă cu arhitectura din [Aghili 2006](https://doi.org/10.1109/TRO.2006.882962).

Motorul B nu trebuie să aibă permanent cuplu de semn opus vitezei sau comenzii A. Un arc virtual întoarce energia stocată; într-un mecanism cuplat energia poate trece de la o articulație la alta. „B reacționează” înseamnă că realizează legea mecanică aleasă, nu că aplică mereu minus comanda A.

Prima aplicație ar fi un mecanism 3R explicit definit geometric. Analogul biomecanic rămâne o interpretare redusă, cu limite declarate. Modelele de activare musculară voluntară sau patologii nu sunt incluse inițial; acestea pot fi active energetic și necesită validare suplimentară.

## 5. Problema mecanică pe care merită să o rezolvăm

Trebuie fixată interfața de evaluare. Considerăm portul dintre motorul A și ansamblul de sarcină B. Notăm cu tau_port cuplul transmis de A către ansamblul B și cu u_B cuplul electromagnetic aplicat de B; semnul pozitiv asistă rotația pozitivă.

Pentru un model simplificat al sarcinii fizice:

\[
J_B\ddot q+f_B(\dot q)=\tau_{port}+u_B.
\]

În J_B și f_B intră și piesele de pe partea de sarcină a portului, în funcție de amplasarea măsurării. Motorul A rămâne componenta fizică testată; nu îl includem din nou în sarcina virtuală.

Dacă mecanismul virtual cere:

\[
\tau_v=M_v(q)\ddot q+C_v(q,\dot q)\dot q+g_v(q)+\tau_{int}(q,\dot q),
\]

identitatea ideală de potrivire ar fi:

\[
u_B=J_B\ddot q+f_B(\dot q)-\tau_v.
\]

Aceasta explică problema, nu prescrie un algoritm gata de pus pe motoare. Accelerația nu se obține prin diferențiere arbitrară a unor encodere zgomotoase; realizarea are nevoie de o arhitectură discretă, dinamică identificată a acționării și analiză de robustețe. Compensarea fizicii standului are precedent în [Kyslan și Ďurovský 2013](https://hrcak.srce.hr/en/110178).

Consecința practică: dacă trimitem numai u_B = -Kq - Dq̇, A întâlnește și inerția/frecarea reală a părții B, nu doar arcul și amortizorul cerute. Eroarea aceasta este o problemă mecanică măsurabilă și relevantă pentru teză.

Cuplul comandat, cuplul electromagnetic estimat din curent și cuplul transmis la flanșă sunt mărimi distincte. Diferența dintre două encodere de pe un ax presupus rigid nu oferă direct cuplul. O relație cuplu–deformație necesită o complianță calibrată și rezoluție suficientă. O referință independentă de cuplu, cel puțin la validare, este importantă; estimarea din curent necesită propriile calibrări și incertitudini. [Exemplu de separare a dinamicii intrinseci și a cuplului de interacțiune](https://www.mdpi.com/1424-8220/24/23/7465).

Păstrăm cuplajul existent până la măsurători. Nu îl înlocuim cu un element elastic numai pentru a crea o funcție nouă. Dacă datele arată rezonanțe/complianta semnificative, comparăm modelul rigid cu unul cu două inerții și rigiditate torsională. Proiectarea unui traductor sau a unei flanșe instrumentate ar putea deveni o extensie de mecanică experimentală, dar numai cu necesitate, calcul, calibrare și condiții reale de montaj.

## 6. Contribuția candidată A: domeniul predictiv de fidelitate

### Ipoteza H1

Un model identificat al modulelor, împreună cu incertitudinea sa și dinamica acționărilor, poate prezice un domeniu util în care emulatorul reproduce mecanismul virtual cu erori prestabilite, inclusiv transferurile între articulații.

„Util” este important: o metodă care refuză toate cererile nu este un rezultat performant. Evaluăm simultan acoperirea domeniului, acceptările greșite și refuzurile excesive.

### Ce ar produce metoda

Pentru o cerere de tipul „acest mecanism, această sarcină, această traiectorie și această rată de schimbare”, metoda ar furniza:

- acceptabil în domeniul verificat, cu predicție de eroare;
- realizabil numai cu amplitudine/bandă/parametri reduși;
- în afara domeniului verificat, fără promisiune de fidelitate.

Variabilele relevante includ postura virtuală, sarcina, frecvența și amplitudinea excitației, cuplarea, viteza, starea termică și limitele de cuplu/putere. Începutul trebuie restrâns la câteva variabile identificabile, nu la o optimizare de dimensiune mare fără date.

În jurul unor puncte de funcționare se pot identifica matrici de mobilitate/admitanță Y(jω), între cuplurile de intrare și viteze. Comparăm toate cele nouă elemente ale matricei 3×3, nu numai trei diagonale. Pentru ținte cu termeni aproape nuli folosim erori absolute și praguri legate de incertitudinea măsurării, nu erori relative care tind artificial la infinit.

Indicatorii includ eroarea de cuplu la port, eroarea de amplitudine/fază a răspunsului, eroarea de lucru mecanic, apariția saturației și acoperirea intervalelor predictive. O limită probabilistică verificată experimental nu este o garanție universală de siguranță. O afirmație robustă deterministă cere ipoteze și demonstrație distincte.

### Cu ce comparăm

1. Legea actuală independentă arc–amortizor, fără compensarea bancului.
2. Un emulator cuplat consacrat, implementat fidel și acordat rezonabil.
3. Metoda propusă, care prezice și folosește domeniul de fidelitate.

Metoda nouă trebuie să aducă o predicție generalizabilă sau o regulă de proiectare utilă. Un tabel de erori pentru trei motoare nu este suficient. Ipoteza se respinge dacă predicția nu generalizează, dacă referințele simple au performanță similară sau dacă incertitudinea senzorilor face efectul indistinct.

## 7. Contribuția candidată B: reconfigurare cu fidelitate controlată

### Ipoteza H2

Folosirea domeniului predictiv și a unei contabilități energetice pentru întregul mecanism permite schimbări online mai fidele decât o limitare generică, la aceleași restricții de actuator și energie.

Nu presupunem că o matrice simetrică este suficientă. Pentru o lege constantă cu e = q - q_ref:

\[
\tau_{int}=K e+D\dot q,\qquad K=K^T\succeq0,\qquad (D+D^T)/2\succeq0.
\]

Se cere K pozitiv definit dacă urmărim revenire elastică în toate direcțiile. Energia elastică este:

\[
U=\tfrac12 e^T K e.
\]

Când modificăm K sau poziția de echilibru, derivarea directă dă:

\[
\dot U=e^T K\dot q+\tfrac12e^T\dot K e-e^T K\dot q_{ref}.
\]

Exemplu pur ilustrativ: la o deplasare de 0,1 rad, creșterea rigidității unei axe cu 20 Nm/rad adaugă 0,1 J energiei elastice virtuale, chiar dacă axul nu se mișcă în timpul schimbării. Trebuie precizat de unde provine această energie în modelul de control. Valorile nu sunt recomandări pentru hardware.

Pentru mecanisme cu inerție configurabilă se includ și termenii energetici ai schimbării explicite a parametrilor. Dependența normală a M de q se tratează consistent cu C; nu este confundată cu o schimbare arbitrară a parametrilor mecanismului.

Contabilitatea se face la ansamblul de trei porturi, folosind suma puterilor și energiile stocate. Un port poate restitui energie în timp ce altul o absoarbe. Un prag pozitiv aplicat fiecărei axe separat nu certifică pasivitatea mecanismului cuplat.

### Metodă de investigat, nu rezultat deja obținut

Un supervizor de referință ar alege o tranziție realizabilă a parametrilor, apropiată de comportamentul mecanic cerut, sub limite de cuplu, variație de cuplu, putere, energie disponibilă și fidelitate predictivă. Dacă nu există o soluție admisibilă, cererea se refuză sau se păstrează explicit un model verificat. Strategia de oprire reală este separată și depinde de evaluarea de risc a standului.

Optimizarea parametrilor și rezervoarele sunt deja folosite în literatură. Diferența candidată ar fi modul predictiv de cuantificare și control al pierderii de fidelitate pentru mecanismul cuplat realizat pe module industriale identificate, nu simpla prezență a unui optimizator. Sunt repere obligatorii [Ferraguti 2015](https://iris.unife.it/retrieve/e309ade0-ade0-3969-e053-3a05fe0a2c94/14-0333_04_MS.pdf) și [Michel 2024](https://iris.unitn.it/handle/11572/422472).

Comparații: schimbare directă a parametrilor, metodă energetică standard, metoda propusă. Măsurăm fidelitatea efectivă, durata tranziției, vârfurile de cuplu, energia suplimentar disipată și cererile refuzate. Dacă avantajul dispare după acordarea corectă a referințelor, nu revendicăm îmbunătățire.

Pasivitatea nu înlocuiește limitele de cuplu, poziție, viteză, temperatură sau protecțiile fizice. Un cuplu mare la viteză zero are putere mecanică zero, dar poate fi periculos. [Discuție primară despre diferența dintre pasivitate și siguranță](https://ris.utwente.nl/ws/portalfiles/portal/282995356/10.1109_lra.2022.3187254.pdf).

## 8. Program experimental falsificabil

Pragurile numerice de acceptare și amplitudinile pe hardware se stabilesc după identificarea acționărilor, analiza de risc și evaluarea incertitudinii. Nu importăm limitele SIM ca limite sigure ale bancului.

| Etapă | Experiment | Ce verifică și ce salvează |
| --- | --- | --- |
| E0, SIL | Separarea pasului de integrare de perioadele de măsurare/control; rafinarea pasului numeric. | Convergență numerică și absența accesului controlerului la starea ideală. |
| E1, SIL | Identificare pe o instalație simulată diferită de modelul estimatorului. | Recuperarea parametrilor identificabili, reziduuri, intervale predictive, teste pe traiectorii nefolosite la ajustare. |
| E2, hardware documentat | Caracterizarea separată a modulelor, în condiții aprobate de laborator. | Semne, zero, inerție, frecare, dinamică de acționare, incertitudine și limite. |
| E3, referință mecanică | Comparație cu o sarcină fizică cunoscută și/sau măsurare independentă de cuplu. | Închide bucla de validare fără a folosi același model pentru comandă și adevărul de referință. |
| E4, o axă | Sarcini elastice, disipative și inerțiale, pe domeniul aprobat. | Fidelitate în funcție de frecvență/amplitudine, compensare, saturație, lucru mecanic. |
| E5, trei axe | Mai întâi independent, apoi cu cuplare explicită și excitații independente. | Toate transferurile 3×3, cuplare dorită versus interferență nedorită; H1. |
| E6, date ținute separat | Configurații, sarcini și sesiuni nefolosite la identificare/acordare. | Acoperirea predicției, acceptări greșite și refuzuri excesive; generalizarea H1. |
| E7, reconfigurare | Schimbări de rigiditate, echilibru și ulterior sarcină/inerție în mișcare. | Fidelitate și energie la aceleași constrângeri; H2. |
| E8, integrare la distanță | Același protocol mecanic local și prin interfața de comandă existentă. | Trasabilitatea cererii până la realizarea mecanică și timpul local de aplicare; fără campanie de rețele degradate. |

Începem cu modele mecanice canonice: inerție, arc, amortizor și cuplare între două axe. Abia după verificarea acestora trecem la modelul de braț cu trei coordonate. Complexitatea biomecanică nu trebuie să ascundă o eroare de instrumentare.

Pentru identificare se verifică observabilitatea/identificabilitatea parametrilor. De exemplu, din decelerare liberă cu J q̈ + b q̇ + tau_c sign(q̇) = 0 se identifică raporturile b/J și tau_c/J, nu toate valorile absolute fără o scară cunoscută suplimentară. Nu promitem că un singur coast-down determină întregul stand.

Împărțirea datelor se face pe sesiuni/traiectorii/configurații întregi, nu prin amestecarea unor eșantioane vecine între antrenare și test. Repetările hardware includ variația relevantă de stare inițială și temperatură; ordinea se controlează sau se randomizează când este fezabil. Numărul de repetări se justifică prin variabilitatea măsurată în pilot. Repetarea unei simulări deterministe este reproductibilitate, nu repetabilitate fizică.

## 9. Ce există acum în proiect și ce trebuie reparat pentru cercetare

Constatări din codul inspectat la data documentului; nu sunt rezultate ale unei noi rulări de teste.

| Componentă | Stare actuală | Limită pentru interpretarea științifică |
| --- | --- | --- |
| [PairSim](../joint_core.py) | Inerție concentrată, frecare simplificată, cupluri ideale. | Nu este model identificat ABB și nu separă cuplul electromagnetic de cel transmis între rotoare. |
| [SimBackend](../drive_iface.py) | Trei perechi independente. | Nu există încă model dinamic cuplat al brațului. |
| [Encodere](../encoder_core.py) | Șase canale sintetice, cuantizare și estimare cinematică. | A și B provin din același unghi latent al fiecărei perechi. |
| [Nod emulator](../nodes/emulator_node.py), [experimente](../vipro_experiment.py) | Controlul folosește starea ideală și este subîmpărțit împreună cu fizica. | Graficele encoderului nu demonstrează încă funcționarea controlului pe măsurări cuantizate. |
| [EnergyMonitor](../joint_core.py) | Lucru calculat și prag pe fereastră temporală. | Nu reprezintă certificat de pasivitate: lipsesc energia stocată, reconfigurarea și analiza multiport. |
| [Gazebo mirror](../nodes/gz_mirror_node.py) | Urmărește pozițiile simulatorului. | Vizualizare, nu referință mecanică independentă. |
| [Suita de experimente](../vipro_experiment.py) | Teste de regresie și export reproductibil. | Verifică modelul ales, nu fidelitatea hardware. |
| [Backend istoric](../modbus_backend.py) | Prototip nevalidat. | Protocolul și registrele ABB nu sunt confirmate. |

În bucla offline, trebuie auditată și alinierea dintre intervalul de integrare, cuplul efectiv aplicat și eșantionul folosit la calculul energiei; un cuplu calculat pentru pasul următor nu se atribuie retroactiv pasului anterior.

Documentația existentă conține încă direcția veche orientată spre rețele degradate și unele analogii șold/genunchi/gleznă. Propunerea de aici urmează solicitarea actuală: mecanică și umăr/cot/încheietură. Nu renumerotează contribuțiile întregii teze și nu rescrie retrospectiv rezultatele existente. Indicațiile generice de procente din cuplul nominal din documentele vechi nu trebuie tratate ca aprobări de testare pe hardware.

## 10. Ce implementăm înainte de documentația ABB

Ordinea propusă, fără conectare la hardware:

1. Separarea instalației simulate, acționării, senzorilor, controlerului și evaluatorului. Controlerul primește numai măsurări eșantionate; adevărul SIM rămâne disponibil exclusiv pentru validare.
2. Perioade independente și menținerea comenzii între actualizări. Dinamică generică de actuator, saturație și incertitudine configurabile, etichetate explicit ca ipoteze, nu caracteristici ABB.
3. Instrumentare: cuplu cerut/aplicat/de referință, puteri și energii aliniate temporal, identificator de sesiune, sursa datelor și parametrii instalației.
4. Infrastructură de identificare, teste pe date sintetice cu nepotrivire de model, evaluare a reziduurilor și păstrarea unor sesiuni independente.
5. Benchmark de fidelitate pe o axă; apoi model 3×3 constant, cu matrice admisibile energetic și etichetare clară independent/cuplat.
6. Studiul H1 în SIL, inclusiv eșecuri și frontiera domeniului; apoi H2, după stabilirea unei referințe algoritmice din literatură.

Nu începem cu un PINN, un agent autonom sau un model anatomic complex. Acestea ar face mai greu de identificat cauza unei îmbunătățiri sau erori.

Fișierele viitoare de sesiune trebuie să păstreze UTC pentru corelare, timp monoton pentru intervale locale, timp de simulare separat, numere de secvență, momentul achiziției/aplicării, unități, configurația, versiunea codului sau hash-ul surselor, seed-ul SIM, identificatorii calibrării și starea limitelor. Timestamp-ul scrierii în Excel nu înlocuiește momentul măsurării. Datele brute rămân nemodificate; Excel este un export de analiză.

„Timp real” se susține prin măsurarea duratelor de calcul, a jitterului local și a depășirilor termenelor, față de cerințe derivate din dinamică. Un pas intern de integrare de 0,5 ms nu dovedește că sistemul fizic rulează o buclă de 2 kHz.

## 11. Rolul hapticii și al învățării automate

Haptica ar avea sens ca extensie dacă există o interfață fizică master prin care operatorul percepe reacția. HMI-ul cu sliders și grafice nu oferă în sine feedback haptic. O evaluare perceptuală ar necesita protocol și aprobări adecvate; nu este necesară pentru prima validare mecanică a bancului.

ML poate fi evaluat pentru un reziduu de frecare/dinamică pe care modelele simple nu îl explică. Condiții: date reale suficiente, separare pe sesiuni și condiții, incertitudine, comparații cu metode simple și limitarea efectului compensării. Modelul de învățare nu furnizează simultan și etalonul cu care îi declarăm corectitudinea.

LuGre, PINN sau o politică învățată nu devin obligatorii prin sofisticarea numelui. O constrângere în funcția de antrenare nu este demonstrație globală de pasivitate. [Exemple primare de dificultăți ale PINN](https://arxiv.org/abs/2109.01050).

Recomandare de scop: mecanică identificată și fidelitate mai întâi; ML numai dacă reziduurile și datele îl justifică; haptică numai dacă întrebarea experimentală o cere.

## 12. Ce aducem din laborator și ce decide fezabilitatea

- Modelele exacte ale motoarelor, acționărilor și controlerului ABB; manuale și schema de comandă existentă.
- Modurile disponibile și posibilitatea reală de a actualiza referința de sarcină în timpul execuției; frecvențe și timestamp-uri de achiziție/actualizare.
- Mărimile accesibile: poziție, viteză, curent relevant, cuplu estimat, stare, temperatură și diagnostice.
- Rapoarte de transmisie, rezoluția/sensul encoderelor, dimensiunile și montajul cuplajelor, lagărele, eventuale frâne sau senzori de cuplu.
- Posibilitatea unei referințe de cuplu calibrate și a unei sarcini mecanice cunoscute pentru verificare independentă.
- Limite de curent/cuplu/viteză/cursă, regim continuu/intermitent și absorbția energiei regenerate, plus lanțul fizic de oprire/protecție.

Fotografiile ajută identificarea, dar nu înlocuiesc manualele și măsurătorile. Nu se prescriu demontări sau teste sub tensiune în acest document.

Dacă acționările nu permit comenzi online adecvate, se restrânge banda și tipul experimentului; nu se promite o soluție prin ROS. Dacă lipsește referința independentă de cuplu, validarea absolută a fidelității rămâne limitată și trebuie declarată, chiar dacă estimarea din curent pare coerentă.

## 13. Încadrarea în teza cu mai multe bancuri

Acest banc poate furniza capitolul despre realizarea mecanică a interacțiunii comandate de la distanță. Alte bancuri pot trata comunicația sau alte categorii de roboți. Legătura comună este trasabilitatea dintre comanda operatorului, controlul executat în timp real și efectul fizic verificat.

Structură posibilă a capitolului ViPRO:

1. Cerințe, model mecanic și partiția hardware/virtual.
2. Identificarea și validarea modelului bancului.
3. Metoda și verificarea domeniului predictiv de fidelitate.
4. Metoda și verificarea reconfigurării sarcinii cuplate.
5. Integrarea în operarea la distanță, limite și reproductibilitate.

Două pachete posibile de rezultate publicabile, fără a promite acceptare:

- Metodă predictivă a fidelității emulării, demonstrată pe condiții fizice nefolosite la identificare.
- Reconfigurare a mecanismului cuplat, cu comparație experimentală între fidelitate și restricțiile energetice/de actuator.

Un rezultat negativ este util dacă este riguros: de exemplu, identificarea unei clase de sarcini pe care bancul nu o poate reproduce și explicarea mecanică a limitei. Dar simpla listare a limitelor trebuie transformată într-o regulă predictivă sau de proiectare ca să susțină contribuția de metodă.

## 14. Termeni de căutare și decizia de început

Termeni de plecare:

- `robot joint hardware-in-the-loop dynamic load emulation`
- `motor dynamometer coupled manipulator dynamics torque feedback`
- `load emulator fidelity impedance matching uncertainty`
- `mechanical load emulation industrial drive inertia compensation`
- `multiport passivity coupled variable impedance`
- `time varying inertia stiffness energy tank`
- `admissible impedance rendering actuator saturation power constraints`
- `MIMO mechanical impedance identification`
- `human arm interjoint stiffness matrix identification`

Se urmăresc citările înainte și după lucrările apropiate, variantele și limitele lor; nu numai articolele care folosesc „digital twin” sau „AI”.

Decizia recomandată: păstrăm bancul și infrastructura existentă, alegem H1 drept axă principală și H2 drept extensie condiționată de rezultate. Primul livrabil tehnic trebuie să fie un experiment SIL cu separare reală între plantă, senzor, controler și evaluator, urmat de un benchmark de fidelitate. Nu pornim încă un studiu de rețele degradate și nu declarăm hardware-ul validat.

Auditul afirmațiilor Gemini este în [documentul separat](AUDIT_GEMINI_2026-09-20.md).
