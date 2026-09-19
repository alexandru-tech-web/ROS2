# Copyright 2026 Alexandru Gheorghita
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
"""Pure state transitions for servo keyboard teleoperation."""

from dataclasses import dataclass
from math import isfinite


KEY_RIGHT = '\x1b[C'
KEY_LEFT = '\x1b[D'
KEY_UP = '\x1b[A'
KEY_DOWN = '\x1b[B'
KEY_STOP = ' '
KEY_QUIT_CONTROL_C = '\x03'


@dataclass(frozen=True)
class TeleopConfig:
    """Bounds and increments used by the teleoperation state machine."""

    initial_speed: float = 1.0
    speed_step: float = 0.5
    min_speed: float = 0.5
    max_speed: float = 10.0

    def __post_init__(self):
        values = (
            self.initial_speed,
            self.speed_step,
            self.min_speed,
            self.max_speed,
        )
        if not all(isfinite(value) for value in values):
            raise ValueError('Parametrii de viteza trebuie sa fie finiti.')
        if self.min_speed <= 0.0:
            raise ValueError('min_speed trebuie sa fie pozitiv.')
        if self.max_speed < self.min_speed:
            raise ValueError('max_speed trebuie sa fie >= min_speed.')
        if not self.min_speed <= self.initial_speed <= self.max_speed:
            raise ValueError(
                'initial_speed trebuie sa fie intre min_speed si max_speed.'
            )
        if self.speed_step <= 0.0:
            raise ValueError('speed_step trebuie sa fie pozitiv.')


@dataclass(frozen=True)
class TeleopState:
    """Current selected speed and signed command velocity."""

    speed: float
    velocity: float = 0.0


@dataclass(frozen=True)
class KeyResult:
    """Result of applying one keyboard input."""

    state: TeleopState
    handled: bool = False
    should_quit: bool = False


def initial_state(config):
    """Create a stopped state from a validated configuration."""
    return TeleopState(speed=config.initial_speed)


def apply_key(state, key, config):
    """Return the deterministic state transition for one key sequence."""
    if key == KEY_RIGHT:
        return KeyResult(
            TeleopState(speed=state.speed, velocity=state.speed),
            handled=True,
        )
    if key == KEY_LEFT:
        return KeyResult(
            TeleopState(speed=state.speed, velocity=-state.speed),
            handled=True,
        )
    if key == KEY_UP:
        speed = min(state.speed + config.speed_step, config.max_speed)
        velocity = _velocity_with_preserved_direction(state.velocity, speed)
        return KeyResult(
            TeleopState(speed=speed, velocity=velocity),
            handled=True,
        )
    if key == KEY_DOWN:
        speed = max(state.speed - config.speed_step, config.min_speed)
        velocity = _velocity_with_preserved_direction(state.velocity, speed)
        return KeyResult(
            TeleopState(speed=speed, velocity=velocity),
            handled=True,
        )
    if key == KEY_STOP:
        return KeyResult(
            TeleopState(speed=state.speed, velocity=0.0),
            handled=True,
        )
    if key in ('q', 'Q', KEY_QUIT_CONTROL_C):
        return KeyResult(
            TeleopState(speed=state.speed, velocity=0.0),
            handled=True,
            should_quit=True,
        )
    return KeyResult(state)


def stop_if_stale(state, elapsed, command_timeout):
    """Stop a moving command once its inactivity timeout has elapsed."""
    if (
        command_timeout > 0.0
        and state.velocity != 0.0
        and elapsed >= command_timeout
    ):
        return TeleopState(speed=state.speed, velocity=0.0), True
    return state, False


def _velocity_with_preserved_direction(velocity, speed):
    """Apply a new magnitude while retaining motion direction."""
    if velocity > 0.0:
        return speed
    if velocity < 0.0:
        return -speed
    return 0.0
