# Modulul 8 — QoS (Quality of Service)

## Ce înveți
- Ce este **QoS** și de ce două noduri pot avea același topic, dar să **nu schimbe niciun mesaj**.
- Cele trei politici esențiale: **reliability**, **durability** și **history**.
- Când folosești `BEST_EFFORT` (date de senzor, fluxuri rapide) versus `RELIABLE` (comenzi).
- Ce înseamnă `TRANSIENT_LOCAL` ("latched") și la ce e bun.
- Cum verifici QoS-ul real al fiecărui endpoint cu `ros2 topic info ... --verbose`.
- **Capcana centrală:** QoS incompatibil = **zero mesaje, în tăcere** (fără nicio eroare).

## Conceptul, pe scurt
Imaginează-ți comunicarea pe un topic ca pe trimiterea de **scrisori**. QoS-ul stabilește **regulile poștei**:

- **Reliability** = trimiți scrisoarea cu **confirmare de primire** (RELIABLE: se retrimite până ajunge) sau o pui pur și simplu în cutie și speri c-ajunge (BEST_EFFORT: rapid, dar fără garanție)?
- **Durability** = poșta **păstrează ultima scrisoare** pentru cineva care abia acum își deschide cutia poștală (TRANSIENT_LOCAL = "latched") sau scrisorile trecute sunt pierdute definitiv pentru cei care vin târziu (VOLATILE)?
- **History** = câte scrisori ții în cutia de așteptare înainte să le arunci pe cele vechi (KEEP_LAST + depth) sau le păstrezi pe **toate** (KEEP_ALL)?

Ideea-cheie: **publisher-ul și subscriber-ul trebuie să aibă reguli compatibile.** Dacă subscriber-ul cere confirmare de primire (RELIABLE), dar publisher-ul trimite fără confirmare (BEST_EFFORT), poșta refuză să livreze — **dar nu-ți spune nimic**.

## Cele trei politici

### 1. Reliability (fiabilitate)
| Politică | Ce face | Când o folosești |
|---|---|---|
| `RELIABLE` | Garantează livrarea: retransmite până ajunge. Mai lent, consumă bandă. | **Comenzi**, setări, orice nu vrei să pierzi. |
| `BEST_EFFORT` | "Trimit și uit": fără retransmisii. Rapid, dar mesajele se pot pierde. | **Date de senzor**, fluxuri rapide (camere, LiDAR), unde un cadru pierdut nu contează. |

### 2. Durability (durabilitate)
| Politică | Ce face | Când o folosești |
|---|---|---|
| `VOLATILE` | Doar mesajele trimise **după** ce te-ai abonat. Implicit. | Fluxuri continue (un senzor publică oricum mereu). |
| `TRANSIENT_LOCAL` | "**Latched**": publisher-ul reține ultimele mesaje și le livrează unui subscriber care se abonează **mai târziu**. | Date care se schimbă **rar**: o hartă, o configurație, starea statică a robotului. |

### 3. History (istoric)
| Politică | Ce face |
|---|---|
| `KEEP_LAST` + `depth=N` | Păstrează în coadă ultimele **N** mesaje; cele mai vechi sunt aruncate. (Implicit, `depth=10` la noi.) |
| `KEEP_ALL` | Păstrează **toate** mesajele (limitat de resursele sistemului). Rar necesar. |

### Profilul gata făcut pentru senzori
ROS 2 oferă un profil predefinit pentru date de senzor: `rclpy.qos.qos_profile_sensor_data`. El este, în esență, `BEST_EFFORT` + `KEEP_LAST` cu un `depth` mic — exact ce vrei pentru fluxuri rapide unde prospețimea contează mai mult decât integralitatea:

```python
from rclpy.qos import qos_profile_sensor_data

self.sub = self.create_subscription(
    Image, '/camera/image', self.cb, qos_profile_sensor_data
)
```

## Codul-cheie
Construim `QoSProfile`-ul în funcție de un parametru `profil`, ca să pornim **același nod** cu reguli diferite, fără să edităm codul:

```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

def construieste_qos(self, profil):
    qos = QoSProfile(depth=10)                  # KEEP_LAST cu adancime 10
    if profil == 'best_effort':
        qos.reliability = ReliabilityPolicy.BEST_EFFORT   # rapid, fara garantie
    elif profil == 'transient':
        qos.reliability = ReliabilityPolicy.RELIABLE
        qos.durability = DurabilityPolicy.TRANSIENT_LOCAL # "latched"
        qos.history = HistoryPolicy.KEEP_LAST
    else:  # "reliable" (implicit)
        qos.reliability = ReliabilityPolicy.RELIABLE      # garanteaza livrarea
    return qos
```

Apoi atașăm acest QoS la endpoint:

```python
# Publisher:
self.pub = self.create_publisher(String, '/qos_demo', qos)
# Subscriber:
self.sub = self.create_subscription(String, '/qos_demo', self.cb_mesaj, qos)
```

## Regula de compatibilitate (de reținut!)
La **reliability**, regula este: subscriber-ul poate cere o livrare **cel mult la fel de strictă** ca a publisher-ului.

| Publisher | Subscriber | Se conectează? |
|---|---|---|
| `RELIABLE` | `RELIABLE` | DA |
| `RELIABLE` | `BEST_EFFORT` | DA (subscriber-ul e mai permisiv) |
| `BEST_EFFORT` | `BEST_EFFORT` | DA |
| **`BEST_EFFORT`** | **`RELIABLE`** | **NU — zero mesaje, în tăcere!** |

Pe scurt: un subscriber `RELIABLE` **refuză** un publisher `BEST_EFFORT`, pentru că publisher-ul nu poate garanta ce cere subscriber-ul.

## Cum rulezi

### Experimentul 1 — profiluri INCOMPATIBILE (nu vin mesaje)
În ROS 2 dăm parametri cu `--ros-args -p nume:=valoare`.

**T1 — publisher BEST_EFFORT:**
```bash
ros2 run curs_ros2 m8_pub --ros-args -p profil:=best_effort
```

**T2 — subscriber RELIABLE:**
```bash
ros2 run curs_ros2 m8_sub --ros-args -p profil:=reliable
```

Rezultat: în **T1** vezi "Publicat: mesaj #1, #2, ...", dar în **T2** **nu apare niciun "Primit:"**. Topicul există, ambele noduri rulează, dar QoS-ul incompatibil **blochează livrarea în tăcere**. Aceasta este capcana centrală a modulului.

### Experimentul 2 — profiluri COMPATIBILE (vin mesaje)
Oprește T2 cu `Ctrl+C` și repornește-l cu același profil ca publisher-ul:

**T2 — subscriber BEST_EFFORT:**
```bash
ros2 run curs_ros2 m8_sub --ros-args -p profil:=best_effort
```

Acum în **T2** apar "Primit: mesaj #...". Lăsând ambele pe `reliable` (fără `-p`, valoarea implicită) funcționează la fel de bine.

### Experimentul 3 — "latched" cu TRANSIENT_LOCAL
**T1 — publisher transient (pornește-l PRIMUL și lasă-l să publice câteva mesaje):**
```bash
ros2 run curs_ros2 m8_pub --ros-args -p profil:=transient
```

**T2 — subscriber transient, abonat MAI TÂRZIU:**
```bash
ros2 run curs_ros2 m8_sub --ros-args -p profil:=transient
```

Deși s-a abonat târziu, subscriber-ul primește imediat **ultimele mesaje reținute** de publisher (efectul "latched"). Cu `VOLATILE` (profilurile `reliable`/`best_effort`) nu ai primi mesajele trimise înainte de abonare.

## Verificare
Cu publisher-ul și subscriber-ul pornite, inspectează QoS-ul real al fiecărui endpoint:

```bash
ros2 topic info /qos_demo --verbose
```

Vei vedea, pentru **fiecare** Publisher și Subscription, secțiunea `QoS profile` cu `Reliability`, `Durability`, `History` și `Depth`. Așa confirmi negru pe alb dacă endpoint-urile sunt compatibile sau nu.

```bash
# Numara cati publisheri / subscriberi vede ROS pe topic:
ros2 topic info /qos_demo
```

```bash
# Vezi daca mesajele chiar curg (cu QoS compatibil vei vedea ~2 Hz):
ros2 topic hz /qos_demo
```

> Notă: și `ros2 topic echo /qos_demo` are propriul QoS. Dacă nu vezi nimic la `echo` pe un topic `BEST_EFFORT`, adaugă `--qos-reliability best_effort` — altfel `echo` (RELIABLE implicit) e și el incompatibil!

## Exerciții
1. **Hartă incompatibilitatea.** Pornește publisher-ul pe `best_effort` și un subscriber pe `reliable`. Rulează `ros2 topic info /qos_demo --verbose` și identifică exact linia de `Reliability` care diferă între cele două endpoint-uri. Apoi schimbă subscriber-ul pe `best_effort` și confirmă că acum mesajele curg.
2. **Profilul de senzor.** Modifică (într-o copie de probă) subscriber-ul să folosească `qos_profile_sensor_data` în loc de profilul construit manual. Cu ce profil al publisher-ului funcționează și cu ce profil **nu** funcționează? Explică de ce, pe baza tabelului de compatibilitate.
3. **Latched cu echo.** Pornește doar publisher-ul `transient`, lasă-l să publice câteva mesaje, oprește-l, apoi pornește un subscriber `transient`. Ce primește? Repetă experimentul cu `ros2 topic echo /qos_demo --qos-durability transient_local` și compară comportamentul.

## Capcane frecvente
- **CAPCANA MAJORĂ: QoS incompatibil = ZERO mesaje, în tăcere.** Nu apare nicio eroare, nicio excepție, niciun avertisment. Topicul există, nodurile rulează, dar callback-ul nu se apelează niciodată. Este una dintre cele mai frecvente confuzii reale în ROS 2. Dacă "nu vin mesaje deși totul pare corect", **prima suspiciune trebuie să fie QoS-ul.**
- **Subscriber `RELIABLE` + publisher `BEST_EFFORT` = nu se conectează.** Verifică mereu cu `ros2 topic info /qos_demo --verbose`.
- **`ros2 topic echo` are și el QoS.** Implicit este `RELIABLE`/`VOLATILE`. Pe un topic `BEST_EFFORT` sau `TRANSIENT_LOCAL` trebuie să-i dai opțiunile potrivite (`--qos-reliability`, `--qos-durability`), altfel "echo nu arată nimic" și tragi concluzia greșită că publisher-ul e stricat.
- **Nu pune `RELIABLE` peste tot "ca să fii sigur".** Pe fluxuri rapide de senzor, retransmisiile RELIABLE pot aglomera rețeaua și introduce latență. Pentru date de senzor folosește `BEST_EFFORT` / `qos_profile_sensor_data`.
- **`TRANSIENT_LOCAL` nu păstrează mesajele la infinit pentru oricine.** Reține doar ultimele `depth` mesaje și doar cât trăiește publisher-ul. Dacă oprești publisher-ul, "latch"-ul dispare odată cu el.
- **Schimbarea QoS-ului după creare nu este permisă.** QoS-ul se fixează la `create_publisher` / `create_subscription`. Ca să-l schimbi, recreezi endpoint-ul.
