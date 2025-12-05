"""
Authentication schemas
Login, token response, etc.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class LoginRequest(BaseModel):
    """Login request body"""
    agent_id: str = Field(..., min_length=3, max_length=50, description="Agent login ID")
    password: str = Field(..., min_length=6, description="Agent password")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "AG001",
                "password": "secure_password_123"
            }
        }


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class AgentProfile(BaseModel):
    """Current agent profile"""
    id: int
    agent_id: str
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    permissions: List[str] = []
    is_active: bool
    is_online: bool
    total_calls: int = 0
    total_wins: int = 0
    total_losses: int = 0
    average_call_duration: int = 0
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    
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
                "is_online": True,
                "total_calls": 150,
                "total_wins": 45,
                "total_losses": 105,
                "average_call_duration": 320
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    old_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)
