#!/usr/bin/env python3
"""
Servo Teleop — control shaft din tastatura
Sageata DREAPTA  → sens orar (viteza creste)
Sageata STANGA   → sens antiorar (viteza creste)
Sageata SUS      → creste viteza curenta
Sageata JOS      → scade viteza curenta
SPATIU           → stop imediat
Q                → iesire

Publicare pe: /model/servo1/joint/shaft_joint/cmd_vel
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import sys
import tty
import termios
import threading

TOPIC = '/model/servo1/joint/shaft_joint/cmd_vel'

SPEED_STEP = 0.5    # rad/s per apasare
MAX_SPEED  = 10.0   # rad/s maxim
MIN_SPEED  = 0.5    # rad/s minim (sub asta consideram stop)

BANNER = """
╔══════════════════════════════════════════╗
║       SERVO TELEOP — Tastatura           ║
╠══════════════════════════════════════════╣
║  ←  Sens antiorar                        ║
║  →  Sens orar                            ║
║  ↑  Creste viteza                        ║
║  ↓  Scade viteza                         ║
║  SPATIU  Stop                            ║
║  Q       Iesire                          ║
╚══════════════════════════════════════════╝
Viteza curenta: 0.0 rad/s  |  Directie: STOP
"""

def get_key(settings):
    """Citeste o tasta fara Enter."""
    tty.setraw(sys.stdin.fileno())
    key = sys.stdin.read(1)
    # Secvente escape pentru sageti
    if key == '\x1b':
        key += sys.stdin.read(2)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


class ServoTeleop(Node):
    def __init__(self):
        super().__init__('servo_teleop')
        self.pub = self.create_publisher(Float64, TOPIC, 10)
        self.speed    = 1.0   # rad/s
        self.velocity = 0.0   # valoare curenta publicata (+ orar, - antiorar)
        # Publicare periodica la 20Hz (chiar daca nu se apasa nimic)
        self.timer = self.create_timer(0.05, self.publish_vel)
        self.get_logger().info(f'Servo Teleop pornit → topic: {TOPIC}')

    def publish_vel(self):
        msg = Float64()
        msg.data = self.velocity
        self.pub.publish(msg)

    def print_status(self):
        if self.velocity > 0:
            directie = 'ORAR >>>'
        elif self.velocity < 0:
            directie = '<<< ANTIORAR'
        else:
            directie = 'STOP'
        print(f'\r  Viteza: {abs(self.velocity):.1f} rad/s  |  Directie: {directie}    ', end='', flush=True)

    def run_keyboard(self):
        settings = termios.tcgetattr(sys.stdin)
        print(BANNER)
        try:
            while rclpy.ok():
                key = get_key(settings)

                if key == '\x1b[C':          # Sageata DREAPTA → orar
                    self.velocity = self.speed
                elif key == '\x1b[D':        # Sageata STANGA → antiorar
                    self.velocity = -self.speed
                elif key == '\x1b[A':        # Sageata SUS → creste viteza
                    self.speed = min(self.speed + SPEED_STEP, MAX_SPEED)
                    if self.velocity != 0:
                        self.velocity = self.speed * (1 if self.velocity > 0 else -1)
                elif key == '\x1b[B':        # Sageata JOS → scade viteza
                    self.speed = max(self.speed - SPEED_STEP, MIN_SPEED)
                    if self.velocity != 0:
                        self.velocity = self.speed * (1 if self.velocity > 0 else -1)
                elif key == ' ':             # Spatiu → stop
                    self.velocity = 0.0
                elif key in ('q', 'Q'):      # Q → iesire
                    self.velocity = 0.0
                    self.publish_vel()
                    print('\nOprit. Pa!')
                    break

                self.print_status()

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)


def main():
    rclpy.init()
    node = ServoTeleop()

    # ROS2 spin pe thread separat ca sa nu blocheze tastatura
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    try:
        node.run_keyboard()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
