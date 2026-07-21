"""
Plan 1 (event-driven) — "ตรวจตอนรถข้ามเส้น → จำลองการวิ่งต่อเอง"

หลักการ (ตามที่ตกลงกันไว้ — ไม่พยายามสะท้อนตำแหน่งจริงเป๊ะ เพราะกล้องตัวเดียวเพี้ยน):
- YOLOv8 + ByteTrack ตรวจ+ติดตามรถ
- มีเส้นนับขวางถนน (เส้น A) — พอรถข้ามเส้น A ครั้งแรก จะยิง 1 "spawn event":
    * ชนิด : โหวตจากหลายเฟรม (majority) แล้วล็อกไว้ ไม่ให้สลับกลางทาง
    * เลน  : จาก x กลางกล่อง ณ จังหวะข้ามเส้น -> lane_index_from_x()
    * ความเร็ว: กำหนดตามชนิด (SPEED_BY_TYPE) — ไม่ใช้ค่าจาก pixel/homography
- PopulationManager เอา event ไป spawn รถจำลองในเลนนั้น แล้วขับไป +Z (ระยะตามถนน p)
  พร้อม car-following กันรถซ้อน จนพ้นปลายถนนแล้วเอาออก
- เส้น B (ถ้าใส่) ใช้ "วัดความเร็วจริง A->B" ไว้เป็นสถิติรายงานเท่านั้น ไม่ได้ขับรถ

พิกัดที่ส่งออกเป็น "local frame ของถนน": x = เยื้องเลน, z = ระยะตามถนน (0..ROAD_LEN)
ฝั่ง Unity เอา TrafficOrigin (anchor) ไปวาง/หมุนทับถนนจริงเอง — ดู unity/CLAUDE.md
ค่า LANES / ROAD_* / LANE_HALF_WIDTH ต้องตรงกับ TrafficOriginGizmo ในซีน (single source of truth)

output เป็น payload ตาม docs/data-contract.md ผ่าน contract.py (ไม่แก้สัญญา)
"""

import math
import os
import random
from collections import defaultdict

import cv2
import numpy as np
from dotenv import load_dotenv

import contract

load_dotenv()  # อ่าน .env ก่อน (count_detector ถูก import ก่อน load_dotenv ใน app.py)


def _env_floats(key: str, default: str) -> tuple[float, ...]:
    """อ่าน list ตัวเลขจาก env — ทน () [] และช่องว่าง; ค่าเสียจะถูกข้ามพร้อม warning (ไม่ทำแอปพัง)"""
    raw = os.getenv(key, default).strip().strip("()[]")
    out: list[float] = []
    for x in raw.split(","):
        x = x.strip()
        if x == "":
            continue
        try:
            out.append(float(x))
        except ValueError:
            print(f"[count_detector] ข้ามค่า {key} ที่ไม่ใช่ตัวเลข: {x!r}")
    return tuple(out)


# ---- ถนน (local frame): รถเกิดที่ START วิ่งไป END; anchor ใน Unity จัดตำแหน่งจริง ----
# ค่าเริ่มต้น = วิ่งตรงตามแกน +Z ยาว ROAD_LEN เมตร (ให้ Unity anchor หมุน/ย้ายเอง)
ROAD_START_X = float(os.getenv("ROAD_START_X", "0"))
ROAD_START_Z = float(os.getenv("ROAD_START_Z", "0"))
ROAD_END_X = float(os.getenv("ROAD_END_X", "0"))
ROAD_END_Z = float(os.getenv("ROAD_END_Z", "200"))
LANES = _env_floats("LANES", "-3.5,0,3.5")            # เยื้องเลน (- ซ้าย / + ขวา) — ตรงกับ gizmo Unity
LANE_HALF_WIDTH = float(os.getenv("LANE_HALF_WIDTH", "1.6"))

_dx = ROAD_END_X - ROAD_START_X
_dz = ROAD_END_Z - ROAD_START_Z
ROAD_LEN = math.hypot(_dx, _dz) or 1.0
FWD = (_dx / ROAD_LEN, _dz / ROAD_LEN)                # เวกเตอร์ทิศวิ่ง (x,z)
RIGHT = (FWD[1], -FWD[0])                             # ตั้งฉากกับถนน (ใช้เยื้องเลน)


def _world_xz(p: float, lane_off: float) -> tuple[float, float]:
    """แปลง (ระยะตามถนน p, เยื้องเลน) -> พิกัด local (x, z)"""
    x = ROAD_START_X + FWD[0] * p + RIGHT[0] * lane_off
    z = ROAD_START_Z + FWD[1] * p + RIGHT[1] * lane_off
    return x, z


# ---- ความเร็ว: กำหนดตามชนิด (km/h) ตามที่ตกลง (ไม่ใช้ pixel) ----
DEFAULT_SPEED = 40.0


def _env_speed_by_type() -> dict[str, float]:
    """อ่าน SPEED_BY_TYPE รูปแบบ 'car:40,motorcycle:45,truck:35' -> dict"""
    out: dict[str, float] = {}
    for part in os.getenv("SPEED_BY_TYPE", "car:40,motorcycle:45,truck:35").split(","):
        part = part.strip()
        if ":" in part:
            key, val = part.split(":", 1)
            try:
                out[key.strip().lower()] = float(val)
            except ValueError:
                pass
    return out


SPEED_BY_TYPE = _env_speed_by_type()


def speed_for_type(vtype: str) -> float:
    """ความเร็วเป้าหมายตามชนิด (fallback = car -> DEFAULT_SPEED)"""
    return SPEED_BY_TYPE.get(vtype, SPEED_BY_TYPE.get("car", DEFAULT_SPEED))


# ---- แมป x (pixel) ที่เส้นนับ -> index เลน ----
# ใส่เส้นแบ่งเองแม่นสุด: LANE_X_BOUNDS = ค่า x ของเส้นแบ่ง (len = จำนวนเลน + 1)
# ถ้าไม่ใส่ -> แบ่งช่วง [ROAD_X_MIN, ROAD_X_MAX] เท่าๆ กันเป็น len(LANES) เลน (หยาบกว่า)
ROAD_X_MIN = float(os.getenv("ROAD_X_MIN", "0"))
ROAD_X_MAX = float(os.getenv("ROAD_X_MAX", "1920"))
LANE_X_BOUNDS = _env_floats("LANE_X_BOUNDS", "")


def lane_index_from_x(cx: float) -> int:
    """x กลางกล่อง ณ เส้นนับ -> index เลน (0..len(LANES)-1)"""
    n = len(LANES)
    b = LANE_X_BOUNDS
    if len(b) >= 2:
        if cx < b[0]:
            return 0
        for i in range(len(b) - 1):
            if b[i] <= cx < b[i + 1]:
                return min(i, n - 1)
        return n - 1
    span = (ROAD_X_MAX - ROAD_X_MIN) or 1.0
    idx = int((cx - ROAD_X_MIN) / span * n)
    return max(0, min(n - 1, idx))


def in_road_span(cx: float) -> bool:
    """รถอยู่ในฝั่ง/ช่วงถนนที่สนใจไหม (นอกช่วง = อีกฝั่ง/นอกถนน -> ข้าม) = โฟกัสทีละฝั่ง"""
    b = LANE_X_BOUNDS
    if len(b) >= 2:
        return b[0] <= cx <= b[-1]
    return ROAD_X_MIN <= cx <= ROAD_X_MAX


# ---- พารามิเตอร์การจำลอง ----
MIN_GAP = float(os.getenv("MIN_GAP", "7"))   # ระยะขั้นต่ำหน้า-หลังในเลนเดียวกัน (เมตร) กันรถซ้อน
SPEED_JITTER = 0.15                          # ความเร็วรายคันต่างจากค่าตามชนิด ±15%
SPEED_EASE = 0.4                             # ปรับความเร็วจริงเข้าค่าเป้าหมายเนียนแค่ไหน
LANE_DRIFT = 0.3
LANE_JITTER = 0.1

CLASS_NAMES = {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
VEHICLE_CLASSES = [1, 2, 3, 5, 7]


class _Synth:
    """รถจำลอง 1 คัน — เก็บ 'ระยะตามถนน' p (แปลงเป็นพิกัดตอน output)"""

    __slots__ = ("tid", "type", "lane", "p", "speed", "target", "lat")

    def __init__(self, tid: int, vtype: str, lane_idx: int, target: float):
        self.tid = tid
        self.type = vtype             # ชนิดตามสัญญา (car/truck/motorcycle) — ล็อกแล้ว
        self.lane = lane_idx
        self.p = 0.0                  # ระยะที่วิ่งไปตามถนน (เมตร) 0..ROAD_LEN
        self.speed = target           # ความเร็วปัจจุบัน (km/h)
        self.target = target          # ความเร็วเป้าหมายตามชนิด (+jitter รายคัน)
        self.lat = LANES[lane_idx]    # เยื้องเลนปัจจุบัน


class PopulationManager:
    """
    รับ spawn event (ชนิด/เลน/ความเร็ว) -> คุมรถจำลองให้วิ่งไปข้างหน้า + car-following:
    - รถเข้าใกล้คันหน้าในเลนเดียวกันได้ไม่เกิน MIN_GAP (ไล่ทันคันช้า -> ชะลอตาม)
    - ต้นถนนยังไม่ว่าง (คันท้ายสุด < MIN_GAP) -> พัก event ไว้ใน pending รอมีที่ว่าง
    - พ้นปลายถนน (p > ROAD_LEN) -> เอาออก
    """

    def __init__(self) -> None:
        self.vehicles: list[_Synth] = []
        self._pending: list[tuple[int, str, int, float]] = []

    def _lane_back_p(self, lane_idx: int):
        ps = [v.p for v in self.vehicles if v.lane == lane_idx]
        return min(ps) if ps else None

    def request_spawn(self, tid: int, vtype: str, lane_idx: int, target: float) -> None:
        lane_idx = max(0, min(int(lane_idx), len(LANES) - 1))
        jitter = random.uniform(1 - SPEED_JITTER, 1 + SPEED_JITTER)
        self._pending.append((tid, vtype, lane_idx, max(1.0, target * jitter)))

    def _flush_pending(self) -> None:
        still: list[tuple[int, str, int, float]] = []
        for ev in self._pending:
            tid, vtype, lane_idx, target = ev
            if len(self.vehicles) >= contract.MAX_VEHICLES:
                still.append(ev)
                continue
            back = self._lane_back_p(lane_idx)
            if back is None or back >= MIN_GAP:
                self.vehicles.append(_Synth(tid, vtype, lane_idx, target))
            else:
                still.append(ev)  # ต้นถนนยังไม่ว่าง -> รอรอบถัดไป
        self._pending = still

    def step(self, dt: float) -> None:
        self.vehicles = [v for v in self.vehicles if v.p <= ROAD_LEN]  # พ้นถนน -> ออก
        for li in range(len(LANES)):
            lane_cars = sorted((v for v in self.vehicles if v.lane == li), key=lambda v: v.p)
            for i in range(len(lane_cars) - 1, -1, -1):     # คันหน้าสุด (p มาก) อัปเดตก่อน
                v = lane_cars[i]
                desired = max(1.0, v.target)                # ความเร็วเป้าหมายตามชนิด
                free_p = v.p + (desired / 3.6) * dt
                if i == len(lane_cars) - 1:
                    new_p = free_p                          # คันหน้าสุด วิ่งอิสระ
                else:
                    new_p = min(free_p, lane_cars[i + 1].p - MIN_GAP)  # กันชนคันหน้า
                new_p = max(new_p, v.p)                      # ห้ามถอยหลัง
                v.speed += ((new_p - v.p) / dt * 3.6 - v.speed) * SPEED_EASE
                v.p = new_p
                half = LANE_HALF_WIDTH * 0.5
                v.lat += (LANES[li] - v.lat) * LANE_DRIFT + random.uniform(-LANE_JITTER, LANE_JITTER)
                v.lat = max(LANES[li] - half, min(LANES[li] + half, v.lat))
        self._flush_pending()

    def as_raw(self) -> list[dict]:
        """คืน dict รูปแบบภายใน (ให้ contract.py แปลงต่อ): x->pos.x, y->pos.z"""
        out = []
        for v in self.vehicles:
            x, z = _world_xz(v.p, v.lat)
            out.append({"id": v.tid, "type": v.type, "x": x, "y": z, "speed_kmh": max(0.0, v.speed)})
        return out


def run_count(
    model,
    video_path: str,
    out_video_path: str,
    fps: float,
    conf: float,
    line_a_y: float,
    line_b_y: float,
    distance_m: float,
    stream_hz: float,
    camera_id: str,
) -> dict:
    """
    รันวิเคราะห์ทั้งวิดีโอ คืน dict:
      { "contract_frames": [...], "stats": {...} }
    พร้อมเขียนวิดีโอ annotate (เส้นนับ + ตัวนับ + ความเร็วเฉลี่ยจริง) ที่ out_video_path
    """
    sample_step = max(1, round(fps / stream_hz)) if stream_hz > 0 else 1
    dt = sample_step / fps  # วินาทีจริงต่อ 1 เฟรมที่ส่ง

    prev_cy: dict[int, float] = {}
    cross_frame: dict[int, dict] = defaultdict(dict)   # tid -> {"A": idx, "B": idx}
    votes: dict[int, dict] = defaultdict(lambda: defaultdict(int))  # tid -> {classname: count}
    spawned: set[int] = set()          # tid ที่ยิง spawn event ไปแล้ว (กันซ้ำ)
    locked: dict[int, tuple] = {}      # tid -> (ชนิด, เลน) ที่ล็อกตอน spawn (ใช้โชว์ป้าย)
    counted: set[int] = set()          # tid ที่นับจริง (ข้ามเส้น A + ชนิดอยู่ใน enum)
    measured: set[int] = set()
    speeds: list[float] = []           # ความเร็วจริงที่วัดได้ A->B (km/h) — สถิติเท่านั้น
    max_speed = 0.0

    pop = PopulationManager()
    contract_frames: list[dict] = []

    writer = None
    results = model.track(
        source=video_path, persist=True, tracker="bytetrack.yaml",
        classes=VEHICLE_CLASSES, conf=conf, stream=True, verbose=False,
    )

    for idx, r in enumerate(results):
        img = r.orig_img.copy()
        h, w = img.shape[:2]
        if writer is None:
            writer = cv2.VideoWriter(
                out_video_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
            )

        current_ids: set[int] = set()

        if r.boxes is not None and r.boxes.id is not None:
            for box in r.boxes:
                tid = int(box.id)
                cls = int(box.cls)
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0

                # โฟกัสฝั่งเดียว: รถนอกช่วงถนนที่สนใจ (อีกฝั่ง) -> ข้ามทั้งหมด
                if not in_road_span(cx):
                    continue

                current_ids.add(tid)
                votes[tid][CLASS_NAMES.get(cls, "car")] += 1

                # ตรวจการข้ามเส้น A/B (sign change ของ cy - line_y)
                if tid in prev_cy:
                    pcy = prev_cy[tid]
                    for name, ly in (("A", line_a_y), ("B", line_b_y)):
                        if (pcy - ly) * (cy - ly) < 0 and name not in cross_frame[tid]:
                            cross_frame[tid][name] = idx
                    # วัดความเร็วจริง A->B ครั้งเดียว/คัน (ไว้เป็นสถิติ ไม่ได้ขับรถ)
                    cf = cross_frame[tid]
                    if "A" in cf and "B" in cf and tid not in measured:
                        dframes = abs(cf["B"] - cf["A"])
                        if dframes > 0:
                            sp = distance_m / (dframes / fps) * 3.6
                            if 0 < sp < contract.MAX_SPEED:
                                speeds.append(sp)
                                measured.add(tid)
                                max_speed = max(max_speed, sp)
                prev_cy[tid] = cy

                # ข้ามเส้น A ครั้งแรก -> ยิง spawn event (ชนิดโหวต + เลนจาก x + ความเร็วตามชนิด)
                if "A" in cross_frame[tid] and tid not in spawned:
                    spawned.add(tid)
                    name = max(votes[tid].items(), key=lambda kv: kv[1])[0]
                    mapped = contract.TYPE_MAP.get(name)
                    if mapped is not None:      # bicycle ไม่อยู่ใน enum -> ข้าม (ไม่ spawn/ไม่นับ)
                        lane_idx = lane_index_from_x(cx)
                        pop.request_spawn(tid, mapped, lane_idx, speed_for_type(mapped))
                        counted.add(tid)
                        locked[tid] = (mapped, lane_idx)   # ล็อกค่าที่ส่งเข้า Unity ไว้โชว์

                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 200, 255), 2)
                # ป้าย: ข้ามเส้น A แล้ว -> โชว์ค่าที่ "ล็อก" (ตรงกับที่ส่ง Unity)
                #        ยังไม่ข้าม -> โชว์ค่าชั่วคราว + "?" (เลนที่ y นี้อาจยังไม่ตรงกับที่เส้น A)
                if tid in locked:
                    tdisp, ldisp = locked[tid]
                    label = f"#{tid} {tdisp} L{ldisp}"
                else:
                    name_dbg = CLASS_NAMES.get(cls, "car")
                    label = f"#{tid} {contract.TYPE_MAP.get(name_dbg, name_dbg)} L{lane_index_from_x(cx)}?"
                cv2.rectangle(img, (int(x1), int(y1) - 18),
                              (int(x1) + 9 * len(label), int(y1)), (0, 200, 255), -1)
                cv2.putText(img, label, (int(x1) + 2, int(y1) - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

        # วาดเส้นนับ + เส้นแบ่งเลน (ถ้ากำหนด) + สถิติ
        cv2.line(img, (0, int(line_a_y)), (w, int(line_a_y)), (80, 220, 120), 2)
        cv2.line(img, (0, int(line_b_y)), (w, int(line_b_y)), (245, 165, 36), 2)
        cv2.putText(img, "A", (8, int(line_a_y) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 220, 120), 2)
        cv2.putText(img, "B", (8, int(line_b_y) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (245, 165, 36), 2)
        for bx in LANE_X_BOUNDS:
            cv2.line(img, (int(bx), 0), (int(bx), h), (120, 120, 120), 1)
        avg_measured = float(np.mean(speeds)) if speeds else 0.0
        hud = f"count(total)={len(counted)}  now={len(current_ids)}  avg(real)={avg_measured:4.1f}km/h  spawned={len(pop.vehicles)}"
        cv2.rectangle(img, (0, 0), (max(460, 9 * len(hud)), 28), (20, 24, 30), -1)
        cv2.putText(img, hud, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 237, 243), 1, cv2.LINE_AA)
        writer.write(img)

        # ทุก sample_step: ขับรถจำลองไปข้างหน้า -> ส่งออกเป็น contract frame
        if idx % sample_step == 0:
            pop.step(dt)
            contract_frames.append(
                contract.to_contract_frame(
                    pop.as_raw(), frame_count=len(contract_frames), camera_id=camera_id
                )
            )

    if writer is not None:
        writer.release()

    avg_all = float(np.mean(speeds)) if speeds else 0.0
    return {
        "contract_frames": contract_frames,
        "stats": {
            "mode": "count-event",
            "unique_vehicles": len(counted),      # นับข้ามเส้น A จริง (เฉพาะชนิดใน enum)
            "measured_speeds": len(speeds),        # จำนวนคันที่วัดความเร็วจริงได้ (A->B)
            "avg_speed_kmh": round(avg_all, 2),    # ความเร็วจริงเฉลี่ย (สถิติ)
            "max_speed_kmh": round(max_speed, 2),
            "distance_m": distance_m,
            "lanes": list(LANES),
            "total_frames": len(contract_frames),
            "fps": fps,
        },
    }
