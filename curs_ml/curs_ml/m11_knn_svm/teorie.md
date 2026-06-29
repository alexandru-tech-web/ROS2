# M11 -- k-NN si SVM cu kernel

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa explici regula k-NN (vecini + vot) si efectul lui k si al scarii feature-urilor;
- sa derivezi pierderea hinge si subgradientul ei, si sa implementezi SVM liniar
  prin Pegasos (subgradient stocastic);
- sa explici trucul kernel si sa folosesti kernelul RBF pentru granite neliniare;
- sa alegi intre k-NN si SVM pe o problema data si sa motivezi alegerea lui C/gamma.

Prerechizite: M00 (algebra liniara -- produs scalar, norma, distante), M02
(optimizare -- coborare pe (sub)gradient), M03 (risc empiric, clasificare).
Timp estimat: 3-4 h. Dificultate: 3/3.

Vocabular cheie (vezi GLOSAR.md): vecinul cel mai apropiat, vot majoritar, distanta
euclidiana, marja, vector de suport, pierderea hinge, subgradient, regularizare L2,
truc kernel, kernel RBF, gamma, C (regularizare).

ONESTITATE: datele de demonstratie/exercitii sunt SINTETICE (cluster-e si inele
semanate aici, sau ferestre de link din `date_sar.py`). Servesc invatarii; nu sunt
masuratori reale.

## 1. Intuitie

Doua idei foarte diferite pentru aceeasi sarcina (clasificare):

- k-NN ('lenes'): nu invata niciun parametru. Ca sa clasifici un punct nou, te uiti
  la cei mai apropiati k vecini din setul de antrenare si votezi eticheta majoritara.
  Granita de decizie iese din date, poate fi oricat de zbarlita.

- SVM liniar ('avid'): cauta UN hiperplan care separa clasele cu marja MAXIMA -- cea
  mai lata banda goala intre clase. Punctele care ating banda (vectorii de suport) o
  determina. Marja mare = generalizare mai buna (mai putin sensibil la zgomot).

## 2. Formalizare

Distante (M00). Pentru x, z in R^d:
- produs scalar  <x, z> = sum_i x_i z_i
- norma euclidiana  ||x|| = sqrt(<x, x>)
- distanta  ||x - z|| = sqrt( sum_i (x_i - z_i)^2 )

k-NN. Fie D = {(x_i, y_i)}. Pentru o interogare q:
  N_k(q) = indicii celor k puncte de antrenare cu cea mai mica ||q - x_i||;
  predictie = eticheta cu cele mai multe voturi in {y_i : i in N_k(q)}.

SVM liniar (problema marginii). Cu etichete y in {-1, +1} si scorul f(x) = <w, x>
(bias inclus prin add_bias), separarea cu marja cere y_i <w, x_i> >= 1 pentru toti i.
Marja geometrica este 1/||w||, deci 'marja maxima' = minimizarea lui ||w||. Pe date
ne-separabile relaxam cu pierderea hinge (vezi mai jos).

## 3. Derivare

### 3a. Regula k-NN
Nu exista parametri de antrenat: 'antrenarea' = memorarea lui D. Costul e la predictie
(calculul tuturor distantelor). Alegerea lui k controleaza neted-vs-zgomot: k=1
urmareste fiecare punct (varianta mare); k mare netezeste (bias mai mare). k impar
evita egalitatile la 2 clase.

### 3b. Pierderea hinge si subgradientul (SVM liniar)
Obiectivul SVM (forma primala regularizata), peste n exemple:
  J(w) = (lam/2) ||w||^2 + (1/n) sum_i  max(0, 1 - y_i <w, x_i>)
Termenul hinge L_i(w) = max(0, 1 - y_i <w, x_i>) e convex dar nediferentiabil in
punctul de cot (marja = 1). Subgradientul lui per exemplu:
  daca y_i <w, x_i> < 1:  d/dw L_i = -y_i x_i
  daca y_i <w, x_i> >= 1: d/dw L_i = 0
Subgradientul lui J pe un exemplu i (Pegasos foloseste cate un exemplu pe pas):
  g = lam w - [ y_i <w, x_i> < 1 ] * y_i x_i
Pasul de coborare cu rata eta_t = 1/(lam t):
  w <- w - eta_t g = (1 - eta_t lam) w + eta_t * [marja violata] * y_i x_i
adica EXACT regula implementata: contracta w (regularizarea), si daca marja e violata
imping w in directia y_i x_i. Rata 1/(lam t) scade in timp -> convergenta.

### 3c. Trucul kernel (pe scurt) si RBF
SVM liniar trage doar drepte. Trucul kernel: inlocuieste produsul scalar <x, z> cu o
functie kernel k(x, z) = <phi(x), phi(z)>, unde phi mapeaza intr-un spatiu de
dimensiune mai mare (posibil infinita) -- fara a calcula phi explicit. O granita
liniara in spatiul phi devine neliniara in spatiul original. Kernelul RBF (gaussian):
  k(x, z) = exp(-gamma ||x - z||^2),  gamma > 0
Proprietati: =1 cand x=z, scade spre 0 cand x si z se departeaza, mereu in (0, 1].
gamma mare = nucleu ingust (fiecare punct influenteaza doar local -> granita zbarlita,
risc de supra-invatare); gamma mic = nucleu lat (granita neteda). In nucleul nostru
implementam RBF ca matrice (rbf_kernel) -- piesa de baza a unui SVM kernelizat.

## 4. Algoritm (pseudocod)

```
k-NN.predict(q):
  pentru fiecare x_i: d_i = ||q - x_i||
  ia indicii celor mai mici k distante
  intoarce eticheta majoritara a vecinilor

Pegasos(X, y in {-1,+1}, lam, n_epoci):
  w = 0 ; t = 0
  pentru epoca = 1..n_epoci:
    pentru i intr-o permutare aleatoare a indicilor:
      t += 1 ; eta = 1/(lam*t)
      daca y_i * <w, x_i> < 1:  w = (1 - eta*lam) w + eta * y_i * x_i
      altfel:                   w = (1 - eta*lam) w
  intoarce w
predict(x) = semn(<w, x>)
```

## 5. Exemplu lucrat numeric (verifica-l de mana)

### (a) k-NN, k=1 si k=3
Patru puncte de antrenare in R^2:
  x1=(0,0) clasa 0,  x2=(1,0) clasa 0,  x3=(4,4) clasa 1,  x4=(5,4) clasa 1.
Interogare q=(1.5, 0.5). Distante LA PATRAT (mai usor de comparat):
  ||q-x1||^2 = 1.5^2 + 0.5^2 = 2.25 + 0.25 = 2.50
  ||q-x2||^2 = 0.5^2 + 0.5^2 = 0.25 + 0.25 = 0.50
  ||q-x3||^2 = 2.5^2 + 3.5^2 = 6.25 + 12.25 = 18.50
  ||q-x4||^2 = 3.5^2 + 3.5^2 = 12.25 + 12.25 = 24.50
Ordinea crescatoare: x2 (0.50), x1 (2.50), x3 (18.50), x4 (24.50).
- k=1: cel mai apropiat e x2 (clasa 0) -> predictie CLASA 0.
- k=3: cei mai apropiati 3 sunt x2, x1, x3 cu clasele {0, 0, 1} -> vot 2-1 -> CLASA 0.
(Selftest-ul nucleului si Ex.2 verifica exact aceste doua raspunsuri.)

### (b) un pas Pegasos
w = (0, 0), exemplu x = (1, 2), y = +1, lam = 0, eta = 0.5.
Marja: y <w, x> = 1 * 0 = 0 < 1 -> violata. Actualizare:
  w <- (1 - 0)*w + 0.5 * 1 * (1, 2) = (0.5, 1.0).
w s-a mutat in directia y*x, exact cum cere subgradientul. (Ex.4 verifica asta.)

## 6. Vizualizare

`demo_sil.py` produce `fig_granite.png`: doua inele concentrice (granita circulara,
neliniara). k-NN (k=5) urmareste cercul si clasifica aproape perfect; SVM-ul liniar,
care poate trasa doar o dreapta, ramane in jur de 60% -- ilustrarea limpede a nevoii
de kernel. Date SINTETICE.

## 7. Capcane frecvente

- Scara feature-urilor la k-NN: distanta euclidiana e dominata de feature-ul cu scara
  mare; un feature in ms (mii) striveste unul in fractii. STANDARDIZEAZA mereu inainte
  de k-NN (vezi Ex.3, unde standardizarea schimba eticheta). Acelasi avertisment
  pentru SVM cu RBF (gamma se raporteaza la distante).
- Alegerea lui k: prea mic = zgomotos (supra-invatare); prea mare = sterge structura
  fina (sub-invatare). Alege prin validare incrucisata (M07).
- Alegerea lui C (= ~1/(lam*n)) si gamma la SVM: C mare / gamma mare = potrivire
  agresiva (supra-invatare); prea mici = sub-invatare. Cauta pe grila, cu CV.
- k-NN e scump la predictie (toate distantele) si sufera de 'blestemul dimensiunii':
  in multe dimensiuni distantele se uniformizeaza.

## 8. De ce conteaza pentru teza

Granita DDS-vs-Zenoh (ce middleware e mai bun in ce regim de retea) NU e liniara in
spatiul (p95, pierdere, jitter, distanta): exista zone unde Zenoh castiga si zone unde
DDS castiga, separate de o frontiera curba. Un clasificator liniar (regresie logistica,
M08) o aproximeaza grosier; k-NN si SVM-RBF pot prinde frontiera curba. Atentie insa:
la N mic (C1, N=5) k-NN supra-invata usor, iar SVM cere reglarea atenta a lui C/gamma
prin validare pe grupuri (LOCO, vezi M07 si selectorul C1). Modelul flexibil castiga
doar daca e validat onest.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa clasifici un punct de mana cu k-NN pentru k=1 si k=3;
- [ ] sa explici de ce standardizarea conteaza la k-NN;
- [ ] sa derivezi subgradientul pierderii hinge si sa scrii pasul Pegasos;
- [ ] sa explici trucul kernel si rolul lui gamma in RBF;
- [ ] sa alegi intre k-NN si SVM si sa motivezi C/gamma/k prin validare.

## Mergi mai departe

ESL cap. 12 (SVM si kernele) si cap. 13 (k-NN, prototipi); ISL cap. 9. Pegasos:
Shalev-Shwartz et al., 'Pegasos: Primal Estimated sub-GrAdient SOlver for SVM'.
Vezi BIBLIOGRAFIE.md.
