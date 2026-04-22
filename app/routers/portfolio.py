"""Portfolio router - accomplishments view for manager 1:1s."""
import json
import logging
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional, List

from app.database import get_db
from app.models.accomplishment import Accomplishment
from app.models.initiative import Initiative
from app.template_config import templates

logger = logging.getLogger("chief_of_staff.portfolio")
router = APIRouter()


def get_week_start(d: date) -> date:
    """Get Monday of the week containing date d."""
    return d - timedelta(days=d.weekday())


@router.get("/", response_class=HTMLResponse)
async def portfolio_view(
    request: Request,
    weeks: int = 4,
    db: Session = Depends(get_db)
):
    """Portfolio view showing accomplishments by week."""
    from app.services.tasks_sync import TasksSyncService
    from app.services.portfolio_service import PortfolioService

    portfolio_service = PortfolioService(db)

    tasks_sync = TasksSyncService(db)
    tasks_sync.sync_completed_to_accomplishments()

    accomplishments = portfolio_service.get_by_week(weeks=weeks)
    initiatives = portfolio_service.get_initiatives()

    return templates.TemplateResponse(request, "portfolio.html", {
        "weeks_data": accomplishments,
        "initiatives": initiatives,
        "weeks_shown": weeks,
    })


@router.get("/export", response_class=PlainTextResponse)
async def export_portfolio(weeks: int = 2, db: Session = Depends(get_db)):
    """Export portfolio as markdown for Chris 1:1."""
    from app.services.portfolio_service import PortfolioService

    portfolio_service = PortfolioService(db)
    return portfolio_service.export_markdown(weeks=weeks)


@router.post("/impact/{accomplishment_id}")
async def update_impact(
    accomplishment_id: int,
    impact: str = Form(...),
    db: Session = Depends(get_db)
):
    """Update impact narrative for an accomplishment."""
    acc = db.query(Accomplishment).filter(Accomplishment.id == accomplishment_id).first()
    if not acc:
        return {"error": "Not found"}
    acc.impact = impact
    db.commit()
    return {"id": accomplishment_id, "impact": impact}


# --- Initiative CRUD ---

@router.post("/initiatives/reorder")
async def reorder_initiatives(payload: list, db: Session = Depends(get_db)):
    """Persist drag-and-drop sort order. Expects JSON list of {id, sort_order}."""
    for item in payload:
        db.query(Initiative).filter(Initiative.id == item["id"]).update({"sort_order": item["sort_order"]})
    db.commit()
    return {"ok": True}


@router.post("/initiatives")
async def add_initiative(
    request: Request,
    name: str = Form(...),
    status: str = Form("In Progress"),
    target: str = Form(""),
    description: str = Form(""),
    next_steps: str = Form(""),
    owner: str = Form(""),
    impact: str = Form(""),
    jira_epic: str = Form(""),
    confluence_link: str = Form(""),
    group_label: str = Form(""),
    db: Session = Depends(get_db),
):
    """Add a new initiative."""
    # Parse document links from form (doc_label[] and doc_url[] arrays)
    form_data = await request.form()
    doc_labels = form_data.getlist("doc_label[]")
    doc_urls = form_data.getlist("doc_url[]")
    document_links = []
    for label, url in zip(doc_labels, doc_urls):
        if url and url.strip():
            document_links.append({
                "label": label.strip() if label and label.strip() else "Link",
                "url": url.strip()
            })
    
    max_order = db.query(Initiative).count()
    initiative = Initiative(
        name=name,
        status=status,
        target=target,
        description=description,
        next_steps=next_steps,
        owner=owner,
        impact=impact or None,
        jira_epic=jira_epic or None,
        confluence_link=confluence_link or None,
        group_label=group_label or None,
        sort_order=max_order,
    )
    initiative.set_document_links(document_links)
    db.add(initiative)
    db.commit()
    logger.info("Initiative added: %s", name)
    return RedirectResponse(url="/tracker", status_code=303)


@router.post("/initiatives/{initiative_id}/update")
async def update_initiative(
    request: Request,
    initiative_id: int,
    name: str = Form(...),
    status: str = Form("In Progress"),
    target: str = Form(""),
    description: str = Form(""),
    next_steps: str = Form(""),
    owner: str = Form(""),
    impact: str = Form(""),
    jira_epic: str = Form(""),
    completed_date: str = Form(""),
    confluence_link: str = Form(""),
    group_label: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update an existing initiative."""
    from datetime import date as date_type
    initiative = db.query(Initiative).filter(Initiative.id == initiative_id).first()
    if not initiative:
        return RedirectResponse(url="/tracker", status_code=303)
    
    # Parse document links from form
    form_data = await request.form()
    doc_labels = form_data.getlist("doc_label[]")
    doc_urls = form_data.getlist("doc_url[]")
    document_links = []
    for label, url in zip(doc_labels, doc_urls):
        if url and url.strip():
            document_links.append({
                "label": label.strip() if label and label.strip() else "Link",
                "url": url.strip()
            })
    
    initiative.name = name
    initiative.status = status
    initiative.target = target
    initiative.description = description
    initiative.next_steps = next_steps
    initiative.owner = owner
    initiative.impact = impact or None
    initiative.jira_epic = jira_epic or None
    initiative.confluence_link = confluence_link or None
    initiative.group_label = group_label or None
    initiative.set_document_links(document_links)

    # Parse completed_date
    if completed_date and completed_date.strip():
        try:
            initiative.completed_date = date_type.fromisoformat(completed_date.strip())
        except ValueError:
            pass
    else:
        initiative.completed_date = None

    db.commit()
    logger.info("Initiative updated: id=%s name=%s", initiative_id, name)
    return RedirectResponse(url="/tracker", status_code=303)


@router.delete("/initiatives/{initiative_id}", response_class=HTMLResponse)
async def delete_initiative(initiative_id: int, db: Session = Depends(get_db)):
    """Delete an initiative. Returns empty string so HTMX removes the row."""
    initiative = db.query(Initiative).filter(Initiative.id == initiative_id).first()
    if not initiative:
        return HTMLResponse("")
    db.delete(initiative)
    db.commit()
    logger.info("Initiative deleted: id=%s", initiative_id)
    return HTMLResponse("")


