"""
AI Learning Service
Enables HumeAI to learn from live calls and improve over time
"""
import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging

from app.models.call import Call
from app.models.training_content import TrainingContent
from app.services.hume_service import get_hume_session_manager

logger = logging.getLogger(__name__)


class AILearningService:
    """
    Manages continuous learning from live calls
    Automatically improves AI performance based on outcomes
    """
    
    def __init__(self):
        self.min_confidence_for_learning = 0.75
        self.min_calls_for_pattern = 5
    
    async def learn_from_call(
        self,
        db: AsyncSession,
        call: Call,
        auto_update_training: bool = True
    ) -> Dict:
        """
        Extract and store learnings from a completed call
        
        Args:
            db: Database session
            call: Completed Call object
            auto_update_training: Automatically update training content
            
        Returns:
            Dict with learning summary
        """
        if not call.transcript:
            logger.warning(f"No transcript for call {call.id}, skipping learning")
            return {"status": "skipped", "reason": "no_transcript"}
        
        learnings = {
            "call_id": call.id,
            "timestamp": datetime.utcnow().isoformat(),
            "disposition": call.disposition,
            "confidence": call.disposition_confidence,
            "duration": call.duration_seconds,
            "emotions": self._extract_emotions(call),
            "successful_phrases": [],
            "objection_handling": [],
            "conversation_flow": [],
            "learning_score": 0.0
        }
        
        try:
            # Extract successful phrases (if call was successful)
            if call.disposition in ["Connected", "Callback"] and call.disposition_confidence > self.min_confidence_for_learning:
                learnings["successful_phrases"] = self._extract_successful_phrases(call.transcript)
                learnings["learning_score"] += 0.3
            
            # Extract objection handling patterns
            objections = self._detect_objections(call.transcript)
            if objections:
                learnings["objection_handling"] = self._analyze_objection_responses(
                    call.transcript,
                    objections,
                    success=call.disposition == "Connected"
                )
                learnings["learning_score"] += 0.2
            
            # Analyze conversation flow
            learnings["conversation_flow"] = self._analyze_conversation_flow(call.transcript)
            learnings["learning_score"] += 0.1
            
            # Store learnings in database (for future analysis)
            await self._store_learnings(db, call.id, learnings)
            
            # Auto-update training content if enabled
            if auto_update_training and learnings["learning_score"] > 0.4:
                await self._auto_update_training_content(db, call.agent_id, learnings)
            
            logger.info(
                f"Learned from call {call.id}: "
                f"score={learnings['learning_score']:.2f}, "
                f"phrases={len(learnings['successful_phrases'])}, "
                f"objections={len(learnings['objection_handling'])}"
            )
            
            return learnings
            
        except Exception as e:
            logger.error(f"Error learning from call {call.id}: {e}")
            return {"status": "error", "error": str(e)}
    
    def _extract_emotions(self, call: Call) -> Dict:
        """Extract emotion data from call"""
        if not call.disposition_details:
            return {}
        
        try:
            details = json.loads(call.disposition_details) if isinstance(call.disposition_details, str) else call.disposition_details
            return details.get("emotions", {})
        except:
            return {}
    
    def _extract_successful_phrases(self, transcript: str) -> List[Dict]:
        """
        Extract phrases that led to successful outcome
        """
        phrases = []
        
        # Split transcript into turns (AI and Customer)
        turns = self._split_transcript_into_turns(transcript)
        
        # Look for positive responses after AI statements
        for i, turn in enumerate(turns):
            if turn["speaker"] == "ai" and i + 1 < len(turns):
                next_turn = turns[i + 1]
                
                # Check if customer response is positive
                if self._is_positive_response(next_turn["text"]):
                    phrases.append({
                        "ai_statement": turn["text"],
                        "customer_response": next_turn["text"],
                        "effectiveness": "high",
                        "category": self._categorize_phrase(turn["text"])
                    })
        
        return phrases
    
    def _detect_objections(self, transcript: str) -> List[Dict]:
        """
        Detect objection keywords and phrases
        """
        objection_patterns = [
            (r"\b(too\s+)?expensive\b|\b(too\s+)?costly\b|\bprice\b|\bcost\b", "price"),
            (r"\bnot\s+interested\b|\bno\s+thank\b", "not_interested"),
            (r"\bthink\s+about\s+it\b|\bconsider\b|\bmaybe\s+later\b", "thinking"),
            (r"\bbusy\b|\bno\s+time\b|\bin\s+a\s+hurry\b", "time"),
            (r"\bcall\s+back\b|\blater\b|\banother\s+time\b", "callback"),
            (r"\balready\s+have\b|\bhappy\s+with\b|\bcurrent\s+provider\b", "satisfied"),
            (r"\bnot\s+sure\b|\bconfused\b|\bdon't\s+understand\b", "confusion"),
        ]
        
        objections = []
        for pattern, objection_type in objection_patterns:
            matches = re.finditer(pattern, transcript.lower())
            for match in matches:
                # Get surrounding context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(transcript), match.end() + 50)
                context = transcript[start:end]
                
                objections.append({
                    "type": objection_type,
                    "text": match.group(),
                    "context": context,
                    "position": match.start()
                })
        
        return objections
    
    def _analyze_objection_responses(
        self,
        transcript: str,
        objections: List[Dict],
        success: bool
    ) -> List[Dict]:
        """
        Analyze how AI responded to objections
        """
        turns = self._split_transcript_into_turns(transcript)
        responses = []
        
        for objection in objections:
            # Find the turn containing the objection
            objection_turn = None
            ai_response_turn = None
            
            for i, turn in enumerate(turns):
                if objection["text"].lower() in turn["text"].lower():
                    objection_turn = turn
                    # Get AI's response (next AI turn)
                    for j in range(i + 1, len(turns)):
                        if turns[j]["speaker"] == "ai":
                            ai_response_turn = turns[j]
                            break
                    break
            
            if objection_turn and ai_response_turn:
                responses.append({
                    "objection_type": objection["type"],
                    "objection_text": objection_turn["text"],
                    "ai_response": ai_response_turn["text"],
                    "success": success,
                    "effectiveness": "high" if success else "low"
                })
        
        return responses
    
    def _analyze_conversation_flow(self, transcript: str) -> List[Dict]:
        """
        Analyze the flow and structure of the conversation
        """
        turns = self._split_transcript_into_turns(transcript)
        
        flow = []
        for i, turn in enumerate(turns):
            flow_item = {
                "turn_number": i + 1,
                "speaker": turn["speaker"],
                "category": self._categorize_phrase(turn["text"]),
                "word_count": len(turn["text"].split()),
                "sentiment": self._quick_sentiment(turn["text"])
            }
            flow.append(flow_item)
        
        return flow
    
    def _split_transcript_into_turns(self, transcript: str) -> List[Dict]:
        """
        Split transcript into conversation turns
        Expected format: "AI: text\nCustomer: text\n..."
        """
        turns = []
        lines = transcript.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to detect speaker
            if line.lower().startswith('ai:') or line.lower().startswith('agent:'):
                speaker = "ai"
                text = line.split(':', 1)[1].strip()
            elif line.lower().startswith('customer:') or line.lower().startswith('user:'):
                speaker = "customer"
                text = line.split(':', 1)[1].strip()
            else:
                # Default to alternating (start with AI)
                speaker = "ai" if len(turns) % 2 == 0 else "customer"
                text = line
            
            turns.append({
                "speaker": speaker,
                "text": text
            })
        
        return turns
    
    def _is_positive_response(self, text: str) -> bool:
        """
        Check if response indicates positive engagement
        """
        positive_indicators = [
            r"\byes\b", r"\bokay\b", r"\bsure\b", r"\bsounds\s+good\b",
            r"\binterested\b", r"\btell\s+me\s+more\b", r"\bgo\s+ahead\b",
            r"\bi\s+like\b", r"\bthat's\s+great\b", r"\bperfect\b"
        ]
        
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in positive_indicators)
    
    def _categorize_phrase(self, text: str) -> str:
        """
        Categorize phrase by type
        """
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['hello', 'hi', 'good morning', 'good afternoon']):
            return "greeting"
        elif any(word in text_lower for word in ['offer', 'deal', 'special', 'discount', 'save']):
            return "offer"
        elif any(word in text_lower for word in ['question', 'wondering', 'curious', 'how', 'what', 'why']):
            return "question"
        elif any(word in text_lower for word in ['understand', 'appreciate', 'i see', 'makes sense']):
            return "acknowledgment"
        elif any(word in text_lower for word in ['because', 'reason', 'explain', 'due to']):
            return "explanation"
        elif any(word in text_lower for word in ['thank', 'appreciate', 'grateful']):
            return "gratitude"
        else:
            return "general"
    
    def _quick_sentiment(self, text: str) -> str:
        """
        Quick sentiment analysis (positive/negative/neutral)
        """
        positive_words = ['good', 'great', 'excellent', 'perfect', 'yes', 'sure', 'love', 'like', 'interested']
        negative_words = ['no', 'not', 'never', 'bad', 'terrible', 'hate', 'dislike', 'expensive', 'worried']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    async def _store_learnings(
        self,
        db: AsyncSession,
        call_id: int,
        learnings: Dict
    ):
        """
        Store learnings in call record for future analysis
        """
        # Update call notes with learnings summary
        result = await db.execute(select(Call).where(Call.id == call_id))
        call = result.scalar_one_or_none()
        
        if call:
            learning_summary = (
                f"AI Learning: {len(learnings['successful_phrases'])} successful phrases, "
                f"{len(learnings['objection_handling'])} objections handled, "
                f"score: {learnings['learning_score']:.2f}"
            )
            
            if call.notes:
                call.notes += f"\n{learning_summary}"
            else:
                call.notes = learning_summary
            
            # Store full learnings in custom_data
            if not call.custom_data:
                call.custom_data = {}
            call.custom_data["ai_learnings"] = learnings
            
            await db.commit()
    
    async def _auto_update_training_content(
        self,
        db: AsyncSession,
        agent_id: int,
        learnings: Dict
    ):
        """
        Automatically create/update training content based on learnings
        """
        # Add successful phrases as training content
        for phrase in learnings["successful_phrases"][:5]:  # Top 5 only
            # Check if similar content already exists
            result = await db.execute(
                select(TrainingContent)
                .where(TrainingContent.agent_id == agent_id)
                .where(TrainingContent.content_type == "successful_phrase")
                .where(TrainingContent.content.contains(phrase["ai_statement"][:30]))
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Increment usage count
                existing.usage_count += 1
                existing.success_rate = 100  # It was successful
            else:
                # Create new training content
                training = TrainingContent(
                    agent_id=agent_id,
                    content_type="successful_phrase",
                    title=f"Auto-learned: {phrase['category']}",
                    content=phrase["ai_statement"],
                    category=phrase["category"],
                    priority=75,
                    is_active=True,
                    usage_count=1,
                    success_rate=100,
                    tags=["auto_learned", "successful", learnings["disposition"]],
                    trigger_keywords=self._extract_keywords(phrase["ai_statement"])
                )
                db.add(training)
        
        # Add effective objection responses
        for objection in learnings["objection_handling"]:
            if objection["effectiveness"] == "high":
                result = await db.execute(
                    select(TrainingContent)
                    .where(TrainingContent.agent_id == agent_id)
                    .where(TrainingContent.content_type == "rebuttal")
                    .where(TrainingContent.category == objection["objection_type"])
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    existing.usage_count += 1
                    existing.success_rate = 100
                else:
                    training = TrainingContent(
                        agent_id=agent_id,
                        content_type="rebuttal",
                        title=f"Auto-learned: {objection['objection_type']} objection",
                        content=objection["ai_response"],
                        category=objection["objection_type"],
                        priority=85,
                        is_active=True,
                        usage_count=1,
                        success_rate=100,
                        tags=["auto_learned", "objection", objection["objection_type"]],
                        trigger_keywords=[objection["objection_type"]]
                    )
                    db.add(training)
        
        await db.commit()
        logger.info(f"Auto-updated training content for agent {agent_id}")
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """
        Extract key words from text
        """
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Return unique keywords (first occurrence)
        unique_keywords = []
        for kw in keywords:
            if kw not in unique_keywords:
                unique_keywords.append(kw)
            if len(unique_keywords) >= max_keywords:
                break
        
        return unique_keywords
    
    async def get_learning_insights(
        self,
        db: AsyncSession,
        agent_id: Optional[int] = None,
        days: int = 30
    ) -> Dict:
        """
        Get aggregate learning insights across multiple calls
        """
        # Build query
        query = select(Call).where(
            Call.created_at >= datetime.utcnow() - timedelta(days=days)
        )
        
        if agent_id:
            query = query.where(Call.agent_id == agent_id)
        
        result = await db.execute(query)
        calls = result.scalars().all()
        
        insights = {
            "period_days": days,
            "total_calls": len(calls),
            "successful_calls": 0,
            "top_successful_phrases": [],
            "top_objections": {},
            "best_rebuttals": [],
            "emotion_patterns": {},
            "improvement_trend": []
        }
        
        # Analyze each call
        for call in calls:
            if call.disposition in ["Connected", "Callback"]:
                insights["successful_calls"] += 1
            
            # Extract learnings from custom_data
            if call.custom_data and "ai_learnings" in call.custom_data:
                learnings = call.custom_data["ai_learnings"]
                
                # Collect successful phrases
                for phrase in learnings.get("successful_phrases", []):
                    insights["top_successful_phrases"].append(phrase)
                
                # Count objections
                for obj in learnings.get("objection_handling", []):
                    obj_type = obj["objection_type"]
                    if obj_type not in insights["top_objections"]:
                        insights["top_objections"][obj_type] = {"count": 0, "successful": 0}
                    insights["top_objections"][obj_type]["count"] += 1
                    if obj["success"]:
                        insights["top_objections"][obj_type]["successful"] += 1
        
        # Calculate success rates
        insights["success_rate"] = (
            insights["successful_calls"] / insights["total_calls"]
            if insights["total_calls"] > 0 else 0
        )
        
        return insights


# Global instance
ai_learning_service = AILearningService()
