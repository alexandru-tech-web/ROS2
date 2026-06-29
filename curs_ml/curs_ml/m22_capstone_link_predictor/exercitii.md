# M22 -- Exercitii: CAPSTONE Predictor de link

Gradat, de la asamblarea feature-urilor la impachetarea predictiei intr-o forma
consumabila de un nod ROS subtire. Rezolva in `exercitii.py`; solutiile in
`solutii.py`. Refoloseste `link_predictor_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- dict de feature-uri -> vector ordonat
`ex1_features_to_vector(features)`: foloseste `features_to_vector` ca sa transformi
un dict `{nume: valoare}` in vectorul 1D aliniat la `FEATURE_NAMES`. Asert: lungime
corecta si prima componenta == valoarea primului feature. (De ce conteaza ordinea?
Vezi `teorie.md` sec.3-4.)

## Ex. 2 (aplica) -- antreneaza si masoara acuratetea
`ex2_antreneaza_si_acuratete()`: pe `make_link_usability_dataset(n_per_cond=200,
seed=1)`, split 30% test (seed 0), antreneaza un `LinkUsabilityPredictor` si intoarce
acuratetea pe TEST. Asert: `> 0.85`.

## Ex. 3 (interpreteaza) -- bate baza triviala
`ex3_bate_baza_triviala()`: pe acelasi split, intoarce `(model_acc, base_acc)` unde
baza trivala prezice mereu clasa MAJORITARA din TRAIN. Asert: `model_acc > base_acc`.
Reflectie: la clase dezechilibrate (vezi M09), de ce nu e suficienta acuratetea bruta?

## Ex. 4 (reproductibilitate) -- save -> load identic
`ex4_save_load_identic(tmp_path)`: antreneaza un model, salveaza-l, incarca-l si
intoarce `True` daca etichetele prezise pe TEST coincid EXACT. Asert: `True`. De ce e
asta conditia ca nodul ROS sa fie reproductibil intre porniri?

## Ex. 5 (impacheteaza) -- predictie consumabila
`ex5_predictie_consumabila(features)`: antreneaza modelul, cheama `model.predict` si
intoarce dict-ul `{usable: bool, prob: float}` (prob la 4 zecimale) pe care nodul l-ar
publica pe `/link_predictor/state`. Asert: forma corecta, `prob` in `[0, 1]`.
Reflectie: cum ar folosi `link_adaptive` (C3) acest dict?
