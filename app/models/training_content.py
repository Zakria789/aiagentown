"""
Training Content Model
Stores AI training data: scripts, FAQs, rebuttals, objections
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class TrainingContent(Base):
    """
    AI Training content for campaigns
    """
    __tablename__ = "training_content"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    
    # Content Type
    content_type = Column(String(50), nullable=False, index=True)
    # script, faq, rebuttal, objection_handler, greeting, closing
    
    # Content
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    
    # Metadata
    category = Column(String(100), nullable=True)  # e.g., "pricing", "features"
    tags = Column(JSON, default=list)
    priority = Column(Integer, default=0)  # Higher = more important
    
    # Usage
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    success_rate = Column(Integer, nullable=True)  # 0-100
    
    # Conditional Logic
    trigger_keywords = Column(JSON, default=list)  # When to use this
    context_requirements = Column(JSON, default=dict)  # Conditions
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "content_type": self.content_type,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "priority": self.priority,
            "is_active": self.is_active,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "trigger_keywords": self.trigger_keywords,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationFlow(Base):
    """
    Defines conversation flow templates
    """
    __tablename__ = "conversation_flows"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    
    # Flow Definition
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    # Flow Steps (JSON structure)
    flow_steps = Column(JSON, nullable=False)
    # [
    #   {"step": 1, "type": "greeting", "content": "...", "next": [2, 3]},
    #   {"step": 2, "type": "qualification", "content": "...", "conditions": {...}}
    # ]
    
    # Metadata
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TrainingTest(Base):
    """
    Test scenarios for AI training validation
    """
    __tablename__ = "training_tests"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    
    # Test Scenario
    scenario_name = Column(String(200), nullable=False)
    scenario_description = Column(Text, nullable=True)
    
    # Test Input
    test_input = Column(Text, nullable=False)  # Customer statement/question
    expected_response = Column(Text, nullable=True)  # What AI should say
    expected_action = Column(String(100), nullable=True)  # What AI should do
    
    # Test Result (when run)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_result = Column(String(20), nullable=True)  # pass, fail, warning
    actual_response = Column(Text, nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    tags = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
