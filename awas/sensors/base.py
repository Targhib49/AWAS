"""Sensor base class — defines the contract all sensors must implement."""

from abc import ABC, abstractmethod

from awas.state_machine.telemetry import Telemetry


class Sensor(ABC):
    """A source of telemetry.

    Real sensors (camera, OBD-II, GPS) and mock sensors both implement this.
    The state machine doesn't care which — it just calls `read()`.
    """

    @abstractmethod
    def read(self) -> Telemetry:
        """Return current sensor reading as a Telemetry snapshot."""
        ...

    def close(self) -> None:
        """Release any resources (camera handle, serial port, etc.). Override if needed."""
        pass