# M21 -- Exercitii: MDP si Q-learning

Gradat, de la o actualizare Q de mana la antrenarea unui agent pe mediul de
comutare a legaturii. Rezolva in `exercitii.py`; solutiile in `solutii.py`.
Refoloseste `qlearning_core`.

MDP-ul de comutare a legaturii e un MODEL SINTETIC (vezi antetul lui
`qlearning_core.py`): stari = conditii de link, actiuni = DDS/Zenoh, recompensa =
valoare de misiune -- calibrat dupa intuitia C1, NU masurat.

---

## Ex. 1 (concept) -- return cu discount
`ex1_discounted_return(rewards, gamma)`: dat un sir de recompense
`[r_1, r_2, ..., r_T]` si `gamma`, calculeaza return-ul cu discount
`G = r_1 + gamma r_2 + gamma^2 r_3 + ...`. Asert: pe `[1, 1, 1]`, `gamma=0.5`
da `1 + 0.5 + 0.25 = 1.75`.

## Ex. 2 (implementeaza) -- o actualizare Q de mana
`ex2_q_update(q_sa, r, gamma, alpha, q_next_row)`: aplica O actualizare Q-learning
si returneaza noul `Q(s,a)`. `q_next_row` e randul `Q(s', :)`. (Vezi exemplul
numeric din `teorie.md`.) Asert: cu `q_sa=2.0, r=10, gamma=0.9, alpha=0.5,
q_next_row=[3.0, 5.0]` da `8.25`.

## Ex. 3 (aplica) -- politica greedy fata de un tabel Q
`ex3_greedy_policy(Q)`: dat un tabel `Q` de forma `(nS, nA)`, intoarce politica
greedy (un array de `nS` actiuni, `argmax` pe fiecare rand). NU folosi
`greedy_policy` din nucleu -- scrie-o tu cu numpy. Asert: pe
`[[5,1],[1,5],[2,3]]` da `[0, 1, 1]`.

## Ex. 4 (aplica pe mediul meu) -- referinta optima prin iteratie pe valoare
`ex4_optimal_policy()`: construieste mediul de comutare
(`make_link_switch_mdp`), ruleaza `value_iteration` si intoarce politica optima ca
LISTA de nume de actiuni (ex: `["DDS", "Zenoh", "Zenoh"]`). Asert: politica optima
e `["DDS", "Zenoh", "Zenoh"]` (DDS pe link curat, Zenoh cand se degradeaza).

## Ex. 5 (aplica pe mediul meu) -- Q-learning bate o politica statica
`ex5_learned_beats_static()`: pe mediul de comutare, antreneaza Q-learning, apoi
compara recompensa medie pe episod a politicii INVATATE cu cea mai buna politica
STATICA (mereu DDS sau mereu Zenoh). Intoarce `(r_invatat, r_cea_mai_buna_statica)`.
Asert: `r_invatat >= r_cea_mai_buna_statica` (comutarea adaptiva nu pierde fata de
cea mai buna alegere fixa). Reflectie: ce ar trebui sa fie adevarat in DATE ca acest
castig sa conteze pentru C3?
