"""
AI-Powered Auto-Disposition Engine
Analyzes call data to automatically determine call outcomes
"""
from typing import Dict, Optional, List, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import re

from app.models.call import Call, CallEvent
from app.models.agent import Agent


class DispositionRule:
    """Defines a rule for determining disposition"""
    def __init__(
        self,
        disposition: str,
        keywords: List[str],
        sentiment_threshold: Optional[float] = None,
        duration_min: Optional[int] = None,
        duration_max: Optional[int] = None,
        priority: int = 0
    ):
        self.disposition = disposition
        self.keywords = [kw.lower() for kw in keywords]
        self.sentiment_threshold = sentiment_threshold
        self.duration_min = duration_min
        self.duration_max = duration_max
        self.priority = priority


class DispositionEngine:
    """
    Analyzes call transcripts, duration, events, and HumeAI data
    to automatically determine the most appropriate disposition
    """
    
    # Default disposition rules (can be customized per campaign)
    DEFAULT_RULES = [
        # Do Not Call - Highest priority
        DispositionRule(
            disposition="DNC",
            keywords=["do not call", "don't call", "remove me", "take me off", "stop calling", "unsubscribe", "harassment"],
            priority=100
        ),
        
        # Interested/Connected
        DispositionRule(
            disposition="Connected",
            keywords=["interested", "tell me more", "sounds good", "yes", "sure", "okay let's", "sign me up"],
            sentiment_threshold=0.6,
            duration_min=30,
            priority=90
        ),
        
        # Callback Requested
        DispositionRule(
            disposition="Callback",
            keywords=["call back", "call me back", "later", "not now", "busy", "call tomorrow", "try again"],
            priority=80
        ),
        
        # Not Interested
        DispositionRule(
            disposition="Not Interested",
            keywords=["not interested", "no thank you", "no thanks", "not for me", "don't need"],
            priority=70
        ),
        
        # Voicemail
        DispositionRule(
            disposition="Voicemail",
            keywords=["voicemail", "leave a message", "beep", "not available"],
            duration_max=15,
            priority=85
        ),
        
        # Wrong Number
        DispositionRule(
            disposition="Wrong Number",
            keywords=["wrong number", "who is this", "don't know", "never heard"],
            priority=75
        ),
        
        # No Answer (very short duration, no conversation)
        DispositionRule(
            disposition="No Answer",
            keywords=[],
            duration_max=5,
            priority=60
        ),
    ]
    
    def __init__(self):
        self.rules = self.DEFAULT_RULES.copy()
    
    def add_custom_rule(self, rule: DispositionRule):
        """Add a custom disposition rule"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    async def analyze_call(
        self,
        db: AsyncSession,
        call_id: int,
        transcript: Optional[str] = None,
        hume_metadata: Optional[Dict] = None
    ) -> Tuple[str, float, Dict]:
        """
        Analyze a call and return the disposition
        
        Returns:
            Tuple of (disposition, confidence, analysis_details)
        """
        # Get call data
        result = await db.execute(select(Call).where(Call.id == call_id))
        call = result.scalar_one_or_none()
        
        if not call:
            return "Unknown", 0.0, {"error": "Call not found"}
        
        # Gather all available data
        analysis_data = await self._gather_call_data(db, call, transcript, hume_metadata)
        
        # Apply rules and score each disposition
        scores = self._score_dispositions(analysis_data)
        
        # Get best match
        if not scores:
            return "No Disposition", 0.5, analysis_data
        
        best_disposition = max(scores.items(), key=lambda x: x[1])
        disposition, confidence = best_disposition
        
        analysis_data["scores"] = scores
        analysis_data["selected_disposition"] = disposition
        
        return disposition, confidence, analysis_data
    
    async def _gather_call_data(
        self,
        db: AsyncSession,
        call: Call,
        transcript: Optional[str],
        hume_metadata: Optional[Dict]
    ) -> Dict:
        """Gather all available call data for analysis"""
        data = {
            "call_id": call.id,
            "call_sid": call.dialer_call_sid,
            "duration": call.duration_seconds or 0,
            "call_status": call.status,
            "transcript": transcript or call.transcript or "",
            "hume_metadata": hume_metadata or {},
            "events": []
        }
        
        # Get call events
        result = await db.execute(
            select(CallEvent)
            .where(CallEvent.call_id == call.id)
            .order_by(CallEvent.created_at)
        )
        events = result.scalars().all()
        data["events"] = [
            {
                "event_type": e.event_type,
                "data": e.event_data,
                "timestamp": e.created_at.isoformat()
            }
            for e in events
        ]
        
        # Extract sentiment from HumeAI
        if hume_metadata and "emotions" in hume_metadata:
            data["sentiment_score"] = self._calculate_sentiment(hume_metadata["emotions"])
        else:
            data["sentiment_score"] = None
        
        # Extract conversation metadata
        data["conversation_turns"] = self._count_conversation_turns(transcript or "")
        
        return data
    
    def _calculate_sentiment(self, emotions: Dict) -> float:
        """
        Calculate overall sentiment from HumeAI emotion data
        
        Positive emotions: joy, amusement, contentment, satisfaction
        Negative emotions: anger, disgust, fear, sadness, disappointment
        """
        positive_emotions = ["joy", "amusement", "contentment", "satisfaction", "excitement"]
        negative_emotions = ["anger", "disgust", "fear", "sadness", "disappointment", "frustration"]
        
        positive_score = sum(emotions.get(e, 0) for e in positive_emotions)
        negative_score = sum(emotions.get(e, 0) for e in negative_emotions)
        
        total = positive_score + negative_score
        if total == 0:
            return 0.5  # Neutral
        
        # Return normalized positive sentiment (0-1 scale)
        return positive_score / total
    
    def _count_conversation_turns(self, transcript: str) -> int:
        """Count back-and-forth exchanges in conversation"""
        if not transcript:
            return 0
        
        # Simple heuristic: count speaker changes
        # Format: "Speaker: text"
        lines = transcript.split('\n')
        turns = 0
        last_speaker = None
        
        for line in lines:
            if ':' in line:
                speaker = line.split(':')[0].strip()
                if speaker != last_speaker:
                    turns += 1
                    last_speaker = speaker
        
        return turns
    
    def _score_dispositions(self, analysis_data: Dict) -> Dict[str, float]:
        """
        Score each disposition based on rules
        Returns dict of {disposition: confidence_score}
        """
        scores = {}
        
        for rule in self.rules:
            score = self._evaluate_rule(rule, analysis_data)
            if score > 0:
                # Combine with priority (0-1 scale)
                weighted_score = score * (rule.priority / 100.0)
                
                # Keep highest score for each disposition
                if rule.disposition not in scores or weighted_score > scores[rule.disposition]:
                    scores[rule.disposition] = min(weighted_score, 1.0)
        
        return scores
    
    def _evaluate_rule(self, rule: DispositionRule, data: Dict) -> float:
        """
        Evaluate a single rule against call data
        Returns confidence score 0-1
        """
        score = 0.0
        matches = 0
        total_checks = 0
        
        # Check duration constraints
        if rule.duration_min is not None or rule.duration_max is not None:
            total_checks += 1
            duration = data.get("duration", 0)
            
            if rule.duration_min and duration < rule.duration_min:
                pass  # No match
            elif rule.duration_max and duration > rule.duration_max:
                pass  # No match
            else:
                matches += 1
        
        # Check keywords in transcript
        if rule.keywords:
            total_checks += 1
            transcript = data.get("transcript", "").lower()
            
            keyword_matches = sum(1 for kw in rule.keywords if kw in transcript)
            if keyword_matches > 0:
                matches += 1
                # Bonus for multiple keyword matches
                score += min(keyword_matches * 0.1, 0.3)
        
        # Check sentiment threshold
        if rule.sentiment_threshold is not None and data.get("sentiment_score") is not None:
            total_checks += 1
            sentiment = data["sentiment_score"]
            
            if sentiment >= rule.sentiment_threshold:
                matches += 1
        
        # Calculate base score from matches
        if total_checks > 0:
            base_score = matches / total_checks
            score += base_score
        
        # Normalize to 0-1
        return min(score, 1.0)
    
    async def get_disposition_with_confidence(
        self,
        db: AsyncSession,
        call_id: int,
        transcript: Optional[str] = None,
        hume_metadata: Optional[Dict] = None,
        min_confidence: float = 0.6
    ) -> Tuple[Optional[str], float, Dict]:
        """
        Get disposition only if confidence is above threshold
        
        Returns:
            Tuple of (disposition or None, confidence, details)
        """
        disposition, confidence, details = await self.analyze_call(
            db, call_id, transcript, hume_metadata
        )
        
        if confidence < min_confidence:
            return None, confidence, details
        
        return disposition, confidence, details


# Global instance
disposition_engine = DispositionEngine()


async def auto_disposition_call(
    db: AsyncSession,
    call_id: int,
    transcript: Optional[str] = None,
    hume_metadata: Optional[Dict] = None,
    min_confidence: float = 0.6,
    fallback_disposition: str = "Manual Review"
) -> str:
    """
    Convenience function to auto-disposition a call
    
    Returns the selected disposition (auto or fallback)
    """
    disposition, confidence, details = await disposition_engine.get_disposition_with_confidence(
        db, call_id, transcript, hume_metadata, min_confidence
    )
    
    if disposition is None:
        # Not confident enough, use fallback
        disposition = fallback_disposition
    
    # Update call with disposition
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    
    if call:
        call.disposition = disposition
        call.disposition_confidence = confidence
        call.disposition_details = json.dumps(details)
        await db.commit()
    
    return disposition
