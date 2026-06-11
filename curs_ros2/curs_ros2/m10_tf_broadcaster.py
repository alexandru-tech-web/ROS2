import math

import rclpy
from rclpy.node import Node
# TransformBroadcaster e "difuzorul" de transformari: el publica pe topicul /tf
# o relatie intre doua frame-uri (parinte -> copil). Restul sistemului (listener,
# rviz2) o asculta si stie unde se afla un frame fata de altul.
from tf2_ros import TransformBroadcaster
# TransformStamped e MESAJUL pe care il trimitem: contine un antet (cu timp si
# frame-ul parinte), numele frame-ului copil, o translatie si o rotatie (quaternion).
from geometry_msgs.msg import TransformStamped


def quaternion_din_yaw(yaw):
    # In ROS rotatiile NU se exprima ca unghiuri (Euler), ci ca QUATERNIONI,
    # pentru ca evita ambiguitatile si "gimbal lock". Aici avem o rotatie doar
    # in jurul axei Z (yaw), deci formula se simplifica mult:
    #   qx = qy = 0, qz = sin(yaw/2), qw = cos(yaw/2).
    # Pentru o rotatie pura pe Z, componentele x si y ale quaternionului sunt 0.
    qx = 0.0
    qy = 0.0
    qz = math.sin(yaw / 2.0)
    qw = math.cos(yaw / 2.0)
    return (qx, qy, qz, qw)


class TfBroadcaster(Node):
    def __init__(self):
        super().__init__('tf_broadcaster')

        # Cream difuzorul o singura data; el deschide singur publisher-ul pe /tf.
        self.br = TransformBroadcaster(self)

        # "Ceasul" miscarii: il incrementam la fiecare tic ca sa miscam robotul.
        self.t = 0.0

        # Publicam la 20 Hz (perioada 0.05 s). O frecventa buna pentru transformari
        # dinamice: destul de des cat miscarea sa para fluida, fara sa inundam reteaua.
        self.timer = self.create_timer(0.05, self.cb_timer)

        self.get_logger().info('Broadcaster pornit: public world -> robot la 20 Hz')

    def cb_timer(self):
        # Robotul se plimba pe un cerc de raza 1 si se roteste in jurul propriei axe.
        # x = cos(t), y = sin(t) descriu cercul; yaw = t face robotul sa "priveasca"
        # mereu in directia in care se schimba pozitia, ca o orientare naturala.
        x = math.cos(self.t)
        y = math.sin(self.t)
        yaw = self.t

        # Construim mesajul de transformare (snapshot al pozitiei la momentul curent).
        t = TransformStamped()

        # Antetul: stamp = ACUM. Timpul e esential, pentru ca un listener cere mereu
        # transformarea valabila la un anumit moment; daca timpul lipseste sau e gresit,
        # interpolarea / cautarea esueaza.
        t.header.stamp = self.get_clock().now().to_msg()
        # frame_id = parintele (sistemul de referinta fix "lumea").
        t.header.frame_id = 'world'
        # child_frame_id = copilul (robotul) a carui pozitie o descriem fata de parinte.
        t.child_frame_id = 'robot'

        # Translatia: unde se afla originea frame-ului "robot" fata de "world".
        # z = 0 pentru ca robotul se misca intr-un plan (2D).
        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = 0.0

        # Rotatia: orientarea robotului, ca quaternion derivat din yaw.
        qx, qy, qz, qw = quaternion_din_yaw(yaw)
        t.transform.rotation.x = qx
        t.transform.rotation.y = qy
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw

        # Trimitem transformarea. De aici incolo, oricine asculta /tf stie pozitia.
        self.br.sendTransform(t)

        # Avansam "ceasul" cu 0.05 (acelasi pas ca perioada timer-ului): astfel,
        # robotul parcurge un radian la fiecare ~1 secunda si un cerc complet in ~6.3 s.
        self.t += 0.05


def main(args=None):
    rclpy.init(args=args)
    node = TfBroadcaster()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
