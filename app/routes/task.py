from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.task import Priority, Task
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskListResponse,
    TaskSingleResponse,
    TaskStatsResponse,
    TaskUpdate,
)

router = APIRouter()


@router.post("/", response_model=TaskSingleResponse)
def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db_task = Task(
        user_id=current_user.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        deadline=task.deadline,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return TaskSingleResponse(data=db_task)


@router.get("/", response_model=TaskListResponse)
def get_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    completed: Optional[bool] = Query(None),
    priority: Optional[Priority] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    query = db.query(Task).filter(Task.user_id == current_user.id)
    if completed is not None:
        query = query.filter(Task.is_completed == completed)
    if priority is not None:
        query = query.filter(Task.priority == priority)

    priority_order = case(
        (Task.priority == Priority.URGENT, 0),
        (Task.priority == Priority.HIGH, 1),
        (Task.priority == Priority.MEDIUM, 2),
        else_=3,
    )
    query = query.order_by(
        Task.is_completed.asc(),
        priority_order.asc(),
        Task.deadline.is_(None).asc(),
        Task.deadline.asc(),
    )

    total = query.count()
    tasks = query.offset(offset).limit(limit).all()

    counts_query = db.query(Task).filter(Task.user_id == current_user.id)
    if priority is not None:
        counts_query = counts_query.filter(Task.priority == priority)
    if completed is not None:
        counts_query = counts_query.filter(Task.is_completed == completed)

    completed_count = counts_query.filter(Task.is_completed.is_(True)).count()
    pending_count = counts_query.filter(Task.is_completed.is_(False)).count()
    return TaskListResponse(
        data=tasks,
        total=total,
        completed=completed_count,
        pending=pending_count,
    )


@router.get("/{task_id}", response_model=TaskSingleResponse)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskSingleResponse(data=task)


@router.put("/{task_id}", response_model=TaskSingleResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

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
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
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
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"success": True, "data": {"message": "Task deleted successfully"}}


@router.get("/stats/overview", response_model=TaskStatsResponse)
def get_task_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    total = db.query(Task).filter(Task.user_id == current_user.id).count()
    completed = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.is_completed.is_(True),
    ).count()
    pending = total - completed
    overdue = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.is_completed.is_(False),
        Task.deadline < now,
    ).count()

    priority_stats = {}
    for priority in Priority:
        count = db.query(Task).filter(
            Task.user_id == current_user.id,
            Task.priority == priority,
        ).count()
        priority_stats[priority.value] = count

    return TaskStatsResponse(
        data={
            "total": total,
            "completed": completed,
            "pending": pending,
            "overdue": overdue,
            "by_priority": priority_stats,
        }
    )
