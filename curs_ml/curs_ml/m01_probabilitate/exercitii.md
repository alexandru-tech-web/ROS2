# M01 -- Exercitii: Probabilitate si statistica pentru ML

Gradat, de la formule de baza la estimare si bootstrap pe datele mele. Rezolva in
`exercitii.py` (stub-uri cu TODO); aserturile pica pana completezi. Solutiile
complete sunt in `solutii.py`.

Reaminteste-ti: datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).
Determinism: foloseste `rng(seed)` / `numpy.random.default_rng(seed)`.

---

## Ex. 1 (implementeaza) -- densitatea gaussiana de la zero
`gauss_pdf(x, mu, sigma)` = `1/sqrt(2*pi*sigma^2) * exp(-(x-mu)^2/(2*sigma^2))`.
Asert: `gauss_pdf(0;0,1) = 1/sqrt(2*pi)` si simetria in jurul lui mu.

## Ex. 2 (implementeaza) -- MLE pentru Gauss
`mle_gauss(samples)` intoarce `(mu_hat, sigma2_hat)` cu varianta avand NUMITOR n
(estimatorul de verosimilitate maxima, nu n-1). Asert: pe `[1,2,3,4]` da
`(2.5, 1.25)`.

## Ex. 3 (implementeaza) -- MLE pentru Bernoulli
`mle_bernoulli(samples)` = fractia de 1. Asert: `[1,1,0,0,1] -> 0.6`.

## Ex. 4 (implementeaza) -- interval de incredere prin bootstrap
`bootstrap_mean_ci(samples, n_boot, alpha, seed)`: reesantioneaza CU inlocuire de
`n_boot` ori, ia cuantilele `(alpha/2, 1-alpha/2)` ale mediilor reesantionate.
Foloseste `rng(seed)`. Asert: intervalul acopera media reala si e rezonabil de
ingust. De ce e bootstrap-ul potrivit la N mic (cazul campaniilor mele)?

## Ex. 5 (transfer pe alta conditie) -- media RTT loss_30/Zenoh
`media_rtt_loss30_zenoh()`: pe `make_latency_dataset(n_per_cond=300, seed=0)`,
filtreaza `condition=='loss_30'` si `middleware=='Zenoh'`, intoarce media `rtt_ms`.
Asert: in interval plauzibil (1500..6000 ms). Reflectie: cum se leaga aceasta
medie de p95-ul din tabelul C1?
