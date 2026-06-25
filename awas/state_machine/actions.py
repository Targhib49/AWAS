"""Actions emitted by the state machine for downstream execution."""

from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    SPEAK = "speak"     # ask conversational AI to generate a response
    ALERT = "alert"     # fixed pre-written TTS message (faster, deterministic)
    LOG = "log"         # internal logging only — no audio


@dataclass
class Action:
    """One thing the state machine wants the executor to do."""
    type: ActionType
    urgency: int = 0       # 0=info, 1=mild, 2=engaged, 3=severe, 4=critical
    message: str = ""      # used by ALERT and LOG
    context: str = ""      # used by SPEAK — hint for the AI ("moving_drowsy" etc.)