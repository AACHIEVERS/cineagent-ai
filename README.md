# CineAgent AI — Video Production MVP

CineAgent AI provides two independent production paths:
- **Cinematic Mode:** create a project and submit a short video generation job to Agnes AI.
- **Digital Host Mode:** upload a portrait, enter a script, synthesize speech locally with Kokoro, animate the portrait with SadTalker, and retrieve an MP4 plus an SRT subtitle file.

## Requirements
- Python 3.11+
- For Cinematic Mode: an Agnes AI API key with video access.
- For Digital Host Mode: a machine with a supported PyTorch environment, Kokoro dependencies/model weights, SadTalker and its model weights. A CUDA-capable NVIDIA GPU is strongly recommended. CPU rendering may be very slow.
- Disk space for local model weights and generated videos.

## Run the application
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set AGNES_API_KEY only if you plan to use Cinematic Mode.
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` for the workspace and `http://127.0.0.1:8000/docs` for API docs.

## Digital Host local setup
1. Install and configure SadTalker using its official instructions: https://github.com/OpenTalker/SadTalker
2. Set `SADTALKER_DIR` in `.env` to the folder containing SadTalker's `inference.py`.
3. Install the optional Kokoro speech dependencies:
   ```bash
   pip install -r requirements-host.txt
   ```
4. Start the FastAPI app from the repository root. The first Kokoro run may download model weights and therefore requires internet access.
5. Open Digital Host Mode, upload a front-facing portrait, enter a script, select Chinese or English, and start rendering.

Default Kokoro voices:
- Chinese: `zf_xiaobei` (language code `z`)
- English: `af_heart` (language code `a`)

The render worker creates:
- `output/hosts/<job-id>/final.mp4`
- `output/hosts/<job-id>/captions.srt`
- `output/hosts/<job-id>/voice.wav`

Job status is available from `GET /api/digital-host/jobs/{job_id}`. Files are served from `/outputs/...`.

## Digital Host API
- `POST /api/digital-host/portraits` — multipart image upload; returns a server-side portrait path.
- `POST /api/digital-host/jobs` — JSON body with `title`, `script`, `portrait_path`, optional `language` (`zh` or `en`) and `voice`.
- `GET /api/digital-host/jobs/{job_id}` — read job state and output URLs.

The API queues the render in a FastAPI background task. For a public or multi-user deployment, replace this MVP background task with a durable queue and add authentication, authorization, quotas, file retention policies and object storage.

## Cinematic video flow
1. `POST /api/projects` — create a project.
2. `POST /api/projects/{project_id}/generate` — submit to Agnes.
3. `POST /api/projects/{project_id}/refresh` — poll the provider task.
4. When Agnes reports completion and returns a video URL, the UI displays a preview.

The Agnes request uses `model`, `prompt`, `mode=text`, `seconds` (4–12), `size=720P`, `aspect_ratio` and `n=1`. Configure the model in `.env`.

## Tests
Run `pytest -q`. The Agnes integration tests use a mocked HTTP client and do not consume API quota. A real Agnes end-to-end test requires a valid key. Digital Host rendering requires the local TTS and SadTalker models and is not part of the lightweight test suite.

## Security and cost notes
- Never expose `AGNES_API_KEY` in browser code or commit `.env`.
- Digital Host uses open-source software, but "open source" does not mean zero compute cost: model downloads, electricity, GPU time and storage still have costs.
- Verify the licenses of code, model weights, voice assets and any portrait before commercial use.
- The MVP stores uploads and outputs on local disk. Do not expose it publicly without authentication, rate limits, access controls and storage lifecycle management.
