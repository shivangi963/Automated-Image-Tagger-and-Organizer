from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


# User Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime
    
    class Config:
        json_encoders = {ObjectId: str}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


# Image Models
class ImageUpload(BaseModel):
    filename: str
    content_type: str

class PresignRequest(BaseModel):
    """Schema for requesting a pre-signed URL for file upload."""
    filename: str
    content_type: str = Field(..., description="MIME type of the file being uploaded.")

class ImageIngest(BaseModel):
    storage_key: str
    original_filename: str


class ImageTag(BaseModel):
    tag_name: str
    confidence: float
    source: str  # 'yolo', 'user'


class ImageMetadata(BaseModel):
    width: int
    height: int
    format: str
    mode: str
    size_bytes: int
    exif: Optional[Dict[str, Any]] = None


class ImageResponse(BaseModel):
    id: str
    user_id: str
    storage_key: str
    original_filename: str
    mime_type: str
    metadata: Optional[ImageMetadata] = None
    phash: Optional[str] = None
    tags: List[ImageTag] = []
    status: str  # 'pending', 'processing', 'completed', 'failed'
    created_at: datetime
    processed_at: Optional[datetime] = None
    thumbnail_key: Optional[str] = None
    
    class Config:
        json_encoders = {ObjectId: str}


class ImageUpdate(BaseModel):
    tags: Optional[List[str]] = None


# Album Models
class AlbumCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AlbumUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AlbumResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    image_count: int = 0
    cover_image: Optional[str] = None
    created_at: datetime
    
    class Config:
        json_encoders = {ObjectId: str}


class AlbumAddImages(BaseModel):
    image_ids: List[str]


# Search Models
class SearchQuery(BaseModel):
    query: Optional[str] = None
    tags: Optional[List[str]] = None
    album_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = 50
    skip: int = 0


class SearchResponse(BaseModel):
    total: int
    images: List[ImageResponse]


# Duplicate Detection
class DuplicateGroup(BaseModel):
    images: List[ImageResponse]
    similarity_score: float