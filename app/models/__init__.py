from app.database import Base
from app.models.company import Company
from app.models.department import Department
from app.models.member import Member
from app.models.project import Project
from app.models.document import Document
from app.models.requirement import Requirement
from app.models.source import Source

# This ensures all models are imported and their relationships are properly initialized
__all__ = [
    'Base',
    'Company',
    'Department',
    'Member',
    'Project',
    'Document',
    'Requirement',
    'Source'
] 