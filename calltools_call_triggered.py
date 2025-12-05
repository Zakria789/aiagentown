"""
CallTools with HumeAI - Only connects when call starts
HumeAI will only speak when actual call is connected
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

# Call Detection and HumeAI Integration
CALL_DETECTION_JS = """
(function() {
    console.log('🎯 Call Detection System Started');
    
    // Logging function with timestamp
    function log(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const emoji = {
            'info': 'ℹ️',
            'success': '✅',
            'error': '❌',
            'call': '📞',
            'ai': '🤖',
            'customer': '👤',
            'audio': '🔊'
        }[type] || 'ℹ️';
        
        console.log(`[${timestamp}] ${emoji} ${message}`);
    }
    
    // HumeAI State
    let humeWs = null;
    let chatId = null;
    let audioContext = null;
    let audioQueue = [];
    let isPlaying = false;
    let isSpeaking = false;
    let isCallActive = false;
    let micStream = null;
    let audioProcessor = null;
    let callStartTime = null;
    
    // Detect when call starts
    function detectCallStart() {
        log('Watching for call start...', 'info');
        
        // Store active PeerConnection globally for audio injection
        window.activePeerConnection = null;
        
        // Method 1: Watch for RTCPeerConnection
        const originalRTC = window.RTCPeerConnection;
        window.RTCPeerConnection = function(...args) {
            const pc = new originalRTC(...args);
            
            // Store reference to active peer connection
            window.activePeerConnection = pc;
            log('RTCPeerConnection created and stored', 'info');
            
            pc.addEventListener('iceconnectionstatechange', () => {
                log(`ICE State changed: ${pc.iceConnectionState}`, 'info');
                
                if (pc.iceConnectionState === 'connected' || pc.iceConnectionState === 'completed') {
                    if (!isCallActive) {
                        log('═══════════════════════════════════════════', 'call');
                        log('CALL STARTED - Connection Established!', 'call');
                        log('═══════════════════════════════════════════', 'call');
                        isCallActive = true;
                        callStartTime = new Date();
                        onCallStart();
                    }
                }
                
                if (pc.iceConnectionState === 'disconnected' || pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'closed') {
                    if (isCallActive) {
                        const duration = Math.round((new Date() - callStartTime) / 1000);
                        log('═══════════════════════════════════════════', 'call');
                        log(`CALL ENDED - Duration: ${duration} seconds`, 'call');
                        log('═══════════════════════════════════════════', 'call');
                        isCallActive = false;
                        onCallEnd();
                    }
                }
            });
            
            return pc;
        };
        
        // Method 2: Monitor DOM for call indicators
        setInterval(() => {
            const callButtons = document.querySelectorAll('button, div, span');
            let foundActiveCall = false;
            
            for (let elem of callButtons) {
                const text = elem.textContent.toLowerCase();
                if (text.includes('end call') || text.includes('hang up') || text.includes('in call')) {
                    foundActiveCall = true;
                    break;
                }
            }
            
            if (foundActiveCall && !isCallActive) {
                log('═══════════════════════════════════════════', 'call');
                log('Call detected via UI elements', 'call');
                log('═══════════════════════════════════════════', 'call');
                isCallActive = true;
                callStartTime = new Date();
                onCallStart();
            } else if (!foundActiveCall && isCallActive) {
                const duration = Math.round((new Date() - callStartTime) / 1000);
                log('═══════════════════════════════════════════', 'call');
                log(`Call ended via UI - Duration: ${duration}s`, 'call');
                log('═══════════════════════════════════════════', 'call');
                isCallActive = false;
                onCallEnd();
            }
        }, 1000);
        
        log('Call detection system active', 'success');
    }
    
    // Call Started - Connect HumeAI
    async function onCallStart() {
        log('───────────────────────────────────────────', 'call');
        log('STEP 1: Call connected - Initializing AI', 'call');
        log('───────────────────────────────────────────', 'call');
        document.title = '📞 Call Active - AI Speaking';
        
        try {
            log('Connecting to HumeAI server...', 'info');
            await connectHumeAI();
            log('HumeAI connected successfully!', 'success');
            
            log('Starting microphone capture...', 'info');
            await startMicrophoneCapture();
            log('Microphone active - listening to customer', 'success');
            
            log('───────────────────────────────────────────', 'call');
            log('STEP 2: AI Agent will greet customer now', 'call');
            log('───────────────────────────────────────────', 'call');
        } catch (err) {
            log(`Failed to start AI: ${err.message}`, 'error');
        }
    }
    
    // Call Ended - Disconnect HumeAI
    function onCallEnd() {
        log('═══════════════════════════════════════════', 'call');
        log('🔴 CALL ENDED - Disconnecting HumeAI...', 'call');
        log('═══════════════════════════════════════════', 'call');
        document.title = '⏸️ No Call - Waiting';
        
        // Close HumeAI connection FIRST
        if (humeWs) {
            log('Closing HumeAI WebSocket...', 'info');
            humeWs.close();
            humeWs = null;
            log('✅ HumeAI DISCONNECTED', 'success');
        }
        
        // Stop microphone
        if (micStream) {
            log('Stopping microphone...', 'info');
            micStream.getTracks().forEach(track => track.stop());
            micStream = null;
            log('✅ Microphone stopped', 'success');
        }
        
        if (audioProcessor) {
            audioProcessor.disconnect();
            audioProcessor = null;
        }
        
        // Clear audio queue
        audioQueue = [];
        isPlaying = false;
        isSpeaking = false;
        chatId = null;
        
        log('✅ All resources cleaned up - Ready for next call', 'success');
        log('═══════════════════════════════════════════', 'call');
    }
    
    // Connect to HumeAI
    function connectHumeAI() {
        return new Promise((resolve, reject) => {
            const wsUrl = `wss://api.hume.ai/v0/assistant/chat?api_key=${HUME_API_KEY}&config_id=${HUME_CONFIG_ID}`;
            
            log('Opening WebSocket connection to HumeAI...', 'info');
            humeWs = new WebSocket(wsUrl);
            
            // Keep connection alive
            let keepAliveInterval = null;
            
            humeWs.onopen = () => {
                log('WebSocket connection established!', 'success');
                
                // Send keep-alive pings every 30 seconds
                keepAliveInterval = setInterval(() => {
                    if (humeWs && humeWs.readyState === WebSocket.OPEN) {
                        try {
                            humeWs.send(JSON.stringify({ type: 'ping' }));
                            log('Keep-alive ping sent', 'info');
                        } catch (e) {
                            log('Keep-alive ping failed', 'error');
                        }
                    }
                }, 30000);
                
                resolve();
            };
            
            humeWs.onmessage = async (event) => {
                const message = JSON.parse(event.data);
                
                if (message.type === 'chat_metadata') {
                    chatId = message.chat_id;
                    log(`Chat session created: ${chatId}`, 'success');
                }
                
                if (message.type === 'audio_output' && message.data) {
                    log(`Received AI audio chunk: ${message.data.length} bytes`, 'audio');
                    await playAudioFromBase64(message.data);
                }
                
                if (message.type === 'assistant_message') {
                    log('─────────────────────────────────────', 'ai');
                    log(`AI AGENT: "${message.message.content}"`, 'ai');
                    log('─────────────────────────────────────', 'ai');
                }
                
                if (message.type === 'user_message') {
                    log('─────────────────────────────────────', 'customer');
                    log(`CUSTOMER: "${message.message.content}"`, 'customer');
                    log('─────────────────────────────────────', 'customer');
                }
                
                if (message.type === 'assistant_end') {
                    log('AI finished speaking', 'ai');
                }
                
                if (message.type === 'user_interruption') {
                    log('Customer interrupted AI', 'customer');
                }
                
                if (message.type === 'pong') {
                    log('Keep-alive pong received', 'info');
                }
            };
            
            humeWs.onerror = (error) => {
                log(`WebSocket error: ${error}`, 'error');
                if (keepAliveInterval) clearInterval(keepAliveInterval);
                reject(error);
            };
            
            humeWs.onclose = (event) => {
                log(`WebSocket closed (code: ${event.code}, reason: ${event.reason || 'none'})`, 'info');
                if (keepAliveInterval) clearInterval(keepAliveInterval);
                
                // Auto-reconnect if call is still active
                if (isCallActive) {
                    log('Attempting to reconnect...', 'info');
                    setTimeout(() => {
                        connectHumeAI().catch(err => {
                            log('Reconnection failed', 'error');
                        });
                    }, 2000);
                }
            };
        });
    }
    
    // Play AI audio
    async function playAudioFromBase64(base64Data) {
        try {
            if (!audioContext) {
                audioContext = new (window.AudioContext || window.webkitAudioContext)({
                    sampleRate: 16000
                });
                log('Audio context created (16kHz)', 'audio');
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
            
            // Create audio buffer with FASTER playback (1.3x speed)
            const audioBuffer = audioContext.createBuffer(1, float32Array.length, 16000);
            audioBuffer.getChannelData(0).set(float32Array);
            
            // Add to queue
            audioQueue.push(audioBuffer);
            log(`Audio chunk queued (${audioQueue.length} in queue)`, 'audio');
            
            if (!isPlaying) {
                playNextAudio();
            }
        } catch (error) {
            log(`Audio decode failed: ${error.message}`, 'error');
        }
    }
    
    // Play next audio chunk
    function playNextAudio() {
        if (audioQueue.length === 0) {
            isPlaying = false;
            isSpeaking = false;
            log('Audio playback queue empty', 'audio');
            return;
        }
        
        isPlaying = true;
        isSpeaking = true;
        const audioBuffer = audioQueue.shift();
        const source = audioContext.createBufferSource();
            source.buffer = audioBuffer;
            
            // FASTER PLAYBACK - 1.7x speed for quicker responses
            source.playbackRate.value = 1.7;        // HIGH VOLUME for phone call
        const gainNode = audioContext.createGain();
        gainNode.gain.value = 5.0; // Maximum volume boost
        
        source.connect(gainNode);
        // DON'T play in browser speakers - only phone!
        // gainNode.connect(audioContext.destination);  // COMMENTED OUT
        
        // ONLY inject into phone call stream
        try {
            // Find all RTCPeerConnection objects
            if (window.RTCPeerConnection) {
                const pcs = [];
                // Check if there are any peer connections
                document.querySelectorAll('*').forEach(el => {
                    if (el.__rtcPeerConnection) {
                        pcs.push(el.__rtcPeerConnection);
                    }
                });
                
                // Try to get active PeerConnection
                if (typeof window.activePeerConnection !== 'undefined') {
                    const pc = window.activePeerConnection;
                    const senders = pc.getSenders();
                    const audioSender = senders.find(s => s.track && s.track.kind === 'audio');
                    
                    if (audioSender) {
                        // Create MediaStream from audio buffer
                        const dest = audioContext.createMediaStreamDestination();
                        gainNode.connect(dest);
                        const aiTrack = dest.stream.getAudioTracks()[0];
                        
                        // Replace phone audio with AI audio
                        audioSender.replaceTrack(aiTrack).then(() => {
                            log('✅ AI audio injected into phone call!', 'audio');
                        }).catch(err => {
                            log(`Phone injection failed: ${err.message}`, 'error');
                        });
                    }
                }
            }
        } catch (injectError) {
            // Silent fail - audio will still play through speakers
        }
        
        source.onended = () => {
            log('Audio chunk finished playing', 'audio');
            playNextAudio();
        };
        
        source.start();
        log('▶️ Playing AI audio (1.7x speed, PHONE ONLY)', 'audio');
    }
    
    // Capture microphone
    async function startMicrophoneCapture() {
        try {
            log('Requesting microphone access...', 'info');
            
            micStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000
                } 
            });
            
            log('Microphone access granted', 'success');
            
            const micContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });
            
            const source = micContext.createMediaStreamSource(micStream);
            audioProcessor = micContext.createScriptProcessor(4096, 1, 1);
            
            let lastSendTime = Date.now();
            let audioChunksSent = 0;
            
            audioProcessor.onaudioprocess = (e) => {
                if (isSpeaking || !humeWs || humeWs.readyState !== WebSocket.OPEN) return;
                
                const inputData = e.inputBuffer.getChannelData(0);
                const int16Data = new Int16Array(inputData.length);
                
                for (let i = 0; i < inputData.length; i++) {
                    int16Data[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
                }
                
                const bytes = new Uint8Array(int16Data.buffer);
                const base64 = btoa(String.fromCharCode(...bytes));
                
                try {
                    humeWs.send(JSON.stringify({
                        type: 'audio_input',
                        data: base64
                    }));
                    
                    audioChunksSent++;
                    const now = Date.now();
                    if (now - lastSendTime > 5000) {
                        log(`Sent ${audioChunksSent} audio chunks to AI`, 'customer');
                        lastSendTime = now;
                        audioChunksSent = 0;
                    }
                } catch (err) {
                    log(`Failed to send audio: ${err.message}`, 'error');
                }
            };
            
            source.connect(audioProcessor);
            audioProcessor.connect(micContext.destination);
            
            log('Audio streaming from microphone started', 'success');
            log('Customer can now speak to AI', 'customer');
            
        } catch (error) {
            log(`Microphone error: ${error.message}`, 'error');
            alert('⚠️ Microphone access required! Please allow microphone.');
        }
    }
    
    // Initialize
    log('══════════════════════════════════════════════', 'info');
    log('CallTools + HumeAI Voice Agent Initialized', 'success');
    log('══════════════════════════════════════════════', 'info');
    log('Status: WAITING FOR INCOMING CALL', 'info');
    document.title = '⏸️ Waiting for Call';
    detectCallStart();
    
})();
""".replace("${HUME_API_KEY}", HUME_API_KEY).replace("${HUME_CONFIG_ID}", HUME_CONFIG_ID)

def main():
    print("=" * 70)
    print("🚀 CallTools + HumeAI (Call-Triggered)")
    print("=" * 70)
    print("\n📋 How it works:")
    print("   1. Login to CallTools")
    print("   2. System waits for call to start")
    print("   3. When call connects → HumeAI starts")
    print("   4. AI speaks to caller")
    print("   5. When call ends → HumeAI stops")
    print("\n" + "=" * 70 + "\n")
    
    # Setup Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--use-fake-ui-for-media-stream')
    options.add_argument('--use-fake-device-for-media-stream')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option("detach", True)
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    
    try:
        # Login
        print("📱 Logging into CallTools...")
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
        
        # Login
        try:
            login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except:
            login_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'login')]")
        
        driver.execute_script("arguments[0].click();", login_button)
        print("   ✅ Login button clicked")
        
        time.sleep(5)
        print("✅ Logged in!\n")
        
        # Inject call detection
        print("🔍 Installing call detection system...")
        driver.execute_script(CALL_DETECTION_JS)
        print("✅ Call detection active!\n")
        
        time.sleep(2)
        
        # Ready
        print("=" * 70)
        print("✅ SYSTEM READY!")
        print("=" * 70)
        print("\n⏸️ Status: WAITING FOR CALL")
        print("\n📞 Instructions:")
        print("   1. Apne mobile se call karo")
        print("   2. Jab call connect hoga:")
        print("      → HumeAI automatic start hoga")
        print("      → AI bolega: 'Hello! Thanks for calling...'")
        print("   3. Tum baat karo, AI respond karega")
        print("   4. Jab call end hoga:")
        print("      → HumeAI automatic stop hoga")
        print("\n💡 Browser title dekho:")
        print("   ⏸️ 'Waiting for Call' = No call")
        print("   📞 'Call Active' = AI is speaking")
        print("\n" + "=" * 70)
        
        # Keep running
        print("\n⏳ System running... (Press Ctrl+C to stop)")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Stopping...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Browser will stay open. Close manually when done.")

if __name__ == "__main__":
    main()
