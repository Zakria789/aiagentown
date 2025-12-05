"""
WebRTC Audio Bridge WebSocket Endpoint
Handles direct WebRTC audio streams from browser JavaScript
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import asyncio
import json
import base64
import websockets
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class WebRTCBridgeSession:
    """Handles WebRTC audio bridge to HumeAI"""
    
    def __init__(self, websocket: WebSocket):
        self.client_ws = websocket  # Browser WebSocket
        self.hume_ws = None  # HumeAI WebSocket
        self.chat_id = None
        self.running = False
        self.call_active = False  # Track if actual call is in progress
        self.hume_connected = False  # Track HumeAI connection state
        
    async def connect_humeai(self):
        """Connect to HumeAI"""
        url = "wss://api.hume.ai/v0/assistant/chat"
        headers = {"X-Hume-Api-Key": settings.HUME_API_KEY}
        
        logger.info("-" * 60)
        logger.info("🔗 CONNECTING TO HUMEAI...")
        logger.info(f"   URL: {url}")
        logger.info(f"   API Key: {settings.HUME_API_KEY[:20]}...")
        logger.info(f"   Config ID: {settings.HUME_CONFIG_ID}")
        logger.info("-" * 60)
        
        try:
            self.hume_ws = await websockets.connect(url, extra_headers=headers, ping_interval=20)
            logger.info("✅ WebSocket connection established")
            
            # Send session settings
            session_msg = {
                "type": "session_settings",
                "config_id": settings.HUME_CONFIG_ID,
                "audio": {
                    "encoding": "linear16",
                    "sample_rate": 16000,
                    "channels": 1
                }
            }
            logger.info(f"📤 Sending session settings: {json.dumps(session_msg, indent=2)}")
            await self.hume_ws.send(json.dumps(session_msg))
            
            # Wait for chat_metadata
            logger.info("⏳ Waiting for chat_metadata response...")
            response = await asyncio.wait_for(self.hume_ws.recv(), timeout=5.0)
            data = json.loads(response)
            logger.info(f"📥 Received: {json.dumps(data, indent=2)}")
            
            if data.get("type") == "chat_metadata":
                self.chat_id = data.get("chat_id")
                logger.info("=" * 60)
                logger.info(f"✅ HUMEAI CONNECTED SUCCESSFULLY!")
                logger.info(f"   Chat ID: {self.chat_id}")
                logger.info("=" * 60)
                
                # Send resume message to trigger AI greeting
                logger.info("📤 Sending resume_assistant_message to trigger AI greeting...")
                await self.hume_ws.send(json.dumps({
                    "type": "resume_assistant_message"
                }))
                logger.info("   ✅ Resume sent - AI should greet now!")
                
                return True
            else:
                logger.warning(f"⚠️ Unexpected response type: {data.get('type')}")
                
        except asyncio.TimeoutError:
            logger.error("❌ HumeAI connection timeout - no response in 5 seconds")
        except Exception as e:
            logger.error(f"❌ HumeAI connection failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        return False
    
    async def forward_to_humeai(self):
        """Forward audio from browser to HumeAI"""
        audio_chunk_count = 0
        
        try:
            logger.info("🎤 AUDIO FORWARDING STARTED - Listening for browser audio...")
            
            while self.running:
                # Receive from browser
                message = await self.client_ws.receive_text()
                data = json.loads(message)
                msg_type = data.get("type")
                
                # Handle both 'audio' and 'audio_input' from browser
                if msg_type in ["audio", "audio_input"]:
                    audio_b64 = data.get("data")
                    
                    if audio_b64:
                        # Only process audio if call is active
                        if not self.call_active:
                            continue  # Ignore audio until call starts
                        
                        audio_chunk_count += 1
                        
                        # Log every 50 chunks
                        if audio_chunk_count % 50 == 0:
                            logger.info(f"📡 Audio streaming... chunk #{audio_chunk_count}")
                        
                        # Forward to HumeAI
                        await self.hume_ws.send(json.dumps({
                            "type": "audio_input",
                            "data": audio_b64
                        }))
                        
                        # First chunk special log
                        if audio_chunk_count == 1:
                            logger.info("=" * 60)
                            logger.info("🎤 FIRST AUDIO CHUNK RECEIVED!")
                            logger.info(f"   Size: {len(audio_b64)} bytes (base64)")
                            logger.info("   ✅ Forwarding to HumeAI...")
                            logger.info("=" * 60)
                        
                elif msg_type == "init":
                    # Browser initialization
                    session_id = data.get("session_id", "unknown")
                    logger.info(f"📱 Browser initialized: {session_id}")
                    logger.info("   ⏸️ Waiting for call to start...")
                    
                elif msg_type == "call_start":
                    # Call detected by CallTools monitor
                    logger.info("="*60)
                    logger.info("📞 CALL STARTED - Connecting to HumeAI and activating audio streaming!")
                    logger.info("="*60)
                    
                    # Connect to HumeAI NOW (not before)
                    if not self.hume_connected:
                        if await self.connect_humeai():
                            self.hume_connected = True
                            self.call_active = True
                            
                            # Start HumeAI listener task with error handling
                            listener_task = asyncio.create_task(self.forward_from_humeai())
                            
                            # Add done callback to catch any errors
                            def listener_done_callback(task):
                                try:
                                    task.result()
                                except Exception as e:
                                    logger.error(f"❌ HumeAI listener task failed: {e}")
                                    import traceback
                                    logger.error(traceback.format_exc())
                            
                            listener_task.add_done_callback(listener_done_callback)
                            
                            logger.info("✅ HumeAI connected and ready for audio!")
                        else:
                            logger.error("❌ Failed to connect to HumeAI")
                            await self.client_ws.send_text(json.dumps({
                                "type": "error",
                                "message": "Failed to connect to HumeAI"
                            }))
                    else:
                        self.call_active = True
                    
                elif msg_type == "call_end":
                    # Call ended
                    logger.info("="*60)
                    logger.info("📴 CALL ENDED - Stopping audio streaming and closing HumeAI")
                    logger.info("="*60)
                    self.call_active = False
                    self.running = False  # Stop the session
                    
                    # Close HumeAI connection
                    if self.hume_ws:
                        try:
                            await self.hume_ws.close()
                            logger.info("✅ HumeAI WebSocket closed")
                        except Exception as e:
                            logger.error(f"Error closing HumeAI: {e}")
                        finally:
                            self.hume_ws = None
                            self.hume_connected = False
                    
                    # Notify browser
                    try:
                        await self.client_ws.send_text(json.dumps({
                            "type": "call_end_ack",
                            "message": "Call ended, resources cleaned up"
                        }))
                    except:
                        pass
                    
        except WebSocketDisconnect:
            logger.info("Browser disconnected")
        except Exception as e:
            logger.error(f"Error forwarding audio: {e}")
    
    async def forward_from_humeai(self):
        """Forward responses from HumeAI to browser"""
        ai_response_count = 0
        message_count = 0
        
        try:
            logger.info("🤖 HUMEAI LISTENER STARTED - Waiting for AI responses...")
            logger.info(f"   WebSocket state: {self.hume_ws}")
            
            # Heartbeat task to confirm listener is alive
            last_heartbeat = asyncio.get_event_loop().time()
            
            async for message in self.hume_ws:
                message_count += 1
                current_time = asyncio.get_event_loop().time()
                
                # Log every 10 seconds to show listener is alive
                if current_time - last_heartbeat > 10:
                    logger.info(f"💓 HumeAI listener alive - received {message_count} messages")
                    last_heartbeat = current_time
                
                data = json.loads(message)
                msg_type = data.get("type")
                
                # Log ALL message types AND full data for debugging
                logger.info(f"📥 HumeAI → Backend: {msg_type}")
                logger.info(f"   Full data: {json.dumps(data, indent=2)}")
                
                if msg_type == "audio_output":
                    ai_response_count += 1
                    audio_data = data.get("data")
                    
                    logger.info("=" * 60)
                    logger.info(f"🔊 AI AUDIO RESPONSE #{ai_response_count}!")
                    logger.info(f"   Size: {len(audio_data) if audio_data else 0} bytes")
                    logger.info("   📤 Sending to browser...")
                    logger.info("=" * 60)
                    
                    # Forward AI audio to browser
                    await self.client_ws.send_text(json.dumps({
                        "type": "audio_response",
                        "data": audio_data
                    }))
                    
                elif msg_type == "user_message":
                    message_data = data.get("message", {})
                    role = message_data.get("role", "user")
                    content = message_data.get("content", "")
                    
                    logger.info("")
                    logger.info("🗣️" + "=" * 59)
                    logger.info(f"👤 CUSTOMER SPEAKING:")
                    logger.info(f"   \"{content}\"")
                    logger.info("=" * 60)
                    logger.info("")
                    
                    await self.client_ws.send_text(json.dumps({
                        "type": "transcript",
                        "speaker": "user",
                        "text": content
                    }))
                    
                elif msg_type == "assistant_message":
                    message_data = data.get("message", {})
                    role = message_data.get("role", "assistant")
                    content = message_data.get("content", "")
                    
                    logger.info("")
                    logger.info("🤖" + "=" * 59)
                    logger.info(f"🎙️ AGENT RESPONDING:")
                    logger.info(f"   \"{content}\"")
                    logger.info("=" * 60)
                    logger.info("")
                    
                    await self.client_ws.send_text(json.dumps({
                        "type": "transcript",
                        "speaker": "assistant",
                        "text": content
                    }))
                
                elif msg_type == "user_interruption":
                    logger.info("⚡ CUSTOMER INTERRUPTED AGENT")
                    
                elif msg_type == "agent_message":
                    # Alternative message type
                    content = data.get("message", {}).get("content", "")
                    logger.info("")
                    logger.info("🤖" + "=" * 59)
                    logger.info(f"🎙️ AGENT SPEAKING:")
                    logger.info(f"   \"{content}\"")
                    logger.info("=" * 60)
                    logger.info("")
                
                elif msg_type == "error":
                    # HumeAI error message - CRITICAL
                    error_msg = data.get("message", data.get("error", "Unknown error"))
                    error_code = data.get("code", "N/A")
                    logger.error("")
                    logger.error("🚨" + "=" * 59)
                    logger.error(f"❌ HUMEAI ERROR RECEIVED!")
                    logger.error(f"   Code: {error_code}")
                    logger.error(f"   Message: {error_msg}")
                    logger.error(f"   Full data: {json.dumps(data, indent=2)}")
                    logger.error("=" * 60)
                    logger.error("")
                    
                else:
                    # Log other message types for debugging
                    logger.debug(f"ℹ️ Other HumeAI message: {msg_type}")
                    logger.debug(f"   Data: {json.dumps(data, indent=2)}")
                    
        except Exception as e:
            logger.error("=" * 60)
            logger.error(f"❌ ERROR receiving from HumeAI: {e}")
            logger.error("=" * 60)
            import traceback
            logger.error(traceback.format_exc())
    
    async def start(self):
        """Start bidirectional audio bridge"""
        self.running = True
        
        # Send ready signal to browser - DON'T connect to HumeAI yet
        await self.client_ws.send_text(json.dumps({
            "type": "ready",
            "message": "Bridge ready - waiting for call to start"
        }))
        
        logger.info("⏸️ WebRTC Bridge ready - waiting for call_start event...")
        logger.info("   HumeAI will connect only when call starts")
        
        # Start listening for messages (will handle call_start event)
        await self.forward_to_humeai()
    
    async def cleanup(self):
        """Cleanup connections"""
        self.running = False
        
        if self.hume_ws:
            await self.hume_ws.close()
        
        logger.info("✅ WebRTC bridge session closed")


@router.websocket("/webrtc-audio")
async def webrtc_audio_websocket(websocket: WebSocket):
    """
    WebRTC Audio Bridge WebSocket Endpoint
    
    Receives audio directly from browser JavaScript (WebRTC capture)
    Forwards to HumeAI and returns AI responses
    
    NO VB-Cable needed!
    """
    await websocket.accept()
    logger.info("=" * 60)
    logger.info("📞 NEW WEBRTC CONNECTION ESTABLISHED")
    logger.info(f"   Client: {websocket.client}")
    logger.info("=" * 60)
    
    session = WebRTCBridgeSession(websocket)
    
    try:
        await session.start()
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ WEBRTC BRIDGE ERROR: {e}")
        logger.error("=" * 60)
        import traceback
        logger.error(traceback.format_exc())
    finally:
        await session.cleanup()
