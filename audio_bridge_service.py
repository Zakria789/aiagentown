"""
Audio Bridge Service
Captures audio from VB-Cable, sends to backend, receives HumeAI response, plays back
"""
import asyncio
import json
import pyaudio
import websockets
import numpy as np
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Audio Configuration
CHUNK_SIZE = 1024  # Samples per frame
FORMAT = pyaudio.paInt16  # 16-bit audio
CHANNELS = 1  # Mono
RATE = 48000  # 48kHz sample rate (HumeAI requirement)

# Backend WebSocket URL
BACKEND_WS_URL = "ws://localhost:8000/ws/audio/bridge"

# VB-Cable Device Names (may vary on your system)
VB_CABLE_OUTPUT = "CABLE Output"  # For capturing (recording)
VB_CABLE_INPUT = "CABLE Input"    # For playback


class AudioBridge:
    """
    Bridges audio between VB-Cable and Backend/HumeAI
    """
    
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.websocket = None
        self.is_running = False
        
        # Audio streams
        self.input_stream = None   # Capture from VB-Cable Output
        self.output_stream = None  # Playback to VB-Cable Input
        
        # Audio buffers
        self.playback_queue = asyncio.Queue()
    
    def list_audio_devices(self):
        """List all available audio devices"""
        logger.info("Available Audio Devices:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            logger.info(f"  [{i}] {info['name']} - "
                       f"In:{info['maxInputChannels']} Out:{info['maxOutputChannels']}")
    
    def find_device_index(self, device_name, input_device=True):
        """Find device index by name"""
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if device_name.lower() in info['name'].lower():
                if input_device and info['maxInputChannels'] > 0:
                    return i
                elif not input_device and info['maxOutputChannels'] > 0:
                    return i
        return None
    
    def audio_callback_capture(self, in_data, frame_count, time_info, status):
        """Callback for capturing audio from VB-Cable Output"""
        if self.websocket and self.is_running:
            # Send audio to backend via WebSocket
            asyncio.create_task(self.send_audio(in_data))
        return (None, pyaudio.paContinue)
    
    def audio_callback_playback(self, in_data, frame_count, time_info, status):
        """Callback for playing audio to VB-Cable Input"""
        try:
            # Get audio from playback queue
            audio_data = self.playback_queue.get_nowait()
            return (audio_data, pyaudio.paContinue)
        except:
            # Return silence if no audio available
            silence = b'\x00' * (frame_count * CHANNELS * 2)
            return (silence, pyaudio.paContinue)
    
    async def send_audio(self, audio_data):
        """Send captured audio to backend"""
        try:
            if self.websocket:
                # Convert bytes to base64 or send raw
                await self.websocket.send(audio_data)
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
    
    async def receive_audio(self):
        """Receive audio responses from backend/HumeAI"""
        try:
            while self.is_running:
                message = await self.websocket.recv()
                
                # Check if binary audio data
                if isinstance(message, bytes):
                    # Add to playback queue
                    await self.playback_queue.put(message)
                    logger.debug(f"Received audio: {len(message)} bytes")
                else:
                    # JSON message (metadata)
                    data = json.loads(message)
                    logger.info(f"Received message: {data.get('type', 'unknown')}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error receiving audio: {e}")
    
    async def start_audio_streams(self):
        """Start PyAudio input and output streams"""
        
        # Find VB-Cable devices
        capture_device_idx = self.find_device_index(VB_CABLE_OUTPUT, input_device=True)
        playback_device_idx = self.find_device_index(VB_CABLE_INPUT, input_device=False)
        
        if capture_device_idx is None:
            logger.error(f"Could not find VB-Cable Output device for recording!")
            self.list_audio_devices()
            return False
        
        if playback_device_idx is None:
            logger.error(f"Could not find VB-Cable Input device for playback!")
            self.list_audio_devices()
            return False
        
        logger.info(f"Using capture device: {capture_device_idx}")
        logger.info(f"Using playback device: {playback_device_idx}")
        
        # Open input stream (capture from VB-Cable Output)
        self.input_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=capture_device_idx,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self.audio_callback_capture
        )
        
        # Open output stream (playback to VB-Cable Input)
        self.output_stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            output=True,
            output_device_index=playback_device_idx,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self.audio_callback_playback
        )
        
        logger.info("Audio streams started successfully")
        return True
    
    async def connect_backend(self):
        """Connect to backend WebSocket"""
        try:
            logger.info(f"Connecting to backend: {BACKEND_WS_URL}")
            self.websocket = await websockets.connect(BACKEND_WS_URL)
            logger.info("Connected to backend successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to backend: {e}")
            return False
    
    async def run(self):
        """Main run loop"""
        logger.info("=" * 60)
        logger.info("🎧 Audio Bridge Service Starting...")
        logger.info("=" * 60)
        
        # List available devices
        self.list_audio_devices()
        
        # Connect to backend
        if not await self.connect_backend():
            logger.error("Cannot start without backend connection")
            return
        
        # Start audio streams
        if not await self.start_audio_streams():
            logger.error("Cannot start without audio streams")
            return
        
        self.is_running = True
        
        # Start input stream
        self.input_stream.start_stream()
        self.output_stream.start_stream()
        
        logger.info("=" * 60)
        logger.info("✅ Audio Bridge Active!")
        logger.info("=" * 60)
        logger.info("📥 Capturing audio from: VB-Cable Output")
        logger.info("📤 Playing audio to: VB-Cable Input")
        logger.info("🔗 Connected to backend")
        logger.info("🤖 Ready for HumeAI calls!")
        logger.info("=" * 60)
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        try:
            # Receive audio responses
            await self.receive_audio()
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Clean shutdown"""
        logger.info("Stopping audio bridge...")
        
        self.is_running = False
        
        # Stop streams
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        
        # Close WebSocket
        if self.websocket:
            await self.websocket.close()
        
        # Terminate PyAudio
        self.audio.terminate()
        
        logger.info("Audio bridge stopped")


async def main():
    """Main entry point"""
    bridge = AudioBridge()
    await bridge.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
