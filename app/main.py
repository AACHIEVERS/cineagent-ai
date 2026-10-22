from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from . import db
from .agnes import AgnesError, create_video, get_video
from .config import settings
from .schemas import ProjectCreate, ProjectOut

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield

app = FastAPI(title="CineAgent AI", version="0.1.0", lifespan=lifespan)
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def home():
    return (static_dir / "index.html").read_text(encoding="utf-8")

@app.get("/api/health")
async def health():
    return {"ok": True, "provider_configured": bool(settings.agnes_api_key), "version": "0.1.0"}

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
    prompt = (f"Cinematic short film shot. Project: {project['title']}. Story premise: {project['premise']}. "
              f"Visual style: {project['style']}. Keep character appearance and scene details coherent. "
              "Strong composition, natural motion, cinematic lighting. No subtitles or text rendered in-frame.")
    db.update_project(project_id, status="submitting", error=None)
    try:
        video_id = await create_video(prompt, project["aspect_ratio"], project["duration_seconds"])
        db.update_project(project_id, status="generating", video_id=video_id, provider_status="submitted")
    except AgnesError as e:
        db.update_project(project_id, status="failed", error=str(e))
        raise HTTPException(502, str(e))
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
    except AgnesError as e:
        raise HTTPException(502, str(e))
    provider_status = str(result.get("status", "unknown")).lower()
    result_url = result.get("video_url") or result.get("url") or (result.get("data") or {}).get("url")
    if provider_status in {"succeeded", "success", "completed", "done"}:
        db.update_project(project_id, status="completed", provider_status=provider_status, result_url=result_url, error=None)
    elif provider_status in {"failed", "error", "cancelled"}:
        db.update_project(project_id, status="failed", provider_status=provider_status, error=str(result)[:500])
    else:
        db.update_project(project_id, status="generating", provider_status=provider_status)
    return db.get_project(project_id)
