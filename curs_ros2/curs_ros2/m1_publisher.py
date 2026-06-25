import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64

class Publisher(Node):
    def __init__(self):
        super().__init__('publisher_temperatura')
        
        self.pub = self.create_publisher(Float64, '/temperatura', 10)
        self.valoare = 20.0
        self.timer = self.create_timer(1.0, self.callback)
        self.get_logger().info('Publisher pornit!')

    def callback(self):
        msg = Float64()
        msg.data = self.valoare
        self.pub.publish(msg)
        self.get_logger().info(f'Publicat: {self.valoare}degC')
        self.valoare += 0.5  # creste cu 0.5 grade pe secunda

def main():
    rclpy.init()
    node = Publisher()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()