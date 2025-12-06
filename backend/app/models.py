from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}


class UserOut(BaseModel):
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


class ImageUpload(BaseModel):
    filename: str
    content_type: str


class PresignRequest(BaseModel):
    """Schema for requesting a pre-signed URL for file upload."""
    filename: str = Field(..., description="Name of the file being uploaded")
    mime: str = Field(..., description="MIME type of the file (e.g., 'image/jpeg')")
    
    class Config:
        populate_by_name = True  # Allow both 'mime' and 'content_type'


class ImageTag(BaseModel):
    tag_name: str
    confidence: float
    source: str  # "yolo" or "user"


class ImageMetadata(BaseModel):
    width: int
    height: int
    format: str
    mode: str
    size_bytes: int
    exif: Optional[Dict[str, Any]] = None  # Cleaned EXIF only


class ImageInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    storage_key: str
    original_filename: str
    mime_type: str
    metadata: Optional[ImageMetadata] = None
    phash: Optional[str] = None
    tags: List[ImageTag] = Field(default_factory=list)
    
    # Added for MongoDB text search compatibility
    tag_strings: List[str] = Field(default_factory=list)

    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    thumbnailUrl: Optional[str] = None

    class Config:
        from_attributes = True
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}


class ImageResponse(BaseModel):
    id: str
    user_id: str
    storage_key: str
    original_filename: str
    mime_type: str
    metadata: Optional[ImageMetadata]
    phash: Optional[str]
    tags: List[ImageTag]
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    thumbnailUrl: Optional[str] = None

    class Config:
        json_encoders = {ObjectId: str}


class ImageUpdate(BaseModel):
    tags: List[str] = Field(default_factory=list)


class AlbumCreate(BaseModel):
    name: str
    description: Optional[str] = None


class AlbumUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class AlbumInDB(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    name: str
    description: Optional[str] = None
    image_count: int = 0
    cover_image: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {ObjectId: str}


class AlbumResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    image_count: int
    cover_image: Optional[str]
    created_at: datetime

    class Config:
        json_encoders = {ObjectId: str}


class AlbumAddImages(BaseModel):
    image_ids: List[str]


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


class DuplicateGroup(BaseModel):
    images: List[ImageResponse]
    similarity_score: float

# Find any model with Config class and update:

class SomeModel(BaseModel):
    # ...fields...
    
    class Config:
        populate_by_name = True  # Changed from allow_population_by_field_name
        json_encoders = {ObjectId: str}
