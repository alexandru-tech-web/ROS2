import math

import rclpy
from rclpy.node import Node
# Float64 e cel mai simplu mesaj numeric standard: un singur camp "data" de tip
# float64. Il alegem ca senzorul sa publice un canal "brut" de valori, exact
# cum ar trimite un termometru real: doar numarul, fara interpretare.
from std_msgs.msg import Float64


class SenzorTemperatura(Node):
    """Senzor SIMULAT de temperatura (capstone M13).

    De ce simulat si DETERMINIST (fara random)? Pentru ca un curs trebuie sa fie
    reproductibil: oricine ruleaza nodul vede aceeasi unda, deci aceleasi treceri
    NORMAL -> ATENTIE -> CRITIC la monitor. Folosim o sinusoida:
        valoare = valoare_baza + amplitudine * sin(t)
    care urca si coboara lin prin praguri, perfect pentru demonstratie.
    """

    def __init__(self):
        super().__init__('senzor_temperatura')

        # === Parametri (recapitulare M4) ===
        # Declaram explicit fiecare parametru (rclpy in Jazzy nu citeste parametri
        # nedeclarati). Tipul e fixat de valoarea implicita: 2.0 / 25.0 / 20.0 sunt
        # float, deci toti trei sunt parametri float.
        self.declare_parameter('rata', 2.0)            # Hz: de cate ori pe secunda publicam
        self.declare_parameter('valoare_baza', 25.0)   # grade: centrul oscilatiei
        self.declare_parameter('amplitudine', 20.0)    # grade: cat urca/coboara fata de baza

        # Citim valorile o data, la pornire. ".value" da numarul, nu obiectul Parameter.
        self.rata = self.get_parameter('rata').value
        self.valoare_baza = self.get_parameter('valoare_baza').value
        self.amplitudine = self.get_parameter('amplitudine').value

        # Publisher pe /senzor/temperatura. Coada 10 e suficienta: monitorul
        # citeste mereu ultima valoare, nu ne intereseaza istoricul.
        self.pub = self.create_publisher(Float64, '/senzor/temperatura', 10)

        # === Contor determinist ===
        # NU folosim ceasul real (time.time()) ci un contor pe care il inmultim cu
        # un "pas". Asa unda nu depinde de cand pornesti nodul: mereu incepe din
        # t=0 si urca la fel. "contor" creste cu 1 la fiecare tic de timer.
        self.contor = 0
        # Pasul in "timp" pe tic. Il legam de rata ca unda sa aiba aceeasi forma
        # indiferent de frecventa de publicare: la rata mare, mai multe esantioane
        # pe aceeasi perioada de sinusoida, nu o unda mai rapida.
        self.pas = 1.0 / self.rata

        # Timer pe baza ratei: perioada = 1 / frecventa. La 2.0 Hz -> la 0.5s.
        self.timer = self.create_timer(1.0 / self.rata, self.cb_timer)

        self.get_logger().info(
            f'Senzor pornit: rata={self.rata} Hz, valoare_baza={self.valoare_baza}, '
            f'amplitudine={self.amplitudine}. Public pe /senzor/temperatura...'
        )

    def cb_timer(self):
        # "t" creste lin cu fiecare tic; sin(t) oscileaza intre -1 si 1, deci
        # valoarea oscileaza intre (baza - amplitudine) si (baza + amplitudine).
        # Cu baza 25 si amplitudine 20: intre 5 si 45 -> trece prin pragul de
        # ATENTIE (30) la fiecare urcare/coborare. Mareste amplitudinea ca sa
        # atingi si CRITIC (50).
        t = self.contor * self.pas
        valoare = self.valoare_baza + self.amplitudine * math.sin(t)

        # Construim mesajul GOL si ii punem doar campul "data".
        msg = Float64()
        msg.data = valoare
        self.pub.publish(msg)

        # Logam ce am publicat (rotunjit la afisare, valoarea trimisa ramane exacta).
        self.get_logger().info(f'Temperatura publicata: {valoare:.2f}')

        # Avansam contorul DUPA publicare, ca primul esantion sa fie la t=0
        # (sin(0)=0 -> exact valoarea de baza), un punct de plecare clar.
        self.contor += 1


def main(args=None):
    rclpy.init(args=args)
    node = SenzorTemperatura()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
