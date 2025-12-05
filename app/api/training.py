"""
Training Content API Routes
Manage AI training content, FAQs, rebuttals, scripts
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
import json
import csv
import io

from app.database import get_db
from app.models.training_content import TrainingContent, ConversationFlow, TrainingTest
from app.services.ai_learning import ai_learning_service
from app.schemas.training_content import (
    TrainingContentCreate,
    TrainingContentUpdate,
    TrainingContentResponse,
    ConversationFlowCreate,
    ConversationFlowUpdate,
    ConversationFlowResponse,
    TrainingTestCreate,
    TrainingTestUpdate,
    TrainingTestResponse,
    TrainingTestRun,
    TrainingTestRunResult
)
from datetime import datetime

router = APIRouter(prefix="/api/training", tags=["Training Content"])


# ============= Training Content CRUD =============

@router.post("/content", response_model=TrainingContentResponse, status_code=status.HTTP_201_CREATED)
async def create_training_content(
    content: TrainingContentCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new training content (script, FAQ, rebuttal, etc.)"""
    db_content = TrainingContent(**content.model_dump())
    db.add(db_content)
    await db.commit()
    await db.refresh(db_content)
    return db_content


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_training_files(
    agent_id: int = Form(...),
    content_type: str = Form(..., description="script, faq, rebuttal, objection_handler"),
    category: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload training content files (TXT, CSV, JSON)
    
    Supported formats:
    - TXT: Plain text scripts/FAQs (one per file)
    - CSV: Bulk upload with columns: title, content, category, tags
    - JSON: Array of training content objects
    """
    uploaded_items = []
    
    for file in files:
        try:
            content_bytes = await file.read()
            content_str = content_bytes.decode('utf-8')
            
            if file.filename.endswith('.txt'):
                # Single text file
                title = file.filename.replace('.txt', '').replace('_', ' ').title()
                db_content = TrainingContent(
                    agent_id=agent_id,
                    content_type=content_type,
                    title=title,
                    content=content_str,
                    category=category,
                    priority=50,
                    is_active=True
                )
                db.add(db_content)
                uploaded_items.append({"file": file.filename, "title": title, "status": "success"})
            
            elif file.filename.endswith('.csv'):
                # Bulk CSV upload
                csv_file = io.StringIO(content_str)
                reader = csv.DictReader(csv_file)
                
                for row in reader:
                    db_content = TrainingContent(
                        agent_id=agent_id,
                        content_type=content_type,
                        title=row.get('title', 'Untitled'),
                        content=row.get('content', ''),
                        category=row.get('category', category),
                        tags=row.get('tags', '').split(',') if row.get('tags') else [],
                        priority=int(row.get('priority', 50)),
                        is_active=True
                    )
                    db.add(db_content)
                uploaded_items.append({"file": file.filename, "rows": reader.line_num - 1, "status": "success"})
            
            elif file.filename.endswith('.json'):
                # JSON bulk upload
                data = json.loads(content_str)
                items_list = data if isinstance(data, list) else [data]
                
                for item in items_list:
                    db_content = TrainingContent(
                        agent_id=agent_id,
                        content_type=item.get('content_type', content_type),
                        title=item.get('title', 'Untitled'),
                        content=item.get('content', ''),
                        category=item.get('category', category),
                        tags=item.get('tags', []),
                        priority=item.get('priority', 50),
                        trigger_keywords=item.get('trigger_keywords', []),
                        is_active=True
                    )
                    db.add(db_content)
                uploaded_items.append({"file": file.filename, "items": len(items_list), "status": "success"})
            
            else:
                uploaded_items.append({"file": file.filename, "status": "error", "error": "Unsupported file type"})
        
        except Exception as e:
            uploaded_items.append({"file": file.filename, "status": "error", "error": str(e)})
    
    await db.commit()
    
    return {
        "message": "Files processed",
        "uploaded": uploaded_items,
        "total_files": len(files),
        "successful": len([i for i in uploaded_items if i.get("status") == "success"])
    }


@router.get("/content", response_model=List[TrainingContentResponse])
async def list_training_content(
    agent_id: int = None,
    content_type: str = None,
    category: str = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db)
):
    """List all training content with optional filters"""
    query = select(TrainingContent)
    
    if agent_id:
        query = query.where(TrainingContent.agent_id == agent_id)
    if content_type:
        query = query.where(TrainingContent.content_type == content_type)
    if category:
        query = query.where(TrainingContent.category == category)
    if is_active is not None:
        query = query.where(TrainingContent.is_active == is_active)
    
    query = query.order_by(TrainingContent.priority.desc(), TrainingContent.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/content/{content_id}", response_model=TrainingContentResponse)
async def get_training_content(
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get specific training content by ID"""
    result = await db.execute(select(TrainingContent).where(TrainingContent.id == content_id))
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(status_code=404, detail="Training content not found")
    
    return content


@router.put("/content/{content_id}", response_model=TrainingContentResponse)
async def update_training_content(
    content_id: int,
    content_update: TrainingContentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update training content"""
    result = await db.execute(select(TrainingContent).where(TrainingContent.id == content_id))
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(status_code=404, detail="Training content not found")
    
    # Update fields
    update_data = content_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(content, field, value)
    
    await db.commit()
    await db.refresh(content)
    return content


@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_content(
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete training content"""
    result = await db.execute(select(TrainingContent).where(TrainingContent.id == content_id))
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(status_code=404, detail="Training content not found")
    
    await db.delete(content)
    await db.commit()


# ============= Conversation Flows =============

@router.post("/flows", response_model=ConversationFlowResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation_flow(
    flow: ConversationFlowCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversation flow template"""
    flow_data = flow.model_dump()
    flow_data['flow_steps'] = [step.model_dump() for step in flow.flow_steps]
    
    db_flow = ConversationFlow(**flow_data)
    db.add(db_flow)
    await db.commit()
    await db.refresh(db_flow)
    return db_flow


@router.get("/flows", response_model=List[ConversationFlowResponse])
async def list_conversation_flows(
    agent_id: int = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db)
):
    """List all conversation flows"""
    query = select(ConversationFlow)
    
    if agent_id:
        query = query.where(ConversationFlow.agent_id == agent_id)
    if is_active is not None:
        query = query.where(ConversationFlow.is_active == is_active)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/flows/{flow_id}", response_model=ConversationFlowResponse)
async def get_conversation_flow(
    flow_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get specific conversation flow"""
    result = await db.execute(select(ConversationFlow).where(ConversationFlow.id == flow_id))
    flow = result.scalar_one_or_none()
    
    if not flow:
        raise HTTPException(status_code=404, detail="Conversation flow not found")
    
    return flow


@router.put("/flows/{flow_id}", response_model=ConversationFlowResponse)
async def update_conversation_flow(
    flow_id: int,
    flow_update: ConversationFlowUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update conversation flow"""
    result = await db.execute(select(ConversationFlow).where(ConversationFlow.id == flow_id))
    flow = result.scalar_one_or_none()
    
    if not flow:
        raise HTTPException(status_code=404, detail="Conversation flow not found")
    
    update_data = flow_update.model_dump(exclude_unset=True)
    
    # Convert flow_steps to dict if present
    if 'flow_steps' in update_data and update_data['flow_steps']:
        update_data['flow_steps'] = [step.model_dump() for step in update_data['flow_steps']]
    
    for field, value in update_data.items():
        setattr(flow, field, value)
    
    # Increment version
    flow.version += 1
    
    await db.commit()
    await db.refresh(flow)
    return flow


# ============= Training Tests =============

@router.post("/tests", response_model=TrainingTestResponse, status_code=status.HTTP_201_CREATED)
async def create_training_test(
    test: TrainingTestCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new training test scenario"""
    db_test = TrainingTest(**test.model_dump())
    db.add(db_test)
    await db.commit()
    await db.refresh(db_test)
    return db_test


@router.get("/tests", response_model=List[TrainingTestResponse])
async def list_training_tests(
    agent_id: int = None,
    is_active: bool = None,
    db: AsyncSession = Depends(get_db)
):
    """List all training tests"""
    query = select(TrainingTest)
    
    if agent_id:
        query = query.where(TrainingTest.agent_id == agent_id)
    if is_active is not None:
        query = query.where(TrainingTest.is_active == is_active)
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/tests/{test_id}", response_model=TrainingTestResponse)
async def get_training_test(
    test_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get specific training test"""
    result = await db.execute(select(TrainingTest).where(TrainingTest.id == test_id))
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="Training test not found")
    
    return test


@router.put("/tests/{test_id}", response_model=TrainingTestResponse)
async def update_training_test(
    test_id: int,
    test_update: TrainingTestUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update training test"""
    result = await db.execute(select(TrainingTest).where(TrainingTest.id == test_id))
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="Training test not found")
    
    update_data = test_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(test, field, value)
    
    await db.commit()
    await db.refresh(test)
    return test


@router.post("/tests/run", response_model=TrainingTestRunResult)
async def run_training_test(
    test_run: TrainingTestRun,
    db: AsyncSession = Depends(get_db)
):
    """
    Run a training test scenario
    Simulates AI response to test input
    """
    result = await db.execute(select(TrainingTest).where(TrainingTest.id == test_run.test_id))
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="Training test not found")
    
    # TODO: Integrate with actual HumeAI to get real response
    # For now, return a mock result
    
    # Simple similarity check (in production, use semantic similarity)
    match_score = 0.85  # Mock score
    
    test_result = TrainingTestRunResult(
        test_id=test.id,
        result="pass",
        actual_response="This is a simulated AI response for testing purposes.",
        expected_response=test.expected_response,
        match_score=match_score,
        details={
            "simulated": True,
            "test_input": test.test_input,
            "scenario": test.scenario_name
        },
        timestamp=datetime.utcnow()
    )
    
    # Update test record
    test.last_run_at = datetime.utcnow()
    test.last_result = test_result.result
    test.actual_response = test_result.actual_response
    
    await db.commit()
    
    return test_result


@router.get("/agent/{agent_id}/summary")
async def get_agent_training_summary(
    agent_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get summary of all training content for an agent"""
    
    # Count by content type
    result = await db.execute(
        select(TrainingContent)
        .where(TrainingContent.agent_id == agent_id)
    )
    contents = result.scalars().all()
    
    summary = {
        "agent_id": agent_id,
        "total_content": len(contents),
        "by_type": {},
        "active_count": sum(1 for c in contents if c.is_active),
        "total_usage": sum(c.usage_count for c in contents),
        "average_success_rate": None
    }
    
    # Group by type
    for content in contents:
        ctype = content.content_type
        if ctype not in summary["by_type"]:
            summary["by_type"][ctype] = 0
        summary["by_type"][ctype] += 1
    
    # Calculate average success rate
    success_rates = [c.success_rate for c in contents if c.success_rate is not None]
    if success_rates:
        summary["average_success_rate"] = sum(success_rates) / len(success_rates)
    
    return summary


# ============= AI Learning Insights =============

@router.get("/learning-insights")
async def get_learning_insights(
    agent_id: int = None,
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI learning insights from live calls
    Shows what AI learned from real conversations
    """
    insights = await ai_learning_service.get_learning_insights(
        db=db,
        agent_id=agent_id,
        days=days
    )
    
    return {
        "status": "success",
        "insights": insights,
        "generated_at": datetime.utcnow().isoformat()
    }
