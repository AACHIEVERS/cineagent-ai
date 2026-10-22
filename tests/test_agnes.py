import asyncio

from app import agnes
from app.config import settings


class FakeResponse:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text
        self.is_error = status_code >= 400

    def json(self):
        return self._payload


class FakeAsyncClient:
    calls = []

    def __init__(self, *args, **kwargs):
        self.calls = FakeAsyncClient.calls
        self.calls.append({"timeout": kwargs.get("timeout")})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        self.calls.append({"method": "POST", "url": url, **kwargs})
        return FakeResponse({"video_id": "video_test_123", "status": "queued"})

    async def get(self, url, **kwargs):
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return FakeResponse({"video_id": "video_test_123", "status": "completed", "url": "https://example.test/video.mp4"})


def test_create_video_uses_agnes_video_25_schema(monkeypatch):
    monkeypatch.setattr(settings, "agnes_api_key", "test-key")
    monkeypatch.setattr(settings, "agnes_api_root", "https://apihub.agnes-ai.com")
    monkeypatch.setattr(settings, "agnes_video_model", "agnes-video-2.5")
    monkeypatch.setattr(agnes.httpx, "AsyncClient", FakeAsyncClient)
    FakeAsyncClient.calls = []

    video_id = asyncio.run(agnes.create_video("A fox in a misty forest", "16:9", 5))

    assert video_id == "video_test_123"
    request = next(call for call in FakeAsyncClient.calls if call.get("method") == "POST")
    assert request["url"] == "https://apihub.agnes-ai.com/v1/videos"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["json"]["model"] == "agnes-video-2.5"
    assert request["json"]["seconds"] == 5
    assert request["json"]["aspect_ratio"] == "16:9"
    assert request["json"]["size"] == "720P"
    assert "num_frames" not in request["json"]


def test_get_video_polls_with_video_id_and_model_name(monkeypatch):
    monkeypatch.setattr(settings, "agnes_api_key", "test-key")
    monkeypatch.setattr(settings, "agnes_api_root", "https://apihub.agnes-ai.com")
    monkeypatch.setattr(settings, "agnes_video_model", "agnes-video-2.5")
    monkeypatch.setattr(agnes.httpx, "AsyncClient", FakeAsyncClient)
    FakeAsyncClient.calls = []

    result = asyncio.run(agnes.get_video("video_test_123"))

    request = next(call for call in FakeAsyncClient.calls if call.get("method") == "GET")
    assert request["url"] == "https://apihub.agnes-ai.com/agnesapi"
    assert request["params"] == {
        "video_id": "video_test_123",
        "model_name": "agnes-video-2.5",
    }
    assert result["status"] == "completed"


def test_create_video_rejects_duration_outside_provider_limits():
    try:
        asyncio.run(agnes.create_video("A fox", "16:9", 20))
    except agnes.AgnesError as exc:
        assert "4 and 12 seconds" in str(exc)
    else:
        raise AssertionError("Expected AgnesError for unsupported duration")
