from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application Configuration for VTU Mini Project
    Automated Image Tagger and Organizer
    Bangalore College of Engineering & Technology
    """
    
    # Application Info
    APP_NAME: str = "Automated Image Tagger and Organizer"
    DEBUG: bool = True
    API_VERSION: str = "v1"
    ENVIRONMENT: str = "development"
    
    # Project Information
    PROJECT_NAME: str = "Automated Image Tagger and Organizer"
    INSTITUTION: str = "Bangalore College of Engineering & Technology"
    DEPARTMENT: str = "Computer Science and Engineering"
    SEMESTER: str = "5th Semester"
    ACADEMIC_YEAR: str = "2024-25"
    
    # MongoDB Atlas - Single connection string
    MONGODB_URI: str = "mongodb+srv://aliyaaiman1430_db_user:SW30dWdiUxkFFIGL@cluster0.fydbutx.mongodb.net/imagetagger_db?retryWrites=true&w=majority&appName=Cluster0"
    
    # MinIO / S3 Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "images"
    MINIO_SECURE: bool = False
    
    # Redis for task queue
    REDIS_URI: str = "redis://localhost:6379/0"
    
    # Celery background jobs
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    
    # JWT Authentication
    SECRET_KEY: str = "vtu-bangalore-college-of-engineering-mini-project-2024-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    
    # Computer Vision API
    GOOGLE_VISION_API_KEY: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    USE_GOOGLE_VISION: bool = False  # Set to True when you have API key
    
    # YOLO Configuration (offline detection)
    YOLO_MODEL: str = "yolov8n.pt"
    YOLO_CONFIDENCE: float = 0.25
    YOLO_IOU_THRESHOLD: float = 0.45
    
    # OCR Configuration
    ENABLE_OCR: bool = True
    OCR_LANGUAGES: str = "eng"
    
    # Upload Settings
    MAX_FILE_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: List[str] = ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"]
    MAX_UPLOAD_BATCH: int = 50
    
    # Image Processing
    THUMBNAIL_SIZE: int = 300
    IMAGE_QUALITY: int = 85
    
    # Search Configuration
    SEARCH_RESULTS_LIMIT: int = 100
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    @property
    def database_name(self) -> str:
        """Extract database name from MongoDB URI"""
        try:
            # Parse database name from URI
            if '/' in self.MONGODB_URI and '?' in self.MONGODB_URI:
                # Format: mongodb+srv://user:pass@host/dbname?params
                parts = self.MONGODB_URI.split('/')
                db_part = parts[-1].split('?')[0]
                return db_part if db_part else 'imagetagger_db'
            return 'imagetagger_db'
        except:
            return 'imagetagger_db'
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def use_cloud_vision(self) -> bool:
        """Check if Google Cloud Vision API is configured"""
        return self.USE_GOOGLE_VISION and (
            bool(self.GOOGLE_VISION_API_KEY) or 
            bool(self.GOOGLE_APPLICATION_CREDENTIALS)
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()