# M16 -- Reducerea dimensionalitatii (PCA)

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa derivi PCA ca maximizare a variantei si sa o legi de SVD si de vectorii
  proprii ai matricei de covarianta;
- sa implementezi PCA de la zero (centrare, SVD, proiectie, reconstructie);
- sa interpretezi varianta explicata si sa alegi cate componente retii;
- sa folosesti PCA ca sa comprimi si sa vizualizezi separarea conditiilor de retea;
- sa enunti conceptual ce fac t-SNE / UMAP si in ce difera de PCA.

Prerechizite: M00 (algebra liniara -- valori/vectori proprii, SVD, matrice
simetrica pozitiv semidefinita), M01 (varianta, covarianta). Timp estimat: 2-3 h.
Dificultate: 2/3.

Vocabular cheie (vezi GLOSAR.md): componenta principala, varianta explicata,
matrice de covarianta, valoare/vector propriu, SVD, valoare singulara, proiectie,
reconstructie, centrare, t-SNE, UMAP.

## 1. Intuitie

Ai date in d dimensiuni (multe feature-uri) si vrei sa le comprimi la k << d
PASTRAND cat mai mult din "ce se intampla" -- adica din varianta. PCA gaseste o
noua baza ortogonala in care primele axe sunt directiile pe care datele se
imprastie cel mai mult. Proiectand pe primele cateva, pastrezi forma globala a
norului de puncte dar in mai putine numere: bun la vizualizare (2D) si la
comprimare. Daca o directie nu contine aproape nicio varianta, o poti arunca
aproape fara pierdere.

## 2. Formalizare

Avem X (n x d), n exemple, d feature-uri. Centram pe coloane:
  Xc = X - 1 mu^T,   unde   mu = (1/n) sum_i x_i.
Matricea de covarianta (esantion):
  C = (1/(n-1)) Xc^T Xc   (d x d, simetrica, pozitiv semidefinita).
Cautam o directie unitara w (||w|| = 1) astfel incat proiectiile z_i = w^T xc_i
sa aiba varianta maxima. Varianta proiectiilor este:
  Var(z) = (1/(n-1)) sum_i (w^T xc_i)^2 = w^T C w.

## 3. Derivare: PCA prin maximizarea variantei

Maximizam w^T C w sub constrangerea ||w||^2 = w^T w = 1. Lagrangianul:
  L(w, lambda) = w^T C w - lambda (w^T w - 1).
Anulam gradientul fata de w (C simetrica => d/dw (w^T C w) = 2 C w):
  dL/dw = 2 C w - 2 lambda w = 0   =>   C w = lambda w.
Deci w trebuie sa fie un VECTOR PROPRIU al lui C, iar lambda valoarea proprie
asociata. Inmultind C w = lambda w cu w^T la stanga si folosind w^T w = 1:
  w^T C w = lambda.
Adica varianta de-a lungul lui w este chiar valoarea proprie lambda. Ca sa
MAXIMIZAM varianta, alegem vectorul propriu cu cea mai mare valoare proprie =
prima componenta principala. A doua componenta maximizeaza varianta ramasa sub
constrangerea de a fi ORTOGONALA pe prima -> al doilea vector propriu (a doua
valoare proprie). Asa mai departe. Componentele ies ortonormale fiindca C e
simetrica (teorema spectrala: vectori proprii ortogonali).

Legatura cu SVD. Fie SVD-ul datelor centrate:
  Xc = U S V^T,   U (n x r), S (r x r) diagonala cu s_1 >= s_2 >= ..., V (d x r).
Atunci:
  Xc^T Xc = V S U^T U S V^T = V S^2 V^T.
Comparand cu C = (1/(n-1)) Xc^T Xc = V [S^2/(n-1)] V^T, citim direct:
- coloanele lui V (randurile lui V^T) sunt vectorii proprii ai lui C =
  componentele principale;
- valorile proprii sunt lambda_i = s_i^2 / (n - 1) = varianta pe componenta i.
SVD pe Xc e calea numeric stabila (nu formezi explicit C). Scorurile
(proiectiile) sunt T = Xc V = U S.

## 4. Varianta explicata

Varianta totala = suma valorilor proprii = sum_i lambda_i = urma lui C. RATIA de
varianta explicata de componenta j:
  r_j = lambda_j / sum_i lambda_i,   cu   sum_j r_j = 1.
Varianta explicata CUMULATA de primele k componente, sum_{j<=k} r_j, spune cat
"retii" comprimand la k dimensiuni. Alegi k de la un prag (ex. 95%) sau de la
"cotul" curbei. Reconstructia cu k componente:
  Xc_hat = T_k V_k^T = Xc V_k V_k^T,   X_hat = Xc_hat + mu.
Eroarea de reconstructie (Frobenius) este suma valorilor proprii ARUNCATE,
sum_{j>k} lambda_j -- PCA minimizeaza exact aceasta eroare pentru orice k.

## 5. t-SNE si UMAP (doar ideea)

PCA e LINIAR si global: gaseste axe drepte care pastreaza varianta. Cand datele
stau pe o suprafata curba ("manifold"), o proiectie liniara poate amesteca
grupuri. t-SNE si UMAP sunt metode NELINIARE de vizualizare care pastreaza mai
ales structura LOCALA: incearca sa tina aproape in 2D punctele care erau aproape
in spatiul original (t-SNE potriveste distributii de vecinatate prin minimizarea
divergentei KL; UMAP construieste un graf de vecini si il "intinde" in 2D).
Sunt excelente pentru a SCOATE LA VEDEALA grupuri, dar: nu au transform pe date
noi simplu, distantele si dimensiunile clusterelor in plot NU sunt interpretabile
cantitativ, si rezultatul depinde de hiperparametri (perplexity / n_neighbors).
Regula practica: PCA pentru comprimare/interpretare cantitativa, t-SNE/UMAP doar
pentru a privi structura. Aici implementam PCA; t-SNE/UMAP raman conceptuale.

## 6. Algoritm (pseudocod)

```
PCA.fit(X):
  mu = media pe coloane a lui X
  Xc = X - mu                          # CENTRARE (obligatorie)
  U, S, Vt = svd(Xc, economic)         # Xc = U S Vt
  componente = randurile lui Vt        # fixeaza semnul -> determinist
  varianta_j  = S_j^2 / (n - 1)
  ratie_j     = varianta_j / sum(varianta)

PCA.transform(X, k):  return (X - mu) @ componente[:k]^T      # scoruri T_k
PCA.inverse_transform(T_k): return T_k @ componente[:k] + mu  # reconstructie
```

## 7. Exemplu lucrat numeric (verifica-l de mana)

Patru puncte 2D:
  x1 = (2, 0), x2 = (0, 2), x3 = (-2, 0), x4 = (0, -2).

(a) Centrare. Media: mu = ((2+0-2+0)/4, (0+2+0-2)/4) = (0, 0). Datele sunt deja
centrate; Xc = X.

(b) Covarianta (esantion, impartim la n-1 = 3).
  sum x^2 pe coloana 1: 2^2 + 0 + (-2)^2 + 0 = 8.
  sum x^2 pe coloana 2: 0 + 2^2 + 0 + (-2)^2 = 8.
  sum produs coloana1*coloana2: 2*0 + 0*2 + (-2)*0 + 0*(-2) = 0.
  C = (1/3) [[8, 0], [0, 8]] = [[8/3, 0], [0, 8/3]].

(c) Valori si vectori proprii. C e diagonala: valorile proprii sunt 8/3 si 8/3
(egale), iar orice directie e vector propriu. Aici cele doua axe sunt
echivalente: nicio directie nu e mai "intinsa" -- norul e izotrop (un patrat
rotit cu varfurile pe axe). Ratiile de varianta sunt 0.5 si 0.5.

(d) Caz cu directie dominanta (pentru contrast). Schimbam x2 si x4 in
y2 = (0, 6), y4 = (0, -6). Acum:
  col1: 8 (ca inainte);  col2: 6^2 + 6^2 = 72;  produs incrucisat: inca 0.
  C = (1/3) [[8, 0], [0, 72]] = [[8/3, 0], [0, 24]].
Valori proprii: 24 (pe axa y) si 8/3 (pe axa x). Prima componenta este w1 =
(0, 1) -- axa verticala, unde imprastierea e mare. Varianta explicata de PC1:
  24 / (24 + 8/3) = 24 / 26.667 = 0.90.
Adica 90% din varianta sta pe o singura directie; comprimand la 1D pe acea axa,
pierzi doar 10%. Proiectia lui y2=(0,6) pe w1 este w1^T y2 = 6.

(Selftest-ul nucleului verifica exact aceste idei: o directie dominanta capteaza
> 80% si componenta e aliniata cu directia generatoare.)

## 8. Vizualizare

`demo_sil.py` produce `fig_pca_conditii.png`: feature-urile de latenta
standardizate sunt comprimate la 2D (PC1, PC2); scatter-ul e colorat pe
conditie. Conditiile (ideal, loss_*, lat200_*) se aseaza in regiuni distincte ale
planului -- comprimi spatiul de feature-uri si VEZI ca regimurile de retea sunt
separabile. Al doilea panou: varianta explicata cumulata vs numarul de
componente. Date SINTETICE.

## 9. Capcane frecvente

- SCARA feature-urilor: PCA maximizeaza varianta in unitatile date. Un feature in
  milisecunde (rtt) domina unul in fractii (loss) doar pentru ca are numere mai
  mari. STANDARDIZEAZA (z-score) inainte daca feature-urile au scari diferite.
- CENTRAREA e obligatorie: fara scaderea mediei, prima componenta poate ajunge sa
  "explice" doar deplasarea fata de origine, nu imprastierea.
- Componentele NU sunt feature-uri: PC1 e o COMBINATIE liniara a tuturor
  feature-urilor, nu "feature-ul cel mai important". Interpreteaza prin ponderi
  (loadings), cu grija.
- SEMNUL unei componente e arbitrar (SVD il lasa liber); o fixam determinist, dar
  nu citi sens in semn.
- Varianta mare nu inseamna mereu informatie UTILA pentru o sarcina supervizata:
  PCA e nesupervizat, poate arunca o directie cu varianta mica dar discriminanta.
- t-SNE/UMAP: nu citi distante sau marimi de cluster din plot ca fiind reale.

## 10. De ce conteaza pentru teza

Campaniile produc multe feature-uri corelate pe fiecare conditie de retea (p95,
loss, jitter, distanta, derivate). PCA le comprima si lasa sa se VADA daca
conditiile (degradari netem) si cele doua middleware-uri (DDS vs Zenoh) se separa
intr-un plan -- un argument vizual rapid ca regimurile sunt distincte inainte de
orice clasificator. Comprimarea ajuta si la diagnoza redundantei intre feature-uri
si la pregatirea datelor pentru modele mai simple. Tot sintetic acum; pe datele
reale C1/M, acelasi pas devine o figura de inceput in analiza.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa derivi C w = lambda w din maximizarea w^T C w sub ||w|| = 1;
- [ ] sa explici de ce componentele sunt ortonormale (C simetrica);
- [ ] sa legi valorile singulare ale lui Xc de variantele explicate;
- [ ] sa calculezi covarianta si prima componenta de mana pe 3-4 puncte 2D;
- [ ] sa spui de ce standardizezi inainte de PCA si ce face centrarea;
- [ ] sa explici diferenta dintre PCA si t-SNE/UMAP.

## Mergi mai departe

ESL cap. 14.5 (PCA, SVD); ISL cap. 12 (PCA, clustering). Pentru t-SNE/UMAP: van
der Maaten & Hinton 2008 (t-SNE), McInnes et al. 2018 (UMAP). Vezi BIBLIOGRAFIE.md.
