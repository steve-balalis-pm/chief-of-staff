"""Reference router - team info, links, knowledge base."""
import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.template_config import templates

logger = logging.getLogger("chief_of_staff.reference")
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def reference_view(request: Request, db: Session = Depends(get_db)):
    """Reference view with team info, links, goals."""
    from app.services.context_loader import ContextLoaderService
    from app.services.confluence_service import ConfluenceService

    loader = ContextLoaderService()
    context = loader.load_all()

    confluence = ConfluenceService()
    confluence_data = confluence.get_pages()

    return templates.TemplateResponse("reference.html", {
        "request": request,
        "teams": context.get("teams", {}),
        "tools": context.get("tools", []),
        "goals": context.get("goals", {}),
        "terminology": context.get("terminology", []),
        "confluence": confluence_data,
    })
