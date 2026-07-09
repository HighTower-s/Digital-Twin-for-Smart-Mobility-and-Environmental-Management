"""
แปลงผลตรวจจับภายในของ AI Worker ให้เป็น payload ตาม docs/data-contract.md (v1.0.0)

data-contract คือสัญญากลางระหว่าง AI Worker / Backend / Unity ห้ามแก้ที่นี่
โมดูลนี้มีหน้าที่ "ปรับให้ตรง" สัญญานั้นเท่านั้น — ไม่เปลี่ยนสัญญา

หมายเหตุการ map:
- schema ภายใน  : {id, type, x, y (เมตร), speed_kmh, heading}
- schema สัญญา  : {trackId, type, speed, position:{x, y=0, z}}
- แกน           : ภายใน x -> position.x (ขวางถนน), ภายใน y -> position.z (แนวถนน),
                  position.y = 0.0 เสมอ (ระนาบพื้น ตาม business rule)
"""

from datetime import datetime, timezone

# ค่าคงที่จากสัญญา/กฎธุรกิจ (ห้าม hardcode ซ้ำที่อื่น)
GROUND_Y = 0.0
MAX_VEHICLES = 120
MIN_SPEED = 0.0
MAX_SPEED = 200.0
CONTRACT_TYPES = ("car", "truck", "motorcycle")

# COCO/ภายใน -> ชนิดตามสัญญา (bus รวมเป็น truck; bicycle ไม่อยู่ใน enum จึงถูกข้าม)
TYPE_MAP = {
    "car": "car",
    "truck": "truck",
    "bus": "truck",
    "motorcycle": "motorcycle",
    # "bicycle" -> ไม่ map = ข้าม
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def to_contract_vehicle(raw: dict) -> dict | None:
    """แปลงรถ 1 คันเป็นรูปแบบสัญญา คืน None ถ้าชนิดไม่อยู่ใน enum หรือพิกัดไม่ finite"""
    mapped_type = TYPE_MAP.get(str(raw.get("type", "")).lower())
    if mapped_type is None:
        return None

    x = raw.get("x")
    z = raw.get("y")  # แกน y ภายใน = แนวถนน = position.z ของสัญญา
    if not _is_finite(x) or not _is_finite(z):
        return None

    speed = raw.get("speed_kmh", 0.0)
    if not _is_finite(speed):
        speed = 0.0

    track_id = f"{mapped_type}-{int(raw.get('id', 0)):02d}"

    return {
        "trackId": track_id,
        "type": mapped_type,
        "speed": round(_clamp(float(speed), MIN_SPEED, MAX_SPEED), 2),
        "position": {
            "x": round(float(x), 3),
            "y": GROUND_Y,
            "z": round(float(z), 3),
        },
    }


def to_contract_frame(
    raw_vehicles: list[dict],
    frame_count: int,
    camera_id: str,
    timestamp: str | None = None,
) -> dict:
    """สร้าง payload 1 เฟรมตามสัญญา — cap ที่ MAX_VEHICLES คัน"""
    vehicles: list[dict] = []
    for raw in raw_vehicles:
        v = to_contract_vehicle(raw)
        if v is not None:
            vehicles.append(v)
        if len(vehicles) >= MAX_VEHICLES:
            break

    return {
        "timestamp": timestamp or _now_iso(),
        "cameraId": camera_id,
        "frameCount": frame_count,
        "vehicles": vehicles,
    }


def _now_iso() -> str:
    """เวลา UTC รูปแบบ ISO 8601 ลงท้าย Z (Date.parse ฝั่ง backend อ่านได้)"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _is_finite(value) -> bool:
    return isinstance(value, (int, float)) and value == value and value not in (float("inf"), float("-inf"))
