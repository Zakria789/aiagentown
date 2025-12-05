"""
Fix HumeAI Config via API
"""
import requests
import json

API_KEY = "dmWJAfVJARQhlyqwFJhMBlPnfUTOvN8u3CtbQcSC7GGfAspA"
CONFIG_ID = "64cfa125-77d6-4746-b64f-5b3ac83c5fb6"

headers = {
    "X-Hume-Api-Key": API_KEY,
    "Content-Type": "application/json"
}

# Get current config
print("🔍 Fetching current config...")
response = requests.get(
    f"https://api.hume.ai/v0/evi/configs/{CONFIG_ID}",
    headers=headers
)

if response.status_code == 200:
    config = response.json()
    print("✅ Current config:")
    print(json.dumps(config, indent=2))
    
    # Update config
    print("\n🔧 Updating config...")
    
    # Set agent to speak first
    update_data = {
        "name": config.get("name", "Orange Roofing AI"),
        "voice": {
            "provider": "HUME_AI",
            "name": "ITO"
        },
        "language_model": config.get("language_model", {
            "model_provider": "ANTHROPIC",
            "model_resource": "claude-3-5-sonnet-20241022"
        }),
        "system_prompt": config.get("system_prompt", "You are a helpful AI assistant for Orange Roofing company."),
        "conversation_config": {
            "first_speaker": "AGENT",  # THIS IS THE FIX!
            "turn": {
                "mode": "TURN_BASED"
            }
        }
    }
    
    response = requests.post(
        f"https://api.hume.ai/v0/evi/configs",
        headers=headers,
        json=update_data
    )
    
    if response.status_code in [200, 201]:
        new_config = response.json()
        new_id = new_config.get("id")
        print(f"\n✅ CONFIG UPDATED!")
        print(f"New Config ID: {new_id}")
        print("\n🎯 CHANGES MADE:")
        print("  - First Speaker: AGENT ✅")
        print("  - Voice: ITO ✅")
        print(f"\n📝 Update your code to use: {new_id}")
    else:
        print(f"❌ Update failed: {response.status_code}")
        print(response.text)
else:
    print(f"❌ Failed to get config: {response.status_code}")
    print(response.text)
