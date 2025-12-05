"""
STEP 1: Start this audio bridge
STEP 2: Run auto_dialer_complete.py to make call
STEP 3: AI will automatically talk to customer

This bridge runs independently and waits for CallTools call
"""

import asyncio
import websockets
import json
import os
import pyaudio
import base64
from dotenv import load_dotenv
import wave

load_dotenv()

HUME_API_KEY = os.getenv("HUME_API_KEY")
HUME_CONFIG_ID = os.getenv("HUME_CONFIG_ID")

# Simple audio settings
CHUNK = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 2  # Stereo
RATE = 16000  # VB-Cable default

print("╔══════════════════════════════════════════════════════════╗")
print("║  Simple HumeAI Bridge (No VB-Cable conflicts)           ║")
print("╚══════════════════════════════════════════════════════════╝")
print()
print("📋 Setup Instructions:")
print("   1. Start this bridge (it will wait for connection)")
print("   2. Run auto_dialer_complete.py in another terminal")
print("   3. Make call - AI will connect automatically")
print()

async def run_hume_session():
    """Simple HumeAI session - just connect and log"""
    
    url = "wss://api.hume.ai/v0/assistant/chat"
    headers = {"X-Hume-Api-Key": HUME_API_KEY}
    
    print("🔗 Connecting to HumeAI...")
    
    async with websockets.connect(url, extra_headers=headers) as ws:
        # Init session
        init_msg = {
            "type": "session_settings",
            "config_id": HUME_CONFIG_ID
        }
        
        await ws.send(json.dumps(init_msg))
        response = await ws.recv()
        data = json.loads(response)
        
        if data.get('type') == 'chat_metadata':
            chat_id = data.get('chat_id')
            print(f"✅ HumeAI Connected!")
            print(f"   Chat ID: {chat_id}")
            print()
            print("=" * 60)
            print("🎙️  Waiting for call...")
            print("=" * 60)
            print()
            print("Now run: python auto_dialer_complete.py")
            print()
            
            # Just listen for messages
            while True:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=1)
                    data = json.loads(response)
                    
                    msg_type = data.get('type')
                    
                    if msg_type == 'user_message':
                        text = data.get('message', {}).get('content', '')
                        print(f"\n👤 CUSTOMER: {text}")
                    
                    elif msg_type == 'assistant_message':
                        text = data.get('message', {}).get('content', '')
                        print(f"\n🤖 AI: {text}")
                
                except asyncio.TimeoutError:
                    continue
                except KeyboardInterrupt:
                    break

async def main():
    try:
        await run_hume_session()
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
