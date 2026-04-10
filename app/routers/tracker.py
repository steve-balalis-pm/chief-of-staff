"""Tracker router - manager-facing workstream status tracker."""
from datetime import date

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, PlainTextResponse
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
    # Split into active, on hold, and completed
    active_initiatives = [i for i in initiatives if i["status"] not in ("Complete", "On Hold")]
    on_hold_initiatives = [i for i in initiatives if i["status"] == "On Hold"]
    completed_initiatives = [i for i in initiatives if i["status"] == "Complete"]
    return templates.TemplateResponse(request, "tracker.html", {
        "active": "tracker",
        "initiatives": active_initiatives,
        "on_hold_initiatives": on_hold_initiatives,
        "completed_initiatives": completed_initiatives,
    })


@router.get("/share", response_class=HTMLResponse)
async def tracker_share(request: Request, db: Session = Depends(get_db)):
    """Printable bi-weekly update for manager — no nav, clean layout."""
    from app.services.portfolio_service import PortfolioService
    portfolio_service = PortfolioService(db)
    initiatives = portfolio_service.get_initiatives()
    active = [i for i in initiatives if i["status"] not in ("Complete", "On Hold")]
    on_hold = [i for i in initiatives if i["status"] == "On Hold"]
    return templates.TemplateResponse(request, "tracker_share.html", {
        "active_initiatives": active,
        "on_hold_initiatives": on_hold,
        "report_date": date.today().strftime("%B %d, %Y"),
    })


@router.get("/export/confluence-markdown", response_class=PlainTextResponse)
async def export_confluence_markdown(db: Session = Depends(get_db)):
    """Export tracker as Confluence-ready markdown table."""
    from app.services.portfolio_service import PortfolioService
    portfolio_service = PortfolioService(db)
    initiatives = portfolio_service.get_initiatives()

    active = [i for i in initiatives if i["status"] not in ("Complete", "On Hold")]
    on_hold = [i for i in initiatives if i["status"] == "On Hold"]
    completed = [i for i in initiatives if i["status"] == "Complete"]

    def format_doc_links(doc_links):
        """Format document links as markdown links."""
        if not doc_links:
            return "—"
        links = []
        for link in doc_links:
            label = link.get("label", "Link")
            url = link.get("url", "")
            if url:
                links.append(f"[{label}]({url})")
        return ", ".join(links) if links else "—"

    lines = [
        f"# Workstream Tracker",
        f"",
        f"*Last updated: {date.today().strftime('%B %d, %Y')}*",
        f"",
        f"## Active Workstreams",
        f"",
        f"| Workstream | Status | Next Steps | Owner | Target | Docs |",
        f"|------------|--------|------------|-------|--------|------|",
    ]

    for i in active:
        name = i["name"]
        if i.get("description"):
            name = f"**{i['name']}** - {i['description']}"
        else:
            name = f"**{i['name']}**"
        status = i["status"]
        next_steps = (i.get("next_steps") or "—").replace("|", "/")
        owner = i.get("owner") or "—"
        target = i.get("target") or "—"
        docs = format_doc_links(i.get("document_links"))
        lines.append(f"| {name} | {status} | {next_steps} | {owner} | {target} | {docs} |")

    if on_hold:
        lines.extend([
            f"",
            f"## On Hold",
            f"",
            f"| Workstream | Reason / Notes | Owner | Target | Docs |",
            f"|------------|----------------|-------|--------|------|",
        ])
        for i in on_hold:
            name = f"**{i['name']}**"
            notes = (i.get("next_steps") or "—").replace("|", "/")
            owner = i.get("owner") or "—"
            target = i.get("target") or "—"
            docs = format_doc_links(i.get("document_links"))
            lines.append(f"| {name} | {notes} | {owner} | {target} | {docs} |")

    if completed:
        lines.extend([
            f"",
            f"## Completed",
            f"",
            f"| Workstream | Outcome | Owner | Docs |",
            f"|------------|---------|-------|------|",
        ])
        for i in completed:
            name = f"**{i['name']}**"
            outcome = (i.get("next_steps") or i.get("description") or "—").replace("|", "/")
            owner = i.get("owner") or "—"
            docs = format_doc_links(i.get("document_links"))
            lines.append(f"| {name} | {outcome} | {owner} | {docs} |")

    return "\n".join(lines)
