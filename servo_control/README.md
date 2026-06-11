# servo_control — Documentatie tehnica

Demonstratorul istoric al tezei: un motor simulat in Gazebo, comandat de la
tastatura (rotatie si viteza), pe ROS 2 Jazzy. In economia articolului A1, acest
pachet ilustreaza STRATUL DE DEMONSTRATIE APLICATIVA — distinct de microbenchmarkul
de transport (`c1_benchmark`), cele doua avand roluri complementare, nu redundante.

## 1. Pozitia in arhitectura

```mermaid
graph LR
    KB[tastatura] --> TN[nodul de teleoperare]
    TN -- comanda viteza/rotatie --> SN[nodul motorului]
    SN -- comanda articulatie --> GZ[Gazebo]
    GZ -- starea articulatiei --> SN
```

Lantul demonstreaza bucla completa operator -> middleware -> simulator si a servit
ca prima validare a mediului ROS 2 Jazzy + Gazebo pe masina de lucru.

## 2. Compilare si descoperirea executabilelor

Pachet ament (apare in iesirea `colcon build`). Numele exacte ale executabilelor si
launch-urilor se obtin din pachetul instalat:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select servo_control --symlink-install
source install/setup.bash

# inventarul executabilelor
ros2 pkg executables servo_control

# inventarul launch-urilor
ls $(ros2 pkg prefix servo_control)/share/servo_control/launch/ 2>/dev/null
```

## 3. Sintaxe de pornire

```bash
# porneste lantul (numele launch-ului din inventarul de mai sus)
ros2 launch servo_control <launch-ul listat>

# verificarea topicurilor active
ros2 topic list
ros2 topic echo --once <topicul de stare al motorului>
```

Comanda de la tastatura: rotatie stanga/dreapta si cresterea/scaderea vitezei,
conform nodului de teleoperare al pachetului.

## 4. Statut

Pachet stabil, in regim de arhiva activa: nu se mai dezvolta, dar ramane
demonstratorul de referinta al buclei de teleoperare si materialul vizual al
prezentarilor. Functionalitatea lui de cercetare a fost preluata si extinsa de
`sar_swarm` (teleoperarea roiului) si `joint_emulator` (controlul de impedanta).
