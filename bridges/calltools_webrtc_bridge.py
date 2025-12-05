"""
CallTools WebRTC Audio Bridge
Native browser audio capture using JavaScript injection
No VB-Cable needed - captures WebRTC streams directly
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
import base64

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
USERNAME = "Eddie.Faklis"
PASSWORD = "Roofing123"
PHONE_NUMBER = "2012529790"  # Test number

# FastAPI WebSocket URL
FASTAPI_WS_URL = "ws://localhost:8000/ws/audio-bridge"


class WebRTCAudioBridge:
    """Captures WebRTC audio directly from browser"""
    
    def __init__(self):
        self.driver = None
        self.session_id = str(uuid.uuid4())
        self.fastapi_ws = None
        self.audio_loop_running = False
        
    def setup_browser(self):
        """Setup Chrome with WebRTC permissions"""
        options = webdriver.ChromeOptions()
        options.add_argument('--use-fake-ui-for-media-stream')  # Auto-accept mic
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # Allow mic/speaker access
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
            time.sleep(3)
            
            # Username
            username_selectors = [
                (By.NAME, "username"),
                (By.ID, "username"),
                (By.XPATH, "//input[@type='text' or @type='email']")
            ]
            
            username_field = None
            for by, selector in username_selectors:
                try:
                    username_field = wait.until(EC.presence_of_element_located((by, selector)))
                    break
                except:
                    continue
            
            if not username_field:
                raise Exception("Username field not found")
            
            username_field.clear()
            username_field.send_keys(USERNAME)
            time.sleep(0.5)
            
            # Password
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(PASSWORD)
            time.sleep(0.5)
            
            # Login button
            login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            login_button.click()
            time.sleep(2)
            
            logger.info("✅ LOGIN SUCCESSFUL")
            
            # Join campaign and set status
            time.sleep(3)
            self.join_campaign()
            time.sleep(2)
            self.set_status_available()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False
    
    def join_campaign(self):
        """Join campaign"""
        try:
            time.sleep(2)
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
                        logger.info("✅ Campaign joined")
                        time.sleep(2)
                        return True
                except:
                    continue
        except Exception as e:
            logger.warning(f"⚠️ Could not join campaign: {e}")
        return False
    
    def set_status_available(self):
        """Set status to Available"""
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
                                logger.info("✅ Status set to Available")
                                return True
                            except:
                                continue
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"⚠️ Could not set status: {e}")
        return False
    
    def make_call(self):
        """Dial phone number manually"""
        try:
            logger.info(f"📞 Attempting to dial: {PHONE_NUMBER}")
            wait = WebDriverWait(self.driver, 15)
            time.sleep(2)
            
            # Find dialer input
            dialer_selectors = [
                (By.NAME, "phoneNumber"),
                (By.NAME, "phone"),
                (By.CSS_SELECTOR, "input[placeholder*='phone' i]"),
                (By.CSS_SELECTOR, "input[placeholder*='number' i]"),
                (By.CSS_SELECTOR, "input[type='tel']"),
            ]
            
            dialed = False
            for by, selector in dialer_selectors:
                try:
                    dialer_input = self.driver.find_element(by, selector)
                    dialer_input.clear()
                    dialer_input.send_keys(PHONE_NUMBER)
                    time.sleep(0.5)
                    
                    # Try Enter key
                    from selenium.webdriver.common.keys import Keys
                    dialer_input.send_keys(Keys.RETURN)
                    dialed = True
                    logger.info("✅ Call initiated")
                    break
                except:
                    continue
            
            # Check for popup
            time.sleep(2)
            try:
                popup_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Call')]")
                if popup_btn.is_displayed():
                    popup_btn.click()
                    logger.info("⚠️ Clicked 'Call' on popup")
            except:
                pass
            
            return dialed
            
        except Exception as e:
            logger.error(f"❌ Failed to make call: {e}")
            return False
    
    def inject_webrtc_capture_script(self):
        """
        Inject JavaScript to capture WebRTC audio directly from browser
        This is the CORE of WebRTC solution
        """
        js_code = """
        (function() {
            console.log('🔧 Intercepting WebRTC API...');
            
            // Store all RTCPeerConnections
            window.__peerConnections = [];
            window.__audioTracks = [];
            
            // Intercept RTCPeerConnection constructor
            const OriginalRTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
            
            window.RTCPeerConnection = function(...args) {
                console.log('✅ New RTCPeerConnection created!');
                const pc = new OriginalRTCPeerConnection(...args);
                window.__peerConnections.push(pc);
                
                // Monitor tracks
                pc.ontrack = (event) => {
                    console.log('🎵 Track received:', event.track.kind, event.track.id);
                    if (event.track.kind === 'audio') {
                        window.__audioTracks.push(event.track);
                        console.log('✅ Audio track added! Total:', window.__audioTracks.length);
                        
                        // Try to start capture
                        if (typeof window.startAudioCapture === 'function') {
                            setTimeout(() => window.startAudioCapture(), 1000);
                        }
                    }
                };
                
                return pc;
            };
            
            // Copy static properties
            window.RTCPeerConnection.prototype = OriginalRTCPeerConnection.prototype;
            
            // Create WebSocket connection to FastAPI
            const ws = new WebSocket('ws://localhost:8000/ws/webrtc-audio');
            
            ws.onopen = () => {
                console.log('✅ WebSocket connected to FastAPI');
                window.__audioWsConnected = true;
            };
            
            ws.onerror = (err) => {
                console.error('❌ WebSocket error:', err);
                window.__audioWsConnected = false;
            };
            
            // Variables for audio capture
            window.__audioContext = null;
            window.__mediaStream = null;
            window.__audioProcessor = null;
            window.__audioWs = ws;
            
            // Function to start capturing audio
            window.startAudioCapture = async () => {
                try {
                    console.log('🔍 Checking for active audio tracks...');
                    console.log('Total PeerConnections:', window.__peerConnections.length);
                    console.log('Total Audio Tracks:', window.__audioTracks.length);
                    
                    // Get active audio track
                    let activeTrack = null;
                    for (const track of window.__audioTracks) {
                        if (track.readyState === 'live' && track.enabled) {
                            activeTrack = track;
                            console.log('✅ Found active audio track:', track.id);
                            break;
                        }
                    }
                    
                    if (!activeTrack) {
                        console.warn('⚠️ No active audio track found');
                        return false;
                    }
                    
                    // Create MediaStream from track
                    const stream = new MediaStream([activeTrack]);
                    
                    // Create AudioContext
                    window.__audioContext = new (window.AudioContext || window.webkitAudioContext)({
                        sampleRate: 16000  // HumeAI requires 16kHz
                    });
                    
                    console.log('✅ AudioContext created at 16kHz');
                    
                    // Create MediaStreamSource from track
                    const source = window.__audioContext.createMediaStreamSource(stream);
                    
                    // Create ScriptProcessor for real-time audio processing
                    window.__audioProcessor = window.__audioContext.createScriptProcessor(1024, 1, 1);
                    
                    let frameCount = 0;
                    
                    window.__audioProcessor.onaudioprocess = (e) => {
                        if (!window.__audioWsConnected) return;
                        
                        // Get audio data (Float32Array)
                        const inputData = e.inputBuffer.getChannelData(0);
                        
                        // Convert Float32 to Int16 (PCM16 format for HumeAI)
                        const int16Data = new Int16Array(inputData.length);
                        for (let i = 0; i < inputData.length; i++) {
                            const s = Math.max(-1, Math.min(1, inputData[i]));
                            int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                        }
                        
                        // Convert to base64
                        const base64Audio = btoa(String.fromCharCode.apply(null, new Uint8Array(int16Data.buffer)));
                        
                        // Send to FastAPI
                        if (ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({
                                type: 'audio_input',
                                data: base64Audio,
                                timestamp: Date.now()
                            }));
                            
                            frameCount++;
                            if (frameCount % 100 === 0) {
                                console.log(`📊 Sent ${frameCount} audio frames`);
                            }
                        }
                    };
                    
                    // Connect nodes
                    source.connect(window.__audioProcessor);
                    window.__audioProcessor.connect(window.__audioContext.destination);
                    
                    console.log('✅ WebRTC audio capture started from PeerConnection!');
                    console.log('📡 Sending audio to FastAPI WebSocket');
                    window.__audioCaptureActive = true;
                    return true;
                    
                } catch (error) {
                    console.error('❌ Failed to capture audio:', error);
                    return false;
                }
            };
            
            // Function to check if call is active
            window.isCallActive = () => {
                return window.__audioTracks.length > 0 && 
                       window.__audioTracks.some(t => t.readyState === 'live');
            };
            
            // Function to play AI audio response
            window.playAIAudio = (base64Audio) => {
                try {
                    if (!window.__audioContext) {
                        window.__audioContext = new (window.AudioContext || window.webkitAudioContext)({
                            sampleRate: 16000
                        });
                    }
                    
                    // Decode base64 to ArrayBuffer
                    const binaryString = atob(base64Audio);
                    const len = binaryString.length;
                    const bytes = new Uint8Array(len);
                    for (let i = 0; i < len; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                    }
                    
                    // Convert Int16 to Float32
                    const int16Array = new Int16Array(bytes.buffer);
                    const float32Array = new Float32Array(int16Array.length);
                    for (let i = 0; i < int16Array.length; i++) {
                        float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF);
                    }
                    
                    // Create AudioBuffer
                    const audioBuffer = window.__audioContext.createBuffer(1, float32Array.length, 16000);
                    audioBuffer.getChannelData(0).set(float32Array);
                    
                    // Play
                    const source = window.__audioContext.createBufferSource();
                    source.buffer = audioBuffer;
                    source.connect(window.__audioContext.destination);
                    source.start();
                    
                } catch (error) {
                    console.error('❌ Failed to play AI audio:', error);
                }
            };
            
            // Listen for AI audio from FastAPI
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    if (data.type === 'audio_output') {
                        window.playAIAudio(data.data);
                    } else if (data.type === 'transcript_user') {
                        console.log('👤 User:', data.text);
                    } else if (data.type === 'transcript_ai') {
                        console.log('🤖 AI:', data.text);
                    }
                } catch (error) {
                    console.error('❌ Error processing message:', error);
                }
            };
            
            console.log('✅ WebRTC interception script injected');
            window.__webrtcBridgeReady = true;
            
        })();
        """
        
        self.driver.execute_script(js_code)
        logger.info("✅ WebRTC interception script injected into browser")
    
    def check_call_active(self):
        """Check if call is active by checking RTCPeerConnection"""
        try:
            # Check JavaScript-level tracking
            call_status = self.driver.execute_script("""
                if (typeof window.isCallActive === 'function') {
                    return {
                        active: window.isCallActive(),
                        peerConnections: window.__peerConnections ? window.__peerConnections.length : 0,
                        audioTracks: window.__audioTracks ? window.__audioTracks.length : 0
                    };
                }
                return {active: false, peerConnections: 0, audioTracks: 0};
            """)
            
            logger.info(f"🔍 PeerConnections: {call_status['peerConnections']}, Audio Tracks: {call_status['audioTracks']}, Active: {call_status['active']}")
            
            if call_status['active']:
                logger.info("✅ Active call detected via RTCPeerConnection!")
                return True
            
            # Fallback: Check UI indicators
            active_indicators = [
                "//button[contains(text(), 'Mute')]",
                "//button[contains(text(), 'Hold')]",
                "//button[contains(text(), 'End Call')]",
                "//button[contains(text(), 'Hangup')]",
            ]
            
            for indicator in active_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, indicator)
                    if element.is_displayed():
                        logger.info(f"✅ Found UI indicator: {element.text}")
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.error(f"Error checking call: {e}")
            return False
    
    def start_webrtc_capture(self):
        """Start WebRTC audio capture"""
        try:
            # Check if audio elements exist and log details
            debug_info = self.driver.execute_script("""
                const audios = document.querySelectorAll('audio');
                const videos = document.querySelectorAll('video');
                
                let info = {
                    audioCount: audios.length,
                    videoCount: videos.length,
                    activeStreams: []
                };
                
                audios.forEach((audio, i) => {
                    if (audio.srcObject) {
                        const tracks = audio.srcObject.getAudioTracks();
                        info.activeStreams.push({
                            type: 'audio',
                            index: i,
                            active: audio.srcObject.active,
                            trackCount: tracks.length,
                            trackEnabled: tracks.length > 0 ? tracks[0].enabled : false
                        });
                    }
                });
                
                videos.forEach((video, i) => {
                    if (video.srcObject) {
                        const tracks = video.srcObject.getAudioTracks();
                        info.activeStreams.push({
                            type: 'video',
                            index: i,
                            active: video.srcObject.active,
                            trackCount: tracks.length,
                            trackEnabled: tracks.length > 0 ? tracks[0].enabled : false
                        });
                    }
                });
                
                return info;
            """)
            
            logger.info(f"📊 Media elements: {debug_info['audioCount']} audio, {debug_info['videoCount']} video")
            logger.info(f"📊 Active streams: {len(debug_info['activeStreams'])}")
            
            if debug_info['activeStreams']:
                for stream in debug_info['activeStreams']:
                    logger.info(f"   - {stream['type']}[{stream['index']}]: active={stream['active']}, tracks={stream['trackCount']}, enabled={stream['trackEnabled']}")
            
            # Try to start capture
            result = self.driver.execute_script("return window.startAudioCapture();")
            
            if result:
                logger.info("✅ WebRTC audio capture started")
                
                # Log WebSocket connection status
                ws_status = self.driver.execute_script("return window.__audioWsConnected;")
                logger.info(f"🔌 WebSocket connected: {ws_status}")
                return True
            else:
                logger.warning("⚠️ WebRTC capture not ready yet")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start WebRTC capture: {e}")
            return False
    
    async def monitor_call_and_capture(self):
        """Monitor for call start and automatically start audio capture"""
        logger.info("👁️ Monitoring for call events...")
        logger.info("📞 Waiting for incoming call... (Manual dial DISABLED)")
        
        call_was_active = False
        
        while True:
            try:
                call_active = self.check_call_active()
                
                if call_active and not call_was_active:
                    # Call just started!
                    logger.info("📞 CALL DETECTED! Starting WebRTC capture...")
                    
                    # Wait for audio element to be fully ready
                    await asyncio.sleep(2)
                    
                    # Try to start WebRTC capture (with retries)
                    max_retries = 5
                    for retry in range(max_retries):
                        if self.start_webrtc_capture():
                            logger.info("🎉 WebRTC audio bridge is ACTIVE!")
                            logger.info("🔊 Audio is now flowing: Customer → HumeAI → Customer")
                            call_was_active = True
                            break
                        else:
                            if retry < max_retries - 1:
                                logger.warning(f"⚠️ Retry {retry + 1}/{max_retries} - Waiting for WebRTC stream...")
                                await asyncio.sleep(1)
                            else:
                                logger.error("❌ Failed to capture WebRTC stream after retries")
                                logger.info("💡 Open browser console (F12) to see JavaScript errors")
                                call_was_active = False
                
                elif not call_active and call_was_active:
                    # Call ended
                    logger.info("📴 Call ended")
                    call_was_active = False
                    manual_dial_attempted = False  # Allow retry on next cycle
                
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(2)
    
    async def run(self):
        """Main execution flow"""
        try:
            # Setup browser
            self.setup_browser()
            
            # Login
            if not self.login():
                return
            
            logger.info("🎧 Ready to receive calls!")
            logger.info("💡 System will auto-detect calls and start WebRTC capture")
            
            # Inject WebRTC capture script
            time.sleep(2)
            self.inject_webrtc_capture_script()
            
            # Monitor for calls
            await self.monitor_call_and_capture()
            
        except KeyboardInterrupt:
            logger.info("\n⚠️ Interrupted by user")
        finally:
            if self.driver:
                logger.info("🧹 Cleaning up...")
                self.driver.quit()


async def main():
    bridge = WebRTCAudioBridge()
    await bridge.run()


if __name__ == "__main__":
    logger.info("""
╔══════════════════════════════════════════════════════════╗
║  CallTools WebRTC Audio Bridge                           ║
║  Native browser audio capture - No VB-Cable needed!      ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
