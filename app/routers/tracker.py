"""Tracker router - manager-facing workstream status tracker."""
from datetime import date

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.template_config import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def tracker_view(request: Request, db: Session = Depends(get_db)):
    """Editable workstream tracker."""
    from app.services.portfolio_service import PortfolioService
    portfolio_service = PortfolioService(db)
    initiatives = portfolio_service.get_initiatives()
    return templates.TemplateResponse(request, "tracker.html", {
        "active": "tracker",
        "initiatives": initiatives,
    })


@router.get("/share", response_class=HTMLResponse)
async def tracker_share(request: Request, db: Session = Depends(get_db)):
    """Printable bi-weekly update for manager — no nav, clean layout."""
    from app.services.portfolio_service import PortfolioService
    portfolio_service = PortfolioService(db)
    initiatives = portfolio_service.get_initiatives()
    active = [i for i in initiatives if i.status not in ("Complete", "On Hold")]
    on_hold = [i for i in initiatives if i.status == "On Hold"]
    return templates.TemplateResponse(request, "tracker_share.html", {
        "active_initiatives": active,
        "on_hold_initiatives": on_hold,
        "report_date": date.today().strftime("%B %d, %Y"),
    })
