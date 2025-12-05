"""
Analytics API Routes
Advanced reporting and business intelligence endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional

from app.database import get_db
from app.services.analytics_service import analytics_service
from app.core.dependencies import get_current_user
from app.models.agent import Agent

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/agent/performance")
async def get_agent_performance(
    agent_id: int,
    start_date: Optional[datetime] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    """
    Get comprehensive agent performance metrics
    - Total calls, success rate, duration stats
    - Disposition breakdown
    - Quality scores
    """
    # Authorization: agents can only view their own data, admins can view all
    if current_user.role != "admin" and current_user.id != agent_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this data")
    
    metrics = await analytics_service.get_agent_performance(
        db=db,
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return metrics


@router.get("/dashboard/realtime")
async def get_realtime_dashboard(
    agent_id: Optional[int] = Query(None, description="Filter by agent ID"),
    db: AsyncSession = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    """
    Real-time dashboard metrics
    - Active calls
    - Today's statistics
    - Hourly breakdown
    """
    # If non-admin, force to own agent_id
    if current_user.role != "admin":
        agent_id = current_user.id
    
    dashboard = await analytics_service.get_realtime_dashboard(
        db=db,
        agent_id=agent_id
    )
    
    return dashboard


@router.get("/campaign/summary")
async def get_campaign_analytics(
    start_date: datetime = Query(..., description="Campaign start date"),
    end_date: datetime = Query(..., description="Campaign end date"),
    db: AsyncSession = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    """
    Campaign-wide analytics and insights
    - Total calls and agents
    - Best performing agents
    - Peak hours
    - Disposition summary
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    analytics = await analytics_service.get_campaign_analytics(
        db=db,
        start_date=start_date,
        end_date=end_date
    )
    
    return analytics


@router.get("/conversion/funnel")
async def get_conversion_funnel(
    agent_id: Optional[int] = Query(None, description="Filter by agent ID"),
    days: int = Query(7, description="Number of days to analyze", ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    """
    Conversion funnel analysis
    - Total Calls → Connected → Interested → Sales
    - Conversion rates at each stage
    """
    # Non-admin can only view own funnel
    if current_user.role != "admin":
        agent_id = current_user.id
    
    funnel = await analytics_service.get_conversion_funnel(
        db=db,
        agent_id=agent_id,
        days=days
    )
    
    return funnel


@router.get("/customer/{customer_id}/insights")
async def get_customer_insights(
    customer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    """
    Detailed customer interaction history
    - All calls with this customer
    - Engagement metrics
    - Call frequency
    - Last disposition
    """
    insights = await analytics_service.get_customer_insights(
        db=db,
        customer_id=customer_id
    )
    
    return insights


@router.get("/reports/daily")
async def get_daily_report(
    date: Optional[datetime] = Query(None, description="Report date (defaults to today)"),
    db: AsyncSession = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    """
    Daily summary report
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not date:
        date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    end_date = date + timedelta(days=1)
    
    report = await analytics_service.get_campaign_analytics(
        db=db,
        start_date=date,
        end_date=end_date
    )
    
    report['report_type'] = 'daily'
    report['report_date'] = date.date().isoformat()
    
    return report


@router.get("/reports/weekly")
async def get_weekly_report(
    start_date: Optional[datetime] = Query(None, description="Week start date (defaults to this Monday)"),
    db: AsyncSession = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    """
    Weekly summary report
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if not start_date:
        today = datetime.utcnow()
        start_date = today - timedelta(days=today.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    end_date = start_date + timedelta(days=7)
    
    report = await analytics_service.get_campaign_analytics(
        db=db,
        start_date=start_date,
        end_date=end_date
    )
    
    report['report_type'] = 'weekly'
    report['week_start'] = start_date.date().isoformat()
    report['week_end'] = end_date.date().isoformat()
    
    return report


@router.get("/export/csv")
async def export_analytics_csv(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Agent = Depends(get_current_user)
):
    """
    Export analytics data as CSV
    TODO: Implement CSV generation and download
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {
        "message": "CSV export endpoint - Implementation pending",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat()
    }
