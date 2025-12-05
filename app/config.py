"""
FastAPI Call Center Configuration
Sare environment variables aur settings yahan manage hongay
"""

from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application Settings"""
    
    # App
    APP_NAME: str = "FastAPI Call Center"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    # Redis
    REDIS_URL: str
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # HumeAI
    HUME_API_KEY: str
    HUME_CONFIG_ID: str = ""
    HUME_SECRET_KEY: str = ""
    HUME_WEBSOCKET_URL: str = "wss://api.hume.ai/v0/assistant/chat"
    
    # Dialer
    DIALER_PROVIDER: str = "twilio"  # twilio or vonage or calltools
    
    # CallTools (for automatic call handling)
    CALLTOOLS_URL: str = "https://east-1.calltools.io"
    CALLTOOLS_USERNAME: str = ""
    CALLTOOLS_PASSWORD: str = ""
    CALLTOOLS_AUTO_MONITOR: bool = True  # Auto-start call monitoring
    
    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    TWILIO_VOICE_URL: str = ""
    
    # Vonage
    VONAGE_API_KEY: str = ""
    VONAGE_API_SECRET: str = ""
    VONAGE_NUMBER: str = ""
    VONAGE_APPLICATION_ID: str = ""
    
    # Audio
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHUNK_SIZE: int = 1024
    AUDIO_CHANNELS: int = 1
    AUDIO_FORMAT: str = "LINEAR16"
    
    # Call Configuration
    MAX_CALL_DURATION_SECONDS: int = 1800
    SILENCE_THRESHOLD_SECONDS: int = 3
    INTERRUPT_DETECTION_ENABLED: bool = True
    CALL_RECORDING_ENABLED: bool = True
    
    # Scheduling
    SCHEDULER_TIMEZONE: str = "Asia/Karachi"
    SCHEDULER_WORK_HOURS_START: str = "09:00"
    SCHEDULER_WORK_HOURS_END: str = "18:00"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "30 days"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Performance
    WORKERS: int = 4
    MAX_CONCURRENT_CALLS: int = 100
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 10
    
    # Feature Flags
    ENABLE_CALL_RECORDING: bool = True
    ENABLE_REAL_TIME_ANALYTICS: bool = True
    ENABLE_AUTO_SCHEDULING: bool = True
    ENABLE_SENTIMENT_ANALYSIS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Settings ko cache karke return karta hai
    Yeh function baar baar .env file nahi padhega
    """
    return Settings()


# Global settings instance
settings = get_settings()
