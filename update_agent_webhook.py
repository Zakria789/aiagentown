"""
Update HumeAI Agent with Webhook Configuration
This will allow HumeAI to send events to our backend via ngrok
"""

import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

HUME_API_KEY = os.getenv("HUME_API_KEY")
CONFIG_ID = os.getenv("HUME_CONFIG_ID")
NGROK_URL = "https://uncontortioned-na-ponderously.ngrok-free.dev"

print("🔧 Updating HumeAI Agent with Webhook Configuration")
print("=" * 60)
print(f"Config ID: {CONFIG_ID}")
print(f"Ngrok URL: {NGROK_URL}")
print()

# Get current config
url = f"https://api.hume.ai/v0/evi/configs/{CONFIG_ID}"
headers = {"X-Hume-Api-Key": HUME_API_KEY}

print("Fetching current config...")
response = requests.get(url, headers=headers)

if response.status_code == 200:
    current_config = response.json()
    print("✅ Current config retrieved")
    print()
    
    # Update with webhooks
    updated_config = {
        "name": current_config.get('name') or "Roofing Sales Agent - Orange Roofing",
        "evi_version": str(current_config.get('evi_version')),
        "prompt": {
            "text": current_config.get('prompt', {}).get('text', '')
        },
        "voice": {
            "provider": current_config.get('voice', {}).get('provider'),
            "name": current_config.get('voice', {}).get('name')
        },
        "language_model": current_config.get('language_model'),
        "timeouts": current_config.get('timeouts'),
        "event_messages": current_config.get('event_messages'),
        "webhooks": [
            {
                "url": f"{NGROK_URL}/api/webhooks/hume",
                "events": [
                    "chat_started",
                    "chat_ended",
                    "user_message",
                    "assistant_message",
                    "audio_output"
                ],
                "secret": "hume_webhook_secret_123"
            }
        ]
    }
    
    print("Updating config with webhook...")
    print(f"Webhook URL: {NGROK_URL}/api/webhooks/hume")
    print()
    
    # Update config
    update_response = requests.patch(
        url,
        json=updated_config,
        headers={
            **headers,
            "Content-Type": "application/json"
        }
    )
    
    if update_response.status_code in [200, 201]:
        print("✅ Agent updated successfully!")
        result = update_response.json()
        print()
        print("Updated configuration:")
        print(f"  Name: {result.get('name')}")
        print(f"  Webhooks: {len(result.get('webhooks', []))}")
        if result.get('webhooks'):
            for wh in result['webhooks']:
                print(f"    - URL: {wh.get('url')}")
                print(f"      Events: {', '.join(wh.get('events', []))}")
    else:
        print(f"❌ Update failed: {update_response.status_code}")
        print(update_response.text)

else:
    print(f"❌ Failed to get config: {response.status_code}")
    print(response.text)

print()
print("=" * 60)
print("📋 Next: HumeAI will now send events to your backend")
print(f"   Webhook endpoint: {NGROK_URL}/api/webhooks/hume")
