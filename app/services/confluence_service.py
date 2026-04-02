"""Confluence service - reads cached page data written by Claude via MCP."""
import json
import logging
from pathlib import Path

logger = logging.getLogger("chief_of_staff.confluence")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CACHE_FILE = DATA_DIR / "confluence_cache.json"


class ConfluenceService:
    """
    Reads Confluence page data from a local cache file.

    The cache is populated by Claude using the Atlassian MCP tools.
    To refresh, ask Claude: "Refresh my Confluence cache" and it will
    fetch recent PARTFEEDS pages and write them to data/confluence_cache.json.

    Cache format:
    {
        "cached_at": "2026-03-30 14:00 UTC",
        "pages": [
            {
                "title": "...",
                "url": "https://accoladeinc.atlassian.net/wiki/...",
                "last_updated": "2026-03-28",
                "updated_by": "Cara Stotz"
            },
            ...
        ]
    }
    """

    def get_pages(self) -> dict:
        """Return cached pages. Returns empty state if no cache exists yet."""
        if CACHE_FILE.exists():
            try:
                return json.loads(CACHE_FILE.read_text())
            except Exception as e:
                logger.warning("Could not read confluence cache: %s", e)
        return {"pages": [], "cached_at": None, "error": None}
