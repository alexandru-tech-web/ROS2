# Modulul 1 — Noduri în ROS 2

## Ce înveți

- Ce este un **nod** ROS 2 și de ce împărțim un robot în mai multe noduri.
- Cum scrii un nod în Python (rclpy) ca o **clasă care moștenește `Node`**.
- Rolul constructorului și al apelului `super().__init__('nume_nod')`.
- Cum loghezi mesaje cu `self.get_logger()`.
- Cum creezi un **timer** periodic cu `create_timer(...)`.
- Ce face bucla de evenimente `rclpy.spin(node)` și de ce nodul „rămâne în viață”.
- Rolul perechii `rclpy.init()` / `rclpy.shutdown()`.
- Cum rulezi nodul și cum îl inspectezi din terminal.

---

## Conceptul, pe scurt

Un **nod** este un program care face *o singură treabă bine* în sistemul robotului: citește o cameră, calculează o traiectorie, comandă motoarele, etc. Un robot real este format din zeci de astfel de noduri care comunică între ele.

**Analogie:** gândește-te la o echipă dintr-o bucătărie. Fiecare persoană (nod) are un rol clar — unul taie legume, altul gătește, altul spală vasele. Nimeni nu face tot. Dacă unul lipsește, ceilalți pot continua. La fel, un nod ROS 2 face o singură sarcină, iar dacă unul „cade”, restul sistemului poate funcționa mai departe. ROS 2 este „bucătăria” care îi pune pe toți să comunice.

În rclpy, scriem un nod ca o **clasă care moștenește `rclpy.node.Node`**. Prin moștenire, clasa noastră primește „gratuit” tot mecanismul ROS 2 (logger, timere, publisheri, subscriberi, parametri) și noi adăugăm doar comportamentul specific.

---

## Codul-cheie, comentat

Acesta este nodul din pachet (`curs_ros2/m1_nod_simplu.py`). Îl analizăm linie cu linie.

```python
import rclpy                      # biblioteca client ROS 2 pentru Python
from rclpy.node import Node       # clasa de baza pe care o mostenim

class NodSimplu(Node):
    def __init__(self):
        # super().__init__ inregistreaza nodul in ROS 2 cu numele 'nod_simplu'.
        # Acest nume e cel pe care il vezi in 'ros2 node list' si conteaza pentru
        # ca alte noduri / unelte sa il poata gasi. TREBUIE apelat primul.
        super().__init__('nod_simplu')

        # Logger-ul nodului: scrie mesaje in consola cu nivel, timp si numele nodului.
        # Folosim logger-ul (nu print) pentru ca respecta nivelurile ROS 2.
        self.get_logger().info('Nodul a pornit!')

        # Stare interna a nodului. O tinem ca atribut pentru ca timer-ul,
        # care ruleaza repetat, sa o poata citi si modifica intre apeluri.
        self.contor = 0

        # create_timer(perioada_secunde, functie) cere ROS 2 sa apeleze
        # self.callback la fiecare 1.0 secunde. Pastram referinta in self.timer
        # ca sa nu fie distrusa de garbage collector (altfel timer-ul s-ar opri).
        self.timer = self.create_timer(1.0, self.callback)

    def callback(self):
        # Aceasta functie e apelata de bucla de evenimente, nu de noi direct.
        self.contor += 1
        self.get_logger().info(f'Secunda {self.contor}')

def main():
    rclpy.init()              # initializeaza contextul ROS 2 (o singura data per proces)
    node = NodSimplu()        # construim nodul (ruleaza __init__ de mai sus)
    rclpy.spin(node)          # bucla de evenimente: tine nodul viu si apeleaza callback-urile
    rclpy.shutdown()          # eliberam contextul ROS 2 cand iesim din spin

if __name__ == '__main__':
    main()
```

### Ce se întâmplă, pas cu pas

1. **`rclpy.init()`** — pornește contextul ROS 2 pentru acest proces. Fără el, nu poți crea niciun nod. Se apelează **o singură dată**.
2. **`NodSimplu()`** — rulează `__init__`, care înregistrează nodul (`super().__init__('nod_simplu')`), loghează un mesaj și pornește un timer.
3. **`rclpy.spin(node)`** — predă controlul buclei de evenimente a ROS 2. Aceasta „dă din coadă” în permanență și, când vine momentul (la fiecare secundă), apelează `self.callback`. Apelul **blochează** programul aici: codul de după `spin` nu rulează cât timp nodul este activ.
4. **`Ctrl+C`** întrerupe `spin`, iar execuția ajunge la **`rclpy.shutdown()`**, care închide curat contextul ROS 2.

> Reține: noi **nu** apelăm niciodată `callback()` manual. Bucla de evenimente (`spin`) o apelează pentru noi. Tot ce facem este să *înregistrăm* funcția prin `create_timer`.

---

## Cum rulezi

Ai nevoie ca pachetul să fie compilat și „sursat”. Dacă l-ai modificat sau e prima dată, compilează-l întâi.

**T1 — compilează (doar dacă e necesar) și rulează nodul:**

```bash
# Mergi in radacina workspace-ului
cd ~/ros2_ws

# Sourse mediul ROS 2 Jazzy (distributia)
source /opt/ros/jazzy/setup.bash

# Compileaza pachetul (doar la prima rulare sau dupa modificari in cod)
colcon build --packages-select curs_ros2

# Sourse mediul TAU local (overlay-ul cu pachetul tau)
source install/setup.bash

# Ruleaza nodul prin entry point-ul din setup.py
ros2 run curs_ros2 nod_simplu
```

Ar trebui să vezi în consolă:

```text
[INFO] [....] [nod_simplu]: Nodul a pornit!
[INFO] [....] [nod_simplu]: Secunda 1
[INFO] [....] [nod_simplu]: Secunda 2
...
```

Oprește nodul cu **`Ctrl+C`**.

---

## Verificare

Lasă nodul să ruleze în **T1** și deschide un al doilea terminal **T2**.

**T2 — verifică din exterior că nodul există:**

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# Listeaza toate nodurile active. Trebuie sa apara /nod_simplu
ros2 node list
```

Rezultat așteptat:

```text
/nod_simplu
```

```bash
# Inspecteaza nodul: subscriberi, publisheri, servicii etc.
ros2 node info /nod_simplu
```

Vei vedea topicele implicite (de ex. `/parameter_events`, `/rosout`) și serviciile de parametri pe care orice nod le are automat. Nodul nostru simplu nu publică încă pe topice proprii — asta urmează în lecțiile cu publisher/subscriber.

---

## Exerciții

1. **Schimbă perioada timer-ului.** Modifică `create_timer(1.0, self.callback)` în `create_timer(0.5, self.callback)`. Recompilează (`colcon build --packages-select curs_ros2`), sursează din nou și rulează. Observă că acum loghează de două ori pe secundă. Ce valoare îți dă un mesaj la fiecare 3 secunde?

2. **Adaugă un al doilea timer.** În `__init__`, creează `self.timer2 = self.create_timer(2.0, self.callback2)` și definește o nouă metodă `callback2` care loghează `'Tic la 2 secunde'`. Rulează și observă cum cele două timere se intercalează. De ce e important să-l păstrezi în `self.timer2` și nu doar într-o variabilă locală?

3. **Loghează la nivel warn.** În `callback`, când `self.contor` ajunge multiplu de 5, loghează cu `self.get_logger().warn(...)` în loc de `info(...)`. Observă diferența de culoare/nivel în consolă. Încearcă și `self.get_logger().error(...)`.

---

## Capcane frecvente

- **Ai uitat să faci source la `install/setup.bash`.** Dacă `ros2 run curs_ros2 nod_simplu` dă `Package 'curs_ros2' not found` sau `No executable found`, înseamnă că shell-ul curent nu „vede” overlay-ul. Rulează `source ~/ros2_ws/install/setup.bash` **în fiecare terminal nou**. Și `/opt/ros/jazzy/setup.bash` trebuie sursat înainte.

- **Ai modificat codul dar nu ai recompilat / re-sursat.** Pentru pachete `ament_python`, modificările din `.py` ajung în `install/` doar după `colcon build`. Dacă nu vezi schimbarea, recompilează și sursează din nou. (Sfat: `colcon build --symlink-install` îți permite să eviți recompilarea la fiecare modificare de Python.)

- **Ai uitat să adaugi entry point-ul în `setup.py` și să reconstruiești.** `ros2 run <pachet> <executabil>` găsește nodul prin `console_scripts` din `setup.py`. Dacă numele din `entry_points` nu corespunde, sau dacă ai adăugat un nod nou fără să-l declari acolo și să recompilezi, vei primi `No executable found`. Pentru acest curs entry point-ul există deja: `nod_simplu = curs_ros2.m1_nod_simplu:main`.

- **Ai uitat `rclpy.init()` sau l-ai apelat de două ori.** Fără `init()` nu poți crea niciun nod. Apelat de două ori în același proces dă eroare. Regula: un singur `init()` la început, un singur `shutdown()` la final.

- **Nu păstrezi referința timer-ului.** Dacă scrii `self.create_timer(...)` fără să atribui rezultatul unui atribut `self.`, garbage collector-ul poate distruge timer-ul și callback-ul nu se mai apelează. Ține-l mereu în `self.timer`.

- **Te aștepți ca codul de după `rclpy.spin(node)` să ruleze.** `spin` blochează până la `Ctrl+C`. Tot ce trebuie făcut periodic se face în callback-uri, nu după `spin`.
