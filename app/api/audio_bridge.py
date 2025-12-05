"""
Audio Bridge WebSocket Endpoint for CallTools <-> HumeAI Integration
Handles bidirectional audio streaming with low latency (<300ms)
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Optional
import logging
import asyncio
import json
import base64
import time
import websockets
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Active audio bridges: {session_id: session}
active_bridges: Dict[str, 'AudioBridgeSession'] = {}


class HumeAIClient:
    """HumeAI Realtime WebSocket Client"""
    
    def __init__(self, api_key: str, config_id: str):
        self.api_key = api_key
        self.config_id = config_id
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.chat_id: Optional[str] = None
        
    async def connect(self):
        """Connect to HumeAI"""
        url = "wss://api.hume.ai/v0/assistant/chat"
        headers = {"X-Hume-Api-Key": self.api_key}
        
        try:
            self.ws = await websockets.connect(url, extra_headers=headers, ping_interval=20)
            
            # Send session settings
            await self.ws.send(json.dumps({
                "type": "session_settings",
                "config_id": self.config_id,
                "audio": {
                    "encoding": "linear16",
                    "sample_rate": 16000,
                    "channels": 1
                }
            }))
            
            # Wait for chat_metadata
            response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
            data = json.loads(response)
            
            if data.get("type") == "chat_metadata":
                self.chat_id = data.get("chat_id")
                self.connected = True
                logger.info(f"✅ HumeAI Connected - Chat ID: {self.chat_id}")
                return True
                
        except Exception as e:
            logger.error(f"❌ HumeAI connection failed: {e}")
            
        return False
    
    async def send_audio(self, audio_data: bytes):
        """Send audio to HumeAI"""
        if not self.connected or not self.ws:
            return False
            
        try:
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            await self.ws.send(json.dumps({
                "type": "audio_input",
                "data": audio_b64
            }))
            return True
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            self.connected = False
            return False
    
    async def receive_messages(self, callback):
        """Receive and process HumeAI messages"""
        if not self.ws:
            return
            
        try:
            async for message in self.ws:
                data = json.loads(message)
                msg_type = data.get("type")
                
                if msg_type == "audio_output":
                    audio_b64 = data.get("data")
                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        await callback("audio", audio_bytes)
                        
                elif msg_type == "user_message":
                    transcript = data.get("message", {}).get("content")
                    await callback("transcript_user", transcript)
                    
                elif msg_type == "assistant_message":
                    transcript = data.get("message", {}).get("content")
                    await callback("transcript_ai", transcript)
                    
        except Exception as e:
            logger.error(f"Error receiving from HumeAI: {e}")
            self.connected = False
    
    async def close(self):
        """Close connection"""
        if self.ws:
            await self.ws.close()
            self.connected = False


class AudioBridgeSession:
    """Manages CallTools <-> HumeAI audio bridge"""
    
    def __init__(self, session_id: str, calltools_ws: WebSocket):
        self.session_id = session_id
        self.calltools_ws = calltools_ws
        self.hume_client: Optional[HumeAIClient] = None
        self.running = False
        self.stats = {
            "started": time.time(),
            "frames_sent": 0,
            "frames_received": 0,
            "latency_ms": []
        }
        
    async def start(self):
        """Start audio bridge"""
        logger.info(f"🚀 Starting session: {self.session_id}")
        
        self.hume_client = HumeAIClient(
            api_key=settings.HUME_API_KEY,
            config_id=settings.HUME_CONFIG_ID
        )
        
        if not await self.hume_client.connect():
            await self.calltools_ws.send_json({
                "type": "error",
                "message": "Failed to connect to HumeAI"
            })
            return False
        
        await self.calltools_ws.send_json({
            "type": "ready",
            "chat_id": self.hume_client.chat_id
        })
        
        self.running = True
        asyncio.create_task(self._receive_from_hume())
        return True
    
    async def _receive_from_hume(self):
        """Forward HumeAI responses to CallTools"""
        async def handle_message(msg_type: str, data):
            if msg_type == "audio":
                audio_b64 = base64.b64encode(data).decode('utf-8')
                await self.calltools_ws.send_json({
                    "type": "audio_output",
                    "data": audio_b64
                })
                self.stats["frames_received"] += 1
            elif msg_type.startswith("transcript"):
                await self.calltools_ws.send_json({
                    "type": msg_type,
                    "text": data
                })
        
        if self.hume_client:
            await self.hume_client.receive_messages(handle_message)
    
    async def send_audio(self, audio_data: bytes):
        """Send audio to HumeAI"""
        if not self.hume_client or not self.running:
            return False
        
        start = time.time()
        success = await self.hume_client.send_audio(audio_data)
        
        if success:
            self.stats["frames_sent"] += 1
            latency = (time.time() - start) * 1000
            self.stats["latency_ms"].append(latency)
            
            if latency > 300:
                logger.warning(f"⚠️ High latency: {latency:.1f}ms")
        
        return success
    
    async def stop(self):
        """Stop session"""
        self.running = False
        if self.hume_client:
            await self.hume_client.close()
        
        duration = time.time() - self.stats["started"]
        avg_latency = sum(self.stats["latency_ms"]) / len(self.stats["latency_ms"]) if self.stats["latency_ms"] else 0
        
        logger.info(f"📊 Session ended - Duration: {duration:.1f}s, Frames: {self.stats['frames_sent']}/{self.stats['frames_received']}, Latency: {avg_latency:.1f}ms")


@router.websocket("/audio-bridge/{session_id}")
async def audio_bridge_websocket(websocket: WebSocket, session_id: str):
    """
    CallTools Audio Bridge WebSocket
    
    Messages from CallTools:
    - {"type": "audio_input", "data": "<base64_audio>"}
    
    Messages to CallTools:
    - {"type": "ready", "chat_id": "..."}
    - {"type": "audio_output", "data": "<base64_audio>"}
    - {"type": "transcript_user", "text": "..."}
    - {"type": "transcript_ai", "text": "..."}
    """
    # Accept WebSocket connection without origin checking
    await websocket.accept()
    logger.info(f"📞 CallTools connected: {session_id}")
    
    session = AudioBridgeSession(session_id, websocket)
    active_bridges[session_id] = session
    
    try:
        if not await session.start():
            await websocket.close()
            return
        
        while session.running:
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                msg_type = message.get("type")
                
                if msg_type == "audio_input":
                    audio_b64 = message.get("data")
                    if audio_b64:
                        audio_bytes = base64.b64decode(audio_b64)
                        await session.send_audio(audio_bytes)
                        
                elif msg_type == "close":
                    break
                    
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
                
    except WebSocketDisconnect:
        logger.info(f"CallTools disconnected: {session_id}")
    except Exception as e:
        logger.error(f"Bridge error: {e}")
    finally:
        await session.stop()
        active_bridges.pop(session_id, None)
        try:
            await websocket.close()
        except:
            pass


@router.get("/audio-bridge/stats")
async def get_bridge_stats():
    """Get statistics for active audio bridges"""
    stats = {}
    for session_id, session in active_bridges.items():
        duration = time.time() - session.stats["started"]
        avg_latency = sum(session.stats["latency_ms"]) / len(session.stats["latency_ms"]) if session.stats["latency_ms"] else 0
        
        stats[session_id] = {
            "duration_seconds": round(duration, 1),
            "frames_sent": session.stats["frames_sent"],
            "frames_received": session.stats["frames_received"],
            "avg_latency_ms": round(avg_latency, 1),
            "chat_id": session.hume_client.chat_id if session.hume_client else None,
            "connected": session.hume_client.connected if session.hume_client else False
        }
    
    return {
        "active_sessions": len(active_bridges),
        "sessions": stats
    }
