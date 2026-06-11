import rclpy
from rclpy.node import Node
# AddTwoInts e un tip standard gata facut: request are doua int64 (a, b),
# iar response are un singur int64 (sum). Il folosim ca sa nu definim noi
# un .srv propriu si sa ne concentram pe MODELUL cerere/raspuns.
from example_interfaces.srv import AddTwoInts


class ServerAdunare(Node):
    def __init__(self):
        super().__init__('server_adunare')

        # create_service "deschide ghiseul": de fiecare data cand un client
        # apeleaza serviciul "aduna", ROS 2 cheama cb_aduna cu cererea primita.
        # Numele serviciului ("aduna") trebuie sa coincida cu cel din client.
        self.srv = self.create_service(AddTwoInts, 'aduna', self.cb_aduna)
        self.get_logger().info('Server pornit, astept cereri pe serviciul "aduna"...')

    def cb_aduna(self, request, response):
        # IMPORTANT: nu construim un response nou. ROS 2 ne da deja un obiect
        # response gol, pregatit pentru tipul AddTwoInts; noi doar il completam
        # si il returnam. Asta e contractul: primesti request, returnezi response.
        response.sum = request.a + request.b

        # Logam si cererea, si rezultatul, ca sa vedem clar ce s-a procesat.
        self.get_logger().info(
            f'Cerere primita: {request.a} + {request.b} = {response.sum}'
        )

        # Returnarea response-ului inchide "apelul telefonic": clientul primeste
        # exact aceasta valoare inapoi.
        return response


def main(args=None):
    rclpy.init(args=args)
    node = ServerAdunare()
    # spin tine nodul viu si raspunde la cereri pana il oprim cu Ctrl+C.
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
