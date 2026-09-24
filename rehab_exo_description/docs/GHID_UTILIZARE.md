# Ghid de utilizare — simulatorul robotului de reabilitare LLR

Versiune document: 24 septembrie 2026  
Pachet ROS 2: `rehab_exo_description`  
Platforma verificata: Ubuntu, ROS 2 Jazzy, Gazebo Sim 8

## 1. Ce este acest proiect

Proiectul este un twin de cercetare pentru sistemul LLR de reabilitare a
membrelor inferioare. Modelul are doua lanturi cinematice, stang si drept, cu
cate trei axe actionate:

- sold;
- genunchi;
- glezna.

Mai sunt modelate cinci axe lente de reglaj: scaunul, lungimea celor doua coapse
si lungimea celor doua gambe.

Aplicatia permite:

- rularea unor traiectorii pasive demonstrative;
- observarea pozitiei, vitezei si efortului simulat pentru cele sase axe;
- vizualizarea canalelor de senzori descrise in documentatia LLR;
- inregistrarea automata a unei sesiuni;
- exportul figurilor, metricilor si al unui raport PDF.

> **Atentie:** aceasta este o platforma de simulare si cercetare. Nu este un
> dispozitiv medical certificat si nu se conecteaza la un pacient. Masele,
> inertiile si o parte din geometrie nu sunt validate pe aparatul real.

## 2. Ce este simulat si ce este masurat

| Semnal | Provenienta curenta | Interpretare permisa |
|---|---|---|
| pozitie si viteza articulara | Gazebo `/joint_states` | feedback al simularii |
| referinta articulara | controler ROS 2 | comanda software |
| `effort_sim` | fizica Gazebo | efort simulat, nu cuplu fizic |
| cuplu M2210B | model sintetic declarat | verificarea pipeline-ului |
| forta/moment TR69-1500 | model sintetic declarat | verificarea pipeline-ului |
| unghi BWK216 | model sintetic declarat | verificarea pipeline-ului |
| rigla 406 | model sintetic declarat | verificarea pipeline-ului |

Conform documentatiei tehnice, senzorul aflat sub talpa masoara forte si moment
(`Ff`, `FN`, `MC`). Nu este un senzor de viteza liniara. Encoderul liniar al
pedalei descris in PDF apartine aparatului LTE, nu robotului LLR.

## 3. Pregatirea initiala

Pachetul trebuie sa se afle intr-un workspace ROS 2, de exemplu:

```text
~/ros2_ws/
└── src/
    └── rehab_exo_description/
```

Instaleaza dependentele declarate de pachet:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
```

Pentru interfetele grafice este necesar si Tk:

```bash
sudo apt install python3-tk
```

Construieste pachetul:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build \
  --packages-select rehab_exo_description \
  --symlink-install \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
```

In fiecare terminal nou trebuie incarcate ambele medii, in aceasta ordine:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

## 4. Pornirea recomandata

Dintr-un terminal Ubuntu obisnuit:

```bash
ros2 launch rehab_exo_description demo_c4.launch.py gui:=true
```

Aceasta comanda porneste:

- Gazebo si modelul `rehab_exo`;
- controlerele celor sase articulatii si ale reglajelor;
- initializarea encoderelor;
- controlerul exercitiilor;
- simulatorul si monitorul senzorilor;
- supervizorul de siguranta;
- recorderul sesiunii;
- HMI-ul si graficele live.

### Pornire din terminalul integrat VS Code/Snap

Daca Gazebo afiseaza o eroare cu `libpthread`, `core20` sau `symbol lookup
error`, foloseste scriptul cu mediu curat:

```bash
~/ros2_ws/src/rehab_exo_description/scripts/demo_cu_gui.sh
```

### Pornire fara ferestre grafice

```bash
ros2 launch rehab_exo_description demo_c4.launch.py gui:=false
```

Fizica, controlul, monitorizarea si inregistrarea continua sa functioneze. HMI-ul
si graficele nu sunt pornite implicit in acest mod.

## 5. Ce trebuie asteptat la pornire

Nu comanda imediat o traiectorie. Controlerul asteapta automat:

1. pornirea `controller_manager`;
2. initializarea encoderelor;
3. feedback valid pentru toate cele sase axe;
4. confirmarea conventiei cinematice din URDF.

Mesajul

```text
astept feedback pentru toate cele 6 axe si confirmarea conventiei
```

este normal. Traiectoria este trimisa numai dupa indeplinirea barierei. Aceasta
previne construirea unei miscari din valori implicite zero.

In Gazebo, placa de baza trebuie sa fie pe podea. Nu modifica argumentul
`inaltime:=0.0` pentru utilizarea normala.

## 6. Utilizarea HMI-ului

### Fila „Exercitii”

Selecteaza exercitiul, numarul de repetari si factorul temporal, apoi apasa
**Porneste programul pasiv**.

Factorul temporal nu modifica amplitudinea:

- `x1.0` — durata nominala;
- o valoare peste `1.0` — executie mai rapida;
- o valoare sub `1.0` — executie mai lenta;
- domeniul acceptat este `0.1 ... 3.0`.

Exercitiile disponibile sunt:

| Grupa | Exercitii |
|---|---|
| glezna | flexie/extensie bilaterala, alternanta, mentinere |
| genunchi | extensie bilaterala, alternanta, repetari scurte |
| sold | flexie bilaterala, alternanta, mentinere |
| combinat | mers alternant simulat, extensie coordonata, unda articulata |
| serii | serie glezna, genunchi, sold sau combinata |

Unele programe coordoneaza mai multe articulatii. De exemplu,
`knee_extension` modifica si glezna intre aproximativ 0 si 0,20 rad pentru
pozitionarea piciorului. Aceasta nu este propagarea accidentala a comenzii.

Butonul **STOP controlat** cere revenirea la postura de lucru. Nu este E-STOP si
nu inlocuieste STO/E-stop-ul unui sistem fizic.

### Fila „Reglaje pacient”

Permite reglarea lenta a:

- pozitiei scaunului;
- lungimii coapsei stangi si drepte;
- lungimii gambei stangi si drepte.

Dupa alegerea valorilor apasa **Aplica reglajele**. Controlerul limiteaza
comenzile si aplica regula de garda la sol. Valorile sunt in metri.

Aceste reglaje reprezinta mecanismul simulatorului. Nu sunt cote antropometrice
validate pentru o persoana reala.

### Fila „Senzori LLR”

Afiseaza:

- cuplurile de sold si genunchi asociate M2210B;
- unghiurile de glezna asociate BWK216;
- lungimile gambei asociate riglei 406;
- `Ff`, `FN` si `MC` pentru fiecare talpa TR69-1500.

In versiunea curenta aceste valori sunt sintetice. Eticheta de provenienta este
afisata in aceeasi fila.

`N/A` sau `NaN` inseamna canal nemasurat/lipsa informatiei, nu valoare zero.

### Fila „Date si siguranta”

Afiseaza:

- calea exacta a CSV-ului sesiunii;
- starea supervizorului;
- instructiunea pentru generarea raportului.

Pastreaza calea afisata pentru analiza de dupa oprire.

## 7. Interpretarea graficelor live

Fereastra grafica pastreaza ultimele 30 s si arata:

1. pozitia simulata a celor sase axe;
2. referinta controlerului, cu linie punctata;
3. viteza articulara si limitele;
4. efortul actuatorului raportat de Gazebo;
5. eroarea maxima instantanee de urmarire.

Culorile disting soldul, genunchiul si glezna; linia continua este partea stanga,
iar linia intrerupta partea dreapta.

Daca graficul este plat dupa un timp, verifica momentul afisat. Programul poate fi
deja terminat, iar controlerul mentine ultima postura. Porneste un nou exercitiu
din HMI pentru a vedea o noua miscare.

## 8. Inregistrarea unei sesiuni

Recorderul porneste automat si scrie din primul feedback valid pana la oprirea
lansarii. Directorul implicit este:

```text
~/DATE_TWIN/<AAAALLZZ_HHMMSS>_<exercitiu>/
└── sesiune.csv
```

CSV-ul contine:

- timp simulat si timestamp Unix;
- pozitie, viteza, `effort_sim` si referinta pentru sase articulatii;
- patru canale sintetice de cuplu M2210B;
- canalele celor doua platforme TR69-1500;
- doua unghiuri BWK216;
- doua rigle 406;
- commit-ul, conventia cinematica si parametrii programului;
- evenimentele si contoarele de calitate.

Nu modifica manual CSV-ul brut. Copiaza-l daca este necesara prelucrarea intr-un
alt program.

## 9. Oprirea corecta

Oprirea normala a intregii aplicatii se face o singura data cu:

```text
Ctrl+C
```

in terminalul in care ruleaza launch-ul. Asteapta inchiderea tuturor nodurilor.
Recorderul scrie subsolul de calitate si inchide fisierul. Inchiderea numai a
ferestrei Gazebo nu este metoda recomandata pentru terminarea sesiunii.

## 10. Generarea figurilor si a raportului

Incarca mediul ROS 2, apoi foloseste directorul afisat in HMI.

### PNG-uri pe familii de semnale

```bash
ros2 run rehab_exo_description plot_sesiune.py \
  ~/DATE_TWIN/<director_sesiune>
```

Se genereaza figuri pentru:

- pozitii si referinte;
- viteze;
- efortul Gazebo;
- cuplurile sintetice;
- fortele si momentele la talpa;
- unghiurile gleznei si riglele gambei.

### Raport tehnic complet

```bash
ros2 run rehab_exo_description session_report.py \
  ~/DATE_TWIN/<director_sesiune>
```

Rezultatul este scris in directorul sesiunii:

```text
raport_sesiune.pdf
raport_sesiune.md
metrici_sesiune.csv
metrici_sesiune.json
```

CSV-urile se pot deschide direct in Excel sau LibreOffice Calc. Raportul include
ROM, eroarea de urmarire, vitezele, limitele, efortul Gazebo, canalele sintetice
si simetria stanga-dreapta.

Pentru inspectarea schemei fara generare de fisiere:

```bash
ros2 run rehab_exo_description session_report.py \
  ~/DATE_TWIN/<director_sesiune> --inspect
```

## 11. Verificare rapida dupa instalare

```bash
cd ~/ros2_ws
ctest --test-dir build/rehab_exo_description --output-on-failure \
  -R 'test_(senzori|plot_sesiune|raport_sesiune|recorder|postura|podea|traiectorii|descriere)$'
```

Rezultatul asteptat pentru acest set este `100% tests passed`.

## 12. Probleme frecvente

### `package 'rehab_exo_description' not found`

Pachetul nu este construit sau terminalul nu a incarcat workspace-ul:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select rehab_exo_description --symlink-install
source install/setup.bash
```

### `package 'servo_control' not found`

Este pornit un launch istoric. Pentru fluxul actual foloseste:

```bash
ros2 launch rehab_exo_description demo_c4.launch.py gui:=true
```

Acesta nu necesita pachetul `servo_control`.

### Gazebo porneste, dar modelul pare suspendat

Confirma ca se foloseste `demo_c4.launch.py` si `inaltime:=0.0`:

```bash
ros2 launch rehab_exo_description demo_c4.launch.py gui:=true inaltime:=0.0
```

### Gazebo GUI moare din terminalul VS Code

Porneste prin:

```bash
~/ros2_ws/src/rehab_exo_description/scripts/demo_cu_gui.sh
```

### Lipsesc HMI-ul sau graficele

Confirma `gui:=true`, ori cere explicit ferestrele:

```bash
ros2 launch rehab_exo_description demo_c4.launch.py \
  gui:=false hmi:=true grafice:=true
```

### Nu se scrie niciun rand in CSV

Recorderul nu scrie inainte de primul `/joint_states`. Verifica:

```bash
ros2 topic hz /joint_states
ros2 control list_controllers
```

`joint_state_broadcaster`, `leg_trajectory_controller` si
`adjust_position_controller` trebuie sa fie active.

### Graficele sunt plate

Exercitiul poate fi terminat, modelul poate mentine postura sau fereastra de 30 s
poate sa nu mai contina intervalul activ. Porneste un program nou si urmareste
timpul afisat.

### Apar valori `NaN`

Pentru componentele 6D nedefinite de document (`Fy`, `Mx`, `Mz`) este normal.
Pentru `Ff`, `FN`, `MC`, pozitie, viteza sau referinta, `NaN` indica o problema de
canal si trebuie investigat.

## 13. Reguli pentru modificarea proiectului

1. Editeaza numai `urdf/rehab_exo.urdf.xacro`; URDF-ul este generat la build.
2. Nu prezenta `effort_sim` drept cuplu masurat.
3. Nu prezenta senzorii sintetici drept senzori fizici.
4. Nu introduce mase, inertii sau cote fara sursa si provenienta.
5. Nu dezactiva supervizorul pentru o demonstratie normala.
6. Nu modifica datele brute; genereaza rezultate noi din CSV.
7. Dupa modificari ruleaza build-ul si testele relevante.
8. Orice utilizare pe hardware necesita calibrare, evaluare de risc, E-stop/STO
   fizic si validare separata.

## 14. Ordinea documentelor

Pentru predarea proiectului, citeste in aceasta ordine:

1. `docs/GHID_UTILIZARE.md` — operarea de zi cu zi;
2. `docs/MANUAL_TEHNIC_LLR.md` — arhitectura si senzorii;
3. `docs/RAPORT_DATE_SI_GRAFICE.md` — interpretarea rezultatelor;
4. `docs/HARTA_FISIERELOR.md` — unde se afla fiecare componenta;
5. `IPOTEZE.md` si `urdf/MASE_NEVERIFICATE.md` — limitele modelului;
6. `DECIZII.md` — motivatia schimbarilor tehnice.

## 15. Rezumat operational

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select rehab_exo_description --symlink-install
source install/setup.bash
ros2 launch rehab_exo_description demo_c4.launch.py gui:=true

# dupa Ctrl+C:
ros2 run rehab_exo_description session_report.py \
  ~/DATE_TWIN/<director_sesiune>
```

