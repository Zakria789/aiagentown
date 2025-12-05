"""
Call Transfer Service
Handles transferring calls to human agents or supervisors
"""
from typing import Dict, Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.models.call import Call
from app.models.agent import Agent

logger = logging.getLogger(__name__)


class CallTransferService:
    """
    Manages call transfers from AI agents to human agents
    """
    
    def __init__(self):
        self.transfer_reasons = {
            "customer_request": "Customer requested human agent",
            "complex_query": "Query too complex for AI",
            "escalation": "Customer escalation",
            "technical_issue": "Technical issue with AI",
            "sales_closure": "Final sales closure required",
            "supervisor_request": "Supervisor requested",
            "language_barrier": "Language not supported",
            "compliance": "Compliance requirement"
        }
    
    async def initiate_transfer(
        self,
        db: AsyncSession,
        call_id: int,
        transfer_reason: str,
        target_agent_id: Optional[int] = None,
        transfer_queue: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """
        Initiate call transfer to human agent
        
        Args:
            db: Database session
            call_id: Call to transfer
            transfer_reason: Reason for transfer (from self.transfer_reasons)
            target_agent_id: Specific human agent to transfer to (optional)
            transfer_queue: Queue name if no specific agent (e.g., "sales", "support")
            notes: Additional transfer notes
            
        Returns:
            Dict with transfer status and details
        """
        try:
            # Get call details
            result = await db.execute(select(Call).where(Call.id == call_id))
            call = result.scalar_one_or_none()
            
            if not call:
                return {"status": "error", "error": "Call not found"}
            
            if call.status not in ["answered", "on_call"]:
                return {"status": "error", "error": "Call not in transferable state"}
            
            # Validate transfer reason
            if transfer_reason not in self.transfer_reasons:
                transfer_reason = "customer_request"
            
            # Find available human agent
            if not target_agent_id:
                target_agent_id = await self._find_available_agent(db, transfer_queue)
            
            if not target_agent_id:
                # No agents available - add to transfer queue
                return await self._queue_transfer(db, call, transfer_reason, transfer_queue, notes)
            
            # Execute transfer
            transfer_result = await self._execute_transfer(
                db, call, target_agent_id, transfer_reason, notes
            )
            
            return transfer_result
        
        except Exception as e:
            logger.error(f"Transfer initiation failed for call {call_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def _find_available_agent(
        self,
        db: AsyncSession,
        queue: Optional[str] = None
    ) -> Optional[int]:
        """
        Find available human agent for transfer
        
        Priority:
        1. Agents with status='available' and role='agent' (human)
        2. Least busy agent (lowest active call count)
        """
        try:
            query = select(Agent).where(
                Agent.is_active == True,
                Agent.status == "available",
                Agent.role == "agent"  # Human agents only, not AI
            )
            
            # Filter by queue/skill if specified
            if queue:
                query = query.where(Agent.tags.contains([queue]))
            
            result = await db.execute(query)
            agents = result.scalars().all()
            
            if not agents:
                return None
            
            # Return first available agent
            # TODO: Implement load balancing logic
            return agents[0].id
        
        except Exception as e:
            logger.error(f"Error finding available agent: {e}")
            return None
    
    async def _execute_transfer(
        self,
        db: AsyncSession,
        call: Call,
        target_agent_id: int,
        transfer_reason: str,
        notes: Optional[str]
    ) -> Dict:
        """
        Execute the actual call transfer
        """
        try:
            # Get target agent
            result = await db.execute(select(Agent).where(Agent.id == target_agent_id))
            target_agent = result.scalar_one_or_none()
            
            if not target_agent:
                return {"status": "error", "error": "Target agent not found"}
            
            # Update call record
            call.status = "transferred"
            call.outcome = f"Transferred to {target_agent.full_name}"
            call.disposition = "Transfer"
            
            # Add transfer notes
            transfer_note = f"\n[{datetime.utcnow().isoformat()}] TRANSFER: {self.transfer_reasons.get(transfer_reason)}"
            if notes:
                transfer_note += f"\nNotes: {notes}"
            transfer_note += f"\nTransferred to: Agent {target_agent.agent_id} ({target_agent.full_name})"
            
            if call.notes:
                call.notes += transfer_note
            else:
                call.notes = transfer_note
            
            # Update target agent status
            target_agent.status = "on_call"
            target_agent.current_call_id = call.id
            
            await db.commit()
            
            logger.info(
                f"Call {call.id} transferred from AI agent {call.agent_id} "
                f"to human agent {target_agent_id} - Reason: {transfer_reason}"
            )
            
            return {
                "status": "transferred",
                "call_id": call.id,
                "target_agent_id": target_agent_id,
                "target_agent_name": target_agent.full_name,
                "transfer_reason": transfer_reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Transfer execution failed: {e}")
            await db.rollback()
            return {"status": "error", "error": str(e)}
    
    async def _queue_transfer(
        self,
        db: AsyncSession,
        call: Call,
        transfer_reason: str,
        queue: Optional[str],
        notes: Optional[str]
    ) -> Dict:
        """
        Queue transfer when no agents available
        """
        try:
            call.status = "transfer_queued"
            call.outcome = f"Queued for transfer - {queue or 'default'}"
            
            queue_note = f"\n[{datetime.utcnow().isoformat()}] QUEUED FOR TRANSFER"
            queue_note += f"\nReason: {self.transfer_reasons.get(transfer_reason)}"
            queue_note += f"\nQueue: {queue or 'default'}"
            if notes:
                queue_note += f"\nNotes: {notes}"
            
            if call.notes:
                call.notes += queue_note
            else:
                call.notes = queue_note
            
            await db.commit()
            
            logger.info(f"Call {call.id} queued for transfer - Queue: {queue}")
            
            return {
                "status": "queued",
                "call_id": call.id,
                "queue": queue or "default",
                "transfer_reason": transfer_reason,
                "message": "No agents available. Call queued for transfer.",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Transfer queueing failed: {e}")
            await db.rollback()
            return {"status": "error", "error": str(e)}
    
    async def cancel_transfer(
        self,
        db: AsyncSession,
        call_id: int,
        reason: str = "Customer cancelled"
    ) -> Dict:
        """
        Cancel a pending transfer request
        """
        try:
            result = await db.execute(select(Call).where(Call.id == call_id))
            call = result.scalar_one_or_none()
            
            if not call:
                return {"status": "error", "error": "Call not found"}
            
            if call.status != "transfer_queued":
                return {"status": "error", "error": "Call not in transfer queue"}
            
            # Restore call to active
            call.status = "answered"
            call.outcome = None
            
            cancel_note = f"\n[{datetime.utcnow().isoformat()}] TRANSFER CANCELLED: {reason}"
            if call.notes:
                call.notes += cancel_note
            else:
                call.notes = cancel_note
            
            await db.commit()
            
            logger.info(f"Transfer cancelled for call {call_id}: {reason}")
            
            return {
                "status": "cancelled",
                "call_id": call_id,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Transfer cancellation failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_transfer_queue(
        self,
        db: AsyncSession,
        queue: Optional[str] = None
    ) -> List[Dict]:
        """
        Get list of calls waiting for transfer
        """
        try:
            query = select(Call).where(Call.status == "transfer_queued")
            
            if queue:
                query = query.where(Call.notes.contains(f"Queue: {queue}"))
            
            query = query.order_by(Call.initiated_at)
            
            result = await db.execute(query)
            calls = result.scalars().all()
            
            return [
                {
                    "call_id": c.id,
                    "customer_phone": c.customer_phone,
                    "wait_time": (datetime.utcnow() - c.initiated_at).total_seconds(),
                    "initiated_at": c.initiated_at.isoformat(),
                    "notes": c.notes
                }
                for c in calls
            ]
        
        except Exception as e:
            logger.error(f"Failed to get transfer queue: {e}")
            return []
    
    def get_transfer_reasons(self) -> Dict[str, str]:
        """
        Get list of valid transfer reasons
        """
        return self.transfer_reasons


# Global instance
call_transfer_service = CallTransferService()


async def transfer_call(
    db: AsyncSession,
    call_id: int,
    reason: str = "customer_request",
    target_agent_id: Optional[int] = None,
    queue: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict:
    """
    Convenience function to transfer a call
    """
    return await call_transfer_service.initiate_transfer(
        db=db,
        call_id=call_id,
        transfer_reason=reason,
        target_agent_id=target_agent_id,
        transfer_queue=queue,
        notes=notes
    )
