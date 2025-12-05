"""
Dialer Service
Twilio/Vonage integration for call initiation
"""

import logging
from typing import Optional, Dict, Any
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

# Vonage optional (Pydantic 2 compatibility issue)
try:
    import vonage
    VONAGE_AVAILABLE = True
except (ImportError, TypeError):
    VONAGE_AVAILABLE = False
    vonage = None

from app.config import settings
from app.core.exceptions import DialerException

logger = logging.getLogger(__name__)


class BaseDialer:
    """Base dialer interface"""
    
    async def initiate_call(
        self,
        to_number: str,
        from_number: str,
        webhook_url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Initiate outbound call"""
        raise NotImplementedError
    
    async def end_call(self, call_sid: str) -> bool:
        """End active call"""
        raise NotImplementedError
    
    async def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """Get call status"""
        raise NotImplementedError


class TwilioDialer(BaseDialer):
    """
    Twilio dialer implementation
    Production-ready call initiation
    """
    
    def __init__(self):
        try:
            self.client = TwilioClient(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            logger.info("Twilio client initialized")
        except Exception as e:
            logger.error(f"Twilio initialization failed: {e}")
            raise DialerException(f"Twilio init error: {e}")
    
    async def initiate_call(
        self,
        to_number: str,
        from_number: str = None,
        webhook_url: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Twilio se call initiate karo
        
        Args:
            to_number: Customer ka number
            from_number: Twilio number (optional, default settings se)
            webhook_url: Voice webhook URL
        
        Returns:
            Call details dict with call_sid, status, etc.
        """
        try:
            from_number = from_number or settings.TWILIO_PHONE_NUMBER
            webhook_url = webhook_url or settings.TWILIO_VOICE_URL
            
            # Twilio call create karo
            call = self.client.calls.create(
                to=to_number,
                from_=from_number,
                url=webhook_url,
                status_callback=f"{webhook_url}/status",
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                record=settings.CALL_RECORDING_ENABLED,
                timeout=30,
                **kwargs
            )
            
            logger.info(f"Twilio call initiated: {call.sid} to {to_number}")
            
            return {
                "call_sid": call.sid,
                "status": call.status,
                "direction": call.direction,
                "from": call.from_,
                "to": call.to,
                "provider": "twilio"
            }
            
        except TwilioRestException as e:
            logger.error(f"Twilio call failed: {e}")
            raise DialerException(f"Twilio error: {e.msg}")
        except Exception as e:
            logger.error(f"Unexpected error initiating call: {e}")
            raise DialerException(f"Call initiation failed: {str(e)}")
    
    async def end_call(self, call_sid: str) -> bool:
        """
        Active call ko end karo
        
        Args:
            call_sid: Twilio call SID
        
        Returns:
            True if successful
        """
        try:
            call = self.client.calls(call_sid).update(status='completed')
            logger.info(f"Call ended: {call_sid}")
            return True
        except TwilioRestException as e:
            logger.error(f"Failed to end call {call_sid}: {e}")
            return False
    
    async def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """
        Call status check karo
        
        Args:
            call_sid: Twilio call SID
        
        Returns:
            Call status details
        """
        try:
            call = self.client.calls(call_sid).fetch()
            
            return {
                "call_sid": call.sid,
                "status": call.status,
                "duration": call.duration,
                "from": call.from_,
                "to": call.to,
                "direction": call.direction,
                "answered_by": call.answered_by,
            }
        except TwilioRestException as e:
            logger.error(f"Failed to fetch call status {call_sid}: {e}")
            raise DialerException(f"Status fetch failed: {e.msg}")


class VonageDialer(BaseDialer):
    """
    Vonage (formerly Nexmo) dialer implementation
    Alternative to Twilio
    """
    
    def __init__(self):
        if not VONAGE_AVAILABLE:
            raise DialerException("Vonage library not available (Pydantic 2 compatibility issue)")
        
        try:
            self.client = vonage.Client(
                key=settings.VONAGE_API_KEY,
                secret=settings.VONAGE_API_SECRET
            )
            self.voice = vonage.Voice(self.client)
            logger.info("Vonage client initialized")
        except Exception as e:
            logger.error(f"Vonage initialization failed: {e}")
            raise DialerException(f"Vonage init error: {e}")
    
    async def initiate_call(
        self,
        to_number: str,
        from_number: str = None,
        webhook_url: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Vonage se call initiate karo
        """
        try:
            from_number = from_number or settings.VONAGE_NUMBER
            
            response = self.voice.create_call({
                'to': [{'type': 'phone', 'number': to_number}],
                'from': {'type': 'phone', 'number': from_number},
                'answer_url': [webhook_url] if webhook_url else None,
                'event_url': [f"{webhook_url}/events"] if webhook_url else None,
            })
            
            logger.info(f"Vonage call initiated: {response['uuid']} to {to_number}")
            
            return {
                "call_sid": response['uuid'],
                "status": response['status'],
                "direction": response['direction'],
                "from": from_number,
                "to": to_number,
                "provider": "vonage"
            }
            
        except Exception as e:
            logger.error(f"Vonage call failed: {e}")
            raise DialerException(f"Vonage error: {str(e)}")
    
    async def end_call(self, call_sid: str) -> bool:
        """Vonage call end karo"""
        try:
            self.voice.update_call(call_sid, action='hangup')
            logger.info(f"Vonage call ended: {call_sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to end Vonage call {call_sid}: {e}")
            return False
    
    async def get_call_status(self, call_sid: str) -> Dict[str, Any]:
        """Vonage call status"""
        try:
            call = self.voice.get_call(call_sid)
            return {
                "call_sid": call['uuid'],
                "status": call['status'],
                "duration": call.get('duration'),
                "from": call.get('from'),
                "to": call.get('to'),
                "direction": call.get('direction'),
            }
        except Exception as e:
            logger.error(f"Failed to fetch Vonage call status: {e}")
            raise DialerException(f"Status fetch failed: {str(e)}")


class DialerService:
    """
    Unified dialer service
    Provider-agnostic interface
    """
    
    def __init__(self):
        """Initialize dialer based on configuration"""
        provider = settings.DIALER_PROVIDER.lower()
        
        if provider == "twilio":
            self.dialer = TwilioDialer()
        elif provider == "vonage":
            self.dialer = VonageDialer()
        elif provider == "calltools":
            # CallTools uses direct WebRTC connection, no dialer needed
            self.dialer = None
            logger.info("CallTools mode - using direct WebRTC connection")
        else:
            raise ValueError(f"Unknown dialer provider: {provider}")
        
        if self.dialer:
            logger.info(f"Dialer service initialized with provider: {provider}")
    
    async def make_call(
        self,
        to_number: str,
        from_number: str = None,
        webhook_url: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Unified call initiation
        Provider automatically select hoga
        """
        return await self.dialer.initiate_call(
            to_number=to_number,
            from_number=from_number,
            webhook_url=webhook_url,
            **kwargs
        )
    
    async def hangup(self, call_sid: str) -> bool:
        """Call end karo"""
        return await self.dialer.end_call(call_sid)
    
    async def get_status(self, call_sid: str) -> Dict[str, Any]:
        """Call status get karo"""
        return await self.dialer.get_call_status(call_sid)


# Global dialer instance
dialer_service = DialerService()


def get_dialer_service() -> DialerService:
    """Dependency injection ke liye"""
    return dialer_service
