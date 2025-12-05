"""
Dialer User Model
User credentials for logging into external dialer systems
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class DialerUser(Base):
    """
    User credentials for dialer login
    Multiple users can be assigned to one agent
    """
    __tablename__ = "dialer_users"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User credentials
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # Will be encrypted
    
    # Dialer configuration
    dialer_url = Column(String(500), nullable=False)  # URL of dialer system
    dialer_type = Column(String(50), default="generic")  # generic, vicidial, goautodial, etc.
    
    # Agent assignment
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"))
    agent = relationship("Agent", back_populates="dialer_users")
    
    # Status
    is_active = Column(Boolean, default=True)
    is_logged_in = Column(Boolean, default=False)  # Current login status
    last_login = Column(DateTime, nullable=True)
    
    # Campaign Schedule
    schedule_enabled = Column(Boolean, default=False)
    start_time = Column(String(5), nullable=True)  # "09:00" format (24-hour)
    end_time = Column(String(5), nullable=True)    # "17:00" format (24-hour)
    timezone = Column(String(50), default="UTC")   # Timezone for schedule
    days_of_week = Column(String(100), nullable=True)  # "monday,tuesday,wednesday" comma-separated
    auto_login = Column(Boolean, default=False)    # Auto-login at start_time
    auto_unpause = Column(Boolean, default=False)  # Auto-unpause after login
    
    # Browser session info
    session_id = Column(String(255), nullable=True)  # For tracking browser sessions
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<DialerUser {self.username} -> Agent {self.agent_id}>"
