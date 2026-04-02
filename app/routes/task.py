from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.task import Task, Priority
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse, 
    TaskSingleResponse, TaskStatsResponse
)
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=TaskSingleResponse)
def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new task for the current user"""
    db_task = Task(
        user_id=current_user.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        deadline=task.deadline
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return TaskSingleResponse(data=db_task)

@router.get("/", response_model=TaskListResponse)
def get_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    completed: Optional[bool] = Query(None, description="Filter by completion status"),
    priority: Optional[Priority] = Query(None, description="Filter by priority"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get tasks for the current user with optional filtering"""
    query = db.query(Task).filter(Task.user_id == current_user.id)
    
    if completed is not None:
        query = query.filter(Task.is_completed == completed)
    
    if priority is not None:
        query = query.filter(Task.priority == priority)
    
    # Order by priority (urgent first) then by deadline
    priority_order = {
        Priority.URGENT: 1,
        Priority.HIGH: 2,
        Priority.MEDIUM: 3,
        Priority.LOW: 4
    }
    query = query.order_by(
        Task.is_completed.asc(),  # Incomplete tasks first
        Task.priority.asc(),      # Then by priority
        Task.deadline.asc()       # Then by deadline
    )
    
    # Get total count after applying filters
    total = query.count()
    tasks = query.offset(offset).limit(limit).all()
    
    # Calculate completed and pending counts based on the same filtered query
    completed_query = db.query(Task).filter(Task.user_id == current_user.id)
    
    # Apply the same filters as the main query
    if completed is not None:
        completed_query = completed_query.filter(Task.is_completed == completed)
    if priority is not None:
        completed_query = completed_query.filter(Task.priority == priority)
    
    # Count completed tasks from the filtered query
    completed_count = completed_query.filter(Task.is_completed == True).count()
    
    # Count pending tasks from the filtered query
    pending_count = completed_query.filter(Task.is_completed == False).count()
    
    return TaskListResponse(
        data=tasks,
        total=total,
        completed=completed_count,
        pending=pending_count
    )

@router.get("/{task_id}", response_model=TaskSingleResponse)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific task by ID"""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskSingleResponse(data=task)

@router.put("/{task_id}", response_model=TaskSingleResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a specific task"""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Update only provided fields
    update_data = task_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    
    return TaskSingleResponse(data=task)

@router.patch("/{task_id}/toggle", response_model=TaskSingleResponse)
def toggle_task_completion(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle the completion status of a task"""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_completed = not task.is_completed
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    
    return TaskSingleResponse(data=task)

@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific task"""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    
    return {"success": True, "message": "Task deleted successfully"}

@router.get("/stats/overview", response_model=TaskStatsResponse)
def get_task_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get task statistics for the current user"""
    now = datetime.utcnow()
    
    # Basic counts
    total = db.query(Task).filter(Task.user_id == current_user.id).count()
    completed = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.is_completed == True
    ).count()
    pending = total - completed
    
    # Overdue tasks (incomplete tasks with deadline in the past)
    overdue = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.is_completed == False,
        Task.deadline < now
    ).count()
    
    # Tasks by priority
    priority_stats = {}
    for priority in Priority:
        count = db.query(Task).filter(
            Task.user_id == current_user.id,
            Task.priority == priority
        ).count()
        priority_stats[priority.value] = count
    
    return TaskStatsResponse(
        data={
            "total": total,
            "completed": completed,
            "pending": pending,
            "overdue": overdue,
            "by_priority": priority_stats
        }
    )
