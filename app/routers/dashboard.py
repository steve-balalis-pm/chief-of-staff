"""Dashboard router - main unified view."""
from datetime import date, datetime
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
    from app.models.task import Task

    sync_service = TasksSyncService(db)
    tasks_data = sync_service.get_dashboard_data()

    # Get Jira deadline data — fail gracefully if JSON files are missing or stale
    try:
        jira_service = JiraService()
        upcoming_deadlines = jira_service.get_upcoming_deadlines()
        overdue = jira_service.get_overdue()
        jira_live = jira_service.is_configured
        open_jira_keys = jira_service.get_open_ticket_keys() if jira_live else set()
    except Exception:
        upcoming_deadlines = []
        overdue = []
        jira_live = False
        open_jira_keys = set()

    # Inject recurring tasks from any section into Active Today
    active_today_hashes = {t.get("line_hash") for t in tasks_data.get("active_today", [])}
    recurring_to_inject = []
    for section_key, tasks in tasks_data.items():
        if section_key == "active_today":
            continue
        for task in tasks:
            if task.get("recurring") and task.get("line_hash") not in active_today_hashes:
                recurring_to_inject.append(task)
    if recurring_to_inject:
        tasks_data.setdefault("active_today", [])
        tasks_data["active_today"] = recurring_to_inject + tasks_data["active_today"]

    # Count tasks completed today using DB timestamps (includes recurring completions)
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_done = db.query(Task).filter(
        Task.done == True,
        Task.completed_at >= today_start
    ).count()

    return templates.TemplateResponse(request, "dashboard.html", {
        "active": "dashboard",
        "tasks": tasks_data,
        "deadlines": {
            "upcoming": upcoming_deadlines[:5],
            "overdue": overdue[:5],
            "upcoming_count": len(upcoming_deadlines),
            "overdue_count": len(overdue),
        },
        "jira_live": jira_live,
        "open_jira_keys": open_jira_keys,
        "stats": {
            "today_open": len([t for t in tasks_data.get("active_today", []) if not t.get("done")]),
            "today_done": today_done,
            "week_open": len([t for t in tasks_data.get("this_week", []) if not t.get("done")]),
            "total_done_this_week": len(tasks_data.get("completed", [])),
        }
    })
