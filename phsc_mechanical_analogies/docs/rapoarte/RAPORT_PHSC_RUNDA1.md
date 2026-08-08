# RAPORT PHSC -- Runda 1 (integrare + validare)

Data: 2026-08-08. Mediu: Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic (gz-sim8
8.13.0, gz-plugin2 2.0.4), Python 3.12 sistem (numpy 1.26.4, scipy 1.11.4).

Stare finala: **4/4 pachete build OK, 0 stderr, nodurile ruleaza si publica.**
Toate cifrele de mai jos sunt MASURATE pe aceasta masina, nu estimate.

---

## 1. Output `python3 test_mpc.py`

Scriptul din brief folosea `model.linearized_dynamics()`, metoda care **nu
exista**; numele real este `linearized_matrices()`. Corectat, restul identic.

```
Control optim: 3.1556 N
Convergenta: True
Valori proprii LQR: [-7.5913231 +3.43110222j -7.5913231 -3.43110222j
                    -1.33385512+1.02366665j -1.33385512-1.02366665j]
Toate stabile (Re < 0): True
Castig LQR K: [-10.  -11.72401214  -72.15630632  -14.73718429]
Primele 5 comenzi: [3.15561364 3.72194844 2.98241459 1.7646255  0.55064764]
```

Asteptat ~3.0 N, obtinut 3.1556 N, `success=True`, toate valorile proprii cu
parte reala negativa. **Se confirma.** (Inainte de fix-ul de la sec.4.1 dadea
2.7584 N -- diferenta vine din corectarea matricei A.)

## 2. Output `colcon build`

```
Starting >>> phsc_mechanical_analogies
Starting >>> phsc_gazebo_plugins
Finished <<< phsc_mechanical_analogies [2.35s]
Starting >>> phsc_teleop_mpc
Finished <<< phsc_teleop_mpc [2.32s]
Finished <<< phsc_gazebo_plugins [18.0s]
Starting >>> phsc_bringup
Finished <<< phsc_bringup [2.03s]
Summary: 4 packages finished [21.3s]
```

`rosdep install`: `#All required rosdeps installed successfully`.

**Plugin-ul C++ compileaza fara probleme.** Predictia din brief ("librarii
Gazebo lipsa") a fost falsa -- vezi sec.3.

## 3. Topic-uri publicate

`ros2 topic list` cu nodul MPC pornit:

```
/haptic_feedback      geometry_msgs/Wrench   <- MPC
/human_cmd            geometry_msgs/Twist    (intrare, nepublicat de noi)
/robot_cmd            geometry_msgs/Twist    <- MPC
/robot_state          std_msgs/Float64MultiArray  (intrare)
/parameter_events, /rosout
```

Cu `/robot_state = [0, 0, 0.1, 0]`:

```
/robot_cmd        -> linear.x = 2.6199   (nenul, OK)
/haptic_feedback  -> force.x = -0.0315, torque.z = 0.1914   (nenule, OK)
```

Ambele criterii din brief se confirma. `shared_control_mixer` publica
`/mixed_cmd`; plugin-ul publica `/robot_cmd_delayed`.

(Nota de onestitate: cifrele din acest bloc sunt din rularea live facuta INAINTE
de fix-urile numerice de la sec.4.1 -- de aceea `linear.x = 2.6199` si nu 3.1556.
Semnul si ordinul de marime nu se schimba dupa fix.)

---

## 4. Erori gasite si cum au fost rezolvate

### 4.0 BLOCANT: build-ul C++ picat din cauza interpretorului python (mediu)

```
ModuleNotFoundError: No module named 'catkin_pkg'
CMake Error at ament_cmake_core/cmake/core/ament_package_xml.cmake:95
  execute_process(/home/ubuntu/ros2_ws/.venv_ml/bin/python3 ...)
```

Cauza reala: in shell erau active `.venv_ml` si miniconda inaintea lui
`/usr/bin` in PATH; CMake lua primul `python3`, care nu are `catkin_pkg`.
Nu are nicio legatura cu Gazebo. Suplimentar: python-ul din `.venv_ml`
**nu poate importa rclpy** (lipseste `yaml`).

Rezolvat cu `~/ros2_ws/build_phsc.sh`: `env -u VIRTUAL_ENV`, PATH curatat,
`--cmake-args -DPython3_EXECUTABLE=/usr/bin/python3`.

### 4.1 Erori de corectitudine in nucleu (verificate numeric)

| # | Problema | Verificare | Fix |
|---|---|---|---|
| 1 | `linearized_matrices()`: `A[3][3] = -b/(M*L)` -- termen fictiv de amortizare pe pendul | Jacobian numeric (diferente centrate): analitic `-0.2000` vs numeric `0.0000`. Celelalte 15 intrari + tot B: exacte | `A[3][3] = 0`. Diferenta max A acum `5.8e-12` |
| 2 | `predict_state_delay()`: `n_steps = max(1, int(tau/dt))` trunchiaza orizontul | `tau=0.08, dt=0.05` -> 1 pas -> propaga **0.050 s in loc de 0.080 s = sub-compensare 37.5%**. Exact variabila centrala a lucrarii | Pasi intregi + un pas final partial. Eroare fata de RK4 fin: `1e-7` |
| 3 | `solve_times.append(result.nit)` -- salveaza **iteratii**, nu secunde | `[18, 15, 21, 21, 21]` | `solve_times` = secunde reale (`perf_counter`), `solve_iters` separat |
| 4 | `R_du` nu era expus; lua default 0.5 in timp ce `R=0.01` | raport **50x** in favoarea netezimii | expus ca parametru ROS + comentariu de avertizare in YAML |

Dinamica neliniara este **corecta** -- am re-derivat Euler-Lagrange termen cu
termen si se potriveste exact, inclusiv numitorul. La fel RK4 si conventia de
semn a LQR (`u = -K x`). Nu am modificat nimic acolo.

### 4.2 Erori de impachetare (blocau `ros2 run`)

| Problema | Efect | Fix |
|---|---|---|
| **Lipsea `setup.cfg` in toate 3 pachetele Python** | `ros2 pkg executables phsc_teleop_mpc` = **gol**; `ros2 run` nu gasea nimic, ambele launch files ar fi crapat instant | adaugat `[develop] script_dir` + `[install] install_scripts` -> acum 2 executabile |
| Chei rosdep inexistente `gz-sim8`, `gz-plugin2` | `rosdep install` eroare | `gz_sim_vendor`, `gz_plugin_vendor` |
| `<buildtool_depend>ament_python</buildtool_depend>` in phsc_bringup | `Cannot locate rosdep definition` | inlocuit cu `exec_depend` corecte |
| numpy/scipy nedeclarate | rosdep nu le-ar instala pe o masina curata | `<exec_depend>python3-numpy/scipy` |
| Plugin instalat in `lib/<pkg>` fara environment hook | **Gazebo nu l-ar gasi niciodata** | `hooks/*.dsv.in` cu `GZ_SIM_SYSTEM_PLUGIN_PATH`; verificat: `gz plugin --info` -> `Found 1 plugin: phsc::VariableDelayPlugin`, 3 interfete |
| 5 warning-uri `-Wunused-parameter` | zgomot | `(void)_param;` |

### 4.3 Erori de runtime / configurare

| Problema | Verificare | Fix |
|---|---|---|
| **Launch numea nodul `mpc_controller`, YAML-ul avea cheia `mpc_controller_node`** -> TOT `mpc_tuning.yaml` era ignorat silentios | nu s-a observat pentru ca valorile din YAML erau identice cu default-urile din cod | nume aliniat. Verificat cu un YAML de proba cu valori distincte: `N=7, dt=0.1, u_max=33.0, tau_est=0.15, R=0.02, R_du=0.25` -> toate aplicate |
| `tau_var`, `max_iter`, `ftol` in YAML dar **nedeclarate** in nod -> rclpy le arunca silentios | idem | declarate si folosite efectiv in solver |
| NaN pe `/robot_state` -> fallback-ul LQR `u = -(K@x)` publica **forta NaN** | MPC-ul intoarce `0.0/False`, dar fallback-ul propaga NaN | garda de finititate + lungime in `state_callback` |
| **Ctrl-C: `ros2 run` iesea cu cod 1 si traceback** | in Jazzy `spin()` arunca `ExternalShutdownException`, nu `KeyboardInterrupt`; iar `rclpy.shutdown()` dublu arunca `RCLError: rcl_shutdown already called`. Masurat: `exit=1` inainte | prins ambele + `rclpy.try_shutdown()`. Masurat acum: **`exit=0`, 0 traceback-uri**, ambele noduri |
| `condition=None` la mixer/rviz -> argumentele `use_rviz`/`use_mixer` inerte, ambele porneau mereu | contrazicea `default_value='false'` | `IfCondition` real |
| rviz pornit cu `-d config/phsc.rviz`, **fisier care nu exista** | confirmat: niciun `.rviz` in pachete | scos `-d`, `use_rviz` default `false` |
| ASCII (CLAUDE.md sec.3) | 171 caractere non-ASCII in cod | transliterate; acum `grep -nP '[^\x00-\x7F]'` = curat pe toate 4 pachetele |

---

## 5. LIMITARI DE FOND -- pentru urmatoarea runda (nu le-am "reparat" tacit)

Acestea sunt probleme de proiectare, nu bug-uri. Le las neatinse ca sa decizi tu
directia, dar **niciuna nu poate intra intr-un articol in forma actuala.**

### 5.1 CRITIC: MPC-ul nu ruleaza la 20 Hz, ruleaza la ~2 Hz

Masurat, cu parametrii din `mpc_tuning.yaml` (N=20, dt=0.05):

- un `solve` SLSQP: **mediana 486 ms**, max 549 ms
- perioada timer-ului: 50 ms -> **depasire de ~10x**
- rata efectiva masurata pe `/robot_cmd` cu `ros2 topic hz`: **1.99 Hz**

Cauza: SLSQP cu 20 variabile de decizie si **gradient prin diferente finite** --
fiecare evaluare de cost integreaza 20 pasi RK4 de dinamica neliniara, deci ~21
evaluari per iteratie de gradient.

De ce conteaza: polul instabil al cart-pole-ului este la ~4.65 rad/s (constanta
de timp ~215 ms). La 500 ms per ciclu, controllerul primeste mai putin de un
esantion per constanta de timp a instabilitatii pe care trebuie sa o stabilizeze.
**Orice cifra de "MPC neliniar la 20 Hz" este nesustenabila.**

Am adaugat o garda care face depasirea vizibila in log:
```
[WARN] DEPASIRE timp real: ciclul MPC a durat 103 ms > perioada 100 ms
       (rata efectiva ~9.7 Hz; 1/41 cicluri depasite)
```

Optiuni, in ordinea raportului efect/efort:
1. **CasADi + IPOPT sau acados** cu gradiente analitice / AD si compilare C.
   Este solutia standard si singura care duce la 20 Hz+ cu N=20.
2. Furnizeaza `jac` analitic lui SLSQP si scade N (masurat: N=7 -> 103 ms,
   adica ~10 Hz e la limita).
3. MPC liniar (LQR/LQ-MPC) pe modelul linearizat, cu neliniaritatea doar in
   predictia de delay -- se rezolva in microsecunde. Cea mai buna alegere daca
   scopul e sa demonstrezi *compensarea latentei*, nu MPC-ul neliniar in sine.

### 5.2 Plugin-ul Gazebo masoara timp de PERETE, nu timp SIMULAT

`PreUpdate` primeste `_info` dar il ignora complet (verificat: `(void)_info;`) si
foloseste `ros_node_->now()`. Daca simularea nu ruleaza la RTF=1.0, intarzierea
injectata in simulare este `delay_nominal * RTF` -- deci **variabila
independenta a experimentului nu e controlata si rezultatele nu sunt
reproductibile pe alta masina**. Trebuie rescris pe `_info.simTime`.

### 5.3 Coada de delay produce head-of-line blocking

`std::queue` FIFO cu `break` la primul mesaj neexpirat: cu delay variabil (sine
sau zgomot gaussian) un mesaj cu deadline mai scurt asteapta dupa unul cu
deadline mai lung. Distributia de delay realizata devine anvelopa
**running-max** a celei cerute, nu cea ceruta. Trebuie
`std::priority_queue` pe timpul de livrare.

### 5.4 Bucle deschise -- lantul de control nu e conectat

- `/mixed_cmd`: publicat de mixer, **nimeni nu subscrie** (verificat prin grep).
  Deci `alpha`, adica autoritatea umana, nu are **niciun** efect pe planta.
  Asta e chiar mecanismul central din "shared control".
- `/robot_cmd_delayed`: publicat de plugin, **nimeni nu subscrie**.
- `_constraints()` este definita si **niciodata apelata** (verificat prin grep),
  deci constrangerea `|theta| <= theta_max` din formularea din docstring **nu
  este impusa nicaieri**. Trebuie trecuta ca `NonlinearConstraint` la SLSQP.
- `D_h` in `compute_haptic_feedback` e calculat si nefolosit: feedback-ul e un
  arc pur, fara amortizare, desi docstring-ul promite `-K_h*e - D_h*de/dt`.

### 5.5 Nu exista simulare Gazebo, doar noduri

`cartpole_sim.launch.py` isi documenteaza pornirea Gazebo + URDF cart-pole +
VariableDelayPlugin. **Nu porneste niciunul.** Nu exista niciun `.urdf`, `.sdf`,
`.xacro`, `.world` sau `.rviz` in cele 4 pachete (verificat cu `find`). Ce
porneste efectiv: nodurile ROS. Am corectat docstring-ul si comentariile ca sa
spuna adevarul; modelul ramane de construit.

Necesar: world SDF + model cart-pole cu `<plugin>` pentru VariableDelayPlugin +
`ros_gz_sim/gz_sim.launch.py` + `ros_gz_bridge` pentru topicuri.

### 5.6 Tipuri de mesaje semantic incorecte

`/robot_cmd` este `geometry_msgs/Twist` cu `linear.x` = **forta in Newtoni**.
Orice consumator ROS standard citeste `Twist.linear.x` ca **viteza in m/s**.
Mixerul apoi aduna `alpha*u_human + (1-alpha)*u_robot`, adica o viteza cu o
forta -- marimea rezultata nu are unitati fizice. Recomandare:
`geometry_msgs/WrenchStamped` pentru forta, `Twist` doar pentru viteze, si
mesaje `Stamped` peste tot (fara timestamp nu se poate masura latenta).

### 5.7 `ur3_teleop.launch.py` nu poate functiona pe UR3 real

Foloseste setul de parametri cart-pole (`u_max` = forta pe carucior), nodul
subscrie la `/robot_state` ca vector plat de 4 elemente, iar un UR3 publica
`sensor_msgs/JointState` cu 6 articulatii. Nu porneste niciun driver. Pentru
UR3 e nevoie de: `ur_robot_driver`, model dinamic 6-DOF (sau MPC pe o singura
articulatie ca proof-of-concept), si un nod de conversie
`JointState -> stare`, conform sec.6 din brief.

---

## 6. Sugestii pentru urmatoarea runda cu Kimi

Prioritizate. Punctele 1-3 sunt conditii necesare ca rezultatele sa fie
publicabile; restul sunt de continut.

1. **Rezolva bariera de timp real** (sec.5.1). Fara asta nu exista rezultat de
   control. Recomandat: CasADi/acados, sau LQ-MPC daca teza e despre latenta.
2. **Trece plugin-ul pe `_info.simTime` + `std::priority_queue`** (5.2, 5.3).
   Fara asta, latenta injectata nu e o variabila controlata.
3. **Inchide buclele** (5.4): cine consuma `/mixed_cmd` si `/robot_cmd_delayed`?
   Fara ele, nu exista nici shared control, nici delay in bucla.
4. **Construieste modelul Gazebo** (5.5): world + URDF/SDF cart-pole + bridge.
   Abia atunci `cartpole_sim.launch.py` isi merita numele.
5. **Mesaje cu timestamp si unitati corecte** (5.6) -- preconditie pentru orice
   masuratoare de latenta.
6. **Impune `theta_max`** ca `NonlinearConstraint`, si implementeaza `D_h`.
7. **Adauga `_selftest()` in nucleul pur**, conform metodologiei din CLAUDE.md
   sec.2 (core pur testabil fara ROS + selftest). Ar fi prins imediat 3 din cele
   4 erori numerice de la sec.4.1. Sugestie de teste: Jacobian analitic vs
   numeric, orizontul de predictie vs RK4 fin, stabilitatea `A - B K`.
8. **Decizie de scop:** PHSC nu apare in harta C1-C4 din CLAUDE.md. Merita
   clarificat daca devine o contributie proprie sau ramane demonstrator, ca sa
   nu deschida un al doilea track de cod in paralel.

## 7. Note de mediu (pentru reproducere)

```bash
cd ~/ros2_ws && ./build_phsc.sh          # build corect, evita venv/conda

# in FIECARE terminal nou:
deactivate 2>/dev/null || true
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

Simularile numerice: `~/phsc_sim/` (separat de `ros2_ws/`, cum cerea brief-ul).
Atentie: `cartpole_model.py` / `mpc_controller.py` de acolo sunt **copii**;
re-copiaza-le dupa fiecare modificare a nucleului.
