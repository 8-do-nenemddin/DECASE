from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.database import Base

class Company(Base):
    __tablename__ = 'tm_companies'

    company_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), nullable=False)  # 회사 명
    description = Column(String(500))

    # Relationships
    departments = relationship("Department", back_populates="company", cascade="all, delete-orphan")
    members = relationship("Member", back_populates="company", cascade="all, delete-orphan") 