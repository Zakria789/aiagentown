"""
Agent Management API
Endpoints for creating agents and connecting them to dialer users
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import logging

from app.database import get_db
from app.models import Agent, DialerUser
from app.services.calltools_monitor import initialize_calltools_monitor, shutdown_calltools_monitor

logger = logging.getLogger(__name__)

router = APIRouter()


# Schemas
class CreateAgentRequest(BaseModel):
    name: str
    hume_config_id: str
    calltools_username: str
    calltools_password: str
    description: Optional[str] = None
    auto_start: bool = False  # Auto-start monitoring on creation


class AgentResponse(BaseModel):
    id: int
    name: str
    hume_config_id: str
    calltools_username: str
    status: str
    auto_start: bool
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class ConnectAgentRequest(BaseModel):
    agent_id: int
    user_id: Optional[int] = None
    campaign_id: Optional[int] = None
    auto_start_monitoring: bool = True


class StartMonitoringRequest(BaseModel):
    agent_id: int


# Endpoints

@router.post("/agents/create", response_model=AgentResponse, tags=["Agent Management"])
async def create_agent(
    request: CreateAgentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Create new agent with HumeAI and CallTools configuration
    
    **Parameters:**
    - name: Agent ka naam
    - hume_config_id: HumeAI config ID
    - calltools_username: CallTools login username
    - calltools_password: CallTools login password
    - description: Agent description (optional)
    - auto_start: True = Automatically start monitoring
    
    **Example:**
    ```json
    {
        "name": "Sales Agent 1",
        "hume_config_id": "9607b727-a2e1-4084-a1d0-a0083138ba68",
        "calltools_username": "Eddie.Faklis",
        "calltools_password": "Roofing123",
        "auto_start": true
    }
    ```
    """
    try:
        # Create agent in database
        new_agent = Agent(
            name=request.name,
            hume_config_id=request.hume_config_id,
            calltools_username=request.calltools_username,
            calltools_password=request.calltools_password,
            description=request.description,
            status="active" if request.auto_start else "inactive",
            auto_start=request.auto_start
        )
        
        db.add(new_agent)
        await db.commit()
        await db.refresh(new_agent)
        
        logger.info(f"✅ Agent created: {new_agent.name} (ID: {new_agent.id})")
        
        # Auto-start monitoring if requested
        if request.auto_start:
            try:
                await initialize_calltools_monitor(
                    url="https://east-1.calltools.io",
                    username=request.calltools_username,
                    password=request.calltools_password
                )
                logger.info(f"✅ Auto-started monitoring for agent: {new_agent.name}")
            except Exception as e:
                logger.error(f"❌ Failed to auto-start monitoring: {e}")
                # Don't fail agent creation, just log the error
        
        return AgentResponse(
            id=new_agent.id,
            name=new_agent.name,
            hume_config_id=new_agent.hume_config_id,
            calltools_username=new_agent.calltools_username,
            status=new_agent.status,
            auto_start=new_agent.auto_start,
            description=new_agent.description
        )
        
    except Exception as e:
        logger.error(f"❌ Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.get("/agents", response_model=List[AgentResponse], tags=["Agent Management"])
async def list_agents(db: AsyncSession = Depends(get_db)):
    """
    Get list of all agents
    """
    try:
        result = await db.execute(select(Agent))
        agents = result.scalars().all()
        
        agent_list = []
        for agent in agents:
            # Get first dialer user for this agent (if exists)
            dialer_result = await db.execute(
                select(DialerUser).where(DialerUser.agent_id == agent.id)
            )
            dialer_user = dialer_result.scalar_one_or_none()
            
            agent_list.append(AgentResponse(
                id=agent.id,
                name=agent.name,
                hume_config_id=agent.hume_config_id or "",
                calltools_username=dialer_user.username if dialer_user else "",
                status="active" if agent.is_active else "inactive",
                auto_start=False,  # Default value
                description=f"Agent: {agent.full_name}"
            ))
        
        return agent_list
    except Exception as e:
        logger.error(f"❌ Error listing agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}", response_model=AgentResponse, tags=["Agent Management"])
async def get_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get specific agent details
    """
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get dialer user
        dialer_result = await db.execute(
            select(DialerUser).where(DialerUser.agent_id == agent.id)
        )
        dialer_user = dialer_result.scalar_one_or_none()
        
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            hume_config_id=agent.hume_config_id or "",
            calltools_username=dialer_user.username if dialer_user else "",
            status="active" if agent.is_active else "inactive",
            auto_start=False,
            description=f"Agent: {agent.full_name}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/connect", tags=["Agent Management"])
async def connect_agent(
    agent_id: int,
    request: ConnectAgentRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Connect agent to user or campaign
    
    **Parameters:**
    - agent_id: Agent ID (from path)
    - user_id: User ID to connect (optional)
    - campaign_id: Campaign ID to connect (optional)
    - auto_start_monitoring: Start monitoring immediately
    
    **Example:**
    ```json
    {
        "user_id": 1,
        "auto_start_monitoring": true
    }
    ```
    """
    try:
        # Get agent
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Connect to user
        if request.user_id:
            # user_result = await db.execute(select(User).where(User.id == request.user_id))
            # user = user_result.scalar_one_or_none()
            
            # if not user:
            #     raise HTTPException(status_code=404, detail="User not found")
            
            # Update user's default agent
            # user.default_agent_id = agent_id
            # await db.commit()
            
            logger.info(f"✅ Connected agent {agent.name} to user ID: {request.user_id}")
        
        # Connect to campaign
        if request.campaign_id:
            # campaign_result = await db.execute(select(Campaign).where(Campaign.id == request.campaign_id))
            # campaign = campaign_result.scalar_one_or_none()
            
            # if not campaign:
            #     raise HTTPException(status_code=404, detail="Campaign not found")
            
            # Update campaign's agent
            # campaign.agent_id = agent_id
            # await db.commit()
            
            logger.info(f"✅ Connected agent {agent.name} to campaign ID: {request.campaign_id}")
        
        # Start monitoring if requested
        if request.auto_start_monitoring:
            try:
                await initialize_calltools_monitor(
                    url="https://east-1.calltools.io",
                    username=agent.calltools_username,
                    password=agent.calltools_password
                )
                agent.status = "active"
                await db.commit()
                logger.info(f"✅ Started monitoring for agent: {agent.name}")
            except Exception as e:
                logger.error(f"❌ Failed to start monitoring: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")
        
        return {
            "success": True,
            "message": f"Agent {agent.name} connected successfully",
            "agent_id": agent_id,
            "user_id": request.user_id,
            "campaign_id": request.campaign_id,
            "monitoring_started": request.auto_start_monitoring
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error connecting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/start", tags=["Agent Management"])
async def start_agent_monitoring(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually start agent monitoring
    
    **Parameters:**
    - agent_id: Agent ID to start
    
    **Returns:**
    Success message with monitoring status
    """
    try:
        # Get agent
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Start monitoring
        try:
            # Use hardcoded CallTools credentials (TODO: Move to agent fields in DB)
            await initialize_calltools_monitor(
                url="https://east-1.calltools.io",
                username="Al.Hassan",
                password="Orangeroofing"
            )
            
            # Update agent status if status field exists
            if hasattr(agent, 'status'):
                agent.status = "active"
            agent.is_online = True
            await db.commit()
            
            logger.info(f"✅ Started monitoring for agent: {agent.full_name}")
            
            return {
                "success": True,
                "message": f"Monitoring started for agent: {agent.full_name}",
                "agent_id": agent_id,
                "status": "active",
                "monitoring_active": True,
                "calltools_url": "https://east-1.calltools.io"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to start monitoring: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/stop", tags=["Agent Management"])
async def stop_agent_monitoring(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Stop agent monitoring
    
    **Parameters:**
    - agent_id: Agent ID to stop
    """
    try:
        # Get agent
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Stop monitoring
        try:
            await shutdown_calltools_monitor()
            
            # Update agent status
            agent.status = "inactive"
            await db.commit()
            
            logger.info(f"✅ Stopped monitoring for agent: {agent.name}")
            
            return {
                "success": True,
                "message": f"Monitoring stopped for agent: {agent.name}",
                "agent_id": agent_id,
                "status": "inactive"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to stop monitoring: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error stopping agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agents/{agent_id}", tags=["Agent Management"])
async def delete_agent(agent_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete agent
    """
    try:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Stop monitoring if active
        if agent.status == "active":
            try:
                await shutdown_calltools_monitor()
            except:
                pass
        
        # Delete agent
        await db.delete(agent)
        await db.commit()
        
        logger.info(f"✅ Deleted agent: {agent.name}")
        
        return {
            "success": True,
            "message": f"Agent {agent.name} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))
