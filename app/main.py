"""
Chief of Staff Hub App - Main FastAPI Application
"""
import logging
import traceback
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import init_db
from app.routers import dashboard, tasks, portfolio, notes, reference, jira, briefing

load_dotenv()

# --- Logging setup ---
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "app.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("chief_of_staff")

# --- App ---
app = FastAPI(
    title="Chief of Staff Hub",
    description="Personal productivity hub for TPM work",
    version="1.0.0",
    docs_url="/docs",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(dashboard.router)
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(notes.router, prefix="/notes", tags=["notes"])
app.include_router(reference.router, prefix="/reference", tags=["reference"])
app.include_router(jira.router)
app.include_router(briefing.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Chief of Staff Hub starting up")
    init_db()
    logger.info("Database initialized")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Log all unhandled exceptions and return a friendly error response."""
    logger.error(
        "Unhandled exception on %s %s: %s\n%s",
        request.method,
        request.url.path,
        exc,
        traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Something went wrong. Check logs/app.log for details."},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": "Chief of Staff Hub"}
