"""Run the state machine against a scripted drive and print what happens.

Run from project root:
    python -m scripts.demo_state_machine
"""

from awas.sensors.mock import MockSensor, Scene
from awas.state_machine.controller import StateMachine
from awas.state_machine.states import DrivingState


def build_scenario() -> list[Scene]:
    """A simulated drive: start parked, drive, hit a red light, drive drowsy,
    get stuck in a jam, then park."""
    return [
        Scene(duration_sec=3,  label="parked, engine off",
              ignition_on=False, parking_brake=True),

        Scene(duration_sec=5,  label="engine on, brake released, starting to drive",
              speed_kmh=20, parking_brake=False),

        Scene(duration_sec=10, label="cruising on the highway",
              speed_kmh=80),

        Scene(duration_sec=8,  label="approaching red light — slowing",
              speed_kmh=3, traffic_light_color="red"),

        Scene(duration_sec=4,  label="light turns green — driver still drowsy!",
              speed_kmh=2, traffic_light_color="green", drowsiness_level=3),

        Scene(duration_sec=15, label="driving with mild drowsiness",
              speed_kmh=60, drowsiness_level=1),

        Scene(duration_sec=40, label="traffic comes to a stop — jam forming",
              speed_kmh=0),

        Scene(duration_sec=10, label="traffic starts moving again",
              speed_kmh=15),

        Scene(duration_sec=5,  label="parking",
              speed_kmh=0, parking_brake=True),
    ]


def run() -> None:
    sensor = MockSensor(scenes=build_scenario(), tick_sec=1.0)
    sm = StateMachine(initial_state=DrivingState.PARKED)

    last_label = ""
    while not sensor.is_done():
        t = sensor.read()
        actions = sm.update(t)

        # Print scene change headers for readability
        label = sensor.current_label()
        if label != last_label:
            print(f"\n--- t={t.timestamp:.0f}s | scenario: {label} ---")
            last_label = label

        # Print state + any actions
        if actions:
            for a in actions:
                print(f"  t={t.timestamp:5.1f}s [{sm.state.value:18}] "
                      f"{a.type.value}: {a.message or a.context} (urgency={a.urgency})")


if __name__ == "__main__":
    run()