"""
Agent schemas
Agent create, update, response
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict
from datetime import datetime


class AgentBase(BaseModel):
    """Base agent schema"""
    agent_id: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    role: str = Field(default="agent", pattern="^(agent|supervisor|admin)$")
    permissions: List[str] = []


class AgentCreate(AgentBase):
    """Agent creation schema"""
    password: str = Field(..., min_length=6, description="Agent password")
    dialer_extension: Optional[str] = None
    campaign_script: Optional[str] = Field(None, description="Agent's campaign script (HumeAI system prompt)")
    voice_gender: Optional[str] = Field("male", pattern="^(male|female)$", description="Voice gender for HumeAI")
    voice_style: Optional[str] = Field("professional", pattern="^(professional|friendly|confident)$", description="Voice style")
    hume_rules: Optional[Dict] = Field(None, description="HumeAI configuration rules (event_messages, timeouts, etc.)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "AG001",
                "full_name": "Ahmed Khan",
                "email": "ahmed@example.com",
                "phone": "+923001234567",
                "password": "secure_password",
                "role": "agent",
                "permissions": ["make_calls", "view_customers"],
                "campaign_script": "Hello! I'm calling about our premium product...",
                "voice_gender": "male",
                "voice_style": "professional",
                "hume_rules": {
                    "event_messages": {
                        "on_new_chat": {"enabled": True, "text": "Hello!"}
                    },
                    "timeouts": {
                        "inactivity": {"enabled": True, "duration_secs": 30}
                    }
                }
            }
        }


class AgentUpdate(BaseModel):
    """Agent update schema"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = Field(None, pattern="^(agent|supervisor|admin)$")
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None
    dialer_extension: Optional[str] = None
    dialer_config: Optional[Dict] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Ahmed Khan Updated",
                "phone": "+923009876543",
                "permissions": ["make_calls", "view_customers", "view_reports"]
            }
        }


class AgentResponse(AgentBase):
    """Agent response schema"""
    id: int
    is_active: bool
    is_online: bool
    total_calls: Optional[int] = 0
    total_wins: Optional[int] = 0
    total_losses: Optional[int] = 0
    average_call_duration: Optional[int] = 0
    dialer_extension: Optional[str] = None
    campaign_script: Optional[str] = None
    hume_config_id: Optional[str] = None
    hume_voice_id: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    last_call_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "agent_id": "AG001",
                "full_name": "Ahmed Khan",
                "email": "ahmed@example.com",
                "phone": "+923001234567",
                "role": "agent",
                "permissions": ["make_calls", "view_customers"],
                "is_active": True,
                "is_online": False,
                "total_calls": 150,
                "total_wins": 45,
                "total_losses": 105,
                "average_call_duration": 320,
                "campaign_script": "Hello! I'm calling about...",
                "hume_config_id": "550e8400-e29b-41d4-a716-446655440000",
                "hume_voice_id": "248be419-c632-4f23-adf1-5324ed7dbf1d",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class AgentListResponse(BaseModel):
    """Agent list response with pagination"""
    total: int
    page: int
    page_size: int
    agents: List[AgentResponse]


class AgentStatsResponse(BaseModel):
    """Agent statistics"""
    agent_id: int
    total_calls: int
    total_wins: int
    total_losses: int
    win_rate: float
    average_call_duration: int
    total_talk_time: int
    calls_today: int
    calls_this_week: int
    calls_this_month: int
