"""
Customer/Lead schemas
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
from datetime import datetime


class CustomerBase(BaseModel):
    """Base customer schema"""
    full_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "Pakistan"


class CustomerCreate(CustomerBase):
    """Customer creation schema"""
    status: str = Field(default="new", pattern="^(new|contacted|qualified|win|loss)$")
    priority: int = Field(default=1, ge=1, le=4)
    source: Optional[str] = None
    campaign_id: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []
    custom_fields: Dict = {}
    
    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "Ali Hassan",
                "phone": "+923001234567",
                "email": "ali@example.com",
                "city": "Karachi",
                "state": "Sindh",
                "country": "Pakistan",
                "status": "new",
                "priority": 2,
                "source": "website",
                "tags": ["hot-lead", "interested"],
                "notes": "Interested in premium package"
            }
        }


class CustomerUpdate(BaseModel):
    """Customer update schema"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(new|contacted|qualified|win|loss)$")
    priority: Optional[int] = Field(None, ge=1, le=4)
    assigned_agent_id: Optional[int] = None
    next_call_scheduled_at: Optional[datetime] = None
    source: Optional[str] = None
    campaign_id: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict] = None
    do_not_call: Optional[bool] = None


class CustomerResponse(CustomerBase):
    """Customer response schema"""
    id: int
    status: str
    priority: int
    assigned_agent_id: Optional[int] = None
    assigned_at: Optional[datetime] = None
    total_calls: int
    last_called_at: Optional[datetime] = None
    next_call_scheduled_at: Optional[datetime] = None
    source: Optional[str] = None
    campaign_id: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None
    do_not_call: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    """Customer list with pagination"""
    total: int
    page: int
    page_size: int
    customers: List[CustomerResponse]


class AssignCustomerRequest(BaseModel):
    """Assign customer to agent"""
    customer_ids: List[int]
    agent_id: int
