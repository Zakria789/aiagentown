"""
HumeAI Audio Service
Handles audio streaming to/from HumeAI EVI (Empathic Voice Interface)
"""
import asyncio
import json
import base64
import logging
from typing import Optional, Dict, Any
import websockets
from datetime import datetime

logger = logging.getLogger(__name__)


class HumeAudioService:
    """
    Service to interact with HumeAI's Empathic Voice Interface
    Handles audio streaming, emotion detection, and natural conversations
    """
    
    def __init__(self, api_key: str = None, config_id: str = None):
        """
        Initialize HumeAI audio service
        
        Args:
            api_key: HumeAI API key (from .env)
            config_id: HumeAI configuration ID (optional)
        """
        from app.config import settings
        
        self.api_key = api_key or settings.HUME_API_KEY
        self.config_id = config_id or settings.HUME_CONFIG_ID
        
        # WebSocket connection
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        
        # Audio queue for responses
        self.response_queue = asyncio.Queue()
        
        # Session info
        self.session_id: Optional[str] = None
        self.conversation_id: Optional[str] = None
    
    async def connect(self):
        """
        Connect to HumeAI WebSocket
        """
        try:
            # HumeAI EVI WebSocket URL
            url = f"wss://api.hume.ai/v0/assistant/chat"
            
            # Headers with API key
            headers = {
                "X-Hume-Api-Key": self.api_key
            }
            
            logger.info(f"Connecting to HumeAI EVI...")
            
            # Connect
            self.websocket = await websockets.connect(
                url,
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.is_connected = True
            logger.info("✅ Connected to HumeAI successfully")
            
            # Send initialization message
            init_message = {
                "type": "session_settings",
                "config_id": self.config_id,
                "audio": {
                    "encoding": "linear16",
                    "sample_rate": 48000,
                    "channels": 1
                }
            }
            
            await self.websocket.send(json.dumps(init_message))
            logger.info("Sent session settings to HumeAI")
            
            # Start receiving responses
            asyncio.create_task(self._receive_loop())
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to HumeAI: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from HumeAI"""
        try:
            if self.websocket:
                await self.websocket.close()
                self.is_connected = False
                logger.info("Disconnected from HumeAI")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
    
    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to HumeAI
        
        Args:
            audio_data: Raw audio bytes (16-bit PCM, 16kHz, mono)
        """
        if not self.is_connected or not self.websocket:
            logger.warning("Not connected to HumeAI")
            return
        
        try:
            # Encode audio to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Create audio message
            message = {
                "type": "audio_input",
                "data": audio_base64
            }
            
            # Send to HumeAI
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent {len(audio_data)} bytes to HumeAI")
            
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
    
    async def _receive_loop(self):
        """
        Receive loop for HumeAI responses
        Runs in background task
        """
        try:
            while self.is_connected and self.websocket:
                # Receive message
                message_raw = await self.websocket.recv()
                message = json.loads(message_raw)
                
                # Process message based on type
                message_type = message.get("type")
                
                if message_type == "audio_output":
                    # Audio response from HumeAI
                    await self._handle_audio_output(message)
                    
                elif message_type == "user_message":
                    # User transcript (what customer said)
                    await self._handle_user_message(message)
                    
                elif message_type == "assistant_message":
                    # Assistant transcript (what AI said)
                    await self._handle_assistant_message(message)
                    
                elif message_type == "emotion_scores":
                    # Emotion detection
                    await self._handle_emotion_scores(message)
                    
                elif message_type == "session_started":
                    # Session info
                    self.session_id = message.get("session_id")
                    logger.info(f"HumeAI session started: {self.session_id}")
                    
                elif message_type == "error":
                    # Error from HumeAI
                    logger.error(f"HumeAI error: {message.get('message')}")
                    
                else:
                    logger.debug(f"Received message type: {message_type}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("HumeAI connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            self.is_connected = False
    
    async def _handle_audio_output(self, message: Dict[str, Any]):
        """Handle audio response from HumeAI"""
        try:
            # Decode base64 audio
            audio_base64 = message.get("data")
            audio_data = base64.b64decode(audio_base64)
            
            # Add to response queue
            await self.response_queue.put({
                "type": "audio",
                "data": audio_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.debug(f"Received audio response: {len(audio_data)} bytes")
            
        except Exception as e:
            logger.error(f"Error handling audio output: {e}")
    
    async def _handle_user_message(self, message: Dict[str, Any]):
        """Handle user transcript"""
        try:
            text = message.get("message", {}).get("content", "")
            
            logger.info(f"Customer said: {text}")
            
            # Add to response queue for logging
            await self.response_queue.put({
                "type": "transcript",
                "speaker": "customer",
                "text": text,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling user message: {e}")
    
    async def _handle_assistant_message(self, message: Dict[str, Any]):
        """Handle assistant transcript"""
        try:
            text = message.get("message", {}).get("content", "")
            
            logger.info(f"AI said: {text}")
            
            # Add to response queue
            await self.response_queue.put({
                "type": "transcript",
                "speaker": "ai",
                "text": text,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling assistant message: {e}")
    
    async def _handle_emotion_scores(self, message: Dict[str, Any]):
        """Handle emotion detection"""
        try:
            emotions = message.get("scores", [])
            
            # Get top emotions
            top_emotions = sorted(
                emotions,
                key=lambda x: x.get("score", 0),
                reverse=True
            )[:3]
            
            logger.info(f"Detected emotions: {[e.get('name') for e in top_emotions]}")
            
            # Add to response queue
            await self.response_queue.put({
                "type": "emotion",
                "emotions": top_emotions,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling emotions: {e}")
    
    async def receive_response(self) -> Dict[str, Any]:
        """
        Get next response from HumeAI
        Blocks until response available
        
        Returns:
            Response dict with type, data, etc.
        """
        return await self.response_queue.get()
    
    async def pause(self):
        """Pause audio processing"""
        if self.websocket:
            await self.websocket.send(json.dumps({"type": "pause"}))
    
    async def resume(self):
        """Resume audio processing"""
        if self.websocket:
            await self.websocket.send(json.dumps({"type": "resume"}))
