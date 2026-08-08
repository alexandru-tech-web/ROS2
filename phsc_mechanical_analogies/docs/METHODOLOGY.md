# Predictive Haptic Shared Control with Variable Latency Compensation

Capitol metodologic. Toate cifrele citate sunt masurate; sursa fiecareia este
indicata in `RESULTS.md`. Rezultatele sunt din SIMULARE (N=1 rulare per
conditie, determinista) -- nu sunt date de campanie si trebuie repetate pe
HIL inainte de orice submisie.

## 1. Model mecanic: cart-pole cu timp mort

### 1.1 Dinamica neliniara

Stare `x = [p, p_dot, theta, theta_dot]`, cu `theta` masurat de la verticala
IN SUS si `theta > 0` inclinand varful spre `+x`. Carucior de masa `M` cu
amortizare vascoasa `b`, pendul masa punctiforma `m` la distanta `L`.

Din Euler-Lagrange, cu `x_p = p + L sin(theta)`, `y_p = L cos(theta)`:

```
(M + m) p_ddot + m L (theta_ddot cos(theta) - theta_dot^2 sin(theta)) = u - b p_dot
L theta_ddot + p_ddot cos(theta) = g sin(theta)
```

Eliminand `theta_ddot`:

```
p_ddot = (u - b p_dot + m L theta_dot^2 sin(theta) - m g sin(theta) cos(theta))
         / (M + m - m cos^2(theta))
theta_ddot = (g sin(theta) - cos(theta) p_ddot) / L
```

Integrare: Runge-Kutta 4 cu retinere de ordin zero pe `u` intre pasi.

### 1.2 Linearizare

In jurul echilibrului instabil (`theta = 0`, `theta_dot = 0`, `u = 0`):

```
        [ 0        1           0              0 ]          [    0     ]
   A =  [ 0     -b/M       -m g/M            0 ]     B =  [   1/M    ]
        [ 0        0           0              1 ]          [    0     ]
        [ 0    b/(M L)   g(M+m)/(M L)         0 ]          [ -1/(M L) ]
```

`A[3][3] = 0`: `b` este amortizarea CARUCIORULUI si intra in ecuatia
unghiului doar prin `p_ddot`, adica doar in `A[3][1] = +b/(M L)`. Un termen
`-b/(M L)` pe `theta_dot` ar fi amortizare fictiva pe pendul. Verificat prin
Jacobian numeric (diferente centrate): potrivire la `5.8e-12` pe toate cele
16 intrari.

Cu `M=1.0, m=0.1, L=0.5, g=9.81, b=0.1`: polul instabil in bucla deschisa
este la `4.64 rad/s`, adica o constanta de timp de `215 ms`. Aceasta valoare
fixeaza cerinta de rata a controllerului si e referinta fata de care se
judeca orice latenta.

### 1.3 Analogie mecanica

Canalul cu latenta se comporta ca un amortizor cu timp mort: comanda `u(t)`
ajunge la planta ca `u(t - tau(t))`. Compensarea predictiva este un 'arc
virtual' care intinde comanda in viitor cu exact `tau`.

## 2. Analiza de stabilitate sub latenta

### 2.1 Trei strategii comparate

Toate trei folosesc acelasi LQR (`u = -K x_hat`), aceeasi planta si aceeasi
rata (100 Hz). Singura variabila este ce foloseste ca `x_hat`:

1. **Fara compensare**: `x_hat = x` (starea masurata, deja veche cu `tau`)
2. **Predictie naiva**: `x_hat` = starea propagata `tau` inainte presupunand
   `u = 0` pe fereastra
3. **Predictie Smith**: `x_hat` = starea propagata `tau` inainte folosind
   comenzile REALE deja emise si inca in zbor pe canal, citite din buffer

### 2.2 Rezultatul central

| strategie | prag de latenta |
|---|---|
| fara compensare | 50-80 ms |
| predictie naiva (`u = 0`) | **20-50 ms** |
| predictie Smith (buffer) | 200-250 ms (canal ZOH) |

**Predictia naiva este mai rea decat lipsa oricarei compensari.** La
`tau = 100 ms`, fara compensare pendulul cade la `0.88 s`, cu predictie naiva
la `0.53 s` -- cu 345 ms mai devreme.

### 2.3 Mecanismul esecului

Predictorul naiv presupune ca nimic nu actioneaza pe fereastra de latenta.
Propaga deci un pendul in cadere libera si conchide ca starea viitoare e mult
mai rea decat va fi in realitate, unde comenzile deja trimise vor fi actionat
intre timp. Cere in consecinta o corectie supradimensionata. Comanda satureaza
la `u_max` in `0.35 s` si ramane acolo. Rezultatul este ca predictorul ADAUGA
faza in bucla in loc sa o compenseze -- exact opusul scopului declarat.

Consecinta practica: o compensare de latenta implementata neglijent este mai
periculoasa decat absenta ei. Asta explica de ce implementari de teleoperare
cu 'compensare simpla' esueaza in practica.

## 3. Estimare online de latenta

### 3.1 De ce e o componenta critica, nu un accesoriu

Studiu de sensibilitate pe pragul de stabilitate al buclei LQR+Smith:

| sursa de nepotrivire | prag |
|---|---|
| ideal (predictor = planta) | 300-400 ms |
| canal ZOH (pachete discrete) | 200-250 ms |
| parametri fizici gresiti (+30% masa) | 100-150 ms |
| **tau estimat gresit cu +/-20%** | **100-150 ms** |
| combinat (realist pentru hardware) | 100-150 ms |

O eroare de 20% pe `tau` costa la fel de mult ca o eroare de 30% pe masa
robotului. Si **supraestimarea strica la fel de mult ca subestimarea**, deci
nu exista 'conservatorism' prin marirea lui `tau_est`.

### 3.2 Algoritm

Ping-pong cu timestamp: emitatorul publica `Header` cu `stamp`, partea remota
da echo pastrand timestamp-ul, emitatorul calculeaza `RTT = t_recv - t_send`
si estimeaza `tau ~ RTT/2`.

Filtrare: EWMA cu `alpha = 0.3` la 20 Hz, deci constanta de timp `~170 ms`.

Respingere de outlieri la `3 sigma`, **cu iesire de urgenta**: dupa 8
respingeri consecutive valoarea este acceptata si fereastra repornita. Fara
aceasta clauza, o schimbare reala si sustinuta a latentei arata exact ca un
sir de outlieri si estimatorul ar ramane blocat pe regimul vechi -- adica
tocmai cazul care conteaza intr-o lucrare despre latenta variabila.

### 3.3 Performanta masurata

Cu `tau(t)` sinusoidal 50-150 ms si jitter gaussian de 4 ms pe RTT:

| metrica | valoare |
|---|---|
| eroare medie | +1.06 % |
| eroare p95 | 14.41 % |
| eroare maxima | 18.12 % |

Sub pragul critic de 20%, dar **cu marja subtire**. Limitari cunoscute:
- `tau = RTT/2` presupune canal simetric; pe legaturi asimetrice estimarea e
  partinitoare
- constanta de timp EWMA (170 ms) este comparabila cu perioada variatiei
  latentei, deci filtrul urmareste nivelul dar nu si panta. Un filtru de
  ordinul 2 (Kalman cu stare [tau, d(tau)/dt]) ar reduce eroarea de urmarire.

## 4. Garzi de siguranta

Nodul de siguranta este IN SERIE in lantul de comanda
(`/robot_cmd -> watchdog -> /robot_cmd_safe`), nu doar observator.

| garda | prag implicit | comportament |
|---|---|---|
| stare lipsa in functionare | 200 ms | e-stop |
| stare care nu vine niciodata | 5 s de la pornire | e-stop |
| limita de unghi | 30 grade | e-stop |
| NaN/Inf in stare sau comanda | -- | e-stop |
| clamp comanda | `u_max` | saturare |
| limitare de rata (slew) | 500 N/s | rampa |
| e-stop extern | `/estop_trigger` | e-stop |
| resetare | `/estop_reset` explicit | reia, cu perioada de gratie |

Doua decizii de proiectare care merita explicitate:
- Cat timp e-stop e activ, nodul publica ACTIV zero, repetat. Daca ar tace,
  ultima comanda ar ramane activa in driverul robotului.
- Resetarea este explicita si separata de declansare. Un e-stop care s-ar
  auto-reseta cand starea revine ar putea reporni bratul singur.

## 5. Alegerea arhitecturii de control

| | LQR + Smith | NMPC N=7 | NMPC N=20 |
|---|---|---|---|
| cost / ciclu | 152 us | 39 ms (74 ms cu constrangere tare) | 519 ms (982 ms) |
| rata sustinuta | 100 Hz+ | 25.6 Hz | 1.9 Hz |
| theta rms in bucla inchisa | 1.31 grade | 2.30 grade | cade |
| esantioane / constanta de timp (215 ms) | ~30 | ~2.8 | < 1 |
| constrangeri active pe stare | nu | da | da |

NMPC neliniar nu este imposibil in timp real: la `N=7` ruleaza la 25.6 Hz si
stabilizeaza planta (verificat in nodul ROS: 20.03 Hz masurat cu
`ros2 topic hz`). Este insa de ~500x mai scump si regleaza mai prost decat
LQR cu predictie corecta. Singurul lucru pe care il ofera in plus si LQR nu
poate este impunerea de constrangeri pe stare.

Concluzia: **NMPC ca instrument de proiectare si analiza offline; LQR +
predictor Smith ca implementare in timp real.** Linear MPC (QP) devine
justificat doar daca sunt necesare constrangeri active in timp real.

## 6. Limitari metodologice

- Toate rezultatele sunt din simulare, cu o singura rulare determinista per
  conditie. Nu exista variabilitate statistica raportata.
- Planta si modelul de predictie impart aceeasi structura; nepotrivirea a
  fost introdusa controlat (sec. 3.1), nu observata pe hardware.
- Latenta masurata cu `latency_estimator` a fost verificata doar pe loopback
  local (1.3 ms). RTT-ul peste o legatura reala nu a fost inca masurat in
  bucla de control.
- Feedback-ul haptic este generat si publicat, dar nu a fost evaluat cu
  operator uman si nici cu un dispozitiv haptic real.
- Bucla de shared control este deschisa: `alpha` nu influenteaza inca planta.
