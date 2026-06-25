"""Scripted mock sensor — replays a predefined sequence of telemetry events."""

from dataclasses import dataclass
from typing import List, Optional

from awas.sensors.base import Sensor
from awas.state_machine.telemetry import Telemetry


@dataclass
class Scene:
    """One step in a scripted scenario."""
    duration_sec: float
    speed_kmh: float = 0.0
    ignition_on: bool = True
    parking_brake: bool = False
    drowsiness_level: int = 0
    phone_usage: bool = False
    traffic_light_color: Optional[str] = None
    vehicle_ahead_distance_m: Optional[float] = None
    label: str = ""  # human-readable description of what's happening


class MockSensor(Sensor):
    """Plays back a list of Scenes as telemetry over time.

    Time advances each time `read()` is called by `tick_sec`. Useful for
    deterministic testing — no real clock involved.
    """

    def __init__(self, scenes: List[Scene], tick_sec: float = 1.0):
        self.scenes = scenes
        self.tick_sec = tick_sec
        self.now: float = 0.0

    def read(self) -> Telemetry:
        scene = self._scene_at(self.now)
        t = Telemetry(
            timestamp=self.now,
            drowsiness_level=scene.drowsiness_level,
            phone_usage=scene.phone_usage,
            speed_kmh=scene.speed_kmh,
            parking_brake=scene.parking_brake,
            ignition_on=scene.ignition_on,
            traffic_light_color=scene.traffic_light_color,
            vehicle_ahead_distance_m=scene.vehicle_ahead_distance_m,
        )
        self.now += self.tick_sec
        return t

    def current_label(self) -> str:
        # Look back one tick since read() already advanced
        return self._scene_at(self.now - self.tick_sec).label

    def is_done(self) -> bool:
        total = sum(s.duration_sec for s in self.scenes)
        return self.now > total

    def _scene_at(self, t: float) -> Scene:
        elapsed = 0.0
        for scene in self.scenes:
            if t < elapsed + scene.duration_sec:
                return scene
            elapsed += scene.duration_sec
        return self.scenes[-1]  # past the end, hold the last scene