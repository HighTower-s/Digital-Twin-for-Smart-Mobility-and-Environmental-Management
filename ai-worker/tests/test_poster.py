"""เทส poster.py — ใช้ httpx.MockTransport แทน network จริง ไม่มี request ออกนอกเครื่อง"""

import httpx

from src.poster import BackendPoster

PAYLOAD = {
    "schema": "spawn-event/0.2-draft",
    "timestamp": "2026-08-10T15:42:47.671Z",
    "cameraId": "cam-chalongkrung-01",
    "trackId": "car-0025",
    "type": "car",
    "direction": "out",
    "confidence": 0.757,
}


def make_poster(handler, backend_url: str = "http://localhost:3000") -> BackendPoster:
    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return BackendPoster(backend_url, client=client)


def test_post_success_returns_true_and_increments_sent():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://localhost:3000/api/ingest"
        return httpx.Response(200, json={"ok": True})

    poster = make_poster(handler)
    assert poster.post(PAYLOAD) is True
    assert poster.sent == 1
    assert poster.failed == 0


def test_post_strips_trailing_slash_from_backend_url():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://localhost:3000/api/ingest"
        return httpx.Response(200, json={"ok": True})

    poster = make_poster(handler, backend_url="http://localhost:3000/")
    assert poster.post(PAYLOAD) is True


def test_post_sends_payload_unchanged_as_json_body():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    poster = make_poster(handler)
    poster.post(PAYLOAD)
    assert captured["body"] == PAYLOAD


def test_post_rejection_returns_false_and_increments_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "type is not valid"})

    poster = make_poster(handler)
    assert poster.post(PAYLOAD) is False
    assert poster.sent == 0
    assert poster.failed == 1


def test_post_network_error_returns_false_and_increments_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    poster = make_poster(handler)
    assert poster.post(PAYLOAD) is False
    assert poster.sent == 0
    assert poster.failed == 1


def test_post_does_not_raise_on_failure():
    """หลักการสำคัญ: backend ล่มต้องไม่ทำให้ main loop ของ ai-worker หยุด"""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    poster = make_poster(handler)
    poster.post(PAYLOAD)  # ต้องไม่ raise


def test_multiple_posts_accumulate_sent_and_failed_counts():
    responses = iter([httpx.Response(200), httpx.Response(400), httpx.Response(200)])

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    poster = make_poster(handler)
    poster.post(PAYLOAD)
    poster.post(PAYLOAD)
    poster.post(PAYLOAD)
    assert poster.sent == 2
    assert poster.failed == 1


def test_close_closes_underlying_client():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    poster = make_poster(handler)
    poster.close()
    assert poster._client.is_closed


def test_context_manager_closes_on_exit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    with BackendPoster("http://localhost:3000", client=client) as poster:
        poster.post(PAYLOAD)
    assert client.is_closed
