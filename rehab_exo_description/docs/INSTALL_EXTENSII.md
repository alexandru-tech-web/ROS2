# Instalare si instrumente optionale

Acest document descrie starea **curenta** a pachetului. Sursa canonica a
robotului este `urdf/rehab_exo.urdf.xacro`; nu se aplica patch-uri peste URDF-ul
generat.

## Instalare

```bash
cd /home/ubuntu/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select rehab_exo_description --symlink-install \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

Pornirea recomandata este descrisa in `START_AICI.md`:

```bash
ros2 launch rehab_exo_description demo_c4.launch.py gui:=true
```

## Componente pornite de demo C4

- Gazebo si `ros2_control` pentru cele sase axe;
- controlerul programelor pasive;
- supervizorul de siguranta electrica simulat;
- simulatorul si monitorul senzorilor LLR;
- recorderul sesiunii;
- HMI si grafice live, daca `gui:=true`.

## Export dupa sesiune

```bash
# PNG-uri pe familii de canale
ros2 run rehab_exo_description plot_sesiune.py \
  /home/ubuntu/DATE_TWIN/<director_sesiune>

# PDF, raport Markdown si metrici CSV/JSON
ros2 run rehab_exo_description session_report.py \
  /home/ubuntu/DATE_TWIN/<director_sesiune>
```

`session_report.py --inspect <cale>` afiseaza metadatele si coloanele fara sa
genereze fisiere. `session_report.py --selftest` verifica parserul, metricile si
exportul pe o sesiune sintetica determinista.

## Module optionale/legacy

Pachetul mai contine `telerehab.launch.py`, `operator_heartbeat.py`,
`patient_model.py`, profiluri `netem` si configuratii pentru puntea Gazebo. Ele
nu fac parte din fluxul C4 validat aici si nu trebuie confundate cu senzorii sau
controlul dispozitivului LLR real. In special:

- profilurile de retea necesita drepturi de administrator si o campanie separata;
- modelul de pacient este o sarcina sintetica, nu model biomecanic validat;
- `rehab_world.sdf` este optional; lumea standard C4 ramane configuratia testata;
- niciun script nu trebuie sa modifice direct URDF-ul generat.

Orice activare a acestor module cere un experiment separat, metadate proprii si
o eticheta de provenienta in rezultate.

## Dependente GUI

HMI-ul si graficele folosesc Tk/Matplotlib. Daca Tk lipseste:

```bash
sudo apt install python3-tk
```

Rularea headless ramane disponibila cu `gui:=false`.
