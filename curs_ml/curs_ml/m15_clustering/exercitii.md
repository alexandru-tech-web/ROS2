# M15 -- Exercitii: Clustering

Gradat, de la cei doi pasi Lloyd de mana la alegerea lui k si scara feature-urilor
pe datele mele. Rezolva in `exercitii.py`; solutiile in `solutii.py`. Refoloseste
`clustering_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- pasul de atribuire Lloyd
`ex1_atribuire_lloyd(X, centers)`: pentru fiecare rand din `X` (n x d), indicele
celui mai apropiat centroid din `centers` (k x d), cu distanta euclidiana. NU folosi
`kmeans`. Asert: pe `X=[0,1,9,10]` (1D) si centroizi `[0],[10]` da `[0,0,1,1]`.
(Vezi exemplul numeric din `teorie.md`, pasul de atribuire.)

## Ex. 2 (implementeaza) -- pasul de actualizare a centroizilor
`ex2_actualizare_centroizi(X, labels, k)`: noul centroid al fiecarui cluster e MEDIA
punctelor sale. Asert: pe `X=[0,1,9,10]`, `labels=[0,0,1,1]` da centroizii `0.5` si
`9.5`. De ce e media optimul pentru suma patratelor? (Vezi derivarea din `teorie.md`.)

## Ex. 3 (implementeaza) -- inertia
`ex3_inertie(X, labels, centers)`: suma pe toate punctele a distantei la PATRAT pana
la centroidul propriului cluster. Asert: cu centroizii `0.5, 9.5` da `1.0`
(4 puncte x 0.25). Asta e exact obiectivul minimizat de k-means.

## Ex. 4 (aplica) -- recupereaza gaussienele
`ex4_recupereaza_gaussiene()`: pe `_three_gaussians(n=80, seed=1)`, ruleaza
`kmeans(k=3, n_init=10, seed=0)` si intoarce acuratetea atribuirii fata de adevar
(`cluster_accuracy`, maxim pe permutari). Asert: `> 0.97`. De ce trebuie maximul pe
permutari? (Cluster-ele nu au nume canonice.)

## Ex. 5 (aplica pe datele mele) -- alege k cu silhouette
`ex5_alege_k()`: pe `make_channel_dataset('urban_rubble', seed=2, n=300)`, feature-uri
STANDARDIZATE, ruleaza `kmeans` pentru `k` in {2,3,4,5} si intoarce k-ul cu silhouette
maxim. Asert: `== 3`. De ce nu poti alege k minimizand inertia? (Vezi capcanele.)

## Ex. 6 (capcana) -- scara feature-urilor conteaza
`ex6_scara_conteaza()`: construieste doua grupuri unde structura ADEVARATA traieste
intr-un feature 'mic' (~0.15 vs ~0.85), iar un al doilea feature e zgomot de
amplitudine mare (`normal(80, 25)`). Ruleaza `kmeans(k=2)` (a) pe date BRUTE si (b)
STANDARDIZATE; intoarce `(acc_brut, acc_std)` fata de etichetele adevarate. Asert:
`acc_std > acc_brut`. Reflectie: de ce silhouette NU e metrica buna aici (e calculat
in spatiul dominat de zgomot), iar comparatia corecta e cu adevarul?
