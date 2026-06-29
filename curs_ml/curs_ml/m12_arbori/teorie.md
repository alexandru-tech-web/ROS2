# M12 -- Arbori de decizie

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa definesti si sa calculezi impuritatea unui nod (Gini, entropie) si sa derivi
  castigul de informatie / reducerea de impuritate a unui split;
- sa implementezi de la zero cresterea recursiva greedy a unui arbore CART pentru
  clasificare binara;
- sa explici de ce un arbore adanc supra-invata si cum limiteaza adancimea /
  taierea (pruning) acest fenomen;
- sa citesti regulile interpretabile produse de un arbore -- de ce arborii sunt
  modele explicabile, util pentru deciziile mission_complete din teza.

Prerechizite: M01 (probabilitate: distributii pe clase, entropie ca surpriza
medie), M03 (invatare supervizata: risc empiric, supra/sub-invatare). Timp
estimat: 2-3 h. Dificultate: 2/3.

Vocabular cheie (vezi GLOSAR.md): arbore de decizie, CART, impuritate Gini,
entropie, castig de informatie, reducere de impuritate, prag (threshold), split,
frunza, adancime, taiere (pruning), greedy, importanta feature-urilor.

## 1. Intuitie

Un arbore de decizie pune o secventa de intrebari de tip 'feature <= prag?'. Fiecare
intrebare imparte datele in doua, iar la capatul lantului de intrebari (o frunza)
prezici clasa majoritara a exemplelor care au ajuns acolo. E exact felul in care un
om ar scrie un set de reguli: 'DACA livrarea > 0.6 SI latenta < 2 s ATUNCI misiunea
reuseste'. Invatarea inseamna sa alegem AUTOMAT intrebarile bune: cele care separa
clasele cat mai curat.

'Curat' se masoara cu impuritatea: un nod e pur daca toate exemplele lui au aceeasi
clasa. Crestem arborele alegand greedy, la fiecare pas, split-ul care scade cel mai
mult impuritatea.

## 2. Formalizare: impuritate

Fie un nod cu exemple ale caror etichete dau proportiile pe clase p_c (c = clasa).

- Impuritate Gini:    G = 1 - sum_c p_c^2
- Entropie (in biti): H = -sum_c p_c log2 p_c

Pentru clasificare binara (c in {0, 1}), cu p = fractia clasei 1:
- G = 1 - p^2 - (1-p)^2 = 2 p (1-p)
- H = -p log2 p - (1-p) log2 (1-p)

Cazuri limita (de retinut):
- nod PUR (p = 0 sau p = 1): G = 0, H = 0;
- nod 50/50 (p = 0.5): G = 2*0.5*0.5 = 0.5; H = -(0.5 log2 0.5)*2 = 1 bit.

Ambele sunt maxime la 50/50 si zero la puritate; difera doar prin forma. Gini e mai
ieftin (fara logaritm) si e default-ul CART; entropia (castig de informatie) e
clasica pentru ID3/C4.5. In practica dau arbori foarte asemanatori.

## 3. Derivare: castigul / reducerea de impuritate a unui split

Un split imparte cele n exemple ale unui nod parinte in stanga (n_st exemple, prin
conditia feature_j <= prag) si dreapta (n_dr = n - n_st). Definim reducerea de
impuritate ca impuritatea parintelui minus media PONDERATA a impuritatii copiilor:

    Delta I = I(parinte) - ( n_st/n * I(stanga) + n_dr/n * I(dreapta) )

Ponderile n_st/n si n_dr/n conteaza: un split care izoleaza un singur exemplu intr-o
frunza pura nu valoreaza cat unul care imparte nodul in jumatati pure. Cand I = H,
Delta I se numeste castig de informatie (information gain): reducerea entropiei
(incertitudinii) despre clasa dupa ce afli raspunsul la intrebarea split-ului.

Delta I >= 0 mereu (impuritatea e concava, deci media copiilor nu poate depasi
parintele -- inegalitatea lui Jensen). CART alege, la fiecare nod, perechea
(feature, prag) care MAXIMIZEAZA Delta I.

## 4. Algoritm: CART (crestere recursiva greedy)

```
grow(X, y, depth):
  daca y e pur SAU |y| < min_samples_split SAU depth >= max_depth:
      intoarce Frunza(eticheta = clasa majoritara din y)
  (j, t, gain) = best_split(X, y)            # maximizeaza Delta I
  daca gain == 0:                            # niciun split nu ajuta
      intoarce Frunza(eticheta = clasa majoritara din y)
  stanga  = grow(X[x_j <= t], y[x_j <= t], depth+1)
  dreapta = grow(X[x_j >  t], y[x_j >  t], depth+1)
  intoarce NodIntern(j, t, stanga, dreapta)

best_split(X, y):
  pentru fiecare feature j:
    pentru fiecare prag candidat t (mijloacele valorilor distincte sortate):
      imparte dupa x_j <= t ; calculeaza Delta I
  intoarce (j, t) cu Delta I maxim
```

Pragurile candidate sunt mijloacele dintre valori consecutive distincte ale fiecarui
feature -- e suficient, fiindca Delta I se schimba doar cand un exemplu trece dintr-o
parte in cealalta. Costul unei cresteri e O(n * d * log n) pe nivel.

CART e greedy si miop: alege cel mai bun split LOCAL, fara sa anticipeze. De aceea nu
poate sparge dintr-un foc un tipar de tip XOR (unde niciun split unic pe o axa nu
reduce impuritatea la radacina), dar il rezolva pe niveluri daca exista un split util
in vreun nod.

## 5. Taiere (pruning), pe scurt

Un arbore crescut pana la puritate memoreaza zgomotul (supra-invatare). Doua remedii:
- pre-pruning (oprire timpurie): limiteaza max_depth, cere min_samples_split /
  min_samples_leaf, sau un castig minim. Simplu, folosit aici.
- post-pruning (cost-complexity, CCP): creste arborele complet, apoi taie subarborii
  care nu-si merita complexitatea, penalizand numarul de frunze cu un coeficient alpha
  ales prin validare incrucisata. Mai principial, dar mai costisitor.

In acest modul folosim pre-pruning (max_depth, min_samples_split); CCP e tema de
aprofundare (vezi BIBLIOGRAFIE).

## 6. Exemplu lucrat numeric (verifica-l de mana)

Set de 6 exemple, un singur feature x, eticheta y in {0, 1}:

    x:  1   2   2   3   4   5
    y:  0   0   0   1   1   1

(a) Impuritatea nodului parinte. 3 exemple de clasa 0 si 3 de clasa 1, deci p = 0.5.
    G(parinte) = 1 - 0.5^2 - 0.5^2 = 1 - 0.25 - 0.25 = 0.5.
    H(parinte) = -(0.5 log2 0.5 + 0.5 log2 0.5) = 1 bit.

(b) Candidatul de split x <= 2.5 (mijlocul intre 2 si 3).
    Stanga = {x=1,2,2} -> y = {0,0,0}, pur: G(stanga) = 0.
    Dreapta = {x=3,4,5} -> y = {1,1,1}, pur: G(dreapta) = 0.
    n_st = 3, n_dr = 3, n = 6.
    Delta G = 0.5 - (3/6 * 0 + 3/6 * 0) = 0.5.  Split PERFECT: castig maxim posibil.

(c) Un candidat mai slab, x <= 1.5.
    Stanga = {y=0} (1 exemplu, pur, G=0).
    Dreapta = {0,0,1,1,1} (5 exemple): p = 3/5, G = 1 - (2/5)^2 - (3/5)^2
            = 1 - 0.16 - 0.36 = 0.48.
    Delta G = 0.5 - (1/6 * 0 + 5/6 * 0.48) = 0.5 - 0.40 = 0.10.

(d) Comparatie. Delta G(x<=2.5) = 0.50  >  Delta G(x<=1.5) = 0.10. CART alege pragul
    2.5. Cu castig de informatie (entropie) concluzia e aceeasi: H(x<=2.5) ponderat = 0,
    deci castig de informatie = 1 bit (maxim), iar x<=1.5 da castig mai mic.

Selftest-ul nucleului verifica exact acest exemplu (feature 0, prag 2.5, reducere
Gini 0.5) si exercitiul E3 cere pragul optim pe un caz inrudit.

## 7. Vizualizare

`demo_sil.py` antreneaza un arbore CART (max_depth=3) pe mission_complete si emite
`fig_arbore_importanta.png`: bare cu importanta feature-urilor (reducerea de
impuritate acumulata, normalizata la suma 1). Pe datele mele iese clar ca
`delivered_frac` domina, urmat de `p95_ms` -- exact pragurile cu care e construit
generatorul. Demo-ul tipareste si REGULILE arborelui, o linie per frunza. Date
SINTETICE (semanate din C1/M).

## 8. Capcane frecvente

- Supra-invatare la adancime mare: un arbore fara limita creste pana memoreaza fiecare
  exemplu (acuratete de train ~1.0) si generalizeaza prost. Selftest-ul arata un ciot
  (depth 1) care NU supra-invata pe zgomot, fata de un arbore adanc care il memoreaza.
- Instabilitate: o mica schimbare in date poate schimba primul split si tot arborele
  de sub el. De aceea ensemblurile (M13: bagging, random forest) mediaza multi arbori.
- Bias spre feature-uri cu multe valori distincte (multe praguri candidate). Gini si
  ponderarea ajuta partial; atentie la feature-uri tip identificator.
- Frontiere doar axis-aligned: arborele taie perpendicular pe axe, deci aproximeaza in
  trepte o frontiera oblica (de aceea cere adancime mai mare pentru diagonale).

## 9. De ce conteaza pentru teza

Pentru deciziile operationale (a reusit misiunea? e legatura utilizabila?) un model
INTERPRETABIL valoreaza mult: un arbore mic da reguli citibile de om ('DACA livrarea
> 0.66 SI p95 < 2.1 s -> misiune reusita'), pe care le poti audita, justifica intr-un
articol si transpune intr-o politica de control. Acuratetea singura nu e suficienta
intr-o teza despre teleoperare in retele degradate: trebuie sa poti EXPLICA pragul.
Arborii sunt si caramida de baza pentru ensemblurile din M13, care imbunatatesc
acuratetea pastrand o parte din interpretabilitate (importanta feature-urilor).

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa calculezi Gini si entropia unui nod de mana din numararile pe clase;
- [ ] sa derivi reducerea de impuritate ponderata a unui split si sa explici de ce e >= 0;
- [ ] sa descrii cresterea recursiva greedy a CART si conditiile de oprire;
- [ ] sa explici de ce un arbore adanc supra-invata si cum ajuta pre-pruning-ul;
- [ ] sa citesti regulile si importanta feature-urilor produse de un arbore antrenat.

## Mergi mai departe

ESL cap. 9 (CART), ISL cap. 8 (arbori si metode bazate pe arbori). Vezi
BIBLIOGRAFIE.md.
