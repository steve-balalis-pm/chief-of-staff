"""Dashboard router - main unified view."""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.template_config import templates

router = APIRouter()

@router.get("/")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard view."""
    from app.services.tasks_sync import TasksSyncService
    from app.services.jira_service import JiraService
    
    sync_service = TasksSyncService(db)
    tasks_data = sync_service.get_dashboard_data()
    
    # Get Jira deadline data
    jira_service = JiraService()
    upcoming_deadlines = jira_service.get_upcoming_deadlines()
    overdue = jira_service.get_overdue()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active": "dashboard",
        "tasks": tasks_data,
        "deadlines": {
            "upcoming": upcoming_deadlines[:5],
            "overdue": overdue[:5],
            "upcoming_count": len(upcoming_deadlines),
            "overdue_count": len(overdue),
        },
        "jira_live": jira_service.is_configured,
        "stats": {
            "today_open": len([t for t in tasks_data.get("active_today", []) if not t.get("done")]),
            "today_done": len([t for t in tasks_data.get("active_today", []) if t.get("done")]),
            "week_open": len([t for t in tasks_data.get("this_week", []) if not t.get("done")]),
            "total_done_this_week": len(tasks_data.get("completed", [])),
        }
    })
