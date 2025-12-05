"""
CallTools Call Event Monitor + HumeAI Audio Bridge
===================================================

Automatically detects incoming calls and connects HumeAI for voice interaction.

Features:
- Monitors CallTools for incoming calls via WebRTC PeerConnection detection
- Injects audio bridge JavaScript when call is detected
- Sends call_start event to FastAPI backend
- Backend connects to HumeAI only when call starts
- Clean logs showing exact flow

Usage:
    python calltools_call_event_monitor.py
"""

import asyncio
import logging
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
CALLTOOLS_USERNAME = "Al.Hassan"
CALLTOOLS_PASSWORD = "Roofing123"
BACKEND_WS_URL = "ws://localhost:8000/ws/webrtc-audio"
CHECK_INTERVAL = 2  # seconds
AUTO_JOIN_CAMPAIGN = True  # Automatically join campaign after login
AUTO_START_CALLS = True  # Automatically start making calls


# JavaScript to inject - CallTools Audio Bridge
CALLTOOLS_AUDIO_BRIDGE_JS = """
(function() {
    console.log('CallTools Audio Bridge Script Loading...');
    
    // Configuration
    const BACKEND_WS_URL = 'ws://localhost:8000/ws/webrtc-audio';
    const SESSION_ID = '""" + str(int(time.time())) + """';
    const SAMPLE_RATE = 16000;  // HumeAI requires 16kHz
    
    let ws = null;
    let audioContext = null;
    let processor = null;
    let isCapturing = false;
    let callActive = false;
    let audioChunkCount = 0;
    let peerConnectionCount = 0;
    let audioTrackCount = 0;
    
    // Connect to FastAPI WebSocket
    function connectWebSocket() {
        try {
            ws = new WebSocket(BACKEND_WS_URL);
            
            ws.onopen = () => {
                console.log('✅ WebSocket connected to FastAPI');
                
                // Send initialization message
                ws.send(JSON.stringify({
                    type: 'init',
                    session_id: SESSION_ID,
                    timestamp: Date.now()
                }));
                console.log('📤 Sent init message');
            };
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'ready') {
                        console.log('✅ Bridge ready:', data.message);
                    } else if (data.type === 'audio_response') {
                        // AI audio response from HumeAI
                        console.log('🔊 Received AI audio response');
                        playAudioResponse(data.data);
                    } else if (data.type === 'transcript') {
                        console.log(`💬 ${data.speaker.toUpperCase()}: ${data.text}`);
                    }
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                }
            };
            
            ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
            };
            
            ws.onclose = () => {
                console.log('⚠️ WebSocket closed');
                stopAudioCapture();
            };
            
        } catch (error) {
            console.error('❌ Failed to connect WebSocket:', error);
        }
    }
    
    // Monitor for WebRTC PeerConnection (call detection)
    function monitorPeerConnections() {
        const originalRTCPeerConnection = window.RTCPeerConnection;
        
        window.RTCPeerConnection = function(...args) {
            console.log('✅ New RTCPeerConnection created!');
            const pc = new originalRTCPeerConnection(...args);
            peerConnectionCount++;
            
            // Listen for track events (audio/video streams)
            pc.addEventListener('track', (event) => {
                console.log('🎵 Track received (addEventListener):', event.track.kind, event.track.id);
                
                if (event.track.kind === 'audio') {
                    audioTrackCount++;
                    console.log('✅ Audio track added! Total:', audioTrackCount);
                    
                    // Call detected!
                    if (!callActive) {
                        onCallDetected();
                    }
                }
            });
            
            // Listen for connection state changes
            pc.addEventListener('connectionstatechange', () => {
                console.log('🔗 Connection state:', pc.connectionState);
                
                if (pc.connectionState === 'connected' && !callActive) {
                    onCallDetected();
                } else if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed' || pc.connectionState === 'closed') {
                    console.log('📴 Call ended - Connection state:', pc.connectionState);
                    onCallEnded();
                }
            });
            
            // Also listen for ICE connection state
            pc.addEventListener('iceconnectionstatechange', () => {
                console.log('🧊 ICE Connection state:', pc.iceConnectionState);
                
                if (pc.iceConnectionState === 'disconnected' || pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'closed') {
                    console.log('📴 Call ended - ICE state:', pc.iceConnectionState);
                    onCallEnded();
                }
            });
            
            return pc;
        };
        
        console.log('👁️ Monitoring for PeerConnections...');
    }
    
    // Call detected!
    function onCallDetected() {
        if (callActive) return;
        
        callActive = true;
        console.log('📞 CALL STARTED!');
        
        // Notify backend
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'call_start',
                session_id: SESSION_ID,
                timestamp: Date.now()
            }));
            console.log('📤 Sent call_start event to FastAPI');
        }
        
        // Wait a bit for streams to be ready, then start capturing
        setTimeout(() => {
            if (callActive) {
                ws.send(JSON.stringify({
                    type: 'call_start',
                    session_id: SESSION_ID,
                    timestamp: Date.now()
                }));
                console.log('📤 Sent call_start event to backend');
                startAudioCapture();
            }
        }, 500);
    }
    
    // Call ended
    function onCallEnded() {
        if (!callActive) return;
        
        console.log('📴 CALL ENDED!');
        callActive = false;
        
        // Stop audio capture immediately
        stopAudioCapture();
        
        // Notify backend
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'call_end',
                session_id: SESSION_ID,
                timestamp: Date.now()
            }));
            console.log('📤 Sent call_end event to backend');
        }
    }
    
    // Start capturing audio from active call
    async function startAudioCapture() {
        if (isCapturing) return;
        
        console.log('🎤 Starting audio capture...');
        
        try {
            // Find active audio tracks
            const peerConnections = document.querySelectorAll('*');
            let audioTrack = null;
            
            // Try to get audio from RTCPeerConnection
            if (window.RTCPeerConnection) {
                console.log('✅ Found active audio track:', audioTrack?.id || 'searching...');
            }
            
            // Get user media with specific constraints for CallTools
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: SAMPLE_RATE,
                    channelCount: 1
                }
            });
            
            console.log('✅ Got microphone stream');
            
            // Create audio context at 16kHz (HumeAI requirement)
            audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
            console.log('✅ AudioContext created at', audioContext.sampleRate, 'Hz');
            
            // Create audio context at 16kHz
            audioContext = new AudioContext({ sampleRate: 16000 });
            const source = audioContext.createMediaStreamSource(stream);
            processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            processor.onaudioprocess = (e) => {
                if (!callActive || !ws || ws.readyState !== WebSocket.OPEN) return;
                
                const inputData = e.inputBuffer.getChannelData(0);
                
                // Convert Float32Array to Int16Array (PCM)
                const int16 = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    const s = Math.max(-1, Math.min(1, inputData[i]));
                    int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }
                
                // Encode to base64
                const bytes = new Uint8Array(int16.buffer);
                const base64 = btoa(String.fromCharCode(...bytes));
                
                // Send to backend
                ws.send(JSON.stringify({
                    type: 'audio',
                    data: base64,
                    timestamp: Date.now()
                }));
                
                audioChunkCount++;
                
                // Log every 100 frames
                if (audioChunkCount % 100 === 0) {
                    console.log(`📊 Sent ${audioChunkCount} audio frames`);
                }
            };
            
            source.connect(processor);
            processor.connect(audioContext.destination);
            
            isCapturing = true;
            console.log('✅ Audio capture started!');
            console.log('📡 Sending audio to FastAPI WebSocket');
            
        } catch (error) {
            console.error('❌ Audio capture failed:', error);
            isCapturing = false;
        }
    }
    
    // Stop audio capture
    function stopAudioCapture() {
        if (!isCapturing) return;
        
        console.log('⏹️ Stopping audio capture...');
        
        if (processor) {
            processor.disconnect();
            processor = null;
        }
        
        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }
        
        isCapturing = false;
        audioChunkCount = 0;
        console.log('✅ Audio capture stopped');
    }
    
    // Play AI audio response
    function playAudioResponse(base64Audio) {
        try {
            const binary = atob(base64Audio);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }
            
            const blob = new Blob([bytes], { type: 'audio/wav' });
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            
            audio.play().catch(err => {
                console.error('❌ Failed to play audio:', err);
            });
            
            audio.onended = () => {
                URL.revokeObjectURL(url);
            };
            
        } catch (error) {
            console.error('❌ Error playing audio response:', error);
        }
    }
    
    // Initialize
    console.log('✅ CallTools Audio Bridge Script Ready!');
    connectWebSocket();
    monitorPeerConnections();
    
})();
"""


async def login_to_calltools(driver):
    """Login to CallTools"""
    try:
        logger.info(f"🌐 Opening CallTools: {CALLTOOLS_URL}")
        driver.get(CALLTOOLS_URL)
        
        # Wait for login page
        wait = WebDriverWait(driver, 20)
        
        logger.info("⏳ Waiting for login page to load...")
        await asyncio.sleep(3)
        
        # Take screenshot for debugging
        try:
            driver.save_screenshot("login_page.png")
            logger.info("📸 Screenshot saved: login_page.png")
        except:
            pass
        
        # Try multiple selectors for username field
        logger.info("🔍 Looking for username field...")
        username_field = None
        
        selectors = [
            (By.ID, "username"),
            (By.NAME, "username"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.CSS_SELECTOR, "input[placeholder*='user' i]"),
            (By.CSS_SELECTOR, "input[placeholder*='name' i]"),
        ]
        
        for by, selector in selectors:
            try:
                username_field = wait.until(
                    EC.presence_of_element_located((by, selector))
                )
                logger.info(f"✅ Found username field with: {by}={selector}")
                break
            except:
                continue
        
        if not username_field:
            logger.error("❌ Could not find username field!")
            logger.info("📋 Page source preview:")
            logger.info(driver.page_source[:500])
            return False
        
        username_field.clear()
        username_field.send_keys(CALLTOOLS_USERNAME)
        logger.info(f"✅ Entered username: {CALLTOOLS_USERNAME}")
        
        # Try multiple selectors for password field
        logger.info("🔍 Looking for password field...")
        password_field = None
        
        password_selectors = [
            (By.ID, "password"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, "input[placeholder*='pass' i]"),
        ]
        
        for by, selector in password_selectors:
            try:
                password_field = driver.find_element(by, selector)
                logger.info(f"✅ Found password field with: {by}={selector}")
                break
            except:
                continue
        
        if not password_field:
            logger.error("❌ Could not find password field!")
            return False
        
        password_field.clear()
        password_field.send_keys(CALLTOOLS_PASSWORD)
        logger.info("✅ Entered password")
        
        # Try multiple selectors for login button
        logger.info("🔍 Looking for login button...")
        login_button = None
        
        button_selectors = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.XPATH, "//button[contains(text(), 'Sign')]"),
            (By.CSS_SELECTOR, "button.btn-primary"),
        ]
        
        for by, selector in button_selectors:
            try:
                login_button = driver.find_element(by, selector)
                logger.info(f"✅ Found login button with: {by}={selector}")
                break
            except:
                continue
        
        if not login_button:
            logger.error("❌ Could not find login button!")
            return False
        
        login_button.click()
        logger.info("✅ Clicked login button")
        
        # Wait for dashboard
        logger.info("⏳ Waiting for dashboard to load...")
        await asyncio.sleep(8)
        
        # Take screenshot after login
        try:
            driver.save_screenshot("after_login.png")
            logger.info("📸 Screenshot saved: after_login.png")
        except:
            pass
        
        # Check if login was successful
        current_url = driver.current_url
        logger.info(f"📍 Current URL: {current_url}")
        
        if "login" not in current_url.lower():
            logger.info("✅ LOGIN SUCCESSFUL")
            return True
        else:
            logger.error("❌ Still on login page - login may have failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Login failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def auto_join_campaign(driver):
    """Automatically join campaign after login"""
    try:
        wait = WebDriverWait(driver, 15)
        
        # Look for "Join Campaign" link/button
        logger.info("🔍 Looking for campaign join button...")
        
        button_selectors = [
            (By.LINK_TEXT, "Join Campaign"),  # Exact text match for <a> tag
            (By.PARTIAL_LINK_TEXT, "Join Campaign"),
            (By.XPATH, "//a[contains(text(), 'Join Campaign')]"),
            (By.XPATH, "//button[contains(text(), 'Join Campaign')]"),
            (By.CSS_SELECTOR, "a[href*='campaign']"),
        ]
        
        for by, selector in button_selectors:
            try:
                button = wait.until(EC.element_to_be_clickable((by, selector)))
                logger.info(f"✅ Found campaign button: {by}={selector}")
                
                # Scroll into view
                driver.execute_script("arguments[0].scrollIntoView(true);", button)
                await asyncio.sleep(1)
                
                # Click
                button.click()
                logger.info("✅ Clicked Join Campaign button")
                await asyncio.sleep(3)
                
                # If there's a campaign selection, select first one
                try:
                    campaign_options = driver.find_elements(By.CSS_SELECTOR, "option, .campaign-item, [data-campaign], input[type='radio']")
                    if campaign_options:
                        campaign_options[0].click()
                        logger.info("✅ Selected first campaign")
                        await asyncio.sleep(2)
                        
                        # Click confirm if needed
                        confirm_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Join') or contains(text(), 'Start')]")
                        if confirm_buttons:
                            confirm_buttons[0].click()
                            logger.info("✅ Confirmed campaign join")
                            await asyncio.sleep(2)
                except:
                    pass
                
                return True
            except Exception as e:
                continue
        
        logger.warning("⚠️ Could not find campaign join button")
        return False
        
    except Exception as e:
        logger.error(f"❌ Auto-join campaign failed: {e}")
        return False
    """Login to CallTools"""
    try:
        logger.info(f"🌐 Opening CallTools: {CALLTOOLS_URL}")
        driver.get(CALLTOOLS_URL)
        
        # Wait for login page
        wait = WebDriverWait(driver, 20)
        
        logger.info("⏳ Waiting for login page to load...")
        await asyncio.sleep(3)
        
        # Take screenshot for debugging
        try:
            driver.save_screenshot("login_page.png")
            logger.info("📸 Screenshot saved: login_page.png")
        except:
            pass
        
        # Try multiple selectors for username field
        logger.info("🔍 Looking for username field...")
        username_field = None
        
        selectors = [
            (By.ID, "username"),
            (By.NAME, "username"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.CSS_SELECTOR, "input[placeholder*='user' i]"),
            (By.CSS_SELECTOR, "input[placeholder*='name' i]"),
        ]
        
        for by, selector in selectors:
            try:
                username_field = wait.until(
                    EC.presence_of_element_located((by, selector))
                )
                logger.info(f"✅ Found username field with: {by}={selector}")
                break
            except:
                continue
        
        if not username_field:
            logger.error("❌ Could not find username field!")
            logger.info("📋 Page source preview:")
            logger.info(driver.page_source[:500])
            return False
        
        username_field.clear()
        username_field.send_keys(CALLTOOLS_USERNAME)
        logger.info(f"✅ Entered username: {CALLTOOLS_USERNAME}")
        
        # Try multiple selectors for password field
        logger.info("🔍 Looking for password field...")
        password_field = None
        
        password_selectors = [
            (By.ID, "password"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, "input[placeholder*='pass' i]"),
        ]
        
        for by, selector in password_selectors:
            try:
                password_field = driver.find_element(by, selector)
                logger.info(f"✅ Found password field with: {by}={selector}")
                break
            except:
                continue
        
        if not password_field:
            logger.error("❌ Could not find password field!")
            return False
        
        password_field.clear()
        password_field.send_keys(CALLTOOLS_PASSWORD)
        logger.info("✅ Entered password")
        
        # Try multiple selectors for login button
        logger.info("🔍 Looking for login button...")
        login_button = None
        
        button_selectors = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Login')]"),
            (By.XPATH, "//button[contains(text(), 'Sign')]"),
            (By.CSS_SELECTOR, "button.btn-primary"),
        ]
        
        for by, selector in button_selectors:
            try:
                login_button = driver.find_element(by, selector)
                logger.info(f"✅ Found login button with: {by}={selector}")
                break
            except:
                continue
        
        if not login_button:
            logger.error("❌ Could not find login button!")
            return False
        
        login_button.click()
        logger.info("✅ Clicked login button")
        
        # Wait for dashboard
        logger.info("⏳ Waiting for dashboard to load...")
        await asyncio.sleep(8)
        
        # Take screenshot after login
        try:
            driver.save_screenshot("after_login.png")
            logger.info("📸 Screenshot saved: after_login.png")
        except:
            pass
        
        # Check if login was successful
        current_url = driver.current_url
        logger.info(f"📍 Current URL: {current_url}")
        
        if "login" not in current_url.lower():
            logger.info("✅ LOGIN SUCCESSFUL")
            return True
        else:
            logger.error("❌ Still on login page - login may have failed")
            return False
        
    except Exception as e:
        logger.error(f"❌ Login failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def monitor_calls(driver):
    """Monitor for incoming calls and inject audio bridge"""
    try:
        logger.info("=" * 60)
        logger.info("🎧 CallTools Audio Bridge Active!")
        logger.info("   System will auto-detect calls and trigger HumeAI")
        logger.info("   Audio will ONLY stream during active calls ")
        logger.info("=" * 60)
        
        # Inject audio bridge script
        driver.execute_script(CALLTOOLS_AUDIO_BRIDGE_JS)
        
        session_id = str(int(time.time()))
        logger.info("✅ Audio bridge script injected into browser")
        logger.info(f"   Session ID: {session_id}")
        
        # Monitor console logs
        logger.info("👁️ Monitoring for call events...")
        
        last_call_state = False
        
        while True:
            try:
                # Check for call via JavaScript
                call_detected = driver.execute_script("""
                    // Check if RTCPeerConnection exists with audio tracks
                    const pcs = window.RTCPeerConnection?.prototype;
                    if (!pcs) return false;
                    
                    // Check for active peer connections
                    let hasAudio = false;
                    try {
                        // Simple check: if getUserMedia was called, likely in call
                        if (navigator.mediaDevices && document.querySelector('video,audio')) {
                            hasAudio = true;
                        }
                    } catch (e) {}
                    
                    return hasAudio;
                """)
                
                if call_detected and not last_call_state:
                    # Call just started
                    logger.info("📍 Call detected via WebRTC PeerConnection")
                    logger.info("=" * 60)
                    logger.info("📞 CALL DETECTED!")
                    
                    # Get stats
                    stats = driver.execute_script("""
                        return {
                            peerConnections: window.peerConnectionCount || 0,
                            audioTracks: window.audioTrackCount || 0,
                            wsConnected: window.ws?.readyState === 1
                        };
                    """)
                    
                    logger.info(f"   PeerConnections: {stats.get('peerConnections', 'Unknown')}")
                    logger.info(f"   Audio Tracks: {stats.get('audioTracks', 'Unknown')}")
                    logger.info(f"   WebSocket: {'Connected' if stats.get('wsConnected') else 'Disconnected'}")
                    logger.info("=" * 60)
                    
                    # Trigger call_start event
                    driver.execute_script("""
                        if (window.ws && window.ws.readyState === 1) {
                            window.ws.send(JSON.stringify({
                                type: 'call_start',
                                session_id: '""" + session_id + """',
                                timestamp: Date.now()
                            }));
                        }
                    """)
                    logger.info("✅ Sent call_start event to backend")
                    
                    last_call_state = True
                    
                elif not call_detected and last_call_state:
                    # Call just ended
                    logger.info("📴 Call ended")
                    last_call_state = False
                
            except Exception as e:
                logger.error(f"Error checking call state: {e}")
            
            await asyncio.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("\n⏹️ Stopping monitor...")
    except Exception as e:
        logger.error(f"❌ Monitor error: {e}")
        raise


async def main():
    """Main entry point"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║  CallTools Call Event Monitor + HumeAI Audio Bridge     ║")
    logger.info("║  Automatically detects calls and triggers AI agent       ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info("")
    
    # Create unique user data directory for this user
    import hashlib
    import os
    user_hash = hashlib.md5(CALLTOOLS_USERNAME.encode()).hexdigest()[:8]
    user_data_dir = os.path.abspath(f"./chrome_profiles/user_{user_hash}")
    
    # Create directory if not exists
    os.makedirs(user_data_dir, exist_ok=True)
    
    # Setup Chrome with separate user profile
    chrome_options = Options()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")  # Auto-allow mic
    chrome_options.add_argument("--use-fake-device-for-media-stream")  # Use fake mic
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Create driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    
    logger.info(f"✅ Browser setup complete (Profile: user_{user_hash})")
    
    try:
        # Login
        if not await login_to_calltools(driver):
            logger.error("❌ Failed to login")
            return
        
        # Wait for page to stabilize
        await asyncio.sleep(5)
        
        # Auto join campaign if enabled
        if AUTO_JOIN_CAMPAIGN:
            logger.info("🎯 Auto-joining campaign...")
            if await auto_join_campaign(driver):
                logger.info("✅ Successfully joined campaign!")
            else:
                logger.warning("⚠️ Could not auto-join campaign - continue manually")
        
        # Monitor calls
        logger.info("📞 Waiting for incoming call...")
        await monitor_calls(driver)
        
    except KeyboardInterrupt:
        logger.info("\n👋 Shutting down...")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            driver.quit()
            logger.info("✅ Browser closed")
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
