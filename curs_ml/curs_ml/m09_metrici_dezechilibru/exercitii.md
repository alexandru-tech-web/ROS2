# M09 -- Exercitii: Metrici, dezechilibru si calibrare

Gradat, de la matricea de confuzie si AUC de mana la alegerea pragului si
calibrare pe datele mele. Rezolva in `exercitii.py`; solutiile in `solutii.py`.
Refoloseste `metrici_calibrare_core` si `utils`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- acuratetea care minte
`ex1_acuratete_majoritar(y)`: acuratetea clasificatorului care prezice MEREU clasa
majoritara. Asert: pe `y` cu 70 de zerouri si 30 de unu da `0.70`. Reflectie:
de ce e asta baza fata de care compari orice model? (Vezi `teorie.md` sec. 3.1.)

## Ex. 2 (implementeaza) -- AUC prin numararea perechilor
`ex2_auc_perechi(y, scor)`: AUC de la zero, prin bucle duble pe perechi
(pozitiv, negativ), egalitatile cu 0.5. NU folosi `roc_auc`. Asert: pe pozitivii
`{0.9, 0.4}` si negativii `{0.6, 0.3}` da `0.75` (exemplul din `teorie.md` sec. 5b);
si coincide cu `roc_auc` al nucleului pe date aleatoare.

## Ex. 3 (concept) -- precizie/recall de mana
`ex3_precizie_recall(y, yp)`: intoarce `(precizie, recall)` din matricea de
confuzie (poti folosi `confusion_matrix` din utils). Asert: pe
`y=[1,1,1,0,0]`, `yp=[1,1,0,1,0]` da `(2/3, 2/3)` (exemplul din `teorie.md` sec. 5a).

## Ex. 4 (aplica) -- pragul pentru un recall-tinta
`ex4_prag_recall(y, scor, r_tinta)`: foloseste `threshold_for_recall` si intoarce
`(prag, recall_obtinut)`. Asert: recall-ul obtinut `>= r_tinta` si pragul ales e
cel mai mare care inca atinge tinta (recall la prag+epsilon ar cadea sub tinta).

## Ex. 5 (aplica pe datele mele) -- AUC pe link-ul dezechilibrat
`ex5_auc_link()`: pe `make_link_usability_dataset` (clase dezechilibrate),
construieste un scor MONOTON simplu (ex. `-p95_ms`: cu cat p95 e mai mic, cu atat
link-ul e mai probabil utilizabil) si intoarce AUC-ul fata de eticheta `usable`.
Asert: AUC > 0.7 (semnalul exista) si < 1.0 (scorul brut nu e perfect). Reflectie:
de ce e AUC mai informativ aici decat acuratetea?

## Ex. 6 (aplica pe datele mele) -- calibrare cu Platt
`ex6_calibrare_platt()`: ia scorul brut din Ex. 5 (adus in [0,1] cu o sigmoida),
masoara ECE inainte, potriveste `platt_fit`, masoara ECE dupa. Intoarce
`(ece_brut, ece_calibrat)`. Asert: `ece_calibrat <= ece_brut` (calibrarea nu
strica; de obicei imbunatateste).
