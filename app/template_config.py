"""Template configuration with custom filters."""
import re
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
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
    """Convert basic markdown to HTML."""
    if not text:
        return text
    
    # Bold: **text** or __text__
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    
    # Italic: *text* or _text_
    text = re.sub(r'\*([^*]+?)\*', r'<em>\1</em>', text)
    text = re.sub(r'_([^_]+?)_', r'<em>\1</em>', text)
    
    # Links: [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    
    # Inline code: `code`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # Strikethrough: ~~text~~
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    
    return text

def setup_templates():
    """Create Jinja2Templates with custom filters."""
    templates = Jinja2Templates(directory=BASE_DIR / "templates")
    templates.env.filters['markdown'] = render_markdown
    templates.env.autoescape = False  # Allow HTML from markdown filter
    templates.env.globals['jira_freshness'] = get_jira_freshness
    return templates

# Shared templates instance
templates = setup_templates()
