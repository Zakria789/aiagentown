"""
Agents API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse, AgentListResponse
from app.models.agent import Agent
from app.core.security import hash_password
from app.core.dependencies import get_current_agent
from app.services.hume_config_service import hume_config_service

router = APIRouter()


def require_admin(agent: Agent = Depends(get_current_agent)) -> Agent:
    """Admin access required"""
    if agent.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return agent


@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(require_admin)
):
    """
    Create new agent (Admin only)
    Automatically creates HumeAI configuration
    """
    # Check if agent_id already exists
    result = await db.execute(
        select(Agent).where(Agent.agent_id == agent_data.agent_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Agent ID already exists")
    
    # Hash password
    password_hash = hash_password(agent_data.password)
    
    # Create agent
    agent = Agent(
        agent_id=agent_data.agent_id,
        password_hash=password_hash,
        full_name=agent_data.full_name,
        email=agent_data.email,
        phone=agent_data.phone,
        role=agent_data.role,
        permissions=agent_data.permissions,
        dialer_extension=agent_data.dialer_extension,
        campaign_script=agent_data.campaign_script if hasattr(agent_data, 'campaign_script') else None
    )
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    # Create HumeAI configuration for this agent
    try:
        # Get voice settings from agent_data or use defaults
        voice_gender = getattr(agent_data, 'voice_gender', 'male')
        voice_style = getattr(agent_data, 'voice_style', 'professional')
        rules = getattr(agent_data, 'hume_rules', None)
        
        print(f"[DEBUG] Creating HumeAI config for agent {agent.id}")
        print(f"[DEBUG] Voice: {voice_gender}/{voice_style}, Script: {agent.campaign_script[:50] if agent.campaign_script else 'None'}...")
        
        hume_result = await hume_config_service.create_agent_config(
            db=db,
            agent_id=agent.id,
            voice_gender=voice_gender,
            voice_style=voice_style,
            system_prompt=agent.campaign_script,
            rules=rules
        )
        
        print(f"[DEBUG] HumeAI result: {hume_result}")
        
        # Refresh agent to get updated hume_config_id
        await db.refresh(agent)
        
        print(f"[DEBUG] Agent refreshed - Config ID: {agent.hume_config_id}")
        
    except Exception as e:
        # Log error but don't fail agent creation
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create HumeAI config for agent {agent.id}: {e}", exc_info=True)
        print(f"[ERROR] HumeAI config creation failed: {e}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
    
    return AgentResponse.from_orm(agent)


@router.get("/", response_model=AgentListResponse)
async def get_agents(
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """Get all agents"""
    offset = (page - 1) * page_size
    
    result = await db.execute(
        select(Agent).offset(offset).limit(page_size)
    )
    agents = result.scalars().all()
    
    total_result = await db.execute(select(Agent))
    total = len(total_result.scalars().all())
    
    return AgentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        agents=[AgentResponse.from_orm(a) for a in agents]
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """Get agent by ID"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse.from_orm(agent)


@router.put("/{agent_id}/voice")
async def update_agent_voice(
    agent_id: int,
    voice_gender: str,  # "male" or "female"
    voice_style: str,   # "professional", "friendly", "confident"
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(require_admin)
):
    """
    Update agent's voice settings
    Recreates HumeAI config with new voice
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        hume_result = await hume_config_service.update_agent_config(
            db=db,
            agent_id=agent_id,
            voice_gender=voice_gender,
            voice_style=voice_style
        )
        
        await db.refresh(agent)
        
        return {
            "success": True,
            "message": f"Voice updated to {voice_gender}/{voice_style}",
            "config_id": hume_result["config_id"],
            "voice_id": hume_result["voice_id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update voice: {str(e)}")


@router.put("/{agent_id}/script")
async def update_agent_script(
    agent_id: int,
    script: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(require_admin)
):
    """
    Update agent's campaign script
    Updates both database and HumeAI config
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update local script
    agent.campaign_script = script
    await db.commit()
    
    # Update HumeAI config
    try:
        hume_result = await hume_config_service.update_agent_config(
            db=db,
            agent_id=agent_id,
            system_prompt=script
        )
        
        return {
            "success": True,
            "message": "Script updated successfully",
            "config_id": hume_result["config_id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update script: {str(e)}")


@router.put("/{agent_id}/rules")
async def update_agent_rules(
    agent_id: int,
    rules: dict,  # HumeAI settings (event_messages, timeouts, etc.)
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(require_admin)
):
    """
    Update agent's HumeAI rules/settings
    
    Example rules:
    {
        "event_messages": {
            "on_new_chat": {"enabled": true, "text": "Hello! How can I help?"},
            "on_inactivity_timeout": {"enabled": true, "text": "Are you there?"}
        },
        "timeouts": {
            "inactivity": {"enabled": true, "duration_secs": 30},
            "max_duration": {"enabled": true, "duration_secs": 600}
        },
        "temperature": 0.8
    }
    """
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        hume_result = await hume_config_service.update_agent_config(
            db=db,
            agent_id=agent_id,
            rules=rules
        )
        
        return {
            "success": True,
            "message": "Rules updated successfully",
            "config_id": hume_result["config_id"],
            "applied_rules": rules
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rules: {str(e)}")


@router.get("/{agent_id}/hume-config")
async def get_agent_hume_config(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent)
):
    """Get agent's HumeAI configuration details"""
    config = await hume_config_service.get_agent_config(db, agent_id)
    
    if not config:
        raise HTTPException(status_code=404, detail="HumeAI config not found for this agent")
    
    return config


@router.delete("/{agent_id}/hume-config")
async def delete_agent_hume_config(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(require_admin)
):
    """Delete agent's HumeAI configuration"""
    success = await hume_config_service.delete_agent_config(db, agent_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Failed to delete HumeAI config")
    
    return {"success": True, "message": "HumeAI config deleted successfully"}

