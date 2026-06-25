# AWAS — Advanced Warning & Awareness System

A driver-safety system using edge AI on Raspberry Pi 5. Detects drowsiness
and phone usage via webcam, engages drowsy drivers with conversational AI
rather than alarms, and adapts behavior to driving context (highway, traffic
jam, stopped at light).

Research project for high school competition, 2026.

## Status

- [x] State machine skeleton with mock sensors and tests
- [ ] Webcam drowsiness detection (MediaPipe + EAR)
- [ ] ETS2 simulator integration
- [ ] Conversational AI (TinyLlama on Pi)
- [ ] TTS output (Piper)
- [ ] Raspberry Pi 5 deployment

## Running locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m scripts.demo_state_machine   # see state machine react to scripted drive
python -m pytest -v                    # run tests
```

## Architecture

See `AWAS_State_Machine_Design.md`, `AWAS_Conversational_AI_Architecture.md`,
and `AWAS_Implementation_Details.md` (in `docs/` or repo root) for design.
