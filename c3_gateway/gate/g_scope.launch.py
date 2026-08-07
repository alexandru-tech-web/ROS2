"""g_scope.launch.py -- gate C3 (c): SetEnvironmentVariable in GroupAction izoleaza REAL
mediul per proces? Trei procese identice: doua in grupuri cu RMW diferit, unul in afara
oricarui grup (martor pentru mediul mostenit)."""
import os

from launch import LaunchDescription
from launch.actions import ExecuteProcess, GroupAction, SetEnvironmentVariable

S = os.path.dirname(os.path.abspath(__file__))
PY = "/usr/bin/python3"


def proces(eticheta):
    return ExecuteProcess(cmd=[PY, S + "/g_which.py", eticheta], output="screen")


def generate_launch_description():
    return LaunchDescription([
        GroupAction([
            SetEnvironmentVariable("RMW_IMPLEMENTATION", "rmw_cyclonedds_cpp"),
            proces("grup-cdds"),
        ]),
        GroupAction([
            SetEnvironmentVariable("RMW_IMPLEMENTATION", "rmw_zenoh_cpp"),
            proces("grup-zenoh"),
        ]),
        # in AFARA grupurilor: daca scope-ul tine, aici trebuie sa fie mediul mostenit,
        # nu ultima valoare setata intr-un grup
        proces("in-afara"),
    ])
