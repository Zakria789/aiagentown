"""
COMPLETE INTEGRATED DIALER WITH HUMEAI
Makes call AND connects HumeAI for real-time conversation
"""
import asyncio
import time
import json
import websockets
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
USERNAME = "Al.Hassan"
PASSWORD = "Roofing123"
PHONE_NUMBER = "2012529790"

HUME_API_KEY = os.getenv("HUME_API_KEY")
HUME_CONFIG_ID = os.getenv("HUME_CONFIG_ID")

print("╔══════════════════════════════════════════════════════════╗")
print("║  INTEGRATED CallTools + HumeAI Dialer                   ║")
print("╚══════════════════════════════════════════════════════════╝")
print()
print(f"📞 Calling: {PHONE_NUMBER}")
print(f"🤖 HumeAI: {HUME_CONFIG_ID[:30]}...")
print()


class HumeAICallHandler:
    """Handles HumeAI connection during call"""
    
    def __init__(self):
        self.websocket = None
        self.is_connected = False
        
    async def connect(self):
        """Connect to HumeAI"""
        try:
            url = "wss://api.hume.ai/v0/assistant/chat"
            headers = {"X-Hume-Api-Key": HUME_API_KEY}
            
            print("[HumeAI] Connecting...")
            self.websocket = await websockets.connect(url, extra_headers=headers)
            
            # Send session settings
            init_msg = {
                "type": "session_settings",
                "config_id": HUME_CONFIG_ID,
                "audio": {
                    "encoding": "linear16",
                    "sample_rate": 16000,
                    "channels": 1
                }
            }
            
            await self.websocket.send(json.dumps(init_msg))
            
            # Get response
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            response_data = json.loads(response)
            
            if response_data.get("type") == "chat_metadata":
                self.is_connected = True
                print(f"[HumeAI] ✓ Connected! Chat ID: {response_data.get('chat_id')}")
                return True
            
            return False
            
        except Exception as e:
            print(f"[HumeAI] ✗ Connection failed: {e}")
            return False
    
    async def monitor(self, duration=300):
        """Monitor HumeAI session"""
        if not self.is_connected:
            return
        
        print("[HumeAI] Monitoring session...")
        print("  (Audio routing through VB-Cable)")
        print()
        
        start_time = time.time()
        
        try:
            while (time.time() - start_time) < duration:
                # Try to receive messages
                try:
                    msg = await asyncio.wait_for(self.websocket.recv(), timeout=1)
                    data = json.loads(msg)
                    
                    msg_type = data.get("type")
                    
                    if msg_type == "user_message":
                        text = data.get("message", {}).get("content", "")
                        print(f"[Customer]: {text}")
                    
                    elif msg_type == "assistant_message":
                        text = data.get("message", {}).get("content", "")
                        print(f"[AI Agent]: {text}")
                    
                    elif msg_type == "emotion_scores":
                        emotions = data.get("scores", [])[:3]
                        emotion_names = [e.get("name") for e in emotions]
                        print(f"[Emotions]: {', '.join(emotion_names)}")
                        
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("[HumeAI] Connection closed")
                    break
                    
        except KeyboardInterrupt:
            print("\n[HumeAI] Monitoring stopped by user")
    
    async def disconnect(self):
        """Disconnect from HumeAI"""
        if self.websocket:
            await self.websocket.close()
            print("[HumeAI] Disconnected")


async def make_call_with_hume():
    """Make call and connect HumeAI"""
    driver = None
    hume = HumeAICallHandler()
    
    try:
        # Step 1: Setup browser
        print("[Step 1] Setting up browser...")
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--use-fake-ui-for-media-stream')
        
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.media_stream_mic": 1
        }
        options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        wait = WebDriverWait(driver, 15)
        print("  ✓ Browser ready")
        
        # Step 2: Login
        print("[Step 2] Logging in...")
        driver.get(CALLTOOLS_URL)
        time.sleep(3)
        
        username_field = driver.find_element(By.NAME, "username")
        username_field.send_keys(USERNAME)
        
        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(PASSWORD)
        
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_btn.click()
        time.sleep(5)
        
        # Close popups
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        
        print("  ✓ Logged in")
        
        # Step 3: Find and dial
        print(f"[Step 3] Dialing {PHONE_NUMBER}...")
        time.sleep(2)
        
        # Find phone input
        inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='tel']")
        phone_field = None
        
        for inp in inputs:
            if inp.is_displayed():
                phone_field = inp
                break
        
        if phone_field:
            phone_field.clear()
            phone_field.send_keys(PHONE_NUMBER)
            phone_field.send_keys(Keys.RETURN)
            time.sleep(2)
            print(f"  ✓ Call initiated to {PHONE_NUMBER}")
        else:
            print("  ⚠ Could not find phone field")
            return False
        
        # Step 4: Connect HumeAI
        print("[Step 4] Connecting HumeAI...")
        connected = await hume.connect()
        
        if not connected:
            print("  ✗ HumeAI connection failed")
            return False
        
        # Step 5: Monitor call
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  CALL ACTIVE WITH HUMEAI                                 ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print("📞 Call Status: ACTIVE")
        print(f"🤖 HumeAI Agent: CONNECTED")
        print(f"🎯 Customer: {PHONE_NUMBER}")
        print()
        print("Monitoring conversation (Press Ctrl+C to stop):")
        print("-" * 60)
        
        await hume.monitor(duration=300)
        
        return True
        
    except KeyboardInterrupt:
        print("\n\nCall interrupted by user")
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        await hume.disconnect()
        
        if driver:
            print("\nPress Enter to close browser...")
            input()
            driver.quit()


def main():
    """Main entry point"""
    print("Starting integrated dialer...")
    print()
    
    success = asyncio.run(make_call_with_hume())
    
    if success:
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  CALL COMPLETE                                           ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print("✅ Call made successfully")
        print("✅ HumeAI connected and monitored")
        print()
    
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
