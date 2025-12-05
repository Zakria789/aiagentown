"""
FastAPI dependencies
Reusable dependencies for routes
"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging

from app.database import get_db
from app.redis_client import get_redis, RedisClient
from app.core.security import verify_token
from app.models.agent import Agent
from sqlalchemy import select

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
) -> Agent:
    """
    Current logged-in agent ko get karo
    JWT token se agent verify karta hai
    
    Usage:
        @app.get("/protected")
        async def protected_route(agent: Agent = Depends(get_current_agent)):
            return {"agent": agent.full_name}
    """
    token = credentials.credentials
    
    # Token verify karo
    agent_id = verify_token(token)
    
    if agent_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Database se agent fetch karo
    result = await db.execute(
        select(Agent).where(Agent.agent_id == agent_id)
    )
    agent = result.scalar_one_or_none()
    
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent not found",
        )
    
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent account is deactivated",
        )
    
    # Redis me agent ko online mark karo
    await redis.set_agent_online(agent.id)
    
    return agent


async def get_current_active_agent(
    agent: Agent = Depends(get_current_agent)
) -> Agent:
    """
    Active agent verify karo
    """
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent is not active"
        )
    
    return agent


async def require_role(required_role: str):
    """
    Role-based access control
    
    Usage:
        @app.get("/admin")
        async def admin_only(agent: Agent = Depends(require_role("admin"))):
            ...
    """
    async def role_checker(agent: Agent = Depends(get_current_agent)) -> Agent:
        if agent.role != required_role and agent.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}"
            )
        return agent
    
    return role_checker


async def get_optional_agent(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[Agent]:
    """
    Optional authentication
    Agar token hai toh agent return kare, warna None
    """
    if not authorization:
        return None
    
    try:
        # "Bearer <token>" se token extract karo
        token = authorization.replace("Bearer ", "")
        agent_id = verify_token(token)
        
        if agent_id is None:
            return None
        
        result = await db.execute(
            select(Agent).where(Agent.agent_id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        return agent
    except Exception as e:
        logger.warning(f"Optional auth failed: {e}")
        return None


# Alias for compatibility with analytics routes
get_current_user = get_current_agent
