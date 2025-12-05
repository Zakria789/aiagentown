"""
Customers/Leads API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, desc
from typing import Optional

from app.database import get_db
from app.schemas.customer import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    CustomerListResponse, AssignCustomerRequest
)
from app.models.customer import Customer
from app.models.agent import Agent
from app.core.dependencies import get_current_agent

router = APIRouter()


@router.post("/", response_model=CustomerResponse)
async def create_customer(
    customer: CustomerCreate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Create new customer/lead"""
    db_customer = Customer(**customer.dict())
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    return CustomerResponse.from_orm(db_customer)


@router.get("/", response_model=CustomerListResponse)
async def get_customers(
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    assigned_to_me: bool = False,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Get customer list"""
    query = select(Customer)
    
    if status:
        query = query.where(Customer.status == status)
    
    if assigned_to_me:
        query = query.where(Customer.assigned_agent_id == agent.id)
    
    offset = (page - 1) * page_size
    query = query.order_by(desc(Customer.created_at)).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    customers = result.scalars().all()
    
    total_result = await db.execute(select(Customer))
    total = len(total_result.scalars().all())
    
    return CustomerListResponse(
        total=total,
        page=page,
        page_size=page_size,
        customers=[CustomerResponse.from_orm(c) for c in customers]
    )


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Get customer details"""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return CustomerResponse.from_orm(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Update customer"""
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    update_data = customer_update.dict(exclude_unset=True)
    
    await db.execute(
        update(Customer)
        .where(Customer.id == customer_id)
        .values(**update_data)
    )
    await db.commit()
    await db.refresh(customer)
    
    return CustomerResponse.from_orm(customer)


@router.post("/assign")
async def assign_customers(
    request: AssignCustomerRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """Assign customers to agent"""
    await db.execute(
        update(Customer)
        .where(Customer.id.in_(request.customer_ids))
        .values(assigned_agent_id=request.agent_id)
    )
    await db.commit()
    
    return {"message": f"Assigned {len(request.customer_ids)} customers"}
