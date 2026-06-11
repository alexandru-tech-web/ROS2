import rclpy
from rclpy.node import Node
from std_msgs.msg import String
# Aceleasi politici ca la publisher. Lectia centrala a acestui modul: subscriber-ul
# si publisher-ul trebuie sa aiba QoS-uri COMPATIBILE. Daca nu, topicul exista,
# endpoint-urile se vad in "ros2 topic info", dar NU curge niciun mesaj.
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy


class QosSubscriber(Node):
    def __init__(self):
        super().__init__('qos_subscriber')

        # Acelasi parametru ca la publisher, ca sa putem combina profiluri:
        #   ros2 run curs_ros2 m8_sub --ros-args -p profil:=reliable
        self.declare_parameter('profil', 'reliable')
        profil = self.get_parameter('profil').value

        # Construim acelasi tip de QoSProfile. Pentru a primi mesaje, acest QoS
        # trebuie sa fie compatibil cu cel al publisher-ului (vezi tabelul din .md).
        qos = self.construieste_qos(profil)

        # Cream abonarea cu QoS-ul ales. Daca profilurile sunt incompatibile
        # (ex: publisher BEST_EFFORT, subscriber RELIABLE), callback-ul de mai jos
        # NU se va apela niciodata, desi nu apare nicio eroare.
        self.sub = self.create_subscription(String, '/qos_demo', self.cb_mesaj, qos)

        self.get_logger().info(
            f'Subscriber pornit pe /qos_demo cu profil QoS = "{profil}". Astept mesaje...'
        )

    def construieste_qos(self, profil):
        # depth=10: pastram in coada ultimele 10 mesaje primite (KEEP_LAST implicit).
        qos = QoSProfile(depth=10)

        if profil == 'best_effort':
            # Un subscriber BEST_EFFORT accepta atat un publisher BEST_EFFORT, cat si
            # unul RELIABLE -> e "mai permisiv". Cere o livrare cel mult la fel de stricta.
            qos.reliability = ReliabilityPolicy.BEST_EFFORT
        elif profil == 'transient':
            # Cere si mesajele "latched": TRANSIENT_LOCAL pe partea de subscriber
            # inseamna ca vrem si ultimele mesaje retinute de un publisher transient.
            qos.reliability = ReliabilityPolicy.RELIABLE
            qos.durability = DurabilityPolicy.TRANSIENT_LOCAL
            qos.history = HistoryPolicy.KEEP_LAST
        else:
            # Implicit / "reliable": un subscriber RELIABLE este STRICT. El se conecteaza
            # DOAR la un publisher RELIABLE. Un publisher BEST_EFFORT este incompatibil
            # -> rezultatul este ZERO mesaje primite (capcana clasica!).
            qos.reliability = ReliabilityPolicy.RELIABLE

        return qos

    def cb_mesaj(self, msg):
        # Se apeleaza DOAR daca QoS-ul a fost compatibil si mesajul a fost livrat.
        # Daca nu vezi niciodata acest log, suspecteaza o incompatibilitate de QoS.
        self.get_logger().info(f'Primit: {msg.data}')


def main(args=None):
    rclpy.init(args=args)
    node = QosSubscriber()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
