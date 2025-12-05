"""
Notification Service
Sends alerts for critical events: login failures, call errors, system issues
"""
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import logging
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    DATABASE = "database"


class Notification(Base):
    """
    Notification records in database
    """
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Notification Details
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="medium")
    
    # Classification
    category = Column(String(50), nullable=False, index=True)
    # login_failure, call_error, disposition_issue, shift_anomaly, 
    # system_error, performance_warning
    
    # Related Entities
    agent_id = Column(Integer, nullable=True, index=True)
    call_id = Column(Integer, nullable=True)
    dialer_user_id = Column(Integer, nullable=True)
    
    # Metadata
    details = Column(JSON, default=dict)
    
    # Delivery Status
    channels = Column(JSON, default=list)  # ["email", "sms", "webhook"]
    delivered = Column(Boolean, default=False)
    delivery_attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    
    # Read Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority,
            "category": self.category,
            "agent_id": self.agent_id,
            "call_id": self.call_id,
            "details": self.details,
            "delivered": self.delivered,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class NotificationService:
    """
    Centralized notification management
    """
    
    def __init__(self):
        self.enabled_channels: List[NotificationChannel] = [
            NotificationChannel.DATABASE  # Always enabled
        ]
        
        # Configuration for different channels
        self.config = {
            "email": {
                "enabled": False,
                "smtp_server": None,
                "recipients": []
            },
            "sms": {
                "enabled": False,
                "provider": None,
                "recipients": []
            },
            "webhook": {
                "enabled": False,
                "urls": []
            }
        }
    
    async def send_notification(
        self,
        db: AsyncSession,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        category: str = "general",
        agent_id: Optional[int] = None,
        call_id: Optional[int] = None,
        dialer_user_id: Optional[int] = None,
        details: Optional[Dict] = None,
        channels: Optional[List[NotificationChannel]] = None
    ) -> int:
        """
        Send a notification through specified channels
        
        Returns:
            Notification ID
        """
        # Create notification record
        notification = Notification(
            title=title,
            message=message,
            priority=priority.value,
            category=category,
            agent_id=agent_id,
            call_id=call_id,
            dialer_user_id=dialer_user_id,
            details=details or {},
            channels=[c.value for c in (channels or self.enabled_channels)]
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        logger.info(f"Notification created: {title} (Priority: {priority.value})")
        
        # Attempt delivery through enabled channels
        if channels:
            await self._deliver_notification(notification, channels)
        
        return notification.id
    
    async def _deliver_notification(
        self,
        notification: Notification,
        channels: List[NotificationChannel]
    ):
        """Attempt to deliver notification through specified channels"""
        for channel in channels:
            try:
                if channel == NotificationChannel.EMAIL:
                    await self._send_email(notification)
                elif channel == NotificationChannel.SMS:
                    await self._send_sms(notification)
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook(notification)
                # DATABASE is handled by default (already saved)
            except Exception as e:
                logger.error(f"Failed to deliver notification via {channel.value}: {e}")
    
    async def _send_email(self, notification: Notification):
        """Send email notification"""
        if not self.config["email"]["enabled"]:
            logger.debug("Email notifications not configured")
            return
        
        # TODO: Integrate with email service (SMTP, SendGrid, etc.)
        logger.info(f"Email notification would be sent: {notification.title}")
    
    async def _send_sms(self, notification: Notification):
        """Send SMS notification"""
        if not self.config["sms"]["enabled"]:
            logger.debug("SMS notifications not configured")
            return
        
        # TODO: Integrate with SMS service (Twilio, etc.)
        logger.info(f"SMS notification would be sent: {notification.title}")
    
    async def _send_webhook(self, notification: Notification):
        """Send webhook notification"""
        if not self.config["webhook"]["enabled"]:
            logger.debug("Webhook notifications not configured")
            return
        
        # TODO: Send HTTP POST to webhook URLs
        logger.info(f"Webhook notification would be sent: {notification.title}")
    
    # ========== Pre-built Notification Templates ==========
    
    async def notify_login_failure(
        self,
        db: AsyncSession,
        dialer_user_id: int,
        username: str,
        error: str,
        attempts: int
    ):
        """Notify about dialer login failure"""
        return await self.send_notification(
            db=db,
            title=f"Login Failed: {username}",
            message=f"Failed to login after {attempts} attempts. Error: {error}",
            priority=NotificationPriority.HIGH,
            category="login_failure",
            dialer_user_id=dialer_user_id,
            details={
                "username": username,
                "error": error,
                "attempts": attempts,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def notify_call_error(
        self,
        db: AsyncSession,
        call_id: int,
        agent_id: int,
        error: str
    ):
        """Notify about call error"""
        return await self.send_notification(
            db=db,
            title=f"Call Error: Call #{call_id}",
            message=f"Error during call: {error}",
            priority=NotificationPriority.MEDIUM,
            category="call_error",
            call_id=call_id,
            agent_id=agent_id,
            details={
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def notify_disposition_issue(
        self,
        db: AsyncSession,
        call_id: int,
        agent_id: int,
        confidence: float,
        disposition: str
    ):
        """Notify about low-confidence disposition"""
        return await self.send_notification(
            db=db,
            title=f"Low Confidence Disposition: Call #{call_id}",
            message=f"Auto-disposition has low confidence ({confidence:.2%}). Disposition: {disposition}",
            priority=NotificationPriority.LOW,
            category="disposition_issue",
            call_id=call_id,
            agent_id=agent_id,
            details={
                "confidence": confidence,
                "disposition": disposition,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def notify_shift_anomaly(
        self,
        db: AsyncSession,
        agent_id: int,
        dialer_user_id: int,
        anomaly_type: str,
        description: str
    ):
        """Notify about shift management anomaly"""
        return await self.send_notification(
            db=db,
            title=f"Shift Anomaly: {anomaly_type}",
            message=description,
            priority=NotificationPriority.MEDIUM,
            category="shift_anomaly",
            agent_id=agent_id,
            dialer_user_id=dialer_user_id,
            details={
                "anomaly_type": anomaly_type,
                "description": description,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def notify_system_error(
        self,
        db: AsyncSession,
        component: str,
        error: str,
        severity: NotificationPriority = NotificationPriority.HIGH
    ):
        """Notify about system-level error"""
        return await self.send_notification(
            db=db,
            title=f"System Error: {component}",
            message=f"Error in {component}: {error}",
            priority=severity,
            category="system_error",
            details={
                "component": component,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def notify_performance_warning(
        self,
        db: AsyncSession,
        metric: str,
        value: float,
        threshold: float,
        agent_id: Optional[int] = None
    ):
        """Notify about performance threshold breach"""
        return await self.send_notification(
            db=db,
            title=f"Performance Warning: {metric}",
            message=f"{metric} is {value:.2f}, threshold: {threshold:.2f}",
            priority=NotificationPriority.MEDIUM,
            category="performance_warning",
            agent_id=agent_id,
            details={
                "metric": metric,
                "value": value,
                "threshold": threshold,
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Global instance
notification_service = NotificationService()
