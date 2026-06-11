# Modulul 6 — Acțiuni (task lung, cu feedback și anulare)

## Ce înveți
- Ce este o **acțiune** ROS 2 și pentru ce tip de probleme e potrivită (task-uri **lungi**).
- Cele **trei părți** ale unui fișier `.action`: **goal**, **result** și **feedback**, separate prin `---`.
- Prin ce diferă o **acțiune** de un **serviciu** și de un **topic**.
- Cum scrii un **ActionServer** care trimite feedback și tratează **anularea**.
- Cum scrii un **ActionClient** asincron care urmărește feedback-ul și rezultatul.
- De ce serverul de acțiune trebuie rulat cu un **MultiThreadedExecutor**.

## Conceptul, pe scurt
Un **serviciu** e ca un apel telefonic scurt: întrebi, primești imediat răspunsul. Dar ce faci dacă "răspunsul" durează 30 de secunde? Ai vrea să știi cum **progresează** treaba și să poți **renunța** între timp.

Aici intră **acțiunile**. Analogie: comanda la **restaurant**.
- Dai comanda chelnerului — acesta este **goal**-ul ("vreau friptura X").
- Bucătăria îți trimite din când în când vești: "se pregătește", "mai durează 5 minute" — acesta este **feedback**-ul.
- La final primești farfuria — acesta este **result**-ul.
- Și, important, te poți **răzgândi** și anula comanda cât timp se gătește — aceasta este **anularea** (cancel).

O acțiune e deci un task **lung**, **întreruptibil** și care oferă **progres** pe parcurs. Are doi actori: un **ActionServer** (bucătăria, care execută) și un **ActionClient** (clientul, care comandă și urmărește).

În acest modul folosim tipul standard `example_interfaces/action/Fibonacci`: clientul cere primii `order` termeni din secvența Fibonacci, iar serverul îi calculează unul câte unul, trimițând după fiecare pas secvența parțială ca feedback.

## Fișierul .action (goal --- result --- feedback)
Tipul `Fibonacci` arată conceptual așa:

```
# GOAL — ce cere clientul
int32 order
---
# RESULT — ce intoarce serverul la final
int32[] sequence
---
# FEEDBACK — progres trimis pe parcurs
int32[] sequence
```

Sunt **două** linii `---`, care împart fișierul în trei secțiuni: **goal** (sus), **result** (mijloc) și **feedback** (jos). Din el, ROS 2 generează automat clasele `Fibonacci.Goal()`, `Fibonacci.Result()` și `Fibonacci.Feedback()`.

## Diferența față de servicii (și topicuri)
| | Topic | Serviciu | Acțiune |
|---|---|---|---|
| Model | publish/subscribe | request/response | goal/feedback/result |
| Durată | continuu | scurt, instant | **lung** |
| Feedback pe parcurs | nu | nu | **da** |
| Se poate anula | nu | nu | **da** |
| Confirmare la final | nu | da (un răspuns) | da (un rezultat) |

Pe scurt: dacă task-ul durează și vrei să vezi progresul sau să poți renunța, alegi o **acțiune**. Dacă e instantaneu și vrei un singur răspuns, alegi un **serviciu**. Dacă e un flux continuu de date fără confirmare, alegi un **topic**.

## Codul-cheie

### Server
Serverul primește `goal_handle`, calculează pas cu pas, trimite feedback, tratează anularea și marchează succesul:

```python
from rclpy.action import ActionServer
from example_interfaces.action import Fibonacci

class ServerFibonacci(Node):
    def __init__(self):
        super().__init__('server_fibonacci')
        # Numele "fibonacci" trebuie sa coincida cu cel din client.
        self.server = ActionServer(self, Fibonacci, 'fibonacci', self.executa)

    def executa(self, goal_handle):
        order = goal_handle.request.order
        sequence = [0, 1]
        for i in range(2, order):
            # Verificam anularea INAINTE de fiecare pas:
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                return Fibonacci.Result()      # iesim cu rezultat gol
            sequence.append(sequence[i - 1] + sequence[i - 2])
            # Trimitem secventa partiala ca feedback:
            goal_handle.publish_feedback(Fibonacci.Feedback(sequence=sequence))
            time.sleep(0.5)                    # doar ca sa se vada progresul
        goal_handle.succeed()                  # marcam succesul
        return Fibonacci.Result(sequence=sequence[:order])
```

În `main`, serverul rulează pe un **MultiThreadedExecutor** (vezi secțiunea cu capcanele):

```python
from rclpy.executors import MultiThreadedExecutor

executor = MultiThreadedExecutor()
rclpy.spin(node, executor=executor)
```

### Client
Clientul așteaptă serverul, trimite goal-ul **asincron** și înlănțuie callback-urile fără să blocheze:

```python
from rclpy.action import ActionClient
from example_interfaces.action import Fibonacci

class ClientFibonacci(Node):
    def __init__(self):
        super().__init__('client_fibonacci')
        self.client = ActionClient(self, Fibonacci, 'fibonacci')

    def trimite_goal(self, order):
        self.client.wait_for_server()          # asteptam sa existe serverul
        goal = Fibonacci.Goal()
        goal.order = order
        future_goal = self.client.send_goal_async(goal, feedback_callback=self.cb_feedback)
        future_goal.add_done_callback(self.cb_raspuns)   # cand vine acceptarea

    def cb_feedback(self, feedback_msg):
        self.get_logger().info(f'Feedback: {feedback_msg.feedback.sequence}')

    def cb_raspuns(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:           # serverul poate respinge goal-ul
            rclpy.shutdown()
            return
        goal_handle.get_result_async().add_done_callback(self.cb_rezultat)

    def cb_rezultat(self, future):
        rezultat = future.result().result
        self.get_logger().info(f'Rezultat final: {rezultat.sequence}')
        rclpy.shutdown()                       # am primit ce trebuia -> oprim
```

Fluxul în `main` este: trimitem goal-ul, apoi **`rclpy.spin(node)`** procesează evenimentele (feedback, rezultat) pe măsură ce sosesc. Când `cb_rezultat` cheamă `rclpy.shutdown()`, `spin` se încheie și nodul se termină curat. Astfel folosim `spin` ca să **așteptăm** evenimentele asincrone, dar ieșim imediat ce vine rezultatul — fără să blocăm manual la nesfârșit.

## Cum rulezi

**T1 — serverul:**
```bash
ros2 run curs_ros2 m6_action_server
```

**T2 — clientul (order=10):**
```bash
ros2 run curs_ros2 m6_action_client
```

În T2 ar trebui să vezi întâi o serie de mesaje de **feedback** (secvența crescând: `[0, 1, 1]`, `[0, 1, 1, 2]`, ...), iar la final **rezultatul** complet.

## Verificare
Cu serverul pornit în T1, deschide alt terminal și rulează:

```bash
# Vezi ca actiunea "/fibonacci" exista:
ros2 action list
```

```bash
# Detalii: tipul actiunii, cati clienti/servere sunt conectate:
ros2 action info /fibonacci
```

```bash
# Trimite un goal direct din linia de comanda, cu feedback live:
ros2 action send_goal /fibonacci example_interfaces/action/Fibonacci "{order: 8}" --feedback
```

Cu `--feedback`, vei vedea fiecare mesaj de feedback pe măsură ce sosește, apoi rezultatul final.

## Exerciții
1. **Anulează un goal.** Pornește un goal mare (de exemplu `order: 30`) cu `ros2 action send_goal ... --feedback` și apasă `Ctrl+C` în timpul execuției pentru a cere anularea. Observă în T1 mesajul "Goal anulat..." și verifică în cod ramura `is_cancel_requested`.
2. **Alt order.** Modifică în client `node.trimite_goal(10)` în `node.trimite_goal(5)` (sau altă valoare) și rulează din nou. Compară lungimea secvenței finale cu `order`-ul cerut.
3. **Respinge goal-uri invalide.** Adaugă în server o verificare: dacă `order < 1`, loghează un avertisment. (Avansat: folosește un `goal_callback` care întoarce `GoalResponse.REJECT` pentru cereri invalide și verifică în client ramura `if not goal_handle.accepted`.)

## Capcane frecvente
- **Server pe un singur fir = feedback blocat.** Funcția `executa` durează (are `time.sleep` la fiecare pas). Pe executorul implicit (single-thread), cât timp ea rulează, **nimic altceva** nu este procesat — nici trimiterea feedback-ului către client, nici cererea de anulare. De aceea rulăm serverul cu un **`MultiThreadedExecutor`**: task-ul lung ocupă un fir, iar comunicarea (feedback, cancel) curge în paralel pe alt fir.
- **Numele și tipul acțiunii trebuie să coincidă** la server și la client (`'fibonacci'` și `Fibonacci`). O mică diferență și `wait_for_server()` va aștepta la nesfârșit.
- **Tratează anularea și `return` imediat.** După `goal_handle.canceled()` trebuie să ieși din funcție. Dacă uiți `return`, serverul continuă să lucreze pe un goal deja anulat și apoi cheamă `succeed()`, ceea ce e o stare invalidă.
- **Nu uita `succeed()` la final.** Dacă nu marchezi goal-ul (`succeed()` / `canceled()` / `abort()`), clientul rămâne blocat așteptând un rezultat care nu vine.
- **Citește feedback-ul din câmpul corect.** În client, feedback-ul vine ca `feedback_msg.feedback.sequence` (nu direct `feedback_msg.sequence`), iar rezultatul ca `future.result().result.sequence`.
- **Verifică `goal_handle.accepted`.** Serverul poate respinge un goal. Dacă presupui mereu că a fost acceptat și ceri rezultatul, vei avea o eroare.
