"""
Custom exceptions
Application-specific errors
"""

from fastapi import HTTPException, status


class AgentNotFoundException(HTTPException):
    """Agent not found exception"""
    def __init__(self, agent_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )


class CustomerNotFoundException(HTTPException):
    """Customer not found exception"""
    def __init__(self, customer_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )


class CallNotFoundException(HTTPException):
    """Call not found exception"""
    def __init__(self, call_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call {call_id} not found"
        )


class InvalidCredentialsException(HTTPException):
    """Invalid login credentials"""
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


class AgentAlreadyOnCallException(HTTPException):
    """Agent already on another call"""
    def __init__(self, agent_id: int):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent {agent_id} is already on another call"
        )


class DialerException(HTTPException):
    """Dialer API error"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Dialer error: {message}"
        )


class HumeAIException(HTTPException):
    """HumeAI API error"""
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"HumeAI error: {message}"
        )


class WebSocketConnectionError(Exception):
    """WebSocket connection failed"""
    pass


class AudioProcessingError(Exception):
    """Audio processing failed"""
    pass
