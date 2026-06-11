import rclpy
from rclpy.node import Node
# Buffer = "memoria" TF: aici se acumuleaza toate transformarile auzite pe /tf,
# pe o fereastra de timp. TransformListener = "urechea" care umple bufferul:
# se aboneaza singur la /tf si pune ce aude in buffer.
from tf2_ros import Buffer, TransformListener
# TransformException e exceptia aruncata de lookup_transform cand cautarea
# esueaza (frame inexistent, transformare inca neauzita, timp indisponibil etc.).
from tf2_ros import TransformException


class TfListener(Node):
    def __init__(self):
        super().__init__('tf_listener')

        # Cream intai bufferul (memoria), apoi listener-ul care il alimenteaza.
        # ORDINEA conteaza: listener-ul are nevoie de buffer ca sa stie unde sa scrie.
        self.buffer = Buffer()
        self.listener = TransformListener(self.buffer, self)

        # Interogam transformarea o data pe secunda. Nu publicam nimic; doar CITIM
        # din buffer ce a fost auzit pe /tf.
        self.timer = self.create_timer(1.0, self.cb_timer)

        self.get_logger().info('Listener pornit: caut transformarea world -> robot')

    def cb_timer(self):
        # lookup_transform("world", "robot", ...) raspunde la intrebarea:
        # "unde se afla frame-ul 'robot' fata de frame-ul 'world'?".
        # rclpy.time.Time() (timpul 0) inseamna "DA-MI CEA MAI RECENTA transformare
        # disponibila", nu una de la un moment fix. E cel mai simplu mod si evita
        # erorile de "timp viitor / timp prea vechi".
        try:
            trans = self.buffer.lookup_transform(
                'world',                # frame-ul tinta (de referinta)
                'robot',                # frame-ul sursa (al carui pozitie o vrem)
                rclpy.time.Time()       # timp 0 = cea mai recenta transformare
            )
        except TransformException as e:
            # Daca broadcaster-ul inca nu a pornit sau nu am auzit inca transformarea,
            # NU e o eroare fatala: doar mai asteptam si reincercam la urmatorul tic.
            self.get_logger().info(f'Inca astept transformarea world -> robot: {e}')
            return

        # Daca am ajuns aici, avem transformarea. Componenta de translatie ne da
        # pozitia robotului (x, y) in sistemul "world".
        x = trans.transform.translation.x
        y = trans.transform.translation.y
        self.get_logger().info(f'Robotul este la x={x:.2f}, y={y:.2f} fata de world')


def main(args=None):
    rclpy.init(args=args)
    node = TfListener()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
