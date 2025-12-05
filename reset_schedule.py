"""
Reset and reschedule agent
"""
import asyncio
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
import pytz
from app.database import AsyncSessionLocal
from app.models.dialer_user import DialerUser
from sqlalchemy import select


async def reset_and_schedule():
    async with AsyncSessionLocal() as db:
        # Get user
        result = await db.execute(select(DialerUser).where(DialerUser.id == 1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ User not found")
            return
        
        print(f"✅ Found user: {user.username}")
        print(f"   Currently logged in: {user.is_logged_in}")
        
        # Logout first
        print(f"\n📤 Logging out user...")
        user.is_logged_in = False
        user.session_id = None
        
        # Set new schedule - 2 minutes from now
        tz = pytz.timezone('America/New_York')
        now = datetime.now(tz)
        start_time = now + timedelta(minutes=2)
        end_time = start_time + timedelta(hours=8)
        
        user.schedule_enabled = True
        user.start_time = start_time.strftime('%H:%M')
        user.end_time = end_time.strftime('%H:%M')
        user.timezone = 'America/New_York'
        user.days_of_week = now.strftime('%A')
        user.auto_login = True
        user.auto_unpause = True
        
        await db.commit()
        
        print(f"\n{'='*60}")
        print(f"✅ USER RESET & RESCHEDULED!")
        print(f"{'='*60}")
        print(f"\n⏰ New Schedule:")
        print(f"   Current Time: {now.strftime('%H:%M:%S')}")
        print(f"   Start Time: {start_time.strftime('%H:%M:%S')} (in 2 minutes)")
        print(f"   End Time: {end_time.strftime('%H:%M:%S')}")
        print(f"   Day: {user.days_of_week}")
        print(f"\n🤖 Agent will auto-start in 2 minutes!")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(reset_and_schedule())
