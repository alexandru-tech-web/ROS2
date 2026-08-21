#!/usr/bin/env python3
"""mutant_rmw_scoped.launch.py -- FIXTURE. Reconstruieste DELIBERAT bugul de RMW.

Nu se foloseste in productie si nu importa rmw_common: rmw_common contine FIXUL, iar
un mutant care importa fixul nu mai e mutant. Aici mecanica veche e scrisa pe fata.

    scoped:=true   (implicit)  BUGUL: SetEnvironmentVariable intr-un GroupAction
                               scoped. Grupul isi retrage mediul la iesire, deci
                               nodul nascut din RegisterEventHandler porneste pe
                               RMW-ul implicit, nu pe cel cerut.
    scoped:=false              FIXUL: acelasi lucru, grup nescopat.

Doua gardieni identici, in doua POZITII diferite:
    in_grup      -- pornit in timpul vizitarii grupului. Asta era pozitia
                    gardianului din Valul 1, si de aici venea verdictul VERDE.
    din_handler  -- pornit dintr-un RegisterEventHandler, adica exact pe drumul pe
                    care pornesc spawnerele. Asta e pozitia gardianului v2.

Se ruleaza din test/test_rmw_mutant.py, care citeste codurile lor de iesire.
"""
import os

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction, OpaqueFunction,
                            RegisterEventHandler, SetEnvironmentVariable)
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

AICI = os.path.dirname(os.path.abspath(__file__))
GARDIAN = os.path.join(os.path.dirname(AICI), "..", "scripts", "rmw_guard.py")


def _gardian(eticheta):
    return Node(executable="python3", arguments=[os.path.abspath(GARDIAN),
                                                 "--rmw-asteptat", "cyclonedds",
                                                 "--eticheta", eticheta],
                name=eticheta, output="screen")


def _construieste(context, *_a, **_k):
    scoped = LaunchConfiguration("scoped").perform(context).lower() in ("true", "1")
    in_grup = _gardian("in_grup")
    din_handler = _gardian("din_handler")
    return [GroupAction([
        SetEnvironmentVariable("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp"),
        in_grup,
        RegisterEventHandler(OnProcessExit(target_action=in_grup,
                                           on_exit=[din_handler])),
    ], scoped=scoped)]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("scoped", default_value="true"),
        OpaqueFunction(function=_construieste),
    ])
