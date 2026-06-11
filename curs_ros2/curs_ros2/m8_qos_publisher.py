import rclpy
from rclpy.node import Node
from std_msgs.msg import String
# QoSProfile e "setul de reguli de livrare" pe care le atasam unui publisher
# sau subscriber. Cele trei politici de care ne pasa aici:
#  - ReliabilityPolicy: garantam livrarea (RELIABLE) sau nu (BEST_EFFORT)?
#  - DurabilityPolicy:  pastram ultimul mesaj pentru cei care se aboneaza tarziu
#                       (TRANSIENT_LOCAL = "latched") sau nu (VOLATILE)?
#  - HistoryPolicy:     cate mesaje tinem in coada (KEEP_LAST + depth) sau toate
#                       (KEEP_ALL)?
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy


class QosPublisher(Node):
    def __init__(self):
        super().__init__('qos_publisher')

        # === Parametrul care alege profilul de QoS ===
        # Il declaram ca string cu valoarea implicita "reliable". Asa putem porni
        # acelasi nod cu profiluri diferite de la linia de comanda, fara sa edcitam codul:
        #   ros2 run curs_ros2 m8_pub --ros-args -p profil:=best_effort
        self.declare_parameter('profil', 'reliable')
        profil = self.get_parameter('profil').value

        # Construim QoSProfile-ul potrivit profilului cerut. Pornim mereu de la un
        # depth=10 (cate mesaje tinem in coada inainte sa le aruncam pe cele vechi).
        qos = self.construieste_qos(profil)

        # Atasam acest QoS la publisher. ATENTIE: QoS-ul cu care creezi publisher-ul
        # trebuie sa fie COMPATIBIL cu cel al subscriber-ului, altfel ROS leaga
        # endpoint-urile dar NU livreaza niciun mesaj (in tacere, fara eroare).
        self.pub = self.create_publisher(String, '/qos_demo', qos)

        self.contor = 0
        # Publicam la 2 Hz -> o data la 0.5 secunde.
        self.timer = self.create_timer(0.5, self.cb_timer)

        self.get_logger().info(
            f'Publisher pornit pe /qos_demo cu profil QoS = "{profil}". Public la 2 Hz...'
        )

    def construieste_qos(self, profil):
        # depth=10 inseamna: pastram in coada ultimele 10 mesaje (KEEP_LAST implicit).
        qos = QoSProfile(depth=10)

        if profil == 'best_effort':
            # BEST_EFFORT = "trimit si uit": rapid, fara retransmisii. Daca un pachet
            # se pierde, ghinion. Potrivit pentru date de senzor / fluxuri rapide.
            qos.reliability = ReliabilityPolicy.BEST_EFFORT
        elif profil == 'transient':
            # TRANSIENT_LOCAL = "latched": publisher-ul retine ultimele mesaje si le
            # livreaza unui subscriber care se aboneaza MAI TARZIU. Util pentru date
            # care se schimba rar (o harta, o configuratie). Il tinem si RELIABLE.
            qos.reliability = ReliabilityPolicy.RELIABLE
            qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
            # Setam explicit history ca demonstratie: pastram ultimele 10 (KEEP_LAST).
            qos.history = HistoryPolicy.KEEP_LAST
        else:
            # Implicit / "reliable": RELIABLE garanteaza livrarea (retransmite pana
            # ajunge). Potrivit pentru comenzi, unde nu vrei sa pierzi mesaje.
            qos.reliability = ReliabilityPolicy.RELIABLE

        return qos

    def cb_timer(self):
        # Construim un mesaj cu un contor crescator, ca sa vedem clar ce ajunge
        # (sau ce NU ajunge) la subscriber.
        self.contor += 1
        msg = String()
        msg.data = f'mesaj #{self.contor}'
        self.pub.publish(msg)
        self.get_logger().info(f'Publicat: {msg.data}')


def main(args=None):
    rclpy.init(args=args)
    node = QosPublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
