"""
Complete Automation with Smart Call Detection
- Auto login to CallTools
- Wait for you to dial
- Detect real call start
- Connect HumeAI automatically
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CallTools Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
USERNAME = "Al.Hassan"
PASSWORD = "Orangeroofing"

print("╔══════════════════════════════════════════════════════════╗")
print("║  AUTO LOGIN + SMART CALL DETECTION                      ║")
print("╚══════════════════════════════════════════════════════════╝")
print()
print("✅ Will auto-login to CallTools")
print("⏳ Will wait for YOU to dial")
print("🎯 Will detect REAL call start")
print("🤖 Will connect HumeAI automatically")
print()
print("="*60)


# Smart JavaScript - Real Call Detection
SMART_DETECTION_JS = """
(function() {
    console.log('🚀 Smart Detection System Loading...');
    
    const BACKEND_WS_URL = 'ws://localhost:8000/ws/webrtc-audio';
    const SESSION_ID = 'auto_""" + str(int(time.time())) + """';
    const SAMPLE_RATE = 16000;
    
    let ws = null;
    let audioContext = null;
    let processor = null;
    let isCapturing = false;
    let callActive = false;
    let audioChunkCount = 0;
    let callStartTime = 0;
    
    // Connect WebSocket
    function connectWebSocket() {
        console.log('🔌 Connecting to backend...');
        ws = new WebSocket(BACKEND_WS_URL);
        
        ws.onopen = () => {
            console.log('✅ Connected to backend!');
            ws.send(JSON.stringify({
                type: 'init',
                session_id: SESSION_ID
            }));
        };
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'audio_response') {
                    playAudioResponse(data.data);
                } else if (data.type === 'transcript') {
                    console.log(`💬 ${data.speaker}: ${data.text}`);
                }
            } catch (e) {
                console.error('Parse error:', e);
            }
        };
        
        ws.onerror = (e) => console.error('❌ WS Error:', e);
        ws.onclose = () => {
            console.log('⚠️ WS Closed');
            stopAudioCapture();
        };
    }
    
    // Setup Real Call Detection
    function setupCallDetection() {
        console.log('👁️ Monitoring for call...');
        
        const OriginalRTC = window.RTCPeerConnection;
        window.RTCPeerConnection = function(...args) {
            const pc = new OriginalRTC(...args);
            console.log('🎯 PeerConnection detected!');
            
            pc.addEventListener('connectionstatechange', () => {
                console.log('🔗 State:', pc.connectionState);
                if (pc.connectionState === 'connected' && !callActive) {
                    console.log('✅✅✅ CALL CONNECTED! ✅✅✅');
                    onCallStart();
                } else if (['disconnected', 'failed', 'closed'].includes(pc.connectionState) && callActive) {
                    console.log('📴 Call ended');
                    onCallEnd();
                }
            });
            
            pc.addEventListener('iceconnectionstatechange', () => {
                console.log('🧊 ICE:', pc.iceConnectionState);
                if (pc.iceConnectionState === 'connected' && !callActive) {
                    console.log('✅ ICE Connected = Call Active!');
                    onCallStart();
                }
            });
            
            pc.addEventListener('track', (e) => {
                if (e.track.kind === 'audio' && !callActive) {
                    console.log('🎵 Audio track = Call started!');
                    onCallStart();
                }
            });
            
            return pc;
        };
        window.RTCPeerConnection.prototype = OriginalRTC.prototype;
    }
    
    function onCallStart() {
        if (callActive) return;
        console.log('');
        console.log('═══════════════════════════════════════════════');
        console.log('🚀 CALL STARTED - Activating HumeAI!');
        console.log('═══════════════════════════════════════════════');
        callActive = true;
        callStartTime = Date.now();
        
        if (ws && ws.readyState === 1) {
            ws.send(JSON.stringify({
                type: 'call_start',
                session_id: SESSION_ID,
                timestamp: Date.now()
            }));
        }
        
        setTimeout(() => callActive && startAudioCapture(), 1000);
    }
    
    function onCallEnd() {
        if (!callActive) return;
        console.log('📴 CALL ENDED');
        callActive = false;
        stopAudioCapture();
        
        if (ws && ws.readyState === 1) {
            ws.send(JSON.stringify({
                type: 'call_end',
                session_id: SESSION_ID,
                timestamp: Date.now()
            }));
        }
    }
    
    async function startAudioCapture() {
        if (isCapturing) return;
        console.log('🎤 Starting audio...');
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { sampleRate: SAMPLE_RATE, channelCount: 1 }
            });
            
            audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
            const source = audioContext.createMediaStreamSource(stream);
            processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            processor.onaudioprocess = (e) => {
                if (!callActive || !ws || ws.readyState !== 1) return;
                
                const inputData = e.inputBuffer.getChannelData(0);
                const int16 = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    const s = Math.max(-1, Math.min(1, inputData[i]));
                    int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                }
                
                const bytes = new Uint8Array(int16.buffer);
                ws.send(JSON.stringify({
                    type: 'audio',
                    data: btoa(String.fromCharCode(...bytes))
                }));
                
                if (++audioChunkCount % 50 === 0) {
                    console.log(`📡 Streaming... #${audioChunkCount}`);
                }
            };
            
            source.connect(processor);
            processor.connect(audioContext.destination);
            isCapturing = true;
            console.log('✅ Audio ACTIVE');
        } catch (e) {
            console.error('❌ Audio failed:', e);
        }
    }
    
    function stopAudioCapture() {
        if (!isCapturing) return;
        console.log('⏹️ Stopping audio...');
        if (processor) processor.disconnect();
        if (audioContext) audioContext.close();
        isCapturing = false;
    }
    
    function playAudioResponse(base64) {
        try {
            const binary = atob(base64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            const blob = new Blob([bytes], { type: 'audio/wav' });
            const audio = new Audio(URL.createObjectURL(blob));
            audio.play();
        } catch (e) {
            console.error('❌ Playback error:', e);
        }
    }
    
    console.log('🎬 Initializing...');
    connectWebSocket();
    setupCallDetection();
    console.log('✅ Ready! Dial a number and system will detect the call!');
})();
"""


def auto_login(driver):
    """Auto login to CallTools"""
    try:
        logger.info("🔐 Starting auto-login...")
        time.sleep(3)
        
        # Username
        username_field = None
        for selector in ['input[name="username"]', 'input#username', 'input[type="text"]', 
                        'input[placeholder*="user" i]']:
            try:
                username_field = driver.find_element(By.CSS_SELECTOR, selector)
                if username_field.is_displayed():
                    break
            except:
                continue
        
        if not username_field:
            logger.error("❌ Username field not found")
            return False
        
        username_field.clear()
        username_field.send_keys(USERNAME)
        logger.info(f"✅ Username: {USERNAME}")
        time.sleep(0.5)
        
        # Password
        password_field = None
        for selector in ['input[name="password"]', 'input#password', 'input[type="password"]']:
            try:
                password_field = driver.find_element(By.CSS_SELECTOR, selector)
                if password_field.is_displayed():
                    break
            except:
                continue
        
        if not password_field:
            logger.error("❌ Password field not found")
            return False
        
        password_field.clear()
        password_field.send_keys(PASSWORD)
        logger.info("✅ Password entered")
        time.sleep(0.5)
        
        # Login button
        login_button = None
        for selector in ['button[type="submit"]', 'input[type="submit"]', 
                        'button.login', 'button#login', '.login-button']:
            try:
                login_button = driver.find_element(By.CSS_SELECTOR, selector)
                if login_button.is_displayed():
                    break
            except:
                continue
        
        if not login_button:
            try:
                login_button = driver.find_element(By.XPATH, 
                    "//button[contains(translate(text(), 'LOGIN', 'login'), 'login')]")
            except:
                pass
        
        if not login_button:
            logger.error("❌ Login button not found")
            return False
        
        login_button.click()
        logger.info("✅ Login button clicked")
        time.sleep(5)
        
        # Verify login
        if "login" not in driver.current_url.lower():
            logger.info("✅✅✅ LOGIN SUCCESSFUL! ✅✅✅")
            return True
        
        try:
            driver.find_element(By.CSS_SELECTOR, '.dashboard, #dashboard, [class*="dialer"]')
            logger.info("✅✅✅ LOGIN SUCCESSFUL! ✅✅✅")
            return True
        except:
            logger.warning("⚠️ Login status unclear - continuing")
            return True
            
    except Exception as e:
        logger.error(f"❌ Login failed: {e}")
        return False


def main():
    # Chrome setup
    options = Options()
    options.add_argument('--use-fake-ui-for-media-stream')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.notifications": 2
    })
    
    print("🌐 Opening browser...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Open CallTools
        driver.get(CALLTOOLS_URL)
        
        # Auto login
        if not auto_login(driver):
            print("❌ Login failed! Please login manually.")
        
        time.sleep(2)
        
        # Inject detection
        print("💉 Injecting smart detection...")
        driver.execute_script(SMART_DETECTION_JS)
        print("✅ Detection active!")
        
        print()
        print("="*60)
        print("📞 NOW DIAL A NUMBER!")
        print("   System will auto-detect when call connects")
        print("   HumeAI will activate automatically")
        print("="*60)
        print()
        print("⏳ Monitoring... (Press Ctrl+C to stop)")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Stopping...")
    finally:
        print("🧹 Cleaning up...")
        driver.quit()
        print("✅ Done!")


if __name__ == "__main__":
    main()
