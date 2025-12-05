"""
COMPLETE VB-Cable + HumeAI Integration
Uses VB-Cable to capture CallTools audio and route to HumeAI

How it works:
1. CallTools plays on VB-Cable Input
2. Python captures from VB-Cable Output
3. Python sends to HumeAI
4. HumeAI response plays on VB-Cable Input (back to CallTools)
"""

import asyncio
import websockets
import json
import os
import pyaudio
import base64
from dotenv import load_dotenv

load_dotenv()

HUME_API_KEY = os.getenv("HUME_API_KEY")
HUME_CONFIG_ID = os.getenv("HUME_CONFIG_ID")

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

print("╔══════════════════════════════════════════════════════════╗")
print("║  VB-Cable + HumeAI Voice Bridge                         ║")
print("╚══════════════════════════════════════════════════════════╝")
print()

class HumeAIAudioBridge:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.ws = None
        self.running = False
        
        # Find VB-Cable devices
        self.input_device = None
        self.output_device = None
        
        print("🔍 Scanning audio devices...")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            name = info['name']
            
            # VB-Cable Output = Where we capture FROM (CallTools audio)
            if 'CABLE Output' in name and info['maxInputChannels'] > 0:
                self.input_device = i
                print(f"  ✓ Found VB-Cable Output (Capture): Device {i} - {name}")
            
            # VB-Cable Input = Where we play TO (send HumeAI audio)
            if 'CABLE Input' in name and info['maxOutputChannels'] > 0:
                self.output_device = i
                print(f"  ✓ Found VB-Cable Input (Playback): Device {i} - {name}")
        
        if self.input_device is None or self.output_device is None:
            print("\n❌ ERROR: VB-Cable not found!")
            print("   Install VB-Cable from: https://vb-audio.com/Cable/")
            exit(1)
        
        print()
    
    async def start(self):
        """Start the audio bridge"""
        print("🚀 Starting HumeAI Audio Bridge...")
        print()
        
        # Get device info for proper setup
        input_info = self.audio.get_device_info_by_index(self.input_device)
        output_info = self.audio.get_device_info_by_index(self.output_device)
        
        # Use device's default sample rate if available
        input_rate = int(input_info.get('defaultSampleRate', RATE))
        output_rate = int(output_info.get('defaultSampleRate', RATE))
        
        print(f"  Input device: {input_info['name']}")
        print(f"  Input rate: {input_rate} Hz")
        print(f"  Output device: {output_info['name']}")
        print(f"  Output rate: {output_rate} Hz")
        print()
        
        # Open input stream (capture from VB-Cable Output)
        try:
            input_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=self.input_device,
                frames_per_buffer=CHUNK,
                stream_callback=None
            )
            print("  ✓ Input stream opened (capturing CallTools audio)")
        except Exception as e:
            print(f"  ❌ Failed to open input stream: {e}")
            print(f"     Trying with device's default rate: {input_rate}")
            input_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=input_rate,
                input=True,
                input_device_index=self.input_device,
                frames_per_buffer=CHUNK
            )
            print("  ✓ Input stream opened")
        
        # Open output stream (play to VB-Cable Input)
        try:
            output_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                output_device_index=self.output_device,
                frames_per_buffer=CHUNK,
                stream_callback=None
            )
            print("  ✓ Output stream opened (playing HumeAI audio)")
        except Exception as e:
            print(f"  ❌ Failed to open output stream: {e}")
            print(f"     Trying with device's default rate: {output_rate}")
            output_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=output_rate,
                output=True,
                output_device_index=self.output_device,
                frames_per_buffer=CHUNK
            )
            print("  ✓ Output stream opened")
        
        # Connect to HumeAI
        url = "wss://api.hume.ai/v0/assistant/chat"
        headers = {"X-Hume-Api-Key": HUME_API_KEY}
        
        print(f"  ✓ Connecting to HumeAI...")
        
        async with websockets.connect(url, extra_headers=headers) as ws:
            self.ws = ws
            print("  ✓ Connected to HumeAI WebSocket")
            
            # Send session settings
            init_msg = {
                "type": "session_settings",
                "config_id": HUME_CONFIG_ID,
                "audio": {
                    "encoding": "linear16",
                    "sample_rate": RATE,
                    "channels": CHANNELS
                }
            }
            
            await ws.send(json.dumps(init_msg))
            
            # Wait for response
            response = await ws.recv()
            data = json.loads(response)
            
            if data.get('type') == 'chat_metadata':
                chat_id = data.get('chat_id')
                print(f"  ✅ HumeAI Agent Active!")
                print(f"     Chat ID: {chat_id}")
                print()
                print("=" * 60)
                print("🎙️  LIVE - Bridge is running")
                print("=" * 60)
                print()
                print("📋 Instructions:")
                print("   1. Make a call in CallTools")
                print("   2. Set CallTools audio output to: VB-Cable Input")
                print("   3. AI will automatically talk to customer")
                print()
                print("Press Ctrl+C to stop")
                print()
                
                self.running = True
                
                # Task 1: Capture audio from CallTools and send to HumeAI
                async def capture_and_send():
                    chunk_count = 0
                    while self.running:
                        try:
                            # Read audio from VB-Cable (CallTools/Customer audio)
                            audio_data = input_stream.read(CHUNK, exception_on_overflow=False)
                            
                            # Send to HumeAI
                            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                            msg = {
                                "type": "audio_input",
                                "data": audio_b64
                            }
                            
                            await ws.send(json.dumps(msg))
                            chunk_count += 1
                            
                            if chunk_count % 100 == 0:
                                print(f"  📡 Streaming: {chunk_count} chunks", end='\r')
                            
                            await asyncio.sleep(0.001)
                            
                        except Exception as e:
                            if self.running:
                                print(f"\n  ⚠️  Capture error: {e}")
                            break
                
                # Task 2: Receive HumeAI audio and play to CallTools
                async def receive_and_play():
                    while self.running:
                        try:
                            response = await asyncio.wait_for(ws.recv(), timeout=0.1)
                            data = json.loads(response)
                            
                            msg_type = data.get('type')
                            
                            if msg_type == 'user_message':
                                text = data.get('message', {}).get('content', '')
                                if text:
                                    print(f"\n👤 CUSTOMER: {text}")
                            
                            elif msg_type == 'assistant_message':
                                text = data.get('message', {}).get('content', '')
                                if text:
                                    print(f"\n🤖 AI AGENT: {text}")
                            
                            elif msg_type == 'audio_output':
                                # AI speaking - play to VB-Cable
                                audio_b64 = data.get('data', '')
                                if audio_b64:
                                    try:
                                        audio_bytes = base64.b64decode(audio_b64)
                                        output_stream.write(audio_bytes)
                                    except:
                                        pass
                            
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            if self.running:
                                print(f"\n  ⚠️  Receive error: {e}")
                            break
                
                # Run both tasks
                try:
                    await asyncio.gather(
                        capture_and_send(),
                        receive_and_play()
                    )
                except KeyboardInterrupt:
                    print("\n\n⏹️  Stopping bridge...")
                    self.running = False
        
        # Cleanup
        input_stream.stop_stream()
        input_stream.close()
        output_stream.stop_stream()
        output_stream.close()
        
        print("\n✅ Bridge stopped")
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        self.audio.terminate()

async def main():
    bridge = HumeAIAudioBridge()
    
    try:
        await bridge.start()
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        bridge.cleanup()
        print("\n✅ Complete")

if __name__ == "__main__":
    asyncio.run(main())
