import httpx
from .config import settings


class AgnesError(RuntimeError):
    """Sanitized provider/API error suitable for surfacing to the app UI."""


def _headers():
    if not settings.agnes_api_key:
        raise AgnesError("AGNES_API_KEY is not configured on the server.")
    return {
        "Authorization": f"Bearer {settings.agnes_api_key}",
        "Content-Type": "application/json",
    }


async def create_video(prompt: str, aspect_ratio: str, duration_seconds: int) -> str:
    """Submit a text-to-video job using the Agnes Video 2.5 request schema."""
    if not 4 <= duration_seconds <= 12:
        raise AgnesError("Agnes Video 2.5 supports clips between 4 and 12 seconds.")
    if aspect_ratio not in {"16:9", "9:16", "1:1"}:
        raise AgnesError("Unsupported aspect ratio.")

    payload = {
        "model": settings.agnes_video_model,
        "prompt": prompt,
        "mode": "text",
        "seconds": duration_seconds,
        "size": "720P",
        "aspect_ratio": aspect_ratio,
        "n": 1,
    }
    url = f"{settings.agnes_api_root.rstrip('/')}/v1/videos"
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(url, headers=_headers(), json=payload)
    except httpx.HTTPError as exc:
        raise AgnesError(f"Could not connect to Agnes video API: {type(exc).__name__}") from exc

    if response.is_error:
        raise AgnesError(
            f"Agnes video request failed ({response.status_code}): {response.text[:500]}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise AgnesError("Agnes video API returned invalid JSON.") from exc

    video_id = data.get("video_id") or data.get("id")
    if not video_id:
        raise AgnesError(
            f"Agnes response did not include video_id or id. Keys: {list(data.keys())}"
        )
    return str(video_id)


async def get_video(video_id: str) -> dict:
    """Poll the documented Agnes status endpoint using video_id and model_name."""
    url = f"{settings.agnes_api_root.rstrip('/')}/agnesapi"
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.get(
                url,
                headers=_headers(),
                params={
                    "video_id": video_id,
                    "model_name": settings.agnes_video_model,
                },
            )
    except httpx.HTTPError as exc:
        raise AgnesError(f"Could not connect to Agnes status API: {type(exc).__name__}") from exc

    if response.is_error:
        raise AgnesError(
            f"Agnes status request failed ({response.status_code}): {response.text[:500]}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise AgnesError("Agnes status API returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise AgnesError("Agnes status API returned an unexpected response shape.")
    return data
