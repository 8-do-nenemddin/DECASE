# app/schemas/as_is.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class TocEntry(BaseModel):
    title: str
    page: int
    is_requirement_related: bool # as_is_module.ipynb 에서는 이 필드를 As-Is 관련성으로도 활용

class ParsedToc(BaseModel):
    toc_entries: List[TocEntry]

class TargetSection(BaseModel):
    title: str
    start_page: int
    end_page: int

class ExtractedAsIsChunk(BaseModel): # summarize_chunk_for_as_is 함수의 반환 JSON 구조 기반
    overview: Optional[str] = "정보 없음"
    dynamic_functional_areas: Optional[Dict[str, str]] = {}
    non_functional_aspects: Optional[Dict[str, str]] = {}
    tech_architecture: Optional[Dict[str, str]] = {}

class AsIsReportResponse(BaseModel):
    message: str
    report_filename: Optional[str] = None
    error: Optional[str] = None