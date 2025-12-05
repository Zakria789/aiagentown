"""
Update CallTools URL (without /agent)
"""
import asyncio
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
import pytz
from app.database import AsyncSessionLocal
from app.models.dialer_user import DialerUser
from sqlalchemy import select


async def update_url():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(DialerUser).where(DialerUser.id == 1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ User not found")
            return
        
        print(f"Old URL: {user.dialer_url}")
        
        # Update URL
        user.dialer_url = "https://east-1.calltools.io"
        
        # Logout and reschedule
        user.is_logged_in = False
        user.session_id = None
        
        tz = pytz.timezone('America/New_York')
        now = datetime.now(tz)
        start_time = now + timedelta(minutes=2)
        end_time = start_time + timedelta(hours=8)
        
        user.schedule_enabled = True
        user.start_time = start_time.strftime('%H:%M')
        user.end_time = end_time.strftime('%H:%M')
        user.days_of_week = now.strftime('%A')
        user.auto_login = True
        user.auto_unpause = True
        
        await db.commit()
        
        print(f"\n{'='*60}")
        print(f"✅ URL UPDATED!")
        print(f"{'='*60}")
        print(f"\nNew URL: {user.dialer_url}")
        print(f"Username: {user.username}")
        print(f"\n⏰ Schedule:")
        print(f"   Current: {now.strftime('%H:%M:%S')}")
        print(f"   Start: {start_time.strftime('%H:%M:%S')} (in 2 min)")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(update_url())
