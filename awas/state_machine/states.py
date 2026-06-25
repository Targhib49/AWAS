"""Operational driving states for the AWAS state machine."""

from enum import Enum


class DrivingState(Enum):
    """High-level operational state of the vehicle/system.

    Renamed from `SystemState` in the design docs to avoid clashing
    with the sensor-reading dataclass `Telemetry`.
    """

    SHUTDOWN = "shutdown"
    PARKED = "parked"
    STOPPED_AT_LIGHT = "stopped_at_light"
    TRAFFIC_JAM = "traffic_jam"
    MOVING = "moving"