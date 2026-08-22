# Comanda de viteza vs constrangerea de limita in gz_ros2_control

Comportament observat si reprodus determinist pe 22 aug 2026. Merita raportat upstream
si e material de teza indiferent.

## Mediu

| componenta | versiune |
|---|---|
| ROS 2 | Jazzy |
| Gazebo Sim | 8.11.0 |
| gz_ros2_control | 1.2.17 |
| RMW | rmw_cyclonedds_cpp |
| controller | joint_trajectory_controller, interfata de comanda `position` |

## Comportamentul

O articulatie `revolute` care se odihneste EXACT pe una din limitele ei `<limit>`,
cu gravitatia impingand-o in acea limita, nu mai poate fi mutata de
`gz_ros2_control` prin interfata de comanda de POZITIE.

Lantul: `gz_ros2_control` traduce comanda de pozitie in `JointVelocityCmd`
(`v = position_proportional_gain * eroare`). Constrangerea de limita a solverului,
activa fiindca articulatia sta pe limita sub sarcina gravitationala, castiga in fata
comenzii de viteza. Rezultatul e o articulatie complet imobila.

Ce face diagnosticul greu: **totul de deasupra pare sanatos**.
`joint_trajectory_controller` isi raporteaza corect propria eroare
(`reference 1.346379`, `feedback -9.1e-14`, `error 1.346379`), interfata de comanda
apare `[claimed]` de un singur controller, iar mesajul de traiectorie e corect pana la
ultimul octet. Nimic nu semnaleaza esecul; articulatia pur si simplu nu se misca.

## Reproducere minima

Un model cu o articulatie revolute a carei limita inferioara coincide cu pozitia in
care gravitatia o aseaza. Comanda o pozitie in interiorul cursei: nu se misca.
Coboara limita inferioara cu 2-3 grade, fara nicio alta schimbare: se misca.

Verificat cu control de revenire (limita inapoi sus -> blocat din nou), ca diferenta
sa nu poata fi variatie intre rulari.

## Discriminatorul care conteaza pentru altii

Daca doar UNELE articulatii ale aceluiasi model sunt afectate, criteriul nu e tipul
sau controllerul, ci **directia in care gravitatia impinge fiecare articulatie fata de
limita pe care se odihneste**. La noi soldul era impins SPRE limita lui, iar genunchiul
DINSPRE a lui, cu aceeasi gravitatie si in aceeasi postura -- de aceea doar soldul
picase, si de aceea am cautat luni de zile in locul gresit.
