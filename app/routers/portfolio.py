"""Portfolio router - accomplishments view for manager 1:1s."""
import logging
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional

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

    return templates.TemplateResponse("portfolio.html", {
        "request": request,
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

@router.post("/initiatives")
async def add_initiative(
    name: str = Form(...),
    status: str = Form("In Progress"),
    target: str = Form(""),
    description: str = Form(""),
    owner: str = Form(""),
    db: Session = Depends(get_db),
):
    """Add a new initiative."""
    max_order = db.query(Initiative).count()
    initiative = Initiative(
        name=name,
        status=status,
        target=target,
        description=description,
        owner=owner,
        sort_order=max_order,
    )
    db.add(initiative)
    db.commit()
    logger.info("Initiative added: %s", name)
    return RedirectResponse(url="/portfolio", status_code=303)


@router.post("/initiatives/{initiative_id}/update")
async def update_initiative(
    initiative_id: int,
    name: str = Form(...),
    status: str = Form("In Progress"),
    target: str = Form(""),
    description: str = Form(""),
    owner: str = Form(""),
    db: Session = Depends(get_db),
):
    """Update an existing initiative."""
    initiative = db.query(Initiative).filter(Initiative.id == initiative_id).first()
    if not initiative:
        return RedirectResponse(url="/portfolio", status_code=303)
    initiative.name = name
    initiative.status = status
    initiative.target = target
    initiative.description = description
    initiative.owner = owner
    db.commit()
    logger.info("Initiative updated: id=%s name=%s", initiative_id, name)
    return RedirectResponse(url="/portfolio", status_code=303)


@router.delete("/initiatives/{initiative_id}", response_class=HTMLResponse)
async def delete_initiative(initiative_id: int, db: Session = Depends(get_db)):
    """Delete an initiative. Returns empty string so HTMX removes the card."""
    initiative = db.query(Initiative).filter(Initiative.id == initiative_id).first()
    if not initiative:
        return HTMLResponse("")
    db.delete(initiative)
    db.commit()
    logger.info("Initiative deleted: id=%s", initiative_id)
    return HTMLResponse("")
