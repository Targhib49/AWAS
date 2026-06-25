"""Sensor-reading snapshot — single source of truth for current world state."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Telemetry:
    """A snapshot of all sensor readings at one point in time.

    Sensors update fields on this object; the state machine reads it.
    Your trained drowsiness model's job is to produce `drowsiness_level`
    (an int 0-4). Everything else is from other sensors or for diagnostics.
    """

    # Timing
    timestamp: float = 0.0

    # Driver state (from camera + drowsiness model)
    drowsiness_level: int = 0       # 0=alert, 1=mild, 2=moderate, 3=severe, 4=critical
    phone_usage: bool = False
    eye_aspect_ratio: float = 0.3   # diagnostic only; raw EAR
    head_pitch_deg: float = 0.0     # diagnostic only; head-down angle

    # Vehicle state (from OBD-II)
    speed_kmh: float = 0.0
    parking_brake: bool = False
    ignition_on: bool = False

    # Road state (from dashcam)
    traffic_light_color: Optional[str] = None       # "red" | "yellow" | "green" | None
    vehicle_ahead_distance_m: Optional[float] = None

    # GPS
    latitude: float = 0.0
    longitude: float = 0.0