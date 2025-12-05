"""
Calls API
Call initiation, management, history
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, desc
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from app.database import get_db
from app.redis_client import get_redis, RedisClient
from app.schemas.call import (
    InitiateCallRequest, CallResponse, EndCallRequest,
    CallListResponse, CallStatsResponse
)
from app.models.call import Call, CallEvent
from app.models.agent import Agent
from app.models.customer import Customer
from app.core.dependencies import get_current_agent
from app.core.exceptions import AgentAlreadyOnCallException, CustomerNotFoundException
from app.services.dialer_service import get_dialer_service, DialerService
from app.services.call_transfer import call_transfer_service
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/initiate", response_model=CallResponse)
async def initiate_call(
    request: InitiateCallRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    dialer: DialerService = Depends(get_dialer_service)
):
    """
    Call initiate karo
    
    Agent dashboard se customer ko select karke call start kare
    
    Process:
    1. Check karo agent already call par hai ya nahi
    2. Customer ka number get karo
    3. Dialer se call initiate karo
    4. Database me call record save karo
    5. Redis me call state save karo
    """
    try:
        # Check: Agent already on call?
        active_call_id = await redis.get_active_call(agent.id)
        if active_call_id:
            logger.warning(f"Agent {agent.id} already on call {active_call_id}")
            raise AgentAlreadyOnCallException(agent.id)
        
        # Customer fetch karo
        result = await db.execute(
            select(Customer).where(Customer.id == request.customer_id)
        )
        customer = result.scalar_one_or_none()
        
        if not customer:
            raise CustomerNotFoundException(request.customer_id)
        
        # Do-not-call check
        if customer.do_not_call:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer is on Do Not Call list"
            )
        
        # Unique call ID generate karo
        call_id = str(uuid.uuid4())
        
        # Dialer se call initiate karo
        logger.info(f"Initiating call {call_id} from agent {agent.id} to customer {customer.id}")
        
        dialer_response = await dialer.make_call(
            to_number=customer.phone,
            from_number=settings.TWILIO_PHONE_NUMBER if settings.DIALER_PROVIDER == "twilio" else settings.VONAGE_NUMBER,
            webhook_url=f"{settings.TWILIO_VOICE_URL}/calls/{call_id}/webhook"
        )
        
        # Database me call record create karo
        call = Call(
            call_id=call_id,
            agent_id=agent.id,
            customer_id=customer.id,
            from_number=dialer_response['from'],
            to_number=dialer_response['to'],
            status="initiated",
            dialer_call_sid=dialer_response['call_sid'],
            dialer_provider=dialer_response['provider'],
            initiated_at=datetime.utcnow(),
            notes=request.notes
        )
        
        db.add(call)
        await db.commit()
        await db.refresh(call)
        
        # Redis me call state save karo
        call_state = {
            "call_id": call_id,
            "agent_id": agent.id,
            "customer_id": customer.id,
            "status": "initiated",
            "initiated_at": datetime.utcnow().isoformat()
        }
        await redis.set_call_state(call_id, call_state)
        await redis.set_active_call(agent.id, call_id)
        
        # Call event log karo
        event = CallEvent(
            call_id=call_id,
            event_type="initiated",
            event_data={"dialer_sid": dialer_response['call_sid']}
        )
        db.add(event)
        await db.commit()
        
        logger.info(f"✅ Call {call_id} initiated successfully")
        
        return CallResponse.from_orm(call)
        
    except (AgentAlreadyOnCallException, CustomerNotFoundException):
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Call initiation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate call: {str(e)}"
        )


@router.post("/{call_id}/end")
async def end_call(
    call_id: str,
    request: EndCallRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
    dialer: DialerService = Depends(get_dialer_service)
):
    """
    Call end karo
    
    Agent call khatam kare aur outcome mark kare
    """
    try:
        # Call fetch karo
        result = await db.execute(
            select(Call).where(
                and_(
                    Call.call_id == call_id,
                    Call.agent_id == agent.id
                )
            )
        )
        call = result.scalar_one_or_none()
        
        if not call:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Call not found"
            )
        
        # Dialer me call end karo
        if call.dialer_call_sid:
            await dialer.hangup(call.dialer_call_sid)
        
        # Call record update karo
        ended_at = datetime.utcnow()
        duration = int((ended_at - call.initiated_at).total_seconds()) if call.initiated_at else 0
        
        await db.execute(
            update(Call)
            .where(Call.call_id == call_id)
            .values(
                status="completed",
                outcome=request.outcome,
                ended_at=ended_at,
                duration_seconds=duration,
                notes=request.notes if request.notes else call.notes,
                tags=request.tags if request.tags else call.tags,
                needs_follow_up="yes" if request.follow_up_date else "no",
                follow_up_date=request.follow_up_date,
                follow_up_notes=request.notes
            )
        )
        await db.commit()
        
        # Customer stats update karo
        await db.execute(
            update(Customer)
            .where(Customer.id == call.customer_id)
            .values(
                total_calls=Customer.total_calls + 1,
                last_called_at=ended_at,
                next_call_scheduled_at=request.follow_up_date,
                status="win" if request.outcome == "win" else Customer.status
            )
        )
        await db.commit()
        
        # Agent stats update karo
        agent_updates = {Agent.total_calls: Agent.total_calls + 1}
        if request.outcome == "win":
            agent_updates[Agent.total_wins] = Agent.total_wins + 1
        elif request.outcome == "loss":
            agent_updates[Agent.total_losses] = Agent.total_losses + 1
        
        await db.execute(
            update(Agent)
            .where(Agent.id == agent.id)
            .values(**agent_updates)
        )
        await db.commit()
        
        # Redis cleanup
        await redis.delete_call_state(call_id)
        await redis.remove_active_call(agent.id)
        
        # Event log
        event = CallEvent(
            call_id=call_id,
            event_type="ended",
            event_data={
                "outcome": request.outcome,
                "duration": duration
            }
        )
        db.add(event)
        await db.commit()
        
        logger.info(f"✅ Call {call_id} ended with outcome: {request.outcome}")
        
        return {
            "message": "Call ended successfully",
            "call_id": call_id,
            "outcome": request.outcome,
            "duration": duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"End call failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end call: {str(e)}"
        )


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """
    Call details get karo
    """
    result = await db.execute(
        select(Call).where(Call.call_id == call_id)
    )
    call = result.scalar_one_or_none()
    
    if not call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Call not found"
        )
    
    return CallResponse.from_orm(call)


@router.get("/", response_model=CallListResponse)
async def get_calls(
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    outcome: Optional[str] = None,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """
    Agent ki call history
    
    Filtering by status aur outcome
    """
    # Query build karo
    query = select(Call).where(Call.agent_id == agent.id)
    
    if status:
        query = query.where(Call.status == status)
    
    if outcome:
        query = query.where(Call.outcome == outcome)
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(desc(Call.initiated_at)).offset(offset).limit(page_size)
    
    # Execute
    result = await db.execute(query)
    calls = result.scalars().all()
    
    # Total count
    count_query = select(Call).where(Call.agent_id == agent.id)
    if status:
        count_query = count_query.where(Call.status == status)
    if outcome:
        count_query = count_query.where(Call.outcome == outcome)
    
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())
    
    return CallListResponse(
        total=total,
        page=page,
        page_size=page_size,
        calls=[CallResponse.from_orm(c) for c in calls]
    )


@router.get("/stats/summary", response_model=CallStatsResponse)
async def get_call_stats(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """
    Agent ke call statistics
    """
    result = await db.execute(
        select(Call).where(Call.agent_id == agent.id)
    )
    calls = result.scalars().all()
    
    total_calls = len(calls)
    answered_calls = len([c for c in calls if c.status == "answered"])
    missed_calls = len([c for c in calls if c.status in ["no_answer", "failed"]])
    
    total_duration = sum(c.duration_seconds for c in calls if c.duration_seconds)
    avg_duration = total_duration // total_calls if total_calls > 0 else 0
    
    wins = len([c for c in calls if c.outcome == "win"])
    win_rate = (wins / total_calls * 100) if total_calls > 0 else 0
    
    outcomes = {}
    for call in calls:
        if call.outcome:
            outcomes[call.outcome] = outcomes.get(call.outcome, 0) + 1
    
    return CallStatsResponse(
        total_calls=total_calls,
        answered_calls=answered_calls,
        missed_calls=missed_calls,
        average_duration=avg_duration,
        total_talk_time=total_duration,
        win_rate=win_rate,
        outcomes=outcomes
    )


# ============= Call Transfer Endpoints =============

@router.post("/{call_id}/transfer")
async def transfer_call_endpoint(
    call_id: int,
    target_agent_id: Optional[int] = None,
    transfer_queue: Optional[str] = None,
    transfer_reason: str = "customer_request",
    notes: Optional[str] = None,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """
    Transfer call to human agent
    
    Transfer Reasons:
    - customer_request: Customer asked for human
    - complex_query: Too complex for AI
    - escalation: Customer escalation
    - sales_closure: Final sales needed
    - supervisor_request: Supervisor needed
    """
    result = await call_transfer_service.initiate_transfer(
        db=db,
        call_id=call_id,
        transfer_reason=transfer_reason,
        target_agent_id=target_agent_id,
        transfer_queue=transfer_queue,
        notes=notes
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/transfer/queue")
async def get_transfer_queue(
    queue: Optional[str] = None,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """
    Get calls waiting for transfer
    """
    queue_list = await call_transfer_service.get_transfer_queue(db, queue)
    
    return {
        "queue": queue or "all",
        "total_waiting": len(queue_list),
        "calls": queue_list
    }


@router.post("/{call_id}/transfer/cancel")
async def cancel_transfer(
    call_id: int,
    reason: str = "Customer changed mind",
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel pending transfer
    """
    result = await call_transfer_service.cancel_transfer(db, call_id, reason)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/transfer/reasons")
async def get_transfer_reasons():
    """
    Get list of valid transfer reasons
    """
    return {
        "reasons": call_transfer_service.get_transfer_reasons()
    }
