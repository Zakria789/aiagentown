"""
Agent Model
Call center agent ka account aur profile
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Agent(Base):
    """
    Agent/User model
    Har agent ka apna ID aur password hoga
    """
    __tablename__ = "agents"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Authentication
    agent_id = Column(String(50), unique=True, index=True, nullable=False)  # Login ID
    password_hash = Column(String(255), nullable=False)  # Bcrypt hash
    
    # Personal Info
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)  # Real-time presence
    
    # Role & Permissions
    role = Column(String(20), default="agent")  # agent, supervisor, admin
    permissions = Column(JSON, default=list)  # ["make_calls", "view_reports", etc.]
    
    # Statistics (cached from calls table)
    total_calls = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_losses = Column(Integer, default=0)
    average_call_duration = Column(Integer, default=0)  # seconds
    
    # Dialer Configuration
    dialer_extension = Column(String(50), nullable=True)  # Agent ka dialer extension
    dialer_config = Column(JSON, default=dict)  # Extra config
    
    # Campaign Configuration
    campaign_script = Column(Text, nullable=True)  # AI agent's sales script/prompt
    
    # HumeAI Configuration
    hume_config_id = Column(String(100), nullable=True)  # HumeAI config ID
    hume_voice_id = Column(String(100), nullable=True)   # HumeAI voice ID
    
    # Relationships
    dialer_users = relationship("DialerUser", back_populates="agent", cascade="all, delete-orphan")
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_call_at = Column(DateTime(timezone=True), nullable=True)
    
    @property
    def name(self):
        """Alias for full_name for API compatibility"""
        return self.full_name
    
    def __repr__(self):
        return f"<Agent {self.agent_id} - {self.full_name}>"
    
    def to_dict(self):
        """Model ko dictionary me convert karo (API response ke liye)"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "is_active": self.is_active,
            "is_online": self.is_online,
            "role": self.role,
            "permissions": self.permissions,
            "total_calls": self.total_calls,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "average_call_duration": self.average_call_duration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
