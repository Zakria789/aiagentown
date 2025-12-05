"""
Quick Fix - Inject to Running Browser
Open browser console (F12) and paste the JavaScript from this file
"""

print("""
╔════════════════════════════════════════════════════╗
║  Quick Audio Bridge Fix                            ║
║  Browser me F12 press karo aur Console me paste    ║
╚════════════════════════════════════════════════════╝

Copy this JavaScript and paste in browser console:
""")

print("""
(function() {
    console.clear();
    console.log('🚀 QUICK AUDIO BRIDGE STARTING...');
    
    // Backend WebSocket
    const ws = new WebSocket('ws://localhost:8000/ws/webrtc-audio');
    
    ws.onopen = async () => {
        console.log('✅ WebSocket connected to backend');
        
        // Init message
        ws.send(JSON.stringify({
            type: 'init',
            session_id: 'manual_test_' + Date.now()
        }));
        
        // Get microphone immediately
        try {
            console.log('🎤 Requesting microphone...');
            
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000
                }
            });
            
            console.log('✅ Microphone granted!');
            
            // Create audio context
            const audioCtx = new AudioContext({ sampleRate: 16000 });
            const source = audioCtx.createMediaStreamSource(stream);
            const processor = audioCtx.createScriptProcessor(4096, 1, 1);
            
            let counter = 0;
            processor.onaudioprocess = (e) => {
                if (ws.readyState === WebSocket.OPEN) {
                    const input = e.inputBuffer.getChannelData(0);
                    
                    // Convert to int16
                    const int16 = new Int16Array(input.length);
                    for (let i = 0; i < input.length; i++) {
                        const s = Math.max(-1, Math.min(1, input[i]));
                        int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    }
                    
                    // Send to backend
                    const bytes = new Uint8Array(int16.buffer);
                    const base64 = btoa(String.fromCharCode(...bytes));
                    
                    ws.send(JSON.stringify({
                        type: 'audio',
                        data: base64
                    }));
                    
                    if (++counter % 50 === 0) {
                        console.log('📡 Streaming... chunk', counter);
                    }
                }
            };
            
            source.connect(processor);
            processor.connect(audioCtx.destination);
            
            console.log('');
            console.log('════════════════════════════════════════');
            console.log('✅ AUDIO BRIDGE ACTIVE!');
            console.log('🎤 Microphone is capturing');
            console.log('📡 Streaming to backend');
            console.log('🤖 HumeAI should respond');
            console.log('════════════════════════════════════════');
            console.log('');
            
            // Green border indicator
            document.body.style.border = '5px solid #00ff00';
            
            // Add indicator
            const indicator = document.createElement('div');
            indicator.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                background: #00ff00;
                color: black;
                padding: 15px 25px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 16px;
                z-index: 999999;
                box-shadow: 0 4px 15px rgba(0,255,0,0.5);
                animation: pulse 2s infinite;
            `;
            indicator.innerHTML = '🎤 AUDIO ACTIVE';
            document.body.appendChild(indicator);
            
            // Add CSS animation
            const style = document.createElement('style');
            style.textContent = `
                @keyframes pulse {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                }
            `;
            document.head.appendChild(style);
            
        } catch (error) {
            console.error('❌ Microphone error:', error);
            alert('Please allow microphone access!');
        }
    };
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            console.log('📥 Backend:', data.type);
            
            if (data.type === 'audio_response') {
                console.log('🔊 AI response received');
                // Play audio
                const binary = atob(data.data);
                const bytes = new Uint8Array(binary.length);
                for (let i = 0; i < binary.length; i++) {
                    bytes[i] = binary.charCodeAt(i);
                }
                const blob = new Blob([bytes], { type: 'audio/wav' });
                const url = URL.createObjectURL(blob);
                const audio = new Audio(url);
                audio.play();
            }
        } catch (e) {}
    };
    
    ws.onerror = (err) => {
        console.error('❌ WebSocket error:', err);
    };
    
    ws.onclose = () => {
        console.log('🔌 WebSocket closed');
        document.body.style.border = '5px solid red';
    };
    
})();
""")

print("\n" + "="*60)
print("STEPS:")
print("1. Browser me F12 press karo")
print("2. 'Console' tab kholo")
print("3. Upar wala JavaScript copy karke paste karo")
print("4. Enter press karo")
print("5. Microphone permission ALLOW karo")
print("6. Green border dikhai dega = ACTIVE!")
print("="*60)
