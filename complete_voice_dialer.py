"""
Complete Integrated Auto Dialer with HumeAI Audio
- Selenium automation for CallTools
- PyAudio for microphone/speaker
- HumeAI WebSocket for AI conversation
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import asyncio
import websockets
import json
import base64
import os
import time
import pyaudio
from dotenv import load_dotenv

load_dotenv()

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
CALLTOOLS_USER = "Al.Hassan"
CALLTOOLS_PASS = "Roofing123"
TARGET_PHONE = "2012529790"

HUME_API_KEY = os.getenv("HUME_API_KEY")
HUME_CONFIG_ID = os.getenv("HUME_CONFIG_ID")

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

print("╔══════════════════════════════════════════════════════════╗")
print("║  CallTools Auto Dialer + HumeAI Voice Agent            ║")
print("╚══════════════════════════════════════════════════════════╝")
print()

# Global variables for audio and call state
audio_interface = None
input_stream = None
output_stream = None
call_active = False
ws_connection = None

def setup_browser():
    """Setup Chrome browser"""
    chrome_options = Options()
    chrome_options.add_argument("--use-fake-ui-for-media-stream")  # Auto-allow microphone
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    return driver

def login(driver, wait):
    """Login to CallTools"""
    print("[1] Logging in...")
    driver.get(CALLTOOLS_URL)
    time.sleep(3)
    
    username = wait.until(EC.presence_of_element_located((By.NAME, "user")))
    password = driver.find_element(By.NAME, "pass")
    
    username.send_keys(CALLTOOLS_USER)
    password.send_keys(CALLTOOLS_PASS)
    
    login_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
    login_btn.click()
    
    time.sleep(5)
    print("  ✅ Logged in")

def dial_number(driver, wait):
    """Dial the target number"""
    print(f"\n[2] Dialing {TARGET_PHONE}...")
    time.sleep(2)
    
    # Find phone input
    inputs = driver.find_elements(By.XPATH, "//input[@type='text' and not(@disabled)]")
    for inp in inputs:
        if inp.is_displayed():
            inp.clear()
            inp.send_keys(TARGET_PHONE)
            print(f"  ✓ Entered number")
            time.sleep(1)
            
            # Press Enter to dial
            from selenium.webdriver.common.keys import Keys
            inp.send_keys(Keys.ENTER)
            print(f"  ✅ Call initiated")
            break
    
    time.sleep(5)  # Wait for call to connect

async def run_hume_audio():
    """Run HumeAI audio conversation"""
    global audio_interface, input_stream, output_stream, call_active, ws_connection
    
    print("\n[3] Starting HumeAI Audio Agent...")
    
    # Initialize PyAudio
    audio_interface = pyaudio.PyAudio()
    
    # Open microphone input stream
    input_stream = audio_interface.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    
    # Open speaker output stream
    output_stream = audio_interface.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        output=True,
        frames_per_buffer=CHUNK
    )
    
    print("  ✓ Audio streams ready")
    
    # Connect to HumeAI
    url = "wss://api.hume.ai/v0/assistant/chat"
    headers = {"X-Hume-Api-Key": HUME_API_KEY}
    
    async with websockets.connect(url, extra_headers=headers) as ws:
        ws_connection = ws
        print("  ✓ Connected to HumeAI")
        
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
        
        # Wait for chat metadata
        response = await ws.recv()
        response_data = json.loads(response)
        
        if response_data.get('type') == 'chat_metadata':
            chat_id = response_data.get('chat_id')
            print(f"  ✅ HumeAI Agent Active! (Chat ID: {chat_id})")
            print()
            print("=" * 60)
            print("🎙️  CALL IN PROGRESS - AI Agent is talking to customer")
            print("=" * 60)
            print()
            
            call_active = True
            
            # Send audio from microphone to HumeAI
            async def send_audio():
                chunk_count = 0
                while call_active:
                    try:
                        # Read from microphone
                        audio_data = input_stream.read(CHUNK, exception_on_overflow=False)
                        
                        # Encode and send to HumeAI
                        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                        audio_msg = {
                            "type": "audio_input",
                            "data": audio_b64
                        }
                        
                        await ws.send(json.dumps(audio_msg))
                        chunk_count += 1
                        
                        if chunk_count % 100 == 0:
                            print(f"  📡 Streaming... ({chunk_count} chunks)", end='\r')
                        
                        await asyncio.sleep(0.01)
                    except Exception as e:
                        if call_active:
                            print(f"\n  ⚠️  Audio send error: {e}")
                        break
            
            # Receive audio from HumeAI and play to speaker
            async def receive_audio():
                while call_active:
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        response_data = json.loads(response)
                        
                        msg_type = response_data.get('type')
                        
                        if msg_type == 'user_message':
                            # Customer spoke
                            text = response_data.get('message', {}).get('content', '')
                            if text:
                                print(f"\n👤 CUSTOMER: {text}")
                        
                        elif msg_type == 'assistant_message':
                            # AI responded
                            text = response_data.get('message', {}).get('content', '')
                            if text:
                                print(f"\n🤖 AI AGENT: {text}")
                        
                        elif msg_type == 'audio_output':
                            # AI speaking - play audio
                            audio_b64 = response_data.get('data', '')
                            if audio_b64:
                                try:
                                    audio_bytes = base64.b64decode(audio_b64)
                                    output_stream.write(audio_bytes)
                                except:
                                    pass
                        
                        elif msg_type == 'user_interruption':
                            print("  ⚠️  Customer interrupted")
                        
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        if call_active:
                            print(f"\n  ⚠️  Receive error: {e}")
                        break
            
            # Run both audio streams
            try:
                await asyncio.gather(
                    send_audio(),
                    receive_audio()
                )
            except KeyboardInterrupt:
                print("\n\n⏹️  Call ended by user")
            except Exception as e:
                print(f"\n❌ Audio error: {e}")

def cleanup_audio():
    """Cleanup audio resources"""
    global input_stream, output_stream, audio_interface, call_active
    
    call_active = False
    
    if input_stream:
        input_stream.stop_stream()
        input_stream.close()
    
    if output_stream:
        output_stream.stop_stream()
        output_stream.close()
    
    if audio_interface:
        audio_interface.terminate()

def main():
    driver = None
    
    try:
        # Setup browser
        driver = setup_browser()
        wait = WebDriverWait(driver, 20)
        
        # Login
        login(driver, wait)
        
        # Dial number
        dial_number(driver, wait)
        
        # Run HumeAI audio conversation
        print("\n⏳ Starting AI conversation in 3 seconds...")
        time.sleep(3)
        
        asyncio.run(run_hume_audio())
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_audio()
        
        if driver:
            print("\n📸 Taking final screenshot...")
            driver.save_screenshot("final_call_state.png")
            
            print("Closing browser in 5 seconds...")
            time.sleep(5)
            driver.quit()
        
        print("\n✅ Complete")

if __name__ == "__main__":
    main()
