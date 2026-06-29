# M14 -- Interpretabilitate

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa explici DE CE avem nevoie de explicabilitate (incredere, depanare, justificare);
- sa derivezi si sa implementezi importanta prin permutare si dependenta partiala;
- sa calculezi valori Shapley exacte pentru un model liniar si sa verifici
  proprietatea de eficienta;
- sa identifici capcanele (corelatii intre feature-uri, PDP inselator) si sa
  justifici in articol ce variabila de link conteaza cel mai mult.

Prerechizite: M13 (ensembluri -- modele puternice dar opace, de unde nevoia de
explicabilitate), M05 (regresie liniara -- cazul exact pentru Shapley). Timp
estimat: 2-3 h. Dificultate: 2/3.

Vocabular cheie (vezi GLOSAR.md): interpretabilitate, model-agnostic, importanta
prin permutare, dependenta partiala (PDP), valori Shapley, eficienta (axioma),
baza (valoare de referinta), explicatie locala vs globala.

## 1. Intuitie

Un model bun care nu poate fi explicat e greu de folosit intr-o teza: nu poti sustine
ca o concluzie e robusta daca nu stii PE CE se sprijina. Explicabilitatea raspunde la
doua intrebari: (a) GLOBAL -- ce feature-uri conteaza in general (importanta prin
permutare, PDP); (b) LOCAL -- de ce a dat modelul ACEASTA predictie pentru ACEST
exemplu (valori Shapley). Tehnicile de aici sunt MODEL-AGNOSTICE: vad modelul ca pe o
cutie neagra cu o functie `model_predict(X)` si nu cer acces la interior. Asta le face
aplicabile la orice -- de la o regresie liniara la un ensemblu din M13.

## 2. Formalizare si derivare

Notatie: model f cu predictie f(x); n exemple, d feature-uri; X matricea (n x d);
metric un scor (R2, acuratete) unde MAI MARE = mai bine.

### 2.1 Importanta prin permutare

Ideea: daca un feature conteaza, atunci STRICAREA legaturii lui cu tinta trebuie sa
strice scorul. Permutam aleator coloana j (pastram distributia marginala a feature-ului,
dar rupem corelatia cu y), recalculam scorul si masuram cat a scazut:

    imp_j = metric(y, f(X)) - E_perm[ metric(y, f(X cu coloana j permutata)) ]

Mediem peste mai multe permutari (zgomot Monte Carlo). Daca feature j e irelevant,
permutarea nu schimba scorul -> imp_j ~ 0. Daca e esential, scorul se prabuseste ->
imp_j mare. Avantaj: nu cere reantrenare; dezavantaj: la feature-uri CORELATE poate
subestima (vezi 5).

### 2.2 Dependenta partiala (PDP)

Vrem efectul MEDIU al feature-ului j asupra predictiei, marginalizand peste restul.
Definitie (Friedman): fie x_S feature-ul de interes (aici unul singur, j) si x_C restul.

    PDP_j(v) = E_{x_C}[ f(v, x_C) ]

Estimam empiric: FORTAM coloana j la valoarea v pe toate randurile (pastram x_C la
valorile reale ale fiecarui rand) si mediem predictia:

    PDP_j(v) = (1/n) sum_i f( x_i cu x_{i,j} := v )

Variind v peste o grila obtinem un profil. Pentru un model liniar f(x)=w0+sum w_k x_k,
fortand x_j=v: media peste i da PDP_j(v) = w_j*v + const, deci o DREAPTA de panta w_j --
PDP recupereaza exact coeficientul. Pentru un model neliniar, profilul arata forma
(crescator/descrescator/in U) a efectului mediu.

### 2.3 Valori Shapley

Imprumutate din teoria jocurilor cooperative. Tratam feature-urile ca jucatori care
contribuie la predictie. Valoarea Shapley a feature-ului j este contributia lui medie
pe TOATE ordinile de adaugare:

    phi_j = sum_{S subset N\{j}} [ |S|!(d-|S|-1)! / d! ] * ( v(S U {j}) - v(S) )

unde v(S) este predictia folosind doar feature-urile din S (restul la valoarea de baza).
Axiomele Shapley garanteaza unicitatea; cea mai utila e EFICIENTA:

    sum_j phi_j = f(x) - E[f]                       (suma contributiilor = predictie - baza)

adica explicatia se "imparte complet" intre feature-uri, fara rest.

Caz EXACT pentru un model liniar. Daca f(x) = w0 + sum_j w_j x_j, atunci v(S) =
w0 + sum_{k in S} w_k x_k + sum_{k not in S} w_k E[x_k] (feature-urile absente luate la
medie). Diferenta v(S U {j}) - v(S) = w_j*(x_j - E[x_j]) NU depinde de S, deci suma
ponderata Shapley colapseaza la acel termen:

    phi_j = w_j * (x_j - E[x_j])                     (valoare Shapley liniara, EXACTA)

Verificam eficienta: sum_j phi_j = sum_j w_j (x_j - E[x_j]) = (w0+sum w_j x_j) -
(w0+sum w_j E[x_j]) = f(x) - E[f]. Interceptul w0 se anuleaza. QED.

## 3. Algoritm (pseudocod)

```
permutation_importance(f, X, y, metric, n_repeats, seed):
  baza = metric(y, f(X))
  pentru fiecare feature j:
    pentru r = 1..n_repeats:
      Xp = X cu coloana j permutata aleator (seed)
      drop_r = baza - metric(y, f(Xp))
    imp[j] = media(drop_r)
  intoarce imp

partial_dependence(f, X, j, grid):
  pentru fiecare v in grid:
    Xv = X cu coloana j fortata la v
    pdp(v) = media( f(Xv) )
  intoarce pdp

shapley_linear(w, x, x_mean):     # w = pantele (fara intercept)
  intoarce w * (x - x_mean)        # element cu element
```

## 4. Exemplu lucrat numeric (verifica-l de mana)

Model liniar cu DOUA feature-uri, valori Shapley exacte calculate de mana.

Fie f(x) = w0 + w1*x1 + w2*x2 cu w0 = 10, w1 = 2, w2 = -3.
Mediile populatiei: E[x1] = 0, E[x2] = 5. Baza (predictia medie):

    E[f] = w0 + w1*E[x1] + w2*E[x2] = 10 + 2*0 + (-3)*5 = 10 - 15 = -5.

Instanta de explicat: x = (x1, x2) = (1, 4). Predictia:

    f(x) = 10 + 2*1 + (-3)*4 = 10 + 2 - 12 = 0.

Valorile Shapley (formula liniara phi_j = w_j*(x_j - E[x_j])):

    phi_1 = w1*(x1 - E[x1]) = 2*(1 - 0) = +2.
    phi_2 = w2*(x2 - E[x2]) = -3*(4 - 5) = -3*(-1) = +3.

Interpretare: ambele feature-uri imp ing predictia IN SUS fata de baza (cu +2 si +3),
desi w2 e negativ -- pentru ca x2=4 e SUB media 5, iar un coeficient negativ pe o
valoare sub-medie contribuie pozitiv.

Verificarea EFICIENTEI (controlul tau):

    phi_1 + phi_2 = 2 + 3 = 5 = f(x) - E[f] = 0 - (-5) = 5.   OK.

(Selftest-ul nucleului si exercitiul E1/E2 verifica exact aceste valori: phi = [2, 3]
si suma = predictie - baza.)

## 5. Vizualizare

`demo_sil.py` produce `fig_importanta_link.png`: bar chart cu importanta prin permutare
a feature-urilor de link pentru eticheta `usable`, plus un profil PDP pe `loss_frac`.
Pe datele SINTETICE, `p95_ms` domina clasamentul, iar PDP-ul pe pierdere e descrescator
(mai multa pierdere -> scor de utilizabilitate mai mic) -- semn corect. Date SINTETICE.

## 6. Capcane frecvente

- Feature-uri CORELATE. Importanta prin permutare imparte creditul intre feature-uri
  corelate si poate face fiecare sa para mai putin important decat e (permutarea unuia
  lasa informatia in geamanul corelat). Solutii: grupare, importanta conditionala.
- PDP INSELATOR la corelatii. PDP forteaza x_j=v pe randuri cu x_C arbitrar, inclusiv
  combinatii (v, x_C) care NU apar in date (extrapolare). Profilul poate arata un efect
  intr-o regiune fara suport. Diagnostic: uita-te si la histograma feature-ului.
- PDP ascunde interactiunile: media peste populatie poate fi plata desi efectul e
  puternic dar de semn opus pe subpopulatii. (Remediu: ICE, dependenta partiala
  individuala.)
- A confunda corelatie cu cauzalitate: importanta nu inseamna ca feature-ul CAUZEAZA
  tinta -- inseamna doar ca modelul se sprijina pe el.

## 7. De ce conteaza pentru teza

Intrebarea practica: care variabila de link decide utilizabilitatea legaturii, ca sa o
pot justifica in articol? Importanta prin permutare da un clasament defensabil (pe
datele sintetice: p95 RTT > jitter > pierdere), iar valorile Shapley explica o decizie
INDIVIDUALA (de ce ACEASTA fereastra a fost clasata inutilizabila). E exact uneltita de
care ai nevoie cand un reviewer intreaba "pe ce se bazeaza concluzia": un model nu se
sustine ca argument decat daca poti arata ce il conduce. Aceeasi logica e in spatele
selectorului C1, unde conteaza ce feature impinge alegerea middleware-ului.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa explici de ce permutarea unui feature irelevant nu schimba scorul;
- [ ] sa derivezi PDP_j(v) si sa arati ca pentru un model liniar panta lui e w_j;
- [ ] sa calculezi valori Shapley liniare de mana pe un caz cu 2 feature-uri;
- [ ] sa verifici eficienta (suma contributiilor = predictie - baza);
- [ ] sa numesti doua capcane (corelatii in importanta, extrapolare in PDP).

## Mergi mai departe

ESL cap. 10 si 15 (importanta de feature); articolul SHAP (Lundberg & Lee, 2017) si
cartea Molnar -- Interpretable Machine Learning (online, gratuit). Vezi BIBLIOGRAFIE.md.
