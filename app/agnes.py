import httpx
from .config import settings

class AgnesError(RuntimeError):
    pass

def _headers():
    if not settings.agnes_api_key:
        raise AgnesError("AGNES_API_KEY is not configured on the server.")
    return {"Authorization": f"Bearer {settings.agnes_api_key}", "Content-Type": "application/json"}

def _video_dimensions(aspect_ratio: str):
    return {"16:9": (1152, 648), "9:16": (648, 1152), "1:1": (768, 768)}[aspect_ratio]

async def create_video(prompt: str, aspect_ratio: str, duration_seconds: int) -> str:
    width, height = _video_dimensions(aspect_ratio)
    num_frames = max(49, min(481, duration_seconds * 24 + 1))
    payload = {"model": settings.agnes_video_model, "prompt": prompt, "width": width,
               "height": height, "num_frames": num_frames, "frame_rate": 24}
    url = f"{settings.agnes_api_root.rstrip('/')}/v1/videos"
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, headers=_headers(), json=payload)
    if response.is_error:
        raise AgnesError(f"Agnes video request failed ({response.status_code}): {response.text[:500]}")
    data = response.json()
    video_id = data.get("video_id") or data.get("id")
    if not video_id:
        raise AgnesError(f"Agnes response did not include video_id. Keys: {list(data.keys())}")
    return str(video_id)

async def get_video(video_id: str) -> dict:
    url = f"{settings.agnes_api_root.rstrip('/')}/agnesapi"
    async with httpx.AsyncClient(timeout=45) as client:
        response = await client.get(url, headers=_headers(), params={"video_id": video_id})
    if response.is_error:
        raise AgnesError(f"Agnes status request failed ({response.status_code}): {response.text[:500]}")
    return response.json()
