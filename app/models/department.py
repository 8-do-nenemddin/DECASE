from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Department(Base):
    __tablename__ = "tn_departments"

    department_id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String(30), nullable=False)
    company_id = Column(Integer, ForeignKey('tm_companies.company_id'), nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="departments")
    members = relationship("Member", back_populates="department", cascade="all, delete-orphan") 