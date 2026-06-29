# M02 -- Exercitii: Optimizare pentru ML

Gradat, de la verificarea gradientului la metode cu moment si oprire timpurie.
Banc de proba: o patratica SPD `f(w) = 0.5 w^T A w - b^T w` cu optim analitic
`w* = A^-1 b` (din nucleul `optimizare_core`). Rezolva in `exercitii.py`;
solutiile in `solutii.py`.

Determinism: `numpy.random.default_rng(seed)`.

---

## Ex. 1 (implementeaza) -- gradient prin diferente finite centrate
`ex1_grad_numeric(f, w, h)`: `d f / d w_i ~ (f(w+h e_i) - f(w-h e_i)) / (2h)`.
Asert: coincide cu gradientul analitic sub 1e-5. E unealta de DEBUG pentru orice
gradient implementat de mana.

## Ex. 2 (implementeaza) -- coborare pe gradient (batch GD)
`ex2_gd(grad, w0, eta, n_iter)`: itereaza `w <- w - eta * grad(w)`. Asert: cu
pasul optim converge la `w*`.

## Ex. 3 (implementeaza) -- moment (heavy-ball)
`ex3_momentum(grad, w0, eta, mu, n_iter)`: `v <- mu*v - eta*grad(w); w <- w + v`,
`v` initial 0. Asert: converge la `w*`. De ce accelereaza momentul pe vai inguste
(conditionare mare)?

## Ex. 4 (deriva si aplica) -- pasul optim
`ex4_best_step(A)` = `2 / (lambda_max(A) + lambda_min(A))` (via
`numpy.linalg.eigvalsh`). Acesta minimizeaza factorul de contractie al GD pe
patratica. Asert: valoarea exacta.

## Ex. 5 (implementeaza) -- oprire timpurie cu rabdare
`ex5_early_stopping(grad, value_val, w0, eta, n_iter, patience)`: GD pe
antrenare, dar urmareste pierderea de VALIDARE; tine cel mai bun w; daca validarea
nu se imbunatateste `patience` iteratii, opreste si intoarce CEL MAI BUN w (nu
ultimul), cu `(w_best, best_val, n_iteratii)`. Asert: w_best mai aproape de
optimul de validare decat de cel de antrenare; s-a oprit inainte de n_iter.
Legatura cu supra-invatarea (preludiu la M03/M07).
