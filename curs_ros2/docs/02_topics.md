# Modul 2 — Topics (publisher / subscriber)

## Ce înveți

- Cum comunică două noduri ROS 2 prin **topics** folosind modelul **publish / subscribe**.
- Ce sunt tipurile de mesaj `std_msgs/Float64` și `std_msgs/String` și cum le folosești.
- Ce înseamnă parametrul `depth=10` al cozii (un QoS de bază) și de ce contează.
- De ce publisher-ul și subscriber-ul sunt **decuplate** (nu se cunosc între ele).
- Cum verifici din terminal că un topic funcționează (`ros2 topic list / echo / hz / info / pub`).

În acest modul **nu** scriem cod nou: folosim cele două noduri care există deja în pachet,
`m1_publisher.py` și `m1_subscriber.py`. Le citim, le rulăm și le inspectăm.

---

## Conceptul: stație radio și ascultători

Imaginează-ți o **stație radio**. Crainicul vorbește la microfon și emite pe o **frecvență** (de exemplu 98.5 FM).
El nu știe câte radiouri sunt pornite, cine ascultă sau dacă ascultă cineva. Pur și simplu **emite**.

Pe de altă parte, **ascultătorii** își potrivesc radioul pe aceeași frecvență și aud ce se transmite.
Pot fi zero ascultători, unul sau o mie — crainicul transmite la fel.

În ROS 2:

- **frecvența** = **topic** (un nume, de exemplu `/temperatura`);
- **crainicul** = **publisher** (publică mesaje pe topic);
- **ascultătorul** = **subscriber** (primește mesaje de pe topic).

> Important: publisher-ul și subscriber-ul **nu se cunosc direct**. Ei se "întâlnesc" doar prin numele topicului
> și prin tipul mesajului. Asta înseamnă **decuplare**: poți porni mai întâi subscriber-ul, apoi publisher-ul
> (sau invers), poți avea mai mulți subscriberi pe același topic, sau mai mulți publisheri — totul funcționează
> fără ca nodurile să fie modificate. Datorită acestei decuplări poți reporni un nod fără să-l reporneșți pe celălalt.

### Ce fac concret nodurile noastre

**Publisher (`publisher_temperatura`)** simulează un senzor de temperatură:

- publică un număr zecimal (`std_msgs/Float64`) pe topicul `/temperatura`;
- pornește de la `20.0` °C și **crește cu `0.5` °C în fiecare secundă** (un `timer` de `1.0` s declanșează publicarea);
- la fiecare pas scrie în log valoarea publicată.

**Subscriber (`subscriber_temperatura`)** se abonează la `/temperatura`, **clasifică** valoarea și **publică o alarmă**:

- citește temperatura primită și o încadrează în trei niveluri:
  - `< 30.0` °C  → `NORMAL`
  - `< 50.0` °C  → `ATENTIE`
  - `>= 50.0` °C → `CRITIC`
- afișează în log temperatura și statusul;
- publică un mesaj text (`std_msgs/String`) pe un **al doilea topic**, `/alarma`, cu un mesaj corespunzător
  nivelului (`VALOARE NORMALA!`, `VALOARE DE ATENTIONARE!` sau `VALOARE CRITICA`).

Observă că **același nod este în același timp subscriber** (pe `/temperatura`) **și publisher** (pe `/alarma`).
Asta e foarte des întâlnit: un nod consumă date, le procesează și produce alte date.

---

## Tipurile de mesaj

Un topic transportă întotdeauna **un singur tip de mesaj**. Aici folosim mesaje gata făcute din pachetul `std_msgs`:

- `std_msgs/Float64` — un câmp `data` de tip număr zecimal pe 64 de biți. Perfect pentru o temperatură: `23.5`.
- `std_msgs/String` — un câmp `data` de tip text. Perfect pentru un mesaj de alarmă: `"VALOARE CRITICA"`.

În cod, mesajul se construiește ca un obiect și i se setează câmpul `data`:

```python
from std_msgs.msg import Float64

msg = Float64()
msg.data = 23.5        # tipul trebuie sa fie float, nu int
self.pub.publish(msg)
```

```python
from std_msgs.msg import String

alarma = String()
alarma.data = 'VALOARE CRITICA'   # tipul trebuie sa fie text
self.pub_alarma.publish(alarma)
```

> Reține: nu publici direct numărul `23.5`, ci un **obiect mesaj** (`Float64`) cu câmpul `data` setat.
> Publisher-ul și subscriber-ul **trebuie să folosească exact același tip** pe același topic, altfel nu comunică.

---

## Codul-cheie comentat

### Publisher — crearea publisher-ului și a timer-ului

```python
self.pub = self.create_publisher(Float64, '/temperatura', 10)
#                                 ^tip      ^nume topic   ^depth (coada QoS)
self.valoare = 20.0
self.timer = self.create_timer(1.0, self.callback)
#                              ^la fiecare 1.0 s apeleaza self.callback
```

```python
def callback(self):
    msg = Float64()
    msg.data = self.valoare      # punem temperatura in campul data
    self.pub.publish(msg)        # emitem pe /temperatura
    self.valoare += 0.5          # creste cu 0.5 grade pe secunda
```

De ce un **timer** și nu un `while True`? Pentru că în ROS 2 bucla principală o ține `rclpy.spin(node)`.
Timer-ul îi spune lui ROS "cheamă-mă periodic", iar `spin` se ocupă de planificare. Astfel un singur nod poate
avea, în paralel, și un timer, și callback-uri de subscriber — fără ca tu să scrii o buclă manuală care le blochează.

### Subscriber — abonarea și procesarea

```python
self.sub = self.create_subscription(
    Float64,          # tipul mesajului (trebuie sa coincida cu al publisher-ului)
    '/temperatura',   # numele topicului (acelasi ca la publisher)
    self.callback,    # functia apelata automat la fiecare mesaj primit
    10                # depth: cate mesaje tine ROS in coada daca nu apucam sa le procesam
)
self.pub_alarma = self.create_publisher(String, '/alarma', 10)
```

```python
def callback(self, msg):
    temperatura = msg.data          # scoatem numarul din mesajul primit
    if temperatura < 30.0:
        status = 'NORMAL'
    elif temperatura < 50.0:
        status = 'ATENTIE'
    else:
        status = 'CRITIC'

    alarma = String()               # <-- variabila NOUA, nu suprascriem msg
    alarma.data = '...'             # textul depinde de status
    self.pub_alarma.publish(alarma)
```

> Atenție la comentariul din cod: creăm un obiect **nou** `alarma = String()` pentru alarmă.
> Nu refolosim variabila `msg` (care este `Float64` și ne ține valoarea primită). Vezi secțiunea
> "Capcane frecvente" pentru ce se întâmplă dacă suprascrii `msg`.

### Ce înseamnă `depth=10` (QoS de bază)

Al treilea/al patrulea argument (`10`) este **adâncimea cozii** (`depth`), partea cea mai simplă a configurației **QoS**
(Quality of Service). Este o coadă de tip "ține ultimele N mesaje":

- Dacă subscriber-ul nu apucă să proceseze mesajele suficient de repede, ROS păstrează **ultimele 10** și le aruncă pe cele mai vechi.
- La un publisher, `depth` controlează câte mesaje recente sunt ținute pentru livrare.
- Pentru cursul nostru (1 mesaj/secundă) valoarea `10` este mai mult decât suficientă; e o valoare implicită rezonabilă.

> Pentru ca două noduri să comunice, profilurile lor QoS trebuie să fie **compatibile**. Aici ambele folosesc
> profilul implicit cu `depth=10`, deci sunt compatibile automat.

---

## Cum rulezi

Mai întâi, o singură dată, construiește și încarcă mediul (workspace-ul):

```bash
cd ~/ros2_ws
colcon build --packages-select curs_ros2
source install/setup.bash
```

> În **fiecare** terminal nou trebuie să faci `source ~/ros2_ws/install/setup.bash` înainte de `ros2 run`.

**T1 — pornește publisher-ul:**

```bash
ros2 run curs_ros2 publisher
```

Ar trebui să vezi în T1:

```
[INFO] [publisher_temperatura]: Publisher pornit!
[INFO] [publisher_temperatura]: Publicat: 20.0°C
[INFO] [publisher_temperatura]: Publicat: 20.5°C
...
```

**T2 — pornește subscriber-ul:**

```bash
ros2 run curs_ros2 subscriber
```

Ar trebui să vezi în T2:

```
[INFO] [subscriber_temperatura]: Subscriber pornit, ascult /temperatura...
[INFO] [subscriber_temperatura]: Temperatura: 23.0°C  →  NORMAL
[INFO] [subscriber_temperatura]: Temperatura: 30.0°C  →  ATENTIE
...
```

Lasă-l să ruleze. Pe măsură ce temperatura urcă, vei vedea trecerea `NORMAL → ATENTIE → CRITIC`.

---

## Verificare

Deschide un **al treilea terminal (T3)**, fă `source` și folosește uneltele de inspecție din linia de comandă.
Acestea îți arată "din exterior" că totul funcționează, fără să modifici codul.

**Vezi ce topicuri există:**

```bash
ros2 topic list
```

Ar trebui să apară (printre altele) `/temperatura` și `/alarma`.

**Ascultă datele care curg pe un topic:**

```bash
ros2 topic echo /temperatura
```

Vei vedea blocuri `data: 23.0` apărând o dată pe secundă. Pentru alarme:

```bash
ros2 topic echo /alarma
```

**Vezi frecvența de publicare (Hz):**

```bash
ros2 topic hz /temperatura
```

Pentru că publicăm o dată pe secundă, valoarea afișată va fi în jur de `1.0` Hz.

**Vezi detalii despre topic (tip + câți publisheri/subscriberi):**

```bash
ros2 topic info /temperatura
```

Ar trebui să arate `Type: std_msgs/msg/Float64`, `Publisher count: 1` și `Subscription count: 1`
(publisher-ul nostru și subscriber-ul nostru). Verifică și tipul alarmei:

```bash
ros2 topic info /alarma
```

→ `Type: std_msgs/msg/String`.

**Publică manual pe un topic (fără publisher-ul nostru):**

Poți injecta tu o valoare ca să testezi reacția subscriber-ului. Oprește publisher-ul (T1, `Ctrl+C`)
sau lasă-l pornit (vor exista doi publisheri), apoi în T3:

```bash
ros2 topic pub --once /temperatura std_msgs/msg/Float64 "{data: 60.0}"
```

Acel `--once` publică un singur mesaj. În T2 ar trebui să apară imediat:

```
[INFO] [subscriber_temperatura]: Temperatura: 60.0°C  →  CRITIC
```

Poți publica și repetat, la o anumită frecvență (de exemplu 2 Hz):

```bash
ros2 topic pub --rate 2 /temperatura std_msgs/msg/Float64 "{data: 45.0}"
```

> Această comandă demonstrează perfect **decuplarea**: subscriber-ul nostru nici nu știe că mesajul vine
> de la `ros2 topic pub` și nu de la nodul publisher. Îi pasă doar de **numele topicului** și de **tipul mesajului**.

---

## Exerciții

1. **Schimbă pasul de creștere.** În `m1_publisher.py`, modifică `self.valoare += 0.5` în `+= 2.0`.
   Reconstruiește (`colcon build --packages-select curs_ros2`), rulează din nou și observă cât de repede
   ajungi de la `NORMAL` la `CRITIC`. Reglează apoi perioada timer-ului din `create_timer(1.0, ...)` la `0.5`
   și uită-te cum se schimbă valoarea de la `ros2 topic hz /temperatura`.

2. **Adaugă un al doilea subscriber.** Deschide un al patrulea terminal și pornește încă o instanță a
   subscriber-ului (`ros2 run curs_ros2 subscriber`). Vei vedea **ambele** noduri primind aceleași date
   (asta confirmă modelul "o stație, mulți ascultători"). Rulează `ros2 topic info /temperatura` și observă
   cum `Subscription count` a crescut. (Opțional: dă fiecărui subscriber un nume diferit pentru a-i distinge în log.)

3. **Publică și o alarmă cu nivel numeric.** Pe lângă topicul text `/alarma`, adaugă în subscriber un nou
   publisher pe `/alarma_nivel` cu tip `std_msgs/Int32` (`0` = NORMAL, `1` = ATENTIE, `2` = CRITIC) și publică
   nivelul corespunzător statusului. Verifică apoi cu `ros2 topic echo /alarma_nivel` și `ros2 topic info /alarma_nivel`.

---

## Capcane frecvente

- **Nume de topic greșit (cu/fără slash).** `/temperatura` și `temperatura` pot ajunge să fie tratate diferit
  în funcție de namespace. Cea mai sigură regulă: folosește **exact același nume**, cu același slash, la publisher
  și la subscriber. Dacă subscriber-ul "nu primește nimic", verifică întâi cu `ros2 topic list` numele exact al topicului.

- **Tip de mesaj nepotrivit.** Dacă publisher-ul emite `Float64` și subscriber-ul așteaptă `String` (sau invers),
  comunicarea **nu** are loc — chiar dacă numele topicului e identic. `ros2 topic info <topic>` îți arată tipul real;
  trebuie să coincidă peste tot. La fel, când dai `ros2 topic pub`, scrie tipul complet: `std_msgs/msg/Float64`.

- **Pui `int` unde se așteaptă `float`.** `msg.data = 20` poate da eroare de tip pentru `Float64`. Folosește `20.0`.

- **Suprascrierea variabilei `msg`.** În callback-ul subscriber-ului, parametrul `msg` este mesajul **primit**
  (un `Float64`). Dacă scrii din greșeală `msg = String()` ca să construiești alarma, pierzi valoarea primită
  și amesteci tipurile. De aceea în cod alarma e o **variabilă nouă**: `alarma = String()` — vezi comentariul
  `# <-- variabila noua, nu suprascrie msg`.

- **Ai uitat `source install/setup.bash`.** Dacă `ros2 run curs_ros2 publisher` dă "package not found" sau
  entry point inexistent, aproape sigur ai uitat să faci `source` în terminalul respectiv (sau nu ai dat `colcon build`).

- **Te aștepți la date "vechi" la pornire.** Cu QoS implicit, un subscriber pornit **după** publisher nu primește
  mesajele trecute, ci doar pe cele de **acum încolo**. E normal: gândește-te că ai pornit radioul mai târziu și
  ai pierdut începutul emisiunii.
