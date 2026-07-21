"""
Vehicle Digital Twin — YOLOv8 backend
อัปโหลดวิดีโอ -> ตรวจจับ+ติดตามรถ -> แปลง pixel เป็นเมตรด้วย homography (โหมด twin)
หรือ ตีเส้น 2 เส้นเพื่อ นับ+วัดความเร็ว แล้วจำลองตำแหน่ง (โหมด count)
-> ส่งออกวิดีโอที่ annotate แล้ว + สตรีมตาม data-contract เข้า backend -> Unity

รัน:  uvicorn app:app --reload --port 8000
เปิด: http://localhost:8000
"""

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from collections import defaultdict, deque
from pathlib import Path

import cv2
import httpx
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from ultralytics import YOLO

import contract
import count_detector

load_dotenv()

# ---------- config ----------
BASE = Path(__file__).parent
UPLOAD_DIR = BASE / "data" / "uploads"
OUTPUT_DIR = BASE / "data" / "outputs"
FRAME_DIR = BASE / "data" / "frames"
for d in (UPLOAD_DIR, OUTPUT_DIR, FRAME_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ปลายทางสตรีมเข้า pipeline จริง (backend -> WebSocket -> Unity) — override ได้ผ่าน .env
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:3000")
CAMERA_ID = os.getenv("CAMERA_ID", "cam-chalongkrung-01")
STREAM_HZ = float(os.getenv("STREAM_HZ", "2"))            # จำนวนเฟรมที่ส่งเข้า backend ต่อวินาที
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))  # business rule >= 0.5

# COCO vehicle classes: 1 bicycle, 2 car, 3 motorcycle, 5 bus, 7 truck
VEHICLE_CLASSES = [1, 2, 3, 5, 7]
CLASS_NAMES = {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}

# โหลดโมเดลครั้งเดียวตอนสตาร์ท — เปลี่ยนผ่าน .env: YOLO_MODEL=yolov8s.pt (แม่นมอไซค์ขึ้น, ช้าลง)
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
model = YOLO(YOLO_MODEL)

app = FastAPI(title="Vehicle Digital Twin")

# สถานะการสตรีมต่อ video_id (ให้ UI poll ดูความคืบหน้า)
stream_state: dict[str, dict] = {}


# ---------- helpers ----------
def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def to_web_mp4(src: Path) -> Path:
    """แปลงเป็น H.264 ให้เบราว์เซอร์เล่นได้ ถ้ามี ffmpeg; ไม่งั้นคืนไฟล์เดิม"""
    if not has_ffmpeg():
        return src
    dst = src.with_name(src.stem + "_h264.mp4")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), "-c:v", "libx264",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)],
            check=True, capture_output=True,
        )
        return dst
    except Exception:
        return src


# ---------- routes ----------
@app.get("/", response_class=HTMLResponse)
def index():
    return (BASE / "static" / "index.html").read_text(encoding="utf-8")


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """รับวิดีโอ, บันทึก, ดึงเฟรมแรกไว้ให้ผู้ใช้ calibrate"""
    vid = uuid.uuid4().hex[:12]
    ext = Path(file.filename).suffix or ".mp4"
    vpath = UPLOAD_DIR / f"{vid}{ext}"
    with vpath.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    cap = cv2.VideoCapture(str(vpath))
    ok, frame = cap.read()
    if not ok:
        raise HTTPException(400, "อ่านวิดีโอไม่ได้ — ไฟล์อาจเสียหรือฟอร์แมตไม่รองรับ")
    h, w = frame.shape[:2]
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()

    fpath = FRAME_DIR / f"{vid}.jpg"
    cv2.imwrite(str(fpath), frame)

    return {
        "video_id": vid,
        "filename": vpath.name,
        "frame_url": f"/frame/{vid}",
        "width": w,
        "height": h,
        "fps": round(fps, 3),
        "frames": total,
        "duration_s": round(total / fps, 2) if fps else None,
    }


@app.get("/frame/{vid}")
def frame(vid: str):
    fpath = FRAME_DIR / f"{vid}.jpg"
    if not fpath.exists():
        raise HTTPException(404, "ไม่พบเฟรม")
    return FileResponse(fpath, media_type="image/jpeg")


@app.post("/process")
async def process(
    video_id: str = Form(...),
    filename: str = Form(...),
    src_points: str = Form(...),   # JSON: [[x,y],... 4 จุด] พิกัด pixel บนภาพจริง
    dst_points: str = Form(...),   # JSON: [[X,Y],... 4 จุด] พิกัดจริงหน่วยเมตร
    fps: float = Form(...),
    conf: float = Form(CONFIDENCE_THRESHOLD),
    smooth_window: int = Form(6),  # จำนวนเฟรมเฉลี่ยความเร็ว
):
    """โหมด twin (สมจริง): homography -> ตำแหน่งจริงทุกคัน"""
    vpath = UPLOAD_DIR / filename
    if not vpath.exists():
        raise HTTPException(404, "ไม่พบไฟล์วิดีโอ")

    src = np.float32(json.loads(src_points))
    dst = np.float32(json.loads(dst_points))
    if src.shape != (4, 2) or dst.shape != (4, 2):
        raise HTTPException(400, "ต้องระบุจุด calibrate 4 จุดทั้ง src และ dst")
    H = cv2.getPerspectiveTransform(src, dst)

    cap = cv2.VideoCapture(str(vpath))
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    raw_out = OUTPUT_DIR / f"{video_id}_annot.mp4"
    writer = cv2.VideoWriter(str(raw_out), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    # history ต่อ track: เก็บ (t, X, Y) ไว้ smooth + คำนวณ speed/heading
    hist = defaultdict(lambda: deque(maxlen=max(2, smooth_window)))
    frames_json = []
    contract_frames = []                        # เฟรมที่แปลงตาม data-contract (สุ่มลดเหลือ ~STREAM_HZ)
    sample_step = max(1, round(fps / STREAM_HZ)) if STREAM_HZ > 0 else 1
    max_speed = 0.0
    seen_ids = set()

    results = model.track(
        source=str(vpath), persist=True, tracker="bytetrack.yaml",
        classes=VEHICLE_CLASSES, conf=conf, stream=True, verbose=False,
    )

    for idx, r in enumerate(results):
        t = idx / fps
        img = r.orig_img.copy()
        vehicles = []

        if r.boxes is not None and r.boxes.id is not None:
            for box in r.boxes:
                tid = int(box.id)
                cls = int(box.cls)
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                # จุดกลาง-ล่างของกล่อง = ตำแหน่งล้อสัมผัสพื้น
                px, py = (x1 + x2) / 2.0, y2
                wp = cv2.perspectiveTransform(
                    np.array([[[px, py]]], np.float32), H)[0][0]
                X, Y = float(wp[0]), float(wp[1])

                dq = hist[tid]
                speed_kmh, heading = 0.0, None
                if dq:
                    pt0, pX0, pY0 = dq[0]
                    dt = t - pt0
                    if dt > 1e-3:
                        dist = float(np.hypot(X - pX0, Y - pY0))
                        speed_kmh = dist / dt * 3.6
                        heading = float(np.degrees(np.arctan2(Y - pY0, X - pX0)))
                dq.append((t, X, Y))
                seen_ids.add(tid)
                max_speed = max(max_speed, speed_kmh)

                vehicles.append({
                    "id": tid,
                    "type": CLASS_NAMES.get(cls, str(cls)),
                    "x": round(X, 3),
                    "y": round(Y, 3),
                    "speed_kmh": round(speed_kmh, 2),
                    "heading": round(heading, 1) if heading is not None else None,
                    "bbox": [round(x1), round(y1), round(x2), round(y2)],
                })

                color = (0, 200, 255)
                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.circle(img, (int(px), int(py)), 4, (0, 0, 255), -1)
                label = f"#{tid} {CLASS_NAMES.get(cls,'?')} {speed_kmh:4.1f}km/h"
                cv2.rectangle(img, (int(x1), int(y1) - 20),
                              (int(x1) + 11 * len(label), int(y1)), color, -1)
                cv2.putText(img, label, (int(x1) + 2, int(y1) - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

        cv2.polylines(img, [src.astype(np.int32)], True, (80, 220, 120), 2)
        writer.write(img)

        frames_json.append({
            "frame": idx,
            "timestamp": round(t, 3),
            "vehicles": vehicles,
        })

        # สุ่มลดเฟรมให้เหลือ ~STREAM_HZ แล้วแปลงเป็นรูปแบบ data-contract ไว้สตรีมเข้า backend
        if idx % sample_step == 0:
            contract_frames.append(
                contract.to_contract_frame(
                    vehicles, frame_count=len(contract_frames), camera_id=CAMERA_ID
                )
            )

    writer.release()
    web_mp4 = to_web_mp4(raw_out)

    payload = {
        "meta": {
            "video_id": video_id,
            "fps": fps,
            "resolution": [w, h],
            "homography_src_px": src.tolist(),
            "homography_dst_m": dst.tolist(),
            "unique_vehicles": len(seen_ids),
            "max_speed_kmh": round(max_speed, 2),
            "total_frames": len(frames_json),
        },
        "frames": frames_json,
    }
    json_path = OUTPUT_DIR / f"{video_id}.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # บันทึกเฟรมรูปแบบ data-contract ไว้สำหรับสตรีมเข้า backend (endpoint /stream)
    contract_path = OUTPUT_DIR / f"{video_id}_contract.json"
    contract_path.write_text(json.dumps(contract_frames, ensure_ascii=False), encoding="utf-8")

    return {
        "video_url": f"/output/{web_mp4.name}",
        "json_url": f"/output/{json_path.name}",
        "playable": web_mp4.name.endswith("_h264.mp4") or has_ffmpeg(),
        "stats": payload["meta"],
        "contract_frames": len(contract_frames),
        "stream_hz": STREAM_HZ,
        "backend_url": BACKEND_URL,
    }


@app.post("/process_count")
async def process_count(
    video_id: str = Form(...),
    filename: str = Form(...),
    line_a_y: float = Form(...),   # พิกัด y (pixel) ของเส้น A
    line_b_y: float = Form(...),   # พิกัด y (pixel) ของเส้น B
    distance_m: float = Form(...), # ระยะจริงระหว่าง 2 เส้น (เมตร)
    fps: float = Form(...),
    conf: float = Form(CONFIDENCE_THRESHOLD),
):
    """โหมด count (คร่าวๆ): ตีเส้น 2 เส้น -> นับ+ความเร็ว -> จำลองตำแหน่ง -> contract"""
    vpath = UPLOAD_DIR / filename
    if not vpath.exists():
        raise HTTPException(404, "ไม่พบไฟล์วิดีโอ")
    if distance_m <= 0:
        raise HTTPException(400, "ระยะระหว่างเส้น (เมตร) ต้องมากกว่า 0")

    raw_out = OUTPUT_DIR / f"{video_id}_count.mp4"
    result = count_detector.run_count(
        model=model, video_path=str(vpath), out_video_path=str(raw_out),
        fps=fps, conf=conf, line_a_y=line_a_y, line_b_y=line_b_y,
        distance_m=distance_m, stream_hz=STREAM_HZ, camera_id=CAMERA_ID,
    )
    web_mp4 = to_web_mp4(raw_out)

    contract_frames = result["contract_frames"]
    contract_path = OUTPUT_DIR / f"{video_id}_contract.json"
    contract_path.write_text(json.dumps(contract_frames, ensure_ascii=False), encoding="utf-8")

    return {
        "video_url": f"/output/{web_mp4.name}",
        "playable": web_mp4.name.endswith("_h264.mp4") or has_ffmpeg(),
        "stats": result["stats"],
        "contract_frames": len(contract_frames),
        "stream_hz": STREAM_HZ,
        "backend_url": BACKEND_URL,
    }


@app.get("/output/{name}")
def output(name: str):
    p = OUTPUT_DIR / name
    if not p.exists():
        raise HTTPException(404, "ไม่พบไฟล์")
    media = "application/json" if name.endswith(".json") else "video/mp4"
    return FileResponse(p, media_type=media, filename=name)


# ---------- streaming เข้า pipeline จริง (backend -> WebSocket -> Unity) ----------
async def _run_stream(video_id: str, frames: list, loop: bool) -> None:
    """ยิงเฟรมตาม data-contract เข้า backend/api/ingest แบบ real-time (~STREAM_HZ)"""
    st = stream_state[video_id]
    delay = 1.0 / STREAM_HZ if STREAM_HZ > 0 else 0.5
    ingest_url = f"{BACKEND_URL.rstrip('/')}/api/ingest"
    sent = 0
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            while True:
                for frame in frames:
                    if st.get("stop"):
                        return
                    frame["timestamp"] = contract._now_iso()  # เวลาส่งจริง
                    frame["frameCount"] = sent
                    try:
                        r = await client.post(ingest_url, json=frame)
                        if r.status_code != 200:
                            st["errors"] += 1
                            st["last_error"] = f"HTTP {r.status_code}: {r.text[:120]}"
                    except Exception as exc:  # เครือข่าย/backend ยังไม่ขึ้น
                        st["errors"] += 1
                        st["last_error"] = str(exc)[:120]
                    sent += 1
                    st["sent"] = sent
                    st["vehicles"] = len(frame["vehicles"])
                    await asyncio.sleep(delay)
                if not loop:
                    return
    finally:
        st["running"] = False
        st["done"] = True


@app.post("/stream")
async def stream(video_id: str = Form(...), loop: bool = Form(False)):
    """เริ่มสตรีมผลตรวจจับของวิดีโอเข้า backend"""
    contract_path = OUTPUT_DIR / f"{video_id}_contract.json"
    if not contract_path.exists():
        raise HTTPException(404, "ยังไม่มีข้อมูล contract — ต้องประมวลผลวิดีโอก่อน")
    frames = json.loads(contract_path.read_text(encoding="utf-8"))
    if not frames:
        raise HTTPException(400, "ไม่มีเฟรมให้สตรีม")

    prev = stream_state.get(video_id)
    if prev and prev.get("running"):
        prev["stop"] = True  # หยุดรอบเดิมก่อนเริ่มใหม่

    stream_state[video_id] = {
        "running": True, "done": False, "stop": False,
        "sent": 0, "total": len(frames), "vehicles": 0,
        "errors": 0, "last_error": None,
        "backend_url": BACKEND_URL, "stream_hz": STREAM_HZ, "loop": loop,
    }
    asyncio.create_task(_run_stream(video_id, frames, loop))
    return {"ok": True, "total": len(frames), "backend_url": BACKEND_URL}


@app.post("/stream/stop")
def stream_stop(video_id: str = Form(...)):
    st = stream_state.get(video_id)
    if st:
        st["stop"] = True
    return {"ok": True}


@app.get("/stream_status/{video_id}")
def stream_status(video_id: str):
    return stream_state.get(video_id, {"running": False, "done": False, "sent": 0, "total": 0})


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
