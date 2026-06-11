# AI Worker — CLAUDE.md

> Read `../CLAUDE.md` and `../docs/architecture.md` before this file.
> This file covers only AI Worker-specific context.

---

## What This Module Does

1. Pulls frames from RTSP stream via OpenCV
2. Detects and tracks vehicles using YOLOv8 + ByteTrack
3. Converts 2D bounding box center → 3D world coordinates via Homography matrix
4. Validates output against data contract (no NaN, confidence ≥ 0.5)
5. POSTs JSON payload to `http://localhost:3000/api/ingest` every ~1 second

---

## Planned Folder Layout

```
ai-worker/
├── CLAUDE.md
├── requirements.txt
├── .env.example
└── src/
    ├── main.py          ← entry point
    ├── capture.py       ← RTSP frame capture (OpenCV)
    ├── detector.py      ← YOLOv8 inference + ByteTrack
    ├── homography.py    ← 2D → 3D coordinate transform
    ├── validator.py     ← payload validation before POST
    ├── poster.py        ← HTTP POST to backend
    └── constants.py     ← named constants (no magic numbers)
```

---

## Business Rules (from architecture.md)

- Confidence threshold: discard detections with `confidence < 0.5`
- `trackId` must be stable across frames for the same vehicle (ByteTrack)
- `position.y` is always `0.0` — ground plane only, never derive from image
- Validate before every POST — never send NaN or Infinity
- Target frame interval: ~1 second between POSTs

---

## Environment Variables (`.env`)

```
RTSP_URL=rtsp://...
BACKEND_URL=http://localhost:3000
CAMERA_ID=cam-chalongkrung-01
YOLO_MODEL_PATH=./models/yolov8n.pt
CONFIDENCE_THRESHOLD=0.5
```

---

## Standards

- Python 3.11, type hints required on all functions
- Format: `black` — run before every commit
- Lint: `ruff check src/`
- No global state — pass config explicitly via function arguments
