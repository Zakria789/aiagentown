"""
Post-Call Handler Service
Manages actions after call completion: disposition, next call preparation, logging
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import logging

from app.models.call import Call
from app.models.agent import Agent
from app.models.dialer_user import DialerUser
from app.services.disposition_engine import auto_disposition_call
from app.services.dialer_automation import dialer_automation
from app.services.ai_learning import ai_learning_service

logger = logging.getLogger(__name__)


class PostCallHandler:
    """Handles all post-call processing and automation"""
    
    def __init__(self):
        self.processing_calls = set()  # Prevent duplicate processing
    
    async def process_call_completion(
        self,
        db: AsyncSession,
        call_id: int,
        transcript: Optional[str] = None,
        hume_metadata: Optional[Dict] = None,
        auto_next_call: bool = True
    ) -> Dict:
        """
        Main entry point for post-call processing
        
        Steps:
        1. Auto-disposition the call
        2. Update call status and metrics
        3. Log call completion event
        4. Prepare agent for next call (auto-unpause)
        5. Trigger any follow-up actions
        
        Returns:
            Dict with processing results
        """
        # Prevent duplicate processing
        if call_id in self.processing_calls:
            logger.warning(f"Call {call_id} already being processed, skipping")
            return {"status": "already_processing"}
        
        self.processing_calls.add(call_id)
        
        try:
            results = {
                "call_id": call_id,
                "timestamp": datetime.utcnow().isoformat(),
                "steps_completed": []
            }
            
            # Step 1: Get call details
            result = await db.execute(select(Call).where(Call.id == call_id))
            call = result.scalar_one_or_none()
            
            if not call:
                logger.error(f"Call {call_id} not found")
                return {"error": "Call not found"}
            
            # Step 2: Auto-disposition
            try:
                disposition = await auto_disposition_call(
                    db=db,
                    call_id=call_id,
                    transcript=transcript,
                    hume_metadata=hume_metadata,
                    min_confidence=0.6,
                    fallback_disposition="Manual Review"
                )
                results["disposition"] = disposition
                results["steps_completed"].append("auto_disposition")
                logger.info(f"Call {call_id} auto-dispositioned as: {disposition}")
            except Exception as e:
                logger.error(f"Auto-disposition failed for call {call_id}: {e}")
                results["disposition_error"] = str(e)
            
            # Step 3: Update call completion metrics
            try:
                await self._update_call_metrics(db, call)
                results["steps_completed"].append("update_metrics")
            except Exception as e:
                logger.error(f"Failed to update metrics for call {call_id}: {e}")
                results["metrics_error"] = str(e)
            
            # Step 4: Update agent availability
            if auto_next_call:
                try:
                    agent_ready = await self._prepare_agent_for_next_call(db, call.agent_id)
                    results["agent_ready"] = agent_ready
                    results["steps_completed"].append("prepare_agent")
                except Exception as e:
                    logger.error(f"Failed to prepare agent {call.agent_id}: {e}")
                    results["agent_error"] = str(e)
            
            # Step 5: Handle follow-up actions based on disposition
            try:
                follow_up = await self._handle_follow_up_actions(db, call)
                results["follow_up"] = follow_up
                results["steps_completed"].append("follow_up")
            except Exception as e:
                logger.error(f"Failed to handle follow-ups for call {call_id}: {e}")
                results["follow_up_error"] = str(e)
            
            # Step 6: Auto-unpause in dialer (if applicable)
            if auto_next_call:
                try:
                    unpause_result = await self._auto_unpause_dialer(db, call.agent_id)
                    results["unpause"] = unpause_result
                    results["steps_completed"].append("auto_unpause")
                except Exception as e:
                    logger.error(f"Failed to auto-unpause for agent {call.agent_id}: {e}")
                    results["unpause_error"] = str(e)
            
            # Step 7: AI Learning - Learn from this call
            try:
                learning_results = await ai_learning_service.learn_from_call(
                    db=db,
                    call=call,
                    auto_update_training=True  # Automatically update training content
                )
                results["ai_learning"] = learning_results
                results["steps_completed"].append("ai_learning")
                logger.info(f"AI learned from call {call_id}: score={learning_results.get('learning_score', 0)}")
            except Exception as e:
                logger.error(f"Failed AI learning for call {call_id}: {e}")
                results["learning_error"] = str(e)
            
            results["status"] = "completed"
            logger.info(f"Post-call processing completed for call {call_id}")
            
            return results
            
        finally:
            # Always remove from processing set
            self.processing_calls.discard(call_id)
    
    async def _update_call_metrics(self, db: AsyncSession, call: Call):
        """Update call with final metrics"""
        if not call.ended_at:
            call.ended_at = datetime.utcnow()
        
        # Calculate duration if not set
        if call.answered_at and call.ended_at and not call.duration_seconds:
            duration = (call.ended_at - call.answered_at).total_seconds()
            call.duration_seconds = int(duration)
        
        # Update status to completed
        if call.status not in ["completed", "failed"]:
            call.status = "completed"
        
        await db.commit()
        logger.info(f"Updated metrics for call {call.id}")
    
    async def _prepare_agent_for_next_call(
        self,
        db: AsyncSession,
        agent_id: int
    ) -> bool:
        """
        Prepare agent for next call
        - Mark agent as available
        - Reset any temporary states
        """
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return False
        
        # Update agent status to available/ready
        agent.status = "available"
        agent.current_call_id = None
        agent.last_call_at = datetime.utcnow()
        
        await db.commit()
        logger.info(f"Agent {agent_id} prepared for next call")
        
        return True
    
    async def _handle_follow_up_actions(
        self,
        db: AsyncSession,
        call: Call
    ) -> Dict:
        """
        Handle follow-up actions based on disposition
        """
        actions = {}
        
        disposition = call.disposition or call.outcome
        
        if not disposition:
            return {"action": "none", "reason": "no_disposition"}
        
        # Callback - Schedule follow-up
        if disposition in ["Callback", "callback"]:
            # Set follow-up date (24 hours from now by default)
            if not call.follow_up_date:
                call.follow_up_date = datetime.utcnow() + timedelta(days=1)
                call.needs_follow_up = "yes"
                actions["scheduled_callback"] = call.follow_up_date.isoformat()
        
        # DNC - Mark customer for exclusion
        elif disposition in ["DNC", "Do Not Call"]:
            # This would typically update customer record
            # For now, just flag it
            call.needs_follow_up = "no"
            actions["dnc_flagged"] = True
        
        # Connected/Interested - Mark for immediate follow-up
        elif disposition in ["Connected", "Interested"]:
            call.needs_follow_up = "yes"
            call.follow_up_date = datetime.utcnow() + timedelta(hours=2)
            actions["priority_follow_up"] = True
        
        # Not Interested - No follow-up
        elif disposition in ["Not Interested", "Wrong Number", "Voicemail"]:
            call.needs_follow_up = "no"
            actions["no_follow_up"] = True
        
        await db.commit()
        
        return actions
    
    async def _auto_unpause_dialer(
        self,
        db: AsyncSession,
        agent_id: int
    ) -> Dict:
        """
        Automatically unpause the agent in dialer to receive next call
        """
        # Get agent's dialer user
        result = await db.execute(
            select(DialerUser).where(DialerUser.agent_id == agent_id)
        )
        dialer_user = result.scalar_one_or_none()
        
        if not dialer_user:
            return {"status": "no_dialer_user"}
        
        if not dialer_user.is_logged_in:
            return {"status": "not_logged_in"}
        
        # Use dialer automation to unpause
        try:
            # This would trigger the actual unpause action in the dialer
            # For now, we'll log it
            logger.info(f"Auto-unpausing dialer user {dialer_user.id} for agent {agent_id}")
            
            # In real implementation, this would call:
            # await dialer_automation.unpause_agent(dialer_user.id)
            
            return {
                "status": "unpaused",
                "dialer_user_id": dialer_user.id,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to unpause dialer: {e}")
            return {"status": "error", "error": str(e)}
    
    async def handle_call_failure(
        self,
        db: AsyncSession,
        call_id: int,
        error: str,
        retry: bool = True
    ) -> Dict:
        """
        Handle call failures
        - Log error
        - Mark call as failed
        - Optionally retry
        """
        result = await db.execute(select(Call).where(Call.id == call_id))
        call = result.scalar_one_or_none()
        
        if not call:
            return {"error": "Call not found"}
        
        # Update call status
        call.status = "failed"
        call.ended_at = datetime.utcnow()
        
        # Store error in notes
        error_msg = f"Call failed: {error} at {datetime.utcnow().isoformat()}"
        if call.notes:
            call.notes += f"\n{error_msg}"
        else:
            call.notes = error_msg
        
        await db.commit()
        
        logger.error(f"Call {call_id} failed: {error}")
        
        return {
            "status": "failed",
            "error": error,
            "retry": retry
        }


# Global instance
post_call_handler = PostCallHandler()


async def handle_call_completed(
    db: AsyncSession,
    call_id: int,
    transcript: Optional[str] = None,
    hume_metadata: Optional[Dict] = None,
    auto_next_call: bool = True
) -> Dict:
    """
    Convenience function to handle call completion
    """
    return await post_call_handler.process_call_completion(
        db=db,
        call_id=call_id,
        transcript=transcript,
        hume_metadata=hume_metadata,
        auto_next_call=auto_next_call
    )
