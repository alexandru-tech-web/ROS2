# Modulul 13 — Proiect final (capstone)

## Ce înveți
- Cum **integrezi** într-un singur sistem coerent tot ce ai învățat: **parametri** (M4), **topicuri** (M2), un **serviciu custom** (M5 + M7) și o **logică pură testată**.
- Cum se separă curat **decizia** (nucleul pur `logica.py`) de **infrastructura** (nodurile ROS care doar "îmbracă" funcția).
- Cum se schimbă comportamentul unui sistem **live**, fără restart, printr-un serviciu.
- **Lecția de aur** a întregului repo: *nucleu pur + teste înainte de orice rulare live*.

## Conceptul, pe scurt
Imaginează-ți un **termostat dintr-o seră**: un **termometru** măsoară temperatura și o anunță continuu (nu-i pasă cine ascultă), iar un **panou de control** ascultă valoarea, o **interpretează** (e normal? e cald? e periculos?) și aprinde o lumină de alarmă. Dacă vine vara și plantele suportă mai mult, un operator **rotește un buton** și mută pragul — fără să oprească instalația.

În proiectul nostru:
- **Termometrul** = nodul `senzor_temperatura` (publisher pe un topic).
- **Panoul de control** = nodul `monitor_temperatura` (subscriber + alarmă + serviciu).
- **Butonul de prag** = serviciul custom `/ajusteaza_prag`.

### Arhitectura (diagramă text)

```
                 parametri (M4):
                 rata, valoare_baza, amplitudine
                          |
                          v
   +--------------------------+        std_msgs/Float64
   |   senzor_temperatura     | ----------------------------+
   |   (M13 senzor, publisher)|     /senzor/temperatura      |
   +--------------------------+                              |
   valoare = baza + ampl*sin(t)                              v
   (DETERMINIST, fara random)                  +----------------------------+
                                               |   monitor_temperatura      |
   parametri (M4):                             |   (M13 monitor)            |
   prag_atentie, prag_critic  --------------->  |  subscriber + clasificare  |
                                               +----------------------------+
                                                 |                    ^
                          clasifica_temperatura( |                    |  serviciu custom (M5+M7)
                          valoare, prag_atentie, |                    |  curs_ros2_interfaces/srv/
                          prag_critic)           |                    |  AjustareTemperatura
                          [NUCLEU PUR, M-uri]    |                    |
                                                 v                    |
                            std_msgs/String      |            /ajusteaza_prag
                            /senzor/alarma  <-----+         (schimba prag_atentie LIVE)
                            "NORMAL/ATENTIE/CRITIC"
```

Pe scurt:
**senzor → `/senzor/temperatura` → monitor → `/senzor/alarma`**, iar serviciul **`/ajusteaza_prag`** schimbă pragul **live**, deci aceeași valoare poate trece dintr-o clasă în alta fără să repornești nimic.

## Lecția de aur a repo-ului
> **Nucleu pur + teste, înainte de orice rulare live.**

Inima sistemului — *cum decidem dacă o temperatură e NORMAL / ATENTIE / CRITIC* — **nu** stă în nod. Stă într-o **funcție pură**, fără ROS și fără efecte secundare, în `curs_ros2/logica.py`:

```python
def clasifica_temperatura(valoare, prag_atentie=30.0, prag_critic=50.0):
    if valoare < prag_atentie:
        return 'NORMAL'
    if valoare < prag_critic:
        return 'ATENTIE'
    return 'CRITIC'
```

Această funcție are **teste automate** în `test/test_logica.py` (inclusiv cazurile de graniță: 29.999, 30.0, 49.999, 50.0 și praguri custom). Monitorul **o importă**, nu o rescrie:

```python
from curs_ros2.logica import clasifica_temperatura
...
status = clasifica_temperatura(msg.data, self.prag_atentie, self.prag_critic)
```

De ce contează? Pentru că un bug în logica de praguri se prinde în **milisecunde** la `pytest`, nu după ce ai pornit launch-ul, ai deschis trei terminale și ai așteptat ca unda să urce. **Testează nucleul rece, apoi pornește sistemul cald.**

## Codul-cheie

### Senzorul — determinist, pe bază de parametri
Valoarea NU e aleatoare: e o sinusoidă reproductibilă, ca toți cursanții să vadă exact aceeași evoluție.

```python
self.declare_parameter('rata', 2.0)            # Hz
self.declare_parameter('valoare_baza', 25.0)   # centrul oscilatiei
self.declare_parameter('amplitudine', 20.0)    # cat urca/coboara

# contor determinist (NU time.time()): unda nu depinde de cand pornesti
t = self.contor * self.pas
valoare = self.valoare_baza + self.amplitudine * math.sin(t)
msg = Float64()
msg.data = valoare
self.pub.publish(msg)
self.contor += 1
```

### Monitorul — clasifică, publică alarma, oferă serviciul
```python
def cb_temperatura(self, msg):
    # decizia vine din nucleul PUR si TESTAT, nu din nod
    status = clasifica_temperatura(msg.data, self.prag_atentie, self.prag_critic)
    alarma = String()
    alarma.data = status
    self.pub_alarma.publish(alarma)
    self.get_logger().info(f'Valoare={msg.data:.2f} -> status={status}')

def cb_ajusteaza(self, request, response):
    prag_vechi = self.prag_atentie
    if request.prag_nou <= 0.0:                 # validare
        response.succes = False
        response.prag_anterior = prag_vechi
        response.mesaj = f'Refuzat: prag_nou={request.prag_nou} trebuie > 0.'
        return response
    self.prag_atentie = request.prag_nou        # schimbare LIVE
    response.succes = True
    response.prag_anterior = prag_vechi
    response.mesaj = f'Prag schimbat de la {prag_vechi} la {self.prag_atentie}.'
    return response
```

### Serviciul custom (`.srv`)
Tipul `curs_ros2_interfaces/srv/AjustareTemperatura`, definit în pachetul de interfețe:

```
# CEREREA — noul prag de atentie
float64 prag_nou
---
# RASPUNSUL
bool    succes
float64 prag_anterior
string  mesaj
```

## Cum rulezi

**T1 — pornește tot sistemul cu un singur launch:**
```bash
ros2 launch curs_ros2 m13_proiect_launch.py
```
Vei vedea senzorul publicând valori și monitorul logând `Valoare=... -> status=...`.

**T2 — urmărește alarma (statusul interpretat):**
```bash
ros2 topic echo /senzor/alarma
```
Pe măsură ce unda urcă peste 30, statusul trece din `NORMAL` în `ATENTIE` (și în `CRITIC` peste 50, dacă amplitudinea e suficientă — în launch e setată la 30, deci unda atinge 55).

**T3 — schimbă pragul LIVE și observă efectul:**
```bash
ros2 service call /ajusteaza_prag curs_ros2_interfaces/srv/AjustareTemperatura "{prag_nou: 35.0}"
```
Imediat după apel, valori care înainte erau `ATENTIE` (între 30 și 35) devin din nou `NORMAL`. Privește `/senzor/alarma` din T2 cum își schimbă clasificarea, **fără să fi repornit nimic**.

Acest proiect combină **M2** (topicuri), **M4** (parametri), **M5** (servicii) și **M7** (interfață custom) într-un singur sistem.

## Verificare
```bash
# Cele doua noduri ruleaza:
ros2 node list
# -> /senzor_temperatura  /monitor_temperatura
```
```bash
# Topicurile exista si au tipurile asteptate:
ros2 topic info /senzor/temperatura   # -> std_msgs/msg/Float64
ros2 topic info /senzor/alarma        # -> std_msgs/msg/String
```
```bash
# Serviciul exista si are tipul custom:
ros2 service type /ajusteaza_prag     # -> curs_ros2_interfaces/srv/AjustareTemperatura
```
```bash
# Vezi pragul curent al monitorului:
ros2 param get /monitor_temperatura prag_atentie
```
```bash
# RULEAZA TESTELE nucleului pur (recomandat INAINTE de rularea live):
python3 -m pytest src/curs_ros2/test/test_logica.py -v
```

## Exerciții
1. **Histereză (anti-pâlpâire).** În jurul pragului, statusul poate "pâlpâi" între `NORMAL` și `ATENTIE` la fiecare oscilație. Adaugă o bandă de histereză în monitor: treci în `ATENTIE` la `prag_atentie`, dar revii în `NORMAL` abia sub `prag_atentie - delta` (ex. `delta = 2.0`). Atenție: ține histereza tot ca **funcție pură** în `logica.py` și scrie-i un test înainte.
2. **Al doilea senzor.** Pornește în launch încă un `senzor_temperatura` cu `name` diferit și `amplitudine` mai mare, publicând pe `/senzor/temperatura_2`. Fă monitorul să asculte ambele topicuri și să publice alarme distincte (`/senzor/alarma_2`).
3. **Jurnal CSV.** Adaugă în monitor scrierea fiecărei perechi `timp, valoare, status` într-un fișier `.csv`. Folosește-l ca exercițiu de a NU bloca callback-ul (deschide fișierul o singură dată, scrie pe rând).

## Capcane frecvente
- **`ModuleNotFoundError: curs_ros2_interfaces`** sau **`curs_ros2.logica`** — ai uitat să faci `source install/setup.bash` după `colcon build` (interfețele și pachetul trebuie construite și "source-uite").
- **Pragul nu se schimbă după `service call`** — apelezi serviciul pe nodul greșit sau cu alt nume. Verifică `ros2 service list`; numele trebuie să fie exact `/ajusteaza_prag`.
- **`prag_nou <= 0` "merge" fără efect** — e intenționat: serverul îl **refuză** (`succes: False`) și păstrează pragul vechi. Citește câmpul `mesaj` din răspuns.
- **Aștepți `CRITIC` și nu apare** — depinde de `amplitudine`. Cu `valoare_baza=25` și `amplitudine=20`, vârful e 45 (< 50), deci nu atingi `CRITIC`. Mărește amplitudinea (în launch e 30).
- **Vrei să rescrii clasificarea în nod** — NU. Asta sparge lecția de aur. Orice logică nouă (ex. histereza) se scrie în `logica.py` și se testează acolo.
- **Senzor "aleator"** — nu folosi `random` pentru valoarea simulată: pierzi reproductibilitatea cursului. Unda sinusoidală deterministă e intenționată.
