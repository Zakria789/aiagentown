import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

HUME_API_KEY = os.getenv("HUME_API_KEY")

# Roofing sales script based on the PDF manual
system_prompt = """You are a professional AI sales agent for Orange Roofing company specializing in residential roofing services in New Jersey.

Your role:
- Professional, friendly, and helpful tone
- Ask questions to understand customer's roofing needs
- Book free roof inspection appointments
- Handle objections professionally
- Provide information about roofing services, repairs, and replacements

Key points:
- We offer FREE roof inspections and estimates
- Residential roofing specialists in New Jersey
- Professional installation and repair services
- Emergency roof repairs available
- Multiple financing options available

Call flow:
1. Greet professionally: "Hi, this is [Agent Name] from Orange Roofing. How are you today?"
2. State purpose: "We're calling homeowners in your area about our free roof inspection service."
3. Ask qualifying questions: "When was the last time you had your roof inspected?"
4. Book appointment: "I can schedule a free inspection for you. What day works best?"
5. Confirm details and thank them

Handle DNC requests immediately: "I apologize for the inconvenience. I will add your number to our Do Not Call list right away. Have a great day."

Stay professional, listen actively, and help customers understand the value of our roofing services."""

# Agent configuration using CORRECT format from existing agents
agent_config = {
    "name": "Roofing Sales Agent - Orange Roofing",
    "evi_version": "3",
    "prompt": {
        "text": system_prompt
    },
    "voice": {
        "provider": "HUME_AI",
        "name": "ITO"
    },
    "language_model": {
        "model_provider": "ANTHROPIC",
        "model_resource": "claude-3-5-sonnet-20241022"
    },
    "timeouts": {
        "inactivity": {
            "enabled": True,
            "duration_secs": 120
        },
        "max_duration": {
            "enabled": True,
            "duration_secs": 1800
        }
    },
    "event_messages": {
        "on_new_chat": {
            "enabled": False
        },
        "on_inactivity_timeout": {
            "enabled": True,
            "text": "I haven't heard from you in a while. Are you still there?"
        },
        "on_max_duration_timeout": {
            "enabled": True,
            "text": "I apologize, but our call time limit has been reached. Thank you for your time today!"
        }
    }
}

print("Creating new HumeAI agent for roofing sales...")
print(f"Using format from existing 'Zakria' agent")

url = "https://api.hume.ai/v0/evi/configs"
headers = {
    "X-Hume-Api-Key": HUME_API_KEY,
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=agent_config, headers=headers)
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"\nFull Response:")
    print(json.dumps(response.json(), indent=2))
    
    if response.status_code == 200 or response.status_code == 201:
        result = response.json()
        print("\n✅ SUCCESS! Agent created!")
        print(f"\n📋 Agent Details:")
        print(f"   ID: {result.get('id')}")
        print(f"   Name: {result.get('name')}")
        print(f"   Version: {result.get('version')}")
        print(f"   EVI Version: {result.get('evi_version')}")
        
        print(f"\n🔑 Add this to your .env file:")
        print(f"   HUME_CONFIG_ID={result.get('id')}")
    else:
        print(f"\n❌ Error creating agent")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {str(e)}")
