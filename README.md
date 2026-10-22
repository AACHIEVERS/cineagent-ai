# CineAgent AI — MVP

A small, server-side FastAPI app for cinematic short-video generation with Agnes AI. The MVP flow is: create a project, submit an asynchronous video job, poll status, then preview the returned video URL. The default model is Agnes Video 2.5 Flash at 720P; storyboards, persistent character memory, and post-production are planned next.

## Requirements
- Python 3.11+
- Agnes AI API key with video access
- Optional FFmpeg for future post-production

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set AGNES_API_KEY in .env (never commit this file)
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` for the UI and `http://127.0.0.1:8000/docs` for API docs.

## Video flow
1. `POST /api/projects` — create a project.
2. `POST /api/projects/{project_id}/generate` — submit to `POST https://apihub.agnes-ai.com/v1/videos`.
3. `POST /api/projects/{project_id}/refresh` — poll `GET /agnesapi?video_id=...&model_name=...`.
4. When Agnes returns `completed` and a video URL, the page displays a playable preview and an open/download link.

The Agnes Video 2.5 request uses `model`, `prompt`, `mode=text`, `seconds` (4–12), `size=720P`, `aspect_ratio`, and `n=1`. Change `AGNES_VIDEO_MODEL` to `agnes-video-2.5` if that model is enabled for your account and you need its higher-resolution options.

## API
- `GET /api/health` — confirms the backend is reachable and whether an API key is configured (never returns the key).
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/generate`
- `POST /api/projects/{project_id}/refresh`

## Tests
Run `pytest -q`. Agnes integration tests use a mocked HTTP client, so they validate request/response wiring without spending quota or requiring a real API key. A real end-to-end video test still requires a valid Agnes key in the backend environment.

## Security and MVP limits
- Never expose `AGNES_API_KEY` in browser code or commit `.env`.
- Set the key as a secret/environment variable on the backend host.
- Add authentication, rate limits, per-user quotas and persistent object storage before public launch.
- SQLite stores project metadata only; this MVP does not copy generated videos into owned storage. The preview links to Agnes's returned URL.
