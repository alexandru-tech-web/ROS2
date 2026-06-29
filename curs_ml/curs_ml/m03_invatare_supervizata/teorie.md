# M03 -- Cadrul invatarii supervizate

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa explici ERM (minimizarea riscului empiric) si diferenta risc empiric vs real;
- sa derivezi descompunerea bias-varianta a erorii patratice asteptate;
- sa implementezi si sa compari functii de pierdere (patratica, 0-1, hinge, logistica);
- sa evaluezi cum complexitatea modelului muta echilibrul bias-varianta.

Prerechizite: M00 (algebra, asteptari ca produse), M01 (asteptare, varianta,
zgomot), M02 (minimizare). Timp estimat: 3-4 h. Dificultate: 2/3.

Vocabular cheie (vezi GLOSAR.md): invatare supervizata, functie de pierdere, risc
empiric (ERM), risc real, supra-invatare, sub-invatare, bias, varianta, capacitate,
no-free-lunch.

## 1. Intuitie

Invatarea supervizata cauta o functie h care, data o intrare x, prezice bine
eticheta y. Dar nu putem masura direct eroarea pe lumea intreaga (riscul real) --
avem doar un esantion. Asa ca minimizam eroarea medie pe datele observate (riscul
empiric). Intrebarea centrala a tot cursului: cand minimizarea pe esantion duce la
performanta buna pe date noi -- si cand ne pacaleste (supra-invatare).

## 2. Formalizare

Date perechi (x_i, y_i), i = 1..n, trase i.i.d. dintr-o distributie necunoscuta D.
O functie de pierdere L(y, p) >= 0 masoara costul prezicerii p cand adevarul e y.

- Risc real (ce ne intereseaza):  R(h) = E_{(x,y)~D}[ L(y, h(x)) ].
- Risc empiric (ce putem calcula): R_emp(h) = (1/n) sum_i L(y_i, h(x_i)).

ERM alege h* = argmin_{h in H} R_emp(h) peste o clasa de modele H. Capacitatea lui
H (cat de bogata e) controleaza compromisul: H prea saraca -> sub-invatare (bias
mare); H prea bogata -> supra-invatare (varianta mare).

Functii de pierdere uzuale:
- patratica: L = (y - p)^2                  (regresie)
- 0-1:       L = 1[y != pred]               (clasificare; nediferentiabila)
- hinge:     L = max(0, 1 - y*score), y in {-1,+1}   (SVM, surogat al 0-1)
- logistica: L = log(1 + exp(score)) - y*score, y in {0,1}  (entropie incrucisata)

Hinge si logistica sunt SURGATE netede/convexe ale pierderii 0-1, pe care o putem
optimiza cu gradient (M02), spre deosebire de 0-1 care e in trepte.

## 3. Derivare: descompunerea bias-varianta

Fixam un punct x. Modelul h_S e antrenat pe un set aleator S; nota h_bar(x) =
E_S[h_S(x)] media predictiilor peste toate seturile posibile. Eticheta are zgomot
ireductibil: y = f(x) + eps, cu E[eps]=0, Var[eps]=sigma^2, eps independent de S.

Eroarea patratica asteptata (peste S si eps):

    E[(y - h_S(x))^2]
      = E[(f + eps - h_S)^2]
      = E[(f - h_S)^2] + 2 E[eps (f - h_S)] + E[eps^2]
      = E[(f - h_S)^2] + 0 + sigma^2          (eps indep. de S, medie 0)

Pentru primul termen adunam si scadem h_bar:

    E[(f - h_S)^2] = E[((f - h_bar) - (h_S - h_bar))^2]
      = (f - h_bar)^2 + E[(h_S - h_bar)^2]    (termenul incrucisat se anuleaza)
      = bias(x)^2 + Var(x)

unde bias(x) = h_bar(x) - f(x) si Var(x) = E_S[(h_S(x) - h_bar(x))^2]. Deci:

    E[(y - h_S(x))^2] = bias(x)^2 + Var(x) + sigma^2.            (egalitatea cheie)

Interpretare: eroarea = eroare sistematica^2 + sensibilitate la date + zgomot
ireductibil. Modelele simple au bias mare / varianta mica; modelele flexibile au
bias mic / varianta mare. Optimul e la mijloc.

## 4. Algoritm (verificarea Monte Carlo a egalitatii)

```
intrare: f(x), grid de puncte, grad d, sigma, n_train, n_seturi
pentru s = 1..n_seturi:
    esantioneaza x_tr; y_tr = f(x_tr) + N(0, sigma^2)
    potriveste polinom de grad d -> h_s; prezice pe grid -> preds[s]
    trage un y proaspat pe grid: fresh_y[s] = f(grid) + N(0, sigma^2)
h_bar = media pe seturi a preds
bias2 = media_grid (h_bar - f)^2
var   = media_grid (varianta pe seturi a preds)
total = media (fresh_y - preds)^2
verifica: total ~ bias2 + var + sigma^2
```

(Implementat in `invatare_supervizata_core.bias_variance_decomposition`.)

## 5. Exemplu lucrat numeric (verifica-l de mana)

Functii de pierdere pe cazuri mici (exact ce verifica selftest-ul nucleului):

(a) Patratica. y = [3, 0, -2], p = [1, 0, 1].
    per esantion: (3-1)^2=4, (0-0)^2=0, (-2-1)^2=9 -> [4, 0, 9].
    R_emp = (4 + 0 + 9) / 3 = 13/3 = 4.3333...

(b) 0-1. y = [0, 1, 1, 0], pred = [0, 1, 0, 0].
    diferente: [nu, nu, DA, nu] -> [0, 0, 1, 0]. R_emp = 1/4 = 0.25.

(c) Hinge (y in {-1,+1}). y = [+1, +1, -1], score = [2, 0.3, 0.5].
    max(0, 1 - 1*2)   = max(0, -1)  = 0
    max(0, 1 - 1*0.3) = max(0, 0.7) = 0.7
    max(0, 1 - (-1)*0.5) = max(0, 1.5) = 1.5   -> [0, 0.7, 1.5].
    Observatie: margine >= 1 pe partea corecta -> pierdere 0.

(d) Logistica la score = 0: log(1 + exp(0)) - y*0 = log(2) = 0.6931..., pentru
    ORICE y (la scor 0 modelul e indecis -> aceeasi penalizare).

Bias-varianta (intuitie numerica). Pe tinta f(x) = sin(1.5*pi*x) cu sigma=0.25 si
n_train=20, un polinom de grad 1 are bias2 mare si varianta mica (linia dreapta nu
poate urma sinusul), iar gradul 11 are bias2 mic dar varianta mare (urmeaza
zgomotul). Egalitatea total ~ bias2 + var + sigma^2 se verifica pentru ambele sub
8% eroare relativa (selftest).

## 6. Vizualizare

`demo_sil.py` produce `fig_biasvar_complexitate.png` (bias2, varianta si total vs
gradul polinomului -- forma clasica de U a erorii totale) si
`fig_pierderi_surogat.png` (hinge si logistica vs 0-1 ca functii de margine).
Datele sunt SINTETICE (proces controlat), nu masuratori reale.

## 7. Capcane frecvente

- A confunda riscul empiric (pe esantion) cu cel real (pe lume): un R_emp mic NU
  garanteaza R mic -- exact ce previne validarea (M07).
- A crede ca 'mai complex = mai bun': dincolo de optim, varianta domina si eroarea
  pe date noi creste.
- A optimiza pierderea 0-1 direct: e in trepte, gradient zero aproape peste tot;
  de aceea folosim surogate (hinge, logistica).
- Zgomotul ireductibil sigma^2 nu poate fi invatat -- e podeaua oricarui model.

## 8. De ce conteaza pentru teza

La N mic (campania C1 are N=5), varianta domina: un model flexibil 'invata'
zgomotul masuratorilor si nu generalizeaza. De aici insistenta cursului pe
regularizare (M06), validare corecta (M07) si incertitudine (M17). Cadrul de aici
explica de ce un selector simplu (always-CycloneDDS) bate adesea unul invatat in
regimul cu putine date -- vezi concluzia C1.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa scrii definitia riscului empiric si a celui real si sa le distingi;
- [ ] sa derivezi E[(y-h)^2] = bias^2 + Var + sigma^2 de la zero;
- [ ] sa calculezi de mana pierderea patratica, 0-1, hinge si logistica pe un caz mic;
- [ ] sa explici de ce gradul mare creste varianta;
- [ ] sa identifici zgomotul ireductibil ca podea a erorii.

## Mergi mai departe

ESL cap. 2 si 7 (bias-varianta), PRML cap. 1, ISL cap. 2. Vezi BIBLIOGRAFIE.md.
