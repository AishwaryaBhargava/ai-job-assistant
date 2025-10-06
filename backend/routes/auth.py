from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import users_collection
from models.user import UserRegister, UserLogin, UserInDB
from bson import ObjectId
import os
from utils.logger import logger  # ✅ Added logger

router = APIRouter()

# 🔑 Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 🔑 JWT config
SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")  # fallback for dev
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    try:
        hashed = pwd_context.hash(password)
        logger.debug("Password hashed successfully")
        return hashed
    except Exception as e:
        logger.error(f"Error hashing password: {e}", exc_info=True)
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against hash."""
    try:
        valid = pwd_context.verify(plain_password, hashed_password)
        logger.debug("Password verification completed")
        return valid
    except Exception as e:
        logger.error(f"Password verification failed: {e}", exc_info=True)
        return False


def create_access_token(data: dict, expires_delta: timedelta = None):
    """Generate a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    try:
        token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"Access token created for user: {data.get('sub')}")
        return token
    except Exception as e:
        logger.error(f"Failed to create JWT token: {e}", exc_info=True)
        raise


# 📌 Register user
@router.post("/register")
async def register(user: UserRegister):
    logger.info(f"Registration attempt for email: {user.email}")
    try:
        existing_user = await users_collection.find_one({"email": user.email})
        if existing_user:
            logger.warning(f"Registration failed — Email already registered: {user.email}")
            raise HTTPException(status_code=400, detail="Email already registered")

        user_dict = user.dict()
        user_dict["hashed_password"] = hash_password(user.password)
        del user_dict["password"]

        result = await users_collection.insert_one(user_dict)
        logger.info(f"User registered successfully: {user.email} (id={result.inserted_id})")
        return {"id": str(result.inserted_id), "message": "User registered successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration for {user.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during registration")


# 📌 Login user
@router.post("/login")
async def login(user: UserLogin):
    logger.info(f"Login attempt for email: {user.email}")
    try:
        db_user = await users_collection.find_one({"email": user.email})
        if not db_user:
            logger.warning(f"Login failed — user not found: {user.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not verify_password(user.password, db_user["hashed_password"]):
            logger.warning(f"Login failed — invalid password for user: {user.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        access_token = create_access_token(data={"sub": db_user["email"]})
        logger.info(f"User logged in successfully: {user.email}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": str(db_user["_id"]),
            "email": db_user["email"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login for {user.email}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during login")
