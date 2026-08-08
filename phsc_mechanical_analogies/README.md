# phsc_mechanical_analogies

Nucleul PHSC: modelul mecanic si compensarea latentei prin predictor Smith.
Pachet ament_python, fara noduri ROS -- nodurile stau in `phsc_teleop_mpc`.

**Stare: track PE PAUZA.** Conditiile de reactivare sunt in
[`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md).

## 1. Scop

Raspunde la o intrebare de control: cat de multa latenta suporta o bucla
inchisa peste retea, si de ce anume depinde marja. Sistemul de test e un
cart-pole (instabil in bucla deschisa, constanta de timp 215 ms), ales pentru
ca face marja masurabila -- daca latenta e prea mare, pendulul cade.

## 2. Rezultatul principal

Trei strategii de compensare, aceeasi lege de comanda, aceeasi rata:

| strategie | prag de stabilitate (P=50%, N=50) |
|---|---|
| fara compensare | 69 ms |
| predictie naiva (`u = 0` pe fereastra) | **55 ms** |
| predictie Smith (comenzi in zbor din buffer) | **265 ms** |

Predictia naiva este mai rea decat lipsa oricarei compensari. Pe 150 de
incercari perechi nu a salvat niciodata una pe care lipsa compensarii o
pierdea; a stricat 62 (McNemar exact, p < 2.4e-04).

Mecanismul: predictorul presupune ca nimic nu actioneaza pe fereastra de
latenta, supraestimeaza caderea, cere o corectie supradimensionata care
satureaza -- si adauga faza in loc sa o elimine.

## 3. Continut

```
phsc_mechanical_analogies/   nucleul pur, fara ROS
  cartpole_model.py          dinamica neliniara, linearizare, LQR,
                             predict_state_smith (predictia corecta)
  mpc_controller.py          MPC neliniar + compensare de delay
studies/                     scripturile care produc cifrele si figurile
docs/                        metodologie, rezultate, figuri, date
```

Punctul de intrare in documentatie: [`docs/00_INDEX.md`](docs/00_INDEX.md).
Pentru orice cifra citata, sursa e in [`docs/RESULTS.md`](docs/RESULTS.md).

## 4. Verificare rapida

```bash
cd studies
python3 test_mpc.py          # asteptat: 3.1556 N, valori proprii cu Re < 0
```

Scripturile merg si cu pachetul instalat, si direct din sursa (vezi
`studies/_context.py`). Detalii si duratele fiecarui studiu:
[`studies/README.md`](studies/README.md).

## 5. Igiena datelor

Nu exista date de campanie aici. Tot ce e in `docs/date/` provine din
simulare si e regenerabil cu scripturile din `studies/`.

## 6. Limitari

Toate rezultatele sunt din SIMULARE. Nicio validare pe hardware, niciun
operator uman, bucla de shared control inca deschisa. Pragul de 265 ms
presupune ca latenta e cunoscuta cu ~5-10% eroare; cu 20% eroare scade la
100-150 ms (`docs/RESULTS.md` sec. 4). Extinderea pe hardware cere
identificare experimentala prealabila -- vezi
[`docs/UR3_MIGRATION.md`](docs/UR3_MIGRATION.md).
