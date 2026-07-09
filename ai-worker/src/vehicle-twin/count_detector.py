"""
Plan 1 (คร่าวๆ) — count-based ด้วยวิธี "ตีเส้น 2 เส้น"

หลักการ (ตามที่คุยกันไว้):
- YOLOv8 + ByteTrack ตรวจ+ติดตามรถ
- เส้น A / เส้น B ขวางถนน ระยะจริง d เมตร
    * นับรถ  : ครั้งเดียวต่อ trackId ที่ข้ามเส้น (counted-set กันนับซ้ำตอนคร่อมเส้น)
    * ความเร็ว: d / (เวลาข้าม A->B) * 3.6  (ไม่ใช้ pixel เลย -> ไม่ต้อง homography เต็ม)
- ตำแหน่งรถแต่ละคัน "จำลอง" ด้วย Population Manager ให้ลงถนนตรงกับซีน Unity
  (เลน x=-9/0/9, z=-60..240 — ค่าเดียวกับ mock-server)
- ส่งออกเป็น payload ตาม data-contract ผ่าน contract.py

สรุป: จำนวน = จริง, ความเร็วเฉลี่ย = จริง (จาก 2 เส้น), ตำแหน่งรายคัน = จำลอง
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
    return tuple(float(x) for x in os.getenv(key, default).split(",") if x.strip() != "")


# ---- ถนนแบบ "ใส่ค่าเอง": จุดเริ่ม + จุดปลาย (อ่านพิกัดจาก Unity มาใส่) ----
# รถเกิดที่ START แล้ววิ่งไปหา END  (ทิศ + ความยาว คำนวณจาก 2 จุดนี้; สลับ 2 จุด = กลับทิศ)
ROAD_START_X = float(os.getenv("ROAD_START_X", "0"))   # จุดสปอน x (world)
ROAD_START_Z = float(os.getenv("ROAD_START_Z", "0"))   # จุดสปอน z (world)
ROAD_END_X = float(os.getenv("ROAD_END_X", "0"))       # ปลายถนน x
ROAD_END_Z = float(os.getenv("ROAD_END_Z", "200"))     # ปลายถนน z
LANES = _env_floats("LANES", "-3.5,0,3.5")             # ระยะเยื้อง "ตั้งฉาก" กับถนน (- ซ้าย / + ขวา)
LANE_HALF_WIDTH = float(os.getenv("LANE_HALF_WIDTH", "1.2"))
SPAWN_SPREAD = float(os.getenv("SPAWN_SPREAD", "30"))

_dx = ROAD_END_X - ROAD_START_X
_dz = ROAD_END_Z - ROAD_START_Z
ROAD_LEN = math.hypot(_dx, _dz) or 1.0
FWD = (_dx / ROAD_LEN, _dz / ROAD_LEN)                 # เวกเตอร์ทิศวิ่ง (x,z)
RIGHT = (FWD[1], -FWD[0])                              # ตั้งฉากกับถนน (ใช้เยื้องเลน)


def _world_xz(p: float, lane_off: float) -> tuple[float, float]:
    """แปลง (ระยะตามถนน p, เยื้องเลน) -> พิกัดโลก (x, z)"""
    x = ROAD_START_X + FWD[0] * p + RIGHT[0] * lane_off
    z = ROAD_START_Z + FWD[1] * p + RIGHT[1] * lane_off
    return x, z

DEFAULT_SPEED = 40.0          # ใช้ตอนยังวัดความเร็วไม่ได้
MIN_GAP = float(os.getenv("MIN_GAP", "7"))   # ระยะขั้นต่ำหน้า-หลังในเลนเดียวกัน (เมตร) กันรถซ้อน
SPEED_JITTER = 0.15           # ความเร็วรายคันต่างจากเฉลี่ย ±15%
SPEED_EASE = 0.4              # ปรับความเร็วเข้าค่าจริงเนียนแค่ไหน
LANE_DRIFT = 0.3
LANE_JITTER = 0.1
SPEED_SMOOTH = 8              # เฉลี่ยความเร็วที่วัดได้ล่าสุดกี่ค่า

CLASS_NAMES = {1: "bicycle", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
VEHICLE_CLASSES = [1, 2, 3, 5, 7]


class _Synth:
    """รถจำลอง 1 คัน — เก็บ 'ระยะตามถนน' p (แปลงเป็นพิกัดโลกตอน output)"""

    __slots__ = ("tid", "type", "lane", "p", "speed", "factor", "lat")

    def __init__(self, tid: int, vtype: str, lane_idx: int, p: float, factor: float):
        self.tid = tid
        self.type = vtype
        self.lane = lane_idx          # index ของเลน (0..len(LANES)-1)
        self.p = p                    # ระยะที่วิ่งไปตามถนน (เมตร) 0..ROAD_LEN
        self.speed = 0.0
        self.factor = factor          # ความเร็ว "ที่อยากได้" = avg * factor (คงความต่างรายคัน)
        self.lat = LANES[lane_idx]    # เยื้องเลนปัจจุบัน


class PopulationManager:
    """
    คุมจำนวนรถให้ตรง count จริง + car-following กันรถซ้อน (ทำงานบนระยะตามถนน p):
    - รถเข้าใกล้คันหน้าในเลนเดียวกันได้ไม่เกิน MIN_GAP
    - ไล่ทันคันหน้าที่ช้ากว่า -> ชะลอตาม (รถติดเป็นแถวแบบธรรมชาติ)
    """

    def __init__(self) -> None:
        self.vehicles: list[_Synth] = []
        self._next_id = 0
        self._pick = lambda: "car"

    def _lane_back_p(self, lane_idx: int):
        ps = [v.p for v in self.vehicles if v.lane == lane_idx]
        return min(ps) if ps else None

    def _try_spawn(self) -> bool:
        # เลือกเลนที่ต้นถนนว่างพอ (คันท้ายสุดห่างจาก 0 อย่างน้อย MIN_GAP) จะได้ไม่ทับ
        order = list(range(len(LANES)))
        random.shuffle(order)
        for li in order:
            back = self._lane_back_p(li)
            if back is None or back >= MIN_GAP:
                self._next_id += 1
                factor = random.uniform(1 - SPEED_JITTER, 1 + SPEED_JITTER)
                self.vehicles.append(_Synth(self._next_id, self._pick(), li, 0.0, factor))
                return True
        return False  # ทุกเลนแน่นตรงต้นถนน -> ยังไม่ spawn รอมีที่ว่าง

    def reconcile(self, target: int, pick_type) -> None:
        self._pick = pick_type
        target = max(0, min(target, contract.MAX_VEHICLES))
        self.vehicles = [v for v in self.vehicles if v.p <= ROAD_LEN]   # ออกนอกถนน -> เอาออก
        while len(self.vehicles) > target:
            self.vehicles.sort(key=lambda v: v.p)
            self.vehicles.pop()                                          # เกิน -> เอาคันหน้าสุดออก
        guard = 0
        while len(self.vehicles) < target and guard < len(LANES) + 1:
            if not self._try_spawn():
                guard += 1

    def step(self, dt: float, avg_speed: float) -> None:
        for li in range(len(LANES)):
            lane_cars = sorted((v for v in self.vehicles if v.lane == li), key=lambda v: v.p)
            for i in range(len(lane_cars) - 1, -1, -1):     # คันหน้าสุด (p มาก) อัปเดตก่อน
                v = lane_cars[i]
                desired = max(1.0, avg_speed * v.factor)
                free_p = v.p + (desired / 3.6) * dt
                if i == len(lane_cars) - 1:
                    new_p = free_p                                       # คันหน้าสุด วิ่งอิสระ
                else:
                    new_p = min(free_p, lane_cars[i + 1].p - MIN_GAP)    # ไม่เข้าใกล้เกิน MIN_GAP
                new_p = max(new_p, v.p)                                  # ห้ามถอยหลัง
                v.speed += ((new_p - v.p) / dt * 3.6 - v.speed) * SPEED_EASE
                v.p = new_p
                half = LANE_HALF_WIDTH * 0.5
                v.lat += (LANES[li] - v.lat) * LANE_DRIFT + random.uniform(-LANE_JITTER, LANE_JITTER)
                v.lat = max(LANES[li] - half, min(LANES[li] + half, v.lat))

    def as_raw(self) -> list[dict]:
        """คืน dict รูปแบบภายใน (ให้ contract.py แปลงต่อ): x->pos.x, y->pos.z (พิกัดโลก)"""
        out = []
        for v in self.vehicles:
            x, z = _world_xz(v.p, v.lat)
            out.append({"id": v.tid, "type": v.type, "x": x, "y": z, "speed_kmh": max(0.0, v.speed)})
        return out


def _make_type_picker(type_hist: dict[str, int]):
    """สุ่มชนิดรถจำลองตามสัดส่วนชนิดที่ตรวจเจอจริง (map ให้อยู่ใน enum ของสัญญา)"""
    weights: dict[str, int] = defaultdict(int)
    for name, n in type_hist.items():
        mapped = contract.TYPE_MAP.get(name)
        if mapped:
            weights[mapped] += n
    if not weights:
        return lambda: "car"
    types = list(weights.keys())
    w = list(weights.values())

    def pick() -> str:
        return random.choices(types, weights=w, k=1)[0]

    return pick


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
    พร้อมเขียนวิดีโอ annotate (มีเส้น 2 เส้น + ตัวนับ + ความเร็ว) ที่ out_video_path
    """
    sample_step = max(1, round(fps / stream_hz)) if stream_hz > 0 else 1
    dt = sample_step / fps  # วินาทีจริงต่อ 1 เฟรมที่ส่ง

    prev_cy: dict[int, float] = {}
    cross_frame: dict[int, dict] = defaultdict(dict)  # tid -> {"A": idx, "B": idx}
    counted: set[int] = set()
    measured: set[int] = set()
    speeds: list[float] = []           # ความเร็วที่วัดได้ (km/h)
    type_hist: dict[str, int] = defaultdict(int)

    pop = PopulationManager()
    contract_frames: list[dict] = []
    max_speed = 0.0

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
                cy = (y1 + y2) / 2.0
                current_ids.add(tid)
                type_hist[CLASS_NAMES.get(cls, "car")] += 1

                # ตรวจการข้ามเส้น (sign change ของ cy - line_y) ทั้งสองทิศ
                if tid in prev_cy:
                    p = prev_cy[tid]
                    for name, ly in (("A", line_a_y), ("B", line_b_y)):
                        if (p - ly) * (cy - ly) < 0 and name not in cross_frame[tid]:
                            cross_frame[tid][name] = idx
                    # ครบ 2 เส้น -> คำนวณความเร็วครั้งเดียวต่อคัน
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

                # นับครั้งเดียวต่อ trackId ที่ข้ามเส้น A (กันนับซ้ำตอนคร่อมเส้น)
                if "A" in cross_frame[tid] and tid not in counted:
                    counted.add(tid)

                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 200, 255), 2)

        # ความเร็วเฉลี่ยล่าสุด (fallback = DEFAULT ถ้ายังวัดไม่ได้)
        avg_speed = float(np.mean(speeds[-SPEED_SMOOTH:])) if speeds else DEFAULT_SPEED

        # วาดเส้น 2 เส้น + สถิติ
        cv2.line(img, (0, int(line_a_y)), (w, int(line_a_y)), (80, 220, 120), 2)
        cv2.line(img, (0, int(line_b_y)), (w, int(line_b_y)), (245, 165, 36), 2)
        cv2.putText(img, "A", (8, int(line_a_y) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 220, 120), 2)
        cv2.putText(img, "B", (8, int(line_b_y) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (245, 165, 36), 2)
        hud = f"count(total)={len(counted)}  now={len(current_ids)}  avg={avg_speed:4.1f}km/h"
        cv2.rectangle(img, (0, 0), (max(360, 9 * len(hud)), 28), (20, 24, 30), -1)
        cv2.putText(img, hud, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (230, 237, 243), 1, cv2.LINE_AA)
        writer.write(img)

        # ทุก sample_step: จำนวนจริง (now) -> population -> contract frame
        if idx % sample_step == 0:
            pick = _make_type_picker(type_hist)
            pop.reconcile(len(current_ids), pick)
            pop.step(dt, avg_speed)
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
            "mode": "count",
            "unique_vehicles": len(counted),   # นับข้ามเส้นจริง
            "measured_speeds": len(speeds),
            "avg_speed_kmh": round(avg_all, 2),
            "max_speed_kmh": round(max_speed, 2),
            "distance_m": distance_m,
            "total_frames": len(contract_frames),
            "fps": fps,
        },
    }
