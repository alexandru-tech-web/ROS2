# M20 -- Retele neuronale

> ONESTITATE: figurile, demo-ul si exemplele numerice folosesc date SINTETICE
> (XOR, sin, latenta semanata din C1/M via date_sar.py). Marcat la fiecare loc.

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa explici de ce un strat ascuns cu activare neliniara da expresivitate peste
  un model liniar (compunere de transformari neliniare);
- sa derivi backpropagation cu regula lantului pentru un MLP cu un strat ascuns
  (gradientii pentru W2, b2, W1, b1);
- sa implementezi forward + backward + un pas de gradient descent in numpy pur;
- sa verifici backprop-ul cu diferente finite (gradient check);
- sa judeci onest cand un MLP NU merita la N mic / semnal aproape liniar.

Prerechizite: M02 (optimizare, gradient descent), M03 (risc empiric vs real,
sub/supra-invatare), M08 (regresie logistica -- sigmoidul si entropia incrucisata).
Timp estimat: 3-4 h. Dificultate: 3/3.

Vocabular cheie (vezi GLOSAR.md): strat ascuns, neuron, activare (relu/tanh/sigmoid),
propagare inainte (forward), backpropagation, regula lantului, gradient check,
weight decay, dropout, initializare He/Xavier.

## 1. Intuitie

Un model liniar invata o singura granita dreapta: y = X w + b. Multe semnale nu se
descriu asa -- exemplul-canon e XOR (poarta sau-exclusiv): cu doua intrari in {0,1},
iesirea e 1 cand exact UNA dintre intrari e 1. Nicio dreapta nu separa {(0,1),(1,0)}
de {(0,0),(1,1)}.

Solutia: compune doua transformari neliniare. Stratul ascuns proiecteaza intrarea
intr-un spatiu nou (z1 = X W1 + b1), o ACTIVARE neliniara indoaie acel spatiu
(a1 = activare(z1)), iar stratul de iesire pune o granita liniara pe reprezentarea
indoita (z2 = a1 W2 + b2). Compunerea liniar -> neliniar -> liniar poate aproxima
functii pe care un singur strat liniar nu le atinge (teorema de aproximare
universala: un strat ascuns destul de larg aproximeaza orice functie continua pe
un compact). Pretul: mai multi parametri si o pierdere NECONVEXA.

## 2. Formalizare (MLP cu un strat ascuns)

Notatii: X are n exemple pe randuri si d feature-uri pe coloane. Stratul ascuns are
H neuroni. Pentru REGRESIE cu o iesire:

    z1 = X W1 + b1        X: n x d, W1: d x H, b1: H   ->  z1: n x H
    a1 = activare(z1)                                  ->  a1: n x H
    z2 = a1 W2 + b2       W2: H x 1, b2: 1             ->  z2: n x 1
    y_hat = z2            (regresie: iesire liniara)

Pierderea (eroare patratica medie, MSE):

    L = (1/n) sum_i (y_hat_i - y_i)^2

Pentru CLASIFICARE binara: y_hat = sigmoid(z2) si pierderea e entropia incrucisata
binara (BCE):  L = -(1/n) sum_i [ y_i log y_hat_i + (1 - y_i) log(1 - y_hat_i) ].

## 3. Derivare: backpropagation (regula lantului)

Vrem gradientii lui L fata de W1, b1, W2, b2. Aplicam regula lantului INAPOI, de la
iesire spre intrare. Notam dV = dL/dV pentru orice marime V.

Pasul de iesire. Pentru REGRESIE cu MSE, derivata pierderii fata de z2 este:

    dz2 = dL/dz2 = (2/n) (y_hat - y)          (n x 1)

(Pentru CLASIFICARE cu sigmoid + BCE, derivata sigmoidului se anuleaza cu cea a
entropiei incrucisate si ramane forma curata  dz2 = (1/n)(y_hat - y).)

Gradientii stratului de iesire (z2 = a1 W2 + b2, deci dz2/dW2 = a1, dz2/db2 = 1):

    dW2 = a1^T dz2                              (H x 1)
    db2 = sum peste exemple de dz2             (1,)

Propagam inapoi in stratul ascuns. Intai gradientul fata de activari, apoi prin
derivata activarii (inmultire element cu element, fiindca activarea actioneaza
component cu component):

    da1 = dz2 W2^T                             (n x H)
    dz1 = da1 (.) activare'(z1)                (n x H)   ((.) = produs Hadamard)

Gradientii stratului ascuns (z1 = X W1 + b1):

    dW1 = X^T dz1                              (d x H)
    db1 = sum peste exemple de dz1            (H,)

Pasul de gradient descent (rata lr): W <- W - lr * dW pentru fiecare parametru.

REGULARIZARE prin weight decay (L2 cu coeficient lambda): adauga lambda*(||W1||^2 +
||W2||^2) la L; in gradient asta inseamna dW += 2*lambda*W pentru fiecare matrice de
greutati (biasurile nu se penalizeaza de obicei).

## 4. Functii de activare

- relu(z) = max(0, z);  relu'(z) = 1 daca z > 0 altfel 0. Ieftina, nu satureaza pe
  partea pozitiva; risc de 'neuroni morti' (gradient 0 pe partea negativa).
- tanh(z) in (-1, 1);  tanh'(z) = 1 - tanh(z)^2. Centrata in 0, buna pentru retele
  mici (folosita in demo-ul nostru).
- sigmoid(z) = 1/(1+e^-z) in (0, 1);  sigmoid'(z) = sigmoid(z)(1 - sigmoid(z)).
  Satureaza la capete (gradient ~0) -> invatare lenta in straturi adanci.

## 5. Algoritm (pseudocod)

```
fit(X, y):
  initializeaza W1,b1,W2,b2     # He/Xavier: W ~ N(0,1) * sqrt(2/fan_in)
  repeta n_iter de ori:
    # FORWARD
    z1 = X W1 + b1 ; a1 = activare(z1) ; z2 = a1 W2 + b2 ; y_hat = iesire(z2)
    L  = pierdere(y_hat, y) + lambda*(||W1||^2 + ||W2||^2)
    # BACKWARD (regula lantului)
    dz2 = grad_iesire(y_hat, y)                      # (2/n)(y_hat-y) la MSE
    dW2 = a1^T dz2 + 2*lambda*W2 ; db2 = sum(dz2)
    dz1 = (dz2 W2^T) (.) activare'(z1)
    dW1 = X^T dz1 + 2*lambda*W1 ; db1 = sum(dz1)
    # PAS
    W1 -= lr*dW1 ; b1 -= lr*db1 ; W2 -= lr*dW2 ; b2 -= lr*db2
predict(X): forward(X) -> y_hat (sau prag 0.5 la clasificare)
```

## 6. Exemplu lucrat numeric (verifica-l de mana)

Retea minuscula: 1 intrare, 1 neuron ascuns (activare tanh), 1 iesire liniara,
UN exemplu. Parametri: w1 = 0.8, b1 = -0.1, w2 = 1.2, b2 = 0.3. Exemplu: x = 0.5,
tinta y = 1.0. Pierdere MSE pe n = 1.

FORWARD:
- z1 = x*w1 + b1 = 0.5*0.8 + (-0.1) = 0.4 - 0.1 = 0.3
- a1 = tanh(0.3) = 0.291313 (sase zecimale)
- z2 = a1*w2 + b2 = 0.291313*1.2 + 0.3 = 0.349575 + 0.3 = 0.649575
- y_hat = z2 = 0.649575
- L = (y_hat - y)^2 = (0.649575 - 1.0)^2 = (-0.350425)^2 = 0.122798

BACKWARD (n = 1, deci dz2 = 2*(y_hat - y)):
- dz2 = 2*(0.649575 - 1.0) = 2*(-0.350425) = -0.700850
- dW2 = a1 * dz2 = 0.291313 * (-0.700850) = -0.204166
- db2 = dz2 = -0.700850
- da1 = dz2 * w2 = -0.700850 * 1.2 = -0.841020
- tanh'(z1) = 1 - tanh(0.3)^2 = 1 - 0.291313^2 = 1 - 0.084863 = 0.915137
- dz1 = da1 * tanh'(z1) = -0.841020 * 0.915137 = -0.769648
- dW1 = x * dz1 = 0.5 * (-0.769648) = -0.384824
- db1 = dz1 = -0.769648

UN PAS de gradient descent cu lr = 0.1:
- w2 <- 1.2 - 0.1*(-0.204166) = 1.220417
- b2 <- 0.3 - 0.1*(-0.700850) = 0.370085
- w1 <- 0.8 - 0.1*(-0.384824) = 0.838482
- b1 <- -0.1 - 0.1*(-0.769648) = -0.023035

Toti gradientii sunt negativi: y_hat (0.65) e sub tinta (1.0), deci pasul creste
greutatile ca sa ridice iesirea. (Functia ex2_forward_un_neuron din exercitii
reproduce exact pasul forward; gradient check-ul din mlp_core confirma backward-ul.)

## 7. Vizualizare

`demo_sil.py` produce `fig_mlp_vs_liniar.png`: prezis vs real (log10 rtt) pentru
regresia liniara si pentru MLP, pe acelasi split. Punctele pe diagonala = predictie
buna. Compara cele doua RMSE-uri din titluri. Date SINTETICE.

## 8. Capcane frecvente

- Initializare proasta: toate greutatile 0 -> toti neuronii ascunsi invata identic
  (simetrie nesparta). Foloseste He/Xavier (scalare cu sqrt(2/fan_in)).
- Rata de invatare: prea mare -> pierderea diverge/oscileaza; prea mica -> invata
  exasperant de lent. Verifica intai ca pierderea SCADE in primii pasi.
- Supra-invatare la N mic: un MLP are multi parametri; cu putine date memoreaza
  zgomotul. Aparare: weight decay, mai putini neuroni, oprire timpurie, dropout.
- Gradient gresit: o eroare de semn in backprop nu da crash, doar invata prost.
  Verifica MEREU cu gradient check (diferente finite) inainte sa ai incredere.
- Pierdere neconvexa: gradient descent gaseste un minim LOCAL; rezultatul depinde
  de samanta. Determinismul (seed) face experimentul reproductibil, nu optim.

## 9. De ce conteaza pentru teza

Un MLP e candidat natural pentru predictorul de latenta (din feature-uri de retea
-> RTT) si pentru selectorul de middleware. DAR onestitatea cere nota inversa: in
campaniile mele N e mic (C1: N=5) si semnalul e aproape liniar in log (latenta de
baza si pierderea intra aditiv in log10 rtt). Pe demo-ul SIL, MLP-ul nu aduce o
imbunatatire care sa justifice complexitatea fata de o regresie liniara/Ridge --
exact ca la selectorul C1, unde modelul invatat nu bate regula simpla decat in
regimuri inguste. Lectia de transmis: o retea neuronala isi merita locul cand
exista neliniaritate REALA de exploatat SI date suficiente; altfel raporteaza
cinstit ca modelul simplu castiga si NU umfla arhitectura.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa explici de ce un strat ascuns neliniar rezolva XOR iar un model liniar nu;
- [ ] sa derivi dW2, db2, dW1, db1 cu regula lantului pentru un MLP cu un strat;
- [ ] sa faci un pas forward + backward de mana pe o retea cu un neuron;
- [ ] sa verifici backprop-ul cu diferente finite (gradient check < 1e-4);
- [ ] sa explici ce face weight decay-ul si cand un MLP NU merita la N mic.

## Mergi mai departe

ESL cap. 11 (retele neuronale), Goodfellow et al. 'Deep Learning' cap. 6 (MLP) si
cap. 7 (regularizare: weight decay, dropout). Vezi BIBLIOGRAFIE.md.
