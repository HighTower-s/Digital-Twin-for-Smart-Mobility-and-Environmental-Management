"""เล่นซ้ำ events.jsonl ตามจังหวะเวลาจริงของวิดีโอต้นฉบับ — สำหรับเดโม/ทดสอบ

    python -m src.replay                              พิมพ์ event ออกจอตามจังหวะ (ไม่ส่งเข้า backend)
    python -m src.replay --backend                     ส่งเข้า backend ด้วย (ต้องรัน backend ไว้ก่อน)
    python -m src.replay --file other/events.jsonl     ใช้ไฟล์อื่น

ใช้ src/pacer.py จัดจังหวะ — ดู ai-worker/CLAUDE.md ว่าทำไม pacing ถึงจำเป็นเฉพาะ
ตอนเดโมด้วยไฟล์วิดีโอ (Prototype) เท่านั้น ไม่เกี่ยวกับตอนเป็นกล้องสด (RTSP)
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from src.constants import DEFAULT_BACKEND_URL
from src.pacer import replay_paced
from src.poster import BackendPoster

HERE = Path(__file__).parent
AI_WORKER_ROOT = HERE.parent
DEFAULT_EVENTS_PATH = AI_WORKER_ROOT / "data" / "output_results" / "events.jsonl"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="เล่นซ้ำ events.jsonl ตามจังหวะเวลาจริงของวิดีโอต้นฉบับ"
    )
    parser.add_argument(
        "--file", type=Path, default=DEFAULT_EVENTS_PATH, help="path ไปยัง events.jsonl"
    )
    parser.add_argument(
        "--backend", action="store_true", help="ส่งเข้า backend ด้วย (ไม่ใช่แค่พิมพ์)"
    )
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    return parser.parse_args(argv)


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(
            f"ไม่พบไฟล์: {path.resolve()}\n  รัน python -m src.main ก่อนเพื่อสร้าง events.jsonl"
        )

    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    events = load_events(args.file)

    if not events:
        print(f"[replay] {args.file} ว่างเปล่า ไม่มีอะไรให้เล่นซ้ำ")
        return 0

    total_span = events[-1]["videoTimeSec"] - events[0]["videoTimeSec"]
    print(f"[replay] โหลด {len(events)} events จาก {args.file}")
    print(f"[replay] ช่วงเวลาตามวิดีโอ: {total_span:.2f} วินาที")
    if args.backend:
        print(f"[replay] จะส่งเข้า backend ที่ {args.backend_url}")
    print()

    poster = BackendPoster(args.backend_url) if args.backend else None

    def on_event(event: dict[str, Any]) -> None:
        print(json.dumps(event, ensure_ascii=False))
        if poster is not None:
            poster.post(event)

    replay_paced(events, on_event)

    print()
    if poster is not None:
        print(f"[replay] ส่งเข้า backend: {poster.sent} สำเร็จ | {poster.failed} ล้มเหลว")
        poster.close()
    print(
        f"[replay] เล่นจบ — {len(events)} events ใน {total_span:.2f} วินาที (ตามจังหวะวิดีโอต้นฉบับ)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
