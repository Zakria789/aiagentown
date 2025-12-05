"""
Training Content Schemas
Pydantic models for AI training API
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class TrainingContentBase(BaseModel):
    content_type: str = Field(..., description="Type: script, faq, rebuttal, objection_handler, greeting, closing")
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=10)
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    priority: int = Field(default=0, ge=0, le=100)
    trigger_keywords: List[str] = Field(default_factory=list)
    context_requirements: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed = ['script', 'faq', 'rebuttal', 'objection_handler', 'greeting', 'closing', 'general']
        if v not in allowed:
            raise ValueError(f"content_type must be one of: {', '.join(allowed)}")
        return v


class TrainingContentCreate(TrainingContentBase):
    agent_id: int


class TrainingContentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    content: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    trigger_keywords: Optional[List[str]] = None
    context_requirements: Optional[Dict[str, Any]] = None


class TrainingContentResponse(TrainingContentBase):
    id: int
    agent_id: int
    is_active: bool
    usage_count: int
    success_rate: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ConversationFlowStep(BaseModel):
    step: int
    step_type: str  # greeting, question, objection_handler, closing
    content: str
    next_steps: List[int] = Field(default_factory=list)
    conditions: Dict[str, Any] = Field(default_factory=dict)


class ConversationFlowBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    flow_steps: List[ConversationFlowStep]


class ConversationFlowCreate(ConversationFlowBase):
    agent_id: int


class ConversationFlowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    flow_steps: Optional[List[ConversationFlowStep]] = None
    is_active: Optional[bool] = None


class ConversationFlowResponse(ConversationFlowBase):
    id: int
    agent_id: int
    is_active: bool
    version: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TrainingTestBase(BaseModel):
    scenario_name: str = Field(..., min_length=3, max_length=200)
    scenario_description: Optional[str] = None
    test_input: str = Field(..., min_length=5)
    expected_response: Optional[str] = None
    expected_action: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class TrainingTestCreate(TrainingTestBase):
    agent_id: int


class TrainingTestUpdate(BaseModel):
    scenario_name: Optional[str] = Field(None, min_length=3, max_length=200)
    scenario_description: Optional[str] = None
    test_input: Optional[str] = Field(None, min_length=5)
    expected_response: Optional[str] = None
    expected_action: Optional[str] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None


class TrainingTestResponse(TrainingTestBase):
    id: int
    agent_id: int
    is_active: bool
    last_run_at: Optional[datetime]
    last_result: Optional[str]
    actual_response: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TrainingTestRun(BaseModel):
    """Request to run a training test"""
    test_id: int
    simulate: bool = Field(default=True, description="If True, only simulate without affecting actual AI")


class TrainingTestRunResult(BaseModel):
    """Result of a training test run"""
    test_id: int
    result: str  # pass, fail, warning
    actual_response: str
    expected_response: Optional[str]
    match_score: float  # 0-1 similarity score
    details: Dict[str, Any]
    timestamp: datetime
