"""
CallTools Browser with Audio Capture
Captures audio from browser during calls and streams to FastAPI WebSocket
"""
import asyncio
import json
import time
import uuid
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import websockets
import pyaudio
import base64
from threading import Thread

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
USERNAME = "Al.Hassan"
PASSWORD = "Roofing123"
PHONE_NUMBER = "2012529790"  # Change this to your actual phone number for testing

# FastAPI WebSocket URL
FASTAPI_WS_URL = "ws://localhost:8000/ws/audio-bridge"

# Audio configuration (16kHz mono PCM16 for HumeAI)
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1024  # 64ms chunks at 16kHz


def find_vb_cable_device():
    """Find VB-Cable virtual audio device"""
    audio = pyaudio.PyAudio()
    vb_input_idx = None
    vb_output_idx = None
    
    logger.info("🔍 Searching for VB-Cable devices...")
    
    for i in range(audio.get_device_count()):
        info = audio.get_device_info_by_index(i)
        name = info['name'].lower()
        
        # Find VB-Cable Output (for recording browser audio)
        if 'cable output' in name or 'vb-audio' in name:
            if info['maxInputChannels'] > 0:
                vb_input_idx = i
                logger.info(f"✅ Found VB-Cable Input: {info['name']} (index {i})")
        
        # Find VB-Cable Input (for playing AI audio to browser)
        if 'cable input' in name or 'vb-audio' in name:
            if info['maxOutputChannels'] > 0:
                vb_output_idx = i
                logger.info(f"✅ Found VB-Cable Output: {info['name']} (index {i})")
    
    audio.terminate()
    
    if vb_input_idx is None:
        logger.warning("⚠️ VB-Cable not found! Using default microphone.")
        logger.warning("📥 Install VB-Cable: https://vb-audio.com/Cable/")
    
    return vb_input_idx, vb_output_idx


class AudioCapture:
    """Captures microphone audio and sends to WebSocket"""
    
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        
    async def connect(self):
        """Connect to FastAPI WebSocket"""
        try:
            self.ws = await websockets.connect(self.ws_url)
            logger.info(f"✅ Connected to audio bridge: {self.ws_url}")
            
            # Wait for ready signal
            response = await self.ws.recv()
            data = json.loads(response)
            
            if data.get("type") == "ready":
                logger.info(f"✅ HumeAI Ready - Chat ID: {data.get('chat_id')}")
                return True
            else:
                logger.error(f"Unexpected response: {data}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to audio bridge: {e}")
            return False
    
    async def start_capture(self):
        """Start capturing audio from microphone"""
        try:
            # Find VB-Cable devices
            vb_input_idx, vb_output_idx = find_vb_cable_device()
            
            # Open audio INPUT stream (capture from VB-Cable Output)
            input_device = vb_input_idx if vb_input_idx is not None else None
            
            self.stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=input_device,
                frames_per_buffer=CHUNK
            )
            
            if vb_input_idx:
                logger.info("🎤 Audio capture started (VB-Cable)")
            else:
                logger.info("🎤 Audio capture started (Default Mic)")
            
            self.running = True
            
            # Store output device for playback
            self.vb_output_idx = vb_output_idx
            
            # Start playback handler
            asyncio.create_task(self._receive_audio())
            
            # Capture and send audio
            frames_sent = 0
            while self.running:
                try:
                    # Read audio chunk
                    audio_data = self.stream.read(CHUNK, exception_on_overflow=False)
                    
                    # Send to WebSocket
                    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                    await self.ws.send(json.dumps({
                        "type": "audio_input",
                        "data": audio_b64
                    }))
                    
                    frames_sent += 1
                    
                    # Log progress every 100 frames (~6 seconds)
                    if frames_sent % 100 == 0:
                        logger.info(f"📊 Audio frames sent: {frames_sent}")
                    
                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    logger.error(f"❌ Error capturing audio: {e}")
                    break
            
            logger.info(f"✅ Total audio frames sent: {frames_sent}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to start audio capture: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
    
    async def _receive_audio(self):
        """Receive and play audio from HumeAI"""
        try:
            # Open playback stream (output to VB-Cable Input)
            output_device = self.vb_output_idx if hasattr(self, 'vb_output_idx') and self.vb_output_idx is not None else None
            
            speaker = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True,
                output_device_index=output_device
            )
            
            if output_device:
                logger.info("🔊 Audio playback started (VB-Cable)")
            else:
                logger.info("🔊 Audio playback started (Default Speaker)")
            
            # Send initial message to trigger HumeAI
            await self.ws.send(json.dumps({
                "type": "session_start",
                "timestamp": time.time()
            }))
            logger.info("📡 Session start signal sent to HumeAI")
            
            while self.running:
                try:
                    # Receive message from WebSocket
                    message = await asyncio.wait_for(self.ws.recv(), timeout=0.1)
                    data = json.loads(message)
                    msg_type = data.get("type")
                    
                    if msg_type == "audio_output":
                        # Play AI audio
                        audio_b64 = data.get("data")
                        if audio_b64:
                            audio_bytes = base64.b64decode(audio_b64)
                            speaker.write(audio_bytes)
                            
                    elif msg_type == "transcript_user":
                        logger.info(f"👤 You: {data.get('text')}")
                        
                    elif msg_type == "transcript_ai":
                        logger.info(f"🤖 AI: {data.get('text')}")
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving audio: {e}")
                    break
            
            speaker.stop_stream()
            speaker.close()
            
        except Exception as e:
            logger.error(f"Playback error: {e}")
    
    def stop(self):
        """Stop audio capture"""
        self.running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            
        if self.audio:
            self.audio.terminate()
        
        logger.info("Audio capture stopped")


class CallToolsDialer:
    """CallTools browser automation with audio bridge"""
    
    def __init__(self):
        self.driver = None
        self.audio_capture = None
        self.session_id = str(uuid.uuid4())
        
    def setup_browser(self):
        """Setup Chrome with audio permissions"""
        options = webdriver.ChromeOptions()
        options.add_argument('--use-fake-ui-for-media-stream')  # Auto-accept mic/speaker
        options.add_argument('--use-fake-device-for-media-stream')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Allow microphone access
        prefs = {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.maximize_window()
        
        logger.info("✅ Browser setup complete")
    
    def login(self):
        """Login to CallTools"""
        try:
            logger.info(f"🌐 Opening CallTools: {CALLTOOLS_URL}")
            self.driver.get(CALLTOOLS_URL)
            
            wait = WebDriverWait(self.driver, 20)
            
            # Wait for page load
            time.sleep(3)
            
            # Try multiple selectors for username
            username_field = None
            username_selectors = [
                (By.NAME, "username"),
                (By.NAME, "user"),
                (By.ID, "username"),
                (By.CSS_SELECTOR, "input[placeholder*='Username']"),
                (By.CSS_SELECTOR, "input[placeholder*='User']"),
                (By.XPATH, "//input[@type='text' or @type='email']")
            ]
            
            for by, selector in username_selectors:
                try:
                    username_field = wait.until(EC.presence_of_element_located((by, selector)))
                    logger.info(f"Found username field with {by}: {selector}")
                    break
                except:
                    continue
            
            if not username_field:
                raise Exception("Could not find username field")
            
            username_field.clear()
            username_field.send_keys(USERNAME)
            time.sleep(0.5)
            
            # Try multiple selectors for password
            password_field = None
            password_selectors = [
                (By.NAME, "password"),
                (By.NAME, "pass"),
                (By.ID, "password"),
                (By.CSS_SELECTOR, "input[type='password']")
            ]
            
            for by, selector in password_selectors:
                try:
                    password_field = self.driver.find_element(by, selector)
                    logger.info(f"Found password field with {by}: {selector}")
                    break
                except:
                    continue
            
            if not password_field:
                raise Exception("Could not find password field")
            
            password_field.clear()
            password_field.send_keys(PASSWORD)
            time.sleep(0.5)
            
            # Try multiple selectors for login button
            login_button = None
            button_selectors = [
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.XPATH, "//button[contains(text(), 'Login')]"),
                (By.XPATH, "//button[contains(text(), 'Sign in')]"),
                (By.XPATH, "//input[@type='submit']"),
                (By.CSS_SELECTOR, "button.login-button"),
                (By.CSS_SELECTOR, "button.btn-primary")
            ]
            
            for by, selector in button_selectors:
                try:
                    login_button = self.driver.find_element(by, selector)
                    logger.info(f"Found login button with {by}: {selector}")
                    break
                except:
                    continue
            
            if login_button:
                login_button.click()
            else:
                # Try pressing Enter on password field
                logger.info("Trying Enter key on password field")
                from selenium.webdriver.common.keys import Keys
                password_field.send_keys(Keys.RETURN)
            
            time.sleep(2)
            
            # Wait for dashboard or any post-login page
            try:
                wait.until(lambda driver: "login" not in driver.current_url.lower())
                logger.info("✅ LOGIN SUCCESSFUL")
                
                # NOW JOIN CAMPAIGN AND SET STATUS
                time.sleep(3)
                
                # Join Campaign
                logger.info("📋 Joining campaign...")
                if self.join_campaign():
                    logger.info("✅ Campaign joined")
                else:
                    logger.warning("⚠️ Could not join campaign automatically")
                
                # Set Status to Available
                time.sleep(2)
                logger.info("📊 Setting status to Available...")
                if self.set_status_available():
                    logger.info("✅ Status set to Available")
                else:
                    logger.warning("⚠️ Could not set status automatically")
                
                return True
            except:
                # Check if we're already logged in
                if "dashboard" in self.driver.current_url.lower() or "login" not in self.driver.current_url.lower():
                    logger.info("✅ LOGIN SUCCESSFUL")
                    return True
                else:
                    raise Exception("Login page did not redirect")
            
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            # Take screenshot for debugging
            try:
                screenshot_path = f"login_error_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot saved: {screenshot_path}")
            except:
                pass
            return False
    
    def join_campaign(self):
        """Join Orange Roofing campaign"""
        try:
            # Look for "Join Campaign" button
            join_selectors = [
                "//button[contains(text(), 'Join Campaign')]",
                "//a[contains(text(), 'Join Campaign')]",
                "//button[contains(., 'Join')]"
            ]
            
            for selector in join_selectors:
                try:
                    join_btn = self.driver.find_element(By.XPATH, selector)
                    if join_btn.is_displayed():
                        join_btn.click()
                        logger.info("Clicked Join Campaign button")
                        time.sleep(2)
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error joining campaign: {e}")
            return False
    
    def set_status_available(self):
        """Set agent status to Available"""
        try:
            # Look for Status dropdown/button
            status_selectors = [
                "//button[contains(@class, 'status')]",
                "//div[contains(text(), 'Status')]",
                "//select[contains(@name, 'status')]",
                "//*[contains(text(), 'Status')]"
            ]
            
            for selector in status_selectors:
                try:
                    status_elem = self.driver.find_element(By.XPATH, selector)
                    if status_elem.is_displayed():
                        status_elem.click()
                        time.sleep(1)
                        
                        # Now select "Available"
                        available_selectors = [
                            "//option[contains(text(), 'Available')]",
                            "//li[contains(text(), 'Available')]",
                            "//button[contains(text(), 'Available')]",
                            "//*[text()='Available']"
                        ]
                        
                        for avail_sel in available_selectors:
                            try:
                                avail_elem = self.driver.find_element(By.XPATH, avail_sel)
                                avail_elem.click()
                                logger.info("Selected Available status")
                                return True
                            except:
                                continue
                        break
                except:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error setting status: {e}")
            return False
    
    def make_call(self):
        """Dial phone number"""
        try:
            wait = WebDriverWait(self.driver, 15)
            
            logger.info(f"Looking for dialer on CallTools...")
            time.sleep(2)  # Let page load completely
            
            # Try multiple approaches to find and use the dialer
            dialed = False
            
            # Approach 1: Direct input field
            dialer_selectors = [
                (By.CSS_SELECTOR, "input[placeholder*='phone']"),
                (By.CSS_SELECTOR, "input[placeholder*='Phone']"),
                (By.CSS_SELECTOR, "input[placeholder*='number']"),
                (By.CSS_SELECTOR, "input[placeholder*='Number']"),
                (By.CSS_SELECTOR, "input[type='tel']"),
                (By.CSS_SELECTOR, "input.phone-input"),
                (By.CSS_SELECTOR, "input.dialer-input"),
                (By.ID, "phone"),
                (By.ID, "phoneNumber"),
                (By.NAME, "phone"),
                (By.NAME, "phoneNumber")
            ]
            
            for by, selector in dialer_selectors:
                try:
                    dialer_input = self.driver.find_element(by, selector)
                    logger.info(f"Found dialer input with {by}: {selector}")
                    dialer_input.clear()
                    dialer_input.send_keys(PHONE_NUMBER)
                    time.sleep(0.5)
                    
                    # Find and click dial button
                    dial_selectors = [
                        (By.XPATH, "//button[contains(text(), 'Call')]"),
                        (By.XPATH, "//button[contains(text(), 'Dial')]"),
                        (By.CSS_SELECTOR, "button.call-button"),
                        (By.CSS_SELECTOR, "button.dial-button"),
                        (By.CSS_SELECTOR, "button[title*='Call']"),
                        (By.CSS_SELECTOR, "button[title*='Dial']"),
                        (By.XPATH, "//button[@type='button' and contains(@class, 'call')]")
                    ]
                    
                    for dial_by, dial_selector in dial_selectors:
                        try:
                            dial_button = self.driver.find_element(dial_by, dial_selector)
                            logger.info(f"Found dial button with {dial_by}: {dial_selector}")
                            dial_button.click()
                            dialed = True
                            break
                        except:
                            continue
                    
                    if dialed:
                        break
                        
                    # If no button found, try pressing Enter
                    if not dialed:
                        logger.info("Trying Enter key on phone input")
                        from selenium.webdriver.common.keys import Keys
                        dialer_input.send_keys(Keys.RETURN)
                        dialed = True
                        break
                        
                except Exception as e:
                    continue
            
            if not dialed:
                # Approach 2: Look for clickable phone number buttons (like a dialpad)
                logger.info("Looking for dialpad buttons...")
                for digit in PHONE_NUMBER:
                    try:
                        digit_button = self.driver.find_element(
                            By.XPATH, 
                            f"//button[text()='{digit}' or @data-digit='{digit}']"
                        )
                        digit_button.click()
                        time.sleep(0.1)
                    except:
                        pass
                
                # Click call button after entering digits
                try:
                    call_btn = self.driver.find_element(
                        By.XPATH,
                        "//button[contains(@class, 'call') or contains(text(), 'Call')]"
                    )
                    call_btn.click()
                    dialed = True
                except:
                    pass
            
            if not dialed:
                raise Exception("Could not find dialer interface")
            
            logger.info(f"📞 CALL INITIATED: {PHONE_NUMBER}")
            
            # Check for "outside legal hours" popup and click Call anyway
            time.sleep(2)
            try:
                # Look for the popup with "Would you still like to call?" text
                popup_call_button = None
                popup_selectors = [
                    "//button[text()='Call']",
                    "//button[contains(text(), 'Call')]",
                    "//button[@type='button' and contains(text(), 'Call')]"
                ]
                
                for selector in popup_selectors:
                    try:
                        popup_call_button = self.driver.find_element(By.XPATH, selector)
                        if popup_call_button.is_displayed():
                            logger.info("⚠️ Found 'outside legal hours' popup - clicking Call button")
                            popup_call_button.click()
                            break
                    except:
                        continue
            except Exception as e:
                logger.debug(f"No popup found (this is normal): {e}")
            
            # Wait for call to connect
            time.sleep(3)
            
            # Check for call connected indicators
            connected_indicators = [
                "//div[contains(text(), 'Connected')]",
                "//div[contains(text(), 'In Call')]",
                "//button[contains(text(), 'End Call')]",
                "//button[contains(text(), 'Hang Up')]"
            ]
            
            for indicator in connected_indicators:
                try:
                    self.driver.find_element(By.XPATH, indicator)
                    logger.info("✅ CALL CONNECTED")
                    return True
                except:
                    continue
            
            # If no indicator found, assume connected after delay
            logger.info("✅ CALL CONNECTED (assumed)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to make call: {e}")
            # Take screenshot for debugging
            try:
                screenshot_path = f"call_error_{int(time.time())}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"Screenshot saved: {screenshot_path}")
            except:
                pass
            return False
    
    async def run_with_audio(self):
        """Run CallTools with audio streaming"""
        try:
            # Setup browser
            self.setup_browser()
            
            # Login (includes campaign join and status set)
            if not self.login():
                return
            
            logger.info("🎧 Ready to receive calls!")
            logger.info("⏳ Waiting for incoming calls from campaign...")
            logger.info("💡 System will auto-answer and connect HumeAI")
            
            # Wait for incoming call
            time.sleep(5)
            
            # Check if call is active
            logger.info("🔍 Checking for active calls...")
            call_active = self.check_call_active()
            
            if not call_active:
                logger.warning("⚠️ No active call detected")
                logger.info("💡 Try manually dialing a number or wait for campaign call")
                
                # Give option to manual dial
                time.sleep(5)
                logger.info("📞 Attempting manual dial as fallback...")
                if not self.make_call():
                    logger.error("❌ No calls to handle")
                    return
                
                # Wait for answer
                logger.info("⏳ Waiting for call to be answered...")
                time.sleep(3)
                call_active = self.check_call_active()
                
                if not call_active:
                    logger.error("❌ Call was not answered")
                    return
            
            logger.info("✅ CALL ACTIVE - Starting audio bridge...")
            
            # Initialize audio capture AFTER call is active
            ws_url = f"{FASTAPI_WS_URL}/{self.session_id}"
            self.audio_capture = AudioCapture(ws_url)
            
            # Connect to audio bridge
            if not await self.audio_capture.connect():
                logger.error("Failed to connect to audio bridge")
                return
            
            # Start audio streaming
            logger.info("🎵 Starting audio streaming...")
            await self.audio_capture.start_capture()
            
        except KeyboardInterrupt:
            logger.info("\n⚠️ Interrupted by user")
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            self.cleanup()
    
    def check_call_active(self, wait_time=15, check_interval=2):
        """
        Check if call is actually active/answered
        
        Args:
            wait_time: Maximum time to wait for call answer (seconds)
            check_interval: How often to check (seconds)
        """
        try:
            logger.info(f"⏳ Checking call status (max wait: {wait_time}s)...")
            
            start_time = time.time()
            checks_done = 0
            
            while (time.time() - start_time) < wait_time:
                checks_done += 1
                logger.info(f"🔍 Check #{checks_done}...")
                
                # Look for RINGING indicators first
                ringing_indicators = [
                    "//div[contains(text(), 'Ringing')]",
                    "//div[contains(text(), 'Calling')]",
                    "//span[contains(text(), 'Ringing')]",
                    "//span[contains(@class, 'ringing')]"
                ]
                
                is_ringing = False
                for indicator in ringing_indicators:
                    try:
                        element = self.driver.find_element(By.XPATH, indicator)
                        if element.is_displayed():
                            logger.info(f"📞 Call is ringing... waiting for answer")
                            is_ringing = True
                            break
                    except:
                        continue
                
                # Look for ANSWERED/CONNECTED indicators (case-insensitive)
                active_indicators = [
                    "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'on a call')]",  # Case-insensitive
                    "//*[text()='On a Call']",  # Exact match
                    "//div[contains(text(), 'On a Call')]",  # CallTools specific
                    "//span[contains(text(), 'On a Call')]",
                    "//p[contains(text(), 'On a Call')]",
                    "//*[contains(text(), 'Connected')]",
                    "//*[contains(text(), 'In Call')]",
                    "//button[contains(text(), 'Mute')]",  # Mute button means call is active
                    "//button[contains(text(), 'Hold')]",  # CallTools has Hold button
                    "//button[contains(text(), 'Transfer')]",  # CallTools has Transfer button
                    "//*[text()='call_end']",  # Material icon exact text
                    "//button[contains(., 'call_end')]",  # Button containing call_end icon
                ]
                
                for indicator in active_indicators:
                    try:
                        element = self.driver.find_element(By.XPATH, indicator)
                        if element.is_displayed():
                            logger.info(f"✅ Call ANSWERED - Found: {indicator}")
                            return True
                    except:
                        continue
                
                # Check for call duration timer
                try:
                    timer_selectors = [
                        "//div[contains(@class, 'timer')]",
                        "//div[contains(@class, 'duration')]",
                        "//span[contains(@class, 'call-time')]",
                        "//div[contains(text(), ':') and string-length(text()) < 10]"  # Looks for time format
                    ]
                    for selector in timer_selectors:
                        timer = self.driver.find_element(By.XPATH, selector)
                        if timer.is_displayed():
                            timer_text = timer.text.strip()
                            if ':' in timer_text:  # Looks like a timer (00:05, etc)
                                logger.info(f"✅ Call ANSWERED - Timer found: {timer_text}")
                                return True
                except:
                    pass
                
                # Check for FAILED/REJECTED indicators
                failed_indicators = [
                    "//div[contains(text(), 'Failed')]",
                    "//div[contains(text(), 'Rejected')]",
                    "//div[contains(text(), 'Busy')]",
                    "//div[contains(text(), 'No Answer')]",
                    "//div[contains(text(), 'Unavailable')]"
                ]
                
                for indicator in failed_indicators:
                    try:
                        element = self.driver.find_element(By.XPATH, indicator)
                        if element.is_displayed():
                            logger.error(f"❌ Call FAILED - Found: {indicator}")
                            return False
                    except:
                        continue
                
                # If ringing, wait and continue
                if is_ringing:
                    logger.info(f"⏳ Still ringing... ({int(time.time() - start_time)}s elapsed)")
                    time.sleep(check_interval)
                    continue
                
                # No clear indicator, wait a bit
                logger.info(f"⏳ No clear status yet... ({int(time.time() - start_time)}s elapsed)")
                time.sleep(check_interval)
            
            # Timeout reached
            logger.warning(f"⚠️ Could not confirm call answer after {wait_time}s")
            screenshot_path = f"call_timeout_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Get all visible text on page for debugging
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                logger.info(f"📄 Page content:\n{body_text[:500]}...")  # First 500 chars
            except:
                pass
            
            return False  # Don't assume - actually fail if can't confirm
            
        except Exception as e:
            logger.error(f"Error checking call status: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up...")
        
        if self.audio_capture:
            self.audio_capture.stop()
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        logger.info("✅ Cleanup complete")


async def main():
    """Main entry point"""
    logger.info("""
╔══════════════════════════════════════════════════════════╗
║  CallTools + HumeAI Audio Bridge                         ║
║  Real-time voice AI integration                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    dialer = CallToolsDialer()
    await dialer.run_with_audio()


if __name__ == "__main__":
    asyncio.run(main())
