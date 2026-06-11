# Modul 12 — Turtlesim: de la open-loop la control cu feedback

## Ce înveți

- Ce este `turtlesim`, laboratorul clasic în care înveți să miști un robot fără hardware.
- Cele două topice care contează: `/turtle1/cmd_vel` (comenzi de viteză) și `/turtle1/pose` (poziția reală).
- Diferența practică dintre **open-loop** (comanzi pe baza de timp, fără să te uiți) și **control proporțional cu feedback** (corectezi în timp real față de eroarea reală).
- **Lecția de aur a acestui repo**: logica de control e scrisă ca funcții **pure** și **testate** în `curs_ros2/logica.py`, separată de stratul ROS.

## Turtlesim — laboratorul clasic

`turtlesim` este o simulare minimală care vine cu ROS 2: o fereastră cu o broască pe care o comanzi ca pe un robot diferențial. E "Hello, robot!"-ul roboticii cu ROS: poți exersa publisher/subscriber, parametri și control fără să riști hardware real.

Gândește-l ca pe un **simulator auto de școală**: înveți volanul și frâna în siguranță, înainte să urci în mașina adevărată (Gazebo, apoi robotul fizic).

### Topicele importante

| Topic | Tip mesaj | Direcție | Rol |
|---|---|---|---|
| `/turtle1/cmd_vel` | `geometry_msgs/Twist` | tu **publici** | viteza comandată: `linear.x` (înainte), `angular.z` (rotire) |
| `/turtle1/pose` | `turtlesim/Pose` | tu **asculți** | poziția reală: `x`, `y`, `theta` (orientarea în radiani) |

> Atenție: poziția folosește tipul **propriu** `turtlesim/Pose`, NU `geometry_msgs`. E o capcană clasică (vezi mai jos).

## Open-loop vs. control proporțional cu feedback

### Varianta naivă: open-loop (`m12_turtle_patrat.py`)

"Mergi înainte 2 secunde, apoi rotește-te ~1 secundă, repetă." Nu măsori nimic — doar comanzi viteze pe baza unui cronometru și a unei mașini de stări.

```python
if self.stare == 'inainte':
    twist.linear.x = self.viteza_inainte
    twist.angular.z = 0.0
else:  # 'rotire'
    twist.linear.x = 0.0
    twist.angular.z = self.viteza_rotire
self.pub.publish(twist)
```

Problema: erorile se **acumulează**. Dacă rotirea nu durează fix cât trebuie, fiecare colț e puțin greșit și pătratul iese strâmb. Open-loop e simplu, dar imprecis.

### Varianta corectă: control proporțional (`m12_turtle_control.py`)

Te uiți tot timpul la poziția reală și comanzi viteze **proporționale cu eroarea rămasă**. Cu cât ești mai departe / mai prost orientat, cu atât comanzi mai mult; pe măsură ce te apropii, comenzile scad singure și robotul se oprește lin pe țintă.

```python
dist = eroare_distanta(x, y, self.x_tinta, self.y_tinta)
if dist < 0.1:
    self.pub_cmd.publish(Twist())   # Twist gol = stop
    return

err_unghi = normalizeaza_unghi(
    unghi_spre_tinta(x, y, self.x_tinta, self.y_tinta) - theta
)
twist.angular.z = 4.0 * err_unghi          # rotire proporțională cu eroarea de unghi
if abs(err_unghi) < 0.2:
    twist.linear.x = 1.5 * dist            # mergi înainte DOAR dacă ești aliniat
```

Detaliile didactice:
- **Întâi te aliniezi, apoi înaintezi**: dacă ai merge înainte cu broasca întoarsă greșit, ai pleca în direcția greșită. De aceea `linear.x` e nenul doar când `|err_unghi|` e mic.
- **`normalizeaza_unghi`** aduce diferența de unghi în `[-pi, pi]` ca să te rotești pe drumul **scurt**, nu pe cel lung.
- **Publicăm mereu un stop** când am ajuns, ca broasca să nu rămână cu ultima viteză comandată.

## Lecția de aur: logica pură, separată de ROS

Observă că nodul de control **nu** își calculează singur distanța sau unghiul. Le importă din modulul partajat:

```python
from curs_ros2.logica import eroare_distanta, unghi_spre_tinta, normalizeaza_unghi
```

Aceste funcții nu știu nimic despre ROS: primesc numere, întorc numere. Sunt **testate automat** în `test/test_logica.py`. Avantajul:

- Defectele de "creier" (matematica) se prind în **milisecunde** la `pytest`, fără să pornești turtlesim sau Gazebo.
- Nodul ROS rămâne subțire: doar abonare, publicare și apelarea logicii deja verificate.

Aceasta este regula pe care o repetăm în tot cursul: **logica importantă = funcții pure + teste; ROS = doar stratul de comunicație.**

## Cum rulezi

### Varianta open-loop (pătrat aproximativ)

```bash
# T1 — pornește simularea
ros2 run turtlesim turtlesim_node
```

```bash
# T2 — comandă broasca pe traseu de pătrat (open-loop)
ros2 run curs_ros2 m12_patrat
```

### Varianta control cu feedback (go-to-goal)

```bash
# T1 — pornește simularea
ros2 run turtlesim turtlesim_node
```

```bash
# T2 — du broasca la o țintă (implicit 8.0, 8.0)
ros2 run curs_ros2 m12_control

# sau cu o țintă proprie, prin parametri:
ros2 run curs_ros2 m12_control --ros-args -p x_tinta:=2.0 -p y_tinta:=9.0
```

### Varianta cu launch (totul dintr-o comandă)

Pornește simularea și, după 2 secunde, nodul de control:

```bash
# T1
ros2 launch curs_ros2 m12_turtle_launch.py
```

## Verificare

```bash
# Vezi poziția reală a broastei în timp real (x, y, theta):
ros2 topic echo /turtle1/pose
```

Urmărește în fereastra turtlesim cum broasca **atinge ținta** și se oprește. La open-loop, observă cum pătratul iese aproximativ; la control, observă cum viteza scade lin pe măsură ce se apropie.

```bash
# Util pentru depanare — vezi ce comenzi de viteză pleacă spre broască:
ros2 topic echo /turtle1/cmd_vel
```

## Exerciții

1. **Mai multe ținte în serie.** Modifică `m12_turtle_control.py` să primească o listă de ținte (de ex. un parametru sau o listă hardcodată) și să treacă la următoarea de fiecare dată când `dist < 0.1`. Broasca face astfel un traseu cu mai multe puncte.

2. **Desenează un pătrat cu control închis.** Folosind ideea de la exercițiul 1, dă cele patru colțuri ale unui pătrat ca ținte succesive. Compară rezultatul cu `m12_patrat` (open-loop): pătratul închis trebuie să iasă vizibil mai drept.

3. **Reglarea câștigurilor.** Experimentează cu câștigurile `4.0` (rotire) și `1.5` (înaintare) și cu pragul `0.2`. Vezi când broasca devine instabilă (oscilează) sau prea lentă, și notează compromisul.

## Capcane frecvente

- **Tip de mesaj greșit pentru poziție.** `turtlesim` folosește `turtlesim/Pose` (cu `x, y, theta`), **NU** `geometry_msgs`. Dacă încerci să te abonezi cu alt tip, fie nu primești nimic, fie ai eroare de tip.
- **Saturarea vitezelor.** Cu câștiguri prea mari, `angular.z` sau `linear.x` ies enorme și broasca se mișcă haotic. Într-un sistem real ai **limita (clamp)** vitezele la un maxim. Pentru exercițiu, scade câștigurile sau adaugă o saturare manuală.
- **Pornirea înainte de prima poziție.** La primele tic-uri s-ar putea să nu fi sosit niciun mesaj pe `/turtle1/pose`. De aceea nodul pleacă cu `pose = None` și nu comandă nimic până nu primește primul mesaj (iar la launch întârziem controlul cu 2 secunde).
- **Nu publici stop la sosire.** Dacă oprești bucla fără să trimiți un `Twist` gol, broasca rămâne cu ultima viteză și continuă să alunece. Publică mereu stop când `dist < 0.1`.
