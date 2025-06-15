from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class ProjectStatus(enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class Project(Base):
    __tablename__ = 'tm_projects'

    project_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    scale = Column(Integer, nullable=False, default=0)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    description = Column(String(1000), nullable=False)
    proposal_pm = Column(String(100))
    revision_count = Column(Integer, nullable=False, default=1)
    status = Column(Enum(ProjectStatus), nullable=False)
    created_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    modified_date = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
