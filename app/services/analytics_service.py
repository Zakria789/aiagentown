"""
Advanced Analytics Service
Real-time metrics, reporting, and business intelligence
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from collections import defaultdict
import logging

from app.models.call import Call, CallEvent
from app.models.agent import Agent
from app.models.customer import Customer

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Comprehensive analytics and reporting service
    """
    
    async def get_agent_performance(
        self,
        db: AsyncSession,
        agent_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get detailed agent performance metrics
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Query calls
        query = select(Call).where(
            and_(
                Call.agent_id == agent_id,
                Call.created_at >= start_date,
                Call.created_at <= end_date
            )
        )
        result = await db.execute(query)
        calls = result.scalars().all()
        
        # Calculate metrics
        total_calls = len(calls)
        total_duration = sum(c.duration for c in calls if c.duration)
        avg_duration = total_duration / total_calls if total_calls > 0 else 0
        
        # Disposition breakdown
        dispositions = defaultdict(int)
        for call in calls:
            if call.disposition:
                dispositions[call.disposition] += 1
        
        # Success rate (Connected, Sale Made, etc.)
        success_dispositions = ['Connected', 'Sale Made', 'Interested']
        successful_calls = sum(
            dispositions[d] for d in success_dispositions if d in dispositions
        )
        success_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0
        
        # Call outcome analysis
        outcomes = {
            'total_calls': total_calls,
            'successful_calls': successful_calls,
            'success_rate': round(success_rate, 2),
            'average_duration': round(avg_duration, 2),
            'total_duration': total_duration,
            'disposition_breakdown': dict(dispositions),
        }
        
        # Call quality metrics
        quality_scores = [c.ai_quality_score for c in calls if c.ai_quality_score]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        outcomes['average_quality_score'] = round(avg_quality, 2)
        outcomes['calls_with_quality_score'] = len(quality_scores)
        
        return outcomes
    
    async def get_realtime_dashboard(
        self,
        db: AsyncSession,
        agent_id: Optional[int] = None
    ) -> Dict:
        """
        Real-time dashboard metrics for monitoring
        """
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Base query
        base_query = select(Call).where(Call.created_at >= today_start)
        if agent_id:
            base_query = base_query.where(Call.agent_id == agent_id)
        
        result = await db.execute(base_query)
        today_calls = result.scalars().all()
        
        # Active calls (in last 5 minutes)
        active_threshold = now - timedelta(minutes=5)
        active_calls = [
            c for c in today_calls 
            if c.created_at >= active_threshold and c.status in ['active', 'ringing']
        ]
        
        # Calls per hour (last 24 hours)
        hourly_stats = defaultdict(int)
        for call in today_calls:
            hour = call.created_at.hour
            hourly_stats[hour] += 1
        
        return {
            'timestamp': now.isoformat(),
            'today_total_calls': len(today_calls),
            'active_calls': len(active_calls),
            'calls_last_hour': sum(
                1 for c in today_calls 
                if c.created_at >= now - timedelta(hours=1)
            ),
            'hourly_breakdown': dict(hourly_stats),
            'average_call_duration_today': round(
                sum(c.duration for c in today_calls if c.duration) / len(today_calls)
                if today_calls else 0,
                2
            )
        }
    
    async def get_campaign_analytics(
        self,
        db: AsyncSession,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Campaign-wide analytics and insights
        """
        # Get all calls in date range
        query = select(Call).where(
            and_(
                Call.created_at >= start_date,
                Call.created_at <= end_date
            )
        )
        result = await db.execute(query)
        calls = result.scalars().all()
        
        if not calls:
            return {
                'total_calls': 0,
                'message': 'No calls found in this date range'
            }
        
        # Agent performance comparison
        agent_stats = defaultdict(lambda: {'calls': 0, 'duration': 0, 'success': 0})
        for call in calls:
            agent_id = call.agent_id or 0
            agent_stats[agent_id]['calls'] += 1
            agent_stats[agent_id]['duration'] += call.duration or 0
            if call.disposition in ['Connected', 'Sale Made', 'Interested']:
                agent_stats[agent_id]['success'] += 1
        
        # Best performing agent
        best_agent = max(
            agent_stats.items(),
            key=lambda x: x[1]['success'] / x[1]['calls'] if x[1]['calls'] > 0 else 0
        ) if agent_stats else (None, None)
        
        # Time-based insights
        peak_hours = defaultdict(int)
        for call in calls:
            peak_hours[call.created_at.hour] += 1
        
        best_hour = max(peak_hours.items(), key=lambda x: x[1])[0] if peak_hours else None
        
        # Disposition analysis
        disposition_counts = defaultdict(int)
        for call in calls:
            if call.disposition:
                disposition_counts[call.disposition] += 1
        
        return {
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_calls': len(calls),
            'total_agents': len(agent_stats),
            'best_performing_agent_id': best_agent[0] if best_agent[0] else None,
            'best_performing_agent_success_rate': round(
                best_agent[1]['success'] / best_agent[1]['calls'] * 100
                if best_agent[1] and best_agent[1]['calls'] > 0 else 0,
                2
            ),
            'peak_calling_hour': best_hour,
            'disposition_summary': dict(disposition_counts),
            'total_duration_minutes': round(sum(c.duration for c in calls if c.duration) / 60, 2),
            'average_call_duration': round(
                sum(c.duration for c in calls if c.duration) / len(calls),
                2
            )
        }
    
    async def get_conversion_funnel(
        self,
        db: AsyncSession,
        agent_id: Optional[int] = None,
        days: int = 7
    ) -> Dict:
        """
        Analyze conversion funnel: Total Calls → Connected → Interested → Sale
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        base_query = select(Call).where(Call.created_at >= start_date)
        if agent_id:
            base_query = base_query.where(Call.agent_id == agent_id)
        
        result = await db.execute(base_query)
        calls = result.scalars().all()
        
        total = len(calls)
        connected = sum(1 for c in calls if c.disposition == 'Connected')
        interested = sum(1 for c in calls if c.disposition in ['Interested', 'Callback'])
        sales = sum(1 for c in calls if c.disposition == 'Sale Made')
        
        return {
            'funnel': {
                'total_calls': total,
                'connected': connected,
                'interested': interested,
                'sales': sales
            },
            'conversion_rates': {
                'connect_rate': round(connected / total * 100, 2) if total > 0 else 0,
                'interest_rate': round(interested / connected * 100, 2) if connected > 0 else 0,
                'close_rate': round(sales / interested * 100, 2) if interested > 0 else 0,
                'overall_conversion': round(sales / total * 100, 2) if total > 0 else 0
            },
            'period_days': days
        }
    
    async def get_customer_insights(
        self,
        db: AsyncSession,
        customer_id: int
    ) -> Dict:
        """
        Get detailed customer interaction history and insights
        """
        # Get all calls for this customer
        query = select(Call).where(Call.customer_id == customer_id).order_by(Call.created_at.desc())
        result = await db.execute(query)
        calls = result.scalars().all()
        
        if not calls:
            return {'customer_id': customer_id, 'total_calls': 0}
        
        # Get customer details
        customer_query = select(Customer).where(Customer.id == customer_id)
        customer_result = await db.execute(customer_query)
        customer = customer_result.scalar_one_or_none()
        
        # Analyze call history
        call_history = []
        for call in calls:
            call_history.append({
                'call_id': call.call_id,
                'date': call.created_at.isoformat(),
                'duration': call.duration,
                'disposition': call.disposition,
                'agent_id': call.agent_id,
                'summary': call.call_summary
            })
        
        # Engagement metrics
        total_duration = sum(c.duration for c in calls if c.duration)
        avg_duration = total_duration / len(calls) if calls else 0
        
        # Last disposition
        last_disposition = calls[0].disposition if calls else None
        
        # Call frequency
        first_call = calls[-1].created_at if calls else None
        days_since_first = (datetime.utcnow() - first_call).days if first_call else 0
        call_frequency = len(calls) / days_since_first if days_since_first > 0 else 0
        
        return {
            'customer_id': customer_id,
            'customer_name': customer.name if customer else None,
            'customer_phone': customer.phone if customer else None,
            'total_calls': len(calls),
            'first_contact': first_call.isoformat() if first_call else None,
            'last_contact': calls[0].created_at.isoformat() if calls else None,
            'last_disposition': last_disposition,
            'total_engagement_time': total_duration,
            'average_call_duration': round(avg_duration, 2),
            'call_frequency_per_day': round(call_frequency, 2),
            'call_history': call_history[:10]  # Last 10 calls
        }


# Global instance
analytics_service = AnalyticsService()
