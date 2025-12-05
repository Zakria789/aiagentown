"""
Call schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class CallBase(BaseModel):
    """Base call schema"""
    agent_id: int
    customer_id: int
    to_number: str = Field(..., min_length=10)


class CallCreate(CallBase):
    """Call initiation request"""
    notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": 1,
                "customer_id": 5,
                "to_number": "+923001234567",
                "notes": "Follow-up call"
            }
        }


class CallUpdate(BaseModel):
    """Call update schema"""
    status: Optional[str] = None
    outcome: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    needs_follow_up: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    follow_up_notes: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class CallResponse(CallBase):
    """Call response schema"""
    id: int
    call_id: str
    from_number: str
    to_number: str
    status: str
    outcome: Optional[str] = None
    duration_seconds: int
    talk_time_seconds: int
    initiated_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    dialer_call_sid: Optional[str] = None
    dialer_provider: str
    transcript: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    recording_url: Optional[str] = None
    needs_follow_up: str
    follow_up_date: Optional[datetime] = None
    tags: List[str] = []
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CallEventResponse(BaseModel):
    """Call event response"""
    id: int
    call_id: str
    event_type: str
    event_data: Dict
    timestamp: datetime
    
    class Config:
        from_attributes = True


class CallListResponse(BaseModel):
    """Call list with pagination"""
    total: int
    page: int
    page_size: int
    calls: List[CallResponse]


class CallStatsResponse(BaseModel):
    """Call statistics"""
    total_calls: int
    answered_calls: int
    missed_calls: int
    average_duration: int
    total_talk_time: int
    win_rate: float
    outcomes: Dict[str, int]


class InitiateCallRequest(BaseModel):
    """Request to initiate a call"""
    customer_id: int
    notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "customer_id": 5,
                "notes": "Follow-up regarding pricing"
            }
        }


class EndCallRequest(BaseModel):
    """Request to end a call"""
    outcome: str = Field(..., pattern="^(win|loss|follow_up|no_answer|wrong_number|callback|not_interested)$")
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    tags: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "outcome": "follow_up",
                "notes": "Customer wants to discuss with family",
                "follow_up_date": "2024-01-20T14:00:00Z",
                "tags": ["interested", "needs-time"]
            }
        }
