"""
Simple Direct Approach - HumeAI Voice Agent for Phone Calls
Uses browser's default audio routing to phone
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# CallTools credentials
USERNAME = "Al.Hassan"
PASSWORD = "Orangeroofing"
CALLTOOLS_URL = "https://east-1.calltools.io"

# HumeAI credentials
HUME_API_KEY = "dmWJAfVJARQhlyqwFJhMBlPnfUTOvN8u3CtbQcSC7GGfAspA"
HUME_CONFIG_ID = "64cfa125-77d6-4746-b64f-5b3ac83c5fb6"

print("="*70)
print("🚀 Simple Phone + HumeAI Integration")
print("="*70)
print("\n📋 This version uses SIMPLE audio routing")
print("   ✅ Browser plays AI voice through speakers")
print("   ✅ Microphone captures your voice")
print("   ✅ Full conversation with HumeAI")
print("\n" + "="*70 + "\n")

# Setup Chrome
options = webdriver.ChromeOptions()
options.add_experimental_option("detach", True)
options.add_argument("--use-fake-ui-for-media-stream")
options.add_argument("--autoplay-policy=no-user-gesture-required")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option("excludeSwitches", ["enable-automation"])

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.maximize_window()

# Login to CallTools
print("📱 Logging into CallTools...")
driver.get(CALLTOOLS_URL)
time.sleep(3)

try:
    username_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
    )
    password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    
    username_input.clear()
    username_input.send_keys(USERNAME)
    print("   ✅ Username entered")
    
    password_input.clear()
    password_input.send_keys(PASSWORD)
    print("   ✅ Password entered")
    
    time.sleep(1)
    login_buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in login_buttons:
        if btn.text.strip():
            driver.execute_script("arguments[0].click();", btn)
            print("   ✅ Login button clicked")
            break
    
    time.sleep(5)
    print("✅ Logged in!\n")
except Exception as e:
    print(f"❌ Login failed: {e}")
    driver.quit()
    exit()

# Inject simple HumeAI integration
print("🔍 Setting up HumeAI voice agent...")

SIMPLE_HUME_JS = f"""
(function() {{
    const HUME_API_KEY = '{HUME_API_KEY}';
    const HUME_CONFIG_ID = '{HUME_CONFIG_ID}';
    
    let humeWs = null;
    let micStream = null;
    let audioContext = null;
    let isCallActive = false;
    let audioQueue = [];
    let isPlaying = false;
    
    function log(msg) {{
        console.log(`[HumeAI] ${{new Date().toLocaleTimeString()}} - ${{msg}}`);
    }}
    
    // Detect call start
    const originalRTC = window.RTCPeerConnection;
    window.RTCPeerConnection = function(...args) {{
        const pc = new originalRTC(...args);
        
        pc.addEventListener('iceconnectionstatechange', () => {{
            if (pc.iceConnectionState === 'connected' && !isCallActive) {{
                isCallActive = true;
                log('📞 CALL STARTED - Starting HumeAI...');
                startHumeAI();
            }}
            if (pc.iceConnectionState === 'disconnected' && isCallActive) {{
                isCallActive = false;
                log('🔴 CALL ENDED - Stopping HumeAI...');
                stopHumeAI();
            }}
        }});
        
        return pc;
    }};
    
    async function startHumeAI() {{
        try {{
            // Create audio context
            audioContext = new (window.AudioContext || window.webkitAudioContext)({{
                sampleRate: 16000
            }});
            
            // Get microphone
            micStream = await navigator.mediaDevices.getUserMedia({{
                audio: {{ echoCancellation: true, noiseSuppression: true, sampleRate: 16000 }}
            }});
            log('✅ Microphone access granted');
            
            // Connect to HumeAI
            const wsUrl = `wss://api.hume.ai/v0/assistant/chat?api_key=${{HUME_API_KEY}}&config_id=${{HUME_CONFIG_ID}}`;
            humeWs = new WebSocket(wsUrl);
            
            humeWs.onopen = () => {{
                log('✅ HumeAI connected!');
                startAudioStreaming();
            }};
            
            humeWs.onmessage = async (event) => {{
                const msg = JSON.parse(event.data);
                
                if (msg.type === 'chat_metadata') {{
                    log(`Chat ID: ${{msg.chat_id}}`);
                }}
                
                if (msg.type === 'audio_output' && msg.data) {{
                    log(`🤖 AI speaking (${{msg.data.length}} bytes)`);
                    audioQueue.push(msg.data);
                    if (!isPlaying) playNextAudio();
                }}
                
                if (msg.type === 'assistant_message') {{
                    log(`AI said: "${{msg.message.content}}"`);
                }}
                
                if (msg.type === 'user_message') {{
                    log(`You said: "${{msg.message.content}}"`);
                }}
            }};
            
            humeWs.onerror = (err) => log(`❌ WebSocket error: ${{err}}`);
            humeWs.onclose = () => log('HumeAI disconnected');
            
        }} catch (error) {{
            log(`❌ Setup error: ${{error.message}}`);
        }}
    }}
    
    function startAudioStreaming() {{
        const source = audioContext.createMediaStreamSource(micStream);
        const processor = audioContext.createScriptProcessor(4096, 1, 1);
        
        let chunks = 0;
        processor.onaudioprocess = (e) => {{
            if (!humeWs || humeWs.readyState !== WebSocket.OPEN) return;
            
            const inputData = e.inputBuffer.getChannelData(0);
            const int16 = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {{
                int16[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
            }}
            
            const bytes = new Uint8Array(int16.buffer);
            const base64 = btoa(String.fromCharCode(...bytes));
            
            humeWs.send(JSON.stringify({{ type: 'audio_input', data: base64 }}));
            
            chunks++;
            if (chunks === 1) log('📤 Streaming audio to AI...');
        }};
        
        source.connect(processor);
        processor.connect(audioContext.destination);
        log('✅ Audio streaming active');
    }}
    
    async function playNextAudio() {{
        if (audioQueue.length === 0) {{
            isPlaying = false;
            return;
        }}
        
        isPlaying = true;
        const base64Data = audioQueue.shift();
        
        try {{
            // Decode
            const binary = atob(base64Data);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {{
                bytes[i] = binary.charCodeAt(i);
            }}
            
            // Convert to float
            const float32 = new Float32Array(bytes.length / 2);
            const dataView = new DataView(bytes.buffer);
            for (let i = 0; i < float32.length; i++) {{
                float32[i] = dataView.getInt16(i * 2, true) / 32768.0;
            }}
            
            // Create buffer
            const buffer = audioContext.createBuffer(1, float32.length, 16000);
            buffer.getChannelData(0).set(float32);
            
            // Play
            const source = audioContext.createBufferSource();
            source.buffer = buffer;
            source.playbackRate.value = 1.2; // Slightly faster
            
            const gain = audioContext.createGain();
            gain.gain.value = 2.0; // Louder
            
            source.connect(gain);
            gain.connect(audioContext.destination);
            
            source.onended = () => {{
                log('🎵 Audio finished');
                playNextAudio();
            }};
            
            source.start();
            log('🔊 Playing AI audio');
            
        }} catch (error) {{
            log(`❌ Audio play error: ${{error.message}}`);
            playNextAudio();
        }}
    }}
    
    function stopHumeAI() {{
        if (humeWs) {{
            humeWs.close();
            humeWs = null;
        }}
        if (micStream) {{
            micStream.getTracks().forEach(t => t.stop());
            micStream = null;
        }}
        audioQueue = [];
        isPlaying = false;
        log('✅ Cleaned up');
    }}
    
    log('🎯 System ready - waiting for call...');
}})();
"""

driver.execute_script(SIMPLE_HUME_JS)
print("✅ HumeAI voice agent installed!\n")

print("="*70)
print("🎯 READY!")
print("="*70)
print("\n📱 Now make a phone call")
print("🎧 You'll hear AI voice in BROWSER SPEAKERS")
print("🎤 Speak into your COMPUTER MICROPHONE")
print("💬 Have a natural conversation!\n")
print("⚠️  NOTE: This is for TESTING - audio routes through browser")
print("    For production, use phone audio directly\n")
print("="*70)
print("\n⌨️  Press Ctrl+C to stop...\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\n🛑 Stopping...")
    driver.quit()
