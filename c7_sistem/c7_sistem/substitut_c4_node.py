#!/usr/bin/env python3
"""substitut_c4_node.py -- SUBSTITUT, NU MASURATOARE. Tine locul nodului C4 (c4_platforma, P0, dupa 28.09)
in graficul V0: publica CONSTANTE pe /network_confidence (1.0) si /network_age (0.0), std_msgs/Float32, 10 Hz.
Singurul rol: sa existe topicurile cu tipul lor, ca restul graficului sa poata fi pornit. Nu contine logica."""
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class SubstitutC4(Node):
    def __init__(self):
        super().__init__("c4_SUBSTITUT_nu_masuratoare")
        self.declare_parameter("alpha_const", 1.0)
        self.declare_parameter("age_const", 0.0)
        self.pa = self.create_publisher(Float32, "/network_confidence", 10)
        self.pg = self.create_publisher(Float32, "/network_age", 10)
        self.n = 0
        self.create_timer(0.1, self._tick)
        self.get_logger().warn("SUBSTITUT C4, NU MASURATOARE: /network_confidence = %.2f si /network_age = %.2f constante, 10 Hz"
                               % (self.get_parameter("alpha_const").value, self.get_parameter("age_const").value))

    def _tick(self):
        self.pa.publish(Float32(data=float(self.get_parameter("alpha_const").value)))
        self.pg.publish(Float32(data=float(self.get_parameter("age_const").value)))
        self.n += 1
        if self.n % 100 == 0:
            self.get_logger().info("SUBSTITUT C4 (nu masuratoare): %d mesaje publicate" % self.n)


def main(args=None):
    rclpy.init(args=args)
    n = SubstitutC4()
    try:
        rclpy.spin(n)
    except KeyboardInterrupt:
        pass
    finally:
        n.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
