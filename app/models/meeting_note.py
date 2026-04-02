"""Meeting note and action item models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class MeetingNote(Base):
    __tablename__ = "meeting_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=True)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    processed = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    action_items = relationship("ActionItem", back_populates="meeting_note", cascade="all, delete-orphan")
    
    def __repr__(self):
        status = "processed" if self.processed else "pending"
        return f"<MeetingNote(id={self.id}, title={self.title}, status={status})>"


class ActionItem(Base):
    __tablename__ = "action_items"
    
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("meeting_notes.id"), nullable=False)
    text = Column(Text, nullable=False)
    assignee = Column(String(100), nullable=True)  # Extracted assignee if found
    
    pushed_to_tasks = Column(Boolean, default=False)
    task_id = Column(Integer, nullable=True)  # FK to tasks.id if pushed
    dismissed = Column(Boolean, default=False)  # User chose not to add
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    meeting_note = relationship("MeetingNote", back_populates="action_items")
    
    def __repr__(self):
        status = "pushed" if self.pushed_to_tasks else ("dismissed" if self.dismissed else "pending")
        return f"<ActionItem(id={self.id}, status={status})>"
