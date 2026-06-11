import rclpy
from rclpy.node import Node
# Twist = comanda de viteza pe care o trimitem broastei.
from geometry_msgs.msg import Twist
# ATENTIE: turtlesim NU foloseste geometry_msgs pentru pozitie, ci propriul tip
# turtlesim/msg/Pose, cu campurile x, y, theta (orientarea in radiani) si vitezele.
from turtlesim.msg import Pose

# Importam LOGICA PURA din modulul partajat. Aceste functii NU stiu nimic despre
# ROS: primesc numere, intorc numere. Sunt testate automat in test/test_logica.py.
# Asa, "creierul" controlului e verificat independent de stratul de comunicatie.
from curs_ros2.logica import eroare_distanta, unghi_spre_tinta, normalizeaza_unghi


class TurtleControl(Node):
    """Control proportional "go-to-goal" cu FEEDBACK.

    Spre deosebire de varianta open-loop, aici ne uitam tot timpul la pozitia
    reala a broastei (din /turtle1/pose) si comandam viteze PROPORTIONALE cu
    eroarea ramasa: cu cat suntem mai departe / mai prost orientati, cu atat
    comandam mai mult. Pe masura ce ne apropiem, comenzile scad singure -> robotul
    se opreste lin pe tinta. Aceasta este esenta controlului cu feedback.
    """

    def __init__(self):
        super().__init__('turtle_control')

        # === Tinta ca parametri ROS ===
        # Le declaram ca parametri ca sa le putem schimba de la rulare fara a edita
        # codul: ros2 run ... -p x_tinta:=2.0 -p y_tinta:=9.0
        self.declare_parameter('x_tinta', 8.0)
        self.declare_parameter('y_tinta', 8.0)
        self.x_tinta = self.get_parameter('x_tinta').value
        self.y_tinta = self.get_parameter('y_tinta').value

        # Pozitia curenta a broastei; o vom completa din callback-ul de Pose.
        # Pornim cu None ca sa NU comandam nimic inainte sa fi primit primul mesaj.
        self.pose = None

        # Ne abonam la pozitia broastei (feedback-ul nostru).
        self.sub_pose = self.create_subscription(
            Pose, '/turtle1/pose', self.cb_pose, 10
        )
        # Publicam comenzile de viteza.
        self.pub_cmd = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)

        # Bucla de control la 10 Hz (perioada 0.1 s). 10 Hz e suficient pentru
        # turtlesim si tine codul didactic, fara sa incarcam inutil sistemul.
        self.timer = self.create_timer(0.1, self.cb_control)

        # Flag ca sa logam "ajuns" o singura data, nu la fiecare tic dupa sosire.
        self.ajuns = False

        self.get_logger().info(
            f'turtle_control pornit. Tinta = ({self.x_tinta}, {self.y_tinta}).'
        )

    def cb_pose(self, msg):
        # Salvam ultima pozitie cunoscuta. Nu calculam nimic aici: doar memoram,
        # iar decizia de control o luam ritmat in cb_control (separare clara).
        self.pose = msg

    def cb_control(self):
        # Daca inca nu am primit nicio pozitie, nu avem pe ce baza sa decidem.
        if self.pose is None:
            return

        x = self.pose.x
        y = self.pose.y
        theta = self.pose.theta

        # 1) Cat de departe suntem de tinta? (functie pura, testata)
        dist = eroare_distanta(x, y, self.x_tinta, self.y_tinta)

        # 2) Daca am ajuns suficient de aproape, ne oprim complet.
        # Twist gol = toate vitezele 0. Publicam mereu un stop, ca broasca sa nu
        # ramana cu ultima viteza comandata (altfel ar continua sa alunece).
        if dist < 0.1:
            self.pub_cmd.publish(Twist())
            if not self.ajuns:
                self.get_logger().info('Am ajuns la tinta! Opresc broasca.')
                self.ajuns = True
            return

        # Daca ne-am miscat tinta sau am fost deplasati, redevenim "in miscare".
        self.ajuns = False

        # 3) Cat de prost orientati suntem fata de directia spre tinta?
        # unghi_spre_tinta da unghiul absolut catre tinta; scadem theta (unde
        # privim acum) si NORMALIZAM in [-pi, pi] ca sa ne rotim pe drumul scurt.
        err_unghi = normalizeaza_unghi(
            unghi_spre_tinta(x, y, self.x_tinta, self.y_tinta) - theta
        )

        twist = Twist()
        # Control proportional pe rotire: cu cat eroarea de unghi e mai mare,
        # cu atat ne rotim mai repede. Castigul 4.0 a fost ales empiric.
        twist.angular.z = 4.0 * err_unghi

        # Mergem inainte DOAR daca suntem deja aproape orientati spre tinta
        # (|err_unghi| mic). Daca am merge inainte cu robotul intors gresit, am
        # pleca in directia gresita -> intai ne aliniem, apoi inaintam.
        if abs(err_unghi) < 0.2:
            twist.linear.x = 1.5 * dist
        else:
            twist.linear.x = 0.0

        self.pub_cmd.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = TurtleControl()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
