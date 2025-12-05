"""
WebSocket API
Real-time audio streaming for calls
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, Optional
import asyncio
import json
import logging
import base64

from app.redis_client import get_redis, RedisClient
from app.services.hume_service import get_hume_session_manager, HumeAISessionManager
from app.core.security import verify_token
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.agent import Agent
from app.models.call import Call, CallEvent

router = APIRouter()
logger = logging.getLogger(__name__)


# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


@router.websocket("/call/{call_id}")
async def call_websocket(
    websocket: WebSocket,
    call_id: str,
    token: str = Query(..., description="JWT access token"),
    redis: RedisClient = Depends(get_redis),
    hume_manager: HumeAISessionManager = Depends(get_hume_session_manager)
):
    """
    Real-time call audio streaming WebSocket
    
    Flow:
    1. Agent connects with call_id
    2. Customer audio → Server → HumeAI
    3. HumeAI response → Server → Agent & Customer
    4. Bidirectional audio stream
    
    Message Format (Client to Server):
    {
        "type": "audio",
        "data": "<base64_audio>"
    }
    
    Message Format (Server to Client):
    {
        "type": "audio_response",
        "data": "<base64_audio>",
        "transcript": "...",
        "emotion": {...}
    }
    """
    
    # WebSocket accept karo
    await websocket.accept()
    logger.info(f"WebSocket connected for call {call_id}")
    
    # Token verify karo
    agent_id = verify_token(token)
    if not agent_id:
        await websocket.send_json({"error": "Invalid token"})
        await websocket.close()
        return
    
    # Call state verify karo
    call_state = await redis.get_call_state(call_id)
    if not call_state:
        await websocket.send_json({"error": "Call not found"})
        await websocket.close()
        return
    
    # Add to active connections
    active_connections[call_id] = websocket
    
    # HumeAI session create karo
    try:
        hume_service = await hume_manager.create_session(call_id)
        logger.info(f"HumeAI session created for call {call_id}")
        
        # Initial message
        await websocket.send_json({
            "type": "connected",
            "call_id": call_id,
            "message": "WebSocket connected, AI ready"
        })
        
        # Response handler for HumeAI
        async def on_hume_response(response: dict):
            """
            HumeAI se response aaye toh client ko send karo
            """
            try:
                response_type = response.get("type")
                
                if response_type == "audio_output":
                    # AI ki awaaz
                    audio_data = response.get("data")  # Base64 audio
                    
                    await websocket.send_json({
                        "type": "audio_response",
                        "data": audio_data,
                        "timestamp": response.get("timestamp")
                    })
                
                elif response_type == "transcript":
                    # Transcript update
                    await websocket.send_json({
                        "type": "transcript",
                        "text": response.get("text"),
                        "speaker": response.get("speaker", "ai")
                    })
                
                elif response_type == "emotion":
                    # Emotion detection
                    await websocket.send_json({
                        "type": "emotion",
                        "emotions": response.get("emotions"),
                        "sentiment": response.get("sentiment")
                    })
                
                elif response_type == "interrupt":
                    # Customer ne interrupt kiya
                    await websocket.send_json({
                        "type": "interrupt",
                        "message": "Customer interrupted"
                    })
                    
            except Exception as e:
                logger.error(f"Error sending HumeAI response: {e}")
        
        # Error handler
        async def on_hume_error(error: Exception):
            """HumeAI error"""
            logger.error(f"HumeAI error for call {call_id}: {error}")
            await websocket.send_json({
                "type": "error",
                "message": str(error)
            })
        
        # Start HumeAI conversation loop
        hume_task = asyncio.create_task(
            hume_service.start_conversation(
                on_response=on_hume_response,
                on_error=on_hume_error
            )
        )
        
        # Main WebSocket loop
        while True:
            try:
                # Client se message receive karo
                message = await websocket.receive_text()
                data = json.loads(message)
                
                message_type = data.get("type")
                
                if message_type == "audio":
                    # Customer audio chunk
                    audio_b64 = data.get("data")
                    
                    if audio_b64:
                        # Base64 decode karo
                        audio_bytes = base64.b64decode(audio_b64)
                        
                        # HumeAI ko send karo
                        await hume_service.send_audio_chunk(audio_bytes)
                
                elif message_type == "text":
                    # Text message (optional - agent ka instruction)
                    text = data.get("text")
                    await hume_service.send_text_message(text)
                
                elif message_type == "ping":
                    # Keep-alive ping
                    await websocket.send_json({"type": "pong"})
                
                elif message_type == "end":
                    # Call end signal
                    logger.info(f"End signal received for call {call_id}")
                    break
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for call {call_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                await websocket.send_json({"error": "Invalid message format"})
            except Exception as e:
                logger.error(f"WebSocket error: {e}", exc_info=True)
                break
        
    except Exception as e:
        logger.error(f"WebSocket setup error: {e}", exc_info=True)
        await websocket.send_json({"error": str(e)})
    
    finally:
        # Cleanup
        logger.info(f"Cleaning up WebSocket for call {call_id}")
        
        # HumeAI session end karo
        if call_id in hume_manager.sessions:
            await hume_manager.end_session(call_id)
        
        # Active connections se remove karo
        if call_id in active_connections:
            del active_connections[call_id]
        
        # WebSocket close karo
        try:
            await websocket.close()
        except:
            pass
        
        logger.info(f"WebSocket cleaned up for call {call_id}")


@router.websocket("/agent/{agent_id}/presence")
async def agent_presence_websocket(
    websocket: WebSocket,
    agent_id: int,
    token: str = Query(..., description="JWT access token"),
    redis: RedisClient = Depends(get_redis)
):
    """
    Agent presence WebSocket
    Real-time agent status updates
    
    Messages:
    - Call started
    - Call ended
    - New lead assigned
    - Schedule reminder
    """
    
    await websocket.accept()
    logger.info(f"Presence WebSocket connected for agent {agent_id}")
    
    # Token verify karo
    verified_agent_id = verify_token(token)
    if not verified_agent_id:
        await websocket.send_json({"error": "Invalid token"})
        await websocket.close()
        return
    
    try:
        # Redis Pub/Sub subscribe karo
        channel = f"agent:{agent_id}:events"
        pubsub = await redis.subscribe(channel)
        
        # Keep-alive ping task
        async def send_pings():
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({"type": "ping"})
                except:
                    break
        
        ping_task = asyncio.create_task(send_pings())
        
        # Listen for events
        while True:
            try:
                # Check for new messages
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                
                if message:
                    event_data = json.loads(message['data'])
                    await websocket.send_json(event_data)
                
                # Also check for WebSocket messages
                try:
                    client_msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                    data = json.loads(client_msg)
                    
                    if data.get("type") == "pong":
                        # Pong received
                        pass
                        
                except asyncio.TimeoutError:
                    pass
                    
            except WebSocketDisconnect:
                logger.info(f"Presence WebSocket disconnected for agent {agent_id}")
                break
            except Exception as e:
                logger.error(f"Presence WebSocket error: {e}")
                break
        
    finally:
        # Cleanup
        ping_task.cancel()
        await websocket.close()
        logger.info(f"Presence WebSocket cleaned up for agent {agent_id}")
