"""Teste pentru nucleul pur curs_ros2/logica.py.

Ruleaza independent de ROS:  pytest src/curs_ros2/test/test_logica.py
sau, in workspace:           colcon test --packages-select curs_ros2
"""

import math

from curs_ros2.logica import (
    clasifica_temperatura,
    normalizeaza_unghi,
    eroare_distanta,
    unghi_spre_tinta,
)


def test_clasificare_normal():
    assert clasifica_temperatura(20.0) == 'NORMAL'
    assert clasifica_temperatura(29.999) == 'NORMAL'


def test_clasificare_atentie():
    assert clasifica_temperatura(30.0) == 'ATENTIE'
    assert clasifica_temperatura(49.999) == 'ATENTIE'


def test_clasificare_critic():
    assert clasifica_temperatura(50.0) == 'CRITIC'
    assert clasifica_temperatura(120.0) == 'CRITIC'


def test_clasificare_praguri_custom():
    # cu praguri mutate, aceeasi valoare isi schimba clasa
    assert clasifica_temperatura(35.0, prag_atentie=40.0) == 'NORMAL'
    assert clasifica_temperatura(35.0, prag_atentie=30.0) == 'ATENTIE'


def test_normalizeaza_unghi():
    assert math.isclose(normalizeaza_unghi(0.0), 0.0, abs_tol=1e-9)
    # 3*pi se reduce la pi (sau -pi, echivalent)
    assert math.isclose(abs(normalizeaza_unghi(3 * math.pi)), math.pi, abs_tol=1e-9)
    # un unghi mic ramane neschimbat
    assert math.isclose(normalizeaza_unghi(0.5), 0.5, abs_tol=1e-9)
    # rezultatul e mereu in [-pi, pi]
    for u in [-10.0, -3.0, 0.0, 3.0, 10.0, 100.0]:
        assert -math.pi - 1e-9 <= normalizeaza_unghi(u) <= math.pi + 1e-9


def test_eroare_distanta():
    assert math.isclose(eroare_distanta(0.0, 0.0, 3.0, 4.0), 5.0)
    assert math.isclose(eroare_distanta(1.0, 1.0, 1.0, 1.0), 0.0)


def test_unghi_spre_tinta():
    # tinta la dreapta -> 0 rad
    assert math.isclose(unghi_spre_tinta(0.0, 0.0, 1.0, 0.0), 0.0)
    # tinta in sus -> pi/2
    assert math.isclose(unghi_spre_tinta(0.0, 0.0, 0.0, 1.0), math.pi / 2)
