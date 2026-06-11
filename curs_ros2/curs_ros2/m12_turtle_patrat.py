import rclpy
from rclpy.node import Node
# Twist este mesajul standard de "comanda de viteza": camp liniar (x,y,z) si
# unghiular (x,y,z). Pentru o broasca 2D folosim doar linear.x (inainte/inapoi)
# si angular.z (rotire in jurul axei verticale).
from geometry_msgs.msg import Twist


class TurtlePatrat(Node):
    """Deseneaza un patrat in OPEN-LOOP: comanda viteze pe baza de timp, fara
    sa se uite la pozitia reala a broastei.

    DE CE open-loop? E cel mai simplu mod de a misca robotul: "mergi inainte
    2 secunde, apoi roteste-te ~2 secunde". PROBLEMA: nu masuram nimic. Daca
    simularea variaza putin, daca rotirea nu dureaza exact cat trebuie sau daca
    vitezele nu sunt fix cele cerute, erorile se ACUMULEAZA si patratul iese
    stramb. De aici motivatia nodului urmator (m12_turtle_control), care
    foloseste FEEDBACK din /turtle1/pose si corecteaza in timp real.
    """

    def __init__(self):
        super().__init__('turtle_patrat')

        # Publicam comenzi de viteza catre broasca. turtlesim asculta exact pe
        # acest topic; numele "turtle1" este broasca implicita din simulare.
        self.pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)

        # === Parametrii de miscare (open-loop) ===
        # Le tinem ca atribute ca sa fie usor de citit si de ajustat.
        self.viteza_inainte = 2.0   # m/s pe linear.x cat mergem drept
        self.viteza_rotire = 1.5708  # rad/s pe angular.z (~pi/2 rad/s)
        self.durata_inainte = 2.0   # secunde cat mergem drept (latura patratului)
        # Ca sa ne rotim 90 de grade (pi/2 rad) la viteza_rotire rad/s, avem
        # nevoie de timp = unghi / viteza = (pi/2) / (pi/2) = 1.0 secunda.
        # Calculam explicit ca sa fie clar de unde vine numarul.
        self.durata_rotire = (3.14159265 / 2.0) / self.viteza_rotire

        # === Masina de stari minimala ===
        # Alternam intre doua stari: 'inainte' si 'rotire'. Contorizam timpul
        # scurs in starea curenta si comutam cand am depasit durata alocata.
        self.stare = 'inainte'
        self.timp_in_stare = 0.0

        # Perioada timer-ului: 0.1 s -> 10 Hz. Folosim aceasta perioada si ca
        # increment de timp, ca sa stim cat de "vechi" e starea curenta.
        self.perioada = 0.1
        self.timer = self.create_timer(self.perioada, self.cb_timer)

        self.get_logger().info(
            'turtle_patrat pornit (OPEN-LOOP). Atentie: fara feedback, '
            'patratul va iesi aproximativ, nu perfect.'
        )

    def cb_timer(self):
        # Construim comanda in functie de starea curenta.
        twist = Twist()

        if self.stare == 'inainte':
            twist.linear.x = self.viteza_inainte
            twist.angular.z = 0.0
        else:  # 'rotire'
            twist.linear.x = 0.0
            twist.angular.z = self.viteza_rotire

        self.pub.publish(twist)

        # Avansam ceasul intern al starii cu o perioada de timer.
        self.timp_in_stare += self.perioada

        # Verificam daca trebuie sa comutam starea.
        if self.stare == 'inainte' and self.timp_in_stare >= self.durata_inainte:
            self.stare = 'rotire'
            self.timp_in_stare = 0.0
            self.get_logger().info('Latura terminata -> incep rotirea de 90 grade.')
        elif self.stare == 'rotire' and self.timp_in_stare >= self.durata_rotire:
            self.stare = 'inainte'
            self.timp_in_stare = 0.0
            self.get_logger().info('Rotire terminata -> merg pe latura urmatoare.')


def main(args=None):
    rclpy.init(args=args)
    node = TurtlePatrat()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
