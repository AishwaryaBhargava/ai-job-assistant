# backend/auth_utils.py
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import Optional
import os
from database import users_collection  # ✅ fetch users from Mongo
from bson import ObjectId
from utils.logger import logger  # ✅ Added logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

SECRET_KEY = os.getenv("SECRET_KEY", "mysecretkey")
ALGORITHM = "HS256"


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Decode JWT token, validate user existence, and return user document.
    """
    logger.info("Attempting to authenticate user from provided JWT token")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            logger.error("JWT token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 🔹 Fetch user from DB by email
        user = await users_collection.find_one({"email": email})
        if not user:
            logger.error(f"User not found in database for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user["_id"] = str(user["_id"])  # convert ObjectId → str
        logger.info(f"User authenticated successfully: {email}")
        return user

    except JWTError as e:
        logger.error(f"JWT decoding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during user authentication: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal authentication error",
        )


async def get_optional_user(authorization: Optional[str] = Header(None)):
    """
    Return the user if token is provided and valid, otherwise return None.
    Useful for routes accessible by both guests and logged-in users.
    """
    if not authorization:
        logger.info("No Authorization header found — treating request as guest access")
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        logger.warning("Invalid Authorization header format")
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.warning(f"JWT decode failed for optional user: {e}")
        return None

    email = payload.get("sub")
    if not email:
        logger.warning("JWT token missing 'sub' claim for optional user")
        return None

    user = await users_collection.find_one({"email": email})
    if not user:
        logger.info(f"No matching user found for optional token (email={email})")
        return None

    user["_id"] = str(user["_id"])
    logger.info(f"Optional user identified successfully: {email}")
    return user
