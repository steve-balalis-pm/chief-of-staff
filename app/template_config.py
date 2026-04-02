"""Template configuration with custom filters."""
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent

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
    return templates

# Shared templates instance
templates = setup_templates()
