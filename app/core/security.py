"""
Security utilities
Password hashing, JWT token generation, etc.
"""

from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.config import settings


def hash_password(password: str) -> str:
    """
    Password ko hash karo using bcrypt directly
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Password verify karo using bcrypt directly
    
    Args:
        plain_password: User ne jo password diya
        hashed_password: Database me saved hash
    
    Returns:
        True agar password match kare
    """
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Password verification error: {e}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT access token create karo
    
    Args:
        data: Token me include karne wala data (e.g., {"sub": agent_id})
        expires_delta: Token expiry time (optional)
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    JWT refresh token create karo (longer expiry)
    
    Args:
        data: Token me include karne wala data
    
    Returns:
        JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    JWT token ko decode karo
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload agar valid ho, warna None
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str) -> Optional[str]:
    """
    Token verify karke agent_id return karo
    
    Args:
        token: JWT token
    
    Returns:
        agent_id agar token valid ho
    """
    payload = decode_token(token)
    
    if payload is None:
        return None
    
    # Check expiry - no need to manually check, jose handles it
    # The decode_token already validates expiry
    
    # Extract agent_id
    agent_id: str = payload.get("sub")
    
    return agent_id
