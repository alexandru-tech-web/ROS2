# Modulul 5 — Servicii (cerere/răspuns)

## Ce înveți
- Ce este un **serviciu** ROS 2 și prin ce diferă de topicuri (publisher/subscriber).
- Structura unui fișier `.srv`: partea de **request** și partea de **response**, separate prin `---`.
- Diferența dintre apel **sincron** și **asincron** și de ce preferăm `call_async`.
- De ce combinăm `call_async` + `spin_until_future_complete` și care este capcana clasică (a apela un serviciu sincron din interiorul unui callback).

## Conceptul, pe scurt
Un **topic** e ca un **radio**: cineva transmite (publish) și oricine ascultă primește, dar emițătorul nu știe (și nu așteaptă) cine a auzit. E o comunicare unidirecțională, continuă, fără confirmare.

Un **serviciu** e ca un **apel telefonic**: suni un anume număr (numele serviciului), pui o întrebare (**request**) și **aștepți un răspuns** de la celălalt capăt (**response**). Comunicarea e punctuală și are confirmare: pentru fiecare cerere există fix un răspuns.

Doi actori:
- **Server** = cel care "ridică telefonul" și răspunde. El oferă serviciul.
- **Client** = cel care "sună" și pune întrebarea.

În acest modul folosim tipul standard `example_interfaces/srv/AddTwoInts`: clientul trimite două numere întregi `a` și `b`, iar serverul răspunde cu `sum`.

## Fișierul .srv (request --- response)
Tipul `AddTwoInts` arată conceptual așa:

```
# CEREREA (request) — ce trimite clientul
int64 a
int64 b
---
# RASPUNSUL (response) — ce intoarce serverul
int64 sum
```

Linia `---` desparte **cererea** (deasupra) de **răspunsul** (dedesubt). Din acest fișier, ROS 2 generează automat clasele Python `AddTwoInts.Request()` și `AddTwoInts.Response()`.

## Codul-cheie

### Server
Serverul completează `response` și îl returnează — nu construiește un obiect nou:

```python
from example_interfaces.srv import AddTwoInts

class ServerAdunare(Node):
    def __init__(self):
        super().__init__('server_adunare')
        # "Deschidem ghiseul": numele serviciului trebuie sa coincida cu cel din client.
        self.srv = self.create_service(AddTwoInts, 'aduna', self.cb_aduna)

    def cb_aduna(self, request, response):
        response.sum = request.a + request.b      # completam raspunsul primit
        self.get_logger().info(
            f'Cerere: {request.a} + {request.b} = {response.sum}'
        )
        return response                            # returnarea inchide apelul
```

### Client
Clientul așteaptă serviciul, apoi trimite cererea **asincron**:

```python
self.cli = self.create_client(AddTwoInts, 'aduna')

# Asteptam ca serverul sa existe, ca sa nu "sunam in gol":
while not self.cli.wait_for_service(timeout_sec=1.0):
    self.get_logger().info('Astept serviciul "aduna"...')

request = AddTwoInts.Request()
request.a = 5
request.b = 7
future = self.cli.call_async(request)   # NU blocheaza, intoarce un "future"
```

În `main`, așteptăm răspunsul controlat:

```python
future = node.trimite_cerere(a, b)
rclpy.spin_until_future_complete(node, future)  # invarte nodul pana soseste raspunsul
rezultat = future.result()
node.get_logger().info(f'Rezultat: {rezultat.sum}')
```

## Sincron vs. asincron (și de ce async)
- **Sincron** (`call`): trimiți cererea și firul de execuție **se blochează** până vine răspunsul. Simplu, dar periculos în ROS 2: dacă blochezi firul care ar trebui să proceseze comunicarea, poți ajunge într-un **deadlock** (te blochezi așteptând un răspuns care nu poate sosi pentru că tocmai ai blocat mecanismul care îl aduce).
- **Asincron** (`call_async`): primești imediat un `future` (o promisiune). Nodul rămâne reactiv. Tu decizi când/cum aștepți rezultatul.

De aceea folosim `call_async` împreună cu `spin_until_future_complete(node, future)`: această funcție **învârte** nodul (procesează comunicarea ROS 2) exact până când `future` este gata, apoi se oprește. Obții comportamentul "așteaptă răspunsul" fără riscul de deadlock al apelului sincron.

## Cum rulezi

**T1 — serverul:**
```bash
ros2 run curs_ros2 m5_server
```

**T2 — clientul (5 + 7):**
```bash
ros2 run curs_ros2 m5_client 5 7
```

Dacă rulezi clientul fără argumente, va folosi valorile implicite `2` și `3`:
```bash
ros2 run curs_ros2 m5_client
```

**Alternativ, cu launch** (pornește serverul, apoi clientul după 2s cu argumentele 5 și 7):
```bash
ros2 launch curs_ros2 m5_service_launch.py
```

## Verificare
Cu serverul pornit în T1, deschide alt terminal și rulează:

```bash
# Vezi ca serviciul "aduna" exista:
ros2 service list
```

```bash
# Afla tipul serviciului:
ros2 service type /aduna
# -> example_interfaces/srv/AddTwoInts
```

```bash
# Apeleaza serviciul direct din linia de comanda, fara client propriu:
ros2 service call /aduna example_interfaces/srv/AddTwoInts "{a: 4, b: 6}"
# -> response: example_interfaces.srv.AddTwoInts_Response(sum=10)
```

## Exerciții
1. **Scădere în loc de adunare.** Modifică serverul să întoarcă `request.a - request.b`. Verifică rezultatul cu `ros2 service call` și cu clientul.
2. **Validare în server.** Loghează un avertisment (`self.get_logger().warn(...)`) când suma depășește `100`, dar întoarce totuși răspunsul corect.
3. **Argumente robuste în client.** Fă clientul să accepte și numere negative și să afișeze un mesaj clar dacă argumentele din linia de comandă nu sunt numere întregi valide (`try/except` la `int(...)`).

## Capcane frecvente
- **NU apela un serviciu sincron (`call`) din interiorul unui callback** (de timer, de subscriber sau chiar dintr-un callback de serviciu). Callback-ul rulează în executor; dacă îl blochezi așteptând răspunsul, blochezi chiar mecanismul care ar aduce răspunsul → **deadlock**. Folosește `call_async`.
- **Numele serviciului trebuie să fie identic** la server și la client (`'aduna'`). O mică diferență și clientul va aștepta la nesfârșit în `wait_for_service`.
- **Nu construi un `response` nou în server.** Completează obiectul `response` primit ca parametru și returnează-l; altfel contractul tipului nu este respectat.
- **Tipul serviciului trebuie să coincidă** (`AddTwoInts` peste tot). Server și client cu tipuri diferite nu se conectează.
- **Nu uita `wait_for_service`** în client. Dacă suni înainte ca serverul să existe, cererea poate fi pierdută.
- **Nu citi `future.result()` înainte ca future-ul să fie gata.** Folosește întâi `spin_until_future_complete(node, future)`, abia apoi `future.result()`.
