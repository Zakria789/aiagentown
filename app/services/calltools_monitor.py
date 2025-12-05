"""
CallTools WebRTC Monitor Service
Production-ready service for automatic call detection and HumeAI integration
Runs as background service without human interaction
"""
import asyncio
import json
import time
import uuid
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class CallToolsMonitorService:
    """
    Production service for automatic CallTools monitoring
    - Auto-login to CallTools
    - Auto-join campaign
    - Detect calls automatically
    - Trigger HumeAI voice agent
    - No human interaction required
    """
    
    def __init__(self, calltools_url: str, username: str, password: str):
        self.calltools_url = calltools_url
        self.username = username
        self.password = password
        self.driver: Optional[webdriver.Chrome] = None
        self.session_id = str(uuid.uuid4())
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None
        
    def setup_browser(self):
        """Setup visible Chrome with WebRTC permissions"""
        options = webdriver.ChromeOptions()
        
        # VISIBLE MODE - Browser window will be visible for testing
        # options.add_argument('--headless=new')  # COMMENTED OUT for visible browser
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--start-maximized')  # Start browser maximized
        
        # WebRTC permissions
        options.add_argument('--use-fake-ui-for-media-stream')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        # Media permissions
        prefs = {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        logger.info("✅ Browser setup complete (VISIBLE mode - window will be shown)")
    
    def login(self) -> bool:
        """Auto-login to CallTools"""
        try:
            logger.info(f"🌐 Connecting to CallTools: {self.calltools_url}")
            self.driver.get(self.calltools_url)
            
            wait = WebDriverWait(self.driver, 20)
            time.sleep(3)
            
            # Find username field
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
            username_field.send_keys(self.username)
            time.sleep(0.5)
            
            # Find password field
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(0.5)
            
            # Click login button
            login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            login_button.click()
            time.sleep(2)
            
            logger.info("✅ LOGIN SUCCESSFUL")
            
            # Auto-join campaign and set status
            time.sleep(3)
            self.join_campaign()
            time.sleep(2)
            self.set_status_available()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False
    
    def join_campaign(self) -> bool:
        """Auto-join campaign"""
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
                        logger.info("✅ Campaign joined automatically")
                        time.sleep(2)
                        return True
                except:
                    continue
                    
            logger.warning("⚠️ Campaign join button not found")
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Could not join campaign: {e}")
            return False
    
    def set_status_available(self) -> bool:
        """Auto-set status to Available"""
        try:
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
                        
                        # Select "Available"
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
                    
            logger.warning("⚠️ Could not set status to Available")
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Could not set status: {e}")
            return False
    
    def inject_audio_bridge_script(self):
        """Inject JavaScript for WebRTC monitoring and audio streaming"""
        
        # First, add a warning banner at the top of the page
        banner_script = """
        (function() {
            const banner = document.createElement('div');
            banner.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: linear-gradient(90deg, #ff6b6b, #ee5a6f);
                color: white;
                padding: 15px;
                text-align: center;
                font-size: 18px;
                font-weight: bold;
                z-index: 999999;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                border-bottom: 3px solid #c92a2a;
            `;
            banner.innerHTML = `
                🤖 AI AGENT MONITORING ACTIVE - DO NOT CLOSE THIS WINDOW! 🤖
                <div style="font-size: 14px; margin-top: 5px; font-weight: normal;">
                    Waiting for incoming calls... | CallTools Username: Al.Hassan
                </div>
            `;
            
            // Insert banner at the very top
            if (document.body) {
                document.body.insertBefore(banner, document.body.firstChild);
                
                // Add margin to avoid content overlap
                const style = document.createElement('style');
                style.textContent = 'body { padding-top: 80px !important; }';
                document.head.appendChild(style);
            }
        })();
        """
        
        self.driver.execute_script(banner_script)
        logger.info("✅ Warning banner added to browser")
        
        # Now inject the main audio bridge script
        js_code = """
        (function() {
            console.log('🔧 CallTools Audio Bridge Script Loading...');
            
            window.__callState = {
                active: false,
                peerConnections: [],
                audioTracks: [],
                audioContext: null,
                audioProcessor: null,
                ws: null,
                wsConnected: false,
                frameCount: 0
            };
            
            function connectWebSocket() {
                const ws = new WebSocket('ws://localhost:8000/ws/webrtc-audio');
                
                ws.onopen = () => {
                    console.log('✅ WebSocket connected to backend');
                    window.__callState.ws = ws;
                    window.__callState.wsConnected = true;
                    
                    ws.send(JSON.stringify({
                        type: 'init',
                        session_id: '%SESSION_ID%',
                        timestamp: Date.now()
                    }));
                };
                
                ws.onerror = (err) => {
                    console.error('❌ WebSocket error:', err);
                    window.__callState.wsConnected = false;
                };
                
                ws.onclose = () => {
                    console.warn('⚠️ WebSocket closed - reconnecting...');
                    window.__callState.wsConnected = false;
                    setTimeout(connectWebSocket, 3000);
                };
                
                ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'ready') {
                            console.log('✅ Bridge ready:', data.message);
                        } else if (data.type === 'audio_response') {
                            window.playAIAudio(data.data);
                        } else if (data.type === 'transcript') {
                            if (data.speaker === 'user') {
                                console.log('👤 Customer:', data.text);
                            } else if (data.speaker === 'assistant') {
                                console.log('🤖 Agent:', data.text);
                            }
                        }
                    } catch (error) {
                        console.error('❌ Error processing message:', error);
                    }
                };
                
                return ws;
            }
            
            connectWebSocket();
            
            // Intercept RTCPeerConnection
            const OriginalRTCPeerConnection = window.RTCPeerConnection || window.webkitRTCPeerConnection;
            
            window.RTCPeerConnection = function(...args) {
                const pc = new OriginalRTCPeerConnection(...args);
                window.__callState.peerConnections.push(pc);
                
                pc.addEventListener('track', (event) => {
                    if (event.track.kind === 'audio') {
                        window.__callState.audioTracks.push(event.track);
                        
                        if (!window.__callState.active) {
                            window.__callState.active = true;
                            console.log('📞 CALL STARTED - Auto-triggering HumeAI');
                            
                            if (window.__callState.ws && window.__callState.wsConnected) {
                                window.__callState.ws.send(JSON.stringify({
                                    type: 'call_start',
                                    timestamp: Date.now()
                                }));
                            }
                            
                            setTimeout(() => window.startAudioCapture(), 1000);
                        }
                    }
                });
                
                pc.addEventListener('connectionstatechange', () => {
                    if (pc.connectionState === 'connected' && !window.__callState.active) {
                        const receivers = pc.getReceivers();
                        receivers.forEach((receiver) => {
                            if (receiver.track && receiver.track.kind === 'audio') {
                                window.__callState.audioTracks.push(receiver.track);
                            }
                        });
                        
                        if (window.__callState.audioTracks.length > 0) {
                            window.__callState.active = true;
                            console.log('📞 CALL STARTED (manual detection)');
                            
                            if (window.__callState.ws && window.__callState.wsConnected) {
                                window.__callState.ws.send(JSON.stringify({
                                    type: 'call_start',
                                    timestamp: Date.now()
                                }));
                            }
                            
                            setTimeout(() => window.startAudioCapture(), 1000);
                        }
                    }
                    
                    if (pc.connectionState === 'disconnected' || pc.connectionState === 'closed') {
                        const anyActive = window.__callState.peerConnections.some(
                            p => p.connectionState === 'connected'
                        );
                        
                        if (!anyActive && window.__callState.active) {
                            window.__callState.active = false;
                            console.log('📴 CALL ENDED');
                            
                            if (window.__callState.ws && window.__callState.wsConnected) {
                                window.__callState.ws.send(JSON.stringify({
                                    type: 'call_end',
                                    timestamp: Date.now()
                                }));
                            }
                            
                            window.stopAudioCapture();
                        }
                    }
                });
                
                return pc;
            };
            
            window.RTCPeerConnection.prototype = OriginalRTCPeerConnection.prototype;
            
            window.startAudioCapture = async () => {
                try {
                    let activeTrack = null;
                    for (const track of window.__callState.audioTracks) {
                        if (track.readyState === 'live' && track.enabled) {
                            activeTrack = track;
                            break;
                        }
                    }
                    
                    if (!activeTrack) return false;
                    
                    const stream = new MediaStream([activeTrack]);
                    window.__callState.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                        sampleRate: 16000
                    });
                    
                    const source = window.__callState.audioContext.createMediaStreamSource(stream);
                    const analyser = window.__callState.audioContext.createAnalyser();
                    analyser.fftSize = 2048;
                    source.connect(analyser);
                    
                    const bufferLength = analyser.fftSize;
                    const dataArray = new Float32Array(bufferLength);
                    
                    console.log('✅ Audio capture started - using AnalyserNode polling');
                    console.log(`📊 Buffer size: ${bufferLength}, Sample rate: ${window.__callState.audioContext.sampleRate}`);
                    
                    // Poll audio data every 128ms (8 chunks per second)
                    let chunkCount = 0;
                    window.__callState.audioInterval = setInterval(() => {
                        if (!window.__callState.wsConnected || !window.__callState.active) return;
                        
                        analyser.getFloatTimeDomainData(dataArray);
                        
                        // Convert Float32 to Int16 PCM
                        const int16Data = new Int16Array(dataArray.length);
                        let maxAmplitude = 0;
                        for (let i = 0; i < dataArray.length; i++) {
                            const s = Math.max(-1, Math.min(1, dataArray[i]));
                            int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                            const amplitude = Math.abs(s);
                            if (amplitude > maxAmplitude) maxAmplitude = amplitude;
                        }
                        
                        // Log first few chunks for debugging
                        if (chunkCount < 5 || chunkCount % 20 === 0) {
                            console.log(`🎤 Chunk ${chunkCount}: amplitude = ${maxAmplitude.toFixed(4)}`);
                        }
                        
                        // Skip absolute silence
                        if (maxAmplitude < 0.0001) {
                            return;
                        }
                        
                        const base64Audio = btoa(String.fromCharCode.apply(null, new Uint8Array(int16Data.buffer)));
                        
                        if (window.__callState.ws.readyState === WebSocket.OPEN) {
                            window.__callState.ws.send(JSON.stringify({
                                type: 'audio_input',
                                data: base64Audio,
                                timestamp: Date.now()
                            }));
                            
                            chunkCount++;
                            window.__callState.frameCount++;
                            
                            if (chunkCount === 1) {
                                console.log('✅ FIRST AUDIO CHUNK SENT TO BACKEND!');
                            }
                        }
                    }, 128); // 128ms = ~8 chunks/sec = optimal for real-time
                    
                    console.log('✅ Audio polling active - streaming to HumeAI');
                    return true;
                    
                } catch (error) {
                    console.error('❌ Failed to capture audio:', error);
                    return false;
                }
            };
            
            window.stopAudioCapture = () => {
                try {
                    if (window.__callState.audioInterval) {
                        clearInterval(window.__callState.audioInterval);
                        window.__callState.audioInterval = null;
                        console.log('✅ Audio polling stopped');
                    }
                    
                    if (window.__callState.audioContext) {
                        window.__callState.audioContext.close();
                        window.__callState.audioContext = null;
                    }
                    
                    window.__callState.frameCount = 0;
                    console.log('✅ Audio capture stopped');
                } catch (error) {
                    console.error('❌ Error stopping audio:', error);
                }
            };
            
            window.playAIAudio = (base64Audio) => {
                try {
                    const activePc = window.__callState.peerConnections.find(
                        pc => pc.connectionState === 'connected'
                    );
                    
                    if (!activePc) {
                        console.warn('⚠️ No active PeerConnection');
                        return;
                    }
                    
                    const audioSender = activePc.getSenders().find(sender => 
                        sender.track && sender.track.kind === 'audio'
                    );
                    
                    if (!audioSender || !audioSender.track) {
                        console.warn('⚠️ No audio sender');
                        return;
                    }
                    
                    if (!window.__callState.audioContext) {
                        window.__callState.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                            sampleRate: 16000
                        });
                    }
                    
                    const binaryString = atob(base64Audio);
                    const len = binaryString.length;
                    const bytes = new Uint8Array(len);
                    for (let i = 0; i < len; i++) {
                        bytes[i] = binaryString.charCodeAt(i);
                    }
                    
                    const int16Array = new Int16Array(bytes.buffer);
                    const float32Array = new Float32Array(int16Array.length);
                    for (let i = 0; i < int16Array.length; i++) {
                        float32Array[i] = int16Array[i] / (int16Array[i] < 0 ? 0x8000 : 0x7FFF);
                    }
                    
                    const audioBuffer = window.__callState.audioContext.createBuffer(1, float32Array.length, 16000);
                    audioBuffer.getChannelData(0).set(float32Array);
                    
                    const source = window.__callState.audioContext.createBufferSource();
                    source.buffer = audioBuffer;
                    
                    const destination = window.__callState.audioContext.createMediaStreamDestination();
                    source.connect(destination);
                    
                    const originalTrack = audioSender.track;
                    const aiAudioTrack = destination.stream.getAudioTracks()[0];
                    
                    audioSender.replaceTrack(aiAudioTrack).then(() => {
                        console.log('✅ AI audio injected into call');
                        source.start();
                        
                        source.onended = () => {
                            audioSender.replaceTrack(originalTrack).then(() => {
                                console.log('✅ Restored original track');
                            });
                        };
                    });
                    
                } catch (error) {
                    console.error('❌ Failed to play AI audio:', error);
                }
            };
            
            console.log('✅ CallTools Audio Bridge Ready!');
            window.__audioBridgeReady = true;
            
        })();
        """.replace('%SESSION_ID%', self.session_id)
        
        self.driver.execute_script(js_code)
        logger.info("✅ Audio bridge script injected")
    
    def select_disposition(self, disposition_type: str = "Lead"):
        """
        Select disposition after call ends
        disposition_type options: Lead, Customer Hang Up, No Contact, Not Interested, etc.
        """
        try:
            logger.info(f"🎯 Selecting disposition: {disposition_type}")
            
            # Wait for disposition dialog to appear
            wait = WebDriverWait(self.driver, 10)
            
            # Look for disposition buttons
            disposition_script = f"""
                const buttons = Array.from(document.querySelectorAll('button'));
                const targetButton = buttons.find(btn => 
                    btn.textContent.includes('{disposition_type}')
                );
                if (targetButton) {{
                    targetButton.click();
                    return true;
                }}
                return false;
            """
            
            result = self.driver.execute_script(disposition_script)
            
            if result:
                logger.info(f"✅ Disposition '{disposition_type}' selected")
                return True
            else:
                logger.warning(f"⚠️ Disposition button '{disposition_type}' not found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to select disposition: {e}")
            return False
    
    def set_status_available(self):
        """Set agent status to Available for next call"""
        try:
            logger.info("🟢 Setting status to Available...")
            
            # Look for status dropdown/button
            status_script = """
                // Look for status selector
                const statusElements = document.querySelectorAll('[class*="status"], [id*="status"]');
                
                for (let elem of statusElements) {
                    if (elem.tagName === 'SELECT') {
                        // Dropdown
                        const options = Array.from(elem.options);
                        const availOption = options.find(opt => 
                            opt.text.includes('Available') || opt.value.includes('available')
                        );
                        if (availOption) {
                            elem.value = availOption.value;
                            elem.dispatchEvent(new Event('change'));
                            return 'dropdown';
                        }
                    }
                }
                
                // Look for Available button
                const buttons = Array.from(document.querySelectorAll('button'));
                const availButton = buttons.find(btn => 
                    btn.textContent.includes('Available') || 
                    btn.textContent.includes('Post Call')
                );
                if (availButton) {
                    availButton.click();
                    return 'button';
                }
                
                return null;
            """
            
            result = self.driver.execute_script(status_script)
            
            if result:
                logger.info(f"✅ Status set to Available (via {result})")
                return True
            else:
                logger.warning("⚠️ Status change element not found - may need manual update")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to set status: {e}")
            return False
    
    async def monitor_calls(self):
        """Monitor for call events automatically"""
        logger.info("👁️ Monitoring started - waiting for calls...")
        
        last_call_state = False
        
        while self.running:
            try:
                call_state = self.driver.execute_script("""
                    if (window.__callState) {
                        return {
                            active: window.__callState.active,
                            peerConnections: window.__callState.peerConnections.length,
                            audioTracks: window.__callState.audioTracks.length,
                            wsConnected: window.__callState.wsConnected,
                            frameCount: window.__callState.frameCount
                        };
                    }
                    return null;
                """)
                
                if call_state:
                    current_state = call_state['active']
                    
                    if current_state != last_call_state:
                        if current_state:
                            logger.info("="*60)
                            logger.info("📞 CALL DETECTED - Auto-triggering HumeAI")
                            logger.info(f"   PeerConnections: {call_state['peerConnections']}")
                            logger.info(f"   Audio Tracks: {call_state['audioTracks']}")
                            logger.info("="*60)
                        else:
                            logger.info("="*60)
                            logger.info("📴 CALL ENDED")
                            logger.info(f"   Total frames: {call_state['frameCount']}")
                            logger.info("="*60)
                            
                            # Send call_end event to WebSocket
                            try:
                                self.driver.execute_script("""
                                    if (window.__callState && window.__callState.ws && 
                                        window.__callState.ws.readyState === WebSocket.OPEN) {
                                        window.__callState.ws.send(JSON.stringify({
                                            type: 'call_end',
                                            timestamp: Date.now()
                                        }));
                                        console.log('📴 Call end event sent to backend');
                                    }
                                """)
                                logger.info("✅ Call end event sent to backend")
                            except Exception as e:
                                logger.error(f"Failed to send call_end event: {e}")
                            
                            # Wait for disposition dialog to appear
                            await asyncio.sleep(2)
                            
                            # Auto-select disposition (default: Lead)
                            # You can change this based on AI analysis
                            self.select_disposition("Lead")
                            
                            # Wait a moment then set status to Available
                            await asyncio.sleep(1)
                            self.set_status_available()
                        
                        last_call_state = current_state
                
                await asyncio.sleep(1)
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if browser was closed
                if "invalid session id" in error_msg.lower() or "session deleted" in error_msg.lower():
                    logger.warning("⚠️ Browser window was closed - stopping monitoring")
                    self.running = False
                    break
                
                logger.error(f"Error monitoring: {e}")
                await asyncio.sleep(1)
    
    async def start(self):
        """Start the monitoring service"""
        try:
            logger.info("🚀 Starting CallTools Monitor Service...")
            
            self.setup_browser()
            
            if not self.login():
                raise Exception("Login failed")
            
            time.sleep(2)
            self.inject_audio_bridge_script()
            
            logger.info("✅ Service started - ready for automatic call handling")
            
            self.running = True
            self.monitor_task = asyncio.create_task(self.monitor_calls())
            
        except Exception as e:
            logger.error(f"❌ Failed to start service: {e}")
            raise
    
    async def stop(self):
        """Stop the monitoring service"""
        logger.info("⏹️ Stopping CallTools Monitor Service...")
        
        self.running = False
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ Browser closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
        
        logger.info("✅ Service stopped")


# Global service instance
calltools_monitor: Optional[CallToolsMonitorService] = None


async def initialize_calltools_monitor(url: str, username: str, password: str):
    """Initialize and start the CallTools monitor service"""
    global calltools_monitor
    
    if calltools_monitor is None:
        calltools_monitor = CallToolsMonitorService(url, username, password)
        await calltools_monitor.start()
        logger.info("✅ CallTools Monitor Service initialized")
    
    return calltools_monitor


async def shutdown_calltools_monitor():
    """Shutdown the CallTools monitor service"""
    global calltools_monitor
    
    if calltools_monitor is not None:
        await calltools_monitor.stop()
        calltools_monitor = None
        logger.info("✅ CallTools Monitor Service shut down")
