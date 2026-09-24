# ViPRO-01A — checklist GO/NO-GO

Status inițial: **NO-GO**. Acest checklist este o poartă de dovezi, nu o
procedură de punere în funcțiune. O căsuță se bifează numai cu artefactul indicat
și responsabilul/datele verificării; `UNKNOWN` nu înseamnă PASS.

## Poarta G0 — identitate și configurație

- [ ] Perechea A/B este mapată fără ambiguitate la motoare, drive-uri, canale,
  cabluri și sens mecanic.
- [ ] Modelele, seriile, firmware-ul și configurațiile sunt arhivate.
- [ ] Modul de control A și B este documentat și verificat.
- [ ] Cuplajul, raportul de transmisie și punctele de referință sunt documentate.
- [ ] Versiunea software, configurația, protocolul și manifestul au hash/ID.

Eșecul oricărui punct: **NO-GO**.

## Poarta G1 — siguranță și limite

- [ ] E-stop, STO, enable și interlock au schemă, responsabil și test aprobat.
- [ ] Watchdog/stale, fault, reset și succesiunea de oprire sunt documentate.
- [ ] Limitele aprobate de poziție, viteză, cuplu, rată, curent, putere,
  energie, temperatură, durată și duty-cycle sunt cunoscute.
- [ ] Domeniul `𝒟_safe × 𝒜_safe × ℱ_safe` este derivat și verificat față de
  toate limitele; valorile SIM nu sunt folosite ca limite fizice.
- [ ] Sunt definite condițiile operatorului, zona liberă și comunicarea între
  persoanele responsabile.
- [ ] Nu există reset automat al unui fault pentru continuarea aceluiași trial.

Eșecul oricărui punct: **NO-GO**.

## Poarta G2 — convenții și comandă

- [ ] Semnul lui `q`, `q_dot`, `tau_d`, comanda B și cuplul senzorului este
  definit la același port mecanic.
- [ ] Relația `tau_d = D_v*q_dot` și transformarea spre B sunt verificate printr-o
  procedură autorizată cu energie redusă.
- [ ] Se poate demonstra ce comandă a fost emisă, limitată, primită/aplicată ori
  respinsă, cu ID și timestamp.
- [ ] Clamp, rate-limit, deadband, unități și scalări sunt documentate.
- [ ] Opoziția energetică a sarcinii este confirmată; semnul nu este presupus.

Eșecul oricărui punct: **NO-GO**.

## Poarta G3 — metrologie mecanică

- [ ] Există un senzor independent de cuplu în calea mecanică A/B.
- [ ] Identitatea, locația, sensul, domeniul, banda, condiționarea și
  cross-sensitivity sunt cunoscute.
- [ ] Zero/span, certificat/calibrare și bugetul de incertitudine sunt valide.
- [ ] Independența față de estimatorul buclei de control este demonstrată.
- [ ] Encoderele au scalare, zero, semn, rezoluție, raport și calibrare.
- [ ] Metoda `q_dot` are filtru, întârziere și incertitudine înghețate.
- [ ] Verificările înainte/după sesiune pot detecta driftul.

Fără primele patru puncte poate exista doar un studiu cu semnal
`DERIVED/IDENTIFIED`, nu **PHYSICAL_FIDELITY**.

## Poarta G4 — timp și integritatea datelor

- [ ] Fiecare eșantion are timp monoton și index de secvență.
- [ ] Ceasurile dispozitivelor, rezoluția, wrap, offsetul și driftul sunt
  caracterizate sau există o metodă validată de aliniere.
- [ ] Ratele și jitterul sunt măsurate, nu doar configurate.
- [ ] Lipsa, duplicatele, stale, NaN/Inf, saturația și fault-ul sunt detectabile
  prin câmpuri/măști distincte.
- [ ] Datele brute, valorile SI, evenimentele și manifestul sunt scrise imuabil,
  cu hash și proveniență.
- [ ] Un dry-run fără energizare trece validarea schemei și pipeline-ul
  TASK-010R.

Eșecul oricărui punct: **NO-GO**.

## Poarta G5 — plan experimental preregistrat

- [ ] Factorii, nivelurile și domeniul sigur sunt înghețate.
- [ ] Fereastra staționară, filtrele, excluderile și metricile sunt înghețate.
- [ ] `epsilon_F`, incertitudinea și regula inferențială sunt fixate înaintea
  datelor confirmatorii.
- [ ] `n_within` și `n_sessions` rezultă din pilot și analiza de
  putere/precizie.
- [ ] Ordinea randomizată/blocată și condițiile martor pentru drift sunt fixate.
- [ ] Trial-urile/sesiunile train, calibration și test rezervat sunt separate.
- [ ] Shakedown/pilot nu pot fi reclasificate ulterior drept confirmare.

Eșecul oricărui punct: **NO-GO pentru confirmare**.

## Verificare imediat înaintea fiecărui trial

- [ ] ID-urile sesiunii, trial-ului și condiției corespund planului.
- [ ] Starea mecanică inițială și zona de lucru sunt conforme.
- [ ] E-stop/STO/interlock/watchdog și achiziția raportează starea așteptată.
- [ ] Zero-ul și baseline-ul sunt în limitele metrologice preregistrate.
- [ ] Temperaturile și starea drive-urilor permit trial-ul.
- [ ] Comanda/rampa estimată rămâne în envelopele aprobate.
- [ ] Achiziția a început înaintea oricărei actuații.

Orice abatere: trial-ul nu începe.

## Abort în timpul trial-ului

Abort conform procedurii aprobate la E-stop/STO, fault, pierdere interlock,
watchdog/stale, limită depășită, polaritate neașteptată, divergență A/B,
pierdere de achiziție/timing, saturație persistentă conform regulii
preregistrate, temperatură nepermisă, vibrație/contact neplanificat sau cererea
operatorului. Datele nu se șterg; statusul este `FAULTED` când evenimentul este
de sistem.

## Poarta după trial

- [ ] Fișierele brute și manifestul sunt complete, închise și hash-uite.
- [ ] Numărul de secvențe, timestamp-urile și golurile sunt verificate.
- [ ] Măștile de fault, saturație, stale și measurement-invalid au motive.
- [ ] Orice excludere de măsurare este explicită și auditabilă.
- [ ] Statusul TASK-010R este păstrat; un `FAULTED` nu poate deveni `ACCEPT`.
- [ ] Revenirea sigură/termică este confirmată înaintea trial-ului următor.

## Decizii distincte

```text
GO_ACQUISITION
  = G0 ∧ G1 ∧ G2 ∧ G4 și procedura hardware autorizată

GO_PHYSICAL_FIDELITY
  = GO_ACQUISITION ∧ G3 ∧ G5

ELIGIBLE_FOR_LATER_CERTIFICATION
  = trial_status == VALID și toate obligațiile protocolului sunt satisfăcute
```

`ELIGIBLE` nu este `ACCEPT`. Pragul și regula ACCEPT/REJECT aparțin unei etape
viitoare și nu sunt definite de acest protocol.

## UNKNOWN-uri deschise la emiterea documentului

Toate porțile fizice sunt în prezent nerezolvate: maparea A/B; inventarul și
firmware-ul; control mode și command acknowledgement; polaritatea; limitele;
E-stop/STO/interlock/watchdog; existența și calibrarea senzorului de cuplu;
encoderele și viteza; curentul/estimarea drive; ceasurile, ratele și timingul;
regimul termic; domeniul DOE; `epsilon_F`; repetările și regula statistică.

Prin urmare, starea corectă este:

```text
GO_ACQUISITION: NO_GO
GO_PHYSICAL_FIDELITY: NO_GO
```
