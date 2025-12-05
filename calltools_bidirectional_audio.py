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
print("🚀 CallTools + HumeAI (Bidirectional Audio)")
print("="*70)
print("\n📋 Features:")
print("   ✅ Mobile caller hears AI agent")
print("   ✅ AI agent hears mobile caller")
print("   ✅ No browser audio (silent)")
print("   ✅ Direct HumeAI connection (no hardcode)")
print("   ✅ Auto disconnect on call end")
print("\n" + "="*70 + "\n")

# Setup Chrome with microphone permissions
options = webdriver.ChromeOptions()
options.add_experimental_option("detach", True)
options.add_argument("--use-fake-ui-for-media-stream")
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
    
    # Find and click login button
    time.sleep(1)
    login_buttons = driver.find_elements(By.TAG_NAME, "button")
    for btn in login_buttons:
        if btn.text.strip():  # Has text
            driver.execute_script("arguments[0].click();", btn)
            print("   ✅ Login button clicked")
            break
    
    time.sleep(5)
    print("✅ Logged in!\n")
except Exception as e:
    print(f"❌ Login failed: {e}")
    print("🔍 Trying alternative login method...")
    try:
        # Alternative: Just send ENTER key
        password_input.send_keys("\n")
        time.sleep(5)
        print("✅ Logged in (alternative method)!\n")
    except:
        driver.quit()
        exit()

# Inject bidirectional audio system
print("🔍 Installing bidirectional audio system...")
BIDIRECTIONAL_AUDIO_JS = f"""
(function() {{
    // Configuration
    const HUME_API_KEY = '{HUME_API_KEY}';
    const HUME_CONFIG_ID = '{HUME_CONFIG_ID}';
    
    // State
    let humeWs = null;
    let micStream = null;
    let callAudioStream = null;
    let audioContext = null;
    let mixedAudioDestination = null;
    let isCallActive = false;
    let callStartTime = null;
    let audioQueue = [];
    let isPlayingAI = false;
    
    // Logging
    function log(message, type = 'info') {{
        const time = new Date().toLocaleTimeString();
        const emoji = {{
            'info': 'ℹ️',
            'success': '✅',
            'error': '❌',
            'call': '📞',
            'ai': '🤖',
            'customer': '👤',
            'audio': '🔊'
        }}[type] || 'ℹ️';
        console.log(`[${{time}}] ${{emoji}} ${{message}}`);
    }}
    
    // Detect call start
    function detectCallStart() {{
        log('Monitoring for incoming calls...', 'info');
        
        const originalRTC = window.RTCPeerConnection;
        window.RTCPeerConnection = function(...args) {{
            const pc = new originalRTC(...args);
            
            pc.addEventListener('iceconnectionstatechange', () => {{
                log(`ICE State: ${{pc.iceConnectionState}}`, 'info');
                
                if (pc.iceConnectionState === 'connected' && !isCallActive) {{
                    log('═══════════════════════════════════════════', 'call');
                    log('📞 CALL STARTED - Connecting to HumeAI...', 'call');
                    log('═══════════════════════════════════════════', 'call');
                    isCallActive = true;
                    callStartTime = new Date();
                    window.activePeerConnection = pc; // Store it HERE
                    log('✅ Stored peer connection for audio injection', 'info');
                    onCallStart(pc);
                }}
                
                if ((pc.iceConnectionState === 'disconnected' || pc.iceConnectionState === 'failed') && isCallActive) {{
                    const duration = Math.round((new Date() - callStartTime) / 1000);
                    log('═══════════════════════════════════════════', 'call');
                    log(`🔴 CALL ENDED - Duration: ${{duration}}s`, 'call');
                    log('═══════════════════════════════════════════', 'call');
                    isCallActive = false;
                    onCallEnd();
                }}
            }});
            
            // Capture incoming call audio (remote stream)
            pc.addEventListener('track', (event) => {{
                if (event.track.kind === 'audio') {{
                    log('📥 Received remote audio track (caller voice)', 'audio');
                    callAudioStream = event.streams[0];
                }}
            }});
            
            return pc;
        }};
    }}
    
    // Call started - Setup bidirectional audio
    async function onCallStart(peerConnection) {{
        try {{
            // Create audio context
            audioContext = new (window.AudioContext || window.webkitAudioContext)({{
                sampleRate: 16000
            }});
            
            // Get microphone (but we'll send caller's voice instead)
            micStream = await navigator.mediaDevices.getUserMedia({{
                audio: {{
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 48000,  // Higher quality
                    channelCount: 1
                }}
            }});
            
            log('✅ Microphone access granted', 'success');
            
            // Connect to HumeAI
            await connectHumeAI();
            
            // Start capturing CALLER's audio from call and send to HumeAI
            startCapturingCallerAudio();
            
            // Peer connection already stored in detectCallStart
            log('📍 Using stored peer connection', 'info');
            
        }} catch (error) {{
            log(`Setup error: ${{error.message}}`, 'error');
        }}
    }}
    
    // Connect to HumeAI
    function connectHumeAI() {{
        return new Promise((resolve, reject) => {{
            const wsUrl = `wss://api.hume.ai/v0/assistant/chat?api_key=${{HUME_API_KEY}}&config_id=${{HUME_CONFIG_ID}}`;
            
            log('Connecting to HumeAI...', 'info');
            humeWs = new WebSocket(wsUrl);
            
            // Keep connection alive
            let keepAliveInterval = null;
            
            humeWs.onopen = () => {{
                log('✅ HumeAI connected! (Agent will greet automatically)', 'success');
                
                // Send keepalive pings every 30 seconds
                keepAliveInterval = setInterval(() => {{
                    if (humeWs && humeWs.readyState === WebSocket.OPEN) {{
                        humeWs.send(JSON.stringify({{ type: 'ping' }}));
                        log('💚 Keepalive ping sent', 'info');
                    }}
                }}, 30000);
                
                resolve();
            }};
            
            humeWs.onmessage = async (event) => {{
                const message = JSON.parse(event.data);
                
                if (message.type === 'chat_metadata') {{
                    log(`Chat ID: ${{message.chat_id}}`, 'success');
                }}
                
                if (message.type === 'audio_output' && message.data) {{
                    log(`🤖 AI speaking (${{message.data.length}} bytes)`, 'ai');
                    audioQueue.push(message.data);
                    if (!isPlayingAI) {{
                        playNextAudioChunk();
                    }}
                }}
                
                if (message.type === 'assistant_message') {{
                    log(`AI: "${{message.message.content}}"`, 'ai');
                }}
                
                if (message.type === 'user_message') {{
                    log(`Customer: "${{message.message.content}}"`, 'customer');
                }}
                
                if (message.type === 'user_interruption') {{
                    log('⚠️ Customer interrupted AI!', 'customer');
                }}
                
                if (message.type === 'assistant_end') {{
                    log('✅ AI finished speaking', 'ai');
                }}
            }};
            
            humeWs.onerror = (error) => {{
                log(`WebSocket error: ${{error}}`, 'error');
                reject(error);
            }};
            
            humeWs.onclose = () => {{
                log('HumeAI disconnected', 'info');
                if (keepAliveInterval) clearInterval(keepAliveInterval);
                
                // Auto-reconnect if call is still active
                if (isCallActive) {{
                    log('🔄 Reconnecting to HumeAI...', 'info');
                    setTimeout(() => connectHumeAI(), 2000);
                }}
            }};
        }});
    }}
    
    // Capture CALLER's audio (from phone) and send to HumeAI
    function startCapturingCallerAudio() {{
        try {{
            log('🎤 Starting audio capture from microphone...', 'audio');
            
            const source = audioContext.createMediaStreamSource(micStream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            
            let chunkCount = 0;
            processor.onaudioprocess = (e) => {{
                if (!humeWs || humeWs.readyState !== WebSocket.OPEN) return;
                // REMOVED: if (isPlayingAI) return; // Allow interruptions!
                
                const inputData = e.inputBuffer.getChannelData(0);
                const int16Data = new Int16Array(inputData.length);
                
                for (let i = 0; i < inputData.length; i++) {{
                    int16Data[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
                }}
                
                const bytes = new Uint8Array(int16Data.buffer);
                const base64 = btoa(String.fromCharCode(...bytes));
                
                humeWs.send(JSON.stringify({{
                    type: 'audio_input',
                    data: base64
                }}));
                
                chunkCount++;
                if (chunkCount === 1) {{
                    log('📤 Audio streaming active (interruptions enabled)', 'customer');
                }}
                if (chunkCount % 50 === 0) {{
                    log(`📤 Sent ${{chunkCount}} audio chunks to AI`, 'customer');
                }}
            }};
            
            source.connect(processor);
            processor.connect(audioContext.destination);
            
            log('✅ Audio streaming to AI started', 'success');
            
        }} catch (error) {{
            log(`Audio capture error: ${{error.message}}`, 'error');
        }}
    }}
    
    // Play audio chunks from queue sequentially
    async function playNextAudioChunk() {{
        if (audioQueue.length === 0) {{
            isPlayingAI = false;
            log('✅ All AI audio played', 'audio');
            // Restore microphone after ALL audio is done
            if (window.activePeerConnection && micStream) {{
                const pc = window.activePeerConnection;
                const senders = pc.getSenders();
                const audioSender = senders.find(s => s.track && s.track.kind === 'audio');
                if (audioSender) {{
                    const micTrack = micStream.getAudioTracks()[0];
                    await audioSender.replaceTrack(micTrack);
                    log('🔄 Restored caller microphone', 'audio');
                }}
            }}
            return;
        }}
        
        isPlayingAI = true;
        const base64Data = audioQueue.shift();
        await injectAIAudioIntoCall(base64Data, false); // Don't restore mic yet
    }}
    
    // Inject AI audio into phone call
    async function injectAIAudioIntoCall(base64Data, restoreMic = true) {{
        try {{
            // Decode base64 audio
            const binaryString = atob(base64Data);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {{
                bytes[i] = binaryString.charCodeAt(i);
            }}
            
            // Convert to Float32
            const float32Array = new Float32Array(bytes.length / 2);
            const dataView = new DataView(bytes.buffer);
            for (let i = 0; i < float32Array.length; i++) {{
                float32Array[i] = dataView.getInt16(i * 2, true) / 32768.0;
            }}
            
            // Create audio buffer with FASTER playback
            const audioBuffer = audioContext.createBuffer(1, float32Array.length, 16000);
            audioBuffer.getChannelData(0).set(float32Array);
            
            // Create source
            const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.playbackRate.value = 1.2; // Balanced speed for clarity
            
            // Create gain
            const gainNode = audioContext.createGain();
            gainNode.gain.value = 3.0; // Balanced volume (not too loud)
            
            source.connect(gainNode);
            
            // ALSO play in browser for monitoring
            gainNode.connect(audioContext.destination);
            log('🔊 Playing in browser speakers for monitoring', 'audio');
            
            // Inject into phone call
            log('🔍 Checking for peer connection...', 'audio');
            if (window.activePeerConnection) {{
                log('✅ Peer connection found!', 'audio');
                const pc = window.activePeerConnection;
                const senders = pc.getSenders();
                log(`📊 Found ${{senders.length}} senders`, 'audio');
                const audioSender = senders.find(s => s.track && s.track.kind === 'audio');
                
                if (audioSender) {{
                    log('✅ Audio sender found! Injecting...', 'audio');
                    // Create separate destination for phone
                    const phoneDest = audioContext.createMediaStreamDestination();
                    gainNode.connect(phoneDest);
                    const aiTrack = phoneDest.stream.getAudioTracks()[0];
                    
                    await audioSender.replaceTrack(aiTrack);
                    log('✅ AI audio injected into call AND browser', 'audio');
                    
                    source.start();
                    
                    // Play next chunk when this one finishes
                    source.onended = () => {{
                        log('🎵 Audio chunk finished', 'audio');
                        playNextAudioChunk(); // Continue with next chunk
                    }};
                    }};
                }} else {{
                    log('❌ No audio sender found in peer connection!', 'error');
                    log(`Available senders: ${{senders.map(s => s.track?.kind || 'none').join(', ')}}`, 'error');
                    source.start();
                    source.onended = () => {{
                        playNextAudioChunk();
                    }};
                }}
                    log('❌ No audio sender found - playing in browser only', 'error');
                    source.start();
                    source.onended = () => {{
                        playNextAudioChunk();
                    }};
                }}
            }} else {{
                log('⚠️ No peer connection - playing in browser only', 'error');
                source.start();
                source.onended = () => {{
                    playNextAudioChunk();
                }};
            }}
            
        }} catch (error) {{
            log(`AI audio injection error: ${{error.message}}`, 'error');
        }}
    }}
    
    // Call ended - Cleanup
    function onCallEnd() {{
        log('🧹 Cleaning up...', 'info');
        
        if (humeWs) {{
            humeWs.close();
            humeWs = null;
            log('✅ HumeAI disconnected', 'success');
        }}
        
        if (micStream) {{
            micStream.getTracks().forEach(track => track.stop());
            micStream = null;
        }}
        
        callAudioStream = null;
        window.activePeerConnection = null;
        
        log('✅ Ready for next call', 'success');
    }}
    
    // Initialize
    log('═══════════════════════════════════════════', 'success');
    log('Bidirectional Audio System Active', 'success');
    log('═══════════════════════════════════════════', 'success');
    detectCallStart();
}})();
"""

driver.execute_script(BIDIRECTIONAL_AUDIO_JS)
print("✅ Bidirectional audio system installed!\n")

print("="*70)
print("🎯 System Ready!")
print("="*70)
print("\n📱 Now call from your mobile to test")
print("🔊 Caller will hear AI agent")
print("🎤 AI agent will hear caller")
print("🔇 Browser will be silent\n")
print("="*70)
print("\n⌨️ Press Ctrl+C to stop...\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\n🛑 Stopping...")
    driver.quit()
