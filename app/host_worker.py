import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

from . import db
from .config import settings


def make_subtitles(script: str, duration: float, path: Path):
    pieces = [x.strip() for x in re.split(r"(?<=[。！？.!?])", script) if x.strip()]
    if not pieces:
        pieces = [script]
    weights = [max(1, len(x)) for x in pieces]
    total = sum(weights)
    cursor = 0.0
    lines = []
    def stamp(seconds):
        ms = int(seconds * 1000)
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    for i, (piece, weight) in enumerate(zip(pieces, weights), 1):
        end = duration if i == len(pieces) else cursor + duration * weight / total
        lines.extend([str(i), f"{stamp(cursor)} --> {stamp(end)}", piece, ""])
        cursor = end
    path.write_text("\n".join(lines), encoding="utf-8")


def render(job_id: str):
    job = db.get_host_job(job_id)
    if not job:
        raise RuntimeError("Digital host job not found.")
    root = Path(settings.output_dir).resolve() / "hosts" / job_id
    root.mkdir(parents=True, exist_ok=True)
    audio_path = root / "voice.wav"
    subtitle_path = root / "captions.srt"
    db.update_host_job(job_id, status="generating_audio", error=None)

    lang = "z" if job["language"] == "zh" else "a"
    pipeline = KPipeline(lang_code=lang)
    chunks = []
    for _, _, audio in pipeline(job["script"], voice=job["voice"], speed=1.0):
        chunks.append(np.asarray(audio, dtype=np.float32))
    if not chunks:
        raise RuntimeError("Kokoro did not return any audio chunks.")
    audio = np.concatenate(chunks)
    sf.write(str(audio_path), audio, 24000)
    duration = len(audio) / 24000
    make_subtitles(job["script"], duration, subtitle_path)
    db.update_host_job(job_id, audio_path=str(audio_path), subtitle_path=str(subtitle_path),
                       status="rendering_avatar")

    sad = Path(settings.sadtalker_dir).resolve()
    inference = sad / "inference.py"
    if not inference.is_file():
        raise RuntimeError(
            f"SadTalker is not installed at {sad}. Clone SadTalker and set SADTALKER_DIR."
        )
    render_dir = root / "sadtalker"
    render_dir.mkdir(exist_ok=True)
    command = [
        sys.executable, str(inference),
        "--driven_audio", str(audio_path),
        "--source_image", job["portrait_path"],
        "--result_dir", str(render_dir),
        "--still", "--preprocess", "full",
    ]
    completed = subprocess.run(command, cwd=str(sad), capture_output=True,
                               text=True, timeout=1500)
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout or "SadTalker failed")[-2000:])
    videos = sorted(render_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not videos:
        raise RuntimeError("SadTalker finished but no MP4 output was found.")
    final_video = root / "final.mp4"
    shutil.copy2(videos[0], final_video)
    db.update_host_job(job_id, status="completed", video_path=str(final_video))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.host_worker JOB_ID")
    job_id = sys.argv[1]
    try:
        db.init_db()
        render(job_id)
    except Exception as exc:
        db.update_host_job(job_id, status="failed",
                           error=f"{type(exc).__name__}: {str(exc)[:1800]}")
        raise
