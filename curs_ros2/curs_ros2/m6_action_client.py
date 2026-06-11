import rclpy
from rclpy.node import Node
# ActionClient e "telefonul" prin care trimitem un goal serverului si urmarim
# apoi feedback-ul si rezultatul. Tipul si numele actiunii trebuie sa fie
# identice cu cele din server, altfel cei doi nu se conecteaza.
from rclpy.action import ActionClient
from example_interfaces.action import Fibonacci


class ClientFibonacci(Node):
    def __init__(self):
        super().__init__('client_fibonacci')

        # Creem clientul de actiune: acelasi tip (Fibonacci) si acelasi nume
        # ("fibonacci") ca la server.
        self.client = ActionClient(self, Fibonacci, 'fibonacci')

    def trimite_goal(self, order):
        # Asteptam ca serverul sa existe, ca sa nu trimitem un goal "in gol".
        # wait_for_server blocheaza pana cand serverul e disponibil.
        self.get_logger().info('Astept serverul de actiune "fibonacci"...')
        self.client.wait_for_server()
        self.get_logger().info('Serverul este disponibil, trimit goal-ul.')

        # Construim goal-ul: vrem primii "order" termeni din secventa.
        goal = Fibonacci.Goal()
        goal.order = order

        self.get_logger().info(f'Trimit goal: order={order}')

        # send_goal_async NU blocheaza: ne da un "future" pentru raspunsul de
        # acceptare a goal-ului. In plus ii dam feedback_callback, chemat de
        # fiecare data cand serverul publica feedback (secventa partiala).
        future_goal = self.client.send_goal_async(goal, feedback_callback=self.cb_feedback)

        # Cand soseste raspunsul "goal acceptat / respins", se cheama cb_raspuns.
        # Inlantuim astfel pasii (fara sa blocam): acceptare -> rezultat.
        future_goal.add_done_callback(self.cb_raspuns)

    def cb_feedback(self, feedback_msg):
        # feedback_msg.feedback e mesajul Fibonacci.Feedback; campul "sequence"
        # e secventa partiala de pana acum. O afisam ca sa vedem progresul live.
        self.get_logger().info(f'Feedback primit: {feedback_msg.feedback.sequence}')

    def cb_raspuns(self, future):
        # Aici aflam daca serverul a ACCEPTAT goal-ul. goal_handle.accepted e
        # True/False. Daca e respins, ne oprim aici.
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal RESPINS de server.')
            rclpy.shutdown()
            return

        self.get_logger().info('Goal ACCEPTAT de server, astept rezultatul...')

        # Cerem rezultatul tot asincron. Cand task-ul se termina, se cheama
        # cb_rezultat cu rezultatul final.
        future_rezultat = goal_handle.get_result_async()
        future_rezultat.add_done_callback(self.cb_rezultat)

    def cb_rezultat(self, future):
        # future.result().result e mesajul Fibonacci.Result; "sequence" e
        # secventa finala completa.
        rezultat = future.result().result
        self.get_logger().info(f'Rezultat final: {rezultat.sequence}')

        # Am primit ce ne trebuia: oprim rclpy, ceea ce face ca rclpy.spin din
        # main sa se incheie, deci nodul se termina curat. Asa folosim "spin"
        # pentru a astepta evenimentele asincrone, dar iesim cand vine
        # rezultatul, fara sa blocam manual la infinit.
        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = ClientFibonacci()

    # Cerem primii 10 termeni. Apelul e asincron: doar pornim lantul de
    # callback-uri (acceptare -> feedback -> rezultat).
    node.trimite_goal(10)

    # spin invarte nodul si proceseaza feedback-ul si rezultatul pe masura ce
    # sosesc. Se opreste cand cb_rezultat cheama rclpy.shutdown(). De aceea NU
    # mai apelam un al doilea shutdown dupa spin: el a fost deja facut in callback.
    rclpy.spin(node)

    node.destroy_node()


if __name__ == '__main__':
    main()
