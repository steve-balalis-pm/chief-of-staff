"""Tasks router - interactive task management."""
import logging

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional

logger = logging.getLogger("chief_of_staff.tasks")

from app.database import get_db
from app.template_config import templates

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def tasks_view(request: Request, db: Session = Depends(get_db)):
    """Full tasks view."""
    from app.services.tasks_sync import TasksSyncService
    
    sync_service = TasksSyncService(db)
    tasks_data = sync_service.get_all_tasks()
    
    return templates.TemplateResponse("tasks.html", {
        "request": request,
        "sections": tasks_data
    })

@router.post("/toggle/{task_id}")
async def toggle_task(task_id: int, db: Session = Depends(get_db)):
    """Toggle task done/not done - htmx endpoint."""
    from app.services.tasks_sync import TasksSyncService
    
    sync_service = TasksSyncService(db)
    task = sync_service.toggle_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "done": task.get("done", False)}

@router.post("/toggle-hash/{line_hash}")
async def toggle_task_by_hash(line_hash: str, db: Session = Depends(get_db)):
    """Toggle task by line hash - htmx endpoint."""
    from app.services.tasks_sync import TasksSyncService
    
    sync_service = TasksSyncService(db)
    task = sync_service.toggle_task_by_hash(line_hash)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task.get("id"), "done": task.get("done", False)}

@router.post("/add")
async def add_task(
    content: str = Form(...),
    section: str = Form("this_week"),
    priority: str = Form("medium"),
    db: Session = Depends(get_db)
):
    """Add a new task - htmx endpoint."""
    from app.services.tasks_sync import TasksSyncService
    
    sync_service = TasksSyncService(db)
    task = sync_service.add_task(content, section, priority)
    return {"id": task.get("id"), "content": content, "section": section}

@router.post("/move/{task_id}")
async def move_task(
    task_id: int,
    target_section: str = Form(...),
    db: Session = Depends(get_db)
):
    """Move task to different section - htmx endpoint."""
    from app.services.tasks_sync import TasksSyncService
    
    sync_service = TasksSyncService(db)
    success = sync_service.move_task(task_id, target_section)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": task_id, "section": target_section}

@router.delete("/{task_id}", response_class=HTMLResponse)
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task - htmx endpoint. Returns empty string so HTMX removes the element."""
    from app.services.tasks_sync import TasksSyncService

    sync_service = TasksSyncService(db)
    success = sync_service.delete_task(task_id)
    if not success:
        logger.warning("Delete attempted for non-existent task id=%s", task_id)
        raise HTTPException(status_code=404, detail="Task not found")
    logger.info("Task deleted: id=%s", task_id)
    return HTMLResponse("")
