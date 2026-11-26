# CineAgent AI — Video Production MVP

CineAgent AI contains two separate video workflows:
- **Cinematic Mode:** create short-film projects and submit video jobs to Agnes AI.
- **Digital Host Mode:** generate a presenter script with local Ollama, synthesize speech with Kokoro, animate a portrait with SadTalker, create subtitles, and export platform-specific video formats with FFmpeg.

## Requirements
- Python 3.11+
- Cinematic Mode: Agnes AI API key with video access.
- Digital Host Mode: Kokoro, SadTalker and their model weights; a CUDA-capable NVIDIA GPU is strongly recommended. CPU rendering may be very slow.
- Local Ollama for AI script drafting.
- FFmpeg for 9:16 and 16:9 exports.
- Disk space for model weights and generated videos.

## Run the application
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` for the workspace and `http://127.0.0.1:8000/docs` for API docs.

## Digital Host setup
1. Install SadTalker and its model weights: https://github.com/OpenTalker/SadTalker
2. Set `SADTALKER_DIR` in `.env` to the directory containing `inference.py`.
3. Install Kokoro dependencies: `pip install -r requirements-host.txt`. The first run may download model weights.
4. Install Ollama: https://ollama.com/ and pull a local model, for example `ollama pull qwen2.5:3b`.
5. Install FFmpeg and ensure its executable is on PATH.
6. Set `OLLAMA_API_ROOT`, `OLLAMA_MODEL`, and `SADTALKER_DIR` in `.env`.
7. Start the FastAPI app from the repository root.

Default local settings:
- Ollama model: `qwen2.5:3b`
- Chinese Kokoro voice: `zf_xiaobei` (language code `z`)
- English Kokoro voice: `af_heart` (language code `a`)

## Digital Host production flow
1. Enter a topic and use **AI Generate Script**. The app calls the local Ollama server; no paid text-generation API is used.
2. Upload a front-facing portrait (JPG, PNG or WEBP; maximum 12 MB).
3. Select Chinese or English and choose a Kokoro voice.
4. Submit the render. The local worker generates a WAV voice track, an SRT subtitle file and a SadTalker talking-head MP4.
5. Preview the master MP4 and download its subtitle file.
6. Export 9:16 vertical video for TikTok/Shorts and 16:9 horizontal video for YouTube using local FFmpeg.

Generated files are stored under `output/hosts/<job-id>/` and served through `/outputs/...`.

## Digital Host API
- `POST /api/digital-host/script` — JSON: `topic`, optional `language` (`zh` or `en`); drafts a script with local Ollama.
- `POST /api/digital-host/portraits` — multipart image upload; returns a server-side portrait path.
- `POST /api/digital-host/jobs` — JSON: `title`, `script`, `portrait_path`, optional `language` and `voice`.
- `GET /api/digital-host/jobs/{job_id}` — read job status and output URLs.
- `GET /api/digital-host/jobs/{job_id}/export?aspect_ratio=9:16` — export a vertical MP4; use `16:9` for horizontal.

The MVP uses FastAPI background tasks and local disk. Before public or multi-user deployment, add authentication, authorization, durable job queues, quotas, file retention policies and object storage.

## Cinematic video flow
1. `POST /api/projects` — create a project.
2. `POST /api/projects/{project_id}/generate` — submit to Agnes.
3. `POST /api/projects/{project_id}/refresh` — poll the provider task.
4. When Agnes reports completion and returns a video URL, the UI displays a preview.

The Agnes request uses `model`, `prompt`, `mode=text`, `seconds` (4–12), `size=720P`, `aspect_ratio` and `n=1`. Configure the model in `.env`.

## Tests
Run `pytest -q`. Agnes integration tests use a mocked HTTP client and do not consume API quota. A real Agnes end-to-end test requires a valid API key. Digital Host rendering requires the local Kokoro and SadTalker models and is not part of the lightweight test suite.

## Security, licensing and cost
- Never expose `AGNES_API_KEY` in browser code or commit `.env`.
- Open-source software can avoid per-generation API charges, but model downloads, electricity, GPU time and storage are not literally cost-free.
- Verify licenses for source code, model weights, voices and portraits before commercial use.
- The MVP has no user authentication. Do not expose it publicly without access controls, rate limits, upload limits and storage lifecycle management.
