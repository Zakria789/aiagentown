"""
Quick script to create admin user
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.database import AsyncSessionLocal
from app.models.agent import Agent
from app.core.security import hash_password
from sqlalchemy import select


async def create_admin():
    async with AsyncSessionLocal() as db:
        # Check if admin exists
        result = await db.execute(select(Agent).where(Agent.agent_id == "admin"))
        existing = result.scalar_one_or_none()
        
        if existing:
            print("✅ Admin already exists")
            print(f"   ID: {existing.id}")
            print(f"   Email: {existing.email}")
            return
        
        # Create admin
        admin = Agent(
            agent_id="admin",
            password_hash=hash_password("admin123"),
            full_name="System Admin",
            email="admin@callcenter.com",
            role="admin",
            permissions=["*"],
            is_active=True
        )
        
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        
        print("✅ Admin created successfully!")
        print(f"   Agent ID: admin")
        print(f"   Password: admin123")
        print(f"   Email: {admin.email}")
        print(f"   ID: {admin.id}")


if __name__ == "__main__":
    asyncio.run(create_admin())
