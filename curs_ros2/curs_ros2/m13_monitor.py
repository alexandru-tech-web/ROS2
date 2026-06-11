import rclpy
from rclpy.node import Node
# Mesaje standard: Float64 vine de la senzor, String pleaca spre alarma.
from std_msgs.msg import Float64
from std_msgs.msg import String
# AjustareTemperatura este serviciul NOSTRU custom, definit in pachetul de
# interfete curs_ros2_interfaces. Contractul lui (din .srv):
#   request:  float64 prag_nou
#   ---
#   response: bool succes, float64 prag_anterior, string mesaj
# Importul reuseste DOAR daca pachetul de interfete a fost construit cu colcon
# si am dat "source" pe install/setup.bash.
from curs_ros2_interfaces.srv import AjustareTemperatura
# REGULA DE AUR a repo-ului: NU rescriem logica de clasificare aici. O importam
# din nucleul PUR curs_ros2/logica.py, care e deja TESTAT (test/test_logica.py).
# Monitorul devine astfel doar "imbracamintea ROS" peste o functie verificata.
from curs_ros2.logica import clasifica_temperatura


class MonitorTemperatura(Node):
    """Monitor de temperatura (capstone M13).

    Asculta valori brute de la senzor, le clasifica (NORMAL / ATENTIE / CRITIC)
    folosind nucleul pur, publica statusul ca alarma si ofera un serviciu prin
    care pragul de ATENTIE poate fi schimbat LIVE, fara restart.
    """

    def __init__(self):
        super().__init__('monitor_temperatura')

        # === Parametri (M4): pragurile de clasificare ===
        # Le declaram float (30.0 / 50.0). Pot fi setate la lansare (launch / YAML)
        # sau, pentru prag_atentie, schimbate la cald prin serviciul de mai jos.
        self.declare_parameter('prag_atentie', 30.0)
        self.declare_parameter('prag_critic', 50.0)
        self.prag_atentie = self.get_parameter('prag_atentie').value
        self.prag_critic = self.get_parameter('prag_critic').value

        # === Topice (M2) ===
        # Ascultam valorile brute de la senzor...
        self.sub = self.create_subscription(
            Float64,
            '/senzor/temperatura',
            self.cb_temperatura,
            10
        )
        # ...si publicam statusul interpretat pe un topic separat de alarma.
        # Doua canale distincte: unul "brut" (numere), unul "decizie" (text).
        self.pub_alarma = self.create_publisher(String, '/senzor/alarma', 10)

        # === Serviciu custom (M5 + M7) ===
        # Deschidem "ghiseul" /ajusteaza_prag. Cand cineva apeleaza serviciul cu
        # un prag_nou, ROS cheama cb_ajusteaza si trimite raspunsul inapoi.
        self.srv = self.create_service(
            AjustareTemperatura,
            'ajusteaza_prag',
            self.cb_ajusteaza
        )

        self.get_logger().info(
            f'Monitor pornit: prag_atentie={self.prag_atentie}, '
            f'prag_critic={self.prag_critic}. Ascult /senzor/temperatura, '
            f'public /senzor/alarma, serviciu /ajusteaza_prag.'
        )

    def cb_temperatura(self, msg):
        # Toata "inteligenta" sta in functia pura, importata si testata. Aici doar
        # ii dam valoarea curenta si pragurile curente (pragul de atentie se poate
        # fi schimbat intre timp prin serviciu).
        status = clasifica_temperatura(msg.data, self.prag_atentie, self.prag_critic)

        # Publicam statusul ca alarma. String are un singur camp, "data".
        alarma = String()
        alarma.data = status
        self.pub_alarma.publish(alarma)

        # Logam corespondenta valoare -> status, ca sa vedem clar decizia.
        self.get_logger().info(f'Valoare={msg.data:.2f} -> status={status}')

    def cb_ajusteaza(self, request, response):
        # ROS ne da un "response" gol de tipul corect; noi doar il completam.
        # Memoram pragul vechi INAINTE de a-l schimba, ca sa-l putem raporta.
        prag_vechi = self.prag_atentie

        # Validare: un prag <= 0 nu are sens fizic si ar strica clasificarea.
        # In acest caz REFUZAM (succes=False) si NU modificam nimic. Returnam
        # totusi prag_anterior, ca apelantul sa stie ce valoare a ramas activa.
        if request.prag_nou <= 0.0:
            response.succes = False
            response.prag_anterior = prag_vechi
            response.mesaj = (
                f'Refuzat: prag_nou={request.prag_nou} trebuie sa fie strict pozitiv. '
                f'Pragul ramane {prag_vechi}.'
            )
            self.get_logger().warn(response.mesaj)
            return response

        # Valoare buna: aplicam noul prag de atentie LIVE. De acum, urmatoarele
        # mesaje de temperatura vor fi clasificate cu acest prag.
        self.prag_atentie = request.prag_nou

        response.succes = True
        response.prag_anterior = prag_vechi
        response.mesaj = (
            f'Prag de atentie schimbat de la {prag_vechi} la {self.prag_atentie}.'
        )
        self.get_logger().info(response.mesaj)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = MonitorTemperatura()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
