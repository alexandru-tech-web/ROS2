# Capturile pentru articol — comenzi exacte

Doua capturi obligatorii + una optionala. Rezolutie: fereastra maximizata,
PNG, fara decoratiuni de desktop. Decupezi doar viewport-ul 3D.

## Captura A — roiul in Gazebo (fig:gazebo -> figs/gz_swarm.png)

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws/src/sar_swarm
ros2 launch launch/sar_gazebo.launch.py scenario:=baseline.yaml
# asteapta ~40 s pana dronele sunt dispersate pe harta (acoperire ~30-50%)
```
In fereastra Gazebo: roteste camera la ~45 grade, usor de sus, astfel incat
sa se vada toate cele 4 drone si terenul; ascunde panourile laterale (sageata
din coltul panoului); captura de ecran; decupeaza; salveaza ca
`paper/figs/gz_swarm.png`. Apoi in main.tex: comenteaza \placeholderfig si
decomenteaza \includegraphics{gz_swarm.png}.

## Captura B (optionala) — vederea operatorului RViz (apendice/prezentare)

```bash
# T1: ros2 launch launch/sar_ros.launch.py scenario:=baseline.yaml
# T2 (alt terminal): rviz2
# adauga display TF + (daca exista) markerele dronelor; Fixed Frame: map/world
```
Salveaza ca `figs/rviz_operator.png` — nu e obligatorie pentru cele 8 pagini,
dar e utila pe slide-uri.

## Verificarea figurilor de date (existente deja)

```bash
ls ~/ros2_ws/src/c1_benchmark/paper/figs/
# obligatorii in template: fig_transport.png, fig_cdf.png, fig_mission.png
```

## Compilarea

```bash
cd ~/ros2_ws/src/c1_benchmark/paper
pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```
