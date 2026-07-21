# Vehicle Digital Twin — YOLOv8

เว็บแอปสำหรับอัปโหลดวิดีโอจราจร แล้วใช้ **YOLOv8 + ByteTrack** ตรวจจับและติดตามรถ
จากนั้นแปลงพิกัดภาพเป็นพิกัดจริง (เมตร) ด้วย **Homography** เพื่อคำนวณ
`position`, `speed`, `heading` ของรถแต่ละคัน แล้วส่งออกเป็นวิดีโอที่ annotate แล้ว + ไฟล์ **JSON**
สำหรับป้อนเข้า Digital Twin

## ติดตั้ง

ต้องมี Python 3.9+ ก่อน

```bash
cd vehicle-twin
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> โมเดล `yolov8n.pt` จะดาวน์โหลดอัตโนมัติครั้งแรก
> แนะนำให้ติดตั้ง **ffmpeg** ด้วย เพื่อให้วิดีโอผลลัพธ์เล่นในเบราว์เซอร์ได้
> (mac: `brew install ffmpeg` · ubuntu: `sudo apt install ffmpeg`)

## รัน

```bash
uvicorn app:app --reload --port 8000
```
python -m uvicorn app:app --reload --port 8000
เปิดเบราว์เซอร์ที่ http://localhost:8000

## ขั้นตอนใช้งาน

1. **อัปโหลดวิดีโอ** — ระบบดึงเฟรมแรกมาให้ calibrate
2. **Calibrate** — คลิก 4 จุดบนพื้นถนนตามลำดับ 1→2→3→4 แล้วกรอกพิกัดจริง (เมตร)
   ของแต่ละจุด นี่คือขั้นที่สำคัญที่สุด ถ้าจุดอ้างอิงแม่น ตำแหน่ง/ความเร็วจะแม่นตาม
3. **ประมวลผล** — ได้วิดีโอ annotate + ปุ่มดาวน์โหลด JSON

## โครงสร้าง JSON ที่ได้

```json
{
  "meta": {
    "fps": 30.0,
    "resolution": [1920, 1080],
    "homography_src_px": [[...], ...],
    "homography_dst_m": [[0,0],[10,0],[10,20],[0,20]],
    "unique_vehicles": 12,
    "max_speed_kmh": 63.4,
    "total_frames": 900
  },
  "frames": [
    {
      "frame": 0,
      "timestamp": 0.0,
      "vehicles": [
        {"id": 5, "type": "car", "x": 12.3, "y": 45.6,
         "speed_kmh": 42.5, "heading": 90.0, "bbox": [x1,y1,x2,y2]}
      ]
    }
  ]
}
```

- `x`, `y` = ตำแหน่งจริงบนระนาบพื้น (เมตร)
- `heading` = ทิศทางการเคลื่อนที่ (องศา) ใช้หมุนโมเดลรถใน 3D
- ป้อน stream นี้เข้า Unity / three.js / Unreal เพื่อวางรถใน digital twin ได้เลย

## ปรับแต่ง

- เปลี่ยนโมเดลใน `app.py`: `YOLO("yolov8s.pt")` หรือ `m/l/x` เพื่อความแม่นยำสูงขึ้น (ช้าลง)
- `smooth (เฟรม)` มากขึ้น = ความเร็วนิ่งขึ้นแต่ตอบสนองช้าลง
- อยากได้ค่านิ่งระดับ production แนะนำต่อยอดด้วย Kalman filter

## 2 โหมด (เลือกในหน้าเว็บ ขั้น calibrate)

- **สมจริง · twin** — คลิก 4 จุด homography → ตำแหน่งจริงทุกคัน (Digital Twin เต็ม) → `/process`
- **คร่าวๆ · 2 เส้น** — คลิก 2 จุดวางเส้น A/B + กรอกระยะจริง (เมตร) → YOLO นับรถ (นับครั้งเดียว/คัน
  กันซ้ำตอนคร่อมเส้น) + วัดความเร็วจากเวลาข้าม A→B แล้วจำลองตำแหน่งลงถนน (เลน −9/0/9, z −60..240
  ตรงกับ mock-server/Unity) → `/process_count` · logic อยู่ใน `count_detector.py`

ทั้ง 2 โหมด output เป็น data-contract เดียวกัน → กดปุ่ม "ส่งเข้า Digital Twin" สตรีมเข้า Unity ได้เหมือนกัน

## ส่งเข้า Digital Twin (backend → Unity) — เดโมครบวงจร

หลังประมวลผล จะมีปุ่ม **"▶ ส่งเข้า Digital Twin"** ในหน้าเว็บ กดแล้วระบบจะสตรีมผล
ตาม `docs/data-contract.md` เข้า `backend/api/ingest` แบบ real-time (~`STREAM_HZ` เฟรม/วินาที)
→ backend broadcast ผ่าน WebSocket → รถวิ่งใน Unity

ตั้งค่าใน `.env` (ดู `.env.example`): `BACKEND_URL`, `CAMERA_ID`, `STREAM_HZ`, `CONFIDENCE_THRESHOLD`

**ลำดับรันเดโม (3 terminal):**

```bash
# 1) Backend (ไม่ต้องมี TimescaleDB — ENABLE_DB_LOGGING=false เป็นค่าเริ่มต้น)
cd backend && npm install && npm run dev

# 2) Unity — เปิด unity/digitaltwin แล้วกด Play (หรือ WebGL build)

# 3) AI Worker (หน้านี้)
cd ai-worker/src/vehicle-twin && uvicorn app:app --port 8000
#    เปิด http://localhost:8000 → อัปโหลด → calibrate → ประมวลผล → กด "ส่งเข้า Digital Twin"
```

ติ๊ก **"วนซ้ำ"** เพื่อสตรีมวนไปเรื่อยๆ ตอนโชว์อาจารย์ · แผงสถานะบอกจำนวนเฟรมที่ส่ง/รถต่อเฟรม/error

> output ถูกแปลงให้ตรง data-contract แล้ว (`contract.py`): `trackId`, `type` (car/truck/motorcycle,
> bus→truck, ข้าม bicycle), `position.{x,y=0,z}`, speed 0–200, สูงสุด 120 คัน/เฟรม

## หมายเหตุ

- กล้องควรอยู่นิ่ง (fixed) — ถ้ากล้องขยับ homography จะเพี้ยน
- homography ใช้ได้ดีกับพื้นราบ (ถนน) ระนาบเดียว
- กล้อง CCTV จริง (SICA) ยังไม่ได้สิทธิ์ → ใช้วิดีโออัปโหลดแทน RTSP ไปก่อน
  วันได้สิทธิ์ค่อยเปลี่ยนแหล่งเฟรมเป็น RTSP โดย payload/ปลายทางเหมือนเดิม
