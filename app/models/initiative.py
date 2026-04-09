"""Initiative model - in-flight project tracking for portfolio view."""
import json
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Initiative(Base):
    __tablename__ = "initiatives"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    status = Column(String(50), default="In Progress")
    target = Column(String(100))
    description = Column(Text)        # What: brief summary of the workstream
    next_steps = Column(Text)         # What's happening right now / immediate actions
    owner = Column(String(200))
    confluence_link = Column(String(500), nullable=True)  # Legacy: single Confluence link
    document_links = Column(Text, nullable=True)  # JSON array: [{"label": "...", "url": "..."}]
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def get_document_links(self):
        """Parse document_links JSON, falling back to confluence_link for backwards compatibility."""
        if self.document_links:
            try:
                return json.loads(self.document_links)
            except (json.JSONDecodeError, TypeError):
                pass
        # Fallback: if we have a legacy confluence_link but no document_links, use it
        if self.confluence_link:
            return [{"label": "Confluence", "url": self.confluence_link}]
        return []

    def set_document_links(self, links: list):
        """Set document_links from a list of {label, url} dicts."""
        if links:
            self.document_links = json.dumps(links)
        else:
            self.document_links = None
