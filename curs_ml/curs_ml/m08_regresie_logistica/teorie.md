# M08 -- Regresie logistica

## Antet pedagogic

### Obiective de invatare
La finalul modulului poti:
- **deriva** pas cu pas gradientul entropiei incrucisate `(1/n) X^T (p - y)`
  pornind de la verosimilitatea Bernoulli;
- **implementa** regresia logistica de la zero in numpy, antrenata prin coborare pe
  gradient, cu sigmoid stabil numeric;
- **explica** legatura logit / odds / probabilitate si de ce frontiera de decizie
  e liniara in spatiul feature-urilor;
- **evalua** un clasificator probabilistic (acuratete, dar si precizie/recall la
  clase dezechilibrate) si a alege un prag de decizie;
- **aplica** modelul la prezicerea utilizabilitatii unei legaturi de teleoperatie
  din feature-uri de retea.

### Prerechizite
- M02 (optimizare: gradient, coborare pe gradient, rata de invatare). M08 DEPINDE
  direct de M02 pentru mecanica antrenarii.
- M03 (cadru de invatare supervizata: risc empiric, train/test, supra-/sub-invatare).
- M01 (probabilitate: distributia Bernoulli, verosimilitate) ajuta la derivare.

### Timp si dificultate
- Timp estimat: 90-120 min (citire + exemplul numeric de mana + exercitii).
- Dificultate: 2 / 3.

### Vocabular cheie (vezi GLOSAR.md)
sigmoida (functia logistica), logit, odds (sanse), entropie incrucisata (log-loss),
verosimilitate Bernoulli, gradient, frontiera (granita) de decizie, prag de decizie,
probabilitate prezisa, clasa pozitiva.

## 1. Intuitie

Regresia liniara (M05) prezice un numar real; pentru clasificare vrem o
PROBABILITATE in `[0, 1]`. Ideea: ia scorul liniar `z = w^T x` (acelasi tip de scor
ca la regresia liniara) si treci-l printr-o functie care il striveste in `(0, 1)` --
sigmoida. Scorul mare pozitiv -> probabilitate aproape de 1; scor mare negativ ->
aproape de 0; scor 0 -> exact 0.5 (granita de decizie). Antrenarea cauta `w` astfel
incat probabilitatile prezise sa se potriveasca etichetelor observate.

## 2. Formalizare

Sigmoida (functia logistica):
```
sigmoid(z) = 1 / (1 + exp(-z)),   sigmoid: R -> (0, 1)
```
Modelul prezice `p = P(y=1 | x) = sigmoid(w^T x)`, unde `w` include interceptul (bias)
daca lui `x` i s-a adaugat o coloana de 1 (add_bias din utils).

Logit si odds. Inversa sigmoidei e logitul: daca `p = sigmoid(z)`, atunci
```
z = log( p / (1 - p) ) = logit(p).
```
Raportul `p / (1 - p)` sunt SANSELE (odds). Deci regresia logistica modeleaza
LINIAR log-sansele: `log(odds) = w^T x`. De aici si frontiera de decizie liniara:
`p = 0.5  <=>  z = 0  <=>  w^T x = 0` (un hiperplan).

Verosimilitate si pierdere. Cu `y in {0, 1}`, un exemplu urmeaza o Bernoulli de
parametru `p`: `P(y | x) = p^y (1-p)^(1-y)`. Verosimilitatea pe tot setul (puncte
independente) e produsul; maximizam log-verosimilitatea, echivalent cu a MINIMIZA
log-loss-ul mediu (entropia incrucisata binara):
```
L(w) = -(1/n) sum_i [ y_i * log(p_i) + (1 - y_i) * log(1 - p_i) ],   p_i = sigmoid(w^T x_i).
```
Nu exista solutie inchisa ca la regresia liniara (M05); minimizam prin coborare pe
gradient (M02). Vestea buna: `L` e CONVEXA in `w`, deci coborarea pe gradient atinge
minimul global.

## 3. Derivare pas cu pas a gradientului (ASCII-LaTeX inline)

Vrem `dL/dw`. Doua identitati de sprijin.

(i) Derivata sigmoidei. Fie `s = sigmoid(z) = 1/(1+exp(-z))`. Atunci
```
ds/dz = exp(-z) / (1 + exp(-z))^2 = s * (1 - s).
```
(Verificare: `1 - s = exp(-z)/(1+exp(-z))`, deci `s*(1-s) = exp(-z)/(1+exp(-z))^2`.)

(ii) Derivata log-loss-ului pentru UN exemplu fata de scorul `z = w^T x`.
Pierderea pe un exemplu: `l = -[ y*log(s) + (1-y)*log(1-s) ]`, cu `s = sigmoid(z)`.
Derivam dupa `s` intai:
```
dl/ds = -[ y/s - (1-y)/(1-s) ] = -( y*(1-s) - (1-y)*s ) / ( s*(1-s) )
      = -( y - s ) / ( s*(1-s) ).
```
Inmultim cu `ds/dz = s*(1-s)` (regula lantului) -- factorul `s*(1-s)` se SIMPLIFICA:
```
dl/dz = (dl/ds) * (ds/dz) = -( y - s ) = ( s - y ) = ( p - y ).
```
Acesta e pasul-cheie: derivata fata de scor e pur si simplu `p - y` (eroarea de
probabilitate). Acum lantul pana la `w`, cu `dz/dw = x`:
```
dl/dw = (dl/dz) * (dz/dw) = (p - y) * x.
```
(iii) Mediind pe tot setul (forma vectoriala). Cu `X` matricea de design (randuri
`x_i^T`, inclusiv coloana de bias), `p = sigmoid(X w)` vectorul de probabilitati si
`y` vectorul de etichete:
```
grad L(w) = (1/n) * X^T ( p - y ).
```
Aceasta e EXACT formula implementata in `regresie_logistica_core._grad` si in pasul
de update `w <- w - lr * grad L(w)`.

## 4. Algoritm (pseudocod)

```
fit(X, y, lr, n_iter, seed):
  Phi = add_bias(X)                       # coloana de 1 pentru intercept
  w   = mici valori aleatoare (seed)
  pentru t = 1..n_iter:
    p     = sigmoid(Phi w)                # probabilitati prezise
    loss[t] = log_loss(y, p)             # pentru diagnoza convergentei
    g     = (1/n) Phi^T (p - y)          # gradientul derivat in sec.3
    w     = w - lr * g                    # un pas de coborare
  intoarce w, loss

predict_proba(X) = sigmoid(add_bias(X) w)
predict(X, prag) = 1 daca predict_proba(X) >= prag, altfel 0
```

## 5. Exemplu lucrat numeric (verifica-l de mana)

(a) Sigmoid. `sigmoid(0) = 1/(1+exp(0)) = 1/2 = 0.5` (exact granita de decizie).
    `sigmoid(2) = 1/(1+exp(-2)) = 1/(1+0.13534) = 0.8808`.
    Simetrie: `sigmoid(-2) = 1 - sigmoid(2) = 0.1192`.

(b) Un exemplu, un pas de gradient. Fie un singur punct cu bias deja adaugat:
    `x = [1, 2]` (prima coordonata = bias), eticheta `y = 1`, greutati `w = [0, 0]`.
    Scorul: `z = w^T x = 0*1 + 0*2 = 0`. Probabilitatea: `p = sigmoid(0) = 0.5`.
    Eroarea de probabilitate: `p - y = 0.5 - 1 = -0.5`.
    Gradientul (n=1): `g = (p - y) * x = -0.5 * [1, 2] = [-0.5, -1.0]`.
    Cu `lr = 1`: `w_nou = w - lr*g = [0,0] - [-0.5,-1.0] = [0.5, 1.0]`.
    Verificare ca pierderea a scazut: noul scor `z' = 0.5*1 + 1.0*2 = 2.5`,
    `p' = sigmoid(2.5) = 0.9241`. Pierderea (y=1) `-log(p)` a scazut de la
    `-log(0.5) = 0.6931` la `-log(0.9241) = 0.0789`. Pasul a impins `p` spre 1, corect.

(c) Log-loss la indecizie. Daca modelul prezice `p = 0.5` pentru toate punctele,
    log-loss-ul mediu e `-log(0.5) = ln 2 = 0.6931` indiferent de etichete -- baza
    'aruncarea monedei' fata de care trebuie sa te imbunatatesti.

(Selftest-ul nucleului si exercitiile verifica exact aceste valori: `sigmoid(0)=0.5`,
gradientul vs diferente finite, scaderea pierderii dupa un pas, `log-loss=ln 2` la 0.5.)

## 6. Vizualizare

`demo_sil.py` produce `fig_granita_decizie.png`: probabilitatea prezisa `P(usable)`
ca harta de culoare pe planul a doua feature-uri standardizate (`p95_ms`,
`loss_frac`), cu linia neagra a granitei de decizie (`p = 0.5`) si punctele
colorate dupa eticheta. Granita e o DREAPTA -- semnatura modelului liniar in logit.
Date SINTETICE.

## 7. Capcane frecvente

- Overflow in `exp` la scoruri mari: `sigmoid` naiva da `inf`/`nan`. Solutia (in
  nucleu): forma stabila pe ramuri (`exp(z)/(1+exp(z))` pentru `z < 0`).
- `log(0)` cand `p` atinge exact 0 sau 1: tunde `p` in `[eps, 1-eps]` inainte de log.
- Feature-uri pe scari diferite (ex. `p95_ms` in mii vs `loss_frac` sub-unitar):
  fara standardizare, gradientul oscileaza si convergenta e lenta -- standardizeaza
  (M04), cu statistici doar de pe TRAIN (fara scurgere).
- Acuratetea la clase dezechilibrate INSEALA: pe utilizabilitate (~30% usable) un
  model care zice mereu 'inutilizabil' ia ~70% acuratete fara sa fie util. Raporteaza
  si precizie/recall/F1 (vezi M09).
- Pragul fix 0.5 nu e sacru: la cost asimetric (a rata o legatura proasta e scump),
  muta pragul ca sa cresti recall-ul, acceptand mai multe false pozitive.
- Separabilitate perfecta -> greutatile diverg (logit-ul vrea sa creasca la infinit).
  La N mic e un risc real; regularizarea (M06) il tine in frau.

## 8. De ce conteaza pentru teza

Regresia logistica e baza interpretabila pentru deciziile binare ale sistemului:
'e legatura utilizabila pentru teleoperatie acum?' din feature-uri de retea (p95 RTT,
pierdere, jitter, distanta, middleware). Coeficientii spun DIRECT cum schimba fiecare
feature log-sansele -- exact tipul de model pe care il poti aparara intr-un articol.
Datele sunt dezechilibrate (degradarea face majoritatea ferestrelor inutilizabile),
ceea ce pregateste M09 (metrici la dezechilibru) si alimenteaza selectorul C1.
ATENTIE: datele sunt SINTETICE (semanate din C1/M), nu masuratori reale -- de
inlocuit cu campania finala inainte de orice afirmatie din teza.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa scrii sigmoida si sa explici legatura logit / odds / probabilitate;
- [ ] sa derivezi gradientul `(1/n) X^T (p - y)` de la verosimilitatea Bernoulli;
- [ ] sa faci de mana un pas de gradient pe un exemplu mic (sec. 5b);
- [ ] sa explici de ce frontiera de decizie e liniara in feature-uri;
- [ ] sa argumentezi de ce acuratetea inseala la clase dezechilibrate.

## Mergi mai departe

ESL cap. 4; ISL cap. 4; PRML cap. 4 (model liniar generalizat, verosimilitate).
Vezi BIBLIOGRAFIE.md.
