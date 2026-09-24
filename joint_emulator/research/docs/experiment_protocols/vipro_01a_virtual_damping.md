# ViPRO-01A — fidelitatea unei sarcini de amortizare virtuală

Status: `PLANNED_BLOCKED_ON_VIPRO_00`  
Tip: primul experiment fizic, o singură pereche A/B  
Versiune protocol: `vipro-01a/1.0.0`  
Metrici: `vipro-fidelity-metrics/1.1.0`  

## 0. Domeniu și reguli epistemice

ViPRO-01A va măsura diferența dintre o sarcină mecanică virtuală cerută și
sarcina realizată fizic pe o pereche A/B cuplată rigid. Documentul proiectează
experimentul; nu autorizează mișcare sau energizare.

Inventarul actual demonstrează numai lanțul SIM. Modelele motoarelor și
drive-urilor, modurile de control, maparea fizică, limitele, senzorul de cuplu,
ratele și lanțul de siguranță sunt `UNKNOWN`. Niciun număr din SIM nu devine
limită fizică. Orice câmp nerezolvat păstrează `value: null` și
`provenance: UNKNOWN` în manifest.

Separarea semantică obligatorie este:

```text
tau_d_model       model virtual, înainte de limitări
       ↓
tau_B_requested   cererea efectivă după semn, limitări și rate-limit
       ↓
drive B / plantă fizică
       ├── tau_B_drive_estimate   DERIVED/IDENTIFIED; diagnostic
       └── tau_port_sensor        MEASURED independent; referință primară
```

Nici `tau_d_model`, nici comanda, curentul sau estimarea drive-ului nu sunt
cuplu fizic independent.

## 1. Întrebarea de cercetare

Pentru o pereche A/B și un domeniu sigur, declarat înaintea campaniei, cu ce
eroare, întârziere și eroare energetică realizează portul mecanic sarcina de
amortizare virtuală solicitată, și cum depinde această fidelitate de
coeficientul de amortizare, amplitudinea și frecvența excitației?

Rezultatul trebuie să fie o hartă de fidelitate și incertitudine pe domeniul
testat, nu afirmația globală că bancul este „fidel”.

## 2. Ipoteze nule și alternative

Înainte de campania de confirmare se fixează din cerința aplicației și bugetul
metrologic o margine de echivalență `epsilon_F`; aceasta nu se estimează din
aceleași trial-uri folosite pentru confirmare.

Ipoteza primară de echivalență:

- `H0_F`: diferența cerut–realizat nu este demonstrată ca fiind în interiorul
  marginii `epsilon_F` pe domeniul declarat;
- `H1_F`: diferența este în interiorul marginii `epsilon_F`, cu incertitudinea
  și nivelul de încredere preregistrate.

Ipoteza secundară privind factorii:

- `H0_DFA`: `D_v`, amplitudinea, frecvența și interacțiunile preregistrate nu
  modifică sistematic metricile de fidelitate dincolo de repetabilitate și
  incertitudinea metrologică;
- `H1_DFA`: cel puțin un factor sau o interacțiune produce o variație
  sistematică detectabilă.

Un trial `FAULTED`, `INVALID_MEASUREMENT` sau `DEGRADED` nu devine dovadă de
echivalență. El rămâne însă rezultat științific despre realizabilitate.

## 3. Variabile independente

Factorii experimentali primari sunt:

- coeficientul virtual semnat `D_v ∈ 𝒟_safe`, în N·m·s/rad;
- amplitudinea excitației `A ∈ 𝒜_safe`, definită explicit ca poziție, viteză
  sau comandă, fără amestecarea definițiilor;
- frecvența excitației `f ∈ ℱ_safe`, în Hz;
- sensul mișcării/polaritatea, dacă auditul ViPRO-00 demonstrează asimetrie;
- ordinea trial-urilor, randomizată în blocuri de sesiune.

Temperatura inițială sau sesiunea poate fi factor de blocare, nu factor
controlat fictiv, dacă nu poate fi menținută.

## 4. Variabile dependente

Rezultatele primare sunt cele din TASK-010R:

- `torque_nrmse`, `rmse_nm`, `mae_nm`, `peak_absolute_error_nm`;
- `gain_ratio`, `normalized_amplitude_error`;
- `estimated_delay_s` și `delay_aligned_rmse_nm` doar ca diagnostice;
- `requested_work_j`, `observed_work_j`, `work_error_j` și
  `normalized_work_error` când semnalele permit;
- `trial_status`, `fault_occurrence`, fracția de saturație, fracția exclusă și
  eligibilitatea pentru evaluarea confirmatorie.

Rezultate auxiliare: eroarea de urmărire cinematică A/B, temperaturile,
curentul și estimarea drive-ului, latența de comandă/achitare și distribuția
intervalelor de eșantionare. Acestea explică mecanisme; nu înlocuiesc cuplul
independent.

## 5. Variabile controlate și de context

Se fixează sau se înregistrează: perechea și maparea A/B, hardware/firmware,
configurațiile drive-urilor, modul de control, cuplajul și senzorul, versiunea
software/config, calibrarea, sursele de ceas și sincronizarea, estimatorul de
viteză, forma de undă, faza/rampa, condiția inițială, alimentarea, mediul,
temperatura, procedura operatorului și starea de siguranță.

Orice schimbare produce o sesiune/configurație nouă; nu este ascunsă într-o
medie comună.

## 6. Definiția unui trial

Un trial este o singură realizare a unei condiții `(D_v, A, f, sens)` pe o
singură pereche, cu aceleași versiuni și calibrări, cuprinzând:

1. pre-roll staționar;
2. rampă de intrare limitată;
3. regim sinusoidal stabil pentru `N_ss` cicluri;
4. rampă de ieșire;
5. post-roll și verificarea revenirii într-o stare sigură.

`N_ss`, duratele și rampele sunt simbolice până la caracterizarea din
ViPRO-00. Trial-ul păstrează și segmentele tranzitorii; fereastra primară de
regim staționar este declarată separat, nu aleasă retrospectiv pentru un scor
mai bun.

## 7. Definiția unei sesiuni

O sesiune este un bloc de trial-uri între două verificări complete de
configurație/calibrare, fără modificarea hardware-ului, firmware-ului,
controlului, mapării, ceasurilor sau lanțului metrologic. Sesiunea are ID unic,
operator, început/sfârșit UTC și monoton, inventar/config hash, calibrare,
condiții de mediu și registru de evenimente. O întrerupere de siguranță sau o
schimbare relevantă închide sesiunea.

## 8. Semnale fizice obligatorii

Minimul pentru pretenția de fidelitate fizică este:

- `q_A`, `q_B` și o viteză calibrată ori derivată printr-o metodă înghețată;
- `tau_d_model` și `tau_B_requested` cu ID, timp de emitere, deadline,
  limitare și dovadă de primire/aplicare;
- `tau_port_sensor`: cuplu mecanic independent, calibrat și localizat;
- `tau_B_drive_estimate`, dacă există, marcat `DERIVED`/`IDENTIFIED`;
- stare drive, mod, enable, saturație, avertizări, fault și watchdog/stale;
- timp monoton de achiziție, secvență și timpul dispozitivului dacă există;
- temperaturi și mărimi electrice disponibile ca variabile de context;
- starea E-stop/STO/interlock.

Dacă `tau_port_sensor` nu există, campania poate valida achiziția și compara
comanda cu o estimare, dar nu poate formula concluzia primară de fidelitate
fizică independentă.

## 9. Dovezi de calibrare

Înainte de GO sunt necesare:

- senzor de cuplu: identitate, localizare, sens, zero/span, domeniu,
  incertitudine, bandă, condiționare și certificat/trasabilitate;
- encodere: sursă, rezoluție/scalare, zero, semn, raport de transmisie,
  locație și incertitudine;
- viteză: metodă, filtru, întârziere și incertitudine;
- comandă drive: conversie SI–device, punct de referință, semn, clamp și rampă;
- ceasuri: identificare, rezoluție, offset, drift, wrap și aliniere;
- verificarea independentă că lanțul de validare nu reutilizează estimatorul
  controlerului.

Calibrarea se verifică înainte și după sesiune pentru a cuantifica driftul.

## 10. Validare înainte de rulare

Se aplică checklist-ul GO/NO-GO separat. Sunt obligatorii: mapare fizică fără
ambiguitate, control mode documentat, toate limitele aprobate, polaritatea
verificată la energie redusă printr-o procedură autorizată, achiziție coerentă,
ceasuri caracterizate, zero stabil, siguranță verificată, spațiu mecanic liber,
configurații/versionare salvate și operatori autorizați.

Un dry-run fără energizare validează schema de date. Un shakedown sigur validează
numai lanțul; datele lui nu intră în analiza confirmatorie.

## 11. Secvența de execuție

1. Îngheață manifestul sesiunii, protocolul și planul DOE.
2. Verifică NO-GO și starea sigură; pornește achiziția înaintea actuației.
3. Înregistrează zero/baseline și condiția inițială.
4. Activează numai componentele permise de procedura hardware aprobată.
5. Aplică trial-ul cu rampă, menține excitația, apoi revino prin rampă.
6. Verifică automat fault/saturație/stale/limite în tot intervalul.
7. Dezactivează în ordinea aprobată și păstrează post-roll.
8. Scrie atomically datele brute, hash-urile și evenimentele.
9. Verifică integritatea și statusul trial-ului înainte de următorul.
10. Introdu o perioadă de revenire stabilită din răspunsul termic măsurat.

## 12. Reguli de abort și fault

Se oprește/ramp-down/torque-off conform procedurii de siguranță la: E-stop/STO,
fault de drive, pierderea enable/interlock, watchdog/stale, depășirea oricărei
limite aprobate, semn neașteptat, divergență A/B, pierderea achiziției sau
ceasului, saturație persistentă peste regula preregistrată, temperatură/power
nepermisă, zgomot/vibrație/contact neplanificat ori solicitarea operatorului.

Nu se face auto-reset pentru continuarea aceluiași trial. Trial-ul devine
`FAULTED`; cauza și fereastra rămân în date. Reluarea cere stare sigură,
diagnostic, ID nou și autorizare.

## 13. Date brute

Se păstrează imuabil: cadre/registre brute, valori SI, toate timestamp-urile și
secvențele, comenzi înainte/după limitări, confirmări, encodere, cuplu
independent, estimări drive, curenți, temperaturi, status/fault, safety state,
evenimente operator și faza trial-ului. Manifestul include unități, puncte de
referință, proveniență, calibrare, incertitudine, rate declarate și măsurate,
filtre, versiuni, config/hash și motivul fiecărei excluderi.

Fișierele procesate nu suprascriu datele brute. Fiecare derivare păstrează
hash-ul intrării și versiunea algoritmului.

## 14. Preprocesare

- se verifică monotonicitatea, duplicatele, golurile, NaN/Inf și secvențele;
- ceasurile se aliniază numai prin transformarea preregistrată și validată;
- unitățile, semnele și punctele mecanice se convertesc prin calibrări versionate;
- `tau_B_requested` folosit în eroare este comanda efectivă după transformarea
  de semn și limitări, nu modelul ideal înainte de actuator;
- saturația și fault-ul rămân în metricile primare când măsurarea este validă;
- probele stale și measurement-invalid se marchează separat; excluderea cere
  mască și motiv explicit;
- nu se interpolează peste goluri pentru metricile primare;
- filtrarea, ferestrele și eliminarea offsetului sunt preregistrate și raportate;
- întârzierea nu este eliminată din RMSE primar.

## 15. Metrici TASK-010R

Pipeline-ul `vipro-fidelity-metrics/1.1.0` se rulează cu:

```text
requested = tau_B_requested
observed  = tau_port_sensor
kind      = MEASURED
independent = true
```

Se raportează toate metricile, calitatea și statusul, nu doar cea mai bună
valoare. Analize auxiliare pot înlocui `observed` cu estimarea drive-ului, dar
trebuie etichetate `DERIVED` sau `IDENTIFIED` și
`OFFLINE_SIGNAL_COMPARISON`, nu `PHYSICAL_FIDELITY`.

## 16. Repetabilitate și incertitudine

Fiecare condiție confirmatorie are `n_within` repetări în sesiune și
`n_sessions` sesiuni independente; valorile se stabilesc după pilot și analiză
de putere/precizie, nu se ghicesc. Ordinea este randomizată în blocuri, cu
condiții martor repetate pentru drift.

Se raportează distribuția trial-urilor, abaterea de repetabilitate, variația
între sesiuni, intervale de încredere și componentele de varianță. Se păstrează
și rata `VALID/DEGRADED/FAULTED/INVALID_MEASUREMENT`. Media nu poate ascunde
fault-uri sau lipsa repetabilității.

## 17. Strategia DOE

Etapele sunt:

1. dry-run și shakedown, excluse din inferența confirmatorie;
2. pilot sinusoidal cu o singură variabilă schimbată și energie minimă
   autorizată;
3. DOE încrucișat/blocat pentru `D_v`, `A` și `f` în interiorul domeniului
   sigur măsurat, cu ordine randomizată;
4. confirmare pe condiții rezervate și sesiuni noi;
5. multisine/chirp numai după validarea sinusoidală, a benzii, timingului,
   separării spectrale și a envelopei energetice.

Pentru `q*(t)=A_q sin(2πft)`, amplitudinea ideală de viteză este
`2πfA_q`, iar amplitudinea modelului este `|D_v|2πfA_q`. Aceste relații ajută la
proiectarea domeniului, dar limitele finale provin din limite fizice măsurate și
aprobate pentru cuplu, rată, viteză, poziție, curent, putere, energie și termic,
cu marje documentate. Punctele de frontieră se testează numai după interior.

## 18. Separarea train/calibration/test pentru lucrări viitoare

ViPRO-01A este în primul rând experiment metrologic, nu dataset ML. Dacă datele
vor alimenta ulterior un predictor:

- împărțirea se face pe trial-uri și sesiuni complete, niciodată aleator pe
  eșantioane din aceeași serie;
- `train` dezvoltă modelul;
- `calibration` fixează praguri/incertitudine fără acces la test;
- `test` rămâne blocat până la evaluarea finală;
- split-ul păstrează gruparea după hardware/configurație și rezervă, când
  există suficiente date, condiții/sesiuni neîntâlnite;
- datele de shakedown, fault și measurement-invalid au roluri explicite și nu
  sunt recodate drept trial-uri fidele.

## 19. Criterii GO/NO-GO

GO pentru achiziție fizică cere toate porțile din documentul separat în starea
`GO`, dovadă atașată și manifest înghețat. GO pentru analiza confirmatorie cere
în plus semnal independent de cuplu, buget de incertitudine, timing valid,
excitație suficientă și reguli statistice preregistrate.

Absența referinței independente permite cel mult un studiu de realizare a
comenzii/estimării, nu concluzia principală. Niciun `UNKNOWN` critic nu este
interpretat ca zero, false sau „probabil sigur”.

## 20. Condiții de invaliditate științifică

Experimentul este invalid pentru concluzia primară dacă: cererea și observația
sunt același semnal/estimator; nu există cuplu independent calibrat; semnul sau
punctul de referință este ambiguu; ceasurile nu pot fi aliniate; domeniul a fost
ales din datele de test; limitările/fault-urile sunt eliminate; ferestrele sunt
selectate post-hoc; condițiile/configurațiile sunt amestecate; excitația este
insuficientă; incertitudinea este comparabilă cu efectul fără a fi propagată;
datele brute ori proveniența lipsesc; repetările nu sunt independente; sau
trial-uri de pilot/train sunt raportate drept confirmare.

## Modelul virtual și convenția de semn

Modelul cerut este:

\[
\tau_d(t)=D_v\dot q(t).
\]

Această formulă nu autorizează presupunerea că semnul pozitiv al software-ului
produce fizic opoziție. `D_v` este coeficient semnat în coordonata declarată.
Transformarea dintre `tau_d` și comanda B se notează explicit și se verifică în
ViPRO-00. Pentru amortizare disipativă, convenția aleasă trebuie să satisfacă
relația energetică de opoziție la port; dacă polaritatea nu este demonstrată,
testul este NO-GO.

## UNKNOWN-uri care blochează rularea

ViPRO-00 trebuie să rezolve cel puțin:

1. perechea fizică aleasă și maparea motor–drive–canal–A/B;
2. modelele/firmware-ul motoarelor, encodorelor, drive-urilor și controllerului;
3. modurile de control și mecanismul de command/acknowledgement;
4. semnele, zerourile, rapoartele și punctele mecanice de referință;
5. existența, locația și metrologia senzorului independent de cuplu;
6. semantica/scalarea/independența curentului și estimării de cuplu a drive-ului;
7. sursele de ceas, ratele reale, întârzierile, jitterul și sincronizarea;
8. limitele aprobate de poziție, viteză, cuplu, rată, curent, putere, energie,
   temperatură și durată;
9. E-stop, STO, enable, interlock, watchdog, reset și procedura de abort;
10. proprietățile/montajul cuplajului, jocul, rigiditatea și rezonanțele relevante;
11. condițiile termice/de revenire și frecvența verificării calibrării;
12. valorile `epsilon_F`, nivelul de încredere și numărul de repetări, stabilite
    prin cerințe, incertitudine și pilot înaintea confirmării.
