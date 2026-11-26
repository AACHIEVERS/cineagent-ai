from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    agnes_api_key: str = ""
    agnes_api_root: str = "https://apihub.agnes-ai.com"
    agnes_video_model: str = "agnes-video-2.5-flash"
    database_path: str = "./cineagent.db"
    output_dir: str = "./output"
    sadtalker_dir: str = "./SadTalker"
    ollama_api_root: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    app_env: str = "development"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
