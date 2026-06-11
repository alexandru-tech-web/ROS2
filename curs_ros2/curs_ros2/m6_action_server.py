import time

import rclpy
from rclpy.node import Node
# ActionServer e "ghiseul" pentru actiuni: spre deosebire de un serviciu
# (o singura cerere -> un singur raspuns, instant), o actiune e un task LUNG,
# care trimite feedback pe parcurs si poate fi anulat.
from rclpy.action import ActionServer
# MultiThreadedExecutor ruleaza callback-urile pe MAI MULTE fire. Avem nevoie
# de el pentru ca "executa" e o functie de lunga durata (cu time.sleep): pe un
# singur fir, ea ar bloca tot nodul si feedback-ul nu ar mai pleca la timp.
from rclpy.executors import MultiThreadedExecutor
# Fibonacci e un tip standard de actiune gata facut: goal are "order" (cati
# termeni vrem), feedback are "sequence" (secventa partiala de pana acum),
# iar result are "sequence" (secventa finala completa).
from example_interfaces.action import Fibonacci


class ServerFibonacci(Node):
    def __init__(self):
        super().__init__('server_fibonacci')

        # Creem serverul de actiune. Argumentele:
        #   self                -> nodul caruia ii apartine serverul,
        #   Fibonacci           -> tipul actiunii (client si server trebuie sa
        #                          foloseasca acelasi tip),
        #   "fibonacci"         -> numele actiunii (trebuie sa coincida cu clientul),
        #   self.executa        -> functia chemata cand soseste un goal acceptat.
        self.server = ActionServer(self, Fibonacci, 'fibonacci', self.executa)
        self.get_logger().info('Server de actiune pornit, astept goal-uri pe "fibonacci"...')

    def executa(self, goal_handle):
        # goal_handle e "biletul de comanda": prin el citim cererea, trimitem
        # feedback, marcam succesul/anularea si returnam rezultatul.
        order = goal_handle.request.order
        self.get_logger().info(f'Goal primit: calculez primii {order} termeni Fibonacci.')

        # Pornim secventa cu primii doi termeni 0 si 1. Daca order e foarte mic,
        # taiem la final lista la dimensiunea ceruta (vezi return-ul).
        sequence = [0, 1]

        # Construim secventa pas cu pas. Incepem de la indicele 2 pentru ca
        # primii doi termeni ii avem deja. Mergem pana avem "order" termeni.
        for i in range(2, order):
            # Inainte de fiecare pas verificam daca cineva a cerut anularea.
            # Daca da, confirmam anularea cu canceled() si iesim cu un rezultat
            # gol. ESTE IMPORTANT sa returnam dupa canceled(), altfel serverul
            # ar continua sa lucreze pe un goal deja anulat.
            if goal_handle.is_cancel_requested:
                goal_handle.canceled()
                self.get_logger().info('Goal anulat la cererea clientului.')
                return Fibonacci.Result()

            # Termenul urmator = suma ultimilor doi termeni.
            sequence.append(sequence[i - 1] + sequence[i - 2])

            # Trimitem feedback cu secventa partiala de pana acum. Clientul
            # primeste asta in feedback_callback si vede progresul live.
            feedback = Fibonacci.Feedback(sequence=sequence)
            goal_handle.publish_feedback(feedback)
            self.get_logger().info(f'Feedback (pas {i}): {sequence}')

            # Pauza mica DOAR ca sa se vada progresul in demo. Intr-un task real
            # aici ar fi munca propriu-zisa (miscare robot, procesare etc.).
            # Pe MultiThreadedExecutor acest sleep nu blocheaza restul nodului.
            time.sleep(0.5)

        # Am terminat cu succes: marcam goal-ul ca reusit. Acest pas trebuie
        # facut INAINTE de a returna rezultatul, ca sa fie raportat corect.
        goal_handle.succeed()
        self.get_logger().info(f'Goal finalizat cu succes: {sequence[:order]}')

        # Returnam rezultatul final. Taiem la "order" termeni pentru cazurile
        # in care order < 2 (atunci lista [0, 1] ar fi prea lunga).
        return Fibonacci.Result(sequence=sequence[:order])


def main(args=None):
    rclpy.init(args=args)
    node = ServerFibonacci()

    # Folosim un MultiThreadedExecutor: callback-ul "executa" tine 0.5s pe pas.
    # Pe executorul implicit (single-thread) acel timp ar bloca firul si
    # feedback-ul/anularea n-ar mai fi procesate la timp. Cu mai multe fire,
    # task-ul lung ruleaza pe un fir, iar comunicarea curge in paralel.
    executor = MultiThreadedExecutor()

    # spin tine nodul viu si proceseaza goal-uri pana il oprim cu Ctrl+C.
    rclpy.spin(node, executor=executor)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
