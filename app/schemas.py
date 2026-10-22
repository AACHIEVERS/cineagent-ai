from typing import Literal
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    premise: str = Field(min_length=10, max_length=4000)
    style: str = Field(default="cinematic realism", max_length=300)
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"
    duration_seconds: int = Field(default=5, ge=2, le=20)

class ProjectOut(BaseModel):
    id: str
    title: str
    premise: str
    style: str
    aspect_ratio: str
    duration_seconds: int
    status: str
    video_id: str | None = None
    provider_status: str | None = None
    result_url: str | None = None
    error: str | None = None
