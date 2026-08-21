# Mase si inertii NEVERIFICATE -- lista completa

Sursa: urdf/rehab_exo.urdf.xacro. Statut: PLACEHOLDER pentru simulare.
GAP 1 din SPEC_LLR_twin_din_PDF.md: documentul tehnic NU contine mase pe
segmente, centre de masa sau inertii. Cifrele de mai jos NU au sursa
documentara si sunt INTERZISE pentru concluzii dinamice.

Valorile raman numeric neschimbate fata de URDF-ul livrat (Valul 1 nu
schimba nicio cifra); li se schimba doar STATUTUL, din date in placeholder.

| link | masa [kg] | izz | statut |
|---|---|---|---|
| base_link | 22.000 | 1.558333 | PLACEHOLDER |
| seat_link | 9.000 | 0.317400 | PLACEHOLDER |
| backrest_link | 6.000 | 0.108250 | PLACEHOLDER |
| human_torso | 32.000 | 0.461867 | PLACEHOLDER (model de pacient, nu piesa de robot) |
| left_thigh | 6.500 | 0.100533 | PLACEHOLDER |
| left_thigh_ext | 0.800 | 0.001813 | PLACEHOLDER |
| left_shank | 4.000 | 0.008167 | PLACEHOLDER |
| left_shank_ext | 0.600 | 0.000160 | PLACEHOLDER |
| left_foot | 1.200 | 0.007720 | PLACEHOLDER |
| right_thigh | 6.500 | 0.100533 | PLACEHOLDER |
| right_thigh_ext | 0.800 | 0.001813 | PLACEHOLDER |
| right_shank | 4.000 | 0.008167 | PLACEHOLDER |
| right_shank_ext | 0.600 | 0.000160 | PLACEHOLDER |
| right_foot | 1.200 | 0.007720 | PLACEHOLDER |

Total: 95.200 kg (include human_torso = model de pacient).
Sarcina maxima pacient ramane GAP 7 -- necunoscuta.
