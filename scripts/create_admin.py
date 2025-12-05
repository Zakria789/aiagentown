"""
Admin utility script
Create initial admin agent
"""

import asyncio
import sys
from app.database import AsyncSessionLocal
from app.models.agent import Agent
from app.core.security import hash_password


async def create_admin_agent(agent_id: str, password: str, email: str, full_name: str):
    """
    Admin agent create karo
    
    Usage:
        python scripts/create_admin.py admin admin123 admin@example.com "Admin User"
    """
    async with AsyncSessionLocal() as db:
        try:
            # Check if agent already exists
            from sqlalchemy import select
            result = await db.execute(
                select(Agent).where(Agent.agent_id == agent_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"❌ Agent {agent_id} already exists!")
                return False
            
            # Create admin agent
            admin = Agent(
                agent_id=agent_id,
                password_hash=hash_password(password),
                full_name=full_name,
                email=email,
                role="admin",
                permissions=["*"],  # All permissions
                is_active=True
            )
            
            db.add(admin)
            await db.commit()
            
            print("✅ Admin agent created successfully!")
            print(f"   Login ID: {agent_id}")
            print(f"   Password: {password}")
            print(f"   Email: {email}")
            print(f"   Name: {full_name}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating admin: {e}")
            await db.rollback()
            return False


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python scripts/create_admin.py <agent_id> <password> <email> <full_name>")
        print('Example: python scripts/create_admin.py admin admin123 admin@example.com "Admin User"')
        sys.exit(1)
    
    agent_id = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3]
    full_name = sys.argv[4]
    
    asyncio.run(create_admin_agent(agent_id, password, email, full_name))
