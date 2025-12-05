import asyncio
import httpx
from app.config import settings

async def get_hume_voices():
    api_key = settings.HUME_API_KEY
    
    headers = {
        "X-Hume-Api-Key": api_key
    }
    
    async with httpx.AsyncClient() as client:
        # Get available voices
        response = await client.get(
            "https://api.hume.ai/v0/evi/voices",
            headers=headers,
            timeout=10.0
        )
        
        if response.status_code == 200:
            voices = response.json()
            print(f"Total voices: {len(voices.get('octave_voices_page', []))}")
            print("\nAvailable voices:\n")
            
            for voice in voices.get('octave_voices_page', [])[:20]:  # First 20
                tags = voice.get('tags', {})
                gender = tags.get('GENDER', ['Unknown'])[0]
                name = voice.get('name', 'Unknown')
                voice_id = voice.get('id')
                
                print(f"ID: {voice_id}")
                print(f"   Name: {name}")
                print(f"   Gender: {gender}")
                print(f"   Tags: {tags}")
                print()
        else:
            print(f"Error: {response.status_code} - {response.text}")

asyncio.run(get_hume_voices())
