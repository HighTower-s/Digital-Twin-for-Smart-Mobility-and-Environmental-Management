"""เทส config.py — โมดูลบริสุทธิ์ ทดสอบด้วย dict ธรรมดา ไม่ต้องมีไฟล์ config.yaml จริง"""

from pathlib import Path

import pytest

from src.config import ConfigError, auto_zones, build_run_config

FRAME_SIZE = (1920, 1080)
FAKE_PATH = Path("config.yaml")


def base_raw(**overrides):
    raw = {"video": "data/input_videos/clip.mp4"}
    raw.update(overrides)
    return raw


# ==================================================== auto_zones


def test_auto_zones_returns_in_and_out():
    zones = auto_zones(FRAME_SIZE)
    names = {z.name for z in zones}
    assert names == {"in", "out"}


def test_auto_zones_in_is_right_half_toward():
    zones = {z.name: z for z in auto_zones(FRAME_SIZE)}
    assert zones["in"].expected_direction == "toward"
    assert all(x >= FRAME_SIZE[0] / 2 for x, _ in zones["in"].polygon)


def test_auto_zones_out_is_left_half_away():
    zones = {z.name: z for z in auto_zones(FRAME_SIZE)}
    assert zones["out"].expected_direction == "away"
    assert all(x <= FRAME_SIZE[0] / 2 for x, _ in zones["out"].polygon)


# ==================================================== build_run_config — ค่าปกติ


def test_build_run_config_requires_video():
    with pytest.raises(ConfigError, match="video"):
        build_run_config({}, FRAME_SIZE, FAKE_PATH)


def test_build_run_config_uses_defaults_when_omitted():
    cfg = build_run_config(base_raw(), FRAME_SIZE, FAKE_PATH)
    assert cfg.imgsz == 640
    assert 0.0 < cfg.conf_threshold < 1.0
    assert cfg.is_auto is True
    assert len(cfg.zones) == 2


def test_build_run_config_reads_overrides():
    cfg = build_run_config(
        base_raw(imgsz=1280, conf=0.5, camera_id="cam-x", max_frames=900, emit_preview=20),
        FRAME_SIZE,
        FAKE_PATH,
    )
    assert cfg.imgsz == 1280
    assert cfg.conf_threshold == 0.5
    assert cfg.camera_id == "cam-x"
    assert cfg.max_frames == 900
    assert cfg.emit_preview == 20


def test_build_run_config_rejects_bad_imgsz():
    with pytest.raises(ConfigError, match="imgsz"):
        build_run_config(base_raw(imgsz=641), FRAME_SIZE, FAKE_PATH)


def test_build_run_config_rejects_out_of_range_conf():
    with pytest.raises(ConfigError, match="conf"):
        build_run_config(base_raw(conf=1.5), FRAME_SIZE, FAKE_PATH)


# ==================================================== zones ที่ผู้ใช้กำหนดเอง


VALID_ZONE = {
    "name": "in",
    "expectedDirection": "toward",
    "polygon": [[0, 0], [200, 0], [200, 200], [0, 200]],
    "line": [[10, 100], [190, 100]],
}


def test_custom_zones_parsed_correctly():
    cfg = build_run_config(base_raw(zones=[VALID_ZONE]), FRAME_SIZE, FAKE_PATH)
    assert cfg.is_auto is False
    assert len(cfg.zones) == 1
    assert cfg.zones[0].name == "in"


def test_custom_zones_reject_empty_list():
    with pytest.raises(ConfigError, match="zones"):
        build_run_config(base_raw(zones=[]), FRAME_SIZE, FAKE_PATH)


def test_custom_zones_reject_duplicate_names():
    with pytest.raises(ConfigError, match="ซ้ำ"):
        build_run_config(base_raw(zones=[VALID_ZONE, VALID_ZONE]), FRAME_SIZE, FAKE_PATH)


def test_custom_zones_reject_bad_direction():
    bad = {**VALID_ZONE, "expectedDirection": "sideways"}
    with pytest.raises(ConfigError, match="expectedDirection"):
        build_run_config(base_raw(zones=[bad]), FRAME_SIZE, FAKE_PATH)


def test_custom_zones_reject_polygon_with_too_few_points():
    bad = {**VALID_ZONE, "polygon": [[0, 0], [1, 1]]}
    with pytest.raises(ConfigError, match="polygon"):
        build_run_config(base_raw(zones=[bad]), FRAME_SIZE, FAKE_PATH)


def test_custom_zones_reject_line_with_wrong_point_count():
    bad = {**VALID_ZONE, "line": [[10, 100]]}
    with pytest.raises(ConfigError, match="line"):
        build_run_config(base_raw(zones=[bad]), FRAME_SIZE, FAKE_PATH)


def test_custom_zones_reject_zero_length_line():
    bad = {**VALID_ZONE, "line": [[10, 100], [10, 100]]}
    with pytest.raises(ConfigError, match="ศูนย์"):
        build_run_config(base_raw(zones=[bad]), FRAME_SIZE, FAKE_PATH)


def test_custom_zones_reject_near_vertical_line():
    bad = {**VALID_ZONE, "line": [[100, 0], [101, 200]]}
    with pytest.raises(ConfigError, match="ดิ่ง"):
        build_run_config(base_raw(zones=[bad]), FRAME_SIZE, FAKE_PATH)


def test_custom_zones_reject_line_outside_polygon():
    bad = {**VALID_ZONE, "line": [[1000, 1000], [1100, 1000]]}
    with pytest.raises(ConfigError, match="นอก polygon"):
        build_run_config(base_raw(zones=[bad]), FRAME_SIZE, FAKE_PATH)
