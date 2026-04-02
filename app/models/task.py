"""Task model - syncs with TASKS.md."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    section = Column(String(100), nullable=False)  # e.g., "active_today", "this_week", "ongoing"
    subsection = Column(String(100), nullable=True)  # e.g., "high_priority", "medium_priority"
    priority = Column(String(20), default="medium")  # high, medium, low
    done = Column(Boolean, default=False)
    jira_link = Column(String(500), nullable=True)
    zendesk_link = Column(String(500), nullable=True)
    sub_items = Column(Text, nullable=True)  # JSON array of sub-items
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # For syncing with TASKS.md
    md_line_hash = Column(String(64), nullable=True)  # Hash of original markdown line
    
    def __repr__(self):
        status = "done" if self.done else "open"
        return f"<Task(id={self.id}, status={status}, section={self.section})>"
