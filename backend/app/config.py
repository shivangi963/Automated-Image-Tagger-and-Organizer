from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os


# .env lives in project root — two levels above backend/app/config.py
ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"

# override=True makes .env values WIN over any polluted system/user env vars.
# Correct approach for dev — safe to commit since .env stays in .gitignore.
load_dotenv(ROOT_ENV, override=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Automated Image Tagger Organizer"
    DEBUG: bool = True
    API_VERSION: str = "v1"

    MONGODB_URL: str = "mongodb://admin:admin123@localhost:27018/?authSource=admin"
    MONGODB_DB: str = "image_tagger"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "images"
    MINIO_SECURE: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    YOLO_MODEL: str = "yolov8n.pt"
    YOLO_CONFIDENCE: float = 0.25

    MAX_FILE_SIZE: int = 10485760
    ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,gif,bmp,webp"

    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> List[str]:
        v = self.CORS_ORIGINS.strip()
        if not v:
            return []
        return [x.strip() for x in v.split(",") if x.strip()]

print(">>> MONGODB_URL from os.environ:", os.environ.get("MONGODB_URL", "NOT SET"))
settings = Settings()