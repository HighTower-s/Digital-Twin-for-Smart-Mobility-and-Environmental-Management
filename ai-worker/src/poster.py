"""ส่ง spawn event เข้า backend ผ่าน HTTP POST — ไม่บล็อกการนับถ้า backend ล่ม

หลักการเดียวกับ SpawnEventWriter: การนับต้องไม่มีวันหยุดเพราะปัญหาที่ปลายทาง
ส่งไม่สำเร็จ (timeout, connection refused, HTTP 400/500) = log แล้วไปต่อ ไม่ raise
"""

from __future__ import annotations

from typing import Any

import httpx

POST_TIMEOUT_SEC = 3.0


class BackendPoster:
    """POST payload ไปที่ {backend_url}/api/ingest ทีละ event"""

    def __init__(
        self,
        backend_url: str,
        timeout: float = POST_TIMEOUT_SEC,
        client: httpx.Client | None = None,
    ) -> None:
        """client: ใส่เองเพื่อเทส (เช่น httpx.MockTransport) — ปกติปล่อยว่างให้สร้างจริง"""
        self._url = f"{backend_url.rstrip('/')}/api/ingest"
        self._client = client or httpx.Client(timeout=timeout)
        self.sent = 0
        self.failed = 0

    def post(self, payload: dict[str, Any]) -> bool:
        """ส่ง payload คืน True ถ้า backend ตอบ 200 — error ใด ๆ log แล้วคืน False"""
        try:
            response = self._client.post(self._url, json=payload)
        except httpx.HTTPError as exc:
            self.failed += 1
            print(f"[poster] ส่งเข้า backend ไม่ได้ ({self._url}): {exc}", flush=True)
            return False

        if response.status_code != 200:
            self.failed += 1
            print(
                f"[poster] backend ปฏิเสธ ({response.status_code}): {response.text[:200]}",
                flush=True,
            )
            return False

        self.sent += 1
        return True

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> BackendPoster:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
