# studies/ -- artefacte de reproductibilitate

Scripturile care produc tabelele si figurile citate in documentatia PHSC.
Nu sunt noduri ROS si nu se instaleaza; se ruleaza direct din sursa.

## Ce reproduce fiecare

| script | ce produce |
|---|---|
| `monte_carlo_stability.py` | P(stabil) vs latenta pentru cele trei strategii, cu interval Wilson 95%; pragurile 69 / 55 / 265 ms; figura `monte_carlo_stability.png` |
| `mcnemar_ablation.py` | testul pereche McNemar exact pentru 'naiv este mai rau decat lipsa compensarii' (`c=0`, p < 2.4e-04) |

## Rulare

Cu pachetul construit (varianta recomandata):

```bash
cd ~/ros2_ws && ./build_phsc.sh
source install/setup.bash
cd src/phsc_mechanical_analogies/studies
python3 monte_carlo_stability.py 50      # ~19 min
python3 mcnemar_ablation.py              # ~5 min
```

Argumentul lui `monte_carlo_stability.py` este numarul de incercari per
valoare de latenta (implicit 50). Pentru o verificare rapida: `... 3`
(sub un minut), dar cu N mic grila nu separa 'none' de 'naiv'.

## Reproductibilitate

Seed-urile sunt fixe (`10_000 + k` pentru parametrii fizici, `20_000 + k`
pentru zgomotul pe latenta), deci rezultatele sunt identice la re-rulare pe
aceeasi masina. Cele doua scripturi folosesc EXACT aceleasi seed-uri, deci
perechile din McNemar corespund incercarilor din Monte Carlo.

Timpii de rulare depind de masina. Rezultatele numerice nu.

## Atentie la interpretare

Cifrele sunt din simulare. Planta primeste parametri trasi aleator, iar
controllerul foloseste modelul nominal -- deci exista nepotrivire reala de
model, dar NU si eroare de estimare a latentei (controllerul cunoaste tau cu
~5-10% eroare, doar din oscilatia si jitterul canalului). Pragul realist
pentru hardware, cu 20% eroare pe tau, este mai mic: vezi
`~/phsc_docs/RESULTS.md` sec. 4.
