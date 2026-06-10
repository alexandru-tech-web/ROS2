import rclpy
from rclpy.node import Node

class NodSimplu(Node):
    def __init__(self):
        super().__init__('nod_simplu')
        self.get_logger().info('Nodul a pornit!')
        self.contor = 0
        self.timer = self.create_timer(1.0, self.callback)

    def callback(self):
        self.contor += 1
        self.get_logger().info(f'Secunda {self.contor}')

def main():
    rclpy.init()
    node = NodSimplu()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()