# Modulul 9 — Executors și callback groups

## Ce înveți
- Ce este un **executor**: motorul care apelează efectiv callback-urile nodului.
- Diferența dintre **SingleThreadedExecutor** (cel folosit implicit de `rclpy.spin`) și **MultiThreadedExecutor**.
- Ce sunt **callback groups** și diferența dintre **MutuallyExclusive** și **Reentrant**.
- Ce înseamnă concret că două callback-uri pot rula **simultan** și când ai nevoie de asta.
- Cum scapi de problema clasică: un callback „greu” care blochează tot nodul.

## Conceptul, pe scurt
Un nod ROS 2 are mai multe callback-uri: callback-uri de timer, de subscriber, de serviciu, de acțiune. Cineva trebuie să le **apeleze** când apare un eveniment (a sosit un mesaj, a expirat un timer). Acel „cineva” este **executorul**.

Analogie: executorul e ca un **chelner** într-un restaurant. Mesele (callback-urile) cer atenție, iar chelnerul se duce la fiecare. Cu **un singur chelner** (single-threaded), dacă o masă îl ține ocupat 3 minute, toate celelalte mese așteaptă — nimeni altcineva nu e servit până nu termină. Cu **mai mulți chelneri** (multi-threaded), o masă lentă ocupă un singur chelner, iar ceilalți continuă să servească restul.

### SingleThreaded vs. MultiThreaded
- **SingleThreadedExecutor** — un singur fir de execuție. Callback-urile se execută **pe rând**, niciodată în paralel. Cât timp un callback lucrează, toate celelalte stau la coadă. **Acesta este executorul folosit în spate de `rclpy.spin(node)`.** Simplu și sigur, dar un callback lent blochează tot nodul.
- **MultiThreadedExecutor** — mai multe fire (`num_threads`). Poate apela callback-uri **în paralel**, pe fire diferite. Un callback lent ocupă un fir, dar celelalte fire pot rula alte callback-uri în același timp.

### Callback groups: cine are voie să ruleze simultan
Doar a avea mai multe fire **nu** e suficient. Executorul mai are nevoie de o „regulă” care să spună ce callback-uri au voie să se suprapună. Această regulă e dată de **callback group**-ul fiecărui callback:

- **MutuallyExclusiveCallbackGroup** — callback-urile din **același** grup **nu** se suprapun niciodată; se execută unul după altul. Folosește-l când codul callback-urilor partajează stare și **nu e thread-safe** (e alegerea implicită, sigură).
- **ReentrantCallbackGroup** — callback-urile din grup se pot **suprapune** liber, inclusiv aceeași funcție cu ea însăși (de exemplu, un timer care pornește următorul tic înainte ca cel curent să se termine). Foarte util pentru muncă grea sau pentru a aștepta răspunsuri în interiorul unui callback, **dar codul trebuie să fie thread-safe**.

Important: dacă pui **două** callback-uri în **același** `MutuallyExclusive` group, nici măcar `MultiThreadedExecutor` nu le va rula în paralel — regula grupului are prioritate. Ca să obții paralelism, callback-urile trebuie să fie în **grupuri diferite** (sau într-un grup `Reentrant`).

## Codul-cheie
Nodul are un timer **rapid** (0.5s, callback scurt) și un timer **lent** (2.0s, al cărui callback face `time.sleep(3.0)` ca să simuleze muncă grea). Le punem în **callback groups separate** și rulăm cu un `MultiThreadedExecutor`.

```python
import time
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup, MutuallyExclusiveCallbackGroup

class NodExecutor(Node):
    def __init__(self):
        super().__init__('nod_executor')
        self.contor = 0

        # Grupuri SEPARATE => executorul multi-threaded le poate rula in paralel.
        self.grup_rapid = MutuallyExclusiveCallbackGroup()   # callback scurt, pe rand cu el insusi
        self.grup_lent = ReentrantCallbackGroup()            # munca grea, are voie sa se suprapuna

        # Timer rapid: ar trebui sa "bata" constant, ~de 2 ori pe secunda.
        self.timer_rapid = self.create_timer(0.5, self.cb_rapid, callback_group=self.grup_rapid)
        # Timer lent: callback-ul blocheaza firul 3s (simuleaza munca grea).
        self.timer_lent = self.create_timer(2.0, self.cb_lent, callback_group=self.grup_lent)

    def cb_rapid(self):
        self.contor += 1
        self.get_logger().info(f'[rapid] tic #{self.contor}')

    def cb_lent(self):
        self.get_logger().info('[lent] incep munca grea (sleep 3s)...')
        time.sleep(3.0)              # blocheaza firul pe care ruleaza
        self.get_logger().info('[lent] am terminat munca grea.')
```

În `main` NU folosim `rclpy.spin` (care e single-threaded), ci construim explicit un executor cu mai multe fire:

```python
def main(args=None):
    rclpy.init(args=args)
    node = NodExecutor()

    # rclpy.spin(node) ar folosi un SingleThreadedExecutor -> munca grea ar bloca timer-ul rapid.
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()             # invarte nodul, dar pe mai multe fire
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()         # opreste firele executorului
        node.destroy_node()
        rclpy.shutdown()
```

### De ce merge
Pe `MultiThreadedExecutor`, când `cb_lent` intră în `sleep(3.0)`, ocupă **un** fir. Fiindcă `cb_rapid` e într-un **alt** callback group, un alt fir liber îl poate executa în continuare. Rezultat: vezi mesajele `[rapid]` apărând regulat **chiar și în timpul** muncii grele. Cu `rclpy.spin` (single-threaded), `[rapid]` ar dispărea pentru cele 3 secunde cât durează sleep-ul.

## Când ai nevoie de asta
- **Timere/operații grele în paralel** — un loop de control rapid care nu trebuie întrerupt de o operație lentă (citire senzor, calcul, I/O pe disc).
- **Apelarea unui serviciu sau a unei acțiuni din interiorul unui callback** — dacă aștepți răspunsul în același fir single-threaded, blochezi chiar mecanismul care ar aduce răspunsul (deadlock). Un `MultiThreadedExecutor` + un `ReentrantCallbackGroup` permit ca răspunsul să fie procesat pe alt fir.
- **Mai mulți subscriberi care primesc mesaje des** și ale căror callback-uri durează, ca să nu se aglomereze coada.

## Cum rulezi

**T1 — pornește nodul demonstrativ:**
```bash
ros2 run curs_ros2 m9_executor
```

Vei vedea ceva de genul (observă că `[rapid]` continuă să „bată” și în timpul muncii grele):
```text
[rapid] tic #1
[rapid] tic #2
[lent] incep munca grea (sleep 3s)...
[rapid] tic #3
[rapid] tic #4
[rapid] tic #5
[rapid] tic #6
[lent] am terminat munca grea.
```

Dacă acest nod ar folosi `rclpy.spin` (single-threaded), între `incep munca grea` și `am terminat munca grea` **nu** ar apărea niciun `[rapid]` — exact asta vrem să evităm.

## Verificare
Cu nodul pornit în T1, deschide alt terminal:

```bash
# Nodul exista si ruleaza:
ros2 node list
# -> /nod_executor
```

```bash
# Vezi cele doua timere si activitatea nodului:
ros2 node info /nod_executor
```

Cea mai bună „verificare” rămâne **vizuală**: urmărește logurile din T1 și confirmă că numărul `[rapid] tic #N` continuă să crească în cele ~3 secunde cât rulează munca grea.

## Exerciții
1. **Întoarcere la blocaj.** Pune **ambele** timere în **același** `MutuallyExclusiveCallbackGroup` (sau scoate complet `callback_group` și lasă-le în grupul implicit). Rulează din nou și observă că `[rapid]` **se oprește** cât timp rulează munca grea — chiar dacă executorul are 4 fire. Concluzie: grupul, nu numărul de fire, decide suprapunerea.
2. **Single-threaded explicit.** Înlocuiește `MultiThreadedExecutor(num_threads=4)` cu `SingleThreadedExecutor()` și compară comportamentul cu `rclpy.spin(node)`. Sunt identice? (Da — `rclpy.spin` folosește exact un `SingleThreadedExecutor`.)
3. **Reentranță reală.** Mărește perioada timer-ului lent la 1.0s (mai mică decât `sleep(3.0)`), păstrează-l în `ReentrantCallbackGroup` și mărește `num_threads`. Vei vedea mai multe `[lent] incep munca grea...` suprapuse, fiindcă tic-urile pornesc în paralel. Adaugă un contor partajat și gândește-te de ce ai avea nevoie de un lock.

## Capcane frecvente
- **Deadlock: `spin` în `spin`.** Nu apela `rclpy.spin` sau `spin_until_future_complete` din interiorul unui callback care rulează deja sub un executor — încerci să pornești executorul în executor. Pentru a aștepta un răspuns în callback, folosește `call_async` + un `MultiThreadedExecutor` cu `ReentrantCallbackGroup`, nu un spin imbricat.
- **Grupuri diferite, nu doar fire.** A pune `num_threads=4` **nu** garantează paralelism. Dacă callback-urile sunt în același `MutuallyExclusive` group, executorul tot le va serializa. Paralelismul cere callback groups **separate** sau un grup `Reentrant`.
- **Reentrant cere cod thread-safe.** Dacă două callback-uri (sau același callback de două ori) rulează în paralel și ating aceeași variabilă, ai nevoie de sincronizare (`threading.Lock`). Altfel apar curse de date și valori corupte. `MutuallyExclusive` te scutește de asta — folosește-l când nu ești sigur.
- **Nu uita `executor.shutdown()`.** Dacă pornești manual un executor, oprește-l explicit (de obicei în `finally`), apoi `node.destroy_node()` și `rclpy.shutdown()`, ca firele să se închidă curat.
- **`time.sleep` blochează firul.** E ok aici pentru demonstrație, dar în cod real evită blocarea lungă a unui fir; preferă timere, `call_async` și callback groups potrivite.
```
