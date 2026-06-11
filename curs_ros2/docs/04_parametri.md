# Modul 4 — Parametri

## Ce înveți

- Ce sunt parametrii ROS 2 și de ce îți permit să **configurezi un nod fără recompilare**.
- Cum declari un parametru cu `declare_parameter` și un `ParameterDescriptor` (cu descriere).
- Cum citești valoarea cu `get_parameter("nume").value`.
- Cum validezi și reacționezi la schimbări printr-un **callback de set** (`add_on_set_parameters_callback`).
- Diferența dintre a da parametri dintr-un **fișier YAML** și **inline** în launch.

## Conceptul, pe scurt

Un parametru este o **setare reglabilă** a unui nod. Gândește-te la el ca la butoanele de pe un cuptor: aparatul (codul) e același, dar cu butoanele (parametrii) îi schimbi temperatura sau timpul fără să demontezi cuptorul. La fel, schimbi `rata` sau `mesaj` fără să atingi codul Python.

Parametrii au câteva proprietăți importante:

- Sunt **tipizați**. `rclpy` în Jazzy este **strict**: dacă ai declarat `rata` ca `float` (`1.0`), nu poți să-i dai un `int` (`2`).
- Trebuie **declarați** înainte de a fi citiți. Un parametru nedeclarat aruncă excepție.
- Pot fi citiți și modificați **la rulare**, prin `ros2 param ...`.

## Codul-cheie comentat

### 1) Declararea (fixează tipul + adaugă descriere)

```python
from rcl_interfaces.msg import ParameterDescriptor

# 1.0 -> tipul devine float; descrierea apare in "ros2 param describe"
self.declare_parameter(
    'rata',
    1.0,
    ParameterDescriptor(description='Frecventa de logare in Hz (trebuie > 0)')
)
self.declare_parameter(
    'mesaj',
    'Salut din parametri',
    ParameterDescriptor(description='Textul afisat la fiecare tic al timer-ului')
)
```

### 2) Citirea valorilor

```python
# .value intoarce valoarea propriu-zisa (float / str), nu obiectul Parameter
self.rata = self.get_parameter('rata').value
self.mesaj = self.get_parameter('mesaj').value
```

### 3) Callback de set: validare + aplicare la cald

```python
from rcl_interfaces.msg import SetParametersResult

# Se inregistreaza dupa ce am citit valorile initiale
self.add_on_set_parameters_callback(self.cb_parametri)

def cb_parametri(self, params):
    # params este o LISTA: pot fi setati mai multi parametri deodata
    for p in params:
        if p.name == 'rata':
            if p.value <= 0.0:
                # Refuzam valoarea; ROS pastreaza valoarea veche
                return SetParametersResult(
                    successful=False,
                    reason='rata trebuie sa fie strict pozitiva (> 0)'
                )
            # Valoare buna: memoram si RECREAM timer-ul ca sa aplicam noua frecventa
            self.rata = p.value
            self.destroy_timer(self.timer)
            self.timer = self.create_timer(1.0 / self.rata, self.cb_timer)
        elif p.name == 'mesaj':
            self.mesaj = p.value
    return SetParametersResult(successful=True)
```

> De ce recreăm timer-ul? Un timer nu își schimbă perioada „din mers”. Ca să accelerăm sau să încetinim logarea, îl distrugem (`destroy_timer`) și creăm altul nou (`create_timer`) cu perioada `1.0 / rata`.

### 4) YAML vs inline

**YAML** (`config/m4_params.yaml`) — recomandat pentru configurări reutilizabile:

```yaml
nod_parametri:
  ros__parameters:
    rata: 2.0
    mesaj: "Salut din fisierul YAML"
```

Structura este: `nume_nod:` apoi `ros__parameters:` și sub el parametrii. Numele nodului din YAML trebuie să fie **identic** cu numele real al nodului (`nod_parametri`).

**Inline** în launch — rapid, bun pentru un override punctual:

```python
parameters=[{'rata': 5.0}]
```

## Cum rulezi

### Varianta A — direct, fără launch (valori implicite din cod)

**T1:**
```bash
ros2 run curs_ros2 m4_param
```
Vei vedea un mesaj pe secundă (rata implicită = 1.0 Hz).

### Varianta B — cu launch + fișier YAML

> Necesită ca pachetul să fie construit și `source`-uit, ca YAML-ul să ajungă în `share`.

**T1:**
```bash
cd ~/ros2_ws
colcon build --packages-select curs_ros2
source install/setup.bash
ros2 launch curs_ros2 m4_param_launch.py
```
Acum vei vedea **două mesaje pe secundă** (rata = 2.0 din YAML) și textul „Salut din fisierul YAML”.

## Verificare

Cu nodul pornit, deschide un al doilea terminal:

**T2 — listează parametrii nodului:**
```bash
ros2 param list /nod_parametri
```
Ar trebui să apară `rata` și `mesaj` (plus parametri standard precum `use_sim_time`).

**T2 — citește o valoare:**
```bash
ros2 param get /nod_parametri rata
```

**T2 — schimbă rata și observă cum accelerează logarea:**
```bash
ros2 param set /nod_parametri rata 4.0
```
În T1 ar trebui să apară `Rata schimbata la 4.0 Hz` și apoi **mai multe mesaje pe secundă**.

**T2 — descrierea unui parametru (vezi textul din `ParameterDescriptor`):**
```bash
ros2 param describe /nod_parametri rata
```

**T2 — salvează toți parametrii într-un YAML:**
```bash
ros2 param dump /nod_parametri
```

**T2 — testează validarea (trebuie să fie respinsă):**
```bash
ros2 param set /nod_parametri rata -1.0
```
Răspunsul trebuie să fie un eșec cu motivul „rata trebuie sa fie strict pozitiva (> 0)”.

## Exerciții

1. **Limită maximă.** Adaugă în `cb_parametri` o validare suplimentară: refuză `rata` mai mare de `100.0` Hz, cu un `reason` clar. Testează cu `ros2 param set /nod_parametri rata 200.0`.
2. **Parametru nou.** Declară un parametru întreg `repetari` (implicit `1`) și fă ca în `cb_timer` mesajul să fie afișat de `repetari` ori. Modifică-l live cu `ros2 param set /nod_parametri repetari 3`.
3. **YAML propriu.** Creează un al doilea fișier YAML cu `rata: 0.5` și pornește nodul cu el (`parameters=[cale_yaml2]` în launch sau `--params-file` la `ros2 run`). Observă logarea mai rară.

## Capcane frecvente

- **Tipuri stricte (2 vs 2.0).** Dacă ai declarat `rata` ca `float`, comanda `ros2 param set /nod_parametri rata 2` poate eșua pentru că `2` este interpretat ca `int`. Folosește `2.0`. La fel în YAML: scrie `rata: 2.0`, nu `rata: 2`.
- **Parametru nedeclarat.** `get_parameter("ceva")` pentru un parametru pe care nu l-ai declarat aruncă excepție. Declară-l întâi cu `declare_parameter`.
- **Numele nodului din YAML.** Cheia de top din YAML (`nod_parametri:`) trebuie să fie **exact** numele nodului. Dacă diferă, parametrii sunt pur și simplu ignorați (fără eroare vizibilă).
- **YAML din `src`, nu din `share`.** În launch folosește `get_package_share_directory(...)`. Dacă n-ai rulat `colcon build` după ce ai adăugat YAML-ul, fișierul nu există în `share` și launch-ul nu-l găsește.
- **Ai uitat să returnezi `SetParametersResult`.** Callback-ul de set **trebuie** să întoarcă un `SetParametersResult`. Dacă returnezi `None` sau `True`, vei primi erori la fiecare `param set`.
- **Modifici parametrul dar nu și comportamentul.** Schimbarea lui `self.rata` nu face nimic singură; trebuie să **recreezi timer-ul** ca să se aplice noua frecvență.
