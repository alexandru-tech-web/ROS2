# M08 -- Exercitii: Regresie logistica

Gradat, de la sigmoid si log-loss la antrenarea nucleului si pragul de decizie pe
datele mele. Rezolva in `exercitii.py`; solutiile in `solutii.py`. Refoloseste
`regresie_logistica_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (concept) -- proprietatile sigmoidei
`ex1_sigmoid_proprietati(z)`: foloseste `sigmoid` din nucleu si intoarce
`(sigmoid(z), 1 - sigmoid(-z))`. Asert: cele doua sunt egale (simetria sigmoidei) si
`sigmoid(0) = 0.5`. (Vezi exemplul numeric din `teorie.md`.)

## Ex. 2 (implementeaza) -- log-loss de la zero
`ex2_log_loss_manual(y_true, p)` fara a apela `cross_entropy_loss` din nucleu;
tunde `p` in `[1e-12, 1-1e-12]` ca log-ul sa nu explodeze. Asert: predictie aproape
perfecta -> ~0; pe `y=[1,0]`, `p=[0.5,0.5]` da `ln 2`. De ce `ln 2`?

## Ex. 3 (implementeaza) -- un pas de gradient
`ex3_un_pas_gradient(X, y, w, lr)`: adauga interceptul cu `add_bias`, calculeaza
`p = sigmoid(Phi w)`, gradientul `g = (1/n) Phi^T (p - y)` si intoarce
`w - lr*g`. Asert: un pas pornind din `w=0` SCADE pierderea. (Acelasi gradient ca in
derivarea din `teorie.md`.)

## Ex. 4 (aplica pe datele mele) -- acuratete pe utilizabilitate
`ex4_acuratete_test(seed)`: pe `make_link_usability_dataset` cu feature-urile
standardizate, antreneaza `LogisticRegressionGD(lr=0.3, n_iter=4000, seed=seed)` si
intoarce acuratetea pe train. Asert: `> 0.9`. Atentie: clasele sunt DEZECHILIBRATE
(~30% usable) -- acuratetea mare nu spune toata povestea (vezi M09).

## Ex. 5 (aplica) -- pragul de decizie vs recall
`ex5_prag_si_recall(prag)`: antreneaza nucleul pe acelasi set si intoarce RECALL-ul
clasei pozitive pentru un `prag` aplicat pe probabilitate (`predict(X, threshold=prag)`).
Asert: un prag mai MIC (0.1) da recall `>=` decat un prag mai MARE (0.9). Reflectie:
cand vrei recall mare cu pretul preciziei (ex. nu rata o legatura proasta)?
