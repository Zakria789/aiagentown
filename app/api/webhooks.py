"""
Dialer Webhooks API
Handle incoming webhook events from Twilio, Vonage, etc.
Connect HumeAI when call is answered
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import Response, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any
import logging
from datetime import datetime

from app.database import get_db
from app.models.call import Call, CallEvent
from app.models.agent import Agent
from app.redis_client import get_redis, RedisClient
from app.services.hume_service import hume_service
from app.services.post_call_handler import handle_call_completed
from app.services.notification_service import notification_service, NotificationPriority
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/hume")
async def hume_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis)
):
    """
    HumeAI Webhook
    
    Receives events from HumeAI assistant:
    - chat_started: Conversation shuru hua
    - chat_ended: Conversation khatam hua
    - user_message: Customer ne kuch bola
    - assistant_message: AI ne jawab diya
    - audio_output: AI audio generate hua
    """
    try:
        # Get event data
        event_data = await request.json()
        event_type = event_data.get('type')
        chat_id = event_data.get('chat_id')
        
        logger.info(f"🎯 HumeAI webhook: type={event_type}, chat_id={chat_id}")
        logger.debug(f"Full event data: {event_data}")
        
        # Store in Redis for real-time access
        if chat_id:
            await redis.publish_event(
                channel=f"hume:chat:{chat_id}",
                event={
                    "type": event_type,
                    "data": event_data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Process different event types
        if event_type == "chat_started":
            logger.info(f"✅ HumeAI chat started: {chat_id}")
            
        elif event_type == "user_message":
            # Customer spoke
            message = event_data.get('message', {})
            text = message.get('content', '')
            logger.info(f"👤 Customer: {text}")
            
            # Store transcript
            if chat_id:
                transcript_key = f"hume:transcript:{chat_id}"
                await redis.append_to_list(transcript_key, {
                    "speaker": "customer",
                    "text": text,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        elif event_type == "assistant_message":
            # AI responded
            message = event_data.get('message', {})
            text = message.get('content', '')
            logger.info(f"🤖 AI Agent: {text}")
            
            # Store transcript
            if chat_id:
                transcript_key = f"hume:transcript:{chat_id}"
                await redis.append_to_list(transcript_key, {
                    "speaker": "ai",
                    "text": text,
                    "timestamp": datetime.utcnow().isoformat()
                })
        
        elif event_type == "chat_ended":
            logger.info(f"✅ HumeAI chat ended: {chat_id}")
            
            # Get full transcript
            if chat_id:
                transcript_key = f"hume:transcript:{chat_id}"
                full_transcript = await redis.get_list(transcript_key)
                logger.info(f"📝 Full transcript: {len(full_transcript) if full_transcript else 0} messages")
        
        elif event_type == "audio_output":
            # AI generated audio (can log/monitor)
            logger.debug(f"🔊 AI audio output for chat {chat_id}")
        
        return {"status": "ok", "received": event_type}
        
    except Exception as e:
        logger.error(f"❌ HumeAI webhook error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.post("/calls/{call_id}/webhook")
async def twilio_voice_webhook(
    call_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis)
):
    """
    Twilio Voice Webhook
    
    Jab call answer hoti hai, yeh webhook trigger hota hai
    Yahan pe HumeAI connect karenge
    
    Events:
    - initiated: Call shuru hui
    - ringing: Phone ring ho raha hai
    - answered: Customer ne uthaya (🔥 YAHAN HUMEAI CONNECT!)
    - completed: Call khatam hui
    """
    try:
        # Get form data from Twilio
        form_data = await request.form()
        call_status = form_data.get('CallStatus', '').lower()
        call_sid = form_data.get('CallSid')
        from_number = form_data.get('From')
        to_number = form_data.get('To')
        
        logger.info(f"📞 Twilio webhook: call_id={call_id}, status={call_status}, sid={call_sid}")
        
        # Get call from database
        result = await db.execute(
            select(Call).where(Call.call_id == call_id)
        )
        call = result.scalar_one_or_none()
        
        if not call:
            logger.error(f"❌ Call {call_id} not found in database")
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Get agent details
        agent_result = await db.execute(
            select(Agent).where(Agent.id == call.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        
        # Update call status in database
        await db.execute(
            update(Call)
            .where(Call.call_id == call_id)
            .values(status=call_status)
        )
        
        # Log event
        event = CallEvent(
            call_id=call_id,
            event_type=call_status,
            event_data={
                "call_sid": call_sid,
                "from": from_number,
                "to": to_number
            }
        )
        db.add(event)
        await db.commit()
        
        # Update Redis state
        call_state = await redis.get_call_state(call_id)
        if call_state:
            call_state["status"] = call_status
            await redis.set_call_state(call_id, call_state)
        
        # 🔥 YAHAN PE HUMEAI CONNECT HOGA!
        if call_status == 'in-progress' or call_status == 'answered':
            logger.info(f"🎯 Call answered! Connecting HumeAI for call {call_id}")
            
            # Update answered_at timestamp
            await db.execute(
                update(Call)
                .where(Call.call_id == call_id)
                .values(answered_at=datetime.utcnow())
            )
            await db.commit()
            
            # Get agent's campaign script (agar hai toh)
            campaign_script = agent.campaign_script if agent else None
            
            # HumeAI ko connect karo
            twiml_response = await hume_service.generate_twiml_for_call(
                call_id=call_id,
                agent_id=call.agent_id,
                customer_name=call.customer.full_name if call.customer else "Customer",
                campaign_script=campaign_script,
                websocket_url=f"wss://{settings.HOST}/ws/hume/{call_id}"
            )
            
            logger.info(f"✅ HumeAI connected for call {call_id}")
            
            # Return TwiML to connect audio stream to HumeAI
            return Response(content=twiml_response, media_type="application/xml")
        
        # For other statuses, return simple TwiML
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Webhook error for call {call_id}: {e}", exc_info=True)
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response><Say>Error occurred</Say></Response>',
            media_type="application/xml"
        )


@router.post("/calls/{call_id}/webhook/status")
async def twilio_status_callback(
    call_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Twilio Status Callback
    
    Call ke lifecycle events track karne ke liye
    """
    try:
        form_data = await request.form()
        call_status = form_data.get('CallStatus', '').lower()
        call_sid = form_data.get('CallSid')
        duration = form_data.get('CallDuration')
        
        logger.info(f"📊 Status callback: call_id={call_id}, status={call_status}, duration={duration}")
        
        # Update call in database
        update_data = {"status": call_status}
        
        if call_status == 'completed' and duration:
            update_data["duration_seconds"] = int(duration)
            update_data["ended_at"] = datetime.utcnow()
        
        await db.execute(
            update(Call)
            .where(Call.call_id == call_id)
            .values(**update_data)
        )
        
        # Log event
        event = CallEvent(
            call_id=call_id,
            event_type=f"status_{call_status}",
            event_data={
                "call_sid": call_sid,
                "duration": duration
            }
        )
        db.add(event)
        await db.commit()
        
        # 🔥 TRIGGER POST-CALL AUTOMATION ON COMPLETION
        if call_status == 'completed':
            logger.info(f"🎯 Call completed! Triggering post-call automation for {call_id}")
            
            try:
                # Get call from database
                result = await db.execute(
                    select(Call).where(Call.call_id == call_id)
                )
                call = result.scalar_one_or_none()
                
                if call:
                    # Trigger post-call processing (async, non-blocking)
                    import asyncio
                    asyncio.create_task(
                        handle_call_completed(
                            db=db,
                            call_id=call.id,
                            transcript=call.transcript,
                            hume_metadata=None,  # Can extract from HumeAI session
                            auto_next_call=True
                        )
                    )
                    logger.info(f"✅ Post-call automation triggered for call {call_id}")
            except Exception as e:
                logger.error(f"❌ Failed to trigger post-call automation: {e}")
                
                # Send notification about error
                await notification_service.notify_call_error(
                    db=db,
                    call_id=call.id if call else 0,
                    agent_id=call.agent_id if call else 0,
                    error=f"Post-call automation failed: {str(e)}"
                )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Status callback error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.post("/calls/{call_id}/webhook/events")
async def vonage_event_webhook(
    call_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Vonage Event Webhook
    
    Vonage ke events ke liye
    """
    try:
        event_data = await request.json()
        event_status = event_data.get('status', '').lower()
        
        logger.info(f"📞 Vonage event: call_id={call_id}, status={event_status}")
        
        # Similar processing as Twilio
        await db.execute(
            update(Call)
            .where(Call.call_id == call_id)
            .values(status=event_status)
        )
        
        event = CallEvent(
            call_id=call_id,
            event_type=event_status,
            event_data=event_data
        )
        db.add(event)
        await db.commit()
        
        # If answered, connect HumeAI
        if event_status == 'answered':
            logger.info(f"🎯 Vonage call answered! Connecting HumeAI for call {call_id}")
            # Return NCCO to connect audio stream
            return {
                "action": "connect",
                "endpoint": [{
                    "type": "websocket",
                    "uri": f"wss://{settings.HOST}/ws/hume/{call_id}",
                    "content-type": "audio/l16;rate=16000"
                }]
            }
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Vonage event error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@router.post("/calls/{call_id}/recording")
async def recording_status_callback(
    call_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Recording Status Callback
    
    Jab call ki recording complete ho jaye
    """
    try:
        form_data = await request.form()
        recording_url = form_data.get('RecordingUrl')
        recording_sid = form_data.get('RecordingSid')
        recording_duration = form_data.get('RecordingDuration')
        
        logger.info(f"🎙️ Recording ready: call_id={call_id}, url={recording_url}")
        
        # Update call with recording info
        await db.execute(
            update(Call)
            .where(Call.call_id == call_id)
            .values(
                recording_url=recording_url,
                recording_duration=int(recording_duration) if recording_duration else None
            )
        )
        await db.commit()
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"❌ Recording callback error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
