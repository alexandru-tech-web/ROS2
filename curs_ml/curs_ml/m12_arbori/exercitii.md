# M12 -- Exercitii: Arbori de decizie

Gradat, de la impuritate si castig de mana la supra-invatarea unui arbore pe datele
mele. Rezolva in `exercitii.py`; solutiile in `solutii.py`. Refoloseste
`arbori_decizie_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- Gini de mana
`ex1_gini_de_mana(counts)`: din numararile pe clase (ex. `[3, 1]`), calculeaza
`1 - sum_c p_c^2` FARA a folosi `gini()`. Asert: `[2,2] -> 0.5`, `[4,0] -> 0.0`,
`[3,1] -> 0.375`. (Vezi sectiunea 2 din `teorie.md`.)

## Ex. 2 (implementeaza) -- castigul unui split
`ex2_castig_split(y_parinte, y_stanga, y_dreapta)`: reducerea de impuritate Gini
ponderata (foloseste `gini()` din nucleu). Asert: parinte 50/50 cu copii puri ->
castig `0.5`. (Exemplul lucrat 6(b) din `teorie.md`.)

## Ex. 3 (aplica) -- pragul optim
`ex3_prag_optim(X, y)`: pe un set 1D, intoarce pragul ales de `best_split` (Gini).
Asert: pe `x in {1..6}` cu `y=0` pentru `x<=3`, pragul este `3.5`.

## Ex. 4 (aplica pe datele mele) -- acuratete vs adancime
`ex4_acuratete_adancime(max_depth)`: antreneaza un arbore pe `mission_complete`
(`make_mission_outcome_dataset(n=500, seed=3)`, FEATURES, `train_test_split` cu
`test_frac=0.25, seed=0`) si intoarce `(acc_train, acc_test)`. Asert: la
`max_depth=3`, `acc_test > 0.5` si `acc_train >= acc_test`.

## Ex. 5 (concept pe datele mele) -- golul de supra-invatare
`ex5_supra_invatare()`: compara golul `acc_train - acc_test` la un arbore ADANC
(`max_depth=None`) fata de un CIOT (`max_depth=1`). Asert: `gol_adanc >= gol_ciot`.
Reflectie: de ce un arbore adanc are train aproape perfect dar test mai slab, si cum
ar ajuta pre-pruning-ul (cap. 5 din `teorie.md`) sau ensemblurile (M13)?
