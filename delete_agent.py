import requests
import os
from dotenv import load_dotenv

load_dotenv()

HUME_API_KEY = os.getenv("HUME_API_KEY")
CONFIG_ID = "4a8235fb-91d6-4234-aef9-1a88616a966f"

print(f"Deleting empty agent config: {CONFIG_ID}")

url = f"https://api.hume.ai/v0/evi/configs/{CONFIG_ID}"
headers = {"X-Hume-Api-Key": HUME_API_KEY}

response = requests.delete(url, headers=headers)

print(f"Status: {response.status_code}")
if response.status_code in [200, 204]:
    print("✅ Deleted successfully!")
else:
    print(f"Response: {response.text}")
