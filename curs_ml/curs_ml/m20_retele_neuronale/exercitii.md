# M20 -- Exercitii: Retele neuronale

Gradat, de la activari si un pas forward de mana pana la gradient check si MLP vs
liniar pe datele mele. Rezolva in `exercitii.py`; solutiile in `solutii.py`.
Refoloseste nucleul `mlp_core`.

Datele sunt SINTETICE (XOR, sin, latenta semanata din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- ReLU si derivata ei
`ex1_relu_si_derivata(z)`: implementeaza `relu(z) = max(0, z)` si derivata ei
(`1` daca `z > 0`, altfel `0`) de la zero, fara `mlp_core._act`. Returneaza
`(valori, gradient)`. Asert: pe `z=[-2,-0.5,0,1.5,3]` da `[0,0,0,1.5,3]` si
`[0,0,0,1,1]`.

## Ex. 2 (de mana) -- un pas forward pe un neuron
`ex2_forward_un_neuron(x, w1, b1, w2, b2)`: o retea minuscula (1 intrare, 1 neuron
ascuns tanh, 1 iesire liniara): `z1=x*w1+b1`, `a1=tanh(z1)`, `z2=a1*w2+b2`,
`y_hat=z2`. Returneaza `y_hat`. Asert: reproduce exemplul numeric din `teorie.md`
sec.6 (`x=0.5, w1=0.8, b1=-0.1, w2=1.2, b2=0.3` -> `y_hat ~ 0.649575`).

## Ex. 3 (aplica) -- pierderea scade
`ex3_pierdere_scade(X, y, seed)`: antreneaza `MLP(n_hidden=8, tanh, lr=0.05,
n_iter=500)` pe `(X, y)` si intoarce `(loss_primul, loss_ultimul)` din
`loss_history_`. Asert: pierderea a scazut. De ce verificam intai ca SCADE?

## Ex. 4 (verifica) -- gradient check pe W2
`ex4_gradcheck_W2(seed)`: construieste o retea mica de regresie, ia gradientul
analitic `dW2` din `_forward`+`_backward`, compara-l cu `_numerical_grad(..., 'W2')`
(diferente finite) prin `_rel_error`. Returneaza eroarea relativa. Asert: `< 1e-4`.
Aceasta e plasa de siguranta a oricarei retele scrise de mana.

## Ex. 5 (concept aplicat) -- weight decay micsoreaza norma
`ex5_weight_decay_norma()`: pe `y=sin(x)` sintetic, antreneaza doua MLP-uri identice
(aceeasi samanta) cu `l2=0.0` si `l2=0.1`; intoarce `(norma_fara, norma_cu)` din
`weight_norm()`. Asert: cu decay < fara decay. Cum ajuta asta la N mic?

## Ex. 6 (aplica pe datele mele) -- MLP vs liniar pe latenta
`ex6_mlp_vs_liniar_latenta()`: pe `make_latency_dataset(n_per_cond=120, seed=1)`,
feature-uri standardizate -> `log10(rtt_ms)`, compara RMSE-ul de antrenare al unui
MLP (`n_hidden=12, tanh`) cu o regresie liniara cu bias. Returneaza `(rmse_mlp,
rmse_liniar)`. Reflectie: pe semnal aproape liniar, justifica MLP-ul complexitatea?
(Vezi nota onesta din `teorie.md` sec.9.)
