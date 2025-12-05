"""
Dialer User API Routes
CRUD operations for dialer user credentials
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.dialer_user import DialerUser
from app.models.agent import Agent
from app.schemas.dialer_user import (
    DialerUserCreate,
    DialerUserUpdate,
    DialerUserResponse,
    DialerUserLogin,
    DialerUserStatus
)
from app.core.dependencies import get_current_agent
from app.services.dialer_automation import dialer_automation
from app.services.campaign_scheduler import campaign_scheduler
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dialer-users", tags=["Dialer Users"])


@router.post("/", response_model=DialerUserResponse, status_code=status.HTTP_201_CREATED)
async def create_dialer_user(
    user_data: DialerUserCreate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Create new dialer user credentials
    Admin creates user with username, password, and dialer URL
    """
    try:
        # Check if username already exists
        result = await db.execute(
            select(DialerUser).where(DialerUser.username == user_data.username)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username {user_data.username} already exists"
            )
        
        # Check if agent exists
        result = await db.execute(
            select(Agent).where(Agent.id == user_data.agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {user_data.agent_id} not found"
            )
        
        # Create dialer user
        # NOTE: In production, encrypt the password before storing
        new_user = DialerUser(
            username=user_data.username,
            password=user_data.password,  # TODO: Encrypt this
            dialer_url=user_data.dialer_url,
            dialer_type=user_data.dialer_type,
            agent_id=user_data.agent_id,
            is_active=user_data.is_active
        )
        
        # Add schedule if provided
        if user_data.schedule:
            new_user.schedule_enabled = user_data.schedule.schedule_enabled
            new_user.start_time = user_data.schedule.start_time
            new_user.end_time = user_data.schedule.end_time
            new_user.timezone = user_data.schedule.timezone
            new_user.days_of_week = ','.join(user_data.schedule.days_of_week) if user_data.schedule.days_of_week else None
            new_user.auto_login = user_data.schedule.auto_login
            new_user.auto_unpause = user_data.schedule.auto_unpause
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"Created dialer user {new_user.username} for agent {agent.agent_id}")
        return new_user
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating dialer user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create dialer user: {str(e)}"
        )


@router.get("/", response_model=List[DialerUserResponse])
async def get_dialer_users(
    agent_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Get all dialer users (optionally filter by agent)
    """
    try:
        query = select(DialerUser)
        
        if agent_id:
            query = query.where(DialerUser.agent_id == agent_id)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        return users
        
    except Exception as e:
        logger.error(f"Error fetching dialer users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dialer users: {str(e)}"
        )


@router.get("/{user_id}", response_model=DialerUserResponse)
async def get_dialer_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """Get specific dialer user by ID"""
    try:
        result = await db.execute(
            select(DialerUser).where(DialerUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dialer user {user_id} not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dialer user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dialer user: {str(e)}"
        )


@router.put("/{user_id}", response_model=DialerUserResponse)
async def update_dialer_user(
    user_id: int,
    user_data: DialerUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """Update dialer user credentials"""
    try:
        result = await db.execute(
            select(DialerUser).where(DialerUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dialer user {user_id} not found"
            )
        
        # Update fields
        if user_data.password:
            user.password = user_data.password  # TODO: Encrypt
        if user_data.dialer_url:
            user.dialer_url = user_data.dialer_url
        if user_data.dialer_type:
            user.dialer_type = user_data.dialer_type
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        
        # Update schedule if provided
        if user_data.schedule:
            user.schedule_enabled = user_data.schedule.schedule_enabled
            user.start_time = user_data.schedule.start_time
            user.end_time = user_data.schedule.end_time
            user.timezone = user_data.schedule.timezone
            user.days_of_week = ','.join(user_data.schedule.days_of_week) if user_data.schedule.days_of_week else None
            user.auto_login = user_data.schedule.auto_login
            user.auto_unpause = user_data.schedule.auto_unpause
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Updated dialer user {user.username}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating dialer user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update dialer user: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dialer_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """Delete dialer user"""
    try:
        result = await db.execute(
            select(DialerUser).where(DialerUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dialer user {user_id} not found"
            )
        
        # Logout first if logged in
        if user.is_logged_in:
            await dialer_automation.logout_dialer(db, user_id)
        
        await db.delete(user)
        await db.commit()
        
        logger.info(f"Deleted dialer user {user.username}")
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting dialer user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete dialer user: {str(e)}"
        )


@router.post("/{user_id}/login", response_model=dict)
async def login_dialer_user(
    user_id: int,
    login_data: DialerUserLogin = None,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Trigger dialer login for specific user
    Opens browser, navigates to dialer URL, and logs in
    """
    try:
        headless = login_data.headless if login_data else True
        
        success = await dialer_automation.login_dialer(db, user_id, headless)
        
        if success:
            return {
                "status": "success",
                "message": f"Dialer user {user_id} logged in successfully",
                "user_id": user_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Login failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during dialer login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@router.post("/{user_id}/unpause", response_model=dict)
async def unpause_dialer(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Click unpause button on dialer
    Starts auto-dialing
    """
    try:
        success = await dialer_automation.click_unpause(db, user_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Dialer unpaused for user {user_id}",
                "user_id": user_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unpause failed - check if user is logged in"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during unpause: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unpause error: {str(e)}"
        )


@router.post("/{user_id}/pause", response_model=dict)
async def pause_dialer(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Click pause button on dialer
    Stops auto-dialing
    """
    try:
        success = await dialer_automation.click_pause(db, user_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Dialer paused for user {user_id}",
                "user_id": user_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pause failed - check if user is logged in"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during pause: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pause error: {str(e)}"
        )


@router.post("/{user_id}/logout", response_model=dict)
async def logout_dialer_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Logout dialer user and close browser session
    """
    try:
        success = await dialer_automation.logout_dialer(db, user_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Dialer user {user_id} logged out successfully",
                "user_id": user_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Logout failed"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout error: {str(e)}"
        )


@router.get("/{user_id}/status", response_model=DialerUserStatus)
async def get_dialer_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """Get current status of dialer user"""
    try:
        result = await db.execute(
            select(DialerUser).where(DialerUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dialer user {user_id} not found"
            )
        
        return DialerUserStatus(
            user_id=user.id,
            username=user.username,
            is_logged_in=user.is_logged_in,
            is_active=user.is_active,
            agent_id=user.agent_id,
            last_login=user.last_login,
            session_active=user_id in dialer_automation.drivers  # Fixed: use drivers not pages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Status error: {str(e)}"
        )


@router.post("/{user_id}/schedule-quick", response_model=dict)
async def schedule_quick_start(
    user_id: int,
    minutes: int = 3,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Schedule agent to start automatically after N minutes
    Default: 3 minutes
    
    Kya karega:
    1. N minutes wait karega
    2. Automatically dialer login karega
    3. Campaign join karega  
    4. Unpause karega (calls start)
    """
    try:
        # Get user
        result = await db.execute(
            select(DialerUser).where(DialerUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dialer user {user_id} not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {user.username} is not active"
            )
        
        # Calculate start time
        tz = pytz.timezone(user.timezone or 'America/New_York')
        now = datetime.now(tz)
        start_time = now + timedelta(minutes=minutes)
        
        # Update user schedule
        user.schedule_enabled = True
        user.start_time = start_time.strftime('%H:%M')
        user.end_time = (start_time + timedelta(hours=8)).strftime('%H:%M')  # 8 hour shift
        user.timezone = user.timezone or 'America/New_York'
        user.days_of_week = now.strftime('%A')  # Today only
        user.auto_login = True
        user.auto_unpause = True
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"📅 Scheduled {user.username} to start at {start_time.strftime('%H:%M')} ({minutes} minutes)")
        
        return {
            "status": "scheduled",
            "message": f"Agent will start automatically in {minutes} minutes",
            "user_id": user_id,
            "username": user.username,
            "scheduled_start": start_time.isoformat(),
            "current_time": now.isoformat(),
            "actions": [
                "1. Login to CallTools dialer",
                "2. Join campaign",
                "3. Set status to Available",
                "4. Start receiving calls automatically"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error scheduling quick start: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Schedule error: {str(e)}"
        )


@router.post("/{user_id}/start-now", response_model=dict)
async def force_start_now(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Start agent immediately (no waiting)
    
    Kya karega:
    1. Immediately dialer login
    2. Campaign join
    3. Unpause (calls start)
    """
    try:
        success = await campaign_scheduler.force_start_campaign(db, user_id)
        
        if success:
            return {
                "status": "started",
                "message": f"Agent {user_id} started successfully",
                "user_id": user_id,
                "actions_completed": [
                    "✅ Logged into CallTools",
                    "✅ Joined campaign",
                    "✅ Status set to Available",
                    "✅ Ready to receive calls"
                ]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to start agent - check logs"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error force starting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Start error: {str(e)}"
        )


@router.post("/{user_id}/stop-now", response_model=dict)
async def force_stop_now(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """
    Stop agent immediately
    
    Kya karega:
    1. Pause dialer
    2. Logout
    3. Close browser
    """
    try:
        success = await campaign_scheduler.force_stop_campaign(db, user_id)
        
        if success:
            return {
                "status": "stopped",
                "message": f"Agent {user_id} stopped successfully",
                "user_id": user_id,
                "actions_completed": [
                    "✅ Dialer paused",
                    "✅ Logged out",
                    "✅ Browser closed"
                ]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to stop agent - check logs"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error force stopping: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stop error: {str(e)}"
        )

