"""
Customer/Lead Model
Jis customer ko call karni hai uska data
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, Text
from sqlalchemy.sql import func
from app.database import Base


class Customer(Base):
    """
    Customer/Lead model
    Call karne ke liye leads
    """
    __tablename__ = "customers"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Contact Info
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    email = Column(String(100), nullable=True, index=True)
    
    # Address
    city = Column(String(50), nullable=True)
    state = Column(String(50), nullable=True)
    country = Column(String(50), default="Pakistan")
    
    # Lead Status
    status = Column(String(20), default="new")  # new, contacted, qualified, win, loss
    priority = Column(Integer, default=1)  # 1=low, 2=medium, 3=high, 4=urgent
    
    # Assignment
    assigned_agent_id = Column(Integer, nullable=True, index=True)  # FK to agents
    assigned_at = Column(DateTime(timezone=True), nullable=True)
    
    # Call History
    total_calls = Column(Integer, default=0)
    last_called_at = Column(DateTime(timezone=True), nullable=True)
    next_call_scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Lead Source
    source = Column(String(50), nullable=True)  # website, referral, campaign, etc.
    campaign_id = Column(String(50), nullable=True, index=True)
    
    # Notes & Tags
    notes = Column(Text, nullable=True)
    tags = Column(JSON, default=list)  # ["hot-lead", "interested", etc.]
    
    # Custom Data
    custom_fields = Column(JSON, default=dict)  # Extra metadata
    
    # Flags
    do_not_call = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Customer {self.full_name} - {self.phone}>"
    
    def to_dict(self):
        """Model ko dictionary me convert karo"""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "phone": self.phone,
            "email": self.email,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "status": self.status,
            "priority": self.priority,
            "assigned_agent_id": self.assigned_agent_id,
            "total_calls": self.total_calls,
            "last_called_at": self.last_called_at.isoformat() if self.last_called_at else None,
            "next_call_scheduled_at": self.next_call_scheduled_at.isoformat() if self.next_call_scheduled_at else None,
            "source": self.source,
            "tags": self.tags,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
