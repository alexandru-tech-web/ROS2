import rclpy
# Un "lifecycle node" (nod gestionat) NU porneste direct in functiune. El are o
# masina de stari clara (unconfigured -> inactive -> active -> ...) si trece dintr-o
# stare in alta doar la comanda noastra, prin TRANZITII (configure, activate, etc.).
# Asta ne da o pornire CONTROLATA: ideal cand nodul trebuie sa pregateasca ceva
# (deschidere de hardware, alocare de resurse) inainte sa inceapa sa "lucreze".
#
# API Jazzy:
#  - LifecycleNode           = clasa de baza pentru un nod gestionat (in loc de Node).
#  - TransitionCallbackReturn = ce intoarcem dintr-un callback de tranzitie
#                               (SUCCESS / FAILURE / ERROR) ca sa spunem daca a reusit.
#  - LifecycleState          = obiectul "stare" pe care framework-ul ni-l paseaza in
#                               fiecare callback de tranzitie (label + id-ul starii).
from rclpy.lifecycle import LifecycleNode, TransitionCallbackReturn, LifecycleState
from rclpy.executors import MultiThreadedExecutor, ExternalShutdownException
# Nota: in ROS 2 Jazzy clasa de baza exista atat sub numele "LifecycleNode", cat si
# sub aliasul "Node" din rclpy.lifecycle. Daca pe alta distributie importul de mai sus
# ar esua, alternativa echivalenta este:
#     from rclpy.lifecycle import Node as LifecycleNode
from std_msgs.msg import String


class NodLifecycle(LifecycleNode):
    def __init__(self):
        # Mostenim din LifecycleNode, deci nodul porneste automat in starea
        # "unconfigured": exista pe retea, dar inca nu a creat publisher/timer si
        # nu publica nimic. Asteapta comenzi de tranzitie din CLI.
        super().__init__('nod_lifecycle')
        self.get_logger().info('Nod lifecycle creat (stare: unconfigured). Astept tranzitii...')

    def on_configure(self, state: LifecycleState) -> TransitionCallbackReturn:
        # Tranzitia "configure": unconfigured -> inactive.
        # Aici PREGATIM resursele: cream publisher-ul si timer-ul. Le cream acum,
        # nu in __init__, tocmai ca sa demonstram pornirea controlata: nimic nu se
        # aloca pana cand cineva nu cere explicit "configure".
        #
        # Folosim create_lifecycle_publisher (nu create_publisher obisnuit): acest
        # tip de publisher "stie" de starea nodului si publica EFECTIV doar cand
        # nodul e ACTIVE. In inactive, publish(...) e un no-op (nu trimite nimic).
        self._pub = self.create_lifecycle_publisher(String, '/lc_chatter', 10)

        # Timer-ul ruleaza tot timpul (si in inactive), dar publish-ul lui nu are
        # efect pana ce nu activam nodul. Asa vedem clar diferenta inactive/active.
        self._timer = self.create_timer(1.0, self._on_timer)

        self.get_logger().info('on_configure: resurse create (publisher + timer). Trec in inactive.')
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: LifecycleState) -> TransitionCallbackReturn:
        # Tranzitia "activate": inactive -> active.
        # De aici incolo, lifecycle publisher-ul livreaza efectiv mesajele.
        self.get_logger().info('on_activate: nodul devine ACTIVE. Acum se publica pe /lc_chatter.')
        # IMPORTANT: chemam super().on_activate(state). El "porneste" publisher-ele
        # gestionate (le marcheaza ca active). Daca uiti acest apel, publish-ul ramane
        # no-op chiar daca starea apare ca "active".
        return super().on_activate(state)

    def on_deactivate(self, state: LifecycleState) -> TransitionCallbackReturn:
        # Tranzitia "deactivate": active -> inactive.
        # Oprim livrarea fara sa distrugem resursele: publisher-ul si timer-ul exista
        # in continuare, doar ca publish-ul redevine no-op. Util ca "pauza".
        self.get_logger().info('on_deactivate: nodul revine in inactive. Publish-ul redevine no-op.')
        # La fel ca la activate: super() opreste publisher-ele gestionate.
        return super().on_deactivate(state)

    def on_cleanup(self, state: LifecycleState) -> TransitionCallbackReturn:
        # Tranzitia "cleanup": inactive -> unconfigured.
        # Eliberam resursele alocate in on_configure, ca nodul sa revina "curat".
        # Le distrugem in ordine inversa fata de cum le-am creat.
        self.destroy_timer(self._timer)
        self.destroy_lifecycle_publisher(self._pub)
        self.get_logger().info('on_cleanup: resurse eliberate. Inapoi in unconfigured.')
        return TransitionCallbackReturn.SUCCESS

    def on_shutdown(self, state: LifecycleState) -> TransitionCallbackReturn:
        # Tranzitia "shutdown": din orice stare -> finalized (starea terminala).
        # Aici am elibera tot ce a mai ramas. In acest exemplu nu avem nimic special
        # de curatat suplimentar, deci doar confirmam succesul.
        self.get_logger().info('on_shutdown: nodul trece in finalized.')
        return TransitionCallbackReturn.SUCCESS

    def _on_timer(self):
        # Callback-ul timer-ului: construim un mesaj si il "publicam".
        # ATENTIE (ideea-cheie a modulului): acest publish are efect DOAR cand nodul
        # este ACTIVE. In inactive, lifecycle publisher-ul ignora in tacere mesajul
        # (no-op), deci pe /lc_chatter nu apare nimic. Nu e o eroare, e by design.
        msg = String()
        msg.data = 'salut din nodul lifecycle'
        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    # Construim nodul: porneste in "unconfigured" si e condus din linia de comanda
    # cu "ros2 lifecycle set /nod_lifecycle <tranzitie>".
    node = NodLifecycle()

    # Serviciile de lifecycle (change_state / get_state) sunt oferite automat de
    # framework. Le servim cu un MultiThreadedExecutor, NU cu rclpy.spin simplu:
    # cu executorul single-threaded implicit, raspunsul la "ros2 lifecycle get/set"
    # poate intarzia sau expira intermitent ("failed to send response (timeout)"),
    # mai ales pe rmw_fastrtps. Cu mai multe fire, cererile de tranzitie primesc
    # raspuns prompt, in paralel cu timer-ul nodului.
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        # Ctrl+C sau oprire externa: iesim curat, fara traceback.
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
