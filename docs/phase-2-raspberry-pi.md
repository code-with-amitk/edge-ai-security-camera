# Phase 2: Migrate to Raspberry Pi hardware

## Recommended first build

For a capable first physical prototype, use:

| Component | Recommendation | Why |
|---|---|---|
| Board | Raspberry Pi 5, 4 GB RAM | A good balance for camera capture, a lightweight CPU inference model, and a small local service. |
| Camera | Raspberry Pi Camera Module 3, standard (not Wide) | Autofocus, straightforward CSI connection, and sufficient detail for a fixed entryway view. |
| Camera cable | Raspberry Pi 5-compatible camera cable: 22-pin board end to 15-pin camera end | Pi 5's camera connector differs from the camera module's 15-pin connector. Check the connector orientation before purchase. |
| Power | Official Raspberry Pi 27 W USB-C Power Supply | Provides appropriate power headroom for a Pi 5 and attached camera. |
| Cooling/case | Pi 5 Active Cooler plus a compatible ventilated case, or a case with equivalent active cooling | Sustained CPU inference can heat and throttle a passively cooled Pi 5. Ensure the case supports the camera cable path. |
| Storage | 32 GB or larger high-endurance microSD card; 64 GB is a practical starting point | Holds Raspberry Pi OS, the application, model files, and rotating event snapshots. |
| Network | Wi-Fi or Ethernet | Provides local dashboard access and optional LAN delivery. Ethernet is useful during setup. |

Use Raspberry Pi 5 rather than Zero 2 W for the first CPU-inference build: the Zero 2 W has much less memory and compute headroom. Pi 4 can be a lower-cost option if inference speed is acceptable, but Pi 5 is the safer starting point for an actively developed vision pipeline. The Raspberry Pi AI Camera is an alternative when its supported on-sensor model workflow matches the use case; it is not required for this design.

Parts, regional availability, and connector/cable SKUs change. Before ordering, confirm that the cable explicitly supports the Pi 5 and the selected camera, and that the case fits the Pi 5, cooler, and cable.

## Bring-up and camera installation

1. Assemble the Pi 5 case and active cooler following their manufacturers' instructions. Work with the board unpowered.
2. Insert the microSD card, then install Raspberry Pi OS 64-bit using Raspberry Pi Imager. Set a strong device password and enable only the access method you intend to use.
3. Connect the Pi 5-compatible camera cable to a CSI camera connector with the board powered off. Align the cable contacts and locking tab as shown in the official Pi 5 camera instructions; do not force the connector.
4. Attach the other cable end to the Camera Module 3. Secure the camera so the lens points at the monitored area, without blocking its view or bending the ribbon sharply.
5. Connect network and power. Keep the Pi on an isolated, trusted home LAN; do not expose its services directly to the internet.
6. Update Raspberry Pi OS and install the camera software:

```bash
sudo apt update
sudo apt full-upgrade
sudo apt install python3-picamera2 python3-opencv
```

Check the camera with the current Raspberry Pi camera application:

```bash
rpicam-hello --timeout 5000
```

Raspberry Pi OS Bookworm uses the `rpicam-*` tools and the libcamera-based camera stack. For Python capture, use Picamera2 rather than assuming a USB webcam's `cv2.VideoCapture(0)` path. Consult the current [Raspberry Pi camera software documentation](https://www.raspberrypi.com/documentation/computers/camera_software.html) for OS-specific setup and commands.

## Pi software and data path

The laptop script is a logic prototype, not a drop-in Pi service. Replace the webcam read function with Picamera2 capture; retain the event schema and local storage concept. A practical Pi stack is:

- Raspberry Pi OS 64-bit.
- Picamera2/libcamera to configure the camera sensor, exposure, and frame format.
- OpenCV for resizing, grayscale conversion, background subtraction, and motion regions.
- A CPU-friendly, quantized object detector exported to a Pi-supported LiteRT/TensorFlow Lite runtime, or a supported on-camera model if using the AI Camera.
- A small Python event worker plus a local-only dashboard/API (for example, Flask or FastAPI bound to the LAN interface or loopback as appropriate).
- SQLite for event metadata and a bounded snapshot directory with retention cleanup.

### How a CSI camera frame reaches the CPU

The camera module's sensor converts light to pixel data and sends it over the CSI-2 ribbon cable to the Pi's camera receiver. The Raspberry Pi camera stack configures the sensor and ISP; Picamera2 exposes requested frames to the Python process as an in-memory array (commonly RGB). The application resizes or converts that array for motion detection and inference. For a USB camera instead, frames arrive over USB and can be read through V4L2/OpenCV.

The frame is not uploaded anywhere in this design. It remains in Pi memory until the program decides to write an event snapshot or serve it to an authorized local client.

### Suggested processing pipeline

1. Capture frames continuously at a modest size and rate, such as 640x480 at 5-10 frames per second to begin.
2. Use OpenCV motion detection as a cheap trigger. Add debounce, a cooldown, and optional zones of interest.
3. Push a copy of the triggering frame into a bounded queue. If the queue is full, record a dropped-event counter rather than allowing memory use to grow without limit.
4. A single inference worker resizes and normalizes the frame, runs an INT8/quantized model, and filters detections by class, confidence, and region.
5. Save a snapshot and event metadata only for selected events. Write metadata to SQLite and use deterministic retention limits for images.
6. Publish the event to the local dashboard or LAN webhook. Keep camera capture independent of slower model inference.
7. Monitor temperature, queue depth, inference duration, free storage, and camera availability.

MobileNet SSD trained on COCO can recognize categories such as person, cat, and dog, but generic COCO labels do **not** provide a dependable parcel/package class. If package detection is important, collect representative package examples and validate or train a suitable model; do not silently map unrelated object classes to "package." Begin with person/pet detection and add package support only after measured validation.

Ollama and a large vision-language model are convenient for laptop experimentation but are usually not the right Pi 5 inference path. A compact, quantized object detector is faster and consumes less memory. TensorFlow Lite is now commonly referred to as LiteRT; check current runtime support for the exact Raspberry Pi OS, Python, and model combination before choosing a model package. Benchmark it on the target Pi rather than relying on desktop performance.

## Camera Module 3 versus AI Camera

- **Camera Module 3:** a conventional image sensor. The Pi application receives frames and runs its model on the Pi CPU. This is the recommended beginner option because it keeps the capture and inference pipeline transparent.
- **AI Camera:** uses the IMX500 sensor with supported on-sensor inference workflows. It can reduce inference work on the Pi, but requires compatible model packaging and a different integration path. Choose it only after confirming the supported model and class set meets the project requirements.

## Service, security, and operational work before deployment

- Run the application as a dedicated unprivileged user under `systemd`; use restart limits and clear logs.
- Keep model files and snapshots on local storage. Use a retention limit and monitor free disk space.
- Provide a local configuration file for thresholds, camera settings, zones, and retention. Keep credentials out of source control.
- Bind the dashboard only to the intended interface, require authentication for remote LAN access, and use firewall rules. A private LAN is not automatically a trusted LAN.
- Test boot recovery, camera disconnect/reconnect, full storage, power loss, high temperature, night lighting, and false-positive rates.
- Consider a UPS or safe shutdown solution if resilience to power loss is important.

This is a development migration guide, not an assurance of detection performance or an installation/security certification.
