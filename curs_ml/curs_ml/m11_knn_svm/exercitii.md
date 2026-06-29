# M11 -- Exercitii: k-NN si SVM cu kernel

Gradat, de la distante si vot k-NN la subgradientul Pegasos si kernelul RBF.
Rezolva in `exercitii.py`; solutiile in `solutii.py`. Refoloseste `knn_svm_core`.

Datele sunt SINTETICE (semanate aici / din `date_sar.py`).

---

## Ex. 1 (implementeaza) -- distanta euclidiana de la zero
`ex1_dist_euclid(a, b)`: distanta euclidiana intre doi vectori, fara `numpy.linalg`.
Asert: pe `a=(0,0)`, `b=(3,4)` da `5.0`. (Vezi exemplul numeric din `teorie.md`.)

## Ex. 2 (implementeaza) -- votul k-NN de mana
`ex2_vot_knn(dists, labels, k)`: primeste distantele unei interogari catre toate
punctele de antrenare si etichetele lor; intoarce eticheta votata pe cei mai
apropiati `k` vecini (la egalitate, eticheta cu indicele cel mai mic). NU folosi
clasa `KNN`. Asert: pe exemplul din `teorie.md` (4 puncte), `k=1` si `k=3` dau clasa 0.

## Ex. 3 (concept) -- scara feature-urilor la k-NN
`ex3_scara_strica_knn()`: arata ca distantele k-NN sunt dominate de feature-ul cu
scara mare. Construieste 2 puncte de antrenare (clase diferite) si o interogare,
unde pe datele BRUTE k-NN(k=1) da o eticheta, iar pe datele STANDARDIZATE (cu
`utils.standardize`) da CEALALTA. Intoarce `(eticheta_brut, eticheta_std)`.
Asert: cele doua difera. Reflectie: de ce standardizam mereu inainte de k-NN?

## Ex. 4 (implementeaza) -- pasul subgradient Pegasos
`ex4_pas_pegasos(w, x, y, eta, lam)`: un singur pas de actualizare Pegasos.
Regula: daca `y*<w,x> < 1` atunci `w <- (1-eta*lam)w + eta*y*x`, altfel
`w <- (1-eta*lam)w`. Intoarce noul `w`. Asert: cu marja violata, pasul muta `w`
spre `y*x`; cu marja respectata, doar contractia.

## Ex. 5 (aplica) -- Pegasos separa date liniar separabile
`ex5_pegasos_acc(seed)`: genereaza date liniar separabile (refoloseste
`knn_svm_core._linsep`), antreneaza cu `pegasos_svm` si intoarce acuratetea de
antrenare. Asert: `> 0.95`.

## Ex. 6 (implementeaza) -- kernel RBF si efectul lui gamma
`ex6_rbf_gamma(x, z, gamma)`: valoarea scalara `exp(-gamma*||x-z||^2)`, fara
`knn_svm_core`. Asert: `=1` cand `x==z`; in `(0,1)` cand difera; iar pentru aceeasi
pereche, `gamma` mare da o valoare mai mica decat `gamma` mic (nucleu mai ingust).
