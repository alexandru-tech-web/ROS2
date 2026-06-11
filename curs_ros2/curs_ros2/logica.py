"""Nucleu PUR de logica al cursului — fara ROS, fara efecte secundare.

Aceasta este "regula de aur" a acestui workspace (vezi README-ul repo-ului):
logica importanta se scrie ca functii pure, se TESTEAZA automat
(test/test_logica.py), si abia apoi se imbraca in noduri ROS. Asa, defectele
se prind in milisecunde la pytest, nu dupa ce ai pornit Gazebo.

Modulele M12 (control broasca) si M13 (monitor de temperatura) importa
exact functiile de aici, in loc sa-si rescrie logica inline.
"""

import math


def clasifica_temperatura(valoare, prag_atentie=30.0, prag_critic=50.0):
    """Clasifica o temperatura in NORMAL / ATENTIE / CRITIC.

    sub prag_atentie  -> 'NORMAL'
    sub prag_critic   -> 'ATENTIE'
    altfel            -> 'CRITIC'
    """
    if valoare < prag_atentie:
        return 'NORMAL'
    if valoare < prag_critic:
        return 'ATENTIE'
    return 'CRITIC'


def normalizeaza_unghi(unghi):
    """Aduce un unghi (radiani) in intervalul [-pi, pi].

    Esential in control: diferenta de doua unghiuri poate iesi din interval
    si ar face robotul sa se invarta in sensul lung in loc de cel scurt.
    """
    return math.atan2(math.sin(unghi), math.cos(unghi))


def eroare_distanta(x, y, x_tinta, y_tinta):
    """Distanta euclidiana de la pozitia curenta la tinta."""
    return math.hypot(x_tinta - x, y_tinta - y)


def unghi_spre_tinta(x, y, x_tinta, y_tinta):
    """Unghiul (radiani) catre care trebuie sa priveasca robotul ca sa mearga spre tinta."""
    return math.atan2(y_tinta - y, x_tinta - x)
