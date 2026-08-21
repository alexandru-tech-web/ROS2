# Demonstratia C4 -- ce se porneste, ce se vede, ce inseamna

O singura comanda:

    ros2 launch rehab_exo_description demo_c4.launch.py

Cu optiuni:

    ros2 launch rehab_exo_description demo_c4.launch.py \
        exercitiu:=ankle_pump viteza:=1.5 repetari:=5

| argument | implicit | ce face |
|---|---|---|
| `exercitiu:=` | `knee_extension` | numele din `exercise_core.EXERCISES` |
| `viteza:=` | `1.0` | factor pe axa TIMPULUI (0.1 .. 3.0). NU schimba amplitudinea |
| `repetari:=` | `3` | numarul de repetari |
| `inaltime:=` | `1.2` | inaltimea de aparitie [m]; tine talpile deasupra solului |
| `gui:=` | `false` | porneste si GUI-ul Gazebo (vezi *De ce headless*) |
| `rmw:=` | `cyclonedds` | implementarea RMW, pinuita pe TOATE nodurile |

Oprire: `Ctrl+C`. Lansarea inchide tot lantul, inclusiv serverul Gazebo.

## Ce se vede

Un tablou de text, reimprospatat la 2 Hz:

    t =   44.9 s   sintetic, model declarat, fara pretentie de fidelitate fizica

      articulatie      cerut   masurat    eroare  urmarire      cuplu[Nm]
      left sold        +0.000   +0.000   +0.000                  -0.036
      left genunchi    +1.571   +1.546   -0.025  ###            +54.647
      ...
      URMARIRE  : OK   (max +0.029 rad la right_ankle_joint, prag 0.100)
      COERENTA  : OK   (abatere NEEXPLICATA, dupa scaderea offsetului de montaj: ...)
      CANALE    : OK

- **cerut** = referinta lui `joint_trajectory_controller`; **masurat** = `/joint_states`
  din Gazebo. Diferenta lor e urmarirea REALA, in fizica simulata.
- **URMARIRE** compara cele doua. Pragul de 0.100 rad e unul de DEMONSTRATIE, nu o
  cerinta clinica.
- **COERENTA** verifica senzorul dedicat de unghi de glezna impotriva articulatiei,
  dupa ce scade offsetul de montaj declarat (+-0.012 rad). Ce ramane e abaterea
  neexplicata; la o rulare sanatoasa e de ordinul zgomotului (~0.001 rad).
- **CANALE** verifica in AMBELE sensuri ca doar canalele nemasurate sunt NaN. Un
  canal numit care devine NaN inseamna senzor rupt si trebuie sa se vada.

`NaN` se afiseaza ca `NaN`, niciodata ca `0.000`. Un canal nemasurat afisat ca zero
ar arata ca o masuratoare valida de valoare zero -- e cea mai proasta varianta.

## Ce e real si ce nu

| | statut |
|---|---|
| cinematica, limitele articulare, lantul `ros2_control`, urmarirea de traiectorie | **REAL**, masurat in Gazebo |
| toti senzorii (cuplu, forta 6D, unghi de glezna, rigla de gamba) | **SINTETIC**, model declarat in `senzori_core.py` |
| masele si inertiile | **PLACEHOLDER** -- deci NICIO concluzie dinamica |

Eticheta senzorilor circula pe `/rehab/senzori/eticheta` si apare in fiecare cadru
al tabloului. Nu e scrisa a doua oara in monitor, tocmai ca sa nu poata ajunge sa
spuna altceva decat sursa.

## Cifre masurate pe 21 aug 2026

Exercitiu `knee_extension`, `viteza:=1.0`, castig 15.0, robot la 1.2 m:

- cele trei controlere `active`, `/joint_states` la ~57 Hz
- homing curat, 4 encodere absolute citite
- eroare de urmarire maxima **0.027 rad (1.5 grade)**, genunchiul drept la 0.002 rad
- abatere de coerenta neexplicata **0.001 rad**, adica nivelul zgomotului declarat

## De ce headless

`gz sim gui` moare instant pe masina asta cu

    symbol lookup error: /snap/core20/.../libpthread.so.0: __libc_pthread_init

fiindca terminalul e pornit din snap-ul VSCode, care scurge biblioteci `core20` in
mediul proceselor copil. Cand GUI-ul moare, `gz sim` escaladeaza la SIGKILL pe
SERVER: lumea nu mai paseste, `/clock` tace, si `controller_manager`-ul, care ruleaza
IN bucla de update a Gazebo, nu mai e actualizat niciodata. Fizica ruleaza perfect
fara GUI. Dintr-un terminal care nu vine din snap, `gui:=true` functioneaza.

## Trei lucruri de stiut inainte sa se modifice ceva

1. **Robotul trebuie ridicat de la podea.** La `inaltime:=0` talpile intra in planul
   solului, iar contactul tine genunchiul flectat peste tinta cu 0.153 rad si ~69 Nm
   de cuplu inutil. Eroarea NU raspunde la castig (identica la 15 si la 100) -- de
   aceea arata ca o problema de acordare fara sa fie.
2. **`gazebo:=true` strica controlul de pozitie.** Cele 6 plugin-uri `ApplyJointForce`
   scriu `JointForceCmd` la fiecare pas si suprascriu comanda lui `gz_ros2_control`.
   Se exclud reciproc; implicitul e `false`.
3. **Toate nodurile trebuie sa fie pe acelasi RMW.** FastRTPS si CycloneDDS
   interopereaza pe pub/sub dar NU pe servicii: nepotrivirea arata ca un
   `controller_manager` care exista si nu raspunde. Vezi `test/test_rmw_scope.py`.
