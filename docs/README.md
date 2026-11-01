# Project documentation

This project is developed in two stages: validate motion-triggered local vision on a laptop, then move the camera and inference pipeline to a Raspberry Pi.

## Guides

1. [Phase 1: Local laptop POC](phase-1-laptop-poc.md) — environment setup, Ollama model, script operation, and troubleshooting.
2. [Phase 2: Raspberry Pi migration](phase-2-raspberry-pi.md) — recommended hardware, camera installation, and an embedded inference architecture.
3. [System design and offline alerts](system-design.md) — components, data flow, privacy boundaries, and notification options.
4. [Beginner roadmap](roadmap.md) — a chronological build and validation checklist.

The runnable laptop implementation is [../src/laptop_poc.py](../src/laptop_poc.py). It saves snapshots and a JSON Lines log under `data/alerts/` by default. These local files can contain sensitive imagery; secure and remove them as appropriate.
