"""
Dialer User Schemas
Pydantic models for API validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class DialerUserBase(BaseModel):
    """Base schema for dialer user"""
    username: str = Field(..., min_length=3, max_length=100, description="Dialer login username")
    dialer_url: str = Field(..., description="URL of the dialer system")
    dialer_type: str = Field(default="generic", description="Type of dialer (generic, vicidial, goautodial)")
    is_active: bool = Field(default=True, description="Is user account active")


class CampaignSchedule(BaseModel):
    """Campaign schedule configuration"""
    schedule_enabled: bool = Field(default=False, description="Enable scheduled auto-start")
    start_time: Optional[str] = Field(None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="Start time (HH:MM format, 24-hour)")
    end_time: Optional[str] = Field(None, pattern=r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", description="End time (HH:MM format, 24-hour)")
    timezone: str = Field(default="UTC", description="Timezone (e.g., Asia/Karachi, America/New_York)")
    days_of_week: Optional[List[str]] = Field(None, description="Days to run (monday, tuesday, etc.)")
    auto_login: bool = Field(default=True, description="Auto-login at start time")
    auto_unpause: bool = Field(default=True, description="Auto-unpause after login")
    
    @validator('days_of_week')
    def validate_days(cls, v):
        if v:
            valid_days = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'}
            for day in v:
                if day.lower() not in valid_days:
                    raise ValueError(f"Invalid day: {day}. Must be one of {valid_days}")
        return v


class DialerUserCreate(DialerUserBase):
    """Schema for creating new dialer user"""
    password: str = Field(..., min_length=6, description="Dialer login password")
    agent_id: int = Field(..., description="ID of the agent this user belongs to")
    
    # Optional schedule
    schedule: Optional[CampaignSchedule] = None


class DialerUserUpdate(BaseModel):
    """Schema for updating dialer user"""
    password: Optional[str] = Field(None, min_length=6, description="New password")
    dialer_url: Optional[str] = Field(None, description="New dialer URL")
    dialer_type: Optional[str] = Field(None, description="New dialer type")
    is_active: Optional[bool] = Field(None, description="Active status")
    
    # Schedule updates
    schedule: Optional[CampaignSchedule] = None


class DialerUserResponse(DialerUserBase):
    """Schema for dialer user response"""
    id: int
    agent_id: int
    is_logged_in: bool
    last_login: Optional[datetime]
    session_id: Optional[str]
    
    # Schedule info
    schedule_enabled: bool
    start_time: Optional[str]
    end_time: Optional[str]
    timezone: str
    days_of_week: Optional[str]
    auto_login: bool
    auto_unpause: bool
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DialerUserLogin(BaseModel):
    """Schema for manual dialer login trigger"""
    headless: bool = Field(default=True, description="Run browser in headless mode")


class DialerUserStatus(BaseModel):
    """Schema for dialer user status"""
    user_id: int
    username: str
    is_logged_in: bool
    is_active: bool
    agent_id: int
    last_login: Optional[datetime]
    session_active: bool
