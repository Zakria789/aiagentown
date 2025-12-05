"""
Get existing HumeAI configurations to see correct format
"""
import requests
from dotenv import load_dotenv
import os
import json

load_dotenv()

HUME_API_KEY = os.getenv("HUME_API_KEY")

print("Fetching existing HumeAI configurations...")
print()

url = "https://api.hume.ai/v0/evi/configs"
headers = {"X-Hume-Api-Key": HUME_API_KEY}

try:
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        
        # Handle both list and dict responses
        if isinstance(data, dict):
            configs = data.get('configs', [data])
        else:
            configs = data
        
        print(f"Found configurations:")
        print()
        
        for i, config in enumerate(configs[:3]):  # Show first 3
            print("=" * 60)
            print(f"Config #{i+1}")
            print(f"Name: {config.get('name', 'N/A')}")
            print(f"ID: {config.get('id', 'N/A')}")
            print()
            print("Full Config:")
            print(json.dumps(config, indent=2))
            print()
            
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")
