"""Briefing router - Daily briefing generation and display."""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.template_config import templates
from app.services.briefing_service import BriefingService
from app.services.jira_service import JiraService

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.get("")
@router.get("/")
async def daily_briefing(request: Request, db: Session = Depends(get_db)):
    """Display the daily briefing view."""
    jira_service = JiraService()
    briefing_service = BriefingService(jira_service=jira_service, db_session=db)
    
    briefing = briefing_service.generate_briefing()
    
    return templates.TemplateResponse("briefing.html", {
        "request": request,
        "active": "briefing",
        "briefing": briefing,
        "jira_live": jira_service.is_configured,
    })


@router.get("/refresh")
async def refresh_briefing(request: Request, db: Session = Depends(get_db)):
    """HTMX endpoint to refresh briefing content."""
    jira_service = JiraService()
    briefing_service = BriefingService(jira_service=jira_service, db_session=db)
    
    briefing = briefing_service.generate_briefing()
    
    return templates.TemplateResponse("partials/briefing_content.html", {
        "request": request,
        "briefing": briefing,
        "jira_live": jira_service.is_configured,
    })


@router.get("/export")
async def export_briefing(db: Session = Depends(get_db)):
    """Export briefing as markdown for 1:1 prep or sharing."""
    jira_service = JiraService()
    briefing_service = BriefingService(jira_service=jira_service, db_session=db)
    
    markdown_content = briefing_service.export_markdown()
    
    return PlainTextResponse(
        content=markdown_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f"attachment; filename=daily_briefing.md"
        }
    )
