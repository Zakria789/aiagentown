"""
Pydantic Schemas
API request/response validation ke liye
"""

from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.schemas.call import CallCreate, CallUpdate, CallResponse, CallEventResponse
from app.schemas.auth import LoginRequest, TokenResponse, AgentProfile

__all__ = [
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    "CallCreate",
    "CallUpdate",
    "CallResponse",
    "CallEventResponse",
    "LoginRequest",
    "TokenResponse",
    "AgentProfile",
]
