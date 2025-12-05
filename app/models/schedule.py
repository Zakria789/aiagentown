"""
Schedule Model
Call scheduling aur follow-up automation
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Schedule(Base):
    """
    Schedule model
    Call scheduling aur follow-up tracking
    """
    __tablename__ = "schedules"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Relations
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Schedule Type
    schedule_type = Column(String(20), default="manual")  # manual, auto, follow_up
    
    # Timing
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    timezone = Column(String(50), default="Asia/Karachi")
    
    # Status
    status = Column(String(20), default="pending")  
    # pending, completed, cancelled, failed, rescheduled
    
    # Priority
    priority = Column(Integer, default=1)  # 1-4 (low to urgent)
    
    # Linked Call (jab call ho jaye)
    call_id = Column(String(100), nullable=True)
    
    # Notes
    notes = Column(String(500), nullable=True)
    
    # Auto-scheduling metadata
    attempt_number = Column(Integer, default=1)  # Kitni baar try kiya
    max_attempts = Column(Integer, default=3)
    
    # Follow-up chain
    parent_call_id = Column(String(100), nullable=True)  # Previous call reference
    is_follow_up = Column(Boolean, default=False)
    
    # Metadata
    custom_data = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Schedule {self.id} - {self.scheduled_at}>"
    
    def to_dict(self):
        """Model ko dictionary me convert karo"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "customer_id": self.customer_id,
            "schedule_type": self.schedule_type,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "timezone": self.timezone,
            "status": self.status,
            "priority": self.priority,
            "call_id": self.call_id,
            "notes": self.notes,
            "attempt_number": self.attempt_number,
            "is_follow_up": self.is_follow_up,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
