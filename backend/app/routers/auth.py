from fastapi import APIRouter, Depends, HTTPException, status
from app.models import UserCreate, UserLogin, Token, UserOut
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user
from app.database import get_database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db=Depends(get_database)):
    """Register a new user"""
    try:
        existing_user = await db.users.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        user_doc = {
            "email": user.email,
            "password_hash": get_password_hash(user.password),
            "full_name": user.full_name,
            "created_at": datetime.utcnow()
        }

        result = await db.users.insert_one(user_doc)
        created_user = await db.users.find_one({"_id": result.inserted_id})

        # Create and return access token
        access_token = create_access_token(data={"sub": str(created_user["_id"])})
        
        logger.info(f"User registered: {user.email}")
        
        return Token(access_token=access_token, token_type="bearer")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db=Depends(get_database)):
    """Login user and return access token"""
    try:
        user = await db.users.find_one({"email": credentials.email})

        if not user or not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(data={"sub": str(user["_id"])})
        
        logger.info(f"User logged in: {credentials.email}")
        
        return Token(access_token=access_token, token_type="bearer")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return UserOut(
        id=str(current_user["_id"]),
        email=current_user["email"],
        full_name=current_user.get("full_name"),
        created_at=current_user["created_at"]
    )
