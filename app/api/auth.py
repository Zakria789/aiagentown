"""
Authentication API
Agent login, logout, token management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import timedelta, datetime
import logging

from app.database import get_db
from app.redis_client import get_redis, RedisClient
from app.schemas.auth import LoginRequest, TokenResponse, AgentProfile, RefreshTokenRequest
from app.models.agent import Agent
from app.core.security import verify_password, create_access_token, create_refresh_token, verify_token
from app.core.dependencies import get_current_agent
from app.core.exceptions import InvalidCredentialsException
from app.config import settings

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis)
):
    """
    Agent login endpoint
    
    Agent apni ID aur password se login kare
    JWT token milega response me
    """
    try:
        # Database se agent find karo
        result = await db.execute(
            select(Agent).where(Agent.agent_id == credentials.agent_id)
        )
        agent = result.scalar_one_or_none()
        
        # Agent exist karta hai?
        if not agent:
            logger.warning(f"Login failed: Agent {credentials.agent_id} not found")
            raise InvalidCredentialsException()
        
        # Password verify karo
        if not verify_password(credentials.password, agent.password_hash):
            logger.warning(f"Login failed: Invalid password for {credentials.agent_id}")
            raise InvalidCredentialsException()
        
        # Agent active hai?
        if not agent.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agent account is deactivated"
            )
        
        # JWT tokens create karo
        access_token = create_access_token(
            data={"sub": agent.agent_id, "agent_id": agent.id}
        )
        refresh_token = create_refresh_token(
            data={"sub": agent.agent_id, "agent_id": agent.id}
        )
        
        # Last login update karo
        await db.execute(
            update(Agent)
            .where(Agent.id == agent.id)
            .values(last_login=datetime.utcnow(), is_online=True)
        )
        await db.commit()
        
        # Redis me agent ko online mark karo
        await redis.set_agent_online(agent.id)
        
        # Session save karo Redis me
        session_data = {
            "agent_id": agent.id,
            "agent_login_id": agent.agent_id,
            "logged_in_at": datetime.utcnow().isoformat(),
            "role": agent.role
        }
        await redis.save_session(access_token, session_data, expire=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        
        logger.info(f"✅ Agent {credentials.agent_id} logged in successfully")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except InvalidCredentialsException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout")
async def logout(
    agent: Agent = Depends(get_current_agent),
    redis: RedisClient = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    """
    Agent logout
    
    Redis se session delete karo aur agent ko offline mark karo
    """
    try:
        # Agent ko offline mark karo
        await db.execute(
            update(Agent)
            .where(Agent.id == agent.id)
            .values(is_online=False)
        )
        await db.commit()
        
        # Redis me offline mark karo
        await redis.set_agent_offline(agent.id)
        
        logger.info(f"Agent {agent.agent_id} logged out")
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=AgentProfile)
async def get_current_agent_profile(
    agent: Agent = Depends(get_current_agent)
):
    """
    Current logged-in agent ki profile
    
    Returns:
        Agent ka complete profile
    """
    return AgentProfile.from_orm(agent)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Access token refresh karo using refresh token
    
    Jab access token expire ho jaye tab yeh use karo
    """
    try:
        # Refresh token verify karo
        agent_id = verify_token(refresh_request.refresh_token)
        
        if not agent_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Agent fetch karo
        result = await db.execute(
            select(Agent).where(Agent.agent_id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent or not agent.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Agent not found or inactive"
            )
        
        # Naye tokens create karo
        new_access_token = create_access_token(
            data={"sub": agent.agent_id, "agent_id": agent.id}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": agent.agent_id, "agent_id": agent.id}
        )
        
        logger.info(f"Token refreshed for agent {agent.agent_id}")
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/setup-admin")
async def setup_admin(db: AsyncSession = Depends(get_db)):
    """
    Initial admin setup (public endpoint - only works if no admin exists)
    Creates default admin account if database is empty
    """
    from app.core.security import hash_password
    
    # Check if any admin exists
    result = await db.execute(
        select(Agent).where(Agent.role == "admin")
    )
    existing_admin = result.scalar_one_or_none()
    
    if existing_admin:
        raise HTTPException(
            status_code=400,
            detail="Admin already exists. Use login endpoint."
        )
    
    # Create default admin
    admin = Agent(
        agent_id="admin",
        password_hash=hash_password("admin123"),
        full_name="System Administrator",
        email="admin@callcenter.com",
        role="admin",
        permissions=["*"],
        is_active=True
    )
    
    db.add(admin)
    await db.commit()
    await db.refresh(admin)
    
    logger.info("✅ Default admin created")
    
    return {
        "message": "Admin created successfully",
        "agent_id": "admin",
        "password": "admin123",
        "note": "Please change password after first login"
    }

