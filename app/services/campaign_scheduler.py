"""
Campaign Scheduler Service
Automatically starts and stops campaigns based on schedule
"""
import asyncio
import logging
from datetime import datetime, time
from typing import List
import pytz

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.dialer_user import DialerUser
from app.models.call import Call
from app.database import async_session_maker
from app.services.dialer_automation import dialer_automation
from app.services.notification_service import notification_service, NotificationPriority

logger = logging.getLogger(__name__)


class CampaignScheduler:
    """
    Background scheduler for automated campaign management
    Checks schedules and auto-starts/stops campaigns
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.running = False
    
    async def start(self):
        """Start the scheduler"""
        if not self.running:
            # Add job to check schedules every minute
            self.scheduler.add_job(
                self.check_schedules,
                'cron',
                minute='*',  # Run every minute
                id='check_campaign_schedules'
            )
            
            self.scheduler.start()
            self.running = True
            logger.info("Campaign scheduler started - checking every minute")
    
    async def stop(self):
        """Stop the scheduler"""
        if self.running:
            self.scheduler.shutdown()
            self.running = False
            logger.info("Campaign scheduler stopped")
    
    async def check_schedules(self):
        """
        Check all scheduled campaigns and start/stop them
        Called every minute by APScheduler
        """
        try:
            async with async_session_maker() as db:
                # Get all users with schedules enabled
                result = await db.execute(
                    select(DialerUser).where(
                        DialerUser.schedule_enabled == True,
                        DialerUser.is_active == True
                    )
                )
                users = result.scalars().all()
                
                for user in users:
                    await self._process_user_schedule(db, user)
                    
        except Exception as e:
            logger.error(f"Error checking schedules: {e}")
    
    async def _process_user_schedule(self, db: AsyncSession, user: DialerUser):
        """
        Process schedule for a single user
        
        Args:
            db: Database session
            user: DialerUser instance
        """
        try:
            # Get current time in user's timezone
            tz = pytz.timezone(user.timezone)
            now = datetime.now(tz)
            current_time = now.time()
            current_day = now.strftime('%A').lower()  # 'monday', 'tuesday', etc.
            
            # Check if today is a scheduled day
            if user.days_of_week:
                scheduled_days = [d.strip().lower() for d in user.days_of_week.split(',')]
                if current_day not in scheduled_days:
                    logger.debug(f"User {user.username}: Today ({current_day}) not scheduled")
                    return
            
            # Parse start and end times
            if not user.start_time or not user.end_time:
                logger.warning(f"User {user.username}: Missing start/end time")
                return
            
            start_hour, start_min = map(int, user.start_time.split(':'))
            end_hour, end_min = map(int, user.end_time.split(':'))
            
            start_time = time(start_hour, start_min)
            end_time = time(end_hour, end_min)
            
            # Check if we're within the scheduled time window
            is_within_schedule = start_time <= current_time <= end_time
            
            if is_within_schedule:
                # Should be running
                if not user.is_logged_in and user.auto_login:
                    logger.info(f"🚀 Starting campaign for {user.username} - scheduled time reached")
                    
                    # Login to dialer with retry
                    success, attempts, error = await dialer_automation.login_with_retry(
                        db, user.id, max_retries=3, headless=True
                    )
                    
                    if success and user.auto_unpause:
                        # Wait a moment for page to stabilize
                        await asyncio.sleep(2)
                        
                        # Click unpause
                        await dialer_automation.click_unpause(db, user.id)
                        logger.info(f"✅ Campaign started for {user.username}")
                    elif not success:
                        # Login failed after retries, send notification
                        logger.error(f"❌ Failed to login {user.username} after {attempts} attempts")
                        await notification_service.notify_login_failure(
                            db=db,
                            dialer_user_id=user.id,
                            username=user.username,
                            error=error or "Unknown error",
                            attempts=attempts
                        )
                
            else:
                # Should be stopped
                if user.is_logged_in:
                    # Check if we passed the end time
                    if current_time > end_time:
                        # Check for active calls before logout
                        has_active_call = await self._check_active_call(db, user)
                        
                        if has_active_call:
                            logger.warning(
                                f"⚠️ User {user.username} has active call, delaying logout"
                            )
                            return
                        
                        logger.info(f"🛑 Stopping campaign for {user.username} - scheduled end time reached")
                        
                        # Pause first
                        await dialer_automation.click_pause(db, user.id)
                        
                        # Wait a moment
                        await asyncio.sleep(1)
                        
                        # Logout
                        await dialer_automation.logout_dialer(db, user.id)
                        logger.info(f"✅ Campaign stopped for {user.username}")
                        
        except Exception as e:
            logger.error(f"Error processing schedule for user {user.id}: {e}")
    
    async def _check_active_call(self, db: AsyncSession, user: DialerUser) -> bool:
        """
        Check if user/agent has any active calls
        
        Returns:
            True if there's an active call
        """
        try:
            if not user.agent_id:
                return False
            
            # Check for active calls for this agent
            result = await db.execute(
                select(Call).where(
                    Call.agent_id == user.agent_id,
                    Call.status.in_(['initiated', 'ringing', 'answered', 'in_progress'])
                )
            )
            active_call = result.scalar_one_or_none()
            
            return active_call is not None
            
        except Exception as e:
            logger.error(f"Error checking active call: {e}")
            return False  # Default to allowing logout if check fails
    
    async def get_active_campaigns(self, db: AsyncSession) -> List[dict]:
        """
        Get list of currently active campaigns
        
        Returns:
            List of dicts with campaign info
        """
        try:
            result = await db.execute(
                select(DialerUser).where(
                    DialerUser.is_logged_in == True
                )
            )
            users = result.scalars().all()
            
            active_campaigns = []
            for user in users:
                tz = pytz.timezone(user.timezone)
                now = datetime.now(tz)
                
                active_campaigns.append({
                    'user_id': user.id,
                    'username': user.username,
                    'agent_id': user.agent_id,
                    'started_at': user.last_login,
                    'scheduled_end': user.end_time,
                    'timezone': user.timezone,
                    'current_time': now.strftime('%H:%M')
                })
            
            return active_campaigns
            
        except Exception as e:
            logger.error(f"Error getting active campaigns: {e}")
            return []
    
    async def force_start_campaign(self, db: AsyncSession, user_id: int):
        """
        Manually start a campaign regardless of schedule
        
        Args:
            db: Database session
            user_id: Dialer user ID
        """
        try:
            logger.info(f"Force starting campaign for user {user_id}")
            
            # Login
            success = await dialer_automation.login_dialer(db, user_id, headless=True)
            
            if success:
                await asyncio.sleep(2)
                # Unpause
                await dialer_automation.click_unpause(db, user_id)
                logger.info(f"✅ Campaign force-started for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error force starting campaign: {e}")
            return False
    
    async def force_stop_campaign(self, db: AsyncSession, user_id: int):
        """
        Manually stop a campaign regardless of schedule
        
        Args:
            db: Database session
            user_id: Dialer user ID
        """
        try:
            logger.info(f"Force stopping campaign for user {user_id}")
            
            # Pause
            await dialer_automation.click_pause(db, user_id)
            await asyncio.sleep(1)
            
            # Logout
            await dialer_automation.logout_dialer(db, user_id)
            logger.info(f"✅ Campaign force-stopped for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error force stopping campaign: {e}")
            return False


# Global instance
campaign_scheduler = CampaignScheduler()
