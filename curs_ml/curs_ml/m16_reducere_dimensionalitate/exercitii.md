# M16 -- Exercitii: Reducerea dimensionalitatii (PCA)

Gradat, de la centrare si covarianta la PCA pe datele mele. Rezolva in
`exercitii.py`; solutiile in `solutii.py`. Refoloseste nucleul `pca_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- centreaza si covarianta
`ex1_centre_cov(X)`: centreaza `X` (scade media pe coloane) si intoarce
`(Xc, C)`, unde `C` e covarianta de esantion `Xc^T Xc / (n-1)`. Asert: pe cele 4
puncte din exemplul numeric `teorie.md` sec.7(b), `C == [[8/3, 0], [0, 8/3]]` si
media e zero.

## Ex. 2 (implementeaza) -- varianta de-a lungul unei directii
`ex2_var_dir(X, w)`: varianta proiectiilor `w^T xc_i` (cu `w` unitar). Foloseste
`ex1_centre_cov`. Asert: pe cazul cu directie dominanta din `teorie.md` sec.7(d),
varianta pe `w=(0,1)` este `24` si pe `w=(1,0)` este `8/3`. (Maximul = prima
valoare proprie.)

## Ex. 3 (concept) -- cate componente pentru un prag
`ex3_n_componente(ratii, prag)`: dat vectorul ratiilor de varianta explicata
(descrescator) si un prag in (0,1], intoarce numarul MINIM de componente a caror
varianta CUMULATA atinge pragul. Asert: pe `[0.6, 0.25, 0.1, 0.05]` cu prag `0.9`
da `3`.

## Ex. 4 (aplica) -- prima componenta a directiei dominante
`ex4_pc1_dominanta(seed)`: genereaza date 2D cu o directie dominanta (foloseste
`pca_core._dominant_direction_data`), potriveste `PCA` si intoarce
`(ratie_pc1, cos_aliniere)` -- ratia de varianta a PC1 si `|cos|` intre PC1 si
directia generatoare. Asert: `ratie_pc1 > 0.8` si `cos > 0.99`.

## Ex. 5 (aplica pe datele mele) -- comprima latenta in 2D
`ex5_var_2d()`: pe `make_latency_dataset(n_per_cond=150, seed=0)`, ia feature-urile
`["loss_pct","base_lat_ms","jitter_ms","distance_m"]`, standardizeaza-le
(`utils.standardize`), potriveste `PCA` si intoarce varianta explicata CUMULATA de
primele 2 componente (float). Asert: in (0, 1]. Reflectie: cat din structura
conditiilor retii doar cu 2 numere in loc de 4 feature-uri?
