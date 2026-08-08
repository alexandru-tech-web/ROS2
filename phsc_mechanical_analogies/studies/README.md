# studies/ -- artefacte de reproductibilitate

Scripturile care produc cifrele si figurile din `../docs/`. Nu sunt noduri ROS
si nu se instaleaza; se ruleaza direct din sursa.

Toate incep cu `import _context`, care adauga radacina pachetului in `sys.path`
daca pachetul nu e instalat. Deci merg si dupa `colcon build`, si direct din
acest director, fara nicio configurare.

## Ce reproduce fiecare

| script | ce produce | durata |
|---|---|---|
| `test_mpc.py` | validare numerica rapida: control optim, valori proprii LQR | 1 s |
| `lqr_sanity.py` | verificarea in trepte a LQR-ului: fara latenta, cu latenta, predictie naiva, predictie Smith | ~1 min |
| `ablation_study.py` | ablatia determinista la tau=100 ms + baleiaj pe praguri | ~2 min |
| `robustness_smith.py` | cat din marja Smith e metoda si cat e potrivire artificiala predictor-planta | ~3 min |
| `closed_loop_compare.py` | NMPC (N=20/10/7) vs LQR+Smith, cu constrangerea de timp real respectata | ~5 min |
| `benchmark_mpc.py` | timp de solve MPC pe orizonturi, plus alternativele real-time | ~3 min |
| `test_smith_variable.py` | bucla inchisa cu tau variabil 50-150 ms, oracol vs estimat | ~1 min |
| `monte_carlo_stability.py` | P(stabil) vs latenta, N incercari perechi, interval Wilson | ~19 min la N=50 |
| `mcnemar_ablation.py` | testul pereche exact pentru 'naiv e mai rau decat lipsa compensarii' | ~5 min |
| `generate_article_figures.py` | cele 8 figuri din `../docs/figuri/`, PDF vectorial + PNG 300 dpi | ~4 min |

## Rulare

```bash
cd ~/ros2_ws/src/phsc_mechanical_analogies/studies
python3 test_mpc.py
python3 monte_carlo_stability.py 50      # argumentul = incercari per latenta
python3 mcnemar_ablation.py
python3 generate_article_figures.py
```

Pentru o verificare rapida: `python3 monte_carlo_stability.py 3` (sub un
minut), dar cu N mic grila nu separa 'fara compensare' de 'naiv'.

`generate_article_figures.py` scrie in `../docs/figuri/`, iar
`../docs/date/_genereaza_csv.py` reface CSV-urile din iesirile brute.

## Reproductibilitate

Seed-uri fixe (`10_000 + k` pentru parametrii fizici, `20_000 + k` pentru
zgomotul pe latenta), comune intre `monte_carlo_stability.py` si
`mcnemar_ablation.py` -- deci perechile din McNemar corespund exact
incercarilor din Monte Carlo.

Timpii de rulare depind de masina. Rezultatele numerice nu.

## Atentie la interpretare

Cifrele sunt din simulare. In Monte Carlo planta primeste parametri trasi
aleator iar controllerul foloseste modelul nominal -- deci exista nepotrivire
reala de model, dar NU si eroare de estimare a latentei (tau e cunoscut cu
~5-10% eroare, doar din oscilatia si jitterul canalului). Pragul realist
pentru hardware, cu 20% eroare pe tau, este mai mic: vezi `../docs/RESULTS.md`
sec. 4.
