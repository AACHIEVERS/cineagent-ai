import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles\nimport httpx

from . import db
from .agnes import AgnesError, create_video, get_video
from .config import settings
from .schemas import ProjectCreate, ProjectOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="CineAgent AI", version="0.3.0", lifespan=lifespan)
static_dir = Path(__file__).parent / "static"
output_dir = Path(settings.output_dir)
output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/outputs", StaticFiles(directory=output_dir), name="outputs")


@app.get("/", response_class=HTMLResponse)
async def home():
    return (static_dir / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "provider_configured": bool(settings.agnes_api_key),
        "provider": "Agnes AI",
        "video_model": settings.agnes_video_model,
        "digital_host_ready": Path(settings.sadtalker_dir, "inference.py").exists(),
        "kokoro_install_hint": "pip install -r requirements-host.txt",
        "version": "0.3.0",
    }


@app.post("/api/projects", response_model=ProjectOut)
async def create_project(payload: ProjectCreate):
    project_id = str(uuid4())
    db.create_project(project_id, payload.model_dump())
    return db.get_project(project_id)


@app.get("/api/projects/{project_id}", response_model=ProjectOut)
async def read_project(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@app.post("/api/projects/{project_id}/generate", response_model=ProjectOut)
async def generate_project_video(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if project.get("video_id"):
        raise HTTPException(409, "A provider job already exists for this project")

    prompt = (
        f"Cinematic short film shot. Project: {project['title']}. "
        f"Story premise: {project['premise']}. Visual style: {project['style']}. "
        "Keep character appearance and scene details coherent. "
        "Strong composition, natural motion, cinematic lighting. "
        "No subtitles or text rendered in-frame."
    )
    db.update_project(project_id, status="submitting", error=None)
    try:
        video_id = await create_video(
            prompt, project["aspect_ratio"], project["duration_seconds"]
        )
        db.update_project(
            project_id, status="generating", video_id=video_id,
            provider_status="submitted", error=None,
        )
    except AgnesError as exc:
        db.update_project(project_id, status="failed", error=str(exc))
        raise HTTPException(502, str(exc)) from exc
    return db.get_project(project_id)


@app.post("/api/projects/{project_id}/refresh", response_model=ProjectOut)
async def refresh_project(project_id: str):
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.get("video_id"):
        raise HTTPException(409, "No provider video_id exists yet")
    try:
        result = await get_video(project["video_id"])
    except AgnesError as exc:
        raise HTTPException(502, str(exc)) from exc

    provider_status = str(result.get("status", "unknown")).lower()
    nested = result.get("data") if isinstance(result.get("data"), dict) else {}
    metadata = result.get("metadata") if isinstance(result.get("metadata"), dict) else {}
    result_url = (result.get("video_url") or result.get("url")
                  or nested.get("video_url") or nested.get("url") or metadata.get("url"))
    if provider_status in {"succeeded", "success", "completed", "done"}:
        db.update_project(project_id, status="completed", provider_status=provider_status,
                          result_url=result_url, error=None)
    elif provider_status in {"failed", "error", "cancelled", "canceled"}:
        provider_error = result.get("error")
        if isinstance(provider_error, dict):
            provider_error = provider_error.get("message") or str(provider_error)
        db.update_project(project_id, status="failed", provider_status=provider_status,
                          error=str(provider_error or "Agnes reported that video generation failed")[:500])
    else:
        db.update_project(project_id, status="generating", provider_status=provider_status)
    return db.get_project(project_id)


@app.post("/api/digital-host/script")
async def generate_host_script(payload: dict):
    topic = str(payload.get("topic", "")).strip()
    language = str(payload.get("language", "zh"))
    if not topic or len(topic) > 500:
        raise HTTPException(422, "topic is required and must be 500 characters or fewer.")
    if language not in {"zh", "en"}:
        raise HTTPException(422, "language must be zh or en.")
    language_name = "Simplified Chinese" if language == "zh" else "English"
    prompt = (
        f"Write a natural 45-60 second digital-host script in {language_name}. "
        f"Topic: {topic}. Start with a concise hook, explain 2-3 useful points, "
        "and finish with one memorable takeaway. Write only the spoken script, "
        "without stage directions, markdown, headings or fabricated statistics."
    )
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{settings.ollama_api_root.rstrip('/')}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
            )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            503, f"Local Ollama is unavailable. Start Ollama and pull {settings.ollama_model}."
        ) from exc
    script = str(data.get("response", "")).strip()
    if not script:
        raise HTTPException(502, "Ollama returned an empty script.")
    return {"script": script, "model": settings.ollama_model}


@app.post("/api/digital-host/portraits")
async def upload_host_portrait(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 12 * 1024 * 1024:
        raise HTTPException(413, "Portrait image must be 12 MB or smaller.")
    signatures = {b"\xff\xd8\xff": ".jpg", b"\x89PNG\r\n\x1a\n": ".png",
                  b"RIFF": ".webp"}
    extension = next((ext for sig, ext in signatures.items() if content.startswith(sig) and (sig != b"RIFF" or content[8:12] == b"WEBP")), None)
    if not extension:
        raise HTTPException(415, "Upload a JPG, PNG, or WEBP portrait image.")
    portrait_id = str(uuid4())
    folder = output_dir / "portraits"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{portrait_id}{extension}"
    path.write_bytes(content)
    return {"portrait_path": str(path), "portrait_url": f"/outputs/portraits/{path.name}"}


def _run_host_worker(job_id: str):
    command = [sys.executable, "-m", "app.host_worker", job_id]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=1800)
        if completed.returncode != 0:
            job = db.get_host_job(job_id)
            if job and job["status"] not in {"failed", "completed"}:
                detail = (completed.stderr or completed.stdout or "Digital host worker failed")[-1500:]
                db.update_host_job(job_id, status="failed", error=detail)
    except subprocess.TimeoutExpired:
        db.update_host_job(job_id, status="failed", error="Render timed out after 30 minutes.")
    except Exception as exc:
        db.update_host_job(job_id, status="failed", error=f"Worker launch failed: {type(exc).__name__}")


@app.post("/api/digital-host/jobs")
async def create_digital_host_job(payload: dict, background_tasks: BackgroundTasks):
    required = ("title", "script", "portrait_path")
    if any(not str(payload.get(k, "")).strip() for k in required):
        raise HTTPException(422, "title, script and portrait_path are required.")
    script = str(payload["script"]).strip()
    if len(script) > 6000:
        raise HTTPException(422, "Script must be 6,000 characters or fewer.")
    portrait = Path(str(payload["portrait_path"])).resolve()
    allowed_root = (output_dir / "portraits").resolve()
    if allowed_root not in portrait.parents or not portrait.is_file():
        raise HTTPException(400, "Portrait path is invalid. Upload the portrait through this API first.")
    language = str(payload.get("language", "zh"))
    if language not in {"zh", "en"}:
        raise HTTPException(422, "language must be zh or en.")
    voice = str(payload.get("voice") or ("zf_xiaobei" if language == "zh" else "af_heart"))
    if len(voice) > 80:
        raise HTTPException(422, "Voice identifier is too long.")
    job_id = str(uuid4())
    db.create_host_job(job_id, {
        "title": str(payload["title"])[:120], "script": script,
        "language": language, "voice": voice, "portrait_path": str(portrait),
    })
    background_tasks.add_task(_run_host_worker, job_id)
    return db.get_host_job(job_id)


@app.get("/api/digital-host/jobs/{job_id}")
async def get_digital_host_job(job_id: str):
    job = db.get_host_job(job_id)
    if not job:
        raise HTTPException(404, "Digital host job not found.")
    result = dict(job)
    for key in ("video_path", "audio_path", "subtitle_path"):
        value = result.get(key)
        if value:
            try:
                result[key.replace("_path", "_url")] = "/outputs/" + Path(value).resolve().relative_to(output_dir.resolve()).as_posix()
            except ValueError:
                result[key.replace("_path", "_url")] = None
    return result


@app.get("/api/digital-host/jobs/{job_id}/export")
async def export_digital_host_video(job_id: str, aspect_ratio: str = "9:16"):
    if aspect_ratio not in {"9:16", "16:9"}:
        raise HTTPException(422, "aspect_ratio must be 9:16 or 16:9.")
    job = db.get_host_job(job_id)
    if not job:
        raise HTTPException(404, "Digital host job not found.")
    if job.get("status") != "completed" or not job.get("video_path"):
        raise HTTPException(409, "The master video is not ready yet.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise HTTPException(503, "FFmpeg is required for platform exports. Install FFmpeg and retry.")
    source = Path(job["video_path"]).resolve()
    if not source.is_file():
        raise HTTPException(404, "Master video file is missing.")
    width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    destination = source.parent / ("vertical_9x16.mp4" if aspect_ratio == "9:16" else "horizontal_16x9.mp4")
    if not destination.exists():
        vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
        try:
            result = subprocess.run(
                [ffmpeg, "-y", "-i", str(source), "-vf", vf, "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-movflags",
                 "+faststart", str(destination)],
                capture_output=True, text=True, timeout=600,
            )
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(504, "Video export timed out.") from exc
        if result.returncode != 0 or not destination.is_file():
            raise HTTPException(500, "FFmpeg export failed: " + (result.stderr or "")[-1000:])
    relative = destination.relative_to(output_dir.resolve()).as_posix()
    return {"aspect_ratio": aspect_ratio, "video_url": "/outputs/" + relative}
