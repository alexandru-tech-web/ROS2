# VERSIUNI (TODO Sec. 3.1) -- amprente de mediu C1

Culese de pe ACEASTA masina (laptop) la 2026-07-07, READ-ONLY (uname/dpkg; niciun nod ROS pornit).
CONFIRMA ca se potrivesc cu masina care a rulat campania: SIL 2026-06-24, HIL 2026-07-01.
Datele de build ale pachetelor rmw (20260412) preced campania -> consistent.

## Laptop (client + router Zenoh) -- cules acum
- Kernel:            6.17.0-35-generic
- Distro:            Ubuntu 24.04.4 LTS
- ROS 2:             Jazzy Jalisco (/opt/ros/jazzy)
- rmw_cyclonedds_cpp: 2.2.3      (ros-jazzy-rmw-cyclonedds-cpp 2.2.3-1noble.20260412.033317)
- CycloneDDS:         0.10.5     (ros-jazzy-cyclonedds 0.10.5-1noble.20260225.142613)
- rmw_zenoh_cpp:      0.2.9      (ros-jazzy-rmw-zenoh-cpp 0.2.9-1noble.20260412.030951)
- zenohd / zenoh-cpp: 0.2.9      (ros-jazzy-zenoh-cpp-vendor 0.2.9-1noble.20260225.231114;
                                  routerul rmw_zenohd e livrat cu acest pachet)

## Raspberry Pi 4 (echo server + router Zenoh) -- DE COMPLETAT de Alexandru
NU am deschis conexiuni catre Pi (regula 2). Ruleaza SNIPPET-ul de mai jos prin SSH si
lipeste iesirea aici:

```
ssh <user>@<pi-host> 'uname -r; . /etc/os-release; echo "$PRETTY_NAME"; \
  dpkg -l 2>/dev/null | grep -iE "rmw-zenoh|rmw-cyclonedds|^ii  ros-jazzy-cyclonedds|zenoh-cpp-vendor" \
    | awk "{print \$2, \$3}"'
```

Pi -- kernel:            [DE COMPLETAT]
Pi -- distro:            [DE COMPLETAT]
Pi -- rmw_cyclonedds_cpp:[DE COMPLETAT]
Pi -- CycloneDDS:        [DE COMPLETAT]
Pi -- rmw_zenoh_cpp:     [DE COMPLETAT]
Pi -- zenoh-cpp-vendor:  [DE COMPLETAT]

## Fraza gata de lipit in Sec. 3.1 (dupa completarea Pi)
"Both environments ran ROS 2 Jazzy on Ubuntu 24.04 (laptop kernel 6.17.0-35; Raspberry Pi 4
kernel [Pi kernel]). The middlewares were rmw_cyclonedds_cpp 2.2.3 over CycloneDDS 0.10.5 and
rmw_zenoh_cpp 0.2.9 (zenoh-cpp-vendor 0.2.9); the Zenoh router is the rmw_zenohd shipped with
rmw_zenoh_cpp 0.2.9."
(Daca versiunile Pi difera de laptop, raporteaza-le separat -- e o testbed HIL, nu o masina.)
