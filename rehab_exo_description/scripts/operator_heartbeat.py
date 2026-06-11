#!/usr/bin/env python3
"""
operator_heartbeat.py — Statia operatorului pentru telereabilitare (rehab_exo).

Ruleaza PE PARTEA OPERATORULUI (langa operator_panel.py) si masoara continuu
calitatea legaturii catre robot, pe acelasi mecanism folosit la rontul de drone
(GCS): heartbeat numerotat + echo intors de safety_supervisor.

  operator_heartbeat  --/telerehab/heartbeat-->  safety_supervisor (pe robot)
  operator_heartbeat  <--/telerehab/heartbeat_echo--  safety_supervisor

Din perechea trimis/intors rezulta:
  * RTT (ultimul si media mobila exponentiala), in milisecunde;
  * pierderea de pachete in fereastra recenta (ecouri care nu s-au mai intors);
  * starea legaturii: OK / DEGRADED / CRITICAL (praguri configurabile).

Rezultatele se publica pe /telerehab/network_health (String, "cheie=valoare ...")
si, optional, se scriu intr-un CSV in ~/rehab_data/ — exact datele de care ai
nevoie pentru graficele comparative rmw_zenoh vs CycloneDDS din articol.

Parametri:
  hb_rate        frecventa heartbeat, Hz                     (implicit 20)
  loss_timeout   dupa cate secunde un echo lipsa = pierdut    (implicit 1.0)
  window         cate heartbeat-uri intra in fereastra de pierdere (implicit 100)
  rtt_warn       prag RTT pentru DEGRADED, ms                 (implicit 150)
  rtt_crit       prag RTT pentru CRITICAL, ms                 (implicit 400)
  loss_warn      prag pierdere pentru DEGRADED, %             (implicit 5)
  loss_crit      prag pierdere pentru CRITICAL, %             (implicit 20)
  log_csv        true => scrie ~/rehab_data/network_health_<timestamp>.csv
  label          eticheta scrisa in CSV (ex. "zenoh_loss15") pentru experimente
"""

import csv
import os
import time
from collections import OrderedDict, deque

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class OperatorHeartbeat(Node):
    def __init__(self):
        super().__init__("operator_heartbeat")

        self.declare_parameter("hb_rate", 20.0)
        self.declare_parameter("loss_timeout", 1.0)
        self.declare_parameter("window", 100)
        self.declare_parameter("rtt_warn", 150.0)
        self.declare_parameter("rtt_crit", 400.0)
        self.declare_parameter("loss_warn", 5.0)
        self.declare_parameter("loss_crit", 20.0)
        self.declare_parameter("log_csv", True)
        self.declare_parameter("label", os.environ.get("RMW_IMPLEMENTATION", "necunoscut"))

        self.loss_timeout = float(self.get_parameter("loss_timeout").value)
        self.window = int(self.get_parameter("window").value)
        self.rtt_warn = float(self.get_parameter("rtt_warn").value)
        self.rtt_crit = float(self.get_parameter("rtt_crit").value)
        self.loss_warn = float(self.get_parameter("loss_warn").value)
        self.loss_crit = float(self.get_parameter("loss_crit").value)
        self.label = str(self.get_parameter("label").value)

        # Heartbeat-uri in zbor: seq -> momentul trimiterii (monotonic).
        self.in_flight: "OrderedDict[int, float]" = OrderedDict()
        self.results = deque(maxlen=self.window)  # 1 = raspuns, 0 = pierdut
        self.seq = 0
        self.rtt_last_ms = float("nan")
        self.rtt_ema_ms = None

        self.pub_hb = self.create_publisher(String, "/telerehab/heartbeat", 20)
        self.pub_health = self.create_publisher(String, "/telerehab/network_health", 5)
        self.sub_echo = self.create_subscription(
            String, "/telerehab/heartbeat_echo", self._on_echo, 20)

        hb_period = 1.0 / float(self.get_parameter("hb_rate").value)
        self.create_timer(hb_period, self._send_hb)
        self.create_timer(0.5, self._report)

        self.csv_writer = None
        if bool(self.get_parameter("log_csv").value):
            self._open_csv()

        self.get_logger().info(
            f"heartbeat pornit ({1.0/hb_period:.0f} Hz) | eticheta='{self.label}' | "
            f"praguri RTT {self.rtt_warn:.0f}/{self.rtt_crit:.0f} ms, "
            f"pierdere {self.loss_warn:.0f}/{self.loss_crit:.0f} %")

    # ------------------------------------------------------------------ CSV
    def _open_csv(self):
        out_dir = os.path.expanduser("~/rehab_data")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir,
                            f"network_health_{time.strftime('%Y%m%d_%H%M%S')}.csv")
        self._csv_file = open(path, "w", newline="")
        self.csv_writer = csv.writer(self._csv_file)
        self.csv_writer.writerow(
            ["t_unix", "eticheta", "rtt_last_ms", "rtt_ema_ms", "pierdere_pct", "stare"])
        self.get_logger().info(f"jurnal CSV: {path}")

    # ------------------------------------------------------------- heartbeat
    def _send_hb(self):
        now = time.monotonic()
        self.seq += 1
        self.in_flight[self.seq] = now
        self.pub_hb.publish(String(data=f"{self.seq};{time.time_ns()}"))

        # Heartbeat-urile mai vechi decat loss_timeout se considera pierdute.
        expired = [s for s, t in self.in_flight.items() if now - t > self.loss_timeout]
        for s in expired:
            self.in_flight.pop(s, None)
            self.results.append(0)

    def _on_echo(self, msg: String):
        try:
            seq = int(msg.data.split(";", 1)[0])
        except (ValueError, IndexError):
            return
        t_sent = self.in_flight.pop(seq, None)
        if t_sent is None:
            return  # a sosit dupa expirare sau e duplicat
        rtt_ms = (time.monotonic() - t_sent) * 1000.0
        self.rtt_last_ms = rtt_ms
        self.rtt_ema_ms = (rtt_ms if self.rtt_ema_ms is None
                           else 0.85 * self.rtt_ema_ms + 0.15 * rtt_ms)
        self.results.append(1)

    # --------------------------------------------------------------- raport
    def _loss_pct(self):
        if not self.results:
            return 0.0
        return 100.0 * (1.0 - sum(self.results) / len(self.results))

    def _state(self, rtt_ms, loss):
        if (rtt_ms == rtt_ms and rtt_ms > self.rtt_crit) or loss > self.loss_crit:
            return "CRITICAL"
        if (rtt_ms == rtt_ms and rtt_ms > self.rtt_warn) or loss > self.loss_warn:
            return "DEGRADED"
        return "OK"

    def _report(self):
        loss = self._loss_pct()
        ema = self.rtt_ema_ms if self.rtt_ema_ms is not None else float("nan")
        state = self._state(ema, loss)
        txt = (f"rtt_ms={self.rtt_last_ms:.1f} rtt_ema_ms={ema:.1f} "
               f"pierdere={loss:.1f}% stare={state} eticheta={self.label}")
        self.pub_health.publish(String(data=txt))
        if self.csv_writer is not None:
            self.csv_writer.writerow([f"{time.time():.3f}", self.label,
                                      f"{self.rtt_last_ms:.2f}", f"{ema:.2f}",
                                      f"{loss:.2f}", state])
            self._csv_file.flush()
        if state != "OK":
            self.get_logger().warning(txt)


def main():
    rclpy.init()
    node = OperatorHeartbeat()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.csv_writer is not None:
            node._csv_file.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
