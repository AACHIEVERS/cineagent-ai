# CineAgent AI — MVP

A small, server-side FastAPI starter for cinematic short-video generation using Agnes AI. It starts with one path: create a video project, submit a generation job, poll status, and retrieve the provider result. Storyboard and persistent character-memory orchestration are planned next.

## Requirements
- Python 3.11+
- Agnes AI API key
- FFmpeg is optional for future post-production

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set AGNES_API_KEY in .env
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000` for the UI and `http://127.0.0.1:8000/docs` for API docs.

## API
- `GET /api/health`
- `POST /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/generate`
- `POST /api/projects/{project_id}/refresh`

## Security and MVP limits
- Never expose `AGNES_API_KEY` in browser code or commit `.env`.
- Use managed secrets, authentication, rate limits, quotas and object storage before public launch.
- SQLite stores metadata only; generated video files are not persisted by this MVP.
- Confirm the exact model name, request parameters, pricing and status response shape in your Agnes account before production use.
