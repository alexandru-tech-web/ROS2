import rclpy
from rclpy.node import Node
# Temperatura este un tip de mesaj DEFINIT DE NOI, intr-un pachet separat de
# interfete (curs_ros2_interfaces, de tip ament_cmake). Aici doar il IMPORTAM
# si il folosim. Importul reuseste DOAR daca pachetul de interfete a fost
# construit cu colcon si am dat "source" pe install/setup.bash dupa build.
# Tipul are exact doua campuri: float64 valoare; string status.
from curs_ros2_interfaces.msg import Temperatura


class PublisherCustom(Node):
    def __init__(self):
        super().__init__('publisher_custom')

        # Publicam pe /temperatura_custom mesaje de tipul NOSTRU, nu un Float64
        # standard. Avantajul fata de doua topice separate (valoare + status) e
        # ca cele doua campuri calatoresc IMPREUNA, intr-un singur mesaj coerent:
        # nu poti primi vreodata o valoare fara statusul ei.
        self.pub = self.create_publisher(Temperatura, '/temperatura_custom', 10)

        # Valoarea de pornire; o crestem la fiecare tic ca sa vedem cum trece
        # statusul prin pragurile NORMAL -> ATENTIE -> CRITIC.
        self.valoare = 20.0

        # Timer la 1.0s: publicam o data pe secunda, ca la modulul de topice.
        self.timer = self.create_timer(1.0, self.cb_timer)

        self.get_logger().info('Publisher custom pornit, public pe /temperatura_custom...')

    def cb_timer(self):
        # Construim un mesaj GOL de tipul nostru si ii completam cele doua campuri.
        # Numele campurilor (valoare, status) sunt EXACT cele din Temperatura.msg.
        msg = Temperatura()
        msg.valoare = self.valoare

        # Decidem statusul dupa aceleasi praguri ca la modulul de topice, ca sa
        # fie usor de comparat. Logica e in nod ca sa stea langa ce publica el.
        if self.valoare < 30.0:
            msg.status = 'NORMAL'
        elif self.valoare < 50.0:
            msg.status = 'ATENTIE'
        else:
            msg.status = 'CRITIC'

        self.pub.publish(msg)

        # Logam ambele campuri ca sa vedem in terminal corespondenta valoare/status.
        self.get_logger().info(f'Publicat: valoare={msg.valoare}  status={msg.status}')

        # Crestem cu 0.5 grade pe secunda; in cateva zeci de secunde trecem prin
        # toate cele trei statusuri, deci demonstratia e completa.
        self.valoare += 0.5


def main(args=None):
    rclpy.init(args=args)
    node = PublisherCustom()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
