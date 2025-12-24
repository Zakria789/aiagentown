"""
Create NEW HumeAI Config with FAST GPT-4o-mini model
This will fix the voice issue 100%
"""
import requests
import json
from datetime import datetime

API_KEY = "dmWJAfVJARQhlyqwFJhMBlPnfUTOvN8u3CtbQcSC7GGfAspA"
SECRET_KEY = "ONxxShKz6gDjQNXvbJUG8HebAGnUnLr7EOuv4uUZKppC5619lCYFN65mISlEjKfs"

# Create unique config name with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
config_name = f"FastAgent_GPT4omini_{timestamp}"

print("=" * 70)
print("🚀 CREATING NEW HUMEAI CONFIG WITH FAST MODEL")
print("=" * 70)

# NEW CONFIG with GPT-4o-mini (FAST model - no web searches)
config = {
    "name": config_name,
    "version_description": "Fast voice agent with GPT-4o-mini model",
    "language_model": {
        "model_provider": "OPEN_AI",
        "model_resource": "gpt-4o-mini",
        "temperature": 1.0
    },
    "voice": {
        "provider": "HUME_AI",
        "name": "ITO"
    },
    "event_messages": {
        "on_new_chat": {
            "enabled": True,
            "text": "Hello! This is calling from Orange Roofing. How are you doing today?"
        }
    },
    "builtin_tools": [],
    "timeouts": {
        "inactivity": {
            "enabled": True,
            "duration_secs": 600
        },
        "max_duration": {
            "enabled": True,
            "duration_secs": 1800
        }
    }
}

print(f"📝 Config Name: {config_name}")
print(f"🤖 Model: OPEN_AI/gpt-4o-mini (FAST - no web search)")
print(f"🎤 Voice: ITO")
print(f"💬 Auto-greeting: Enabled")
print()

try:
    # Create config
    print("📤 Sending request to HumeAI API...")
    response = requests.post(
        "https://api.hume.ai/v0/evi/configs",
        headers={
            "X-Hume-Api-Key": API_KEY,
            "X-Hume-Secret-Key": SECRET_KEY,
            "Content-Type": "application/json"
        },
        json=config
    )
    
    print(f"📥 Response Status: {response.status_code}")
    
    if response.status_code == 201:
        result = response.json()
        config_id = result.get("id")
        
        print()
        print("=" * 70)
        print("✅ SUCCESS! NEW FAST CONFIG CREATED!")
        print("=" * 70)
        print(f"🆔 Config ID: {config_id}")
        print(f"📛 Config Name: {config_name}")
        print(f"🚀 Model: gpt-4o-mini (FAST)")
        print()
        print("📋 NEXT STEPS:")
        print("1. Update .env file:")
        print(f"   HUME_CONFIG_ID={config_id}")
        print("2. Server will auto-restart")
        print("3. Test call - AI will respond IMMEDIATELY!")
        print("=" * 70)
        
        # Write config ID to file for easy copy-paste
        with open("NEW_CONFIG_ID.txt", "w") as f:
            f.write(f"HUME_CONFIG_ID={config_id}\n")
        print()
        print("✅ Config ID saved to: NEW_CONFIG_ID.txt")
        
    elif response.status_code == 409:
        print()
        print("⚠️ Config name already exists (409 Conflict)")
        print("💡 Solution: Run script again - will create with new timestamp")
        
    else:
        print()
        print(f"❌ Failed to create config: {response.status_code}")
        print(f"📄 Response: {response.text}")
        
except Exception as e:
    print()
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
