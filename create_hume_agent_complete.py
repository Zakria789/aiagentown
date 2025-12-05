"""
Create HumeAI Agent Configuration
Complete setup with proper prompts and voice
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

HUME_API_KEY = os.getenv("HUME_API_KEY")

print("╔══════════════════════════════════════════════════════════╗")
print("║  HumeAI Agent Configuration Creator                     ║")
print("╚══════════════════════════════════════════════════════════╝")
print()

# Agent Configuration
agent_config = {
    "name": "CallCenter AI Agent - Roofing Sales",
    "version_description": "Professional roofing sales agent for call center",
    
    # System Prompt
    "system_prompt": "You are a professional roofing sales representative. Greet customers warmly, introduce yourself, ask about their roofing needs, offer free inspection, and schedule appointments. Be friendly and professional. Start with: 'Hello! This is from the roofing company. How are you doing today?'",
    
    # Voice Configuration
    "voice": {
        "provider": "HUME_AI",
        "name": "ITO"
    },
    
    # Language Model
    "language_model": {
        "model_provider": "ANTHROPIC",
        "model_resource": "claude-3-5-sonnet-20241022"
    },
    
    # EVI Configuration
    "evi_version": "FOUR_MINI"
}

print("Creating HumeAI Agent Configuration...")
print()
print("Agent Details:")
print(f"  Name: {agent_config['name']}")
print(f"  Voice: {agent_config['voice']['name']}")
print(f"  Model: {agent_config['language_model']['model_resource']}")
print()

# Create configuration
url = "https://api.hume.ai/v0/evi/configs"
headers = {
    "X-Hume-Api-Key": HUME_API_KEY,
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, headers=headers, json=agent_config)
    
    if response.status_code == 200 or response.status_code == 201:
        result = response.json()
        config_id = result.get("id")
        
        print("✅ SUCCESS! Agent Created!")
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  Agent Configuration ID                                  ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        print(f"Config ID: {config_id}")
        print()
        print("📝 Save this Config ID in your .env file:")
        print()
        print(f"HUME_CONFIG_ID={config_id}")
        print()
        print("Agent Ready! Now you can:")
        print("  1. Update .env with this Config ID")
        print("  2. Run auto_dialer_complete.py")
        print("  3. AI agent will talk to customers!")
        print()
        
        # Save to file for backup
        with open("hume_config_id.txt", "w") as f:
            f.write(f"HUME_CONFIG_ID={config_id}\n")
            f.write(f"\nCreated: {agent_config['name']}\n")
            f.write(f"Voice: {agent_config['voice']['name']}\n")
        
        print("✅ Config ID also saved to: hume_config_id.txt")
        
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
