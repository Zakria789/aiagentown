"""
Call Model
Har call ka record aur call events
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, ForeignKey, Float
from sqlalchemy.sql import func
from app.database import Base


class Call(Base):
    """
    Call record model
    Har call ka complete data
    """
    __tablename__ = "calls"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    call_id = Column(String(100), unique=True, index=True, nullable=False)  # UUID
    
    # Participants
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    # Phone Numbers
    from_number = Column(String(20), nullable=False)  # Dialer number
    to_number = Column(String(20), nullable=False)    # Customer number
    
    # Call Status
    status = Column(String(20), default="initiated")  
    # initiated, ringing, answered, in_progress, completed, failed, no_answer, busy
    
    # Call Outcome (Result)
    outcome = Column(String(20), nullable=True)
    # win, loss, follow_up, no_answer, wrong_number, callback, not_interested
    
    # Auto-Disposition Fields
    disposition = Column(String(50), nullable=True)  # Auto-determined disposition
    disposition_confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    disposition_details = Column(Text, nullable=True)  # JSON details of analysis
    
    # Duration
    duration_seconds = Column(Integer, default=0)
    talk_time_seconds = Column(Integer, default=0)  # Actual conversation time
    
    # Timestamps
    initiated_at = Column(DateTime(timezone=True), server_default=func.now())
    answered_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Dialer Info
    dialer_call_sid = Column(String(100), nullable=True)  # Twilio/Vonage call ID
    dialer_provider = Column(String(20), default="twilio")
    
    # AI Analysis
    transcript = Column(Text, nullable=True)  # Full conversation transcript
    summary = Column(Text, nullable=True)     # AI-generated summary
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    sentiment_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Customer Responses
    customer_interest_level = Column(Integer, nullable=True)  # 1-10
    objections = Column(JSON, default=list)  # ["price", "timing", etc.]
    
    # Recording
    recording_url = Column(String(500), nullable=True)
    recording_duration = Column(Integer, nullable=True)
    
    # Follow-up
    needs_follow_up = Column(String(10), default="no")  # yes, no, maybe
    follow_up_date = Column(DateTime(timezone=True), nullable=True)
    follow_up_notes = Column(Text, nullable=True)
    
    # Metadata
    tags = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    custom_data = Column(JSON, default=dict)
    
    # Quality Metrics
    quality_score = Column(Float, nullable=True)  # 0-100
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Call {self.call_id} - {self.status}>"
    
    def to_dict(self):
        """Model ko dictionary me convert karo"""
        return {
            "id": self.id,
            "call_id": self.call_id,
            "agent_id": self.agent_id,
            "customer_id": self.customer_id,
            "from_number": self.from_number,
            "to_number": self.to_number,
            "status": self.status,
            "outcome": self.outcome,
            "duration_seconds": self.duration_seconds,
            "talk_time_seconds": self.talk_time_seconds,
            "initiated_at": self.initiated_at.isoformat() if self.initiated_at else None,
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "transcript": self.transcript,
            "summary": self.summary,
            "sentiment": self.sentiment,
            "recording_url": self.recording_url,
            "needs_follow_up": self.needs_follow_up,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "tags": self.tags,
            "notes": self.notes,
        }


class CallEvent(Base):
    """
    Call events log
    Har call ki detailed timeline
    """
    __tablename__ = "call_events"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    call_id = Column(String(100), ForeignKey("calls.call_id"), index=True, nullable=False)
    
    # Event Type
    event_type = Column(String(50), nullable=False)
    # ringing, answered, speech_started, speech_ended, interrupt, 
    # silence_detected, error, hung_up, etc.
    
    # Event Data
    event_data = Column(JSON, default=dict)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<CallEvent {self.call_id} - {self.event_type}>"
