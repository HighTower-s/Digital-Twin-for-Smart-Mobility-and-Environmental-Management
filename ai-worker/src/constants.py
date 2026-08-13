"""ค่าคงที่ทั้งหมดของ AI Worker — ห้าม hardcode ตัวเลข/ชื่อซ้ำที่ไฟล์อื่น

บทเรียนจากโค้ดชุดก่อน (bug 2026-07-21): ค่าเดียวกันถูกเขียนไว้หลายที่แล้วหลุดกัน
เวอร์ชันนี้จึงรวมค่า invariant (ไม่เปลี่ยนตามคลิป) ไว้ที่เดียว ส่วนค่าที่ปรับต่อคลิป
(path วิดีโอ, conf, imgsz, ...) อยู่ใน config.yaml แทน
"""

from typing import Final

# ---------------------------------------------------------------- ชนิดรถ

# COCO class id -> ชนิดรถที่สนใจ
# bicycle (1) ตัดออกตั้งใจ: ไม่ใช่ยานยนต์ และมักถูกสับสนกับมอเตอร์ไซค์
COCO_TO_TYPE: Final[dict[int, str]] = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}
VEHICLE_CLASS_IDS: Final[list[int]] = sorted(COCO_TO_TYPE)
VEHICLE_TYPES: Final[tuple[str, ...]] = ("car", "motorcycle", "bus", "truck")

# ---------------------------------------------------------------- ทิศทาง

# กล้องอยู่บนสะพานลอยมองตามแนวถนน
# รถเข้าหากล้อง = เลื่อนลงล่างในภาพ = toward (IN)
# รถออกจากกล้อง = เลื่อนขึ้นบนในภาพ = away (OUT)
DIRECTION_TOWARD: Final[str] = "toward"
DIRECTION_AWAY: Final[str] = "away"
DIRECTIONS: Final[tuple[str, str]] = (DIRECTION_TOWARD, DIRECTION_AWAY)

# ชื่อทิศที่ใช้ใน payload ที่ส่งออก (ภายในใช้ toward/away เพื่อสื่อความหมายเชิงเรขาคณิต
# แต่ภายนอกใช้ in/out ซึ่งเป็นภาษาที่ทีม Unity กับอาจารย์ใช้)
DIRECTION_TO_IO: Final[dict[str, str]] = {
    DIRECTION_TOWARD: "in",
    DIRECTION_AWAY: "out",
}

# ---------------------------------------------------------------- anomaly

# เหตุผลที่ปฏิเสธการนับ — เขียนลง anomalies.csv เพื่อไล่หาว่าเลขหายไปไหน
REASON_WRONG_DIRECTION: Final[str] = "wrong_direction"
REASON_OUTSIDE_POLYGON: Final[str] = "outside_polygon"
REASON_ALREADY_COUNTED: Final[str] = "already_counted"
REASON_NO_TYPE_VOTES: Final[str] = "no_type_votes"

# ---------------------------------------------------------------- ค่ารันเริ่มต้น

# ใช้เป็นค่า default ถ้า config.yaml ไม่ได้ระบุ (override ได้ผ่าน config.yaml)
DEFAULT_MODEL: Final[str] = "data/weights/yolov8s.pt"
DEFAULT_TRACKER: Final[str] = "bytetrack.yaml"
DEFAULT_IMGSZ: Final[int] = 640
DEFAULT_CONF_THRESHOLD: Final[float] = 0.35

# เตือนเมื่อผ่านไปเท่านี้เฟรมแล้วยังนับไม่ได้เลย -> มักแปลว่า zone/line วางผิด
ZERO_COUNT_WARN_FRAMES: Final[int] = 500

# ล้าง track ที่หายไปนาน กันหน่วยความจำโตไม่จำกัดในวิดีโอยาว
PRUNE_EVERY_FRAMES: Final[int] = 300
TRACK_TTL_FRAMES: Final[int] = 150

# ความยาวด้านที่ยาวที่สุดของหน้าต่างที่แสดง (ภาพจริง 1920x1080 ใหญ่เกินจอโน้ตบุ๊ก)
DISPLAY_MAX_SIDE: Final[int] = 1280

# ---------------------------------------------------------------- payload

# กล้องตัวเดียวใน MVP — ตรงกับ cameraId ใน docs/data-contract.md
DEFAULT_CAMERA_ID: Final[str] = "cam-chalongkrung-01"

# เวอร์ชันของ spawn event — 0.2 เพราะตัด lane/speed ออกจาก 0.1-draft เดิม (2026-08-09)
SPAWN_EVENT_SCHEMA: Final[str] = "spawn-event/0.2-draft"

# backend รันเครื่องเดียวกันในเวอร์ชัน prototype — ตรงกับ backend/.env.example PORT=3000
DEFAULT_BACKEND_URL: Final[str] = "http://localhost:3000"

# ---------------------------------------------------------------- สี (BGR)

# OpenCV ใช้ BGR ไม่ใช่ RGB
COLOR_BY_TYPE: Final[dict[str, tuple[int, int, int]]] = {
    "car": (0, 200, 255),
    "motorcycle": (255, 160, 0),
    "bus": (0, 255, 120),
    "truck": (200, 80, 255),
}
COLOR_UNKNOWN: Final[tuple[int, int, int]] = (160, 160, 160)
COLOR_ZONE: Final[tuple[int, int, int]] = (120, 120, 120)
COLOR_LINE: Final[dict[str, tuple[int, int, int]]] = {
    DIRECTION_TOWARD: (80, 220, 120),
    DIRECTION_AWAY: (245, 165, 36),
}
COLOR_HUD_BG: Final[tuple[int, int, int]] = (20, 24, 30)
COLOR_HUD_TEXT: Final[tuple[int, int, int]] = (230, 237, 243)
COLOR_WARN: Final[tuple[int, int, int]] = (60, 60, 240)
