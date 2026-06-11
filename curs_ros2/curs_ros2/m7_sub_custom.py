import rclpy
from rclpy.node import Node
# Acelasi tip custom ca la publisher. Subscriber-ul TREBUIE sa cunoasca tipul
# mesajului ca sa-l poata deserializa: de aceea importam exact aceeasi clasa.
# Daca publisher si subscriber ar folosi tipuri diferite pe acelasi topic,
# nu s-ar conecta niciodata.
from curs_ros2_interfaces.msg import Temperatura


class SubscriberCustom(Node):
    def __init__(self):
        super().__init__('subscriber_custom')

        # Ne abonam la /temperatura_custom cu tipul NOSTRU, Temperatura.
        # Numele topicului si tipul trebuie sa coincida cu cele de la publisher.
        self.sub = self.create_subscription(
            Temperatura,
            '/temperatura_custom',
            self.cb_temperatura,
            10
        )
        self.get_logger().info('Subscriber custom pornit, ascult /temperatura_custom...')

    def cb_temperatura(self, msg):
        # Frumusetea tipului custom: primim un singur obiect cu AMBELE campuri.
        # Le accesam dupa nume (msg.valoare, msg.status), nu trebuie sa corelam
        # manual doua topice separate.
        self.get_logger().info(
            f'Primit: valoare={msg.valoare}  status={msg.status}'
        )


def main(args=None):
    rclpy.init(args=args)
    node = SubscriberCustom()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
