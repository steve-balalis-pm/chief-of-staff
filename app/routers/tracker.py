"""Tracker router - manager-facing workstream status tracker."""
import json
from datetime import date

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.initiative import Initiative
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


@router.get("/edit/{initiative_id}", response_class=HTMLResponse)
async def edit_initiative_form(request: Request, initiative_id: int, db: Session = Depends(get_db)):
    """Full-page edit form for an initiative."""
    initiative = db.query(Initiative).filter(Initiative.id == initiative_id).first()
    if not initiative:
        return RedirectResponse(url="/tracker/", status_code=303)
    return templates.TemplateResponse(request, "tracker_edit.html", {
        "active": "tracker",
        "initiative": {
            "id": initiative.id,
            "name": initiative.name,
            "status": initiative.status,
            "target": initiative.target or "",
            "description": initiative.description or "",
            "next_steps": initiative.next_steps or "",
            "owner": initiative.owner or "",
            "impact": initiative.impact or "",
            "jira_epic": initiative.jira_epic or "",
            "group_label": initiative.group_label or "",
            "completed_date": initiative.completed_date.isoformat() if initiative.completed_date else "",
            "document_links": initiative.get_document_links(),
        }
    })


@router.post("/edit/{initiative_id}")
async def save_initiative_edit(
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
    group_label: str = Form(""),
    db: Session = Depends(get_db),
):
    """Save changes from the full-page edit form."""
    from datetime import date as date_type
    initiative = db.query(Initiative).filter(Initiative.id == initiative_id).first()
    if not initiative:
        return RedirectResponse(url="/tracker/", status_code=303)

    form_data = await request.form()
    doc_labels = form_data.getlist("doc_label[]")
    doc_urls = form_data.getlist("doc_url[]")
    document_links = [
        {"label": lbl.strip() or "Link", "url": url.strip()}
        for lbl, url in zip(doc_labels, doc_urls) if url and url.strip()
    ]

    initiative.name = name
    initiative.status = status
    initiative.target = target
    initiative.description = description
    initiative.next_steps = next_steps
    initiative.owner = owner
    initiative.impact = impact or None
    initiative.jira_epic = jira_epic or None
    initiative.group_label = group_label or None
    initiative.set_document_links(document_links)

    if completed_date and completed_date.strip():
        try:
            initiative.completed_date = date_type.fromisoformat(completed_date.strip())
        except ValueError:
            pass
    else:
        initiative.completed_date = None

    db.commit()
    return RedirectResponse(url="/tracker/", status_code=303)


@router.get("/share", response_class=HTMLResponse)
async def tracker_share(request: Request, db: Session = Depends(get_db)):
    """Printable bi-weekly update for manager — no nav, clean layout."""
    from app.services.portfolio_service import PortfolioService
    portfolio_service = PortfolioService(db)
    initiatives = portfolio_service.get_initiatives()
    active = [i for i in initiatives if i["status"] not in ("Complete", "On Hold")]
    on_hold = [i for i in initiatives if i["status"] == "On Hold"]
    completed = [i for i in initiatives if i["status"] == "Complete"]
    return templates.TemplateResponse(request, "tracker_share.html", {
        "active_initiatives": active,
        "on_hold_initiatives": on_hold,
        "completed_initiatives": completed,
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
