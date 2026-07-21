"""
Unit tests สำหรับตรรกะจำลอง (count-event) — ไม่ต้องรัน YOLO/torch
รัน:  python test_count_sim.py   (หรือ pytest)
ครอบคลุม: lane_index_from_x, speed_for_type, PopulationManager (spawn/step/despawn/
cap/car-following/เลนตรง) และ output ผ่าน contract.to_contract_frame
"""

import random

import contract
import count_detector as cd


def test_speed_for_type():
    assert cd.speed_for_type("car") == cd.SPEED_BY_TYPE.get("car", cd.DEFAULT_SPEED)
    assert cd.speed_for_type("motorcycle") == cd.SPEED_BY_TYPE.get("motorcycle", cd.DEFAULT_SPEED)
    # ชนิดที่ไม่รู้จัก -> fallback (car หรือ DEFAULT)
    assert cd.speed_for_type("spaceship") > 0


def test_lane_index_equal_split():
    old = cd.LANE_X_BOUNDS
    cd.LANE_X_BOUNDS = ()          # บังคับใช้โหมดแบ่งเท่าๆ กัน
    cd.ROAD_X_MIN, cd.ROAD_X_MAX = 0.0, 900.0
    n = len(cd.LANES)              # 3 เลน -> ช่วงละ 300 px
    assert cd.lane_index_from_x(10) == 0
    assert cd.lane_index_from_x(450) == 1
    assert cd.lane_index_from_x(890) == n - 1
    assert cd.lane_index_from_x(-50) == 0        # นอกช่วงซ้าย -> clamp
    assert cd.lane_index_from_x(99999) == n - 1  # นอกช่วงขวา -> clamp
    cd.LANE_X_BOUNDS = old


def test_lane_index_explicit_bounds():
    old = cd.LANE_X_BOUNDS
    cd.LANE_X_BOUNDS = (500.0, 760.0, 1010.0, 1260.0)  # 3 เลน
    assert cd.lane_index_from_x(600) == 0
    assert cd.lane_index_from_x(800) == 1
    assert cd.lane_index_from_x(1100) == 2
    assert cd.lane_index_from_x(100) == 0     # ซ้ายสุด
    assert cd.lane_index_from_x(5000) == 2    # ขวาสุด
    cd.LANE_X_BOUNDS = old


def test_in_road_span_one_side():
    old = cd.LANE_X_BOUNDS
    cd.LANE_X_BOUNDS = (760.0, 900.0, 1040.0, 1180.0)  # ฝั่งเดียว 3 เลน
    assert cd.in_road_span(800) is True     # ในช่วง
    assert cd.in_road_span(1180) is True     # ขอบขวาพอดี
    assert cd.in_road_span(500) is False     # ซ้ายของช่วง = อีกฝั่ง -> ข้าม
    assert cd.in_road_span(1500) is False    # ขวาของช่วง = อีกฝั่ง -> ข้าม
    cd.LANE_X_BOUNDS = ()
    cd.ROAD_X_MIN, cd.ROAD_X_MAX = 0.0, 1920.0
    assert cd.in_road_span(-5) is False and cd.in_road_span(960) is True
    cd.LANE_X_BOUNDS = old


def test_spawn_lands_in_correct_lane():
    random.seed(0)
    pop = cd.PopulationManager()
    for li in range(len(cd.LANES)):
        pop.request_spawn(tid=li, vtype="car", lane_idx=li, target=40.0)
    pop.step(0.5)  # flush + ขับ 1 สเต็ป
    assert len(pop.vehicles) == len(cd.LANES)
    for raw in pop.as_raw():
        v = next(v for v in pop.vehicles if v.tid == raw["id"])
        expected_x = cd.LANES[v.lane]
        # x ควรอยู่ในเลนของมัน (บวกลบ drift ครึ่งเลน)
        assert abs(raw["x"] - expected_x) <= cd.LANE_HALF_WIDTH + 1e-6, (raw["x"], expected_x)


def test_car_following_keeps_min_gap():
    random.seed(1)
    pop = cd.PopulationManager()
    # ยัด 5 คันเลนเดียวกัน -> pending จะทยอยปล่อยเมื่อต้นถนนว่าง
    for i in range(5):
        pop.request_spawn(tid=i, vtype="car", lane_idx=0, target=40.0)
    for _ in range(200):
        pop.step(0.2)
    ps = sorted(v.p for v in pop.vehicles if v.lane == 0)
    for a, b in zip(ps, ps[1:]):
        assert b - a >= cd.MIN_GAP - 0.5, (a, b)   # เว้นระยะขั้นต่ำ (เผื่อ ease เล็กน้อย)


def test_despawn_past_end():
    random.seed(2)
    pop = cd.PopulationManager()
    pop.request_spawn(tid=1, vtype="car", lane_idx=0, target=120.0)
    pop.step(0.1)  # spawn
    assert len(pop.vehicles) == 1
    for _ in range(2000):  # ขับไกลจนพ้นปลายถนน
        pop.step(0.5)
    assert len(pop.vehicles) == 0


def test_cap_max_vehicles():
    random.seed(3)
    pop = cd.PopulationManager()
    for i in range(cd.contract.MAX_VEHICLES + 40):
        pop.request_spawn(tid=i, vtype="car", lane_idx=i % len(cd.LANES), target=40.0)
    for _ in range(300):
        pop.step(0.3)
    assert len(pop.vehicles) <= contract.MAX_VEHICLES


def test_output_passes_contract():
    random.seed(4)
    pop = cd.PopulationManager()
    for i, t in enumerate(["car", "truck", "motorcycle"]):
        pop.request_spawn(tid=i, vtype=t, lane_idx=i % len(cd.LANES), target=40.0)
    pop.step(0.5)
    frame = contract.to_contract_frame(pop.as_raw(), frame_count=0, camera_id="cam-test")
    assert len(frame["vehicles"]) <= contract.MAX_VEHICLES
    for veh in frame["vehicles"]:
        assert veh["type"] in contract.CONTRACT_TYPES
        assert veh["position"]["y"] == 0.0
        assert 0.0 <= veh["speed"] <= contract.MAX_SPEED
        assert veh["position"]["x"] == veh["position"]["x"]  # ไม่ NaN
        assert veh["position"]["z"] == veh["position"]["z"]


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")


if __name__ == "__main__":
    _run_all()
