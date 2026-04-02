"""Accomplishment model - tracks completed work for manager 1:1s."""
from sqlalchemy import Column, Integer, String, DateTime, Text, Date
from sqlalchemy.sql import func
from app.database import Base

class Accomplishment(Base):
    __tablename__ = "accomplishments"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    impact = Column(Text, nullable=True)  # User-added impact narrative
    
    # Category: task, jira, initiative, meeting_action
    category = Column(String(50), nullable=False, default="task")
    
    # Source references
    source_task_id = Column(Integer, nullable=True)  # FK to tasks.id if from task
    source_jira_key = Column(String(50), nullable=True)  # e.g., JUPITER-1234
    source_note_id = Column(Integer, nullable=True)  # FK to meeting_notes.id if from note
    
    # Timing
    completed_date = Column(Date, nullable=False)
    week_of = Column(Date, nullable=False)  # Monday of the week for grouping
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Accomplishment(id={self.id}, title={self.title[:30]}..., week={self.week_of})>"
