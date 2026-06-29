# M09 -- Metrici, dezechilibru si calibrare

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa explici de ce acuratetea minte la clase dezechilibrate si ce raportezi in loc;
- sa derivezi si sa calculezi AUC-ROC (prin ranguri si prin trapez) si curba
  precizie-recall;
- sa alegi pragul de decizie dupa F1 sau dupa un recall-tinta al clasei rare;
- sa explici ce inseamna o probabilitate CALIBRATA si sa o corectezi (Platt, ECE).

Prerechizite: M08 (regresie logistica -- scoruri/probabilitati de clasificare),
M07 (evaluare si validare incrucisata), M03 (risc empiric vs real), M01
(probabilitate). Timp estimat: 2-3 h. Dificultate: 2/3.

Vocabular cheie (vezi GLOSAR.md): matrice de confuzie, precizie, recall, F1,
curba ROC, TPR/FPR, AUC, curba precizie-recall, precizie medie (AP), prag de
decizie, calibrare, curba de fiabilitate, ECE, scalare Platt, clase dezechilibrate.

## 1. Intuitie

Cand o clasa e rara (in datele mele de link, ferestrele 'usable' sunt ~30% --
degradarea face majoritatea ferestrelor inutilizabile), un model lenes care
prezice MEREU clasa majoritara are acuratete mare si valoare zero. Acuratetea
amesteca doua tipuri de greseli foarte diferite (a rata o fereastra buna vs a
declara buna una proasta) intr-un singur numar care e dominat de clasa frecventa.

Doua remedii: (1) metrici care privesc clasa rara separat -- precizie, recall, F1;
(2) metrici care evalueaza ORDONAREA scorurilor independent de prag -- ROC/AUC si
curba precizie-recall. Iar daca folosesti probabilitatile (nu doar decizia 0/1),
vrei ca ele sa fie CALIBRATE: cand modelul zice 0.7, evenimentul sa se intample
cam in 70% din cazuri.

## 2. Formalizare

Matrice de confuzie binara (pozitiv = clasa de interes, aici 'usable'):

```
                 prezis 0      prezis 1
real 0 (neg)     TN            FP
real 1 (poz)     FN            TP
```

- Acuratete   = (TP + TN) / (TP + TN + FP + FN)
- Precizie     = TP / (TP + FP)     (din cele declarate pozitive, cate chiar sunt)
- Recall (TPR) = TP / (TP + FN)     (din pozitivii reali, cati ii prinzi)
- FPR          = FP / (FP + TN)     (din negativii reali, cati ii declari pozitiv)
- F1           = 2 * precizie * recall / (precizie + recall)   (media armonica)

Un clasificator cu scor produce o eticheta prin PRAG: prezice 1 daca scor >= t.
Pragul controleaza compromisul: t mic prinde mai multi pozitivi (recall sus) dar
cu mai multe alarme false (precizie jos); t mare invers.

## 3. Derivare

### 3.1 De ce acuratetea minte la dezechilibru

Fie pi = P(y=1) rata pozitivilor. Clasificatorul 'prezice mereu 0' are:
  acuratete = TN / total = (1 - pi).
La pi = 0.3, asta da 0.70 fara sa identifice NICIUN pozitiv (recall = 0, precizie
nedefinita). Orice model 'util' trebuie comparat cu aceasta baza, nu cu 0. Mai
mult, acuratetea pondereaza FP si FN identic, desi costul lor difera (a declara
un link bun cand e prost poate insemna pierderea controlului robotului).

### 3.2 Curba ROC si AUC

Variind pragul t de la +inf la -inf, fiecare t da un punct (FPR(t), TPR(t)).
Curba ROC uneste aceste puncte de la (0,0) la (1,1). AUC = aria sub ea.

Interpretare probabilistica (cheia): AUC = P(scor(un pozitiv ales la intamplare)
> scor(un negativ ales la intamplare)). Demonstratie prin numarare de perechi:
fie n_p pozitivi si n_n negativi. Numarul de perechi (poz, neg) e n_p * n_n.
Daca punem 1 pentru fiecare pereche cu scor_poz > scor_neg si 0.5 pentru egalitate,

  AUC = (#{poz > neg} + 0.5 * #{poz = neg}) / (n_p * n_n).

Aceasta e statistica Mann-Whitney U normalizata. De aici doua moduri de calcul
identice: (a) ranguri -- sortezi toate scorurile, U = suma rangurilor pozitivilor
minus n_p(n_p+1)/2, AUC = U / (n_p n_n); (b) trapezul pe punctele ROC. Nucleul
foloseste (a) (stabil, fara alegere de praguri) si verifica ca da acelasi numar ca (b).

Limite: clasificatorul PERFECT (orice pozitiv are scor > orice negativ) -> AUC = 1.
Clasificatorul ALEATOR (scor independent de eticheta) -> AUC = 0.5. AUC < 0.5
inseamna ca ai inversat clasele.

### 3.3 Curba precizie-recall (si de ce e mai potrivita la dezechilibru)

La fel, variezi pragul si pentru fiecare t calculezi (recall(t), precizie(t)).
Recall creste monoton cand pragul scade; precizia oscileaza (de aici aspectul de
'dinte de fierastrau'): cand cobori pragul si urmatorul exemplu adaugat e un FP,
precizia scade local. Linia de baza a unui clasificator aleator in spatiul PR e
ORIZONTALA la precizie = pi (rata pozitivilor), NU diagonala ca la ROC.

Tocmai de aceea PR e mai sensibila la dezechilibru: ROC poate arata frumos
(FPR mic e usor cand negativii sunt multi), in timp ce precizia ramane slaba.
Rezumatul scalar al curbei PR e PRECIZIA MEDIE (AP):

  AP = sum_k (R_k - R_{k-1}) * P_k

(aria sub PR ca suma ponderata cu cresterea recall-ului).

### 3.4 Alegerea pragului

Pragul implicit 0.5 e arbitrar; il alegi din SCOP:
- max F1: parcurgi pragurile candidate (scorurile unice) si pastrezi pe cel cu F1
  maxim -- echilibru intre precizie si recall;
- recall-tinta: vrei sa prinzi cel putin o fractie r* din pozitivi (ex. 90% din
  ferestrele bune). Alegi cel mai MARE prag care inca da recall >= r* -- cobori
  exact cat trebuie ca sa nu umfli inutil fals-pozitivele.

### 3.5 Calibrare

Un scor poate ordona bine (AUC mare) dar sa fie o probabilitate proasta: modelul
zice 0.9 cand evenimentul se intampla doar in 60% din cazuri. Curba de fiabilitate
imparte [0,1] in bin-uri; pentru fiecare bin pune pe axa x probabilitatea medie
prezisa si pe y frecventa reala a pozitivilor. Calibrare perfecta = diagonala.
Rezumatul scalar e ECE (eroarea de calibrare asteptata):

  ECE = sum_b (n_b / N) * |prob_medie_b - frecventa_reala_b|.

Corectie prin SCALARE PLATT: potrivesti o regresie logistica 1D pe scoruri,
  p_calibrat = sigmoid(a * scor + b),
antrenata pe log-pierdere (parametrii a, b prin gradient). Mapeaza monoton scorul
in probabilitati care se potrivesc cu frecventa observata -- nu schimba ordonarea
(deci AUC ramane), doar calibrarea.

## 4. Algoritm (pseudocod)

```
roc_auc(y, scor):           # prin ranguri (Mann-Whitney U)
  ranguri = rang_mediat(scor)         # 1..n, egalitatile mediate
  U = sum(ranguri[y==1]) - n_p*(n_p+1)/2
  intoarce U / (n_p * n_n)

pr_curve(y, scor):
  sorteaza descrescator dupa scor
  TP, FP cumulati; pentru praguri distincte: P=TP/(TP+FP), R=TP/n_p

threshold_for_recall(y, scor, r*):
  pentru praguri t de la mare la mic:
    daca recall(scor>=t) >= r*: intoarce t   # primul (cel mai mare) care atinge

platt_fit(scor, y):          # regresie logistica 1D, gradient
  invata a, b in sigmoid(a*scor + b) minimizand log-pierderea
```

## 5. Exemplu lucrat numeric (verifica-l de mana)

### (a) Matrice de confuzie, precizie/recall/F1

y_real = [1, 1, 1, 0, 0],  y_prezis = [1, 1, 0, 1, 0].
- TP = 2 (indicii 0,1: real 1, prezis 1)
- FN = 1 (indicele 2: real 1, prezis 0)
- FP = 1 (indicele 3: real 0, prezis 1)
- TN = 1 (indicele 4: real 0, prezis 0)

Matrice [[TN, FP], [FN, TP]] = [[1, 1], [1, 2]].
- Precizie = TP/(TP+FP) = 2/3 = 0.6667
- Recall   = TP/(TP+FN) = 2/3 = 0.6667
- F1       = 2 * (2/3)*(2/3) / (2/3 + 2/3) = 2/3 = 0.6667
- Acuratete = (TP+TN)/5 = 3/5 = 0.60

### (b) AUC pe 4 scoruri, de mana

Doi pozitivi cu scoruri {0.9, 0.4}; doi negativi cu scoruri {0.6, 0.3}.
Perechile (pozitiv, negativ) -- numaram cate au scor_poz > scor_neg:
- (0.9, 0.6): 0.9 > 0.6  -> 1
- (0.9, 0.3): 0.9 > 0.3  -> 1
- (0.4, 0.6): 0.4 > 0.6  -> 0
- (0.4, 0.3): 0.4 > 0.3  -> 1

Perechi castigate = 3 din 4 -> AUC = 3/4 = 0.75.
(Selftest-ul nucleului verifica exact 0.75 pe aceste scoruri.)

### (c) ECE pe 2 bin-uri

Bin [0.0, 0.5): 4 exemple, prob medie prezisa 0.30, dintre care 1 pozitiv ->
frecventa reala 0.25; contributie |0.30 - 0.25| = 0.05.
Bin [0.5, 1.0]: 6 exemple, prob medie 0.80, dintre care 5 pozitivi ->
frecventa 0.833; contributie |0.80 - 0.833| = 0.033.
ECE = (4/10)*0.05 + (6/10)*0.033 = 0.02 + 0.02 = 0.04. Aproape calibrat.

## 6. Vizualizare

`demo_sil.py` produce `fig_pr_calibrare.png` cu doua panouri pe datele de link
(dezechilibrate): STANGA = curba precizie-recall cu linia de baza la rata
pozitivilor; DREAPTA = diagrama de calibrare (scoruri brute vs dupa Platt) fata de
diagonala perfecta. ECE-ul scade vizibil dupa Platt. Date SINTETICE.

## 7. Capcane frecvente

- A raporta DOAR acuratetea la dezechilibru: compar-o intotdeauna cu baza
  'prezice mereu majoritarul' (= 1 - pi).
- A te baza pe AUC-ROC cand clasa rara conteaza: ROC poate arata bine cu FPR mic;
  la dezechilibru prefera curba PR / precizia medie.
- A lasa pragul la 0.5: pragul e o decizie de COST, nu o constanta universala.
- A confunda 'ordoneaza bine' cu 'probabilitate buna': AUC mare nu implica
  calibrare; verifica ECE / curba de fiabilitate separat.
- A calibra pe ACELEASI date pe care raportezi: calibrarea se invata pe o portiune
  tinuta deoparte (ca orice pas care invata din date -- vezi scurgerea din M07).
- Bin-uri prea fine la ECF: bin-uri aproape goale dau frecvente zgomotoase.

## 8. De ce conteaza pentru teza

Decizia 'comut pe link / declar fereastra utilizabila' e o clasificare cu cost
asimetric pe date dezechilibrate (degradarea face majoritatea ferestrelor
inutilizabile). A rata o fereastra buna costa diferit fata de a folosi una proasta
(risc de pierdere a controlului). Deci: raportez precizie/recall/F1 pe clasa rara,
nu acuratete; aleg pragul dupa un recall-tinta motivat de siguranta; si daca
selectorul foloseste probabilitati (ex. cost asteptat ca la D mare in selectorul
C1), acele probabilitati trebuie CALIBRATE ca decizia de cost sa fie corecta.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa explici cu o cifra de ce acuratetea minte la pi = 0.3;
- [ ] sa calculezi precizie/recall/F1 de mana dintr-o matrice de confuzie;
- [ ] sa calculezi AUC pe cateva scoruri prin numararea perechilor;
- [ ] sa alegi un prag pentru un recall-tinta dat;
- [ ] sa explici ce inseamna o probabilitate calibrata si cum o masori (ECE).

## Mergi mai departe

ESL cap. 9.2 (evaluare), Davis & Goadrich 2006 (PR vs ROC la dezechilibru),
Platt 1999 (scalare probabilistica), Guo et al. 2017 (calibrare). Vezi BIBLIOGRAFIE.md.
