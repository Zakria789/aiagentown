"""
Initialize database tables
Run this before starting the server
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, engine, Base
from app.models import Agent, Customer, Call, CallEvent, Schedule
from app.models.dialer_user import DialerUser
from app.models.training_content import TrainingContent, ConversationFlow, TrainingTest
from app.services.notification_service import Notification
from app.core.security import hash_password


async def create_tables():
    """Database tables create karo"""
    print("Creating database tables...")
    
    try:
        async with engine.begin() as conn:
            # Drop all tables (careful in production!)
            await conn.run_sync(Base.metadata.drop_all)
            print("✅ Dropped existing tables")
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            print("✅ Created all tables")
        
        print("\n✅ Database initialized successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def create_demo_admin():
    """Demo admin agent create karo"""
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    
    print("\nCreating demo admin agent...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check if admin already exists
            result = await db.execute(
                select(Agent).where(Agent.agent_id == "admin")
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print("⚠️  Admin agent already exists")
                return
            
            # Create admin
            admin = Agent(
                agent_id="admin",
                password_hash=hash_password("admin123"),
                full_name="System Administrator",
                email="admin@callcenter.local",
                phone="+1234567890",
                role="admin",
                permissions=["*"],
                is_active=True
            )
            
            db.add(admin)
            await db.commit()
            
            print("✅ Admin agent created!")
            print("   Login ID: admin")
            print("   Password: admin123")
            print("   Email: admin@callcenter.local")
            
        except Exception as e:
            print(f"❌ Error creating admin: {e}")
            await db.rollback()


async def create_demo_data():
    """Demo data create karo (optional)"""
    from app.database import AsyncSessionLocal
    
    print("\nCreating demo customers...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Create demo customers
            customers = [
                Customer(
                    full_name="Ali Hassan",
                    phone="+923001234567",
                    email="ali@example.com",
                    city="Karachi",
                    state="Sindh",
                    country="Pakistan",
                    status="new",
                    priority=2,
                    source="website",
                    tags=["hot-lead", "interested"]
                ),
                Customer(
                    full_name="Sara Ahmed",
                    phone="+923009876543",
                    email="sara@example.com",
                    city="Lahore",
                    state="Punjab",
                    country="Pakistan",
                    status="new",
                    priority=1,
                    source="referral"
                ),
                Customer(
                    full_name="Bilal Khan",
                    phone="+923007654321",
                    email="bilal@example.com",
                    city="Islamabad",
                    country="Pakistan",
                    status="contacted",
                    priority=3,
                    source="campaign"
                )
            ]
            
            for customer in customers:
                db.add(customer)
            
            await db.commit()
            
            print(f"✅ Created {len(customers)} demo customers")
            
        except Exception as e:
            print(f"⚠️  Error creating demo data: {e}")
            await db.rollback()


async def main():
    """Main setup function"""
    print("=" * 60)
    print("  FastAPI Call Center - Database Setup")
    print("=" * 60)
    print()
    
    # Create tables
    success = await create_tables()
    
    if not success:
        print("\n❌ Setup failed!")
        return
    
    # Create admin
    await create_demo_admin()
    
    # Ask for demo data
    response = input("\nCreate demo customers? (y/n): ").lower()
    if response == 'y':
        await create_demo_data()
    
    print("\n" + "=" * 60)
    print("✅ Setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start server: uvicorn app.main:app --reload")
    print("2. Open API docs: http://localhost:8000/docs")
    print("3. Login with: admin / admin123")
    print()


if __name__ == "__main__":
    asyncio.run(main())
