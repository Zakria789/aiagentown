"""
FastAPI Main Application
Entry point for the call center system
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from logging.handlers import RotatingFileHandler
import os

from app.config import settings
from app.database import init_db, close_db
from app.redis_client import redis_client
from app.api import auth, agents, calls, customers, websocket, dialer_users, webhooks, training, analytics, audio_bridge, webrtc_bridge, agent_management
from app.services.dialer_automation import dialer_automation
from app.services.campaign_scheduler import campaign_scheduler
from app.services.calltools_monitor import initialize_calltools_monitor, shutdown_calltools_monitor

# Logging setup
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management
    Startup aur shutdown events
    """
    # Startup
    logger.info("Starting FastAPI Call Center Application...")
    
    try:
        # Redis connect
        await redis_client.connect()
        logger.info("Redis connected")
        
        # Database initialize (optional - use Alembic in production)
        if settings.DEBUG:
            await init_db()
            logger.info("Database initialized")
        
        # Initialize browser automation (optional - only if needed)
        try:
            await dialer_automation.initialize()
            logger.info("Browser automation initialized")
        except Exception as e:
            logger.warning(f"Browser automation failed to initialize (continuing without it): {e}")
        
        # Start campaign scheduler for automatic schedule checking
        try:
            await campaign_scheduler.start()
            logger.info("Campaign scheduler started - checking schedules every minute")
        except Exception as e:
            logger.warning(f"Campaign scheduler failed to start (continuing without it): {e}")
        
        # CallTools monitor will be started manually via API endpoint
        # Not auto-starting on startup to avoid unnecessary connections
        if settings.DIALER_PROVIDER == "calltools":
            logger.info("CallTools provider configured - use /api/agents/{id}/start to begin monitoring")
        
        logger.info(f"Application ready on {settings.HOST}:{settings.PORT}")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    try:
        # Stop CallTools monitor if running
        try:
            await shutdown_calltools_monitor()
            logger.info("CallTools monitor stopped")
        except Exception as e:
            logger.debug(f"CallTools monitor not running: {e}")
        
        # Stop campaign scheduler
        try:
            await campaign_scheduler.stop()
            logger.info("Campaign scheduler stopped")
        except Exception as e:
            logger.debug(f"Campaign scheduler stop: {e}")
        
        # Shutdown browser automation
        await dialer_automation.shutdown()
        logger.info("Browser automation shut down")
        
        # Redis disconnect
        await redis_client.disconnect()
        logger.info("Redis disconnected")
        
        # Database close
        await close_db()
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# FastAPI app instance
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered call center system with real-time voice agents",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Sare exceptions ko handle karo
    Production me detailed errors nahi dikhate
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error"}
        )


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint"""
    return {
        "message": "FastAPI Call Center System",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "disabled"
    }


# API Routes
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(agent_management.router, prefix="/api", tags=["Agent Management"])
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
app.include_router(customers.router, prefix="/api/customers", tags=["Customers"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
app.include_router(audio_bridge.router, prefix="/ws", tags=["Audio Bridge"])
app.include_router(webrtc_bridge.router, prefix="/ws", tags=["WebRTC Bridge"])
app.include_router(dialer_users.router, tags=["Dialer Users"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(training.router, tags=["Training"])
app.include_router(analytics.router, tags=["Analytics"])


# Startup message
logger.info(f"""
╔══════════════════════════════════════════════════════════╗
║  FastAPI Call Center - AI Voice Agent System            ║
║  Version: {settings.APP_VERSION}                                     ║
║  Environment: {settings.ENVIRONMENT}                              ║
║  Dialer: {settings.DIALER_PROVIDER.upper()}                                  ║
╚══════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )
