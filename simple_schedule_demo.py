"""
Simple Demo: Schedule Agent Automatically
No authentication needed - directly updates database
"""
import asyncio
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
import pytz
from app.database import AsyncSessionLocal
from app.models.dialer_user import DialerUser
from app.models.agent import Agent
from sqlalchemy import select


async def schedule_agent_3min():
    """Schedule agent to start in 3 minutes"""
    
    async with AsyncSessionLocal() as db:
        # Get or create agent
        result = await db.execute(select(Agent).where(Agent.agent_id == "admin"))
        agent = result.scalar_one_or_none()
        
        if not agent:
            print("❌ Agent not found. Please create admin first.")
            return
        
        print(f"✅ Found agent: {agent.agent_id}")
        
        # Get or create dialer user
        result = await db.execute(select(DialerUser).where(DialerUser.agent_id == agent.id))
        dialer_user = result.scalar_one_or_none()
        
        if not dialer_user:
            print("\n📝 Creating dialer user...")
            dialer_user = DialerUser(
                username="Eddie.Faklis",
                password="Roofing123",  # TODO: Encrypt in production
                dialer_url="https://east-1.calltools.io",
                dialer_type="calltools",
                agent_id=agent.id,
                is_active=True
            )
            db.add(dialer_user)
            await db.commit()
            await db.refresh(dialer_user)
            print(f"✅ Created dialer user: {dialer_user.username}")
        else:
            print(f"✅ Found dialer user: {dialer_user.username}")
        
        # Calculate schedule time (3 minutes from now)
        tz = pytz.timezone('America/New_York')
        now = datetime.now(tz)
        start_time = now + timedelta(minutes=3)
        end_time = start_time + timedelta(hours=8)  # 8 hour shift
        
        # Update schedule
        dialer_user.schedule_enabled = True
        dialer_user.start_time = start_time.strftime('%H:%M')
        dialer_user.end_time = end_time.strftime('%H:%M')
        dialer_user.timezone = 'America/New_York'
        dialer_user.days_of_week = now.strftime('%A')  # Today only
        dialer_user.auto_login = True
        dialer_user.auto_unpause = True
        
        await db.commit()
        
        print(f"\n{'='*60}")
        print(f"📅 AGENT SCHEDULED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"\n📋 Schedule Details:")
        print(f"   Agent: {agent.agent_id}")
        print(f"   Dialer User: {dialer_user.username}")
        print(f"   Dialer URL: {dialer_user.dialer_url}")
        print(f"\n⏰ Timing:")
        print(f"   Current Time: {now.strftime('%H:%M:%S')}")
        print(f"   Start Time: {start_time.strftime('%H:%M:%S')} (in 3 minutes)")
        print(f"   End Time: {end_time.strftime('%H:%M:%S')}")
        print(f"   Timezone: {dialer_user.timezone}")
        print(f"   Day: {dialer_user.days_of_week}")
        
        print(f"\n🤖 What will happen automatically:")
        print(f"   1. At {start_time.strftime('%H:%M')}: Login to CallTools")
        print(f"   2. Join campaign automatically")
        print(f"   3. Set status to Available")
        print(f"   4. Start receiving calls")
        print(f"\n⏳ Wait 3 minutes and watch the magic!")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║  Agent Auto-Scheduling System                            ║
║  Schedule agent to start automatically in 3 minutes      ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(schedule_agent_3min())
    
    print("\n💡 TIP: Backend scheduler runs every minute.")
    print("   Make sure your FastAPI backend is running!")
    print("   Command: uvicorn app.main:app --reload")
