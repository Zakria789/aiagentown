"""
Core utilities exports
"""

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from app.core.dependencies import (
    get_current_agent,
    get_current_active_agent,
    require_role,
    get_optional_agent,
)
from app.core.exceptions import (
    AgentNotFoundException,
    CustomerNotFoundException,
    CallNotFoundException,
    InvalidCredentialsException,
    AgentAlreadyOnCallException,
    DialerException,
    HumeAIException,
    WebSocketConnectionError,
    AudioProcessingError,
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "verify_token",
    "get_current_agent",
    "get_current_active_agent",
    "require_role",
    "get_optional_agent",
    "AgentNotFoundException",
    "CustomerNotFoundException",
    "CallNotFoundException",
    "InvalidCredentialsException",
    "AgentAlreadyOnCallException",
    "DialerException",
    "HumeAIException",
    "WebSocketConnectionError",
    "AudioProcessingError",
]
