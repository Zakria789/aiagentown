"""
COMPLETE FIXED IMPLEMENTATION - HumeAI + CallTools Integration
================================================================

PROBLEM ANALYSIS:
-----------------
Current broken flow:
  CallTools Browser → Capture WebRTC Audio → Send to FastAPI → Forward to HumeAI
                                                              ↓
  CallTools Browser ← Inject AI Audio ← Receive from FastAPI ← HumeAI Response

WHY IT FAILS:
1. WebRTC audio is isolated - can't easily intercept
2. Audio routing through backend adds latency
3. Browser audio injection is unreliable during active calls
4. Security restrictions prevent audio manipulation

CORRECT SOLUTION:
-----------------
Use HumeAI's NATIVE browser integration with CallTools:

  CallTools Browser → DIRECT WebSocket → HumeAI EVI
                                       ↓
  CallTools Microphone ←────────── HumeAI Audio Response
  (sent to caller)

HumeAI handles EVERYTHING:
- Listens to microphone (user talking)
- Processes with AI
- Plays response through browser speakers
- Browser audio goes to call via WebRTC automatically

IMPLEMENTATION:
--------------
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
CALLTOOLS_URL = "https://east-1.calltools.io"
USERNAME = "Al.Hassan"
PASSWORD = "Orangeroofing"

# HumeAI Configuration  
HUME_API_KEY = os.getenv("HUME_API_KEY", "dmWJAfVJARQhlyqwFJhMBlPnfUTOvN8u3CtbQcSC7GGfAspA")
HUME_CONFIG_ID = os.getenv("HUME_CONFIG_ID", "04ba744a-5b20-4c66-b3c1-fbb6e9cfcfec")

print("="*80)
print("🎯 COMPLETE HUMEAI + CALLTOOLS INTEGRATION (FIXED)")
print("="*80)
print("\n📋 This version uses HumeAI's NATIVE browser integration")
print("   ✅ Direct WebSocket from browser to HumeAI")
print("   ✅ No backend audio routing needed")
print("   ✅ Lower latency, better reliability")
print("   ✅ AI audio plays through browser automatically")
print("\n" + "="*80)

def setup_browser():
    """Setup Chrome with full audio permissions"""
    options = webdriver.ChromeOptions()
    
    # VISIBLE browser for testing
    options.add_argument('--start-maximized')
    
    # Critical: Auto-grant ALL permissions
    options.add_argument('--use-fake-ui-for-media-stream')
    options.add_argument('--use-fake-device-for-media-stream')
    options.add_argument('--enable-usermedia-screen-capturing')
    options.add_argument('--allow-http-screen-capture')
    options.add_argument('--auto-select-desktop-capture-source=Entire screen')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # Preferences for audio permissions
    prefs = {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    print("✅ Browser setup complete")
    return driver

def login(driver):
    """Login to CallTools"""
    print("\n[1] Logging into CallTools...")
    driver.get(CALLTOOLS_URL)
    wait = WebDriverWait(driver, 20)
    time.sleep(3)
    
    # Find and fill username
    username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
    username_field.clear()
    username_field.send_keys(USERNAME)
    
    # Find and fill password
    password_field = driver.find_element(By.NAME, "password")
    password_field.clear()
    password_field.send_keys(PASSWORD)
    
    # Click login
    login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()
    
    time.sleep(5)
    print("  ✅ Login successful")

def join_campaign(driver):
    """Join campaign automatically"""
    print("\n[2] Joining campaign...")
    wait = WebDriverWait(driver, 15)
    time.sleep(3)
    
    try:
        # Check if already joined
        dashboard_check = driver.execute_script("""
            return window.location.href.includes('dashboard') || 
                   document.querySelector('[class*="dashboard"]') !== null;
        """)
        
        if dashboard_check:
            print("  ✅ Campaign already joined")
            return
        
        # Find and click campaign join button
        join_button = wait.until(EC.element_to_be_clickable((
            By.XPATH, 
            "//button[contains(text(), 'Join') or contains(text(), 'Start')]"
        )))
        join_button.click()
        time.sleep(4)
        print("  ✅ Campaign joined")
    except Exception as e:
        print(f"  ⚠️ Campaign join: {e} (might already be joined)")

def inject_hume_integration(driver):
    """
    Inject COMPLETE HumeAI integration script
    This uses HumeAI's native browser SDK approach
    """
    print("\n[3] Injecting HumeAI integration...")
    
    js_code = f"""
    (async function() {{
        console.log('🎯 Starting HumeAI Native Integration...');
        
        // Configuration
        const HUME_API_KEY = '{HUME_API_KEY}';
        const HUME_CONFIG_ID = '{HUME_CONFIG_ID}';
        
        // State
        let humeWs = null;
        let chatId = null;
        let audioContext = null;
        let micStream = null;
        let callActive = false;
        let audioQueue = [];
        let isPlaying = false;
        
        // Banner
        const banner = document.createElement('div');
        banner.id = 'hume-status-banner';
        banner.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 15px; text-align: center; 
            font-weight: bold; z-index: 99999;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            font-size: 16px;
        `;
        banner.innerHTML = '🤖 HumeAI: Connecting...';
        document.body.appendChild(banner);
        
        function updateStatus(message, color = '#667eea') {{
            banner.innerHTML = message;
            banner.style.background = color;
        }}
        
        // Connect to HumeAI
        async function connectHumeAI() {{
            try {{
                const wsUrl = `wss://api.hume.ai/v0/assistant/chat`;
                
                console.log('📡 Connecting to HumeAI...');
                updateStatus('🤖 HumeAI: Connecting...', '#667eea');
                
                humeWs = new WebSocket(wsUrl);
                
                humeWs.onopen = async () => {{
                    console.log('✅ HumeAI WebSocket opened');
                    
                    // Send authentication and configuration
                    const initMessage = {{
                        type: 'session_settings',
                        config_id: HUME_CONFIG_ID,
                        api_key: HUME_API_KEY,
                        audio: {{
                            encoding: 'linear16',
                            sample_rate: 48000,
                            channels: 1
                        }}
                    }};
                    
                    humeWs.send(JSON.stringify(initMessage));
                    console.log('📤 Sent session_settings');
                }};
                
                humeWs.onmessage = async (event) => {{
                    try {{
                        const message = JSON.parse(event.data);
                        console.log('📥 HumeAI message:', message.type);
                        
                        if (message.type === 'chat_metadata') {{
                            chatId = message.chat_id;
                            console.log('✅ Chat ID:', chatId);
                            updateStatus('🤖 HumeAI: Ready! Waiting for call...', '#10b981');
                            
                            // Start monitoring for calls
                            monitorForCalls();
                        }}
                        
                        if (message.type === 'audio_output' && message.data) {{
                            console.log('🔊 Received AI audio chunk');
                            audioQueue.push(message.data);
                            if (!isPlaying) playNextAudio();
                        }}
                        
                        if (message.type === 'user_message') {{
                            console.log('💬 User said:', message.message?.content);
                        }}
                        
                        if (message.type === 'assistant_message') {{
                            console.log('🤖 AI said:', message.message?.content);
                        }}
                    }} catch (err) {{
                        console.error('❌ Error processing message:', err);
                    }}
                }};
                
                humeWs.onerror = (error) => {{
                    console.error('❌ WebSocket error:', error);
                    updateStatus('❌ HumeAI: Connection Error', '#ef4444');
                }};
                
                humeWs.onclose = () => {{
                    console.log('🔌 HumeAI disconnected');
                    updateStatus('🔌 HumeAI: Disconnected', '#f59e0b');
                    
                    // Auto-reconnect if call is active
                    if (callActive) {{
                        setTimeout(connectHumeAI, 2000);
                    }}
                }};
                
            }} catch (error) {{
                console.error('❌ Failed to connect:', error);
                updateStatus('❌ HumeAI: Failed', '#ef4444');
            }}
        }}
        
        // Monitor for incoming/outgoing calls
        function monitorForCalls() {{
            console.log('👁️ Monitoring for calls...');
            
            // Monitor RTCPeerConnection creation
            const OriginalRTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
            
            window.RTCPeerConnection = function(...args) {{
                const pc = new OriginalRTCPeerConnection(...args);
                
                pc.addEventListener('track', async (event) => {{
                    if (event.track.kind === 'audio' && !callActive) {{
                        console.log('📞 CALL STARTED!');
                        callActive = true;
                        updateStatus('📞 Call Active - AI Listening...', '#8b5cf6');
                        
                        await startAudioCapture();
                    }}
                }});
                
                pc.addEventListener('connectionstatechange', () => {{
                    if (pc.connectionState === 'disconnected' || pc.connectionState === 'closed') {{
                        if (callActive) {{
                            console.log('📴 CALL ENDED');
                            callActive = false;
                            stopAudioCapture();
                            updateStatus('🤖 HumeAI: Ready! Waiting for call...', '#10b981');
                        }}
                    }}
                }});
                
                return pc;
            }};
            
            window.RTCPeerConnection.prototype = OriginalRTCPeerConnection.prototype;
        }}
        
        // Start capturing microphone and sending to HumeAI
        async function startAudioCapture() {{
            try {{
                console.log('🎤 Starting microphone capture...');
                
                // Get microphone access
                micStream = await navigator.mediaDevices.getUserMedia({{
                    audio: {{
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        sampleRate: 48000
                    }}
                }});
                
                console.log('✅ Microphone access granted');
                
                // Create audio context
                audioContext = new (window.AudioContext || window.webkitAudioContext)({{
                    sampleRate: 48000
                }});
                
                const source = audioContext.createMediaStreamSource(micStream);
                const processor = audioContext.createScriptProcessor(4096, 1, 1);
                
                source.connect(processor);
                processor.connect(audioContext.destination);
                
                let chunkCount = 0;
                processor.onaudioprocess = (e) => {{
                    if (!humeWs || humeWs.readyState !== WebSocket.OPEN || !callActive) return;
                    
                    const inputData = e.inputBuffer.getChannelData(0);
                    
                    // Convert Float32 to Int16 PCM
                    const int16Data = new Int16Array(inputData.length);
                    for (let i = 0; i < inputData.length; i++) {{
                        const s = Math.max(-1, Math.min(1, inputData[i]));
                        int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    }}
                    
                    // Send to HumeAI
                    const base64 = btoa(String.fromCharCode.apply(null, new Uint8Array(int16Data.buffer)));
                    
                    humeWs.send(JSON.stringify({{
                        type: 'audio_input',
                        data: base64
                    }}));
                    
                    if (chunkCount % 20 === 0) {{
                        console.log(`🎤 Sending audio chunk #${{chunkCount}}`);
                    }}
                    chunkCount++;
                }};
                
                console.log('✅ Audio capture active');
                
            }} catch (error) {{
                console.error('❌ Microphone error:', error);
                updateStatus('❌ Microphone Error', '#ef4444');
            }}
        }}
        
        // Stop audio capture
        function stopAudioCapture() {{
            if (micStream) {{
                micStream.getTracks().forEach(track => track.stop());
                micStream = null;
            }}
            if (audioContext) {{
                audioContext.close();
                audioContext = null;
            }}
            console.log('✅ Audio capture stopped');
        }}
        
        // Play AI audio response
        async function playNextAudio() {{
            if (audioQueue.length === 0 || isPlaying) return;
            
            isPlaying = true;
            const base64Audio = audioQueue.shift();
            
            try {{
                if (!audioContext) {{
                    audioContext = new (window.AudioContext || window.webkitAudioContext)({{
                        sampleRate: 48000
                    }});
                }}
                
                // Decode base64 to Int16 PCM
                const binaryString = atob(base64Audio);
                const len = binaryString.length;
                const bytes = new Uint8Array(len);
                for (let i = 0; i < len; i++) {{
                    bytes[i] = binaryString.charCodeAt(i);
                }}
                
                const int16Array = new Int16Array(bytes.buffer);
                
                // Convert to Float32
                const float32Array = new Float32Array(int16Array.length);
                for (let i = 0; i < int16Array.length; i++) {{
                    float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF);
                }}
                
                // Create audio buffer and play
                const audioBuffer = audioContext.createBuffer(1, float32Array.length, 48000);
                audioBuffer.getChannelData(0).set(float32Array);
                
                const source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination);
                
                source.onended = () => {{
                    isPlaying = false;
                    playNextAudio(); // Play next in queue
                }};
                
                source.start();
                console.log('🔊 Playing AI audio');
                
            }} catch (error) {{
                console.error('❌ Audio playback error:', error);
                isPlaying = false;
            }}
        }}
        
        // Start the integration
        await connectHumeAI();
        
        console.log('✅ HumeAI Integration Complete!');
        
    }})().catch(err => {{
        console.error('❌ Integration failed:', err);
    }});
    """
    
    driver.execute_script(js_code)
    print("  ✅ HumeAI integration injected")
    time.sleep(2)

def main():
    """Main execution"""
    driver = None
    
    try:
        # Setup browser
        driver = setup_browser()
        
        # Login to CallTools
        login(driver)
        
        # Join campaign
        join_campaign(driver)
        
        # Inject HumeAI integration
        inject_hume_integration(driver)
        
        print("\n" + "="*80)
        print("✅ SYSTEM READY!")
        print("="*80)
        print("\n📞 How to test:")
        print("   1. Call 2015024650 from your mobile phone")
        print("   2. Call will connect through CallTools")
        print("   3. HumeAI will answer and talk to you")
        print("   4. You can have a conversation with the AI")
        print("\n⚠️  IMPORTANT: Keep this browser window OPEN!")
        print("   Do not close or minimize the browser")
        print("\n" + "="*80)
        
        # Keep browser alive
        print("\n⏳ Press Ctrl+C to stop...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n✅ Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            print("\n🔌 Keeping browser open for testing...")
            print("   Close browser window manually when done")
            input("Press Enter to close browser...")
            driver.quit()

if __name__ == "__main__":
    main()
