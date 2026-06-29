# M15 -- Clustering

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa explici ce inseamna sa gasesti grupuri in date FARA etichete si cand e util;
- sa derivezi algoritmul Lloyd pentru k-means din obiectivul inertiei si sa explici
  de ce inertia scade monoton;
- sa implementezi k-means (cu reporniri), silhouette si un DBSCAN simplu de la zero;
- sa alegi numarul de cluster-e cu scorul silhouette si sa eviti capcanele clasice
  (initializare, k gresit, scara feature-urilor).

Prerechizite: M00 (algebra liniara: norme, distante euclidiene), M01 (medii si
varianta), notiuni de distanta. Timp estimat: 2-3 h. Dificultate: 2/3.

Vocabular cheie (vezi GLOSAR.md): invatare nesupervizata, cluster, centroid,
inertie (suma patratelor intra-cluster), algoritmul Lloyd, k-means++, scor
silhouette, densitate, DBSCAN, zgomot, minim local.

## 1. Intuitie

Pana acum am avut perechi (x, y): feature-uri si o eticheta tinta. In clustering nu
avem etichete -- doar puncte x. Vrem sa le grupam asa incat punctele dintr-un grup
sa fie SIMILARE intre ele si DIFERITE de cele din alte grupuri. Nimeni nu ne spune
care e raspunsul corect; structura trebuie descoperita din geometria datelor.

Exemplu concret din teza: feature-uri de canal (distanta, path loss, marja fata de
sensibilitate, fractie livrata) masurate fara o eticheta de 'regim'. Clusteringul
descopera regimuri -- de exemplu 'aproape, link bun', 'mediu', 'departe, link slab'
-- direct din date neetichetate. Asta e valoarea lui: ipoteze despre structura cand
nu ai supervizare.

## 2. Formalizare: obiectivul k-means

Avem n puncte x_1..x_n in R^d si vrem k cluster-e. O solutie e o atribuire a fiecarui
punct la un cluster (etichetele c_i in {1..k}) plus k centroizi mu_1..mu_k. Obiectivul
k-means e INERTIA -- suma patratelor distantelor de la fiecare punct la centroidul
clusterului sau:

    J(c, mu) = sum_{i=1..n} || x_i - mu_{c_i} ||^2

Cautam atribuirea si centroizii care minimizeaza J. Aceasta masoara cat de COMPACTE
sunt cluster-ele. Minimizarea exacta e NP-grea, dar algoritmul Lloyd o coboara
eficient prin coordonate alternante.

## 3. Derivare: algoritmul Lloyd

J depinde de doua grupuri de necunoscute: atribuirile c si centroizii mu. Le
optimizam ALTERNATIV, fixand pe unul si minimizand dupa celalalt.

(a) Fixam centroizii mu, optimizam atribuirile c. J e o suma de termeni
    independenti pe puncte; termenul punctului i, || x_i - mu_{c_i} ||^2, e minim
    cand c_i alege cel mai apropiat centroid. Deci:

        c_i = argmin_j || x_i - mu_j ||^2        (pasul de ATRIBUIRE)

(b) Fixam atribuirile c, optimizam centroizii mu. Pentru clusterul j, partea din J
    e sum_{i: c_i = j} || x_i - mu_j ||^2. Derivam dupa mu_j si egalam cu zero:

        d/d mu_j  sum_{i in j} || x_i - mu_j ||^2
          = sum_{i in j} -2 (x_i - mu_j) = 0
          =>  mu_j = (1 / |j|) sum_{i in j} x_i      (pasul de ACTUALIZARE)

    Adica noul centroid e MEDIA punctelor sale. (Media minimizeaza suma patratelor
    distantelor -- exact rezultatul de la M01.)

De ce scade inertia monoton. Fiecare pas nu poate creste J:
- pasul de atribuire alege, pentru fiecare punct, centroidul cel mai apropiat dintre
  cei CURENTI -> J scade sau ramane egal;
- pasul de actualizare inlocuieste fiecare centroid cu media, care minimizeaza partea
  lui din J pentru atribuirea CURENTA -> J scade sau ramane egal.
Deci J(t+1) <= J(t) la fiecare iteratie. J e marginita inferior de 0 si ia un numar
finit de atribuiri posibile, deci sirul converge (la un minim LOCAL, nu neaparat
global -- de aici reporniri multiple).

## 4. DBSCAN pe scurt (densitate)

k-means presupune cluster-e ~sferice si cere k dinainte. DBSCAN gandeste in termeni
de DENSITATE: un punct e 'de baza' (core) daca are cel putin `min_samples` vecini in
raza `eps`. Cluster-ele cresc unind punctele de baza prin vecinatati conectate;
punctele care nu cad in nicio zona densa raman ZGOMOT (eticheta -1). Avantaje: nu
fixezi k, prinde forme arbitrare, marcheaza outlierii. Dezavantaj: sensibil la
alegerea lui (eps, min_samples) si la scara.

## 5. Scor silhouette

Cum stim cat de bune sunt cluster-ele FARA etichete? Scorul silhouette al punctului i:

    a_i = distanta medie de la i la celelalte puncte din PROPRIUL cluster
    b_i = min, pe celelalte cluster-e, a distantei medii de la i la acel cluster
    s_i = (b_i - a_i) / max(a_i, b_i)

Interpretare: s_i aproape de +1 = i e mult mai aproape de propriul cluster decat de
oricare altul (bine plasat); s_i ~ 0 = pe granita; s_i < 0 = probabil atribuit gresit.
Scorul global e media s_i pe toate punctele, in [-1, 1]. Il folosim ca sa alegem k:
rulam k-means pentru cateva valori si pastram k-ul cu silhouette maxim.

## 6. Algoritm (pseudocod Lloyd)

```
kmeans(X, k, n_init):
  best = None
  repeta n_init ori:
    mu = kmeans_plus_plus(X, k)          # centroizi initiali departati
    repeta pana la convergenta:
      # ATRIBUIRE
      pentru fiecare i: c_i = argmin_j || x_i - mu_j ||^2
      # ACTUALIZARE
      pentru fiecare j: mu_j = media punctelor cu c_i = j
      daca inertia nu mai scade (sub tol): opreste
    daca inertia < best.inertia: best = (c, mu, inertia)
  intoarce best
```

Reporniri (`n_init`): Lloyd converge la un minim LOCAL care depinde de
initializare. Pornim de mai multe ori (k-means++ pe seed-uri diferite) si pastram
rularea cu inertia minima.

## 7. Exemplu lucrat numeric (verifica-l de mana)

Sase puncte 1D: X = [1, 2, 3, 8, 9, 10], k = 2. O iteratie Lloyd dintr-o
initializare nefericita mu_0 = 3, mu_1 = 8.

(a) ATRIBUIRE. Compara |x - 3| cu |x - 8| pentru fiecare punct:
    x=1: |-2|=2 vs |-7|=7 -> cluster 0
    x=2: 1 vs 6 -> 0 ;  x=3: 0 vs 5 -> 0
    x=8: 5 vs 0 -> 1 ;  x=9: 6 vs 1 -> 1 ;  x=10: 7 vs 2 -> 1
    Atribuire: [0, 0, 0, 1, 1, 1].

(b) ACTUALIZARE. mu_0 = media{1,2,3} = 2.0 ; mu_1 = media{8,9,10} = 9.0.

(c) INERTIA scade. Cu centroizii VECHI (3 si 8) si atribuirea noua:
    J = (1-3)^2+(2-3)^2+(3-3)^2 + (8-8)^2+(9-8)^2+(10-8)^2
      = 4+1+0 + 0+1+4 = 10.0
    Cu centroizii NOI (2 si 9):
    J = (1-2)^2+(2-2)^2+(3-2)^2 + (8-9)^2+(9-9)^2+(10-9)^2
      = 1+0+1 + 1+0+1 = 4.0
    Inertia a scazut de la 10.0 la 4.0 -- exact ce promite teoria.

(d) SILHOUETTE pentru x=1 (in cluster 0, ceilalti din cluster 0 sunt 2 si 3):
    a = medie(|1-2|, |1-3|) = (1+2)/2 = 1.5
    b = medie(|1-8|, |1-9|, |1-10|) = (7+8+9)/3 = 8.0
    s_1 = (8.0 - 1.5) / max(1.5, 8.0) = 6.5 / 8.0 = 0.8125 (bine plasat).

(Selftest-ul nucleului si exercitiile verifica exact aceste valori: inertia 10 -> 4,
centroizii 2.0 si 9.0, silhouette mare pe grupuri separate.)

## 8. Vizualizare

`demo_sil.py` produce `fig_silhouette_k.png`: in stanga, scatter pe (distanta,
fractie livrata) colorat pe cluster la k-ul ales; in dreapta, curba silhouette vs k.
Varful curbei indica numarul de regimuri de canal. Pe profilul urban_rubble, k=3 da
silhouette-ul maxim -- trei regimuri distincte. Date SINTETICE (semanate din C1/M).

## 9. Capcane frecvente

- INITIALIZARE: Lloyd cade in minime locale; centroizi initiali prosti -> partitie
  proasta. Foloseste k-means++ si reporniri (n_init), pastreaza inertia minima.
- k ALES GRESIT: inertia scade MEREU cand creste k (k=n da inertie 0), deci nu poti
  alege k minimizand inertia. Foloseste silhouette (varf) sau metoda cotului.
- SCARA FEATURE-URILOR: distanta euclidiana e dominata de feature-ul cu amplitudinea
  cea mai mare. Un feature in [0, 1] si unul in [0, 1000] -> al doilea decide totul.
  Standardizeaza (z-score) inainte de clustering. (Vezi exercitiul E6: pe date cu un
  zgomot de amplitudine mare, k-means brut rateaza structura, iar standardizat o
  recupereaza complet.)
- ATENTIE la silhouette: e calculat in spatiul in care masori distantele; pe date
  needescalate poate parea mare desi partitia e gresita fata de structura reala.

## 10. De ce conteaza pentru teza

Datele de canal si de latenta din campanii vin adesea fara o eticheta de 'regim'.
Clusteringul descopera regimuri de operare (link bun / marginal / pierdut) direct din
masuratori neetichetate -- util ca pas exploratoriu inainte de a defini praguri sau
clase (vezi M09, link utilizabil). E si o verificare de sanatate: daca grupurile
gasite nesupervizat se aliniaza cu conditiile cunoscute (loss_5, lat200_l15...),
feature-urile chiar separa regimurile.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa explici obiectivul k-means (inertia) si ce minimizeaza;
- [ ] sa derivezi cei doi pasi Lloyd (atribuire + media) si de ce inertia scade;
- [ ] sa calculezi o iteratie Lloyd de mana pe 4-6 puncte;
- [ ] sa calculezi scorul silhouette al unui punct de mana;
- [ ] sa alegi k cu silhouette si sa explici de ce nu cu inertia;
- [ ] sa spui de ce standardizezi feature-urile inainte de clustering.

## Mergi mai departe

ESL cap. 14.3 (cluster analysis, k-means). ISL cap. 12 (unsupervised learning).
Ester et al. 1996 (DBSCAN). Rousseeuw 1987 (silhouette). Vezi BIBLIOGRAFIE.md.
