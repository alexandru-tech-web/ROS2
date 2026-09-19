# Copyright 2026 Alexandru Gheorghita
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
"""Unit tests for the ROS-independent teleoperation state machine."""

import pytest

from servo_control.teleop_core import apply_key
from servo_control.teleop_core import initial_state
from servo_control.teleop_core import KEY_DOWN
from servo_control.teleop_core import KEY_LEFT
from servo_control.teleop_core import KEY_RIGHT
from servo_control.teleop_core import KEY_UP
from servo_control.teleop_core import stop_if_stale
from servo_control.teleop_core import TeleopConfig
from servo_control.teleop_core import TeleopState


@pytest.fixture
def config():
    """Provide compact limits that are easy to exercise."""
    return TeleopConfig(
        initial_speed=1.0,
        speed_step=0.5,
        min_speed=0.5,
        max_speed=2.0,
    )


def test_direction_keys_apply_the_selected_speed(config):
    state = initial_state(config)

    clockwise = apply_key(state, KEY_RIGHT, config)
    anticlockwise = apply_key(clockwise.state, KEY_LEFT, config)

    assert clockwise.state.velocity == 1.0
    assert anticlockwise.state.velocity == -1.0
    assert clockwise.handled
    assert anticlockwise.handled


def test_speed_changes_preserve_direction_and_clamp(config):
    state = TeleopState(speed=1.5, velocity=-1.5)

    state = apply_key(state, KEY_UP, config).state
    state = apply_key(state, KEY_UP, config).state
    assert state == TeleopState(speed=2.0, velocity=-2.0)

    for _ in range(10):
        state = apply_key(state, KEY_DOWN, config).state
    assert state == TeleopState(speed=0.5, velocity=-0.5)


def test_speed_can_change_while_stopped(config):
    state = initial_state(config)

    state = apply_key(state, KEY_UP, config).state

    assert state == TeleopState(speed=1.5, velocity=0.0)


@pytest.mark.parametrize('key', [' ', 'q', 'Q', '\x03'])
def test_stop_and_quit_keys_always_zero_velocity(config, key):
    moving = TeleopState(speed=1.5, velocity=1.5)

    result = apply_key(moving, key, config)

    assert result.state.velocity == 0.0
    assert result.handled
    assert result.should_quit is (key != ' ')


def test_unknown_key_does_not_refresh_command(config):
    state = TeleopState(speed=1.0, velocity=1.0)

    result = apply_key(state, 'x', config)

    assert result.state is state
    assert not result.handled


def test_watchdog_stops_only_stale_motion():
    moving = TeleopState(speed=1.0, velocity=1.0)

    fresh, fresh_timed_out = stop_if_stale(moving, 0.74, 0.75)
    stale, stale_timed_out = stop_if_stale(moving, 0.75, 0.75)
    disabled, disabled_timed_out = stop_if_stale(moving, 100.0, 0.0)

    assert fresh is moving
    assert not fresh_timed_out
    assert stale == TeleopState(speed=1.0, velocity=0.0)
    assert stale_timed_out
    assert disabled is moving
    assert not disabled_timed_out


@pytest.mark.parametrize(
    'overrides',
    [
        {'min_speed': 0.0},
        {'min_speed': 2.0, 'max_speed': 1.0},
        {'initial_speed': 11.0},
        {'speed_step': 0.0},
        {'max_speed': float('inf')},
    ],
)
def test_invalid_configuration_is_rejected(overrides):
    with pytest.raises(ValueError):
        TeleopConfig(**overrides)
