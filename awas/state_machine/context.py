"""Internal bookkeeping for the state machine — timers and counters."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StateContext:
    """Timers and history the state machine uses to make decisions.

    These are *internal* to the state machine — not sensor data, not actions.
    They exist because transitions like "stopped for 30 seconds → traffic jam"
    require tracking when things started.
    """

    # When we entered the current DrivingState
    state_entered_at: float = 0.0

    # When speed first dropped below the "stopped" threshold (None = currently moving)
    speed_dropped_at: Optional[float] = None

    # When ignition turned off (None = currently on)
    ignition_off_at: Optional[float] = None

    # Last time we triggered a drowsiness intervention (for rate limiting)
    last_intervention_at: Optional[float] = None   
    last_alert_at: Optional[float] = None          