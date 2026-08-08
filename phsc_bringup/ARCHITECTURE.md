# Arhitectura PHSC (Predictive Haptic Shared Control)

Document de decizie, runda 3. Toate cifrele sunt masurate pe masina de
dezvoltare (Ubuntu 24.04, ROS 2 Jazzy, Python 3.12, numpy 1.26 / scipy 1.11).

## Decizia

Doua straturi, cu roluri separate:

```
Strat REAL-TIME (100 Hz, in ROS 2 si pe hardware)
  LQR (castig precalculat) + predictor Smith neliniar
  Predictia foloseste bufferul de comenzi EMISE (in zbor pe canal),
  propagat prin dinamica neliniara cu RK4.
  Cost masurat: ~152 us/ciclu.

Strat OFFLINE (analiza, tuning, comparatii pentru teza)
  NMPC neliniar (SLSQP) pe orizont N=10..20.
  Cost masurat: 87 ms (N=10) .. 519 ms (N=20) per solve.
  Rol: proiectare, studii de stabilitate, referinta de comparatie.
```

## De ce, in cifre

| | LQR + Smith | NMPC N=7 | NMPC N=20 |
|---|---|---|---|
| cost / ciclu | **152 us** | 39 ms (74 ms cu theta_max) | 519 ms (982 ms) |
| rata sustinuta | **100 Hz+** | 25.6 Hz (13.5 Hz) | 1.9 Hz (1.0 Hz) |
| theta rms in bucla inchisa | **1.31 grade** | 2.30 grade | cade |
| esantioane / constanta de timp a instabilitatii (215 ms) | **~30** | ~2.8 | < 1 |
| constrangeri active pe stare | nu | da | da |

NMPC nu este 'imposibil in timp real' -- N=7 ruleaza la 25.6 Hz si
stabilizeaza planta. Este insa de ~500x mai scump si regleaza mai prost decat
LQR cu o predictie corecta a starii. Avantajul lui real este singurul lucru pe
care LQR nu il poate face: sa impuna constrangeri pe stare si comanda.

## Rezultatul care justifica arhitectura

Ablatie, LQR pe cart-pole, tau = 100 ms constant, controller la 100 Hz:

| conditie | theta max | verdict |
|---|---|---|
| 1. fara compensare | 5954 grade | cade la 0.88 s |
| 2. predictie naiva (u=0 pe fereastra) | 5115 grade | **cade la 0.53 s** |
| 3. predictie Smith (buffer de comenzi) | **6.43 grade** | **stabil** |

Conditia 2 este mai rea decat conditia 1, cu 345 ms mai devreme la cadere.
Praguri de latenta: fara compensare 50-80 ms, predictie naiva 20-50 ms,
predictie Smith peste 300 ms in conditii ideale.

Concluzie: nu conteaza doar CA prezici starea, ci CU CE comanda o prezici.
O compensare implementata neglijent este mai rea decat lipsa ei.

## Marja reala pe hardware (nu cea ideala)

Pragul de 300-400 ms este obtinut cu predictor identic cu planta. Pe robot
real acest lucru nu se intampla. Masurat, cu nepotriviri introduse controlat:

| sursa de nepotrivire | prag de stabilitate |
|---|---|
| ideal (predictor = planta) | 300-400 ms |
| canal ZOH (pachete discrete) | 200-250 ms |
| parametri fizici gresiti (+30% masa) | 100-150 ms |
| **tau estimat gresit cu +/-20%** | **100-150 ms** |
| combinat (realist pentru hardware) | **100-150 ms** |

**Sensibilitatea dominanta este la eroarea de estimare a latentei**, nu la
parametrii fizici si nu la forma canalului: 20% eroare pe tau taie pragul de
la 300-400 ms la 100-150 ms. Deci estimarea online a lui tau nu este un
detaliu de implementare, ci o componenta critica a buclei.

## Ce inseamna pentru teza

- Capitol de metoda: NMPC ca instrument de proiectare si analiza (offline).
- Capitol de implementare: LQR + predictor Smith, 100 Hz, cu pragul de
  latenta masurat si cu studiul de sensibilitate de mai sus.
- Contributia experimentala cea mai clara: ablatia in trei conditii, plus
  observatia ca marja reala este dictata de calitatea estimarii latentei.

Linear MPC (QP / OSQP) merita adaugat DOAR daca ai nevoie de constrangeri
active in timp real (~1 ms/solve). Daca nu, LQR + Smith este suficient si mai
usor de aparat metodologic.

## Parametri relevanti ai nodului

- `theta_mode`: `hard` (constrangere exacta, ~2x timp de solve) | `soft`
  (penalizare in cost, aproape gratis, fara garantie) | `none`
- `n_pred`: sub-pasi de integrare pe fereastra de latenta (default 20)
- `tau_est`, `tau_var`: latenta estimata; vezi sensibilitatea de mai sus
