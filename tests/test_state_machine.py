"""State machine tests — fast, deterministic, no I/O.

Run from project root:
    pytest tests/test_state_machine.py -v
"""

from awas.state_machine.actions import ActionType
from awas.state_machine.controller import StateMachine
from awas.state_machine.states import DrivingState
from awas.state_machine.telemetry import Telemetry


def drive(sm, **kwargs):
    """Build a Telemetry from kwargs, feed it to the state machine, return actions."""
    return sm.update(Telemetry(**kwargs))


def has_type(actions, action_type):
    return any(a.type == action_type for a in actions)


# ---------- basic state transitions ----------

class TestBasicTransitions:
    def test_parked_to_moving(self):
        sm = StateMachine()
        assert sm.state == DrivingState.PARKED
        drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=30.0)
        assert sm.state == DrivingState.MOVING

    def test_parked_stays_parked_with_brake(self):
        sm = StateMachine()
        drive(sm, timestamp=1.0, ignition_on=True, parking_brake=True)
        assert sm.state == DrivingState.PARKED

    def test_moving_to_stopped_at_light_on_red(self):
        sm = StateMachine()
        drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=30.0)
        drive(sm, timestamp=2.0, ignition_on=True, speed_kmh=2.0,
              traffic_light_color="red")
        assert sm.state == DrivingState.STOPPED_AT_LIGHT

    def test_stopped_at_light_to_moving_on_acceleration(self):
        sm = StateMachine(initial_state=DrivingState.STOPPED_AT_LIGHT)
        drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=20.0,
              traffic_light_color="green")
        assert sm.state == DrivingState.MOVING

    def test_moving_to_traffic_jam_after_30s_stopped(self):
        sm = StateMachine()
        drive(sm, timestamp=0.0, ignition_on=True, speed_kmh=30.0)
        drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=0.0)
        assert sm.state == DrivingState.MOVING  # not yet
        drive(sm, timestamp=29.0, ignition_on=True, speed_kmh=0.0)
        assert sm.state == DrivingState.MOVING  # still not
        drive(sm, timestamp=32.0, ignition_on=True, speed_kmh=0.0)
        assert sm.state == DrivingState.TRAFFIC_JAM

    def test_traffic_jam_to_moving_on_acceleration(self):
        sm = StateMachine(initial_state=DrivingState.TRAFFIC_JAM)
        drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=20.0)
        assert sm.state == DrivingState.MOVING

    def test_moving_to_parked_on_brake(self):
        sm = StateMachine()
        drive(sm, timestamp=0.0, ignition_on=True, speed_kmh=30.0)
        drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=0.0,
              parking_brake=True)
        assert sm.state == DrivingState.PARKED


# ---------- shutdown ----------

class TestShutdown:
    def test_ignition_off_30s_triggers_shutdown(self):
        sm = StateMachine()
        drive(sm, timestamp=0.0, ignition_on=True, speed_kmh=30.0)
        drive(sm, timestamp=10.0, ignition_on=False)
        assert sm.state == DrivingState.MOVING  # not yet
        drive(sm, timestamp=45.0, ignition_on=False)
        assert sm.state == DrivingState.SHUTDOWN

    def test_shutdown_to_parked_on_ignition_on(self):
        sm = StateMachine(initial_state=DrivingState.SHUTDOWN)
        drive(sm, timestamp=1.0, ignition_on=True, parking_brake=True)
        assert sm.state == DrivingState.PARKED


# ---------- drowsiness intervention ----------

class TestDrowsinessIntervention:
    def test_drowsy_emits_speak(self):
        sm = StateMachine()
        drive(sm, timestamp=0.0, ignition_on=True, speed_kmh=30.0)
        actions = drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=30.0,
                        drowsiness_level=2)
        speak = [a for a in actions if a.type == ActionType.SPEAK]
        assert len(speak) == 1
        assert speak[0].urgency == 2
        assert speak[0].context == "moving_drowsy"

    def test_drowsiness_rate_limited(self):
        sm = StateMachine()
        drive(sm, timestamp=0.0, ignition_on=True, speed_kmh=30.0)
        a1 = drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=30.0,
                   drowsiness_level=2)
        assert has_type(a1, ActionType.SPEAK)
        # Same conditions a few seconds later — silent (cooldown)
        a2 = drive(sm, timestamp=5.0, ignition_on=True, speed_kmh=30.0,
                   drowsiness_level=2)
        assert not has_type(a2, ActionType.SPEAK)
        # Past 30s cooldown — fires again
        a3 = drive(sm, timestamp=32.0, ignition_on=True, speed_kmh=30.0,
                   drowsiness_level=2)
        assert has_type(a3, ActionType.SPEAK)


# ---------- green-light override ----------

class TestGreenLightOverride:
    def test_green_with_severe_drowsy_alerts(self):
        sm = StateMachine(initial_state=DrivingState.STOPPED_AT_LIGHT)
        actions = drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=2.0,
                        traffic_light_color="green", drowsiness_level=3)
        alerts = [a for a in actions if a.type == ActionType.ALERT]
        assert len(alerts) == 1
        assert "green" in alerts[0].message.lower()

    def test_green_with_mild_drowsy_does_not_alert(self):
        sm = StateMachine(initial_state=DrivingState.STOPPED_AT_LIGHT)
        actions = drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=2.0,
                        traffic_light_color="green", drowsiness_level=1)
        assert not has_type(actions, ActionType.ALERT)

    def test_green_alert_cooldown(self):
        """The bug from the demo run: should not fire every tick."""
        sm = StateMachine(initial_state=DrivingState.STOPPED_AT_LIGHT)
        a1 = drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=2.0,
                   traffic_light_color="green", drowsiness_level=3)
        assert has_type(a1, ActionType.ALERT)
        a2 = drive(sm, timestamp=2.0, ignition_on=True, speed_kmh=2.0,
                   traffic_light_color="green", drowsiness_level=3)
        assert not has_type(a2, ActionType.ALERT)
        a3 = drive(sm, timestamp=7.0, ignition_on=True, speed_kmh=2.0,
                   traffic_light_color="green", drowsiness_level=3)
        assert has_type(a3, ActionType.ALERT)


# ---------- phone usage ----------

class TestPhoneUsage:
    def test_phone_usage_emits_alert(self):
        sm = StateMachine()
        drive(sm, timestamp=0.0, ignition_on=True, speed_kmh=30.0)
        actions = drive(sm, timestamp=1.0, ignition_on=True, speed_kmh=30.0,
                        phone_usage=True)
        assert has_type(actions, ActionType.ALERT)