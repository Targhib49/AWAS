"""State machine controller — pure logic, no I/O."""

from typing import List

from .actions import Action, ActionType
from .context import StateContext
from .states import DrivingState
from .telemetry import Telemetry


# --- Tunable thresholds (move to config.yaml later) ---
STOPPED_SPEED_KMH = 5.0           # below this = "stopped"
MOVING_SPEED_KMH = 5.0            # above this = "moving" again
TRAFFIC_JAM_AFTER_SEC = 30.0      # stopped this long w/o light → jam
LIGHT_TO_JAM_SEC = 120.0          # stuck at light this long → jam
SHUTDOWN_AFTER_OFF_SEC = 30.0     # ignition off this long → shutdown
INTERVENTION_COOLDOWN_SEC = 30.0  # min gap between drowsiness interventions
ALERT_COOLDOWN_SEC = 5.0


class StateMachine:
    """Decides DrivingState transitions and emits Actions.

    Call `update(telemetry)` once per sensor tick. Returns a list of Actions
    the executor should perform (speak, alert, log). No side effects here.
    """

    def __init__(self, initial_state: DrivingState = DrivingState.PARKED):
        self.state = initial_state
        self.ctx = StateContext()

    # -------- public API --------

    def update(self, t: Telemetry) -> List[Action]:
        """Process one telemetry snapshot. Return actions to execute."""
        self._update_timers(t)

        next_state = self._next_state(t)
        if next_state != self.state:
            actions = self._on_exit(self.state, t)
            self.state = next_state
            self.ctx.state_entered_at = t.timestamp
            actions += self._on_enter(next_state, t)
            return actions

        return self._in_state_actions(t)
    
    def _cooldown_ok(self, last_at, now: float, cooldown_sec: float) -> bool:
        """True if enough time has passed since `last_at` (or it's never fired)."""
        if last_at is None:
            return True
        return now - last_at >= cooldown_sec

    # -------- timer bookkeeping --------

    def _update_timers(self, t: Telemetry) -> None:
        # Track "speed dropped below threshold" timer
        if t.speed_kmh < STOPPED_SPEED_KMH:
            if self.ctx.speed_dropped_at is None:
                self.ctx.speed_dropped_at = t.timestamp
        else:
            self.ctx.speed_dropped_at = None

        # Track "ignition off" timer
        if not t.ignition_on:
            if self.ctx.ignition_off_at is None:
                self.ctx.ignition_off_at = t.timestamp
        else:
            self.ctx.ignition_off_at = None

    # -------- transition logic --------

    def _next_state(self, t: Telemetry) -> DrivingState:
        # SHUTDOWN takes priority — applies from any state
        if self.ctx.ignition_off_at is not None:
            off_for = t.timestamp - self.ctx.ignition_off_at
            if off_for >= SHUTDOWN_AFTER_OFF_SEC:
                return DrivingState.SHUTDOWN

        if self.state == DrivingState.SHUTDOWN:
            if t.ignition_on:
                return DrivingState.PARKED  # warm up before MOVING

        elif self.state == DrivingState.PARKED:
            if t.ignition_on and not t.parking_brake and t.speed_kmh > 0:
                return DrivingState.MOVING

        elif self.state == DrivingState.MOVING:
            if t.parking_brake and t.speed_kmh == 0:
                return DrivingState.PARKED
            if t.speed_kmh < STOPPED_SPEED_KMH:
                if t.traffic_light_color in ("red", "yellow"):
                    return DrivingState.STOPPED_AT_LIGHT
                if self._stopped_for(t) >= TRAFFIC_JAM_AFTER_SEC:
                    return DrivingState.TRAFFIC_JAM

        elif self.state == DrivingState.STOPPED_AT_LIGHT:
            if t.speed_kmh > MOVING_SPEED_KMH:
                return DrivingState.MOVING
            if self._time_in_state(t) >= LIGHT_TO_JAM_SEC:
                return DrivingState.TRAFFIC_JAM

        elif self.state == DrivingState.TRAFFIC_JAM:
            if t.speed_kmh > MOVING_SPEED_KMH:
                return DrivingState.MOVING
            if t.traffic_light_color in ("red", "yellow"):
                return DrivingState.STOPPED_AT_LIGHT

        return self.state

    # -------- per-state in-state actions --------

    def _in_state_actions(self, t: Telemetry) -> List[Action]:
        if self.state == DrivingState.MOVING:
            return self._moving_actions(t)
        if self.state == DrivingState.STOPPED_AT_LIGHT:
            return self._light_actions(t)
        if self.state == DrivingState.TRAFFIC_JAM:
            return self._jam_actions(t)
        return []

    def _moving_actions(self, t: Telemetry) -> List[Action]:
        actions: List[Action] = []

        # Drowsiness intervention (rate-limited)
        if t.drowsiness_level > 0:
            if self._cooldown_ok(self.ctx.last_intervention_at, t.timestamp, INTERVENTION_COOLDOWN_SEC):
                actions.append(Action(
                    type=ActionType.SPEAK,
                    urgency=t.drowsiness_level,
                    context="moving_drowsy",
                ))
                self.ctx.last_intervention_at = t.timestamp

        if t.phone_usage:
            if self._cooldown_ok(self.ctx.last_alert_at, t.timestamp, ALERT_COOLDOWN_SEC):
                actions.append(Action(
                    type=ActionType.ALERT,
                    urgency=2,
                    message="Eyes on the road, please.",
                ))
                self.ctx.last_alert_at = t.timestamp

        return actions

    def _light_actions(self, t: Telemetry) -> List[Action]:
        if t.traffic_light_color == "green" and t.drowsiness_level >= 3:
            if self._cooldown_ok(self.ctx.last_alert_at, t.timestamp, ALERT_COOLDOWN_SEC):
                self.ctx.last_alert_at = t.timestamp
                return [Action(
                    type=ActionType.ALERT,
                    urgency=3,
                    message="Light is green! Please wake up!",
                )]
        return []

    def _jam_actions(self, t: Telemetry) -> List[Action]:
        actions: List[Action] = []
        if t.vehicle_ahead_distance_m is not None and t.vehicle_ahead_distance_m > 5.0:
            actions.append(Action(
                type=ActionType.ALERT,
                urgency=1,
                message="Traffic is moving.",
            ))
        return actions

    # -------- enter/exit hooks --------

    def _on_enter(self, state: DrivingState, t: Telemetry) -> List[Action]:
        return [Action(
            type=ActionType.LOG,
            message=f"Entered {state.value} at t={t.timestamp:.2f}",
        )]

    def _on_exit(self, state: DrivingState, t: Telemetry) -> List[Action]:
        return []

    # -------- helpers --------

    def _time_in_state(self, t: Telemetry) -> float:
        return t.timestamp - self.ctx.state_entered_at

    def _stopped_for(self, t: Telemetry) -> float:
        if self.ctx.speed_dropped_at is None:
            return 0.0
        return t.timestamp - self.ctx.speed_dropped_at