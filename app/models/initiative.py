"""Initiative model - in-flight project tracking for portfolio view."""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Initiative(Base):
    __tablename__ = "initiatives"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    status = Column(String(50), default="In Progress")
    target = Column(String(100))
    description = Column(Text)
    owner = Column(String(200))
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
