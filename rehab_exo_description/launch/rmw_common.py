"""rmw_common.py -- pinuirea RMW-ului, o singura data, pentru toate launch-urile.

Tiparul vine de la C3 etapa 1c: SetEnvironmentVariable in interiorul unui
GroupAction. Grupul NU mai e insa scoped, si motivul merita scris, fiindca a costat
o zi de diagnostic gresit.

DE CE NESCOPAT (masurat pe 21 aug 2026)
Un GroupAction scoped isi pune si isi SCOATE mediul in timpul vizitarii grupului.
Actiunile pornite mai tarziu de un RegisterEventHandler (on_exit) se executa DUPA ce
scope-ul s-a inchis, deci pe mediul original. In gazebo.launch.py asta insemna ca
gz_sim, robot_state_publisher si puntea de ceas porneau pe rmw_cyclonedds_cpp, dar
joint_state_broadcaster, homing, leg_trajectory_controller si adjust -- toate
declansate prin evenimente -- porneau pe RMW-ul implicit, rmw_fastrtps_cpp.

Semnatura defectului induce puternic in eroare: FastRTPS si CycloneDDS interopereaza
la nivel RTPS pe pub/sub, dar NU pe servicii. Deci topicurile se vedeau, `ros2 node
list` si `ros2 service list` aratau totul, si singurul simptom era ca apelurile de
serviciu nu se intorceau niciodata. De aici concluzia gresita, tinuta luni de zile,
ca "serviciul /controller_manager/list_controllers exista dar nu raspunde" ar fi un
defect de ros2_control. Nu era.

Proba, pe aceeasi simulare pornita, la cateva secunde distanta:
    RMW_IMPLEMENTATION=rmw_fastrtps_cpp   spawner joint_state_broadcaster -> timeout
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp spawner joint_state_broadcaster -> activat

Pretul renuntarii la scope: RMW-ul ramane setat pana la finalul procesului de launch.
Nu se scurge in afara lui (e mediul unui proces copil al shell-ului), iar fiecare
launch C4 pinuieste oricum EXACT o implementare. Cine chiar are nevoie de doua
RMW-uri in acelasi fisier de launch cere explicit scoped=True si NU foloseste event
handlers inauntru.

Trei lucruri se intampla aici, nu unul:
  1. se DECLARA argumentul rmw:= (implicit cyclonedds -- decizia din registrul de
     pe 18 aug: demonstratorul isi alege stiva care nu colapseaza, iar zenoh
     ramane optiune de prima clasa, nu accident de environment);
  2. se APLICA, prin variabila de mediu, in grup NEscopat (vezi mai jos de ce);
  3. se VERIFICA la runtime, cu rmw_guard.py pornit DIN LANT (gardian_in_lant),
     care iese nenul daca implementarea efectiv incarcata difera de cea ceruta
     (cod 3), sau daca un apel de serviciu real nu se intoarce (cod 6).
     Pasul 3 nu e redundant fata de 2, dar NU din motivul scris aici initial:
     afirmatia ca 'rclpy cade linistit pe implicit cand RMW-ul nu e instalat' e
     FALSA pe Jazzy -- acolo eroarea e zgomotoasa si procesul moare cu cod 1.
     Ce e cu adevarat tacut e cazul din 21 aug: mediul care nu ajunge la procesele
     nascute din event handlers. Vezi antetul lui rmw_guard.py.

Tabela de aliasuri si functia de verdict NU se dubleaza aici: se importa din
rmw_guard.py, care e instalat si in launch/ tocmai ca sa existe o singura sursa.
"""
import os
import sys

from launch.actions import (DeclareLaunchArgument, GroupAction, LogInfo,
                            OpaqueFunction, RegisterEventHandler,
                            SetEnvironmentVariable, Shutdown)
from launch.event_handlers import OnProcessExit
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# O SINGURA sursa pentru rmw_guard.py, cautata in cele doua locuri unde poate sta:
# instalat (share/<pkg>/launch/) sau in arborele sursa (../scripts/). NU se copiaza --
# doua copii ale aceleiasi tabele de aliasuri ar fi exact anti-tiparul pe care F1a il
# elimina din descriere.
_AICI = os.path.dirname(os.path.abspath(__file__))
for _c in (_AICI, os.path.join(os.path.dirname(_AICI), "scripts")):
    if os.path.isfile(os.path.join(_c, "rmw_guard.py")):
        sys.path.insert(0, _c)
        break
else:
    raise RuntimeError("rmw_guard.py nu a fost gasit nici in %s, nici in ../scripts" % _AICI)
from rmw_guard import IMPLICIT, normalizeaza          # noqa: E402

PACHET = "rehab_exo_description"


def argument_rmw():
    """Argumentul de launch. Se declara O SINGURA DATA per launch de nivel inalt."""
    return DeclareLaunchArgument(
        "rmw", default_value=IMPLICIT,
        description=("implementarea RMW: cyclonedds (implicit) | zenoh | fastrtps, "
                     "sau un identificator complet rmw_*_cpp"))


def cu_rmw(actiuni, eticheta="rehab", cu_gardian=True, scoped=False):
    """Inveleste `actiuni` intr-un GroupAction cu RMW-ul pinuit.

    `actiuni` poate fi o lista, sau o functie context -> lista (cand actiunile au
    nevoie de valori rezolvate). Intoarce un OpaqueFunction, fiindca aliasul
    ('cyclonedds') trebuie rezolvat la numele complet INAINTE de a ajunge in
    variabila de mediu -- substitutiile nu pot face maparea singure."""
    def _construieste(context, *_a, **_k):
        cerut = LaunchConfiguration("rmw").perform(context)
        plin = normalizeaza(cerut)
        interior = actiuni(context) if callable(actiuni) else list(actiuni)
        continut = [
            SetEnvironmentVariable("RMW_IMPLEMENTATION", plin),
            LogInfo(msg="[%s] RMW pinuit: %s (cerut: '%s')" % (eticheta, plin, cerut)),
        ]
        if cu_gardian:
            continut.append(Node(
                package=PACHET, executable="rmw_guard.py",
                name="rmw_guard_%s" % eticheta,
                arguments=["--rmw-asteptat", plin, "--eticheta",
                           "rmw_guard_%s" % eticheta],
                output="screen"))
        return [GroupAction(continut + interior, scoped=scoped)]
    return OpaqueFunction(function=_construieste)


def gardian_in_lant(eticheta, urmatoare, serviciu=None, asteapta=20.0):
    """Gardianul, pornit PE ACELASI DRUM ca spawnerele, cu poarta pe codul de iesire.

    DE CE NU IN PROCESUL LAUNCH-ULUI, cum era in Valul 1
    Gardianul de atunci se executa in timpul vizitarii grupului si raporta VERDE in
    tot timpul in care jumatate din lant pornea pe alt RMW. Nu era o slabiciune de
    implementare: raspundea corect la 'pe ce RMW rulez EU', iar el chiar rula pe cel
    cerut. Intrebarea era pusa din locul gresit. Aici gardianul se naste dintr-un
    RegisterEventHandler, adica exact drumul pe care se nasteau si spawnerele care
    deviau -- deci mosteneste acelasi mediu ca ele si masoara ce trebuie.
    Fixture-ul test/fixtures/mutant_rmw_scoped.launch.py arata cele doua pozitii una
    langa alta, pe acelasi sistem stricat, cu verdicte opuse.

    `serviciu` adauga proba ACTIVA: un apel real care trebuie sa se intoarca. Nu e
    redundanta fata de verificarea de identificator, fiindca raspunde la alta
    intrebare -- 'ajung la restul lantului' -- si fiindca exact serviciile mor la
    nepotrivire, in timp ce topicurile trec si ar da verde pe un sistem mort.

    `urmatoare` porneste DOAR daca gardianul a iesit cu 0. Altfel lansarea se opreste
    cu motiv: un lant care nu comunica nu merita pornit pe jumatate.
    """
    nume = "rmw_guard_%s" % eticheta
    args = ["--rmw-asteptat", LaunchConfiguration("rmw"), "--eticheta", nume]
    if serviciu:
        args += ["--verifica-serviciu", serviciu, "--asteapta", str(asteapta)]
    nod = Node(package=PACHET, executable="rmw_guard.py", name=nume,
               arguments=args, output="screen")

    def _dupa(event, context):
        cod = event.returncode
        if cod:
            return [LogInfo(msg="[%s] gardianul a iesit cu %d; opresc lansarea. "
                                "Vezi rmw_guard.py pentru intelesul codului "
                                "(3 = nepotrivire RMW, 6 = serviciu mut)."
                                % (nume, cod)),
                    Shutdown(reason="gardian RMW: cod %d" % cod)]
        return list(urmatoare)

    return [nod, RegisterEventHandler(OnProcessExit(target_action=nod,
                                                    on_exit=_dupa))]
