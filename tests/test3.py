import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        # Login
        login = await client.post("http://localhost:8000/api/auth/login", json={"agent_id": "admin", "password": "admin123"})
        token = login.json()["access_token"]
        
        # Create agent
        agent_data = {
            "agent_id": "HUME003",
            "full_name": "Test Agent 3",
            "email": "hume003@test.com",
            "password": "Test@123",
            "phone": "+1234567890",
            "role": "agent",
            "permissions": ["make_calls"],
            "dialer_extension": "103",
            "campaign_script": "Hello from TechCorp!"
        }
        
        response = await client.post(
            "http://localhost:8000/api/agents/",
            json=agent_data,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            agent = response.json()
            print(f"Agent: {agent['agent_id']}")
            print(f"Config: {agent.get('hume_config_id')}")
        else:
            print(f"Error: {response.text}")

asyncio.run(test())
