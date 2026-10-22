import sqlite3
from pathlib import Path
from .config import settings

def connect():
    path = Path(settings.database_path)
    if path.parent != Path("."):
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, premise TEXT NOT NULL,
            style TEXT NOT NULL, aspect_ratio TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL, status TEXT NOT NULL,
            video_id TEXT, provider_status TEXT, result_url TEXT, error TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')

def create_project(project_id: str, data: dict):
    with connect() as c:
        c.execute('''INSERT INTO projects
        (id,title,premise,style,aspect_ratio,duration_seconds,status)
        VALUES (?,?,?,?,?,?,?)''',
        (project_id, data["title"], data["premise"], data["style"],
         data["aspect_ratio"], data["duration_seconds"], "draft"))

def get_project(project_id: str):
    with connect() as c:
        row = c.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    return dict(row) if row else None

def update_project(project_id: str, **fields):
    allowed = {"status", "video_id", "provider_status", "result_url", "error"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    sql = ", ".join(f"{k}=?" for k in fields)
    with connect() as c:
        c.execute(f"UPDATE projects SET {sql} WHERE id=?", (*fields.values(), project_id))
