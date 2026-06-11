import sys

import rclpy
from rclpy.node import Node
# Acelasi tip ca la server: clientul si serverul TREBUIE sa vorbeasca
# aceeasi "limba", adica acelasi tip de serviciu, altfel nu se conecteaza.
from example_interfaces.srv import AddTwoInts


class ClientAdunare(Node):
    def __init__(self):
        super().__init__('client_adunare')

        # create_client e "telefonul" prin care sunam serverul de pe serviciul
        # "aduna". Numele trebuie sa fie identic cu cel folosit la server.
        self.cli = self.create_client(AddTwoInts, 'aduna')

        # Daca apelam un server care inca nu exista, cererea s-ar pierde.
        # De aceea asteptam politicos pana serverul e disponibil. timeout_sec=1.0
        # inseamna ca verificam o data pe secunda si logam ca inca asteptam.
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Astept serviciul "aduna" sa devina disponibil...')

        self.get_logger().info('Serviciul "aduna" este disponibil.')

    def trimite_cerere(self, a, b):
        # Construim cererea si ii completam campurile a si b.
        request = AddTwoInts.Request()
        request.a = a
        request.b = b

        self.get_logger().info(f'Trimit cererea: {a} + {b}')

        # call_async NU blocheaza: ne da imediat un "future" (o promisiune ca
        # raspunsul va sosi candva). Asa nodul ramane reactiv. Asteptarea
        # propriu-zisa o facem in main, controlat, cu spin_until_future_complete.
        return self.cli.call_async(request)


def main(args=None):
    rclpy.init(args=args)
    node = ClientAdunare()

    # Citim cele doua numere din linia de comanda daca exista
    # (ex: ros2 run curs_ros2 m5_client 5 7), altfel folosim valori implicite.
    if len(sys.argv) >= 3:
        a = int(sys.argv[1])
        b = int(sys.argv[2])
    else:
        a = 2
        b = 3

    future = node.trimite_cerere(a, b)

    # spin_until_future_complete invarte nodul (proceseaza comunicarea) DOAR
    # pana cand raspunsul soseste, apoi se opreste. Asa nu blocam la infinit
    # si nu apelam serviciul sincron dintr-un callback (vezi capcanele din .md).
    rclpy.spin_until_future_complete(node, future)

    rezultat = future.result()
    node.get_logger().info(f'Rezultat primit de la server: {a} + {b} = {rezultat.sum}')

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
