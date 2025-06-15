from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncAttrs

# 비동기 지원을 위한 SQLAlchemy 기본 클래스
Base = declarative_base(cls=AsyncAttrs) 