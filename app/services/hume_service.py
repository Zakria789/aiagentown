"""
HumeAI Service
Real-time AI voice conversation integration
"""

import asyncio
import json
import logging
import websockets
from typing import Optional, Callable, Dict, Any
import base64
from app.config import settings
from app.core.exceptions import HumeAIException

logger = logging.getLogger(__name__)


class HumeAIService:
    """
    HumeAI real-time WebSocket integration
    Voice-to-voice AI conversation
    """
    
    def __init__(self, config_id: Optional[str] = None):
        self.ws_url = settings.HUME_WEBSOCKET_URL
        self.api_key = settings.HUME_API_KEY
        # Use agent-specific config_id if provided, otherwise use default
        self.config_id = config_id or settings.HUME_CONFIG_ID
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.conversation_active = False
        
    async def connect(self) -> bool:
        """
        HumeAI WebSocket se connect karo
        
        Returns:
            True if connection successful
        """
        try:
            # WebSocket URL with authentication
            auth_url = f"{self.ws_url}?api_key={self.api_key}"
            
            if self.config_id:
                auth_url += f"&config_id={self.config_id}"
            
            logger.info("Connecting to HumeAI WebSocket...")
            
            self.ws = await websockets.connect(
                auth_url,
                ping_interval=settings.WEBSOCKET_PING_INTERVAL,
                ping_timeout=settings.WEBSOCKET_PING_TIMEOUT,
                max_size=10 * 1024 * 1024,  # 10MB max message size
            )
            
            self.is_connected = True
            logger.info("✅ HumeAI WebSocket connected successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ HumeAI connection failed: {e}")
            self.is_connected = False
            raise HumeAIException(f"Connection failed: {str(e)}")
    
    async def disconnect(self):
        """WebSocket connection close karo"""
        try:
            self.conversation_active = False
            
            if self.ws and self.is_connected:
                await self.ws.close()
                logger.info("HumeAI disconnected")
            
            self.is_connected = False
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    async def send_audio_chunk(self, audio_data: bytes):
        """
        Audio chunk HumeAI ko send karo
        
        Args:
            audio_data: Raw audio bytes (PCM 16kHz mono)
        """
        if not self.is_connected or not self.ws:
            raise HumeAIException("Not connected to HumeAI")
        
        try:
            # Audio ko base64 encode karo
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # HumeAI message format
            message = {
                "type": "audio_input",
                "data": audio_b64,
                "format": {
                    "encoding": settings.AUDIO_FORMAT,
                    "sample_rate": settings.AUDIO_SAMPLE_RATE,
                    "channels": settings.AUDIO_CHANNELS
                }
            }
            
            await self.ws.send(json.dumps(message))
            
        except Exception as e:
            logger.error(f"Failed to send audio chunk: {e}")
            raise HumeAIException(f"Audio send failed: {str(e)}")
    
    async def receive_response(self) -> Optional[Dict[str, Any]]:
        """
        HumeAI se response receive karo
        
        Returns:
            Response dict with audio, text, emotions, etc.
        """
        if not self.is_connected or not self.ws:
            return None
        
        try:
            response = await self.ws.recv()
            
            # JSON parse karo
            data = json.loads(response)
            
            return data
            
        except websockets.exceptions.ConnectionClosed:
            logger.warning("HumeAI connection closed")
            self.is_connected = False
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse HumeAI response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error receiving response: {e}")
            return None
    
    async def start_conversation(
        self,
        on_response: Callable[[Dict[str, Any]], None],
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        """
        Conversation loop start karo
        
        Args:
            on_response: Callback jab HumeAI response aaye
            on_error: Error callback
        """
        self.conversation_active = True
        
        logger.info("Starting HumeAI conversation loop")
        
        try:
            while self.conversation_active and self.is_connected:
                # Response receive karo
                response = await self.receive_response()
                
                if response is None:
                    break
                
                # Response type handle karo
                response_type = response.get("type")
                
                if response_type == "audio_output":
                    # AI ka audio response
                    await on_response(response)
                
                elif response_type == "transcript":
                    # Transcript update
                    logger.info(f"Transcript: {response.get('text')}")
                
                elif response_type == "emotion":
                    # Emotion detection
                    logger.info(f"Emotion detected: {response.get('emotions')}")
                
                elif response_type == "error":
                    # Error from HumeAI
                    logger.error(f"HumeAI error: {response.get('message')}")
                    if on_error:
                        on_error(HumeAIException(response.get('message')))
                
                elif response_type == "interrupt":
                    # User interrupted AI
                    logger.info("User interrupt detected")
                    await on_response({"type": "interrupt"})
                
        except Exception as e:
            logger.error(f"Conversation loop error: {e}")
            if on_error:
                on_error(e)
        finally:
            self.conversation_active = False
    
    async def send_text_message(self, text: str):
        """
        Text message send karo (AI ko instruction dene ke liye)
        
        Args:
            text: Message text
        """
        if not self.is_connected or not self.ws:
            raise HumeAIException("Not connected")
        
        try:
            message = {
                "type": "text_input",
                "text": text
            }
            
            await self.ws.send(json.dumps(message))
            logger.info(f"Sent text message: {text}")
            
        except Exception as e:
            logger.error(f"Failed to send text message: {e}")
            raise HumeAIException(f"Text send failed: {str(e)}")
    
    async def configure_ai(self, config: Dict[str, Any]):
        """
        AI configuration update karo
        
        Args:
            config: Configuration dict (voice, personality, etc.)
        """
        if not self.is_connected or not self.ws:
            raise HumeAIException("Not connected")
        
        try:
            message = {
                "type": "config",
                "config": config
            }
            
            await self.ws.send(json.dumps(message))
            logger.info("AI configuration updated")
            
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            raise HumeAIException(f"Config update failed: {str(e)}")


class HumeAISessionManager:
    """
    HumeAI session management
    Multiple concurrent calls ke liye
    """
    
    def __init__(self):
        self.sessions: Dict[str, HumeAIService] = {}
    
    async def create_session(self, call_id: str, agent_config_id: Optional[str] = None) -> HumeAIService:
        """
        Naya HumeAI session create karo
        
        Args:
            call_id: Unique call ID
            agent_config_id: Agent-specific HumeAI config ID
        
        Returns:
            HumeAI service instance
        """
        if call_id in self.sessions:
            logger.warning(f"Session already exists for call {call_id}")
            return self.sessions[call_id]
        
        # Create HumeAI service with agent-specific config
        hume_service = HumeAIService(config_id=agent_config_id)
        await hume_service.connect()
        
        self.sessions[call_id] = hume_service
        
        logger.info(f"Created HumeAI session for call {call_id} with config {agent_config_id or 'default'}")
        
        return hume_service
    
    async def get_session(self, call_id: str) -> Optional[HumeAIService]:
        """Session get karo"""
        return self.sessions.get(call_id)
    
    async def end_session(self, call_id: str):
        """Session end karo aur cleanup"""
        if call_id in self.sessions:
            await self.sessions[call_id].disconnect()
            del self.sessions[call_id]
            logger.info(f"Ended HumeAI session for call {call_id}")
    
    async def end_all_sessions(self):
        """Sare sessions end karo (shutdown par)"""
        for call_id in list(self.sessions.keys()):
            await self.end_session(call_id)


    async def generate_twiml_for_call(
        self,
        call_id: str,
        agent_id: int,
        customer_name: str = "Customer",
        campaign_script: Optional[str] = None,
        websocket_url: str = None
    ) -> str:
        """
        Generate TwiML to connect call audio to HumeAI WebSocket
        
        Args:
            call_id: Unique call ID
            agent_id: Agent ID
            customer_name: Customer ka naam
            campaign_script: Agent ka campaign script (optional)
            websocket_url: WebSocket URL for audio streaming
            
        Returns:
            TwiML XML string
        """
        # Initial greeting (agar campaign script hai toh usse use karo)
        greeting = campaign_script if campaign_script else f"Hello {customer_name}, this is an AI assistant. How can I help you today?"
        
        # TwiML XML generate karo
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{greeting}</Say>
    <Connect>
        <Stream url="{websocket_url or f'wss://{settings.HOST}/ws/hume/{call_id}'}">
            <Parameter name="call_id" value="{call_id}" />
            <Parameter name="agent_id" value="{agent_id}" />
            <Parameter name="customer_name" value="{customer_name}" />
        </Stream>
    </Connect>
</Response>'''
        
        return twiml


# Global session manager
hume_session_manager = HumeAISessionManager()


def get_hume_session_manager() -> HumeAISessionManager:
    """Dependency injection"""
    return hume_session_manager


# Global hume service instance (for webhook usage)
hume_service = HumeAISessionManager()
