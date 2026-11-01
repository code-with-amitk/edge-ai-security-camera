#!/usr/bin/env python3
"""Local webcam motion detector with optional Ollama vision classification."""

import argparse
import base64
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import cv2


ALLOWED_LABELS = {"person", "pet", "package", "none"}

CLASSIFICATION_PROMPT = """Inspect this security-camera image and return one JSON object with:
- "label": exactly one of "person", "pet", "package", or "none"
- "confidence": a number from 0 to 1
- "description": a short factual description of visible evidence

Choose "person" when a person is visible, "pet" for a visible domestic animal,
"package" only when a parcel/package is clearly visible, and "none" otherwise.
Do not infer identity, intent, or whether a person is authorized. If uncertain,
choose "none" and explain the uncertainty briefly. Return JSON only."""


def parse_args() -> argparse.Namespace:
    """Parse settings that are useful to vary between laptop webcams."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0, help="OpenCV camera index (default: 0)")
    parser.add_argument("--model", default="moondream", help="Ollama vision model name")
    parser.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434",
        help="Ollama base URL (default: local Ollama server)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/alerts"),
        help="Folder for local snapshots and the JSONL event log",
    )
    parser.add_argument(
        "--motion-threshold",
        type=int,
        default=25,
        help="Pixel-difference threshold from 0 to 255",
    )
    parser.add_argument(
        "--min-area",
        type=int,
        default=1500,
        help="Minimum changed pixel area that triggers an event",
    )
    parser.add_argument(
        "--cooldown",
        type=float,
        default=15.0,
        help="Minimum seconds between classifications",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Run without an OpenCV preview window (useful on headless systems)",
    )
    return parser.parse_args()


def find_motion(
    frame,
    background,
    threshold: int,
    min_area: int,
):
    """Compare a frame with a slowly adapting grayscale background model."""
    # Converts the incoming colorful image to grayscale (black and white) and blurs it slightly.
    # This strips away unnecessary color data and smooths out graininess or micro-flickers from your camera sensor.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    # Initializes Background. When your script first starts, it stores this first processed frame as 
    # the baseline reference image of your empty room/scene.
    if background is None:
        return False, gray.astype("float32")

    # Calculates Pixel Differences (absdiff & threshold):
    # It subtracts the current frame from the stored background frame to find pixel changes. 
    # Any change brighter than threshold (e.g., 25) turns pure white ($255$), while unchanged 
    # areas turn pure black ($0$).
    background_frame = cv2.convertScaleAbs(background)
    difference = cv2.absdiff(gray, background_frame)
    _, mask = cv2.threshold(difference, threshold, 255, cv2.THRESH_BINARY)
    mask = cv2.dilate(mask, None, iterations=2)

    # Discard tiny isolated changes such as sensor noise.
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    has_motion = any(cv2.contourArea(contour) >= min_area for contour in contours)

    # Slowly adapt to gradual lighting changes and stationary scene details.
    cv2.accumulateWeighted(gray, background, 0.05)
    return has_motion, background


def classify_with_ollama(image_bytes: bytes, base_url: str, model: str) -> dict:
    """Send one JPEG to Ollama on this machine and validate its JSON answer."""
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": model,
        "prompt": CLASSIFICATION_PROMPT,
        "images": [image_b64],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0},
    }
    request = Request(
        f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            response_text = response.read().decode("utf-8")
    except HTTPError as error:
        detail = error.read(500).decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Ollama at {base_url}: {error.reason}") from error
    except TimeoutError as error:
        raise RuntimeError(f"Timed out waiting for Ollama at {base_url}") from error
    except UnicodeDecodeError as error:
        raise RuntimeError("Ollama returned a response that was not UTF-8 text") from error

    try:
        ollama_result = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise RuntimeError("Ollama returned an invalid API response") from error

    if not isinstance(ollama_result, dict):
        raise RuntimeError("Ollama API response must be a JSON object")
    # The generate API wraps the model's JSON answer inside its response field.
    generated_text = ollama_result.get("response")
    if not isinstance(generated_text, str):
        raise RuntimeError("Ollama response did not contain generated text")

    try:
        result = json.loads(generated_text)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Ollama did not return valid JSON: {generated_text!r}") from error

    if not isinstance(result, dict):
        raise RuntimeError("Ollama classification must be a JSON object")
    label = result.get("label")
    confidence = result.get("confidence")
    description = result.get("description")
    if not isinstance(label, str) or label not in ALLOWED_LABELS:
        raise RuntimeError(f"Ollama returned an unsupported label: {label!r}")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise RuntimeError(f"Ollama returned an invalid confidence: {confidence!r}")
    if not 0 <= confidence <= 1:
        raise RuntimeError(f"Ollama confidence must be between 0 and 1: {confidence!r}")
    if not isinstance(description, str):
        raise RuntimeError("Ollama returned an invalid description")

    return {
        "label": label,
        "confidence": float(confidence),
        "description": description,
    }


def main() -> None:
    args = parse_args()
    if args.min_area < 1:
        raise ValueError("--min-area must be greater than zero")
    if args.cooldown < 0:
        raise ValueError("--cooldown cannot be negative")
    if not 0 <= args.motion_threshold <= 255:
        raise ValueError("--motion-threshold must be between 0 and 255")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.output_dir / "events.jsonl"

    # OpenCV reads frames from the built-in webcam (usually camera index zero).
    camera = cv2.VideoCapture(args.camera)
    if not camera.isOpened():
        raise RuntimeError(
            f"Could not open camera index {args.camera}. Check camera permissions "
            "or try another --camera index."
        )
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    background = None
    next_event_time = 0.0
    print(f"Watching camera {args.camera}; local alerts will be saved in {args.output_dir}.")
    print("Press q in the preview window to stop." if not args.no_display else "Press Ctrl+C to stop.")

    try:
        while True:
            # Keep reading frames continuously while the scene is being monitored.
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Could not read a frame from the webcam")

            motion, background = find_motion(
                frame,
                background,
                args.motion_threshold,
                args.min_area,
            )
            now = time.monotonic()

            # A cooldown prevents a continuous movement from flooding the model and log.
            if motion and now >= next_event_time:
                event_time = datetime.now().astimezone()
                event_id = event_time.strftime("%Y%m%d-%H%M%S-%f")
                image_name = f"{event_id}.jpg"
                image_path = args.output_dir / image_name
                encoded_ok, encoded_image = cv2.imencode(".jpg", frame)
                if not encoded_ok:
                    raise RuntimeError("OpenCV could not encode the captured frame as JPEG")

                image_bytes = encoded_image.tobytes()
                image_path.write_bytes(image_bytes)
                event = {
                    "timestamp": event_time.isoformat(timespec="seconds"),
                    "snapshot": image_name,
                    "model": args.model,
                }

                # Keep the captured event even if the local model is unavailable.
                try:
                    # The POC sends one still image to the local Ollama API per event.
                    classification = classify_with_ollama(
                        image_bytes,
                        args.ollama_url,
                        args.model,
                    )
                    event.update({"status": "classified", **classification})
                    print(
                        f"[{event['timestamp']}] {classification['label']} "
                        f"({classification['confidence']:.2f}): "
                        f"{classification['description']}"
                    )
                except RuntimeError as error:
                    event.update({"status": "classification_error", "error": str(error)})
                    print(f"[{event['timestamp']}] Classification failed: {error}")

                # JSON Lines keeps each event easy to inspect or process later.
                with log_path.open("a", encoding="utf-8") as event_log:
                    event_log.write(json.dumps(event, ensure_ascii=False) + "\n")
                next_event_time = time.monotonic() + args.cooldown

            if not args.no_display:
                cv2.imshow("Local Edge AI Camera - press q to quit", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
    finally:
        camera.release()
        if not args.no_display:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
