from minio import Minio
from minio.error import S3Error
from app.config import settings
import logging
from io import BytesIO
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class MinIOStorage:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(settings.MINIO_BUCKET):
                self.client.make_bucket(settings.MINIO_BUCKET)
                logger.info(f"Created bucket: {settings.MINIO_BUCKET}")
        except S3Error as e:
            logger.error(f"Error creating bucket: {e}")
            raise
    
    def generate_key(self, user_id: str, filename: str) -> str:
        """Generate unique storage key for file"""
        unique_id = uuid.uuid4().hex
        extension = filename.split('.')[-1] if '.' in filename else ''
        return f"{user_id}/{unique_id}.{extension}"
    
    def upload_file(self, file_data: bytes, key: str, content_type: str) -> bool:
        """Upload file to MinIO"""
        try:
            self.client.put_object(
                settings.MINIO_BUCKET,
                key,
                BytesIO(file_data),
                length=len(file_data),
                content_type=content_type
            )
            logger.info(f"Uploaded file: {key}")
            return True
        except S3Error as e:
            logger.error(f"Error uploading file: {e}")
            return False
    
    def download_file(self, key: str) -> Optional[bytes]:
        """Download file from MinIO"""
        try:
            response = self.client.get_object(settings.MINIO_BUCKET, key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error downloading file {key}: {e}")
            return None
    
    def delete_file(self, key: str) -> bool:
        """Delete file from MinIO"""
        try:
            self.client.remove_object(settings.MINIO_BUCKET, key)
            logger.info(f"Deleted file: {key}")
            return True
        except S3Error as e:
            logger.error(f"Error deleting file: {e}")
            return False
    
    def get_presigned_url(self, key: str, expires: int = 3600) -> Optional[str]:
        """Generate presigned URL for file access"""
        try:
            url = self.client.presigned_get_object(
                settings.MINIO_BUCKET,
                key,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
    
    def file_exists(self, key: str) -> bool:
        """Check if file exists"""
        try:
            self.client.stat_object(settings.MINIO_BUCKET, key)
            return True
        except S3Error:
            return False


# Global storage instance
storage = MinIOStorage()