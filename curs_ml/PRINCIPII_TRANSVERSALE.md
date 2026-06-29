# PRINCIPII_TRANSVERSALE.md -- principii care traverseaza tot cursul

Aceste principii conteaza mai mult decat orice algoritm anume. Sunt reluate in
modulele relevante, dar aici stau adunate ca referinta.

## 1. Scurgerea de date (leakage) -- greseala numarul unu

Scurgerea = informatie din test (sau din viitor) ajunge in antrenare. Rezultatul:
metrici optimiste care se prabusesc in realitate. Reguli:
- Standardizarea / imputarea / selectia de feature se INVATA pe TRAIN si se APLICA
  pe TEST (vezi `utils.standardize`, care foloseste media/abaterea de pe train).
- In validarea incrucisata, intreaga preprocesare intra in fiecare fald (foloseste
  Pipeline cand lucrezi cu scikit-learn).
- La serii temporale: NU amesteca aleator. Foloseste split temporal, fara
  look-ahead (M19).
- La date corelate (repetitii ale aceleiasi conditii, ca in campaniile mele):
  split-ul aleator scurge informatie; foloseste leave-one-group-out (vezi si
  selectorul C1, validare LOCO).

## 2. Reproductibilitate

- Orice aleator trece prin `numpy.random.default_rng(seed)`. Acelasi seed ->
  acelasi rezultat.
- Fixeaza split-urile (acelasi seed) cand compari modele.
- Noteaza versiunile bibliotecilor (`pip freeze`) si pastreaza `requirements.txt`.
- Figurile se regenereaza din cod (nu se versioneaza binare); SIL-urile sunt
  deterministe.

## 3. Workflow iterativ onest

- Intai o linie de baza simpla (media, regula triviala), apoi modele mai complexe;
  raporteaza imbunatatirea fata de baza, nu cifra absoluta in vid.
- Separa: train (invata), validare (alegi model/hiperparametri), test (raportezi
  o singura data). Nu te uita la test decat la final.
- La N mic (cazul meu: C1 are N=5), prefera validarea incrucisata si raporteaza
  incertitudinea (M07, M17).

## 4. Supra-optimizarea pe setul de validare

Daca incerci sute de configuratii si alegi maximul pe validare, ai supra-potrivit
validarea. Antidot: nested cross-validation (M18), un set de test tinut deoparte,
si scepticism fata de imbunatatiri mici.

## 5. Cand ML e unealta gresita

- Cand o regula simpla / un model fizic explica datele la fel de bine (ex:
  modelul log-distanta de canal e fizica, nu trebuie 'invatat').
- Cand nu ai destule date pentru a generaliza si nu poti cuantifica incertitudinea.
- Cand costul unei erori cere garantii pe care un model statistic nu le da.
- Onestitate specifica tezei: la N=5, multe 'rezultate' ML sunt zgomot; un
  predictor invatat isi merita locul doar daca bate o baza simpla cu marja
  semnificativa (vezi concluzia selectorului C1: depinde de deadline).

## 6. Limite si etica

- Generalizare: un model invatat pe C1/M (degradare sintetica) nu garanteaza
  comportament pe retele reale -- de aici insistenta pe HIL in teza.
- Date mici: intervalele de incredere sunt largi; nu ascunde asta.
- Bias: datele reflecta conditiile alese (8 conditii netem); concluziile nu se
  extrapoleaza in afara lor fara dovezi.
