# Copyright 2026 Alexandru Gheorghita
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
"""Run a fail-safe keyboard teleoperation node for the servo joint."""

import select
import signal
import sys
import termios
import threading
import time
import tty

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy
from rclpy.qos import HistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from servo_control.teleop_core import apply_key
from servo_control.teleop_core import initial_state
from servo_control.teleop_core import KEY_QUIT_CONTROL_C
from servo_control.teleop_core import stop_if_stale
from servo_control.teleop_core import TeleopConfig
from std_msgs.msg import Float64


DEFAULT_TOPIC = '/model/servo1/joint/shaft_joint/cmd_vel'
KEYBOARD_POLL_SECONDS = 0.1
ESCAPE_CONTINUATION_SECONDS = 0.02
STOP_REPETITIONS = 3
STOP_INTERVAL_SECONDS = 0.05


class TerminalReader:
    """Read individual keys while always restoring the terminal settings."""

    def __init__(self, stream):
        self._stream = stream
        self._settings = None

    def __enter__(self):
        if not self._stream.isatty():
            raise RuntimeError(
                'Intrarea standard nu este un terminal. Ruleaza servo_teleop '
                'intr-un terminal separat.'
            )

        self._settings = termios.tcgetattr(self._stream)
        tty.setcbreak(self._stream.fileno())
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._settings is not None:
            termios.tcsetattr(
                self._stream,
                termios.TCSADRAIN,
                self._settings,
            )

    def read_key(self, timeout=KEYBOARD_POLL_SECONDS):
        """Return one key sequence, or ``None`` when the timeout expires."""
        readable, _, _ = select.select([self._stream], [], [], timeout)
        if not readable:
            return None

        key = self._stream.read(1)
        if key == '':
            raise EOFError('Intrarea terminalului a fost inchisa.')

        if key == '\x1b':
            for _ in range(2):
                readable, _, _ = select.select(
                    [self._stream],
                    [],
                    [],
                    ESCAPE_CONTINUATION_SECONDS,
                )
                if not readable:
                    break
                key += self._stream.read(1)

        return key


class ServoTeleop(Node):
    """Publish bounded servo velocity commands from keyboard input."""

    def __init__(self):
        super().__init__('servo_teleop')

        self.declare_parameter('command_topic', DEFAULT_TOPIC)
        self.declare_parameter('publish_rate', 20.0)
        self.declare_parameter('initial_speed', 1.0)
        self.declare_parameter('speed_step', 0.5)
        self.declare_parameter('min_speed', 0.5)
        self.declare_parameter('max_speed', 10.0)
        self.declare_parameter('command_timeout', 0.75)

        command_topic = self.get_parameter('command_topic').value
        publish_rate = float(self.get_parameter('publish_rate').value)
        command_timeout = float(self.get_parameter('command_timeout').value)

        if not command_topic:
            raise ValueError('Parametrul command_topic nu poate fi gol.')
        if publish_rate <= 0.0:
            raise ValueError('Parametrul publish_rate trebuie sa fie pozitiv.')
        if command_timeout < 0.0:
            raise ValueError('Parametrul command_timeout nu poate fi negativ.')

        self._config = TeleopConfig(
            initial_speed=float(self.get_parameter('initial_speed').value),
            speed_step=float(self.get_parameter('speed_step').value),
            min_speed=float(self.get_parameter('min_speed').value),
            max_speed=float(self.get_parameter('max_speed').value),
        )
        self._command_timeout = command_timeout
        self._state = initial_state(self._config)
        self._state_lock = threading.Lock()
        self._last_command_time = time.monotonic()
        self._watchdog_reported = False

        command_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self._publisher = self.create_publisher(
            Float64,
            command_topic,
            command_qos,
        )
        self._timer = self.create_timer(
            1.0 / publish_rate,
            self.publish_velocity,
        )

        self.get_logger().info(
            f'Servo Teleop pornit pe {command_topic}; '
            f'watchdog={command_timeout:.2f} s'
        )

    def process_key(self, key):
        """Apply a key to the protected control state."""
        with self._state_lock:
            result = apply_key(self._state, key, self._config)
            if result.handled:
                self._state = result.state
                self._last_command_time = time.monotonic()
                self._watchdog_reported = False
            return result

    def publish_velocity(self):
        """Publish the latest command and apply the inactivity watchdog."""
        with self._state_lock:
            elapsed = time.monotonic() - self._last_command_time
            self._state, timed_out = stop_if_stale(
                self._state,
                elapsed,
                self._command_timeout,
            )
            velocity = self._state.velocity
            report_timeout = timed_out and not self._watchdog_reported
            if timed_out:
                self._watchdog_reported = True

        if report_timeout:
            self.get_logger().warning(
                'Watchdog: comanda a expirat; viteza a fost setata la zero.'
            )

        message = Float64()
        message.data = velocity
        self._publisher.publish(message)

    def publish_stop(self):
        """Publish zero repeatedly before shutting the node down."""
        with self._state_lock:
            self._state = apply_key(self._state, ' ', self._config).state

        for _ in range(STOP_REPETITIONS):
            self.publish_velocity()
            time.sleep(STOP_INTERVAL_SECONDS)

    def print_status(self):
        """Render the current speed and direction on one terminal line."""
        with self._state_lock:
            speed = self._state.speed
            velocity = self._state.velocity

        if velocity > 0.0:
            direction = 'ORAR >>>'
        elif velocity < 0.0:
            direction = '<<< ANTIORAR'
        else:
            direction = 'STOP'

        print(
            f'\r  Setare: {speed:.1f} rad/s | '
            f'Comanda: {abs(velocity):.1f} rad/s | '
            f'Directie: {direction}    ',
            end='',
            flush=True,
        )

    def run_keyboard(self, shutdown_event):
        """Read keys until quit, shutdown, or ROS context termination."""
        banner = f"""
+====================================================+
|             SERVO TELEOP - Tastatura              |
+====================================================+
|  sageata STANGA/DREAPTA  selecteaza sensul        |
|  sageata SUS/JOS         modifica viteza           |
|  SPATIU                  stop imediat              |
|  Q sau Ctrl-C            iesire                    |
+====================================================+
Tine apasata tasta de directie pentru miscare continua.
Watchdog-ul opreste comanda dupa {self._command_timeout:.2f} s fara input.
"""
        print(banner)

        with TerminalReader(sys.stdin) as terminal:
            while rclpy.ok() and not shutdown_event.is_set():
                key = terminal.read_key()
                if key is None:
                    continue

                result = self.process_key(key)
                if result.handled:
                    self.print_status()
                if result.should_quit or key == KEY_QUIT_CONTROL_C:
                    print('\nOprire solicitata.')
                    return


def main(args=None):
    """Run the node and perform an ordered, fail-safe shutdown."""
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)

    node = None
    executor = None
    spin_thread = None
    spin_errors = []
    shutdown_event = threading.Event()
    previous_sigterm_handler = signal.getsignal(signal.SIGTERM)

    def request_shutdown(_signum, _frame):
        shutdown_event.set()

    signal.signal(signal.SIGTERM, request_shutdown)
    exit_code = 0

    try:
        node = ServoTeleop()
        executor = SingleThreadedExecutor()
        executor.add_node(node)

        def spin():
            try:
                executor.spin()
            except Exception as error:  # pragma: no cover - executor safeguard
                spin_errors.append(error)
                shutdown_event.set()

        spin_thread = threading.Thread(target=spin, name='ros-spin')
        spin_thread.start()
        node.run_keyboard(shutdown_event)

        if spin_errors:
            raise spin_errors[0]
    except KeyboardInterrupt:
        print('\nCtrl-C receptionat; servoul este oprit.')
    except (EOFError, RuntimeError, ValueError) as error:
        print(f'\nEroare servo_teleop: {error}', file=sys.stderr)
        exit_code = 1
    finally:
        if node is not None and rclpy.ok():
            node.publish_stop()
        if executor is not None:
            executor.shutdown(timeout_sec=1.0)
        if spin_thread is not None:
            spin_thread.join(timeout=1.0)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        signal.signal(signal.SIGTERM, previous_sigterm_handler)

    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
