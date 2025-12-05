"""
CallTools Auto-Login with HumeAI Voice Agent
User will call from mobile, AI will speak
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
USERNAME = "Al.Hassan"
PASSWORD = "Orangeroofing"

# HumeAI Config
HUME_API_KEY = "dmWJAfVJARQhlyqwFJhMBlPnfUTOvN8u3CtbQcSC7GGfAspA"
HUME_CONFIG_ID = "64cfa125-77d6-4746-b64f-5b3ac83c5fb6"

# Complete HumeAI Integration Script
HUME_INTEGRATION_JS = """
(function() {
    console.log('🎯 Starting HumeAI Voice Agent...');
    
    // HumeAI Connection
    let humeWs = null;
    let chatId = null;
    let audioContext = null;
    let audioQueue = [];
    let isPlaying = false;
    let isSpeaking = false;
    
    // Connect to HumeAI
    function connectHumeAI() {
        const wsUrl = `wss://api.hume.ai/v0/assistant/chat?api_key=dmWJAfVJARQhlyqwFJhMBlPnfUTOvN8u3CtbQcSC7GGfAspA&config_id=64cfa125-77d6-4746-b64f-5b3ac83c5fb6`;
        
        console.log('📡 Connecting to HumeAI...');
        humeWs = new WebSocket(wsUrl);
        
        humeWs.onopen = () => {
            console.log('✅ HumeAI Connected!');
            document.title = '✅ HumeAI Ready - Call Now!';
        };
        
        humeWs.onmessage = async (event) => {
            const message = JSON.parse(event.data);
            
            if (message.type === 'chat_metadata') {
                chatId = message.chat_id;
                console.log('✅ Chat ID:', chatId);
                console.log('📞 READY! Call karo ab - Agent bolega!');
            }
            
            if (message.type === 'audio_output' && message.data) {
                console.log('🔊 AI Audio received:', message.data.length, 'bytes');
                await playAudioFromBase64(message.data);
            }
            
            if (message.type === 'assistant_message') {
                console.log('🤖 AI Said:', message.message.content);
            }
            
            if (message.type === 'user_message') {
                console.log('👤 You Said:', message.message.content);
            }
        };
        
        humeWs.onerror = (error) => {
            console.error('❌ HumeAI Error:', error);
        };
        
        humeWs.onclose = () => {
            console.log('🔌 HumeAI Disconnected');
            setTimeout(connectHumeAI, 2000); // Reconnect
        };
    }
    
    // Play AI audio
    async function playAudioFromBase64(base64Data) {
        try {
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: 16000
                });
            }
            
            // Decode base64
            const binaryString = atob(base64Data);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            // Convert to Float32Array
            const float32Array = new Float32Array(bytes.length / 2);
            const dataView = new DataView(bytes.buffer);
            for (let i = 0; i < float32Array.length; i++) {
                float32Array[i] = dataView.getInt16(i * 2, true) / 32768.0;
            }
            
            // Create audio buffer
            const audioBuffer = audioContext.createBuffer(1, float32Array.length, 16000);
            audioBuffer.getChannelData(0).set(float32Array);
            
            // Add to queue
            audioQueue.push(audioBuffer);
            
            if (!isPlaying) {
                playNextAudio();
            }
        } catch (error) {
            console.error('❌ Audio decode error:', error);
        }
    }
    
    // Play next audio chunk
    function playNextAudio() {
        if (audioQueue.length === 0) {
            isPlaying = false;
            isSpeaking = false;
            return;
        }
        
        isPlaying = true;
        isSpeaking = true;
        const audioBuffer = audioQueue.shift();
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        
        // Increase volume
        const gainNode = audioContext.createGain();
        gainNode.gain.value = 2.0; // Double volume
        
        source.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        source.onended = () => {
            playNextAudio();
        };
        
        source.start();
        console.log('▶️ Playing AI audio chunk');
    }
    
    // Capture microphone audio and send to HumeAI
    async function startMicrophoneCapture() {
        try {
            console.log('🎤 Starting microphone capture...');
            
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000
                } 
            });
            
            console.log('✅ Microphone access granted');
            
            const audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });
            
            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            processor.onaudioprocess = (e) => {
                // Don't send audio while AI is speaking
                if (isSpeaking || !humeWs || humeWs.readyState !== WebSocket.OPEN) return;
                
                const inputData = e.inputBuffer.getChannelData(0);
                
                // Convert to Int16
                const int16Data = new Int16Array(inputData.length);
                for (let i = 0; i < inputData.length; i++) {
                    int16Data[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
                }
                
                // Convert to base64
                const bytes = new Uint8Array(int16Data.buffer);
                const base64 = btoa(String.fromCharCode(...bytes));
                
                // Send to HumeAI
                try {
                    humeWs.send(JSON.stringify({
                        type: 'audio_input',
                        data: base64
                    }));
                } catch (err) {
                    console.error('Send error:', err);
                }
            };
            
            source.connect(processor);
            processor.connect(audioContext.destination);
            
            console.log('✅ Audio streaming to HumeAI started');
            
        } catch (error) {
            console.error('❌ Microphone error:', error);
            alert('⚠️ Microphone access required! Please allow microphone access.');
        }
    }
    
    // Initialize everything
    console.log('🚀 Initializing HumeAI Voice Agent...');
    connectHumeAI();
    
    // Wait 2 seconds then start microphone
    setTimeout(() => {
        startMicrophoneCapture();
    }, 2000);
    
    // Keep reference for debugging
    window.humeAgent = {
        ws: humeWs,
        chatId: () => chatId,
        audioQueue: audioQueue,
        isPlaying: () => isPlaying,
        isSpeaking: () => isSpeaking
    };
    
    console.log('✅ HumeAI Voice Agent initialized!');
    console.log('📞 Ab apne mobile se call karo!');
    
})();
"""

def main():
    print("=" * 70)
    print("🚀 CallTools Auto-Login + HumeAI Voice Agent")
    print("=" * 70)
    print("\n📋 Instructions:")
    print("   1. Browser open hoga aur auto-login hoga")
    print("   2. HumeAI agent ready hoga")
    print("   3. Apne mobile se call karo")
    print("   4. AI agent tumse baat karega!")
    print("\n" + "=" * 70 + "\n")
    
    # Setup Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--use-fake-ui-for-media-stream')
    options.add_argument('--use-fake-device-for-media-stream')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    # Keep browser open
    options.add_experimental_option("detach", True)
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    try:
        # Step 1: Login
        print("📱 Step 1: Logging into CallTools...")
        driver.get(CALLTOOLS_URL)
        time.sleep(3)
        
        # Username
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[name='username']"))
        )
        username_input.clear()
        username_input.send_keys(USERNAME)
        print("   ✅ Username entered")
        
        # Password
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_input.clear()
        password_input.send_keys(PASSWORD)
        print("   ✅ Password entered")
        
        # Login button
        try:
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except:
            login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'login')]")
        
        driver.execute_script("arguments[0].click();", login_button)
        print("   ✅ Login button clicked")
        
        time.sleep(5)
        print("✅ Logged in successfully!\n")
        
        # Step 2: Inject HumeAI
        print("🤖 Step 2: Initializing HumeAI Voice Agent...")
        driver.execute_script(HUME_INTEGRATION_JS)
        print("✅ HumeAI Voice Agent ready!\n")
        
        time.sleep(3)
        
        # Step 3: Ready
        print("=" * 70)
        print("🎉 SYSTEM READY!")
        print("=" * 70)
        print("\n📞 Ab apne mobile se call karo!")
        print("🤖 AI agent automatically bolega: 'Hello! Thanks for calling...'")
        print("\n💡 Tips:")
        print("   - AI pehle bolega (greeting)")
        print("   - Phir tum baat karo")
        print("   - AI tumhara response dega")
        print("   - Natural conversation hogi")
        print("\n🔊 Audio:")
        print("   - AI ki awaaz browser speakers se aaegi")
        print("   - Tumhari awaaz phone se jaegi")
        print("\n⏸️ Browser ko open rakho call ke liye!")
        print("=" * 70)
        
        # Keep script running
        print("\n⏳ Waiting for calls... (Press Ctrl+C to stop)")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopping...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Done! Browser will stay open for testing.")
    print("   (Manually close browser when finished)")

if __name__ == "__main__":
    main()
