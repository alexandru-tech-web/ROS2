import rclpy
from rclpy.node import Node
# ParameterDescriptor ne lasa sa atasam metadate (descriere) la un parametru,
# care apar in "ros2 param describe" si ajuta utilizatorul sa inteleaga la ce foloseste.
from rcl_interfaces.msg import ParameterDescriptor
# SetParametersResult este OBIECTUL pe care TREBUIE sa-l returnam din callback-ul
# de validare. Prin el spunem lui ROS daca acceptam ("successful=True") sau
# refuzam ("successful=False") noua valoare propusa.
from rcl_interfaces.msg import SetParametersResult


class NodParametri(Node):
    def __init__(self):
        super().__init__('nod_parametri')

        # === Declararea parametrilor ===
        # De ce declaram explicit? Pentru ca rclpy in Jazzy NU permite citirea unui
        # parametru nedeclarat (ar arunca exceptie). Declararea fixeaza si TIPUL:
        # 1.0 este float, deci parametrul "rata" va accepta DOAR valori float.
        self.declare_parameter(
            'rata',
            1.0,  # implicit 1.0 Hz -> o data pe secunda
            ParameterDescriptor(description='Frecventa de logare in Hz (trebuie > 0)')
        )
        self.declare_parameter(
            'mesaj',
            'Salut din parametri',
            ParameterDescriptor(description='Textul afisat la fiecare tic al timer-ului')
        )

        # === Citirea valorilor ===
        # ".value" intoarce valoarea propriu-zisa (float / str), nu obiectul Parameter.
        # Le pastram ca atribute pentru ca le folosim si modificam in callback-uri.
        self.rata = self.get_parameter('rata').value
        self.mesaj = self.get_parameter('mesaj').value
        self.contor = 0

        # === Callback de schimbare a parametrilor ===
        # Se apeleaza INAINTE ca valoarea sa fie aplicata, ori de cate ori cineva face
        # "ros2 param set ...". Aici validam si actualizam atributele. Il inregistram
        # devreme, dar dupa ce am citit valorile initiale.
        self.add_on_set_parameters_callback(self.cb_parametri)

        # Cream timer-ul pe baza ratei curente. Perioada = 1 / frecventa.
        self.timer = self.create_timer(1.0 / self.rata, self.cb_timer)

        self.get_logger().info(
            f'Nod pornit cu rata={self.rata} Hz si mesaj="{self.mesaj}"'
        )

    def cb_timer(self):
        # La fiecare tic afisam mesajul curent si un contor crescator,
        # ca sa vedem vizual cat de des ruleaza (deci si efectul ratei).
        self.contor += 1
        self.get_logger().info(f'[{self.contor}] {self.mesaj}')

    def cb_parametri(self, params):
        # Primim o LISTA de parametri care urmeaza sa fie setati (pot fi mai multi
        # deodata). O parcurgem si tratam fiecare dupa nume.
        for p in params:
            if p.name == 'rata':
                # Validare: o rata <= 0 ar da perioada infinita/negativa la timer,
                # deci REFUZAM si explicam motivul. ROS pastreaza valoarea veche.
                if p.value <= 0.0:
                    return SetParametersResult(
                        successful=False,
                        reason='rata trebuie sa fie strict pozitiva (> 0)'
                    )
                # Valoare buna: o memoram si RECREAM timer-ul ca sa aplicam noua frecventa.
                # Un timer existent nu isi schimba perioada "din mers", de aceea il
                # distrugem si cream altul nou.
                self.rata = p.value
                self.destroy_timer(self.timer)
                self.timer = self.create_timer(1.0 / self.rata, self.cb_timer)
                self.get_logger().info(f'Rata schimbata la {self.rata} Hz')
            elif p.name == 'mesaj':
                # Textul nu are nevoie de validare speciala; doar il actualizam.
                self.mesaj = p.value
                self.get_logger().info(f'Mesaj schimbat la "{self.mesaj}"')

        # Daca am ajuns aici, toate valorile au fost acceptate.
        return SetParametersResult(successful=True)


def main(args=None):
    rclpy.init(args=args)
    node = NodParametri()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
