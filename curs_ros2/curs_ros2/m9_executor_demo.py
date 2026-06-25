import time

import rclpy
from rclpy.node import Node
# Executorii sunt "motorul" care apeleaza efectiv callback-urile nodului.
# SingleThreadedExecutor ruleaza totul pe UN SINGUR fir: cat timp un callback
# lucreaza, niciun alt callback nu poate porni (exact ca rclpy.spin, care
# foloseste in spate un SingleThreadedExecutor). MultiThreadedExecutor are
# mai multe fire si poate rula callback-uri IN PARALEL.
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
# Callback groups spun executorului CARE callback-uri au voie sa ruleze simultan:
#  - MutuallyExclusiveCallbackGroup: callback-urile din acelasi grup NU se
#    suprapun niciodata (se executa pe rand). Bun pentru cod care nu e thread-safe.
#  - ReentrantCallbackGroup: callback-urile din grup se pot suprapune (chiar si
#    aceeasi functie cu ea insasi). Bun pentru munca grea care nu trebuie sa
#    blocheze restul, dar cere cod thread-safe.
from rclpy.callback_groups import ReentrantCallbackGroup, MutuallyExclusiveCallbackGroup


class NodExecutor(Node):
    def __init__(self):
        super().__init__('nod_executor')

        # Contor pentru timer-ul rapid, ca sa vedem vizual ca el continua sa
        # "bata" chiar si in timp ce timer-ul lent sta blocat in munca grea.
        self.contor = 0

        # === Doua callback groups SEPARATE ===
        # De ce separate? Daca cele doua timere ar fi in ACELASI grup
        # MutuallyExclusive, executorul (chiar si multi-threaded) ar refuza sa le
        # ruleze simultan, iar callback-ul lent ar bloca din nou timer-ul rapid.
        # Punandu-le in grupuri diferite, executorul cu mai multe fire le poate
        # rula in PARALEL.
        #
        # Timer-ul RAPID e in MutuallyExclusive: callback-ul lui e scurt si nu
        # vrem reentranta (e simplu si mai sigur ca nu se suprapune cu el insusi).
        self.grup_rapid = MutuallyExclusiveCallbackGroup()
        # Timer-ul LENT e in Reentrant: chiar daca un tic dureaza 3s iar perioada
        # e 2s, executorul poate porni urmatorul tic in paralel pe alt fir, fara
        # sa astepte ca cel curent sa se termine.
        self.grup_lent = ReentrantCallbackGroup()

        # === Timer RAPID (0.5s) -- callback SCURT ===
        # Logheaza un contor; ar trebui sa "bata" de ~2 ori pe secunda, constant.
        self.timer_rapid = self.create_timer(
            0.5,
            self.cb_rapid,
            callback_group=self.grup_rapid,
        )

        # === Timer LENT (2.0s) -- callback care simuleaza MUNCA GREA ===
        # time.sleep(3.0) blocheaza firul pe care ruleaza callback-ul timp de 3s.
        # Pe un SingleThreadedExecutor, acest sleep ar bloca INTREG nodul, deci
        # timer-ul rapid ar inceta sa logheze in tot acest interval.
        self.timer_lent = self.create_timer(
            2.0,
            self.cb_lent,
            callback_group=self.grup_lent,
        )

        self.get_logger().info(
            'Nod pornit: timer rapid la 0.5s, timer lent (munca grea 3s) la 2.0s.'
        )

    def cb_rapid(self):
        # Callback SCURT: doar incrementam si logam. Daca vezi acest mesaj
        # aparand regulat CHIAR SI in timpul muncii grele, inseamna ca
        # MultiThreadedExecutor a rulat cele doua callback-uri in paralel.
        self.contor += 1
        self.get_logger().info(f'[rapid] tic #{self.contor}')

    def cb_lent(self):
        # Callback LENT: simulam o operatie costisitoare (citire senzor lent,
        # calcul greu, asteptarea unui serviciu extern etc.) cu time.sleep(3.0).
        # ATENTIE: intr-un cod real, blocarea firului asa NU e ideala, dar aici
        # vrem exact sa aratam efectul asupra executorului.
        self.get_logger().info('[lent] incep munca grea (sleep 3s)...')
        time.sleep(3.0)
        self.get_logger().info('[lent] am terminat munca grea.')


def main(args=None):
    rclpy.init(args=args)
    node = NodExecutor()

    # === Diferenta-cheie fata de rclpy.spin(node) ===
    # rclpy.spin(node) foloseste in spate un SingleThreadedExecutor: un singur fir
    # apeleaza toate callback-urile, deci munca grea din cb_lent ar bloca cb_rapid.
    #
    # Aici cream EXPLICIT un MultiThreadedExecutor cu 4 fire. Combinat cu cele doua
    # callback groups de mai sus, asta permite ca timer-ul rapid sa continue sa ruleze
    # in timp ce timer-ul lent sta blocat in sleep, fiindca ruleaza pe fire diferite.
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        # spin() pe executor invarte nodul la fel ca rclpy.spin, dar pe mai multe fire.
        executor.spin()
    except KeyboardInterrupt:
        # Ctrl+C: iesim curat din bucla, fara traceback urat.
        pass
    finally:
        # Oprim intai executorul (firele lui), apoi distrugem nodul si inchidem rclpy.
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
