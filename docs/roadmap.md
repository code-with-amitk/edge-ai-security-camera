# Beginner roadmap

Follow these stages in order. Keep the scope small until each stage works reliably.

## Stage 1 — Prove the laptop pipeline

- [ ] Choose a camera view that can be used lawfully and privately. Mount the laptop so the camera stays still.
- [ ] Install Python, create a virtual environment, and install the project's requirements.
- [ ] Install Ollama, start its local server, and pull `moondream`.
- [ ] Run `python src/laptop_poc.py`; grant webcam access if prompted.
- [ ] Walk through the view and verify that motion creates a JPEG and a line in `data/alerts/events.jsonl`.
- [ ] Review several day/night and no-motion cases. Tune `--min-area`, `--motion-threshold`, and `--cooldown`.
- [ ] Record false positives, missed events, classification latency, and model errors. Do not treat a model label as an authorization decision.
- [ ] Confirm the laptop still works with its internet connection disabled. This validates local capture, inference, and logging.

## Stage 2 — Decide and order Pi hardware

- [ ] Start with the recommended Pi 5 (4 GB), Camera Module 3 standard, compatible 22-to-15-pin camera cable, official 27 W USB-C supply, active cooling, case, and high-endurance microSD.
- [ ] Check current availability, regional power plug, case compatibility, and exact cable connector requirements before purchasing.
- [ ] Decide whether person/pet detection is enough for the first Pi milestone. Treat parcel/package recognition as a later model-validation task.

## Stage 3 — Bring up the Pi and camera

- [ ] Flash Raspberry Pi OS 64-bit and set a unique password.
- [ ] Boot the Pi on a trusted LAN; update packages and install Picamera2/OpenCV.
- [ ] Install the camera with power disconnected, then run `rpicam-hello`.
- [ ] Verify image orientation, focus, exposure, day/night appearance, and the intended field of view.
- [ ] Capture test frames locally before integrating inference.

## Stage 4 — Port the event pipeline

- [ ] Replace OpenCV webcam capture with Picamera2 capture; keep camera and inference code behind small, testable functions.
- [ ] Add background motion detection and event cooldown, then measure CPU load and false positives.
- [ ] Select an appropriately licensed quantized model and a runtime supported on the chosen Pi OS image.
- [ ] Start with person/pet classes; benchmark latency, memory, temperature, and detection quality on the actual Pi.
- [ ] Add package detection only after selecting/training a model with representative parcel examples and evaluating precision/recall.
- [ ] Separate capture and inference with a bounded queue so model latency does not stop camera capture.

## Stage 5 — Local alerts and reliability

- [ ] Save selected snapshots locally, keep event metadata in SQLite, and add retention limits.
- [ ] Add a password-protected dashboard accessible only on the home LAN, or a local MQTT/webhook receiver.
- [ ] Verify the system continues capturing and storing events with WAN access disconnected.
- [ ] Test restart after power loss, camera unplug/replug, full disk, network loss, and model failure.
- [ ] Run for several days; inspect false alarms, missed events, queue drops, storage use, and temperatures.
- [ ] Only after local behavior is reliable, consider an explicitly configured hosted service such as WhatsApp. Document that it requires internet and sends data outside the home.

## Stage 6 — Harden and maintain

- [ ] Run the service as an unprivileged account and configure supervised startup/restart.
- [ ] Keep OS/model updates manageable and back up configuration without copying unnecessary image data.
- [ ] Re-check detection performance after changing camera position, lighting, model, or software.
- [ ] Set and periodically review image retention, access controls, and household privacy expectations.
