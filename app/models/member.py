from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Member(Base):
    __tablename__ = 'tn_members'

    member_id = Column(Integer, primary_key=True, autoincrement=True)
    id = Column(String(30), nullable=False)
    password = Column(String(30), nullable=False)
    name = Column(String(10), nullable=False)
    email = Column(String(50), nullable=False)
    
    # Foreign keys
    company_id = Column(Integer, ForeignKey('tm_companies.company_id'), nullable=False)
    department_id = Column(Integer, ForeignKey('tn_departments.department_id'), nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="members")
    department = relationship("Department", back_populates="members")
    requirements = relationship("Requirement", back_populates="member")
    documents = relationship("Document", back_populates="member")
