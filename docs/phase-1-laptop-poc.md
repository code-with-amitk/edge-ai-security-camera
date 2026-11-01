# Phase 1: Local laptop proof of concept

## Goal and boundaries

The POC reads a laptop webcam, detects pixel changes locally, and asks an Ollama vision model running on the same laptop to describe the captured scene. Snapshots and a JSON Lines event log are written to disk. No video or event is sent to a cloud service by this script.

This is a prototype, not a safety-rated alarm. Motion can be caused by lighting, shadows, or camera movement. A vision model can miss or mislabel objects. It can identify a visible **person**, but it cannot reliably know whether that person is an intruder or is authorized. Review events before taking action.

## 1. Install Python and OpenCV

Use Python 3.10 or later. Check your installation:

```bash
python --version
```

On systems where Python 3 is named `python3`, substitute `python3` for `python` in the commands below.

From the project directory, create and activate a virtual environment:

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The requirements file installs the OpenCV Python package (`opencv-python`), imported in the script as `cv2`. No separate `pip install cv2` is needed. The Python standard library handles HTTP, JSON, base64, and local logging.

Grant your terminal/Python application camera permission if your operating system prompts you. Close other camera applications if the webcam is already in use.

## 2. Install and start Ollama locally

Install Ollama using the instructions for your operating system at [ollama.com/download](https://ollama.com/download). Start the Ollama application/server. Its local API normally listens at `http://127.0.0.1:11434`.

Pull a small vision-capable model:

```bash
ollama pull moondream
```

The script defaults to `moondream`. Confirm Ollama sees the model:

```bash
ollama list
```

You can try another Ollama vision model, such as a LLaVA variant, if it is available for your machine:

```bash
ollama pull llava
```

LLaVA variants can require substantially more memory and disk than Moondream. Model size, speed, and quality depend on the particular model tag and laptop hardware. The model must support image input; text-only models cannot classify these snapshots.

## 3. Run the POC

Activate the virtual environment, ensure Ollama is running, then launch:

```bash
python src/laptop_poc.py
```

The first webcam is camera index `0`; use `--camera 1` if that is not the laptop camera. The OpenCV preview shows the captured feed. Press `q` while the preview has focus to exit. To run without a preview window:

```bash
python src/laptop_poc.py --no-display
```

On the first frame, the script initializes a grayscale background model. It compares subsequent frames with that slowly adapting background and checks whether a sufficiently large changed region exists. When motion is detected and the cooldown has expired, it:

1. Encodes the current frame as a JPEG and saves it locally.
2. Sends that one image to Ollama's local `/api/generate` endpoint.
3. Requests JSON with a `person`, `pet`, `package`, or `none` label, confidence, and a short description.
4. Validates the model output and appends the event to `data/alerts/events.jsonl`.

If Ollama is unavailable or returns invalid data, the snapshot is still kept and a `classification_error` event is logged. The default motion area and cooldown can be tuned:

```bash
python src/laptop_poc.py --min-area 2500 --motion-threshold 30 --cooldown 20
```

For a different model:

```bash
python src/laptop_poc.py --model llava
```

Use `python src/laptop_poc.py --help` for all options. Camera index, model name, Ollama URL, output directory, motion threshold, minimum changed area, cooldown, and preview mode are configurable.

## 4. Local outputs

By default, the script creates `data/alerts/` relative to the current working directory. It contains:

- One JPEG snapshot per triggered event.
- `events.jsonl`, with one JSON object per line. Each record includes a timestamp, snapshot filename, model, status, and classification or error.

These are ordinary local files, not encrypted. Restrict access to the folder, avoid committing it to source control, and delete snapshots when no longer needed. No continuous video recording is implemented.

## 5. POC limitations and troubleshooting

- **Camera fails to open:** check OS camera permissions, close other camera apps, and try another `--camera` index.
- **No motion events:** lower `--min-area` or `--motion-threshold`; keep the camera fixed. A changing scene or low light may produce false events.
- **Too many events:** raise `--min-area`, raise `--motion-threshold`, or increase `--cooldown`.
- **Ollama connection error:** start Ollama and verify the model with `ollama list`. The default endpoint is local; for a custom local endpoint use `--ollama-url`.
- **Slow classification:** use a smaller compatible model or lower webcam resolution. This POC calls Ollama synchronously, so webcam processing pauses during inference.
- **Poor package/person recognition:** change the scene, improve lighting, and evaluate model errors. A general vision-language model is not a validated alarm detector.

The Pi design should use a camera capture loop separate from inference and an explicit event queue to avoid pausing frame capture. See the [migration guide](phase-2-raspberry-pi.md).
