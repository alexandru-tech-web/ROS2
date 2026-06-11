# Modulul 11 — Lifecycle nodes (noduri gestionate)

## Ce înveți
- Ce este un **lifecycle node** (nod gestionat) și prin ce diferă de un nod obișnuit.
- **Mașina de stări** a unui nod gestionat și **tranzitiile** dintre stări (`configure`, `activate`, `deactivate`, `cleanup`, `shutdown`).
- De ce e utilă pornirea **controlată**: hardware/resurse care trebuie pregătite **înainte** ca nodul să înceapă să lucreze.
- Ce este un **lifecycle publisher** și de ce publică efectiv doar în starea `active`.
- Cum conduci nodul **din linia de comandă** cu `ros2 lifecycle`.

## Conceptul, pe scurt
Un nod obișnuit (`Node`) e ca un aparat **fără întrerupător**: îl bagi în priză și pornește imediat — creează publisher-e, deschide senzori, începe să trimită date din prima secundă. Comod, dar incomod când vrei să controlezi *exact* momentul în care începe să lucreze.

Un **lifecycle node** e ca un aparat cu un **panou de control** clar: are stări bine definite și treci dintr-una în alta doar când apeși un buton. Mai întâi îl **configurezi** (pregătești resursele), abia apoi îl **activezi** (începe să lucreze). Îl poți pune pe **pauză** (deactivate) și reactiva, fără să distrugi nimic. Asta înseamnă **pornire controlată** și predictibilă — esențială în roboți reali, unde un motor sau o cameră trebuie inițializate corect *înainte* să se miște ceva.

### Mașina de stări
Stările principale (cu cele 4 stări "de repaus" în care nodul stă între tranziții):

```
   [unconfigured] --configure--> [inactive] --activate--> [active]
        ^                            |  ^                     |
        |                            |  |                     |
        +----------cleanup-----------+  +-----deactivate------+

   din ORICE stare --shutdown--> [finalized]   (stare terminala)
```

- **unconfigured** — nodul există pe rețea, dar nu a alocat nimic și nu lucrează. (Aici pornește.)
- **inactive** — resursele sunt create (publisher-e, timere), dar nodul **nu livrează** date încă.
- **active** — nodul lucrează efectiv: lifecycle publisher-ele trimit mesaje.
- **finalized** — capăt de drum; nodul urmează să fie distrus.

### Tranzitiile (ce face fiecare)
- **configure** (`unconfigured -> inactive`): pregătești resursele. În codul nostru, aici creăm publisher-ul și timer-ul.
- **activate** (`inactive -> active`): pornești "munca". De aici publisher-ul livrează efectiv mesajele.
- **deactivate** (`active -> inactive`): pui pe pauză, **fără** să distrugi resursele. Publish-ul redevine inofensiv (no-op).
- **cleanup** (`inactive -> unconfigured`): eliberezi resursele create la configure; nodul revine "curat".
- **shutdown** (orice stare `-> finalized`): oprire definitivă; eliberezi tot și nodul nu mai poate fi reactivat.

> De ce contează: într-un robot, `configure` poate deschide portul serial al unui senzor și aloca buffere; `activate` pornește citirea/comenzile; `deactivate` oprește în siguranță motoarele fără să închidă portul. Poți reactiva instant, fără re-inițializare.

## Codul-cheie

### Clasa de bază și callback-urile de tranziție
Moștenim din `LifecycleNode` (nu din `Node`). Fiecare tranziție are un callback `on_<tranzitie>` care întoarce `TransitionCallbackReturn.SUCCESS` dacă a reușit:

```python
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn, LifecycleState
from std_msgs.msg import String

class NodLifecycle(LifecycleNode):
    def __init__(self):
        super().__init__('nod_lifecycle')   # porneste in "unconfigured"

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        # Cream resursele ABIA acum, nu in __init__ -> pornire controlata.
        self._pub = self.create_lifecycle_publisher(String, '/lc_chatter', 10)
        self._timer = self.create_timer(1.0, self._on_timer)
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        return super().on_activate(state)     # super() "porneste" publisher-ele gestionate

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        return super().on_deactivate(state)   # super() le pune la loc pe pauza

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        self.destroy_timer(self._timer)
        self.destroy_lifecycle_publisher(self._pub)
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: LifecycleState) -> TransitionCallbackReturn:
        return TransitionCallbackReturn.SUCCESS
```

### Lifecycle publisher — publică doar în `active`
Timer-ul rulează tot timpul, dar `publish` are efect **doar când nodul e ACTIVE**. În `inactive`, publisher-ul gestionat ignoră în tăcere mesajul (no-op):

```python
    def _on_timer(self):
        msg = String()
        msg.data = 'salut din nodul lifecycle'
        # Are efect DOAR in active. In inactive -> no-op (nimic pe /lc_chatter).
        self._pub.publish(msg)
```

> Cele două lucruri esențiale de reținut:
> 1. Folosește `create_lifecycle_publisher` (nu `create_publisher`) ca publish-ul să respecte starea nodului.
> 2. În `on_activate`/`on_deactivate` apelează `super().on_activate(state)` / `super().on_deactivate(state)` — ele sunt cele care pornesc/opresc efectiv publisher-ele gestionate.

## Cum rulezi

**T1 — pornește nodul (va sta în `unconfigured`):**
```bash
ros2 run curs_ros2 m11_lifecycle
```

**T2 — vezi tranzitiile disponibile și starea curentă:**
```bash
ros2 lifecycle list /nod_lifecycle
ros2 lifecycle get /nod_lifecycle
# -> unconfigured [1]
```

**T2 — configurează nodul (creează publisher + timer; trece în `inactive`):**
```bash
ros2 lifecycle set /nod_lifecycle configure
ros2 lifecycle get /nod_lifecycle
# -> inactive [2]
```

**T2 — activează nodul (acum chiar publică pe `/lc_chatter`):**
```bash
ros2 lifecycle set /nod_lifecycle activate
ros2 lifecycle get /nod_lifecycle
# -> active [3]
```

**T3 — ascultă mesajele (apar abia după `activate`):**
```bash
ros2 topic echo /lc_chatter
# -> data: salut din nodul lifecycle   (o data pe secunda)
```

**T2 — pune pe pauză și reia, după preferință:**
```bash
ros2 lifecycle set /nod_lifecycle deactivate   # mesajele se opresc (inactive)
ros2 lifecycle set /nod_lifecycle activate     # repornesc
ros2 lifecycle set /nod_lifecycle cleanup      # eliberează resursele (unconfigured)
```

## Verificare
```bash
# Nodul exista si starea lui se citeste corect:
ros2 lifecycle get /nod_lifecycle
```

```bash
# Tranzitiile pe care le poti face DIN starea curenta:
ros2 lifecycle list /nod_lifecycle
```

```bash
# Demonstreaza ca topicul tace in INACTIVE si vorbeste in ACTIVE:
# 1) cu nodul in inactive, lasa acest echo pornit -> NU apare nimic
ros2 topic echo /lc_chatter
# 2) din alt terminal: ros2 lifecycle set /nod_lifecycle activate
#    -> abia acum incep sa curga mesajele in echo
```

```bash
# Vezi ca publisher-ul exista pe topic chiar si in inactive (e creat la configure),
# desi nu livreaza date pana la activate:
ros2 topic info /lc_chatter
```

## Exerciții
1. **Mesaj cu contor și stare.** Adaugă un `self._contor` care crește la fiecare tic și pune în `msg.data` numărul mesajului. Observă în `ros2 topic echo` că numerotarea "sare" peste perioada cât ai stat în `inactive` (timer-ul a rulat, dar publish-ul a fost no-op).
2. **Tranziții care eșuează.** Fă `on_configure` să întoarcă `TransitionCallbackReturn.FAILURE` dacă un parametru (ex. `port`) lipsește. Declară parametrul, pornește nodul fără el și vezi cum `ros2 lifecycle set ... configure` raportează eșecul, iar nodul rămâne în `unconfigured`.
3. **Două frecvențe.** Adaugă în `on_configure` un al doilea timer care publică pe `/lc_status` la 0.2 Hz. Verifică, prin `deactivate`/`activate`, că ambele topicuri respectă regula "doar în active".

## Capcane frecvente
- **Publici în `inactive` și te miri că nu apare nimic pe topic.** Acesta e comportamentul **corect** al unui lifecycle publisher: în `inactive`, `publish` e un no-op. Mesajele apar abia după `activate`. Nu e bug.
- **Ai folosit `create_publisher` în loc de `create_lifecycle_publisher`.** Atunci publisher-ul *nu* respectă starea nodului și va publica și în `inactive` — pierzi exact avantajul pe care îl demonstrăm aici.
- **Ai uitat `super().on_activate(state)` / `super().on_deactivate(state)`.** Fără apelul la `super()`, publisher-ele gestionate nu sunt pornite/oprite, iar starea poate apărea "active" dar fără livrare reală.
- **Aștepți tranziții "din salt".** Mașina de stări nu permite orice trecere: nu poți face `activate` direct din `unconfigured` — trebuie întâi `configure`. Folosește `ros2 lifecycle list /nod_lifecycle` ca să vezi ce tranziții sunt valide din starea curentă.
- **Creezi resursele în `__init__` în loc de `on_configure`.** Atunci pierzi pornirea controlată: scopul nodului gestionat e ca resursele (hardware, buffere) să apară abia la `configure`, nu imediat ce nodul există.
- **Numele nodului în comenzi.** Comenzile `ros2 lifecycle` cer numele complet cu `/` (`/nod_lifecycle`). Dacă nu îl găsești, verifică cu `ros2 node list`.
- **"Node not found" imediat după pornire.** E doar întârzierea de *discovery*: dă-i nodului 3–5 secunde după `ros2 run` înainte de prima comandă `ros2 lifecycle`, apoi reîncearcă. Dacă persistă, repornește daemon-ul cu `ros2 daemon stop` (se repornește singur la următoarea comandă).
- **De ce `MultiThreadedExecutor` în `main`, nu `rclpy.spin` simplu.** Serviciile de lifecycle (`change_state`/`get_state`, oferite automat de framework) răspund mult mai sigur pe mai multe fire; cu executorul single-threaded răspunsul la `ros2 lifecycle get/set` poate expira intermitent (`failed to send response (timeout)`), mai ales pe `rmw_fastrtps`.
