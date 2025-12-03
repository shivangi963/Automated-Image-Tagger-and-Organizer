from fastapi import APIRouter, Depends, HTTPException, status
from app.models import UserCreate, UserLogin, Token, User
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.database import get_database
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db=Depends(get_database)):
    """Register a new user"""
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user document
    user_doc = {
        "email": user.email,
        "password_hash": get_password_hash(user.password),
        "full_name": user.full_name,
        "created_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_doc)
    
    # Return user without password
    created_user = await db.users.find_one({"_id": result.inserted_id})
    
    return User(
        id=str(created_user["_id"]),
        email=created_user["email"],
        full_name=created_user.get("full_name"),
        created_at=created_user["created_at"]
    )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db=Depends(get_database)):
    """Login and receive access token"""
    
    # Find user
    user = await db.users.find_one({"email": credentials.email})
    
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user["email"]})
    
    return Token(access_token=access_token)


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    
    return User(
        id=str(current_user["_id"]),
        email=current_user["email"],
        full_name=current_user.get("full_name"),
        created_at=current_user["created_at"]
    )