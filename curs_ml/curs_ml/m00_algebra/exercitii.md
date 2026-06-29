# M00 -- Exercitii: Algebra liniara aplicata

Gradat, de la rulare/interpretare la implementare. Rezolva in `exercitii.py`
(stub-uri cu TODO). Aserturile pica pana completezi corect. Solutiile complete
sunt in `solutii.py` (ruleaza-l ca sa verifici dupa ce incerci singur).

Reaminteste-ti: datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).
Determinism: `numpy.random.default_rng(seed)`.

---

## Ex. 1 (implementeaza) -- similaritatea cosinus
`cosine_similarity(x, y)` = `<x, y> / (||x||_2 ||y||_2)`, in [-1, 1]; daca un
vector e ~0 intoarce 0.0. Foloseste doar produs scalar si norma L2. Asert:
cos(x, x) = 1, vectori ortogonali = 0, antiparalel = -1.

## Ex. 2 (implementeaza) -- proiectia pe o baza ortonormala
`project_onto_basis(x, Q)` cu `Q^T Q = I` intoarce `(p, reziduu)` unde
`p = Q (Q^T x)` si `reziduu = x - p`. Asert: proiectia pe e1,e2 din R^3 da
componentele asteptate, iar reziduul e ortogonal pe fiecare coloana a lui Q.

## Ex. 3 (implementeaza) -- fractia de varianta explicata
`explained_variance_ratio(C)` pentru o matrice simetrica C: valorile proprii
(via `numpy.linalg.eigh`) sortate descrescator, normate la suma 1. Asert: pe
`diag(4,1,0)` da `(0.8, 0.2, 0.0)` cu suma 1.

## Ex. 4 (transfer pe datele mele) -- axa dominanta a latentei
`dominant_axis_latency(seed)`: pe `make_latency_dataset`, standardizeaza
feature-urile `['loss_pct','base_lat_ms','jitter_ms','distance_m','rtt_ms']`,
calculeaza covarianta cu nucleul si aplica `power_iteration`. Intoarce
`(valoare_proprie_dominanta, vector_propriu_dominant)` cu `||v||_2 = 1`. Asert:
vectorul e normat, valoarea proprie > 1. Reflectie: ce feature-uri incarca axa
dominanta si ce inseamna asta despre structura de covarianta a telemetriei?
