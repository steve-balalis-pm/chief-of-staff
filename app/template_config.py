"""Template configuration with custom filters."""
import re
from pathlib import Path
from datetime import datetime
import markdown as md_lib
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent
JIRA_DATA_DIR = BASE_DIR.parent / "jira_data"


def get_jira_freshness():
    """Get the timestamp of when the Jira JSON data was last refreshed."""
    filepath = JIRA_DATA_DIR / "jupiter_open.json"
    if filepath.exists():
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        return mtime.strftime("%Y-%m-%d %H:%M")
    return "No data"

def render_markdown(text):
    """Convert markdown to HTML using the markdown library.
    
    Strips the wrapping <p> tag for single-line inline content so task text
    renders inline rather than as a block element.
    """
    if not text:
        return text
    result = md_lib.markdown(str(text))
    # Strip single wrapping <p>...</p> for inline task content
    result = re.sub(r'^<p>(.*)</p>$', r'\1', result.strip(), flags=re.DOTALL)
    return result

def setup_templates():
    """Create Jinja2Templates with custom filters."""
    templates = Jinja2Templates(directory=BASE_DIR / "templates")
    templates.env.filters['markdown'] = render_markdown
    templates.env.autoescape = False  # Allow HTML from markdown filter
    templates.env.globals['jira_freshness'] = get_jira_freshness
    return templates

# Shared templates instance
templates = setup_templates()
