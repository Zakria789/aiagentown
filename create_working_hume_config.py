"""
Create a WORKING HumeAI configuration with proper voice and prompt settings
Ye script HumeAI Dashboard ke configuration ko API se banayega
"""

import requests
import json
from app.config import Settings

settings = Settings()

def create_optimized_config():
    """Create HumeAI config with FAST voice and proper prompts"""
    
    # HumeAI Management API endpoint
    url = "https://api.hume.ai/v0/evi/configs"
    
    headers = {
        "X-Hume-Api-Key": settings.HUME_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Configuration with FAST voice and proper system prompt
    config = {
        "name": "CallCenter Agent - Fast Voice (48kHz)",
        "description": "Optimized configuration for call center with faster response",
        
        # SYSTEM PROMPT - Ye AI ko batata hai kya karna hai
        "prompt": {
            "text": """You are a friendly and professional call center agent for Orange Roofing company. 

Your role:
- Greet the customer warmly when they answer
- Ask about their roofing needs (repair, replacement, inspection)
- Qualify their interest level (hot, warm, cold lead)
- Schedule appointments for qualified leads
- Handle objections professionally

Keep responses:
- Brief (1-2 sentences max)
- Natural and conversational
- Professional but friendly

Start every call with: "Hello! This is calling from Orange Roofing. How are you doing today?"
"""
        },
        
        # VOICE SETTINGS - Faster speech rate
        "voice": {
            "provider": "HUME_AI",
            "name": "ITO"  # Clear, professional voice
        },
        
        # LANGUAGE MODEL - GPT-4 for better responses
        "language_model": {
            "model_provider": "OPEN_AI",
            "model_resource": "gpt-4o-mini"  # Fast and accurate
        },
        
        # AUDIO SETTINGS - 48kHz for quality
        "audio": {
            "sample_rate": 48000,
            "encoding": "linear16",
            "channels": 1
        },
        
        # EVENT MESSAGES - Custom greeting
        "event_messages": {
            "on_new_chat": {
                "enabled": True,
                "text": "Hello! This is calling from Orange Roofing. How are you doing today?"
            },
            "on_inactivity_timeout": {
                "enabled": True,
                "text": "I'm sorry, I didn't catch that. Are you still there?"
            },
            "on_max_duration_timeout": {
                "enabled": True,
                "text": "Thank you for your time. Have a great day!"
            }
        },
        
        # TIMEOUTS
        "timeouts": {
            "inactivity": {
                "enabled": True,
                "duration_secs": 600  # 10 minutes
            },
            "max_duration": {
                "enabled": True,
                "duration_secs": 1800  # 30 minutes max
            }
        }
    }
    
    print("=" * 80)
    print("🚀 Creating NEW HumeAI Configuration...")
    print("=" * 80)
    print(f"\n📝 Configuration Name: {config['name']}")
    print(f"🎤 Voice: {config['voice']['name']} (HUME_AI)")
    print(f"🧠 Model: {config['language_model']['model_resource']}")
    print(f"🎵 Sample Rate: {config['audio']['sample_rate']} Hz")
    print(f"\n💬 System Prompt Preview:")
    print(config['prompt']['text'][:200] + "...")
    
    try:
        # Send request to HumeAI API
        print("\n📤 Sending request to HumeAI API...")
        response = requests.post(url, headers=headers, json=config, timeout=30)
        
        if response.status_code == 201:
            result = response.json()
            config_id = result.get('id')
            
            print("\n" + "=" * 80)
            print("✅ SUCCESS! New Configuration Created")
            print("=" * 80)
            print(f"\n🆔 New Config ID: {config_id}")
            print(f"📛 Name: {result.get('name')}")
            print(f"📅 Created: {result.get('created_on')}")
            
            print("\n" + "=" * 80)
            print("⚙️ NEXT STEPS:")
            print("=" * 80)
            print(f"\n1. Copy this Config ID: {config_id}")
            print("\n2. Update your .env file:")
            print(f"   HUME_CONFIG_ID={config_id}")
            print("\n3. Restart the server:")
            print("   Ctrl+C (stop server)")
            print("   venv\\Scripts\\activate; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
            print("\n4. Test again with a call")
            print("=" * 80)
            
            # Save config details to file
            with open("new_hume_config.json", "w") as f:
                json.dump(result, f, indent=2)
            print("\n💾 Full config saved to: new_hume_config.json")
            
            return config_id
            
        else:
            print("\n" + "=" * 80)
            print("❌ FAILED TO CREATE CONFIG")
            print("=" * 80)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Check if API key is valid
            if response.status_code == 401:
                print("\n⚠️ API Key Invalid or Expired!")
                print(f"Current API Key: {settings.HUME_API_KEY[:20]}...")
            elif response.status_code == 400:
                print("\n⚠️ Invalid Configuration!")
                print("Check the error message above for details.")
            
            return None
            
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ ERROR CREATING CONFIG")
        print("=" * 80)
        print(f"Error: {str(e)}")
        return None


def list_existing_configs():
    """List all existing HumeAI configs"""
    
    url = "https://api.hume.ai/v0/evi/configs"
    headers = {
        "X-Hume-Api-Key": settings.HUME_API_KEY
    }
    
    print("\n" + "=" * 80)
    print("📋 EXISTING HUMEAI CONFIGURATIONS")
    print("=" * 80)
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            configs = response.json()
            
            if not configs:
                print("\n⚠️ No configurations found!")
                return
            
            print(f"\nTotal Configs: {len(configs)}")
            print("\n" + "-" * 80)
            
            for i, config in enumerate(configs, 1):
                print(f"\n{i}. {config.get('name', 'Unnamed')}")
                print(f"   ID: {config.get('id')}")
                print(f"   Voice: {config.get('voice', {}).get('name', 'Not set')}")
                print(f"   Created: {config.get('created_on', 'Unknown')}")
                
                # Check if this is the current config
                if config.get('id') == settings.HUME_CONFIG_ID:
                    print("   ⭐ CURRENTLY ACTIVE IN .ENV")
        else:
            print(f"\n❌ Failed to fetch configs: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🔧 HUMEAI CONFIGURATION MANAGER")
    print("=" * 80)
    
    # First, show existing configs
    list_existing_configs()
    
    # Ask user if they want to create new config
    print("\n" + "=" * 80)
    print("❓ Do you want to create a NEW optimized config?")
    print("=" * 80)
    print("\nThis will create a config with:")
    print("  - Fast voice (ITO from HUME_AI)")
    print("  - Proper system prompt for call center")
    print("  - 48kHz audio quality")
    print("  - GPT-4o-mini for fast responses")
    
    choice = input("\nCreate new config? (y/n): ").strip().lower()
    
    if choice == 'y':
        config_id = create_optimized_config()
        
        if config_id:
            print("\n✅ Configuration created successfully!")
            print(f"\n🔄 Update your .env file with this Config ID:")
            print(f"HUME_CONFIG_ID={config_id}")
    else:
        print("\n❌ Cancelled. Using existing config.")
