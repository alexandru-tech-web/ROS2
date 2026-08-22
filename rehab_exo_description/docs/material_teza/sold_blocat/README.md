# Soldul blocat prin player: ce s-a eliminat, si contradictia ramasa

Trei exercitii pareau sa pice; masurat corect, patru lasa soldul complet nemiscat.
Sesiune de diagnostic 22 aug 2026. **Mecanismul NU a fost gasit.** Ce urmeaza e ce s-a
eliminat prin masurare, ca sa nu fie reincercat, si punctul exact unde firul se rupe.

## Corectie de metoda, inainte de orice

Impartirea "9 trec / 3 pica" era **artefact de esantionare**: verdictele se luau
intr-o singura clipa, la finalul exercitiului, iar exercitiile se termina cu soldul
la 0 -- deci un sold BLOCAT la 0 arata identic cu unul care a urmat traiectoria.
Cu esantionare continua (`smoke_cont.py`), imaginea reala:

| exercitiu | amplitudine sold | eroare max masurata | interpretare |
|---|---:|---:|---|
| `full_extension` | 0.5609 | 0.0296 | urmareste |
| `alternating_march` | 1.0097 | 0.6901 | partial |
| `leg_wave` | 0.7853 | 0.7853 | **nemiscat** |
| `hip_raise` | 1.1220 | 1.1220 | **nemiscat** |
| `hip_alternating` | 1.2342 | 1.2342 | **nemiscat** |
| `hip_hold` | 1.3464 | 1.3464 | **nemiscat** |

Eroare EGALA cu amplitudinea inseamna articulatie care nu s-a clintit.

## Eliminate prin masurare (NU se reincearca)

| ipoteza | test | rezultat |
|---|---|---|
| supervizorul tine articulatia | `supervizor:=false` | acelasi blocaj |
| coliziunea coloanei soldului | coloana facuta vizuala | acelasi blocaj (bugul era real, a ramas reparat) |
| blocaj mecanic la unghi mare | comanda directa in trepte 0.2 .. 1.3 rad | urmarire perfecta |
| `use_sim_time` pe expeditor | replica cu true si cu false, in sesiuni CURATE separate | ambele merg |
| numarul de puncte / durata | replica exacta, 271 puncte pe 27 s, din alt nod | merge |
| continutul mesajului | diff pe campuri intre mesajul playerului si replica | **sold identic, delta 0.0**; doar 2.1e-05 pe genunchi, din `q_init` |
| al doilea pretendent la interfata | `list_hardware_interfaces` IN TIMPUL esecului | `left_hip_joint/position [claimed]`, un singur detinator |
| genunchiul intins ca atare | genunchi indoit la 90 inainte de exercitiu | tot blocat |

## Ce s-a stabilit

**Esecul e SUB JTC.** In timpul blocajului, JTC raporteaza el insusi eroarea:

```
reference.positions[0] = 1.346379
feedback.positions[0]  = -9.1e-14
error.positions[0]     = 1.346379
```

Interfata de pozitie a soldului e revendicata de JTC si de nimeni altcineva. Deci
comanda pleaca corect si nu ajunge in fizica.

**`neutral` duce robotul la TOT ZERO, nu la POSTURA_INITIALA.** Descoperit pe drum;
nu e mecanismul, dar e un defect propriu: demo-ul porneste deci cu piciorul complet
intins, nu in postura de lucru.

## Contradictia ramasa: firul de reluat

Doua teste aproape identice dau rezultate opuse. Difera DOAR prin istoric:

| test | comanda | istoric | rezultat |
|---|---|---|---|
| `disc.py` A | un punct: sold 1.3464, genunchi 1.5708 | robot in postura de lucru | soldul ajunge la **+1.3464** |
| `minim.py` B | acelasi punct | dupa ce piciorul fusese intins complet si indoit la loc | **blocat** |

Sugereaza o stare care se INTEPENESTE sub JTC odata ce piciorul trece prin extensie
completa, si care nu se elibereaza cand genunchiul revine. Nu am confirmat-o: e
ipoteza urmatoarei sesiuni, si se testeaza cu doua sesiuni CURATE, una care trece
prin extensie completa si una care nu.

## Capcana de metoda, consemnata

Doua brate de test in ACEEASI sesiune se contamineaza: al doilea porneste din starea
lasata de primul. M-a pacalit o data (a dat "use_sim_time e cauza", fals). Orice
comparatie A/B se face in sesiuni separate.
