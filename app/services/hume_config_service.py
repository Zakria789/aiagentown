"""
HumeAI Configuration Service
Manages HumeAI EVI configurations for each agent
"""
import httpx
import logging
from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.agent import Agent

logger = logging.getLogger(__name__)

# Popular HumeAI voices (only verified working voices)
HUME_VOICES = {
    "male": {
        "professional": "9e068547-5ba4-4c8e-8e03-69282a008f04",  # Male English Actor (verified working)
        "friendly": "9e068547-5ba4-4c8e-8e03-69282a008f04",      # Using same voice for now
        "confident": "9e068547-5ba4-4c8e-8e03-69282a008f04"      # Using same voice for now
    },
    "female": {
        "professional": "9e068547-5ba4-4c8e-8e03-69282a008f04",  # Default to male voice (TODO: get female voice IDs)
        "friendly": "9e068547-5ba4-4c8e-8e03-69282a008f04",      # Default to male voice
        "confident": "9e068547-5ba4-4c8e-8e03-69282a008f04"      # Default to male voice
    }
}

class HumeConfigService:
    """
    Service for managing HumeAI configurations
    Creates, updates, and deletes HumeAI configs for agents
    """
    
    def __init__(self):
        self.api_key = settings.HUME_API_KEY
        self.base_url = "https://api.hume.ai/v0/evi"
    
    async def create_agent_config(
        self,
        db: AsyncSession,
        agent_id: int,
        voice_gender: str = "male",
        voice_style: str = "professional",
        system_prompt: Optional[str] = None,
        rules: Optional[Dict] = None
    ) -> Dict:
        """
        Create HumeAI configuration for an agent
        
        Args:
            db: Database session
            agent_id: Agent ID
            voice_gender: "male" or "female"
            voice_style: "professional", "friendly", or "confident"
            system_prompt: Custom system prompt (agent's script)
            rules: Additional rules/settings
            
        Returns:
            Dict with config_id and details
        """
        try:
            # Get agent from database
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Use agent's campaign_script if no system_prompt provided
            if not system_prompt:
                if agent.campaign_script:
                    # Combine campaign script with standard call center rules
                    system_prompt = f"""{agent.campaign_script}

{self._get_default_prompt()}"""
                else:
                    system_prompt = self._get_default_prompt()
            
            # Get voice ID
            voice_id = HUME_VOICES.get(voice_gender, {}).get(voice_style)
            if not voice_id:
                voice_id = HUME_VOICES["male"]["professional"]  # Default
            
            # Build configuration payload
            import time
            config_name = f"Agent_{agent.agent_id}_{int(time.time())}"
            
            config_payload = {
                "evi_version": "3",  # Latest version
                "name": config_name,
                "version_description": "Fast response with natural speech",  # Description field
                "voice": {
                    "id": voice_id,
                    "provider": "HUME_AI"
                },
                "language_model": {
                    "model_provider": "ANTHROPIC",
                    "model_resource": "claude-3-5-sonnet-20241022",  # Fastest and most capable model
                    "temperature": 0.7  # Lower temperature for faster responses
                },
                "ellm_model": None,
                "prompt": {
                    "text": system_prompt,
                    "name": f"Agent_{agent.agent_id}_Prompt"
                },
                "event_messages": {
                    "on_new_chat": {
                        "enabled": True,
                        "text": "Hello! Thanks for calling. How can I help you today?"
                    },
                    "on_inactivity_timeout": {
                        "enabled": True,
                        "text": "Are you still there? Let me know if you have any questions."
                    },
                    "on_max_duration_timeout": {
                        "enabled": True,
                        "text": "Thank you for your time. Have a great day!"
                    }
                },
                "timeouts": {
                    "inactivity": {
                        "enabled": True,
                        "duration_secs": 30  # 30 seconds of silence
                    },
                    "max_duration": {
                        "enabled": True,
                        "duration_secs": 600  # 10 minutes max call
                    }
                },
                "tools": []
            }
            
            # Add custom rules if provided
            if rules:
                if "version_description" in rules:
                    config_payload["version_description"] = rules["version_description"]
                if "event_messages" in rules:
                    config_payload["event_messages"].update(rules["event_messages"])
                if "timeouts" in rules:
                    config_payload["timeouts"].update(rules["timeouts"])
            
            # Create config via HumeAI API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/configs",
                    headers={
                        "X-Hume-Api-Key": self.api_key,
                        "Content-Type": "application/json"
                    },
                    json=config_payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                config_data = response.json()
            
            # Update agent with HumeAI config ID
            agent.hume_config_id = config_data["id"]
            agent.hume_voice_id = voice_id
            
            # Store additional config in custom_data
            if not agent.dialer_config:
                agent.dialer_config = {}
            
            agent.dialer_config["hume_config"] = {
                "config_id": config_data["id"],
                "voice_gender": voice_gender,
                "voice_style": voice_style,
                "created_at": config_data.get("created_on"),
                "version": config_data.get("version")
            }
            
            await db.commit()
            
            logger.info(
                f"Created HumeAI config for agent {agent.agent_id}: "
                f"config_id={config_data['id']}, voice={voice_gender}/{voice_style}"
            )
            
            return {
                "success": True,
                "config_id": config_data["id"],
                "voice_id": voice_id,
                "voice_gender": voice_gender,
                "voice_style": voice_style,
                "agent_id": agent.agent_id,
                "config_data": config_data
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HumeAI API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to create HumeAI config: {e.response.text}")
        except Exception as e:
            logger.error(f"Error creating HumeAI config for agent {agent_id}: {e}")
            raise
    
    async def update_agent_config(
        self,
        db: AsyncSession,
        agent_id: int,
        system_prompt: Optional[str] = None,
        voice_gender: Optional[str] = None,
        voice_style: Optional[str] = None,
        rules: Optional[Dict] = None
    ) -> Dict:
        """
        Update existing HumeAI configuration
        
        Note: HumeAI doesn't support PATCH, so we recreate the config
        """
        try:
            # Get agent
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Delete old config if exists
            if agent.hume_config_id:
                await self.delete_agent_config(db, agent_id)
            
            # Create new config with updated settings
            return await self.create_agent_config(
                db=db,
                agent_id=agent_id,
                voice_gender=voice_gender or "male",
                voice_style=voice_style or "professional",
                system_prompt=system_prompt,
                rules=rules
            )
            
        except Exception as e:
            logger.error(f"Error updating HumeAI config for agent {agent_id}: {e}")
            raise
    
    async def delete_agent_config(
        self,
        db: AsyncSession,
        agent_id: int
    ) -> bool:
        """
        Delete HumeAI configuration for an agent
        """
        try:
            # Get agent
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            
            if not agent or not agent.hume_config_id:
                return False
            
            # Delete config via HumeAI API
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/configs/{agent.hume_config_id}",
                    headers={
                        "X-Hume-Api-Key": self.api_key
                    },
                    timeout=30.0
                )
                
                response.raise_for_status()
            
            # Clear agent's config IDs
            agent.hume_config_id = None
            agent.hume_voice_id = None
            
            if agent.dialer_config and "hume_config" in agent.dialer_config:
                del agent.dialer_config["hume_config"]
            
            await db.commit()
            
            logger.info(f"Deleted HumeAI config for agent {agent.agent_id}")
            
            return True
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HumeAI API error: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error deleting HumeAI config for agent {agent_id}: {e}")
            return False
    
    async def get_agent_config(
        self,
        db: AsyncSession,
        agent_id: int
    ) -> Optional[Dict]:
        """
        Get HumeAI configuration details for an agent
        """
        try:
            # Get agent
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            
            if not agent or not agent.hume_config_id:
                return None
            
            # Get config from HumeAI API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/configs/{agent.hume_config_id}",
                    headers={
                        "X-Hume-Api-Key": self.api_key
                    },
                    timeout=30.0
                )
                
                response.raise_for_status()
                return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HumeAI API error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error getting HumeAI config for agent {agent_id}: {e}")
            return None
    
    def _get_default_prompt(self) -> str:
        """Default system prompt with standard call center rules"""
        return """You are a professional call center agent. Follow these standard rules:

**CALL CENTER STANDARD RULES:**

1. GREETING & INTRODUCTION:
   - Greet warmly and professionally
   - State your name and company clearly
   - Ask how you can help today

2. ACTIVE LISTENING:
   - Listen carefully without interrupting
   - Take notes of key points
   - Acknowledge customer concerns with empathy

3. PROFESSIONAL CONDUCT:
   - Use polite, respectful language at all times
   - Maintain a calm, friendly tone
   - Avoid slang or informal language
   - Never argue with customers

4. PROBLEM RESOLUTION:
   - Ask clarifying questions to understand the issue
   - Provide accurate information only
   - If unsure, say \"Let me check that for you\" rather than guessing
   - Offer solutions, not excuses

5. TIME MANAGEMENT:
   - Be efficient but not rushed
   - Set clear expectations for follow-up times
   - Don't leave customers on hold for more than 30 seconds without updates

6. DATA COLLECTION:
   - Collect necessary information politely
   - Verify details for accuracy
   - Explain why information is needed

7. ESCALATION:
   - Recognize when to escalate to supervisor
   - Transfer smoothly with proper context
   - Never promise what you can't deliver

8. CLOSING:
   - Summarize actions taken or next steps
   - Ask if there's anything else you can help with
   - Thank the customer for their time
   - End on a positive note

9. COMPLIANCE:
   - Follow company policies and procedures
   - Protect customer privacy and data
   - Document calls accurately

10. CONTINUOUS IMPROVEMENT:
    - Learn from each interaction
    - Seek feedback when appropriate
    - Stay updated on product/service information

Remember: Keep responses concise (2-3 sentences). Use a friendly, conversational tone. Always prioritize customer satisfaction while maintaining professional standards."""


# Global instance
hume_config_service = HumeConfigService()
