"""Jira router - Live Jira dashboard and field checking."""
from fastapi import APIRouter, Request
from app.template_config import templates
from app.services.jira_service import JiraService
from app.services.field_checker import FieldChecker

router = APIRouter(prefix="/jira", tags=["jira"])


@router.get("")
@router.get("/")
async def jira_dashboard(request: Request):
    """Main Jira dashboard with live ticket data."""
    jira_service = JiraService()
    field_checker = FieldChecker(jira_service)
    
    # Get dashboard data
    dashboard_data = jira_service.get_all_dashboard_data()
    
    # Get field completeness summary
    field_summary = field_checker.get_actionable_summary()
    
    return templates.TemplateResponse(request, "jira.html", {
        "active": "jira",
        "data": dashboard_data,
        "field_summary": field_summary,
        "is_live": dashboard_data.get("is_live", False),
    })


@router.get("/refresh")
async def refresh_data(request: Request):
    """HTMX endpoint to refresh Jira data."""
    jira_service = JiraService()
    field_checker = FieldChecker(jira_service)
    
    dashboard_data = jira_service.get_all_dashboard_data()
    field_summary = field_checker.get_actionable_summary()
    
    return templates.TemplateResponse(request, "partials/jira_content.html", {
        "data": dashboard_data,
        "field_summary": field_summary,
        "is_live": dashboard_data.get("is_live", False),
    })


@router.get("/tickets/{category}")
async def get_ticket_category(request: Request, category: str):
    """Get tickets for a specific category (HTMX endpoint)."""
    jira_service = JiraService()
    
    category_map = {
        "my_tickets": jira_service.get_my_open_tickets,
        "in_progress": jira_service.get_in_progress,
        "high_priority": jira_service.get_high_priority,
        "recently_updated": jira_service.get_recently_updated,
        "stale": jira_service.get_stale_tickets,
        "upcoming_deadlines": jira_service.get_upcoming_deadlines,
        "overdue": jira_service.get_overdue,
        "tpe": jira_service.get_tpe_tickets,
    }
    
    getter = category_map.get(category)
    if not getter:
        return templates.TemplateResponse(request, "partials/ticket_list.html", {
            "tickets": [],
            "category": category,
            "error": "Unknown category"
        })
    
    tickets = getter()
    
    return templates.TemplateResponse(request, "partials/ticket_list.html", {
        "tickets": tickets,
        "category": category,
    })


@router.get("/field-check")
async def field_check(request: Request):
    """Get field completeness check results (HTMX endpoint)."""
    jira_service = JiraService()
    field_checker = FieldChecker(jira_service)
    
    summary = field_checker.get_actionable_summary()
    
    return templates.TemplateResponse(request, "partials/field_check.html", {
        "summary": summary,
    })
