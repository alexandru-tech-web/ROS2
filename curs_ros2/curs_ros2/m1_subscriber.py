import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
from std_msgs.msg import String

class SubTemperatura(Node):
    def __init__(self):
        super().__init__('subscriber_temperatura')
        
        self.sub = self.create_subscription(
            Float64,
            '/temperatura',
            self.callback,
            10
        )
        self.pub_alarma = self.create_publisher(String, '/alarma', 10)
        self.get_logger().info('Subscriber pornit, ascult /temperatura...')

    def callback(self, msg):
        temperatura = msg.data
        
        # Procesam datele primite
        if temperatura < 30.0:
            status = 'NORMAL'
        elif temperatura < 50.0:
            status = 'ATENTIE'
        else:
            status = 'CRITIC'
            
        self.get_logger().info(f'Temperatura: {temperatura}°C  →  {status}')

        if status == 'NORMAL':
            alarma = String()          # <-- variabila noua, nu suprascrie msg
            alarma.data = 'VALOARE NORMALA!'
            self.pub_alarma.publish(alarma)
        elif status == 'ATENTIE':
            alarma = String()          # <-- variabila noua, nu suprascrie msg
            alarma.data = 'VALOARE DE ATENTIONARE!'
            self.pub_alarma.publish(alarma)
        else: 
            alarma = String()          # <-- variabila noua, nu suprascrie msg
            alarma.data = 'VALOARE CRITICA'
            self.pub_alarma.publish(alarma)

def main():
    rclpy.init()
    node = SubTemperatura()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()